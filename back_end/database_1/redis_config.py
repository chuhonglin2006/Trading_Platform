"""Redis配置"""
import redis.asyncio as aioredis
from redis.exceptions import TimeoutError,ConnectionError
import os
from dotenv import load_dotenv
from pathlib import Path
from fastapi import Request
from tools_1.logger import get_logger


logger = get_logger(__name__, "redis")

key_env_path = Path(__file__).resolve().parent.parent / "keys.env"
load_dotenv(key_env_path)
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 50))


pool = aioredis.BlockingConnectionPool(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    max_connections=REDIS_MAX_CONNECTIONS,
    decode_responses=True,
    timeout=5,
    socket_connect_timeout=3,
    socket_timeout=3,
    db=0,
    health_check_interval=30
)

r = aioredis.Redis(connection_pool=pool) # 方便测试 最终要删除



async def redis_content():
    """ 获取Redis连接 """
    redis_client = aioredis.Redis(connection_pool=pool)
    try:
        await redis_client.ping()
    except TimeoutError as e:
        logger.exception(
            "Redis连接超时 host=%s port=%s",
            REDIS_HOST,
            REDIS_PORT
        )
        raise RuntimeError("Redis连接超时") from e
    except ConnectionError as e:
        logger.exception(
            "Redis连接错误 host=%s port=%s",
            REDIS_HOST,
            REDIS_PORT
        )
        raise RuntimeError("Redis连接错误") from e
    except Exception as e:
        logger.exception(
            "Redis连接异常 host=%s port=%s",
            REDIS_HOST,
            REDIS_PORT
        )
        raise RuntimeError("Redis连接异常") from e
    logger.info(
        "Redis连接成功 host=%s port=%s max_connections=%s",
        REDIS_HOST,
        REDIS_PORT,
        REDIS_MAX_CONNECTIONS
    )
    return redis_client

async def redis_close(client:aioredis.Redis):
    """ 关闭Redis连接 """
    try:
        await client.aclose()
        await pool.aclose()
    except Exception:
        logger.exception("关闭Redis连接失败")
        raise
    logger.info("Redis连接池已关闭")

async def get_redis(request:Request) -> aioredis.Redis:
    return request.app.state.redis












