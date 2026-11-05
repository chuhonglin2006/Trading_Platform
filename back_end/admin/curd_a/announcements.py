"""管理员公告管理接口函数"""

from typing import Any
from crud_1.announcements import invalidate_announcements
from fastapi import HTTPException, status
from sqlalchemy import text
from database_1.mysql_config import async_session_maker
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")


async def get_all_announcements(page: int = 1,page_size: int = 20,keyword: str = "") -> dict[str, Any]:
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分页参数不合法"
        )

    keyword = keyword.strip()

    async with async_session_maker() as session:
        conditions = ""
        params: dict[str, Any] = {}

        if keyword:
            conditions = "WHERE title LIKE :keyword"
            params["keyword"] = f"%{keyword}%"

        total_result = await session.execute(
            text(
                f"""
                SELECT COUNT(*) AS total
                FROM announcements
                {conditions}
                """
            ),
            params
        )
        total = int(total_result.scalar_one() or 0)

        params["limit"] = page_size
        params["offset"] = (page - 1) * page_size

        result = await session.execute(
            text(
                f"""
                SELECT
                    id,
                    title,
                    content,
                    created_at,
                    updated_at
                FROM announcements
                {conditions}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params
        )

        rows = [
            {
                "id": row.id,
                "title": row.title,
                "content": row.content,
                "created_at": (
                    row.created_at.isoformat()
                    if row.created_at else None
                ),
                "updated_at": (
                    row.updated_at.isoformat()
                    if row.updated_at else None
                )
            }
            for row in result
        ]

        return {
            "code": 200,
            "message": "获取公告列表成功",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "announcements": rows
            }
        }

async def get_announcement_info(announcement_id: int) -> dict[str, Any]:
    async with async_session_maker() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    title,
                    content,
                    created_at,
                    updated_at
                FROM announcements
                WHERE id = :id
                """
            ),
            {"id": announcement_id}
        )

        row = result.first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公告不存在"
            )

        return {
            "code": 200,
            "message": "获取公告详情成功",
            "data": {
                "id": row.id,
                "title": row.title,
                "content": row.content,
                "created_at": (
                    row.created_at.isoformat()
                    if row.created_at else None
                ),
                "updated_at": (
                    row.updated_at.isoformat()
                    if row.updated_at else None
                )
            }
        }

async def create_announcement(redis,title: str,content: str) -> dict[str, Any]:
    title = title.strip()
    content = content.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告标题不能为空"
        )

    if len(title) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告标题不能超过100个字符"
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告内容不能为空"
        )

    async with async_session_maker() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO announcements
                    (title, content)
                VALUES
                    (:title, :content)
                """
            ),
            {
                "title": title,
                "content": content
            }
        )

        await session.commit()

        announcement_id = result.lastrowid

    await invalidate_announcements(redis)
    logger.info("公告创建成功 announcement_id=%s", announcement_id)
    return await get_announcement_info(announcement_id)

async def update_announcement(redis,announcement_id: int,title: str,content: str) -> dict[str, Any]:
    title = title.strip()
    content = content.strip()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告标题不能为空"
        )

    if len(title) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告标题不能超过100个字符"
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="公告内容不能为空"
        )

    async with async_session_maker() as session:
        result = await session.execute(
            text(
                """
                UPDATE announcements
                SET
                    title = :title,
                    content = :content,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
            ),
            {
                "id": announcement_id,
                "title": title,
                "content": content
            }
        )

        if result.rowcount == 0:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公告不存在"
            )

        await session.commit()

    await invalidate_announcements(redis)
    logger.info("公告更新成功 announcement_id=%s", announcement_id)
    return await get_announcement_info(announcement_id)

async def delete_announcement(redis,announcement_id: int) -> dict[str, Any]:
    async with async_session_maker() as session:
        result = await session.execute(
            text(
                """
                DELETE FROM announcements
                WHERE id = :id
                """
            ),
            {"id": announcement_id}
        )

        if result.rowcount == 0:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="公告不存在"
            )

        await session.commit()
    await invalidate_announcements(redis)
    logger.info("公告删除成功 announcement_id=%s", announcement_id)
    return {
        "code": 200,
        "message": "公告删除成功",
        "data": {
            "id": announcement_id
        }
    }
