from datetime import datetime, timezone
import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
    Query,
)
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import (
    ResendVerificationRequest,
    UserCreate,
    UserOut,
    VerificationMessage,
)
from app.services.email_verify import generate_verification_token, token_expiration
from app.services.mailer import send_verification_email

router = APIRouter(tags=["Autenticação"])


def _cookie_secure() -> bool:
    if os.getenv("TESTING") == "true":
        return settings.REFRESH_COOKIE_SECURE

    if settings.REFRESH_COOKIE_SECURE:
        return True

    frontend_url = (settings.FRONTEND_URL or "").strip().lower()
    app_base_url = (settings.APP_BASE_URL or "").strip().lower()
    return frontend_url.startswith("https://") or app_base_url.startswith("https://")


def _cookie_samesite() -> str:
    same_site = (settings.REFRESH_COOKIE_SAMESITE or "lax").strip().lower()
    if same_site not in {"lax", "strict", "none"}:
        same_site = "lax"
    # Browsers reject SameSite=None without Secure.
    if same_site == "none" and not _cookie_secure():
        same_site = "lax"
    return same_site


def _set_refresh_cookie(response: Response, refresh_token_value: str) -> None:
    max_age = int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    cookie_domain = settings.REFRESH_COOKIE_DOMAIN or None
    cookie_path = settings.REFRESH_COOKIE_PATH or "/"
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token_value,
        max_age=max_age,
        expires=max_age,
        path=cookie_path,
        domain=cookie_domain,
        secure=_cookie_secure(),
        httponly=True,
        samesite=_cookie_samesite(),
    )


def _clear_refresh_cookie(response: Response) -> None:
    cookie_domain = settings.REFRESH_COOKIE_DOMAIN or None
    cookie_path = settings.REFRESH_COOKIE_PATH or "/"
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=cookie_path,
        domain=cookie_domain,
    )


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário (envia verificação por e-mail)",
)
@limiter.limit("3/minute")
def signup(
    request: Request,
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()

    if existing:
        if existing.username == user.username:
            raise HTTPException(status_code=400, detail="Nome de usuário já cadastrado")
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    token = generate_verification_token()

    try:
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
            is_verified=False,
            verification_token=token,
            verification_token_expires_at=token_expiration(24),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Erro ao cadastrar usuário.")

    def send_email_task():
        try:
            send_verification_email(new_user.email, token)
        except Exception as exc:  # pragma: no cover
            import logging

            logging.error(
                "Erro ao enviar email de verificação para %s: %s",
                new_user.email,
                exc,
            )

    background_tasks.add_task(send_email_task)
    return new_user


@router.post("/login", summary="Fazer login (bloqueado se e-mail não verificado)")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E-mail não verificado. Verifique seu e-mail antes de entrar.",
        )

    access_token = create_access_token({"sub": user.username})
    refresh_token_value = create_refresh_token({"sub": user.username})
    _set_refresh_cookie(response, refresh_token_value)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout", summary="Encerra a sessão atual")
def logout(response: Response):
    _clear_refresh_cookie(response)
    return {"message": "Sessão encerrada"}


@router.get(
    "/verify-email",
    summary="Confirmar e-mail pelo token",
    response_model=VerificationMessage,
)
def verify_email(token: str = Query(..., min_length=10), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")

    if user.is_verified:
        return {"message": "E-mail já verificado"}

    expires_at = user.verification_token_expires_at
    now = datetime.now(timezone.utc)

    if not expires_at or expires_at < now:
        raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo.")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()

    return {"message": "E-mail verificado com sucesso. Você já pode fazer login."}


@router.post(
    "/resend-verification",
    summary="Reenviar link de verificação",
    response_model=VerificationMessage,
)
@limiter.limit("5/minute")
def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = payload.email
    neutral = {"message": "Se o e-mail existir, enviaremos um link de verificação."}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return neutral

    if user.is_verified:
        return neutral

    token = generate_verification_token()
    user.verification_token = token
    user.verification_token_expires_at = token_expiration(24)
    db.commit()

    def send_email_task():
        import logging

        try:
            send_verification_email(user.email, token)
        except Exception as exc:  # pragma: no cover
            logging.error("Erro ao reenviar email para %s: %s", email, exc, exc_info=True)

    background_tasks.add_task(send_email_task)
    return neutral


@router.get("/me", response_model=UserOut, summary="Retorna o usuário logado")
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", summary="Renova o access token usando refresh token em cookie HttpOnly")
def refresh_token(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token_value: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not refresh_token_value:
        _clear_refresh_cookie(response)
        raise credentials_exception

    try:
        payload = jwt.decode(refresh_token_value, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "refresh_token":
            _clear_refresh_cookie(response)
            raise credentials_exception
        username: str = payload.get("sub")
        if not username:
            _clear_refresh_cookie(response)
            raise credentials_exception
    except JWTError:
        _clear_refresh_cookie(response)
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        _clear_refresh_cookie(response)
        raise credentials_exception

    new_access_token = create_access_token({"sub": user.username})
    # Rotacao do refresh token.
    new_refresh_token = create_refresh_token({"sub": user.username})
    _set_refresh_cookie(response, new_refresh_token)

    return {"access_token": new_access_token, "token_type": "bearer"}
