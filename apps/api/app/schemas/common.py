from typing import Optional
from pydantic import BaseModel


class PeriodInfo(BaseModel):
    code: str
    date_from: str
    date_to: str


class Filters(BaseModel):
    shop_id: Optional[str] = None
    q: Optional[str] = None


class Paging(BaseModel):
    limit: int
    offset: int
    total: int
