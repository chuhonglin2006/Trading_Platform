"""评价相关函数"""
from decimal import Decimal
from typing import Any

from crud_1.users import invalidate_user
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.order import Order
from modles_1.review import Review
from modles_1.user import User
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from tools_1.logger import get_logger

logger = get_logger(__name__, "python")

# 买家确认收货之后（待完成 / 已完成）就可以评价
REVIEWABLE_STATUS = ("received", "completed")

# 信用分上限
MAX_CREDIT_SCORE = Decimal("120")


def rating_to_credit_change(rating: int) -> Decimal:
    """星级 -> 卖家信用分变化：1~2 星 -1，3 星 0，4~5 星 +0.5"""
    if rating <= 2:
        return Decimal("-1.0")
    if rating == 3:
        return Decimal("0.0")
    return Decimal("0.5")


def review_to_dict(review: Review, reviewer_name: str | None = None) -> dict[str, Any]:
    data = {
        "id": review.id,
        "order_id": review.order_id,
        "buyer_id": review.buyer_id,
        "seller_id": review.seller_id,
        "rating": review.rating,
        "comment": review.comment,
        "credit_change": float(review.credit_change),
        "created_at": review.created_at,
    }
    if reviewer_name is not None:
        data["reviewer_name"] = reviewer_name
    return data


async def create_review(
    redis,
    user_id: int,
    order_id: int,
    rating: int,
    comment: str | None
) -> dict[str, Any]:
    """
    买家评价卖家，并按星级调整卖家信用分
    :param redis: Redis
    :param user_id: 当前用户id（必须是买家）
    :param order_id: 订单id
    :param rating: 1~5 星
    :param comment: 评价留言
    :return: 评价信息
    """
    comment = (comment or "").strip() or None
    change = rating_to_credit_change(rating)

    async with async_session_maker() as session:
        async with session.begin():
            # 先锁订单，再锁卖家，和其他地方加锁顺序一致，避免死锁
            order = (
                await session.execute(
                    select(Order)
                    .where(Order.id == order_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if order is None or user_id not in (order.buyer_id, order.seller_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="订单不存在"
                )
            if order.buyer_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="只有买家可以评价"
                )
            if order.status not in REVIEWABLE_STATUS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="确认收货后才能评价"
                )

            existed = await session.scalar(
                select(Review.id).where(Review.order_id == order_id)
            )
            if existed is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该订单已经评价过了"
                )

            seller = (
                await session.execute(
                    select(User)
                    .where(User.id == order.seller_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if seller is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="卖家不存在"
                )

            old_score = Decimal(seller.credit_score or 0)
            new_score = old_score + change
            if change > 0:
                # 加分不超过上限
                new_score = min(new_score, max(old_score, MAX_CREDIT_SCORE))
            else:
                new_score = max(new_score, Decimal("0"))
            seller.credit_score = new_score

            review = Review(
                order_id=order.id,
                buyer_id=order.buyer_id,
                seller_id=order.seller_id,
                rating=rating,
                comment=comment,
                credit_change=new_score - old_score,
            )
            session.add(review)
            try:
                await session.flush()
            except IntegrityError:
                # 理论上订单行锁已经挡住了并发，这里是最后一道保险（order_id 有唯一约束）
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该订单已经评价过了"
                )
            await session.refresh(review)
            data = review_to_dict(review)
            seller_id = order.seller_id

    # 事务提交之后再清用户缓存（信用分变了）
    await invalidate_user(redis, seller_id)
    logger.info(
        "买家评价卖家 order_id=%s buyer_id=%s seller_id=%s rating=%s credit_change=%s",
        order_id, user_id, seller_id, rating, data["credit_change"]
    )
    return {
        "code": 200,
        "message": "评价成功",
        "data": data
    }


async def get_order_review(user_id: int, order_id: int) -> dict[str, Any]:
    """获取订单的评价（订单的买家、卖家可看），没有评价时 data 为 None"""
    async with async_session_maker() as session:
        order = await session.scalar(
            select(Order).where(Order.id == order_id)
        )
        if order is None or user_id not in (order.buyer_id, order.seller_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在或无权查看"
            )
        review = await session.scalar(
            select(Review).where(Review.order_id == order_id)
        )
        return {
            "code": 200,
            "message": "获取成功",
            "data": review_to_dict(review) if review else None
        }


async def list_seller_reviews(
    seller_id: int,
    page: int = 1,
    page_size: int = 10
) -> dict[str, Any]:
    """卖家收到的评价列表（公开），附带评价数量和平均星级"""
    async with async_session_maker() as session:
        total, average = (
            await session.execute(
                select(func.count(Review.id), func.avg(Review.rating))
                .where(Review.seller_id == seller_id)
            )
        ).one()
        rows = (
            await session.execute(
                select(Review, User.username)
                .join(User, User.id == Review.buyer_id)
                .where(Review.seller_id == seller_id)
                .order_by(Review.created_at.desc(), Review.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "total": total or 0,
                "average": round(float(average), 1) if average is not None else None,
                "page": page,
                "page_size": page_size,
                "items": [review_to_dict(r, name) for r, name in rows],
            }
        }