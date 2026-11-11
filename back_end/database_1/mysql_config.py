"""MySQL配置"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from tools_1.logger import get_logger

logger = get_logger(__name__, "mysql")




key_env_path = Path(__file__).resolve().parent.parent / "keys.env"
load_dotenv(key_env_path)
DATABASE_NAME = os.getenv('DATABASE_NAME')
DATABASE_PORT = os.getenv('DATABASE_PORT')
DATABASE_HOST = os.getenv('DATABASE_HOST')
DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
# 超过这个耗时才记录为慢查询
SLOW_QUERY_MS = float(os.getenv("SLOW_QUERY_MS", "500"))
# 排查问题时设为 1
LOG_ALL_SQL = os.getenv("LOG_ALL_SQL", "").lower() in ("1", "true", "yes")




def get_database_url() -> URL:
    """
    获取数据库连接URL
    :return:数据库连接URL
    """
    DB_URL = URL.create(
            drivername="mysql+aiomysql",
            username=DATABASE_USER,
            password=DATABASE_PASSWORD,
            host=DATABASE_HOST,
            port=int(DATABASE_PORT or 3306),
            database=DATABASE_NAME,
            query={"charset": "utf8mb4"}
            )
    return DB_URL

"""创建异步引擎"""
async_engine = create_async_engine(
    url=get_database_url(),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20  
)
"""创建异步会话工厂"""
async_session_maker  = async_sessionmaker(
    bind = async_engine,
    class_ = AsyncSession,
    autoflush = False,
    expire_on_commit = False
)


def _short_sql(statement: str | None) -> str:
    if not statement:
        return "<unknown>"
    return " ".join(statement.split())[:800]


@event.listens_for(async_engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn,cursor,statement,parameters,context,executemany):
    conn.info["query_started_at"] = time.perf_counter()


@event.listens_for(async_engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn,cursor,statement,parameters,context,executemany):
    started_at = conn.info.pop("query_started_at", None)
    if started_at is None:
        return

    duration_ms = (time.perf_counter() - started_at) * 1000
    if duration_ms >= SLOW_QUERY_MS:
        logger.warning(
            "MySQL慢查询 duration_ms=%.1f sql=%s",
            duration_ms,
            _short_sql(statement)
        )
    elif LOG_ALL_SQL:
        logger.info(
            "MySQL查询完成 duration_ms=%.1f sql=%s",
            duration_ms,
            _short_sql(statement)
        )


@event.listens_for(async_engine.sync_engine, "handle_error")
def _handle_mysql_error(exception_context):
    error = (
        exception_context.original_exception
        or RuntimeError("MySQL未知执行错误")
    )
    logger.error(
        "MySQL执行失败 sql=%s error=%s",
        _short_sql(exception_context.statement),
        error,
        exc_info=(type(error), error, error.__traceback__)
    )

