"""管理员界面举报"""
from datetime import datetime, timedelta
from typing import Any

from crud_1.users import invalidate_user
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, status
from modles_1.products import Product
from modles_1.reports import Report
from modles_1.user import User
from sqlalchemy import select
from tools_1.logger import get_logger

logger = get_logger(__name__, "python")

async def get_all_reports() -> dict[str, Any]:
    """
    获取所有举报。
    列表接口一次返回全部举报，前端负责分页和筛选。
    """
    async with async_session_maker() as session:
        stmt = select(Report).order_by(
            Report.created_at.desc(),
            Report.id.desc()
        )

        result = await session.execute(stmt)
        all_reports = result.scalars().all()

        reports = [
            {
                "id": report.id,
                "reporter_id": report.reporter_id,
                "target_type": report.target_type,
                "target_id": report.target_id,
                "reason": report.reason,
                "status": report.status,
                "handle_type": report.handle_type,
                "punish_score": report.punish_score,
                "ban_days": report.ban_days,
                "handle_note": report.handle_note,
                "created_at": (
                    report.created_at.isoformat()
                    if report.created_at else None
                )
            }
            for report in all_reports
        ]

        return {
            "code": 200,
            "message": "获取举报列表成功",
            "data": reports
        }


async def get_report_info(report_id: int) -> dict[str, Any]:
    """
    获取举报详情。

    product 举报的 reported_user 必须取商品 seller_id，
    而不是把商品 ID 当成用户 ID。
    """
    async with async_session_maker() as session:
        report = (
            await session.execute(
                select(Report).where(Report.id == report_id)
            )
        ).scalar_one_or_none()

        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报不存在"
            )

        reporter = (
            await session.execute(
                select(User).where(User.id == report.reporter_id)
            )
        ).scalar_one_or_none()

        target_data = None
        reported_user = None

        if report.target_type == "user":
            target = (
                await session.execute(
                    select(User).where(User.id == report.target_id)
                )
            ).scalar_one_or_none()

            if target:
                target_data = {
                    "id": target.id,
                    "username": target.username
                }
                reported_user = target_data.copy()

        elif report.target_type == "product":
            target = (
                await session.execute(
                    select(Product).where(Product.id == report.target_id)
                )
            ).scalar_one_or_none()

            if target:
                target_data = {
                    "id": target.id,
                    "product_name": target.name
                }

                seller = (
                    await session.execute(
                        select(User).where(User.id == target.seller_id)
                    )
                ).scalar_one_or_none()

                if seller:
                    reported_user = {
                        "id": seller.id,
                        "username": seller.username
                    }

        return {
            "code": 200,
            "message": "获取举报详情成功",
            "data": {
                "id": report.id,
                "reporter_id": report.reporter_id,
                "reporter": {
                    "id": reporter.id,
                    "username": reporter.username
                } if reporter else None,
                "target_type": report.target_type,
                "target_id": report.target_id,
                "target": target_data,
                "reported_user": reported_user,
                "reason": report.reason,
                "status": report.status,
                "handle_type": report.handle_type,
                "punish_score": report.punish_score,
                "ban_days": report.ban_days,
                "handle_note": report.handle_note,
                "created_at": (
                    report.created_at.isoformat()
                    if report.created_at else None
                )
            }
        }


async def handle_report(
    redis,
    report_id: int,
    handle_type: str,
    punish_score: int | None = None,
    ban_days: int | None = None,
    handle_note: str | None = None
) -> dict[str, Any]:
    """
    处理举报：
    - deduct_score：扣除信用分
    - ban：临时/永久封禁
    """
    if handle_type not in {"deduct_score", "ban"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="处理方式错误"
        )

    if handle_note is not None:
        handle_note = handle_note.strip()

        if len(handle_note) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="处理备注不能超过500字"
            )

    async with async_session_maker() as session:
        try:
            report = (
                await session.execute(
                    select(Report)
                    .where(Report.id == report_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if report is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="举报不存在"
                )

            if report.status != "pending":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该举报已经处理过了"
                )

            # 确定真正被处罚的用户
            if report.target_type == "user":
                reported_user_id = report.target_id

            elif report.target_type == "product":
                product = (
                    await session.execute(
                        select(Product)
                        .where(Product.id == report.target_id)
                    )
                ).scalar_one_or_none()

                if product is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="被举报商品不存在"
                    )

                reported_user_id = product.seller_id

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="举报目标类型错误"
                )

            user = (
                await session.execute(
                    select(User)
                    .where(User.id == reported_user_id)
                    .with_for_update()
                )
            ).scalar_one_or_none()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="被举报用户不存在"
                )

            if handle_type == "deduct_score":
                if punish_score is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="请输入要扣除的信用分"
                    )

                if not isinstance(punish_score, int) or punish_score <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="扣除信用分必须是大于0的整数"
                    )

                actual_score = min(
                    punish_score,
                    int(user.credit_score or 0)
                )

                user.credit_score = int(user.credit_score or 0) - actual_score

                report.handle_type = "deduct_score"
                report.punish_score = actual_score
                report.ban_days = None

            else:
                if ban_days is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="请选择封禁时间"
                    )

                if ban_days != -1 and ban_days <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="封禁天数必须大于0，永久封禁使用-1"
                    )

                user.status = "banned"

                if ban_days == -1:
                    user.banned_until = None
                else:
                    user.banned_until = (
                        datetime.now() +
                        timedelta(days=ban_days)
                    )

                report.handle_type = "ban"
                report.punish_score = None
                report.ban_days = ban_days

            report.status = "resolved"
            report.handle_note = handle_note

            await session.commit()
            await session.refresh(report)
            await invalidate_user(redis, reported_user_id)
            logger.info(
                "举报处理完成 report_id=%s handle_type=%s reported_user_id=%s",
                report.id,
                report.handle_type,
                reported_user_id
            )

            return {
                "code": 200,
                "message": "举报处理成功",
                "data": {
                    "id": report.id,
                    "status": report.status,
                    "handle_type": report.handle_type,
                    "punish_score": report.punish_score,
                    "ban_days": report.ban_days,
                    "handle_note": report.handle_note
                }
            }

        except HTTPException:
            await session.rollback()
            raise

        except Exception:
            await session.rollback()
            raise


async def reject_report(
    report_id: int,
    handle_note: str | None = None
) -> dict[str, Any]:
    """
    驳回举报，不对被举报用户执行处罚。
    """
    if handle_note is not None:
        handle_note = handle_note.strip()

        if len(handle_note) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="处理备注不能超过500字"
            )

    async with async_session_maker() as session:
        report = (
            await session.execute(
                select(Report)
                .where(Report.id == report_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="举报不存在"
            )

        if report.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该举报已经处理过了"
            )

        report.status = "rejected"
        report.handle_type = None
        report.punish_score = None
        report.ban_days = None
        report.handle_note = handle_note

        await session.commit()
        await session.refresh(report)
        logger.info("举报已驳回 report_id=%s", report.id)

        return {
            "code": 200,
            "message": "举报已驳回",
            "data": {
                "id": report.id,
                "status": report.status,
                "handle_note": report.handle_note
            }
        }

