from pydantic import BaseModel
from typing import Optional


class Shop(BaseModel):
    shop_id: str
    shop_name: Optional[str] = None
    locked: bool = False
    is_trial_display: bool = False


class ShopsResponse(BaseModel):
    shops: list[Shop]
