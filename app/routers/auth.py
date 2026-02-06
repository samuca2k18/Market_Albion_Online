# app/routers/auth.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt
from app.core.security import get_current_user
from app.database import SessionLocal
from app.models import User
from app.schemas import (
    UserCreate,
    UserOut,
    ResendVerificationRequest,
    VerificationMessage,
)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.services.email_verify import generate_verification_token, token_expiration
from app.services.mailer import send_verification_email

router = APIRouter(tags=["Autenticação"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário (envia verificação por e-mail)",
)
def signup(
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

    # Envia e-mail em background para não travar a requisição
    def send_email_task():
        try:
            send_verification_email(new_user.email, token)
        except Exception as e:
            import logging
            logging.error(f"Erro ao enviar email de verificação para {new_user.email}: {str(e)}")

    background_tasks.add_task(send_email_task)

    return new_user


@router.post(
    "/login",
    summary="Fazer login (bloqueado se e-mail não verificado)",
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
    return {"access_token": access_token, "token_type": "bearer"}


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
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = payload.email
    # Resposta neutra para não revelar se o email existe
    neutral = {"message": "Se o e-mail existir, enviaremos um link de verificação."}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return neutral

    if user.is_verified:
        return {"message": "E-mail já verificado."}

    token = generate_verification_token()
    user.verification_token = token
    user.verification_token_expires_at = token_expiration(24)
    db.commit()

    # Envia email em background para não travar a requisição
    def send_email_task():
        import logging
        try:
            logging.info(f"Iniciando envio de email de verificação para {email}")
            send_verification_email(user.email, token)
            logging.info(f"Email de verificação enviado com sucesso para {email}")
        except Exception as e:
            logging.error(f"ERRO ao reenviar email para {email}: {str(e)}", exc_info=True)

    background_tasks.add_task(send_email_task)

    return neutral
    
@router.get("/me", response_model=UserOut, summary="Retorna o usuário logado")
def me(current_user: User = Depends(get_current_user)):
    return current_user