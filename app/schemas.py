# schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
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
    is_verified: bool = Field(..., description="Indica se o e-mail já foi verificado")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "johndoe",
                "email": "johndoe@example.com",
                "is_verified": True
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
    display_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Nome amigável escolhido na busca (exibido ao usuário)",
        examples=["Peixe-espada de Aço"]
    )

    @field_validator("item_name")
    @classmethod
    def validate_item_name(cls, v: str) -> str:
        """Valida e normaliza o nome do item."""
        if not v.strip():
            raise ValueError("Nome do item não pode estar vazio")
        return v.strip().upper()

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        val = v.strip()
        return val or None

    model_config = {
        "json_schema_extra": {
            "example": {
                "item_name": "T4_BAG",
                "display_name": "Bolsa do Adepto"
            }
        }
    }


class ItemOut(BaseModel):
    """Schema para resposta de item."""
    id: int = Field(..., description="ID único do item")
    item_name: str = Field(..., description="Nome interno do item")
    display_name: Optional[str] = Field(
        None,
        description="Nome amigável salvo"
    )
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
                "display_name": "Bolsa do Adepto",
                "created_at": "2024-01-15T10:30:00"
            }
        }
    }


class ResendVerificationRequest(BaseModel):
    """Payload para solicitar reenvio do link de verificação."""
    email: EmailStr = Field(
        ...,
        description="E-mail cadastrado",
        examples=["usuario@example.com"]
    )


class VerificationMessage(BaseModel):
    """Resposta padrão para fluxos de verificação de e-mail."""
    message: str = Field(
        ...,
        description="Mensagem descritiva sobre o estado da verificação",
        examples=["E-mail verificado com sucesso. Você já pode fazer login."]
    )
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PriceAlertCreate(BaseModel):
    item_id: str
    display_name: Optional[str] = None
    city: Optional[str] = None
    quality: Optional[int] = None

    # manual absoluto
    target_price: Optional[float] = None

    # “abaixo do esperado” manual
    expected_price: Optional[float] = None
    percent_below: Optional[float] = 20.0  # padrão

    # IA: calcula expected_price sozinho pelo histórico
    use_ai_expected: bool = True
    ai_days: int = 7
    ai_resolution: str = "6h"   # "1h" | "6h" | "24h"
    ai_stat: str = "median"     # "median" | "mean"
    ai_min_points: int = 10

    cooldown_minutes: int = 60

    @field_validator("item_id")
    @classmethod
    def normalize_item_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("item_id não pode estar vazio")
        return v.strip().upper()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        val = v.strip()
        return val or None

    @model_validator(mode="after")
    def validate_rule(self):
        # 1) Se tiver target_price, já vale
        if self.target_price is not None:
            return self

        # 2) Se for manual esperado: precisa expected_price e percent_below
        if self.expected_price is not None and self.percent_below is not None:
            return self

        # 3) Se for IA: precisa use_ai_expected True e percent_below
        if self.use_ai_expected and self.percent_below is not None:
            return self

        raise ValueError(
            "Defina target_price OU expected_price+percent_below OU use_ai_expected+percent_below"
        )


class PriceAlertOut(PriceAlertCreate):
    id: int
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    last_expected_price: Optional[float] = None
    last_expected_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class NotificationOut(BaseModel):
    id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
