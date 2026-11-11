"""
管理员登录防暴力破解
同一个 IP，15 分钟内最多失败 10 次
同一个管理员账号，15 分钟内最多失败 10 次（不管来自哪些 IP，防分布式猜密码）
达到上限后，这个 IP / 这个账号在剩余时间内不能再尝试登录
登录成功后清零
Redis 不可用时拒绝登录
"""

import hashlib

from fastapi import HTTPException, status

from tools_1.logger import get_logger

logger = get_logger(__name__, "redis")

WINDOW_SECONDS = 15 * 60
MAX_FAILS_PER_IP = 10
MAX_FAILS_PER_ACCOUNT = 10


def _ip_key(ip: str) -> str:
    return f"admin:login:fail:ip:{ip}"


def _account_key(username: str) -> str:
    # 账号名先做哈希再放进 key，避免特殊字符和过长的 key
    digest = hashlib.sha256(username.strip().lower().encode("utf-8")).hexdigest()
    return f"admin:login:fail:user:{digest[:32]}"


async def ensure_admin_login_allowed(redis, ip: str, username: str) -> None:
    """
    登录前调用：被锁定时直接抛 429，不会再去查数据库、也不会计算 bcrypt
    Redis 异常时抛 503
    """
    keys = [_ip_key(ip), _account_key(username)]
    limits = [MAX_FAILS_PER_IP, MAX_FAILS_PER_ACCOUNT]
    retry_after: int | None = None

    try:
        values = await redis.mget(keys)
        for key, raw, limit in zip(keys, values, limits):
            if int(raw or 0) >= limit:
                ttl = await redis.ttl(key)
                retry_after = max(retry_after or 0, ttl, 1)
    except Exception:
        logger.exception("管理员登录限流检查失败，拒绝本次登录 ip=%s", ip)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="登录服务暂时不可用，请稍后重试",
        )

    if retry_after is not None:
        logger.warning("管理员登录被限制 ip=%s retry_after=%s", ip, retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，请{retry_after}秒后重试",
            headers={"Retry-After": str(retry_after)},
        )


async def record_admin_login_failure(redis, ip: str, username: str) -> None:
    """登录失败后调用：IP 和账号两个计数各加 1。记录出错不影响返回 401。"""
    try:
        for key in (_ip_key(ip), _account_key(username)):
            pipe = redis.pipeline(transaction=True)
            pipe.set(key, 0, nx=True, ex=WINDOW_SECONDS)   # 第一次失败时才设置有效期
            pipe.incr(key)
            await pipe.execute()
    except Exception:
        logger.exception("记录管理员登录失败次数出错 ip=%s", ip)


async def clear_admin_login_failures(redis, ip: str, username: str) -> None:
    """登录成功后调用：清零。"""
    try:
        await redis.delete(_ip_key(ip), _account_key(username))
    except Exception:
        logger.exception("清除管理员登录失败计数出错 ip=%s", ip)