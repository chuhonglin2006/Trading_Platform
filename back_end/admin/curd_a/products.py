"""管理员界面管理商品函数"""

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from zoneinfo import ZoneInfo
from modles_1.products import Product
from typing import Any
from database_1.mysql_config import async_session_maker
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from crud_1.produces import invalidate_product
from tools_1.uload_image_to_server import normalize_image_url
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")


async def get_all_products(page: int = 1,page_size: int = 20,keyword: str = "",review_status: str | None = None
) -> dict[str, Any]:
    """
    获取所有商品
    """

    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分页参数不合法"
        )

    conditions = []

    keyword = keyword.strip()

    if keyword:
        conditions.append(
            Product.name.like(f"%{keyword}%")
        )

    if review_status:
        if review_status not in (
            "pending",
            "approved",
            "rejected"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="审核状态不合法"
            )

        conditions.append(
            Product.review_status == review_status
        )

    async with async_session_maker() as session:

        count_stmt = (
            select(func.count(Product.id))
            .where(*conditions)
        )

        total = (
            await session.execute(count_stmt)
        ).scalar_one()

        stmt = (
            select(Product)
            .where(*conditions)
            .options(
                selectinload(Product.seller),
                selectinload(Product.category),
                selectinload(Product.images)
            )
            .order_by(
                Product.created_at.desc(),
                Product.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await session.execute(stmt)

        products = result.scalars().all()

        product_list = []

        for product in products:

            product_list.append({
                "id": product.id,

                "name": product.name,

                "price": float(product.price),

                "description": product.description,

                "campus": product.campus,

                "status": product.status,

                "review_status": product.review_status,

                # 图片统一转换成前端通过 Nginx 访问的地址
                "images": [
                    {
                        "id": image.id,
                        "url": normalize_image_url(image.image_url)
                    }
                    for image in product.images
                ],

                "original_price": (
                    float(product.original_price)
                    if product.original_price is not None
                    else None
                ),

                "category": {
                    "id": product.category.id,
                    "name": product.category.name
                } if product.category else None,

                "seller": {
                    "id": product.seller.id,
                    "username": product.seller.username
                } if product.seller else None,

                "created_at": (
                    product.created_at.isoformat()
                    if product.created_at
                    else None
                )
            })

        return {
            "code": 200,
            "message": "获取商品列表成功",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "products": product_list
            }
        }


async def review_product(redis,product_id: int,review_status: str,admin_id: int,
reason: str | None = None) -> dict[str, Any]:
    """
    管理员审核商品。

    review_status:
        approved: 审核通过
        rejected: 审核拒绝
    """

    if review_status not in ("approved", "rejected"):
        return {
            "code": 400,
            "message": "审核状态不合法",
            "data": None
        }

    reason = (reason or "").strip()

    if review_status == "rejected" and not reason:
        return {
            "code": 400,
            "message": "拒绝商品时必须填写原因",
            "data": None
        }

    if len(reason) > 500:
        return {
            "code": 400,
            "message": "拒绝原因不能超过500个字符",
            "data": None
        }

    async with async_session_maker() as session:

        try:

            stmt = (
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
            )

            product = (
                await session.execute(stmt)
            ).scalar_one_or_none()

            if product is None:
                return {
                    "code": 404,
                    "message": "商品不存在",
                    "data": None
                }

            if product.review_status != "pending":
                return {
                    "code": 400,
                    "message": "该商品已经审核，不能重复审核",
                    "data": None
                }

            if product.status == "sold":
                return {
                    "code": 400,
                    "message": "已售出的商品不能重新审核",
                    "data": None
                }

            product.review_status = review_status

            product.review_reason = (
                reason if review_status == "rejected" else None
            )

            product.reviewed_by = admin_id

            product.reviewed_at = datetime.now(
                ZoneInfo("Asia/Shanghai")
            ).replace(tzinfo=None)

            if review_status == "rejected":
                product.status = "off_sale"

            await session.commit()
            await invalidate_product(redis, product_id, product.seller_id)
            logger.info(
                "商品审核完成 product_id=%s status=%s admin_id=%s",
                product_id,
                review_status,
                admin_id
            )

            return {
                "code": 200,
                "message": (
                    "商品审核通过"
                    if review_status == "approved"
                    else "商品审核已拒绝"
                ),
                "data": {
                    "id": product_id,
                    "review_status": review_status,
                    "review_reason": product.review_reason,
                    "reviewed_by": product.reviewed_by,
                    "reviewed_at": product.reviewed_at,
                    "status": product.status
                }
            }

        except SQLAlchemyError:
            await session.rollback()
            raise


async def change_product_status(redis,product_id: int,status: str) -> dict[str, Any]:
    """
    管理员强制下架商品。
    """

    if status != "off_sale":
        return {
            "code": 400,
            "message": "管理员当前仅支持强制下架操作",
            "data": None
        }

    async with async_session_maker() as session:

        try:

            stmt = (
                select(Product)
                .where(Product.id == product_id)
                .with_for_update()
            )

            product = (
                await session.execute(stmt)
            ).scalar_one_or_none()

            if product is None:
                return {
                    "code": 404,
                    "message": "商品不存在",
                    "data": None
                }

            if product.status == "sold":
                return {
                    "code": 400,
                    "message": "已售出的商品不能强制下架",
                    "data": None
                }

            if product.status == "off_sale":
                return {
                    "code": 400,
                    "message": "该商品已经下架",
                    "data": None
                }

            product.status = "off_sale"

            await session.commit()
            await invalidate_product(redis, product_id, product.seller_id)
            logger.info(
                "管理员强制下架商品 product_id=%s seller_id=%s",
                product_id,
                product.seller_id
            )

            return {
                "code": 200,
                "message": "商品已强制下架",
                "data": {
                    "id": product_id,
                    "status": "off_sale"
                }
            }

        except SQLAlchemyError:
            await session.rollback()
            raise
