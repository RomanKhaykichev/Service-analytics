from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProductCogsItem(BaseModel):
    barcode: Optional[str] = None
    barcode_norm: str
    product_name: Optional[str] = None
    sku: Optional[str] = None
    product_image_url: Optional[str] = None
    price: Optional[float] = None
    lk_cogs: Optional[float] = None
    actual_cogs: Optional[float] = None
    unit_margin: Optional[float] = None
    calculation_source: Literal["uzum", "profiboard"] = "uzum"
    date: Optional[str] = None
    effective_from: Optional[str] = None
    first_sale_date: Optional[str] = None


class ProductCogsListResponse(BaseModel):
    items: list[ProductCogsItem]


class ProductCogsUpsertRequest(BaseModel):
    actual_cogs: float = Field(..., ge=0)
    barcode: Optional[str] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None
    shop: Optional[str] = None
    effective_from: str = Field(..., description="Дата начиная с (YYYY-MM-DD)")

    @field_validator("effective_from")
    @classmethod
    def validate_effective_from(cls, v: Optional[str]) -> str:
        if v is None or not str(v).strip():
            raise ValueError("effective_from is required")
        s = str(v).strip()
        if len(s) != 10 or s[4] != "-" or s[7] != "-":
            raise ValueError("effective_from must be YYYY-MM-DD")
        return s


class ProductCogsHistoryEntry(BaseModel):
    period_from: str
    period_to: str
    cogs: float
    calculation_source: Literal["uzum", "profiboard"] = "profiboard"
    effective_from: Optional[str] = None
    can_delete: bool = False


class ProductCogsHistoryResponse(BaseModel):
    product_name: Optional[str] = None
    sku: Optional[str] = None
    first_sale_date: Optional[str] = None
    items: list[ProductCogsHistoryEntry] = []


class ProductCogsTemplateUploadResponse(BaseModel):
    imported: int = 0
    skipped: int = 0
    errors: list[str] = []