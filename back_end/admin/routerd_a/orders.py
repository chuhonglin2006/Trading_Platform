"""管理界面订单接口"""
from admin.curd_a.orders import all_orders,get_order_info
from fastapi import APIRouter,Query,Depends
from admin.curd_a.admins import get_admin_info
from typing import Any

admin_order = APIRouter()


"""获取所有订单接口"""
@admin_order.get("/api/admin/orders")
async def admin_get_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    order_status: str | None = None,
    admin: dict = Depends(get_admin_info)) -> dict[str,Any]:
    result = await all_orders(
        page=page,
        page_size=page_size,
        order_status=order_status
    )
    return result

"""获取订单详情接口"""
@admin_order.get("/api/admin/orders/{order_id}")
async def admin_get_order_detail(
    order_id: int,
    admin: dict = Depends(get_admin_info)
):
    result = await get_order_info(order_id)
    return result