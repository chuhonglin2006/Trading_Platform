"""将 Redis 中的商品浏览量定期写回 MySQL。"""

import asyncio
import uuid

from database_1.mysql_config import async_session_maker
from modles_1.products import Product
from sqlalchemy import func, select, update

from tools_1.logger import get_logger

redis_logger = get_logger(__name__, "redis")
mysql_logger = get_logger(__name__, "mysql")

VIEW_DELTA_KEY = "product:view_delta"
VIEW_DELTA_TMP = "product:view_delta:flushing"
VIEW_FLUSH_LOCK_KEY = "product:view_delta:flush_lock"
VIEW_BASE_FIELD_PREFIX = "__base__:"

_CLAIM_DELTA_LUA = """
if redis.call('exists', KEYS[2]) == 1 then
    return 1
end
if redis.call('exists', KEYS[1]) == 0 then
    return 0
end
redis.call('rename', KEYS[1], KEYS[2])
return 1
"""

_RELEASE_LOCK_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


async def _release_flush_lock(redis, token: str) -> None:
    try:
        await redis.eval(
            _RELEASE_LOCK_LUA,
            1,
            VIEW_FLUSH_LOCK_KEY,
            token
        )
    except Exception:
        pass


async def flush_view_counts(redis) -> None:
    """
    将 Redis 增量写回 MySQL。

    每批数据第一次处理时，把 MySQL 中的原值保存到临时 Hash 的
    __base__:{product_id} 字段。重试时写入 base + delta 的绝对值，
    因此即使 MySQL 已提交但 Redis 删除失败，也不会重复累加。
    """
    token = uuid.uuid4().hex
    acquired = await redis.set(
        VIEW_FLUSH_LOCK_KEY,
        token,
        nx=True,
        ex=120
    )
    if not acquired:
        redis_logger.debug("已有浏览量刷新任务运行中，本轮跳过")
        return

    try:
        await redis.eval(
            _CLAIM_DELTA_LUA,
            2,
            VIEW_DELTA_KEY,
            VIEW_DELTA_TMP
        )

        if not await redis.exists(VIEW_DELTA_TMP):
            return

        raw = await redis.hgetall(VIEW_DELTA_TMP)
        deltas: dict[int, int] = {}
        bases: dict[int, int] = {}

        for field, value in raw.items():
            if field.startswith(VIEW_BASE_FIELD_PREFIX):
                product_id = int(
                    field.removeprefix(VIEW_BASE_FIELD_PREFIX)
                )
                bases[product_id] = int(value)
                continue

            product_id = int(field)
            delta = int(value)
            if delta > 0:
                deltas[product_id] = delta

        if not deltas:
            await redis.delete(VIEW_DELTA_TMP)
            redis_logger.debug("浏览量临时批次无有效增量，已清理")
            return

        missing_base_ids = set(deltas) - set(bases)

        async with async_session_maker() as session:
            if missing_base_ids:
                rows = (
                    await session.execute(
                        select(
                            Product.id,
                            Product.view_count
                        ).where(
                            Product.id.in_(missing_base_ids)
                        )
                    )
                ).all()
                fetched_bases = {
                    int(product_id): int(view_count or 0)
                    for product_id, view_count in rows
                }
                base_mapping = {
                    f"{VIEW_BASE_FIELD_PREFIX}{product_id}":
                    fetched_bases.get(product_id, 0)
                    for product_id in missing_base_ids
                }
                await redis.hset(
                    VIEW_DELTA_TMP,
                    mapping=base_mapping
                )
                bases.update({
                    product_id: fetched_bases.get(product_id, 0)
                    for product_id in missing_base_ids
                })

            for product_id, delta in deltas.items():
                target_count = bases[product_id] + delta
                await session.execute(
                    update(Product).where(
                        Product.id == product_id
                    ).values(
                        view_count=func.greatest(
                            Product.view_count,
                            target_count
                        )
                    )
                )

            await session.commit()
            mysql_logger.info(
                "浏览量写回MySQL成功 products=%s total_delta=%s",
                len(deltas),
                sum(deltas.values())
            )

        # 删除失败时，下一轮会用相同的 base + delta 重放，不会重复累加。
        await redis.delete(VIEW_DELTA_TMP)
        redis_logger.debug("浏览量Redis临时批次已清理")
    finally:
        await _release_flush_lock(redis, token)


async def view_count_flush_loop(redis, interval: int = 60) -> None:
    """每隔 interval 秒刷新一次浏览量。"""
    while True:
        await asyncio.sleep(interval)
        try:
            await flush_view_counts(redis)
        except Exception:
            redis_logger.exception("刷新浏览量失败")
