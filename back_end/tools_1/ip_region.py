"""客户端 IP 省份解析、缓存和商品发布地回填。"""

import ipaddress

from database_1.mysql_config import async_engine, async_session_maker
from sqlalchemy import or_, select, text
from sqlalchemy.orm import joinedload

from tools_1.add_ip_data_to_memory import search_ip_region
from tools_1.logger import get_logger

logger = get_logger(__name__, "python")

UNKNOWN_REGION = "未知"
REGION_CACHE_PREFIX = "ip:region:v2:"
REGION_CACHE_TTL = 7 * 24 * 3600
UNKNOWN_CACHE_TTL = 10 * 60


def _valid_public_ip(value: str | None) -> str | None:
    try:
        ip = ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None
    if not ip.is_global or ip.version != 4:
        return None
    return str(ip)


def _region_from_result(result: str) -> str:
    """XDB 格式为 国家|省份|城市|运营商|国家代码。"""
    parts = [part.strip() for part in (result or "").split("|")]
    if len(parts) < 2:
        return UNKNOWN_REGION

    province = parts[1]
    if province and province != "0":
        return province

    country = parts[0]
    return country if country and country != "0" else UNKNOWN_REGION


async def get_ip_province(redis, ip: str | None) -> str:
    """返回 IP 所属省份；失败时返回“未知”，不向上抛出网络异常。"""
    public_ip = _valid_public_ip(ip)
    if public_ip is None:
        return UNKNOWN_REGION

    cache_key = f"{REGION_CACHE_PREFIX}{public_ip}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            return str(cached)
    except Exception:
        logger.exception("IP 省份缓存读取失败 ip=%s", public_ip)

    province = _region_from_result(search_ip_region(public_ip))

    try:
        ttl = REGION_CACHE_TTL if province != UNKNOWN_REGION else UNKNOWN_CACHE_TTL
        await redis.set(cache_key, province, ex=ttl)
    except Exception:
        logger.exception("IP 省份缓存写入失败 ip=%s", public_ip)

    return province


async def ensure_product_region_schema() -> None:
    """启动时只检查 products.publish_province 列是否存在，不再自动改表。"""
    async with async_engine.connect() as connection:
        exists = (
            await connection.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'products'
                      AND COLUMN_NAME = 'publish_province'
                    """
                )
            )
        ).scalar_one()

    if not exists:
        logger.error("products.publish_province 列不存在")
        raise RuntimeError(
            "数据库缺少 products.publish_province 列，请手动执行："
            "ALTER TABLE products ADD COLUMN publish_province VARCHAR(50) NULL AFTER campus;"
        )


async def backfill_product_publish_provinces(redis) -> None:
    """给上线前发布的商品补齐发布省份，避免旧商品显示为空。"""
    from modles_1.products import Product

    updated = 0
    try:
        async with async_session_maker() as session:
            products = (
                await session.execute(
                    select(Product)
                    .where(
                        or_(
                            Product.publish_province.is_(None),
                            Product.publish_province == "",
                        )
                    )
                    .options(joinedload(Product.seller))
                    .order_by(Product.id.desc())
                    .limit(100)
                )
            ).unique().scalars().all()

            for product in products:
                seller = product.seller
                ip = (
                    seller.last_login_ip
                    or seller.register_ip
                    if seller
                    else None
                )
                province = await get_ip_province(redis, ip)
                if province != UNKNOWN_REGION:
                    product.publish_province = province
                    updated += 1

            if updated:
                await session.commit()
    except Exception:
        logger.exception("历史商品发布省份回填失败")
        return

    if updated:
        try:
            from tools_1.product_cache_version import bump_product_cache_version
            await bump_product_cache_version(redis)
        except Exception:
            logger.exception("商品发布省份回填后的缓存刷新失败")
        logger.info("历史商品发布省份回填完成 updated=%s", updated)