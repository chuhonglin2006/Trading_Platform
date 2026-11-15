"""启动时检查评价功能需要的表结构（和 ensure_product_region_schema 一样，只检查不自动改表）。"""
from database_1.mysql_config import async_engine
from sqlalchemy import text
from tools_1.logger import get_logger

logger = get_logger(__name__, "mysql")


async def ensure_review_schema() -> None:
    async with async_engine.connect() as connection:
        has_table = (
            await connection.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'reviews'
                    """
                )
            )
        ).scalar_one()
        score_type = (
            await connection.execute(
                text(
                    """
                    SELECT DATA_TYPE FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'users'
                      AND COLUMN_NAME = 'credit_score'
                    """
                )
            )
        ).scalar_one_or_none()

    if not has_table or (score_type or "").lower() != "decimal":
        logger.error("评价功能所需表结构缺失 reviews表存在=%s credit_score类型=%s", bool(has_table), score_type)
        raise RuntimeError(
            "数据库还没有升级评价功能所需的表结构，"
            "请先手动执行 back_end/migrations/001_add_reviews.sql 后再启动"
        )
