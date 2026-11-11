"""管理员后台用户函数"""
from typing import Any

from crud_1.users import invalidate_user
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.user import User
from sqlalchemy import func, or_, select
from tools_1.logger import get_logger

logger = get_logger(__name__, "python")


async def get_all_user(page:int = 1,page_size:int = 20,keyword:str = "",user_status:str | None = None) -> dict[str,Any]:
    """
    获取所有用户及状态
    :param page:页数
    :param page_size:页数大小
    :param keyword:用户关键信息
    :param user_status:状态
    :return:
    """
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分页参数不合法"
        )
    conditions = []
    keyword = keyword.strip()
    if keyword:
        conditions.append(
            or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%"),
                User.student_id.like(f"%{keyword}%")
            )
        )
    if user_status is not None:
        if user_status not in ("normal","banned"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户状态不合法"
            )
        conditions.append(User.status == user_status)
    async with async_session_maker() as session:
        count_stmt = select(func.count(User.id)).where(*conditions)
        result = await session.execute(count_stmt)
        total = result.scalar_one()
        stmt = select(User).where(
            *conditions
        ).order_by(User.created_at.desc(),User.id.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await session.execute(stmt)
        users = result.scalars().all()
        return {
            "code": 200,
            "message": "获取用户列表成功",
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "student_id": user.student_id,
                        "campus": user.campus,
                        "status": user.status,
                        "banned_until": (
                            user.banned_until.isoformat()
                            if user.banned_until else None
                        ),
                        "credit_score": user.credit_score,
                        "created_at": (
                            user.created_at.isoformat()
                            if user.created_at else None
                        ),
                        "last_login_at": (
                            user.last_login_at.isoformat()
                            if user.last_login_at else None
                        )
                    }
                    for user in users
                ]
            }
        }

async def update_user_status(redis,user_id: int,new_status: str) -> dict[str, Any]:
    """
    管理员封禁或解封普通用户。
    后台手动封禁按永久封禁处理。
    """
    if new_status not in {"normal", "banned"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户状态不合法"
        )

    async with async_session_maker() as session, session.begin():
        user = (
            await session.execute(
                select(User)
                .where(User.id == user_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        if user.status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已处于该状态"
            )

        user.status = new_status
        # 后台手动封禁是永久封禁，解封也要清空封禁截止时间
        user.banned_until = None

        # 在块里面先把结果组装好，提交之后属性可能已过期，不能再读 user
        response = {
            "code": 200,
            "message": (
                "用户封禁成功"
                if new_status == "banned"
                else "用户解封成功"
            ),
            "data": {
                "id": user.id,
                "username": user.username,
                "status": user.status,
                "banned_until": None
            }
        }
        # 走到这里，事务已经提交

    # 提交成功之后清用户缓存
    await invalidate_user(redis, user_id)
    logger.info(
        "管理员修改用户状态 user_id=%s status=%s",
        user_id,
        new_status
    )

    return response
