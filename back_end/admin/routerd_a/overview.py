"""管理员界面数据总预览接口"""
from fastapi import APIRouter,Depends
from admin.curd_a.overview import get_all_data
from admin.curd_a.admins import get_admin_info
from typing import Any

admin_overview = APIRouter()



"""获取所有数据接口"""
@admin_overview.get("/api/admin/overview")
async def admin_overviews(admin = Depends(get_admin_info)) -> dict[str,Any]:
    result = await get_all_data()
    return result