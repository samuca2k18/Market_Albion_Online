# main.py
import os
import logging
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from jose import JWTError, jwt
import requests
from requests.exceptions import RequestException, Timeout
from dotenv import load_dotenv

from database import Base, engine, SessionLocal
from models import User, UserItem
from schemas import ItemCreate, ItemOut, UserCreate, UserOut
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Cria as tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# Configuração da API do Albion
ALBION_API_BASE_URL = os.getenv(
    "ALBION_API_BASE_URL",
    "https://www.albion-online-data.com/api/v2/stats/prices"
)
ALBION_API_TIMEOUT = int(os.getenv("ALBION_API_TIMEOUT", "10"))

# Cidades padrão do Albion Online
DEFAULT_CITIES = "Bridgewatch,Martlock,Thetford,Lymhurst,FortSterling,Caerleon"

# Configuração do FastAPI
app = FastAPI(
    title="Albion Market API",
    description="API para consulta de preços de itens do jogo Albion Online",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    """
    Dependency para obter sessão do banco de dados.
    Garante que a conexão seja fechada após o uso.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global para exceções não tratadas.
    """
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor"},
    )


@app.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar novo usuário",
    description="Cria uma nova conta de usuário no sistema",
    tags=["Autenticação"],
)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """
    Cadastra um novo usuário no sistema.
    
    - **username**: Nome de usuário único
    - **email**: E-mail válido e único
    - **password**: Senha com pelo menos 6 caracteres
    """
    # Verifica se já existe usuário com mesmo username ou email
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    
    if existing:
        if existing.username == user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome de usuário já cadastrado"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail já cadastrado"
            )

    try:
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password)
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"Novo usuário cadastrado: {user.username}")
        return new_user
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao cadastrar usuário. Verifique os dados fornecidos."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/login",
    summary="Fazer login",
    description="Autentica um usuário e retorna um token JWT",
    tags=["Autenticação"],
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Autentica um usuário e retorna um token de acesso JWT.
    
    - **username**: Nome de usuário
    - **password**: Senha do usuário
    
    Retorna um token JWT que deve ser usado nas requisições autenticadas.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        logger.warning(f"Tentativa de login com usuário inexistente: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Tentativa de login com senha incorreta para: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user.username})
    logger.info(f"Login bem-sucedido: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obter o usuário atual autenticado.
    Valida o token JWT e retorna o usuário correspondente.
    """
    cred_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        
        if username is None:
            raise cred_exception
            
    except JWTError as e:
        logger.warning(f"Erro ao decodificar token: {e}")
        raise cred_exception

    user = db.query(User).filter(User.username == username).first()
    
    if user is None:
        logger.warning(f"Usuário não encontrado para token: {username}")
        raise cred_exception
        
    return user


@app.get(
    "/me",
    response_model=UserOut,
    summary="Obter informações do usuário atual",
    description="Retorna as informações do usuário autenticado",
    tags=["Usuário"],
)
def read_me(current_user: User = Depends(get_current_user)):
    """
    Retorna as informações do usuário autenticado.
    Requer autenticação via token JWT.
    """
    return current_user

@app.post(
    "/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Adicionar item à lista",
    description="Adiciona um novo item à lista de monitoramento do usuário",
    tags=["Itens"],
)
def add_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adiciona um novo item à lista de monitoramento do usuário.
    
    - **item_name**: Nome interno do item (ex: T4_BAG, T5_HEAD_PLATE_SET1)
    
    O item será vinculado ao usuário autenticado.
    """
    # Verifica se o item já existe para o usuário
    existing_item = db.query(UserItem).filter(
        UserItem.user_id == current_user.id,
        UserItem.item_name == item.item_name
    ).first()
    
    if existing_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item já está na sua lista de monitoramento"
        )
    
    try:
        new_item = UserItem(
            user_id=current_user.id,
            item_name=item.item_name.strip().upper()
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        logger.info(f"Item {item.item_name} adicionado para usuário {current_user.username}")
        return new_item
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erro ao adicionar item"
        )


@app.get(
    "/items",
    response_model=List[ItemOut],
    summary="Listar itens do usuário",
    description="Retorna todos os itens na lista de monitoramento do usuário",
    tags=["Itens"],
)
def list_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna todos os itens na lista de monitoramento do usuário autenticado.
    Os itens são ordenados por data de criação (mais recentes primeiro).
    """
    items = db.query(UserItem).filter(
        UserItem.user_id == current_user.id
    ).order_by(UserItem.created_at.desc()).all()
    
    return items

@app.get(
    "/albion/price",
    summary="Consultar preço de item",
    description="Consulta o preço de um item específico nas cidades do Albion Online",
    tags=["Albion Online"],
)
def get_albion_price(
    item_name: str = Query(
        ...,
        description="Nome interno do item (ex: T4_BAG, T5_HEAD_PLATE_SET1)",
        min_length=1,
        max_length=100
    ),
    cities: str = Query(
        DEFAULT_CITIES,
        description="Lista de cidades separadas por vírgula (ex: Bridgewatch,Martlock,Thetford)"
    ),
    current_user: User = Depends(get_current_user)
):
    """
    Consulta o preço de um item específico nas cidades do Albion Online.
    
    - **item_name**: Nome interno do item no formato do jogo
    - **cities**: Lista de cidades separadas por vírgula (opcional)
    
    Retorna a cidade mais barata e todos os dados de preço disponíveis.
    """
    # Normaliza o nome do item
    item_name = item_name.strip().upper()
    
    # Valida e normaliza as cidades
    city_list = [city.strip() for city in cities.split(",") if city.strip()]
    
    if not city_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pelo menos uma cidade deve ser especificada"
        )
    
    url = f"{ALBION_API_BASE_URL}/{item_name}?locations={','.join(city_list)}"
    
    try:
        resp = requests.get(url, timeout=ALBION_API_TIMEOUT)
        resp.raise_for_status()
        
    except Timeout:
        logger.error(f"Timeout ao consultar preço do item {item_name}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout ao consultar a API do Albion Online"
        )
    except RequestException as e:
        logger.error(f"Erro ao consultar API do Albion: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Erro ao consultar a API do Albion Online"
        )

    try:
        data = resp.json()
    except ValueError:
        logger.error(f"Resposta inválida da API do Albion para item {item_name}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta inválida da API do Albion Online"
        )

    if not data or not isinstance(data, list):
        return {
            "item": item_name,
            "cities_checked": city_list,
            "message": "Nenhum dado retornado para esse item/cidades",
            "data": []
        }

    # Filtra apenas itens com preço de venda válido
    valid = [
        d for d in data
        if isinstance(d, dict) and d.get("sell_price_min", 0) > 0
    ]

    if not valid:
        return {
            "item": item_name,
            "cities_checked": city_list,
            "message": "Item encontrado, mas sem preço de venda disponível nas cidades informadas",
            "data": data
        }

    # Ordena por preço e pega o mais barato
    valid.sort(key=lambda x: x.get("sell_price_min", float("inf")))
    cheapest = valid[0]

    return {
        "item": item_name,
        "cities_checked": city_list,
        "cheapest_city": cheapest.get("city", "N/A"),
        "cheapest_price": cheapest.get("sell_price_min", 0),
        "all_data": data
    }

@app.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover item",
    tags=["Itens"],
)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    item = db.query(UserItem).filter(
        UserItem.id == item_id,
        UserItem.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item não encontrado"
        )
    
    db.delete(item)
    db.commit()
    return None

@app.get(
    "/albion/my-items-prices",
    summary="Consultar preços dos meus itens",
    description="Retorna preços no formato compatível com o frontend (array direto)",
    tags=["Albion Online"],
)
def get_my_items_prices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cities: str = Query(
        DEFAULT_CITIES,
        description="Lista de cidades separadas por vírgula"
    ),
    quality: int = Query(0, description="Qualidade do item (0 = qualquer)"),
    enchantment: int = Query(0, description="Encantamento (0 = qualquer)")
):
    user_items = db.query(UserItem).filter(UserItem.user_id == current_user.id).all()
    
    if not user_items:
        return []  # ← frontend espera array vazio

    city_list = [c.strip() for c in cities.split(",") if c.strip()]
    if not city_list:
        city_list = DEFAULT_CITIES.split(",")

    results = []

    for ui in user_items:
        item_name = ui.item_name

        # Monta o item com qualidade e encantamento se necessário
        base_name = item_name
        item_quality = quality
        item_enchant = enchantment

        # Detecta qualidade/encantamento no nome (ex: T4_BAG@3 ou T5_SHOES_CLOTH_SET1.1)
        if "@" in item_name:
            base_name, enchant_str = item_name.split("@", 1)
            try:
                item_enchant = int(enchant_str)
            except:
                item_enchant = 0
        elif "." in item_name:
            parts = item_name.split(".")
            if len(parts) > 1:
                try:
                    item_quality = int(parts[-1])
                    base_name = ".".join(parts[:-1])
                except:
                    pass

        url = f"{ALBION_API_BASE_URL}/{base_name}"
        params = {"locations": ",".join(city_list)}
        if item_quality > 0:
            params["qualities"] = str(item_quality)
        if item_enchant > 0:
            item_name_with_enchant = f"{base_name}@{item_enchant}"
            url = f"{ALBION_API_BASE_URL}/{item_name_with_enchant}"

        try:
            resp = requests.get(url, params=params, timeout=ALBION_API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            valid_prices = [d for d in data if d.get("sell_price_min", 0) > 0]
            if not valid_prices:
                continue

            valid_prices.sort(key=lambda x: x.get("sell_price_min", float("inf")))
            cheapest = valid_prices[0]

            results.append({
                "item_name": ui.item_name,
                "city": cheapest.get("city", "N/A"),
                "price": cheapest.get("sell_price_min", 0),
                "quality": cheapest.get("quality", 1),
                "enchantment": item_enchant,
                "date": cheapest.get("sell_price_min_date", None)
            })

        except Exception as e:
            logger.warning(f"Erro ao buscar {ui.item_name}: {e}")
            continue

    # Ordena por preço crescente
    results.sort(key=lambda x: x["price"])
    return results  # ← agora retorna array direto de objetos!
@app.get(
    "/health",
    summary="Health check",
    description="Endpoint para verificar o status da API",
    tags=["Sistema"],
)
def health_check():
    """
    Endpoint de health check para monitoramento da API.
    """
    return {
        "status": "healthy",
        "service": "Albion Market API",
        "version": "1.0.0"
    }
