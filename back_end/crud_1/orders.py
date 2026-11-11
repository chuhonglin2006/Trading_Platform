"""订单接口函数"""
import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Any

from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.order import Order
from modles_1.products import Product
from modles_1.user import User
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from tools_1.create_order_no import create_order_number
from tools_1.logger import get_logger
from tools_1.product_state import status_after_order_cancelled

from crud_1.produces import invalidate_product

logger = get_logger(__name__, "python")
mysql_logger = get_logger(__name__, "mysql")


async def create_order(redis,user_id:int,product_id:int) -> dict[str,Any]:
    """
    创建订单
    :param redis: Redis
    :param user_id:买家id
    :param product_id:商品id
    :return:订单信息
    """
    async with async_session_maker() as session:
        async with session.begin():
            stmt = (
                select(Product)
                .where(Product.id == product_id)
                .with_for_update())
            product = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品不存在")
            if product.seller_id == user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能购买自己的商品")
            if product.status != "on_sale":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="商品当前不可购买")
            if product.review_status != "approved":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="商品尚未通过审核")
            stmt = select(Order).where(
                Order.product_id == product_id,
                Order.status.in_(["pending", "received", "completed"]))
            existing_order = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if existing_order is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该商品已经被下单")
            seller = await session.scalar(
                select(User).where(
                    User.id == product.seller_id))
            if seller is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="卖家不存在")
            create_time = datetime.datetime.now()

            order = Order(
                order_no=create_order_number(),
                product_id=product.id,
                buyer_id=user_id,
                seller_id=product.seller_id,
                price=product.price,
                status="pending",
                meeting_location=None,
                meeting_time=None,
                created_at=create_time,
                auto_receive_at=create_time + timedelta(days=7)
            )
            seller_id = product.seller_id

            product.status = "off_sale"
            session.add(order)
            await session.flush()
            await session.refresh(order)
            order_data = {
                "id": order.id,
                "order_no": order.order_no,
                "buyer_id": order.buyer_id,
                "seller_id": order.seller_id,
                "product_id": order.product_id,
                "price": order.price,
                "status": order.status,
                "meeting_location": order.meeting_location,
                "meeting_time": order.meeting_time,
                "created_at": order.created_at,
                "completed_at": order.completed_at,
                "cancelled_at": order.cancelled_at
            }
            notification = {
                "email": seller.email,
                "seller_username": seller.username,
                "product_name": product.name,
                "order_no": order.order_no,
                "price": str(order.price),
                "created_at": order.created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }
        order_data["notification"] = notification
        await invalidate_product(redis, product_id, seller_id)
        logger.info(
            "订单创建成功 order_id=%s order_no=%s buyer_id=%s seller_id=%s product_id=%s",
            order_data["id"],
            order_data["order_no"],
            order_data["buyer_id"],
            order_data["seller_id"],
            order_data["product_id"]
        )
        return order_data

async def get_my_orders(user_id:int) -> dict[str,Any]:
    """
    获取用户订单
    :param user_id:用户id
    :return:用户订单
    """
    async with async_session_maker() as session:
        stmt= select(Order).where(
            Order.buyer_id == user_id
        ).options(
            selectinload(Order.product),
            selectinload(Order.seller)
        ).order_by(Order.created_at.desc())
        user_orders_class = await session.execute(stmt)
        user_orders = user_orders_class.scalars().all()
        user_order_list = []
        for user_order in user_orders:
            product = user_order.product
            seller = user_order.seller
            user_order_list.append({
                "id": user_order.id,
                "order_no": user_order.order_no,
                "buyer_id": user_order.buyer_id,
                "seller_id": user_order.seller_id,
                "product_id": user_order.product_id,
                "product_name": product.name if product else "",
                "name": product.name if product else "",
                "seller_name": seller.username if seller else "用户",
                "price": user_order.price,
                "status": user_order.status,
                "meeting_location": user_order.meeting_location,
                "meeting_time": user_order.meeting_time,
                "created_at": user_order.created_at,
                "completed_at": user_order.completed_at,
                "cancelled_at": user_order.cancelled_at,
            })
        return {
            "code": 200,
            "message": "获取成功",
            "data": user_order_list
        }

