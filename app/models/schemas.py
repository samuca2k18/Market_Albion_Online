from typing import List, Optional
from pydantic import BaseModel, Field

class MaterialSchema(BaseModel):
    id: int
    amount: int
    item_id: Optional[int] = None
    resource: str
    name: Optional[str] = None
    icon: Optional[str] = None

class ConsumableSchema(BaseModel):
    id: int
    name: str
    identifier: str
    tier: int
    item_power: int
    icon: Optional[str] = None

class CraftingRowSchema(BaseModel):
    id: int
    yield_amount: int
    item_id: int
    category_id: Optional[int] = None
    enchantment: int
    materials: List[MaterialSchema]
    consumable: Optional[ConsumableSchema] = None

class CraftingResponseSchema(BaseModel):
    data: List[CraftingRowSchema]
