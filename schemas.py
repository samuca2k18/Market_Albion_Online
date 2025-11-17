# schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Schema para criação de usuário."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nome de usuário (3-50 caracteres)",
        examples=["johndoe"]
    )
    email: EmailStr = Field(
        ...,
        description="E-mail válido do usuário",
        examples=["usuario@example.com"]
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="Senha do usuário (mínimo 6 caracteres)",
        examples=["senha123"]
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Valida o nome de usuário."""
        if not v.strip():
            raise ValueError("Nome de usuário não pode estar vazio")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Nome de usuário deve conter apenas letras, números, _ e -")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "password": "senha123"
            }
        }
    }


class UserOut(BaseModel):
    """Schema para resposta de usuário."""
    id: int = Field(..., description="ID único do usuário")
    username: str = Field(..., description="Nome de usuário")
    email: EmailStr = Field(..., description="E-mail do usuário")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "johndoe@example.com"
            }
        }
    }


class ItemCreate(BaseModel):
    """Schema para criação de item."""
    item_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nome interno do item no formato do jogo",
        examples=["T4_BAG", "T5_HEAD_PLATE_SET1"]
    )

    @field_validator("item_name")
    @classmethod
    def validate_item_name(cls, v: str) -> str:
        """Valida e normaliza o nome do item."""
        if not v.strip():
            raise ValueError("Nome do item não pode estar vazio")
        return v.strip().upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "item_name": "T4_BAG"
            }
        }
    }


class ItemOut(BaseModel):
    """Schema para resposta de item."""
    id: int = Field(..., description="ID único do item")
    item_name: str = Field(..., description="Nome interno do item")
    created_at: Optional[datetime] = Field(
        None,
        description="Data e hora de criação do item"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "item_name": "T4_BAG",
                "created_at": "2024-01-15T10:30:00"
            }
        }
    }