async def get_order_info(user_id:int,order_id:int) -> dict[str,Any]:
    """
    获取订单详细信息
    :param user_id:用户id
    :param order_id:订单id
    :return:订单详细信息
    """
    async with async_session_maker() as session:
        stmt = (
            select(Order)
            .where(
                Order.id == order_id,
                or_(
                    Order.buyer_id == user_id,
                    Order.seller_id == user_id
                )
            )
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在或无权查看"
            )
        confirmed = (
                order.buyer_meeting_confirmed
                and order.seller_meeting_confirmed
        )
        return {
            "code": 200,
            "message": "获取成功",
            "data": {
                "id": order.id,
                "order_no": order.order_no,
                "buyer_id": order.buyer_id,
                "seller_id": order.seller_id,
                "product_id": order.product_id,
                "price": order.price,
                "status": order.status,
                "meeting_location": order.meeting_location,
                "meeting_time": order.meeting_time,
                "buyer_meeting_confirmed": (
                    order.buyer_meeting_confirmed
                ),
                "seller_meeting_confirmed": (
                    order.seller_meeting_confirmed
                ),
                "confirmed": confirmed,
                "created_at": order.created_at,
                "completed_at": order.completed_at,
                "cancelled_at": order.cancelled_at,
                "received_at": order.received_at,
                "auto_receive_at": order.auto_receive_at,
            }
        }

async def get_my_sales(user_id: int) -> dict[str, Any]:
    """
    获取我出售的订单
    :param user_id:用户id
    :return:出售的订单
    """
    async with async_session_maker() as session:
        stmt = (
            select(Order)
            .where(Order.seller_id == user_id)
            .options(
                selectinload(Order.buyer),
                selectinload(Order.product)
            ).order_by(Order.created_at.desc()))
        result = await session.execute(stmt)
        orders = result.scalars().all()
        order_list = []
        for order in orders:
            order_list.append({
                "id": order.id,
                "order_no": order.order_no,
                "buyer_id": order.buyer_id,
                "buyer_name": order.buyer.username if order.buyer else "用户",
                "seller_id": order.seller_id,
                "product_id": order.product_id,
                "product_name": order.product.name if order.product else "",
                "price": order.price,
                "status": order.status,
                "meeting_location": order.meeting_location,
                "meeting_time": order.meeting_time,
                "created_at": order.created_at,
                "completed_at": order.completed_at,
                "cancelled_at": order.cancelled_at,
            })
        return {
            "code": 200,
            "message": "获取成功",
            "data": order_list
        }

async def cancel_order(redis,user_id:int,order_id:int) -> dict[str,Any]:
    """
    卖家和买家取消订单
    :param redis: Redis
    :param order_id:订单id
    :param user_id:买家id
    :return:取消信息
    """
    async with async_session_maker() as session:
        async with session.begin():
            stmt = (
                select(Order)
                .where(Order.id == order_id)
                .with_for_update())
            result = await session.execute(stmt)
            order = result.scalar_one_or_none()
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="订单不存在")
            if user_id == order.buyer_id:
                cancel_role = "buyer"
                receiver_id = order.seller_id
            elif user_id == order.seller_id:
                cancel_role = "seller"
                receiver_id = order.buyer_id
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权取消该订单")
            if order.status != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="只有待完成的订单可以取消")
            product = await session.scalar(
                select(Product)
                .where(Product.id == order.product_id)
                .with_for_update())
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品不存在")
            receiver = await session.scalar(
                select(User).where(
                    User.id == receiver_id))
            if receiver is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="通知接收人不存在"
                )
            cancel_time = datetime.datetime.now()
            order.status = "cancelled"
            order.cancelled_at = cancel_time
            # 被驳回 / 强制下架的商品不能因为取消订单而重新上架
            product.status = status_after_order_cancelled(product.review_status)
            cancel_product_id = product.id
            cancel_seller_id = product.seller_id
            notification = {
                "email": receiver.email,
                "username": receiver.username,
                "order_no": order.order_no,
                "product_name": product.name,
                "cancel_role": cancel_role,
                "cancel_time": cancel_time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }
        await invalidate_product(redis, cancel_product_id, cancel_seller_id)
        logger.info(
            "订单取消成功 order_id=%s user_id=%s role=%s",
            order_id,
            user_id,
            cancel_role
        )
        return {
            "code": 200,
            "message": "订单取消成功",
            "data": {
                "order_id": order_id,
                "product_id": order.product_id,
                "status": "cancelled"
            },
            "notification": notification
        }

