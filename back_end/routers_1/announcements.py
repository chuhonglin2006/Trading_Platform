"""公告接口"""
from typing import Any

from crud_1.announcements import get_announcements
from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends
from tools_1.limit import ip_rate_limit

announcements = APIRouter()


"""获取公告接口"""
@announcements.get("/api/announcements",dependencies=[Depends(ip_rate_limit("announcements", 60, 60))])
async def get_all_announcements(redis=Depends(get_redis)) -> dict[str, Any] | None | Any:
    return await get_announcements(redis)