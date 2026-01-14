from fastapi import APIRouter, Request, HTTPException
from app.auth import get_user_id
from app.db import execute_all
from app.schemas import ShopsResponse, Shop

router = APIRouter()


@router.get("/shops", response_model=ShopsResponse)
async def get_shops(request: Request):
    """Get list of shops for current user."""
    user_id = get_user_id(request)
    
    query = """
        SELECT shop_id::text, shop_name
        FROM app.dim_shop
        WHERE user_id = %(user_id)s
        ORDER BY shop_name
    """
    
    rows = execute_all(query, {"user_id": user_id})
    
    shops = [Shop(shop_id=row["shop_id"], shop_name=row["shop_name"]) for row in rows]
    
    return ShopsResponse(shops=shops)