async def buyer_confirmation(user_id:int,order_id:int) -> dict[str,Any]:
    """
    买家确认收货
    :param user_id:用户id
    :param order_id:订单id
    :return:订单信息
    """
    async with async_session_maker() as session:
        async with session.begin():
            stmt = select(Order).where(
                Order.buyer_id == user_id,
                Order.id == order_id
            ).with_for_update()
            order_class = await session.execute(stmt)
            order = order_class.scalar_one_or_none()
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="订单不存在"
                )
            if order.status != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="当前订单无法确认收货"
                )
            receive_time = datetime.datetime.now()
            order.status = "received"
            order.received_at = receive_time
            response = {
                "code": 200,
                "message": "确认收货成功",
                "data": {
                    "order_id": order.id,
                    "order_no": order.order_no,
                    "status": order.status,
                    "received_at": order.received_at
                }
            }
        logger.info(
            "买家确认收货 order_id=%s buyer_id=%s",
            order_id,
            user_id
        )
        return response

async def seller_confirmed(redis,user_id:int,order_id:int) -> dict[str,Any]:
    """
    卖家确认完成
    :param redis: Redis
    :param user_id:用户id
    :param order_id:订单id
    :return:订单信息
    """
    async with async_session_maker() as session:
        async with session.begin():
            stmt = select(Order).where(
                Order.seller_id == user_id,
                Order.id == order_id
            ).with_for_update()
            order_class = await session.execute(stmt)
            order = order_class.scalar_one_or_none()
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="订单不存在"
                )
            if order.status != "received":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="当前订单无法确认完成"
                )
            stmt = select(Product).where(
                Product.id == order.product_id
            ).with_for_update()
            product_class = await session.execute(stmt)
            product = product_class.scalar_one_or_none()
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="商品不存在")
            complete_time = datetime.datetime.now()
            order.status = "completed"
            order.completed_at = complete_time
            product.status = "sold"
            sold_product_id = product.id
            sold_seller_id = product.seller_id
        await invalidate_product(redis, sold_product_id, sold_seller_id)
        logger.info(
            "卖家确认订单完成 order_id=%s seller_id=%s product_id=%s",
            order.id,
            user_id,
            sold_product_id
        )
        return {
            "code": 200,
            "message": "交易完成",
            "data": {
                "order_id": order.id,
                "order_no": order.order_no,
                "product_id": order.product_id,
                "status": order.status,
                "completed_at": order.completed_at
            }
        }

async def auto_receive_orders() -> dict[str,Any]:
    """
    订单自动收货
    :return:订单信息
    """
    receive_time = datetime.datetime.now()
    async with async_session_maker() as session:
        async with session.begin():
            stmt = (
                select(Order)
                .where(
                    Order.status == "pending",
                    Order.auto_receive_at.is_not(None),
                    Order.auto_receive_at <= receive_time
                ).limit(200).with_for_update())
            result = await session.execute(stmt)
            orders = result.scalars().all()
            count = 0
            for order in orders:
                order.status = "received"
                order.received_at = receive_time
                count += 1
        if count:
            mysql_logger.info("自动确认收货写入MySQL count=%s", count)
        return {
            "code": 200,
            "message": "自动确认收货完成",
            "data": {
                "count": count
            }
        }

