""" 限流工具 """
from fastapi import HTTPException,status,Request,Depends
from database_1.redis_config import get_redis
from tools_1.logger import get_logger
from tools_1.client_ip import get_client_ip


logger = get_logger(__name__, "redis")



async def check_rate_limit(redis, key: str, limit: int, window: int, message: str = "请求过于频繁"):
    """ 限流 超过limit次就抛出429 """
    try:
        pipe = redis.pipeline(transaction=True)   # MULTI/EXEC 保证三条命令原子执行
        pipe.set(key, 0, nx=True, ex=window)
        pipe.incr(key)
        pipe.ttl(key)
        _, count, ttl = await pipe.execute()
        if ttl == -1:                              # 修复历史上已经没有 TTL 的 key
            await redis.expire(key, window)
            ttl = window
    except Exception:
        logger.exception("Redis限流异常，本次请求放行 key=%s", key)
        return

    if count > limit:
        retry = max(ttl, 1)
        logger.warning(
            "触发限流 key=%s count=%s limit=%s retry_after=%s",
            key,
            count,
            limit,
            retry
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{message}:请{retry}秒后重试",
            headers={"Retry-After": str(retry)}
        )


def ip_rate_limit(name: str, limit: int, window: int):
    """按 IP 限流"""
    async def dependency(request: Request, redis=Depends(get_redis)):
        ip = get_client_ip(request)
        await check_rate_limit(redis, f"ratelimit:{name}:{ip}", limit, window)
    return dependency


