"""管理员界面：服务器状态接口"""
from typing import Any

from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Query
from tools_1.system_monitor import get_system_status

from admin.curd_a.admins import get_supper_admin_info

admin_system = APIRouter()


"""获取服务器状态接口（仅超级管理员，内含服务器与数据库运行细节）"""
@admin_system.get("/api/admin/system")
async def admin_system_status(
    minutes: int = Query(15, ge=1, le=60),
    admin = Depends(get_supper_admin_info),
    redis = Depends(get_redis),
) -> dict[str, Any]:
    data = await get_system_status(redis, minutes)
    return {
        "code": 200,
        "message": "获取服务器状态成功",
        "data": data
    }
