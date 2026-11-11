"""启动时检查数据库是否已初始化：一张业务表都没有，就执行 schema.sql 建表。"""

from pathlib import Path
from database_1.mysql_config import async_engine
from tools_1.logger import get_logger

logger = get_logger(__name__, "mysql")

# schema.sql 放在 back_end/ 目录下（本文件在 back_end/tools_1/ 下）
SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schema.sql"

REQUIRED_TABLES = {
    "admins", "announcements", "categories", "users", "products",
    "product_images", "favorites", "orders", "chat_conversations",
    "chat_messages", "reports",
}

# 多个后端实例同时启动时，用 MySQL 命名锁保证只有一个去建表
LOCK_NAME = "campus_market_schema_init"
LOCK_TIMEOUT_SECONDS = 30


def _split_statements(sql: str) -> list[str]:
    """去掉 -- 注释行，再按分号拆成单条语句。"""
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return [part.strip() for part in "\n".join(lines).split(";") if part.strip()]


async def _existing_tables(connection) -> set[str]:
    result = await connection.exec_driver_sql(
        "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()"
    )
    return {row[0] for row in result}


async def init_database_if_empty() -> None:
    """
    - 11 张表都在：什么都不做
    - 一张都没有：加锁后执行 schema.sql
    - 只有一部分：抛出错误，让人手动检查（不自动改动已有数据）
    """
    async with async_engine.connect() as connection:
        existing = await _existing_tables(connection)
        if existing >= REQUIRED_TABLES:
            return

        if existing & REQUIRED_TABLES:
            missing = sorted(REQUIRED_TABLES - existing)
            raise RuntimeError(f"数据库表不完整，缺少：{missing}，请手动检查后再启动")

        if not SCHEMA_FILE.exists():
            raise RuntimeError(f"数据库为空，但找不到建表文件：{SCHEMA_FILE}")

        got_lock = (
            await connection.exec_driver_sql(
                f"SELECT GET_LOCK('{LOCK_NAME}', {LOCK_TIMEOUT_SECONDS})"
            )
        ).scalar()
        if got_lock != 1:
            raise RuntimeError("获取建表锁超时，请确认没有其他实例正在初始化数据库")

        try:
            # 拿到锁以后再确认一次：可能别的实例刚刚建完
            if REQUIRED_TABLES <= await _existing_tables(connection):
                logger.info("数据库已由其他实例初始化完成")
                return

            statements = _split_statements(SCHEMA_FILE.read_text(encoding="utf-8"))
            logger.info("数据库为空，开始执行 %s（共 %s 条语句）", SCHEMA_FILE.name, len(statements))
            for statement in statements:
                await connection.exec_driver_sql(statement)
            await connection.commit()
            logger.info("数据库初始化完成")
        finally:
            await connection.exec_driver_sql(f"SELECT RELEASE_LOCK('{LOCK_NAME}')")