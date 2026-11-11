"""管理员界面数据概览"""
from typing import Any

from database_1.mysql_config import async_session_maker
from modles_1.order import Order
from modles_1.products import Product
from modles_1.reports import Report
from modles_1.user import User
from sqlalchemy import func, select


async def get_all_data() -> dict[str,Any]:
    """
    获取所有数据
    :return:
    """
    async with async_session_maker() as session:
        total_users = await session.scalar(
            select(func.count(User.id))
        )
        on_sale_products = await session.scalar(
            select(func.count(Product.id)).where(
                Product.status == "on_sale",
                Product.review_status == "approved"
            )
        )
        pending_products = await session.scalar(
            select(func.count(Product.id)).where(
                Product.review_status == "pending"
            )
        )
        total_orders = await session.scalar(
            select(func.count(Order.id))
        )
        pending_reports = await session.scalar(
            select(func.count(Report.id)).where(
                Report.status == "pending"
            )
        )
        return {
            "code": 200,
            "message": "获取数据概览成功",
            "data": {
                "total_users": total_users or 0,
                "on_sale_products": on_sale_products or 0,
                "pending_products": pending_products or 0,
                "total_orders": total_orders or 0,
                "pending_reports": pending_reports or 0
            }
        }
