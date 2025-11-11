# schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    item_name: str


class ItemOut(BaseModel):
    id: int
    item_name: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
