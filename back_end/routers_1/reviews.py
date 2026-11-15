"""评价接口"""
from typing import Any

from crud_1.reviews import create_review, get_order_review, list_seller_reviews
from crud_1.users import get_user_info
from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Query
from schemas_1.reviews import ReviewRequest
from tools_1.limit import ip_rate_limit

review = APIRouter()


"""买家评价卖家接口"""
@review.post("/api/orders/{order_id}/review")
async def create_order_review(
    order_id: int,
    data: ReviewRequest,
    current_user=Depends(get_user_info),
    redis=Depends(get_redis)
) -> dict[str, Any]:
    return await create_review(
        redis=redis,
        user_id=current_user["id"],
        order_id=order_id,
        rating=data.rating,
        comment=data.comment
    )


"""获取订单评价接口"""
@review.get("/api/orders/{order_id}/review")
async def get_review_of_order(
    order_id: int,
    current_user=Depends(get_user_info)
) -> dict[str, Any]:
    return await get_order_review(
        user_id=current_user["id"],
        order_id=order_id
    )


"""获取卖家收到的评价接口"""
@review.get(
    "/api/users/{user_id}/reviews",
    dependencies=[Depends(ip_rate_limit("seller_reviews", 60, 60))]
)
async def get_seller_reviews(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50)
) -> dict[str, Any]:
    return await list_seller_reviews(
        seller_id=user_id,
        page=page,
        page_size=page_size
    )
