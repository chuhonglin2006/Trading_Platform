"""管理员管理商品接口"""
from typing import Any

from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Query

from admin.curd_a.admins import get_admin_info
from admin.curd_a.products import (
    change_product_status,
    get_all_products,
    review_product,
)
from admin.shemas_a.products import ProductReviewRequest, ProductStatusRequest

admin_product = APIRouter()


"""获取所有商品接口"""
@admin_product.get("/api/admin/products")
async def get_admin_product_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    review_status: str | None = None,
    current_admin: dict = Depends(get_admin_info)) -> dict[str, Any]:

    result = await get_all_products(
        page=page,
        page_size=page_size,
        keyword=keyword,
        review_status=review_status
    )
    return result

"""审核商品接口"""
@admin_product.patch("/api/admin/products/{product_id}/review")
async def admin_review_product(
    product_id: int,
    data: ProductReviewRequest,
    admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)) -> dict[str,Any]:
    admin_id = admin.get("admin_id")
    if admin_id is None:
        return {
            "code": 401,
            "message": "管理员身份信息无效",
            "data": None
        }
    result = await review_product(
        redis=redis,
        product_id=product_id,
        review_status=data.review_status,
        admin_id=admin_id,
        reason=data.reason
    )
    return result

"""强制下架商品接口"""
@admin_product.patch("/api/admin/products/{product_id}/status")
async def admin_change_product_status(
    product_id: int,
    data: ProductStatusRequest,
    admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)) -> dict[str,Any]:
    result = await change_product_status(
        redis=redis,
        product_id=product_id,
        status=data.status,
        reason=data.reason,
        admin_id=admin.get("admin_id")
    )
    return result