async def auto_complete_orders(redis) -> dict[str, Any]:
    """
    订单自动完成：已收货、但卖家长时间没有确认完成的订单，由系统自动完成。
    否则订单会一直停在「已收货」，商品永远是下架状态，也删除不了。
    处理顺序和 seller_confirmed 一致：先锁订单，再锁商品，避免死锁。
    """
    now = datetime.datetime.now()
    cutoff = now - timedelta(days=3)
    sold: list[tuple[int, int]] = []

    async with async_session_maker() as session, session.begin():
        stmt = (
            select(Order)
            .where(
                Order.status == "received",
                Order.received_at.is_not(None),
                Order.received_at <= cutoff
            ).limit(200).with_for_update())   # 一次最多处理 200 个，剩下的下一轮处理
        result = await session.execute(stmt)
        orders = result.scalars().all()

        for order in orders:
            product_result = await session.execute(
                select(Product).where(
                    Product.id == order.product_id
                ).with_for_update()
            )
            product = product_result.scalar_one_or_none()

            order.status = "completed"
            order.completed_at = now

            if product is not None:
                product.status = "sold"
                sold.append((product.id, product.seller_id))

    # 事务提交之后再清缓存；单个商品清缓存失败不影响其他商品
    for product_id, seller_id in sold:
        try:
            await invalidate_product(redis, product_id, seller_id)
        except Exception:
            logger.exception("订单自动完成后清理商品缓存失败 product_id=%s", product_id)

    if orders:
        mysql_logger.info("订单自动完成写入MySQL count=%s", len(orders))

    return {
        "code": 200,
        "message": "订单自动完成处理结束",
        "data": {
            "count": len(orders)
        }
    }

async def sale_statistics(user_id:int) -> dict[str,Any]:
    """
    统计用户销售
    :param user_id:用户id
    :return:销售总量
    """
    async with async_session_maker() as session:
        stmt = (
            select(
                Order.status,
                func.count(Order.id),
                func.coalesce(func.sum(Order.price), 0)
            )
            .where(Order.seller_id == user_id)
            .group_by(Order.status)
        )
        result = await session.execute(stmt)
        rows = result.all()
        statistics = {
            "total_orders": 0,
            "pending_orders": 0,
            "received_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "total_amount": Decimal("0.00")
        }
        for order_status, count, amount in rows:
            statistics["total_orders"] += count
            if order_status == "pending":
                statistics["pending_orders"] = count
            elif order_status == "received":
                statistics["received_orders"] = count
            elif order_status == "completed":
                statistics["completed_orders"] = count
                statistics["total_amount"] += amount
            elif order_status == "cancelled":
                statistics["cancelled_orders"] = count

        return {
            "code": 200,
            "message": "获取销售统计成功",
            "data": statistics
        }

async def set_meting(user_id:int,order_id:int,meeting_time:datetime.datetime,meeting_location:str) -> dict[str,Any]:
    """
    设置交易时间,地点
    距离已确定的交易时间不足1小时时，时间和地点都不能再修改
    """
    meeting_location = meeting_location.strip()
    if not meeting_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="交易地点不能为空"
        )
    if len(meeting_location) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="交易地点过长"
        )
    now = datetime.datetime.now()
    if meeting_time < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="交易时间必须晚于当前时间"
        )
    async with async_session_maker() as session:
        # 加行锁：买卖双方同时修改时串行处理
        stmt = select(Order).where(
            Order.id == order_id
        ).with_for_update()
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        if user_id not in (order.buyer_id, order.seller_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此订单"
            )
        if order.status in ("completed", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前订单不能设置交易安排"
            )

        if order.meeting_time is not None:
            # 内容没变化：直接返回，不重置双方的确认状态
            if (order.meeting_time == meeting_time
                    and order.meeting_location == meeting_location):
                return {
                    "code": 200,
                    "message": "交易安排未变化",
                    "data": {
                        "order_id": order.id,
                        "meeting_time": order.meeting_time,
                        "meeting_location": order.meeting_location,
                        "buyer_meeting_confirmed": order.buyer_meeting_confirmed,
                        "seller_meeting_confirmed": order.seller_meeting_confirmed,
                        "confirmed": bool(
                            order.buyer_meeting_confirmed
                            and order.seller_meeting_confirmed
                        )
                    }
                }
            # 距离交易不足1小时：时间和地点都禁止修改
            if order.meeting_time <= now + datetime.timedelta(hours=1):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="距离交易时间不足1小时，不能修改交易时间或地点"
                )

        old_time, old_location = order.meeting_time, order.meeting_location
        order.meeting_time = meeting_time
        order.meeting_location = meeting_location
        order.buyer_meeting_confirmed = False
        order.seller_meeting_confirmed = False
        await session.commit()
        await session.refresh(order)
        logger.info(
            "交易安排设置成功 order_id=%s user_id=%s old_time=%s new_time=%s old_location=%s new_location=%s",
            order.id, user_id, old_time, order.meeting_time,
            old_location, order.meeting_location
        )
        return {
            "code": 200,
            "message": "交易安排设置成功",
            "data": {
                "order_id": order.id,
                "meeting_time": order.meeting_time,
                "meeting_location": order.meeting_location,
                "buyer_meeting_confirmed": order.buyer_meeting_confirmed,
                "seller_meeting_confirmed": order.seller_meeting_confirmed,
                "confirmed": False
            }
        }

