"""公告接口函数"""
import asyncio
import json
import random
from typing import Any

from cachetools import TTLCache
from database_1.mysql_config import async_session_maker
from modles_1.announcements import Announcements
from sqlalchemy import select
from tools_1.logger import get_logger

logger = get_logger(__name__, "redis")

ANNOUNCEMENTS_KEY = "announcements:list"
announcements_local_cache = TTLCache(maxsize=1, ttl=10)
_announcements_lock = asyncio.Lock()

async def invalidate_announcements(redis) -> None:
    """ 管理员增删改公告后调用 commit 之后 """
    announcements_local_cache.clear()
    try:
        await redis.delete(ANNOUNCEMENTS_KEY)
    except Exception:
        logger.exception("公告缓存删除失败 key=%s", ANNOUNCEMENTS_KEY)

async def get_announcements_from_mysql() -> dict[str, Any]:
    async with async_session_maker() as session:
        stmt = (select(Announcements).order_by(
            Announcements.created_at.desc(),
            Announcements.id.desc()
        ))
        announcements = (await session.execute(stmt)).scalars().all()
        return {
            "code": 200,
            "message": "获取公告成功",
            "data": [
                {
                    "id": a.id,
                    "title": a.title,
                    "content": a.content,
                    "created_at": a.created_at.isoformat()
                }
                for a in announcements
            ]
        }

async def get_announcements(redis) -> dict[str, Any] | None | Any:
    """ 获取公告: 本地缓存 -> Redis -> MySQL """
    data = announcements_local_cache.get(ANNOUNCEMENTS_KEY)
    if data is not None:
        return data

    try:
        cached = await redis.get(ANNOUNCEMENTS_KEY)
        if cached is not None:
            data = json.loads(cached)
            announcements_local_cache[ANNOUNCEMENTS_KEY] = data
            return data
    except Exception:
        logger.exception("公告缓存读取失败 key=%s", ANNOUNCEMENTS_KEY)

    async with _announcements_lock:          # 防击穿
        data = announcements_local_cache.get(ANNOUNCEMENTS_KEY)
        if data is not None:
            return data

        data = await get_announcements_from_mysql()
        try:
            await redis.set(ANNOUNCEMENTS_KEY,
                            json.dumps(data, ensure_ascii=False),
                            ex=300 + random.randint(0, 60))
        except Exception:
            logger.exception("公告缓存写入失败 key=%s", ANNOUNCEMENTS_KEY)
        announcements_local_cache[ANNOUNCEMENTS_KEY] = data
        return data
