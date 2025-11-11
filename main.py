# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from schemas import ItemCreate, ItemOut
from models import UserItem
import requests
from fastapi import Query

from database import Base, engine, SessionLocal
from models import User
from schemas import UserCreate, UserOut
from auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Albion Market API")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # verifica se já existe
    existing = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuário ou e-mail já cadastrado")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha incorreta")

    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    except JWTError:
        raise cred_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise cred_exception
    return user


@app.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/items", response_model=ItemOut)
def add_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_item = UserItem(user_id=current_user.id, item_name=item.item_name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/items", response_model=list[ItemOut])
def list_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(UserItem).filter(UserItem.user_id == current_user.id).all()
    return items

@app.get("/albion/price")
def get_albion_price(
    item_name: str = Query(..., description="Nome interno do item, ex: T4_BAG"),
    cities: str = Query(
        "Bridgewatch,Martlock,Thetford,Lymhurst,FortSterling,Caerleon",
        description="Lista de cidades separadas por vírgula"
    ),
    current_user: User = Depends(get_current_user)  # só logado consulta
):
    url = f"https://www.albion-online-data.com/api/v2/stats/prices/{item_name}?locations={cities}"
    resp = requests.get(url, timeout=10)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Erro na API do Albion")

    data = resp.json()

    if not data:
        return {"message": "Nenhum dado retornado para esse item/cidades"}


    valid = [d for d in data if d.get("sell_price_min", 0) > 0]

    if not valid:
        return {"message": "Item encontrado, mas sem preço de venda disponível nas cidades informadas", "raw": data}


    valid.sort(key=lambda x: x["sell_price_min"])
    cheapest = valid[0]

    return {
        "item": item_name,
        "cities_checked": cities.split(","),
        "cheapest_city": cheapest["city"],
        "cheapest_price": cheapest["sell_price_min"],
        "all_data": data
    }

@app.get("/albion/my-items-prices")
def get_my_items_prices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cities: str = Query("Bridgewatch,Martlock,Thetford,Lymhurst,FortSterling,Caerleon")
):
    user_items = db.query(UserItem).filter(UserItem.user_id == current_user.id).all()
    results = []

    for ui in user_items:
        url = f"https://www.albion-online-data.com/api/v2/stats/prices/{ui.item_name}?locations={cities}"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            continue
        data = resp.json()
        valid = [d for d in data if d.get("sell_price_min", 0) > 0]
        if not valid:
            results.append({
                "item": ui.item_name,
                "message": "sem preço nas cidades informadas"
            })
            continue
        valid.sort(key=lambda x: x["sell_price_min"])
        cheapest = valid[0]
        results.append({
            "item": ui.item_name,
            "cheapest_city": cheapest["city"],
            "cheapest_price": cheapest["sell_price_min"],
        })

    return {
        "user_id": current_user.id,
        "cities_checked": cities.split(","),
        "items": results
    }