async def confirm_meting(user_id:int,order_id:int) -> dict[str,Any]:
    """
    确认交易时间,地点
    :param user_id:用户id
    :param order_id:订单id
    :return:
    """
    async with async_session_maker() as session:
        stmt = select(Order).where(
            Order.id == order_id
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        if user_id not in (
            order.buyer_id,order.seller_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无权操作此订单"
            )
        if order.status in (
            "completed",
            "cancelled"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前订单状态不能确认交易安排"
            )
        if (order.meeting_time is None
            or not order.meeting_location
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先设置交易时间和地点"
            )
        if order.meeting_time <= datetime.datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="交易时间已过期，请重新设置"
            )
        if user_id == order.buyer_id:
            if order.buyer_meeting_confirmed:
                return {
                    "code": 200,
                    "message": "你已经确认过交易安排",
                    "data": {
                        "order_id": order.id,
                        "buyer_meeting_confirmed": (
                            order.buyer_meeting_confirmed
                        ),
                        "seller_meeting_confirmed": (
                            order.seller_meeting_confirmed
                        ),
                        "confirmed": (
                                order.buyer_meeting_confirmed
                                and order.seller_meeting_confirmed
                        )
                    }
                }
            order.buyer_meeting_confirmed = True
        else:
            if order.seller_meeting_confirmed:
                return {
                    "code": 200,
                    "message": "你已经确认过交易安排",
                    "data": {
                        "order_id": order.id,
                        "buyer_meeting_confirmed": (
                            order.buyer_meeting_confirmed
                        ),
                        "seller_meeting_confirmed": (
                            order.seller_meeting_confirmed
                        ),
                        "confirmed": (
                            order.buyer_meeting_confirmed
                            and order.seller_meeting_confirmed
                        )
                    }
                }

            order.seller_meeting_confirmed = True
        await session.commit()
        await session.refresh(order)
        confirmed = (
            order.buyer_meeting_confirmed
            and order.seller_meeting_confirmed
        )
        logger.info(
            "交易安排确认成功 order_id=%s user_id=%s confirmed=%s",
            order.id,
            user_id,
            confirmed
        )
        return {
            "code": 200,
            "message": (
                "双方已确认交易安排"
                if confirmed
                else "交易安排确认成功，等待对方确认"
            ),
            "data": {
                "order_id": order.id,
                "meeting_time": order.meeting_time,
                "meeting_location": order.meeting_location,
                "buyer_meeting_confirmed": (
                    order.buyer_meeting_confirmed
                ),
                "seller_meeting_confirmed": (
                    order.seller_meeting_confirmed
                ),
                "confirmed": confirmed
            }
        }

async def get_meting(user_id:int,order_id:int) -> dict[str,Any]:
    """
    获取交易时间,地点
    :param user_id:用户id
    :param order_id:订单id
    :return:
    """
    async with async_session_maker() as session:
        stmt = (
            select(Order)
            .where(
                Order.id == order_id,
                or_(
                    Order.buyer_id == user_id,
                    Order.seller_id == user_id
                )
            )
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="订单不存在"
            )
        if user_id not in (
            order.buyer_id,order.seller_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无权访问"
            )
        confirmed = (
            order.buyer_meeting_confirmed
            and order.seller_meeting_confirmed
        )
        return {
            "code": 200,
            "message": "获取交易安排成功",
            "data": {
                "order_id": order.id,
                "meeting_time": order.meeting_time,
                "meeting_location": order.meeting_location,
                "buyer_meeting_confirmed": (
                    order.buyer_meeting_confirmed
                ),
                "seller_meeting_confirmed": (
                    order.seller_meeting_confirmed
                ),
                "confirmed": confirmed
            }
        }






























































