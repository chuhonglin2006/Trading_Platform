"""管理员界面用户接口"""
from typing import Any

from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Query

from admin.curd_a.admins import get_admin_info
from admin.curd_a.users import get_all_user, update_user_status
from admin.shemas_a.users import UserStatusRequest

admin_user = APIRouter()


"""获取所有用户接口"""
@admin_user.get("/api/admin/users")
async def get_all_user_list(page: int = Query(1, ge=1),
                        page_size: int = Query(20, ge=1, le=100),
                        keyword: str = "",
                        user_status: str | None = None,
                        current_admin: dict = Depends(get_admin_info)) -> dict[str,Any]:
    result = await get_all_user(
        page=page,
        page_size=page_size,
        keyword=keyword,
        user_status=user_status
    )
    return result

"""修改用户状态接口"""
@admin_user.patch("/api/admin/users/{user_id}/status")
async def change_user_status(
    user_id: int,
    data: UserStatusRequest,
    current_admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)
) -> dict[str,Any]:
    result = await update_user_status(
        redis=redis,
        user_id=user_id,
        new_status=data.status,
    )
    return result