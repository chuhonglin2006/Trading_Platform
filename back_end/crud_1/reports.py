"""举报接口函数"""
from modles_1.reports import Report
from sqlalchemy import select
from typing import Any
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException,status
from modles_1.user import User
from modles_1.products import Product
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")



async def report_user(reporter_id:int,target_id:int,reason:str,target_type:str) -> dict[str,Any]:
    """
    举报用户
    :param target_type:举报类型
    :param reporter_id:举报者id
    :param target_id:被举报者id
    :param reason:原因
    :return:举报信息
    """
    if target_type not in {"user","product"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="举报类型目标错误"
        )
    reson = reason.strip()
    if not reson:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="举报原因不能为空"
        )
    if len(reson) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="超出字数限制"
        )
    async with async_session_maker() as session:
        if target_type == "user":
            stmt = select(User.id).where(
                User.id == target_id
            )
        else:
            stmt = select(Product.id).where(
                Product.id == target_id
            )
        result = await session.execute(stmt)
        target = result.scalar_one_or_none()
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报目标不存在"
            )
        if target_type == "user" and reporter_id == target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不允许举报自己"
            )
        report = Report(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        logger.info(
            "用户提交举报 report_id=%s reporter_id=%s target_type=%s target_id=%s",
            report.id,
            reporter_id,
            target_type,
            target_id
        )
        return {
            "id": report.id,
            "reporter_id": report.reporter_id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason": report.reason,
            "status": report.status,
            "created_at": report.created_at
        }






