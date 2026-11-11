"""管理员订单函数"""
from typing import Any

from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.order import Order
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


async def all_orders(page:int = 1,page_size:int = 20,order_status: str | None = None) -> dict[str,Any]:
    """
    获取所有订单
    :return:
    """
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分页参数不合法"
        )
    allowed_statues = {
        "pending",
        "received",
        "completed",
        "cancelled"
    }
    if order_status is not None:
        if order_status not in allowed_statues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="订单状态不合法"
            )
    async with async_session_maker() as session:
        conditions = []
        if order_status is not None:
            conditions.append(
                Order.status == order_status
            )
        count_stmt = select(
            func.count(Order.id)
        ).where(*conditions)
        total = (await session.execute(count_stmt)).scalar_one()
        stmt = select(Order).options(
            selectinload(Order.buyer),
            selectinload(Order.seller),
            selectinload(Order.product)
        ).where(*conditions).order_by(
            Order.created_at.desc(), Order.id.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(stmt)
        orders = result.scalars().all()
        def format_datetime(value):
            return value.isoformat() if value else None
        order_list = []
        for order in orders:
            order_list.append({
                "id": order.id,
                "order_no": order.order_no,
                "price": float(order.price),
                "status": order.status,
                "buyer": {
                    "id": order.buyer.id,
                    "username": order.buyer.username
                } if order.buyer else None,
                "seller": {
                    "id": order.seller.id,
                    "username": order.seller.username
                } if order.seller else None,
                "product": {
                    "id": order.product.id,
                    "name": order.product.name
                } if order.product else None,
                "meeting_location": order.meeting_location,
                "meeting_time": format_datetime(
                    order.meeting_time
                ),
                "buyer_meeting_confirmed":
                    order.buyer_meeting_confirmed,
                "seller_meeting_confirmed":
                    order.seller_meeting_confirmed,
                "created_at": format_datetime(
                    order.created_at
                ),
                "received_at": format_datetime(
                    order.received_at
                ),
                "completed_at": format_datetime(
                    order.completed_at
                ),
                "cancelled_at": format_datetime(
                    order.cancelled_at
                ),
                "auto_receive_at": format_datetime(
                    order.auto_receive_at
                )
            })
        return {
            "code": 200,
            "message": "获取订单列表成功",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "orders": order_list
            }
        }

async def get_order_info(order_id:int) -> dict[str,Any]:
    """
    获取订单详情
    :param order_id:订单id
    :return:
    """
    async with async_session_maker() as session:
        stmt = select(Order).options(
            selectinload(Order.buyer),
            selectinload(Order.seller),
            selectinload(Order.product)
        ).where(Order.id == order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        def format_time(value):
            return value.isoformat() if value else None
        return {
            "code": 200,
            "message": "获取订单详情成功",
            "data": {
                "id": order.id,
                "order_no": order.order_no,
                "price": float(order.price),
                "status": order.status,
                "buyer": {
                    "id": order.buyer.id,
                    "username": order.buyer.username,
                    "email": order.buyer.email
                } if order.buyer else None,
                "seller": {
                    "id": order.seller.id,
                    "username": order.seller.username,
                    "email": order.seller.email
                } if order.seller else None,
                "product": {
                    "id": order.product.id,
                    "name": order.product.name,
                    "status": order.product.status
                } if order.product else None,
                "meeting_location": order.meeting_location,
                "meeting_time": format_time(order.meeting_time),
                "buyer_meeting_confirmed":
                    order.buyer_meeting_confirmed,
                "seller_meeting_confirmed":
                    order.seller_meeting_confirmed,
                "created_at": format_time(order.created_at),
                "received_at": format_time(order.received_at),
                "completed_at": format_time(order.completed_at),
                "cancelled_at": format_time(order.cancelled_at),
                "auto_receive_at": format_time(order.auto_receive_at)
            }
        }