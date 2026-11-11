"""管理员公告接口"""

from typing import Any

from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Query

from admin.curd_a.admins import get_admin_info
from admin.curd_a.announcements import (
    create_announcement,
    delete_announcement,
    get_all_announcements,
    get_announcement_info,
    update_announcement,
)
from admin.shemas_a.announcements import (
    AnnouncementCreateRequest,
    AnnouncementUpdateRequest,
)

admin_announcement = APIRouter()


@admin_announcement.get("/api/admin/announcements")
async def admin_get_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = "",
    admin: dict = Depends(get_admin_info)
) -> dict[str, Any]:
    return await get_all_announcements(
        page=page,
        page_size=page_size,
        keyword=keyword
    )


@admin_announcement.get("/api/admin/announcements/{announcement_id}")
async def admin_get_announcement(
    announcement_id: int,
    admin: dict = Depends(get_admin_info)
) -> dict[str, Any]:
    return await get_announcement_info(announcement_id)


@admin_announcement.post("/api/admin/announcements")
async def admin_create_announcement(
    data: AnnouncementCreateRequest,
    admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)
) -> dict[str, Any]:
    return await create_announcement(
        redis=redis,
        title=data.title,
        content=data.content
    )


@admin_announcement.patch("/api/admin/announcements/{announcement_id}")
async def admin_update_announcement(
    announcement_id: int,
    data: AnnouncementUpdateRequest,
    admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)
) -> dict[str, Any]:
    return await update_announcement(
        redis=redis,
        announcement_id=announcement_id,
        title=data.title,
        content=data.content
    )


@admin_announcement.delete("/api/admin/announcements/{announcement_id}")
async def admin_delete_announcement(
    announcement_id: int,
    admin: dict = Depends(get_admin_info),
    redis = Depends(get_redis)
) -> dict[str, Any]:
    return await delete_announcement(redis=redis,announcement_id=announcement_id)
