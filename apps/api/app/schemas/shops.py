from pydantic import BaseModel
from typing import Optional


class Shop(BaseModel):
    shop_id: str
    shop_name: Optional[str] = None


class ShopsResponse(BaseModel):
    shops: list[Shop]
