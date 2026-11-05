"""商品列表和搜索缓存的统一版本号。"""

from tools_1.logger import get_logger


logger = get_logger(__name__, "redis")

PRODUCT_CACHE_VERSION_KEY = "product:cache:version:v2"
PRODUCT_CACHE_VERSION_TTL = 7 * 24 * 3600


async def get_product_cache_version(redis) -> str:
    """读取商品聚合缓存的当前版本号，Redis 异常时退回版本 0。"""
    try:
        return await redis.get(PRODUCT_CACHE_VERSION_KEY) or "0"
    except Exception:
        logger.exception("商品缓存版本读取失败，使用版本0")
        return "0"


async def bump_product_cache_version(redis) -> int | None:
    """递增版本号，使旧列表、搜索和他人商品缓存立即失去引用。"""
    try:
        pipe = redis.pipeline(transaction=True)
        pipe.incr(PRODUCT_CACHE_VERSION_KEY)
        pipe.expire(PRODUCT_CACHE_VERSION_KEY, PRODUCT_CACHE_VERSION_TTL)
        version, _ = await pipe.execute()
        logger.info("商品缓存版本已更新 version=%s", version)
        return int(version)
    except Exception:
        logger.exception("商品缓存版本更新失败")
        return None
