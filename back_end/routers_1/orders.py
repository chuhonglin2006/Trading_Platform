"""订单接口"""
from typing import Any

from crud_1.orders import (
    buyer_confirmation,
    cancel_order,
    confirm_meting,
    create_order,
    get_meting,
    get_my_orders,
    get_my_sales,
    get_order_info,
    sale_statistics,
    seller_confirmed,
    set_meting,
)
from crud_1.users import get_user_info
from database_1.redis_config import get_redis
from fastapi import APIRouter, BackgroundTasks, Body, Depends
from schemas_1.orders import MeetingRequest
from tools_1.email import send_cancel_notification, send_new_order_notification

order = APIRouter()


"""创建订单接口"""
@order.post("/api/orders")
async def create_my_order(background_tasks: BackgroundTasks,product_id:int = Body(embed=True),current_user=Depends(get_user_info),
                        redis = Depends(get_redis)) -> dict[str,Any]:
    result = await create_order(
        redis=redis,
        user_id=current_user["id"],
        product_id=product_id)
    notification = result.pop("notification", None)
    if notification and notification.get("email"):
        background_tasks.add_task(
            send_new_order_notification,
            notification["email"],
            notification)
    return result

"""获取我的订单接口"""
@order.get("/api/orders/my")
async def get_orders(current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_my_orders(current_user["id"])
    return result

"""获取订单详情接口"""
@order.get("/api/orders/{order_id}")
async def get_my_order_info(order_id:int,current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_order_info(
        user_id=current_user["id"],
        order_id=order_id
    )
    return result

"""获取出售的订单接口"""
@order.get("/api/sales/my")
async def get_my_sales_api(current_user=Depends(get_user_info)) -> dict[str,Any]:
    result = await get_my_sales(
        user_id=current_user["id"])
    return result

"""取消订单接口"""
@order.patch("/api/orders/{order_id}/cancel")
async def cancel_my_order(order_id:int,background_tasks:BackgroundTasks,current_useer = Depends(get_user_info),
                        redis = Depends(get_redis)) -> dict[str,Any]:
    result = await cancel_order(
        redis=redis,
        user_id=current_useer["id"],
        order_id=order_id)
    notification = result.pop(
        "notification",None)
    if notification and notification.get("email"):
        background_tasks.add_task(
            send_cancel_notification,
            notification["email"],
            notification)
    return result

"""买家确认收货接口"""
@order.patch("/api/orders/{order_id}/receive")
async def buyer_receive(order_id:int,current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await buyer_confirmation(
        user_id=current_user["id"],
        order_id=order_id
    )
    return result

"""卖家确认完成接口"""
@order.patch("/api/orders/{order_id}/complete")
async def seller_confirmed_api(order_id:int,user_info:dict = Depends(get_user_info),redis = Depends(get_redis)) -> dict[str,Any]:
    result = await seller_confirmed(
        redis=redis,
        user_id=user_info["id"],
        order_id=order_id
    )
    return result

"""统计销售接口"""
@order.get("/api/sales-statistics")
async def sales_statistics_api(user_info: dict = Depends(get_user_info)) -> dict[str,Any]:
    result = await sale_statistics(
        user_id=user_info["id"]
    )
    return result

"""设置交易地点,时间接口"""
@order.put("/api/orders/{order_id}/meeting")
async def set_order(
    order_id: int,
    data:MeetingRequest,
    current_user=Depends(get_user_info)) -> dict[str,Any]:
    result = await set_meting(
        user_id=current_user["id"],
        order_id=order_id,
        meeting_time=data.meeting_time,
        meeting_location=data.meeting_location,
    )
    return result

"""确认交易时间,地点"""
@order.post("/api/orders/{order_id}/meeting/confirm")
async def confirm_order_meeting(order_id:int,current_user=Depends(get_user_info)) -> dict[str,Any]:
    result = await confirm_meting(
        user_id=current_user["id"],
        order_id=order_id
    )
    return result

"""获取交易信息"""
@order.get("/api/orders/{order_id}/meeting")
async def get_order_meeting(order_id:int,current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await get_meting(
        user_id=current_user["id"],
        order_id=order_id
    )
    return result



























