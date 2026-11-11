"""举报接口函数"""
from typing import Any

from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.products import Product
from modles_1.reports import Report
from modles_1.user import User
from sqlalchemy import select
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
        # 目标是否存在；商品同时取出卖家 id
        if target_type == "user":
            target = await session.scalar(
                select(User.id).where(User.id == target_id)
            )
            owner_id = target
        else:
            owner_id = await session.scalar(
                select(Product.seller_id).where(Product.id == target_id)
            )
            target = owner_id

        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报目标不存在"
            )

        # 不能举报自己，也不能举报自己的商品
        if owner_id == reporter_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不允许举报自己" if target_type == "user" else "不允许举报自己的商品"
            )

        # 同一用户对同一目标，已有待处理的举报就不能重复提交
        duplicate = await session.scalar(
            select(Report.id).filter_by(
                reporter_id=reporter_id,
                target_type=target_type,
                target_id=target_id,
                status="pending",
            ).limit(1)
        )

        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="你已举报过该目标，请等待处理"
            )

        report = Report(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reson
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






