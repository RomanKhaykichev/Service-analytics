from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_user
from app.utils.tenant_shop_allowlist import norm_shop_label
from app.utils.trial_shop import (
    fetch_loaded_shop_labels,
    get_effective_trial_display_shop,
    is_trial_plan_user,
    set_trial_permitted_shop,
    user_needs_trial_shop_selection,
)

router = APIRouter()


class TrialShopOption(BaseModel):
    shop_id: str
    shop_name: str


class TrialShopSelectionStatus(BaseModel):
    is_trial: bool
    needs_selection: bool
    trial_display_shop: str | None = None
    loaded_shops: list[TrialShopOption] = []


class TrialShopSelectBody(BaseModel):
    shop: str


class TrialShopSelectResponse(BaseModel):
    ok: bool = True
    trial_display_shop: str


@router.get("/trial/shop-selection", response_model=TrialShopSelectionStatus)
async def trial_shop_selection_status(
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    is_trial = is_trial_plan_user(db, user_id)
    loaded = fetch_loaded_shop_labels(db, user_id)
    display = get_effective_trial_display_shop(db, user_id) if is_trial else None
    options = [
        TrialShopOption(
            shop_id=norm_shop_label(name) or name,
            shop_name=name,
        )
        for name in loaded
    ]
    return TrialShopSelectionStatus(
        is_trial=is_trial,
        needs_selection=is_trial and user_needs_trial_shop_selection(db, user_id),
        trial_display_shop=display,
        loaded_shops=options,
    )


@router.post("/trial/shop-selection", response_model=TrialShopSelectResponse)
async def trial_shop_selection_set(
    body: TrialShopSelectBody,
    user_id: UUID = Depends(require_user),
    db: Session = Depends(get_db),
):
    if not is_trial_plan_user(db, user_id):
        raise HTTPException(status_code=400, detail="Выбор trial-магазина доступен только на trial-тарифе")
    if get_effective_trial_display_shop(db, user_id):
        raise HTTPException(
            status_code=409,
            detail="Магазин для trial уже выбран. Обратитесь в поддержку для смены.",
        )
    canon = set_trial_permitted_shop(db, user_id, body.shop, allow_overwrite=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return TrialShopSelectResponse(trial_display_shop=canon)
