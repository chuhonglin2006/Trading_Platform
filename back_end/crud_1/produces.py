"""商品接口函数"""
import asyncio
import copy
import datetime
import hashlib
import json
import random
import uuid
from decimal import Decimal
from typing import Any

from cachetools import TTLCache
from database_1.mysql_config import async_session_maker
from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from modles_1.category import Category
from modles_1.chat import ChatConversation, ChatMessage
from modles_1.favorite import Favorite
from modles_1.order import Order
from modles_1.product_image import ProductImage
from modles_1.products import Product
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from tools_1.add_ttl_for_products import (
    make_null_ttl,
    make_products_ttl,
    make_state_ttl,
)
from tools_1.get_six_mouth import get_six_months_ago
from tools_1.limit import check_rate_limit
from tools_1.logger import get_logger
from tools_1.product_cache_version import (
    bump_product_cache_version,
    get_product_cache_version,
)
from tools_1.product_serializer import build_product_detail
from tools_1.product_state import status_after_resubmit
from tools_1.review_product import validate_product
from tools_1.uload_image_to_server import (
    delete_image,
    get_image_filename,
    normalize_image_url,
    upload_image,
)
from tools_1.warm_up_cache import list_cache_key, products_bloom

from crud_1.users import get_user_cached

app_logger = get_logger(__name__, "python")
redis_logger = get_logger(__name__, "redis")
mysql_logger = get_logger(__name__, "mysql")


""" 获取商品列表 """
def build_list_item(product: Product) -> dict[str, Any]:
    """ 将商品转字典抽成函数 """
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "original_price": product.original_price,
        "description": product.description,
        "status": product.status,
        "view_count": product.view_count,
        "campus": product.campus,
        "publish_province": product.publish_province,
        "created_at": product.created_at,
        "images": [normalize_image_url(i.image_url) for i in product.images],
        "category": {
            "id": product.category.id,
            "key": product.category.key,
            "name": product.category.name,
        } if product.category else None,
        "seller": {
            "id": product.seller.id,
            "username": product.seller.username,
        } if product.seller else None,
    }

# 列表专用本地缓存 条目大 容量小 TTL 短
list_local_cache = TTLCache(maxsize=50, ttl=15)
# 防击穿 用固定数量的分片锁，按 key 的哈希取模选锁，数量固定不会增长
_LIST_LOCKS = [asyncio.Lock() for _ in range(64)]


async def get_products_list_from_mysql(page: int, page_size: int) -> dict[str, Any]:
    """
    从MySQL中获取所有商品列表
    :return: 商品列表
    """

    conditions = (Product.status == "on_sale",Product.review_status == "approved")

    async with async_session_maker() as session:
        stmt = select(Product).where(*conditions).options(
            joinedload(Product.category),
            joinedload(Product.seller),
            joinedload(Product.images)
        ).order_by(Product.created_at.desc(),Product.id.desc()).offset(
            (page - 1) * page_size).limit(page_size)

        products = (await session.execute(stmt)).unique().scalars().all()

        total = (await session.execute(select(func.count(Product.id)).where(*conditions))).scalar_one()

        return {
            "code": 200,
            "message": "获取成功",
            "data": [build_list_item(p) for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

async def get_products_list_cache(redis,page:int,page_size:int) -> Any | None:
    """
    从本地缓存、Redis中获取商品列表
    :return: 商品列表
    """
    MAX_CACHE_PAGE = 5 # 只存前5页
    MAX_CACHE_PAGE_SIZE = 50 # page_size上限

    # 深翻页、page_size过大 直接查询MySQL
    if page > MAX_CACHE_PAGE or page_size > MAX_CACHE_PAGE_SIZE:
        return jsonable_encoder(await get_products_list_from_mysql(page,page_size))

    version = await get_product_cache_version(redis)
    key = list_cache_key(page, page_size, version)

    # 本地缓存
    data = list_local_cache.get(key)
    if data is not None:
        redis_logger.debug("商品列表本地缓存命中 key=%s", key)
        return data

    # Redis
    try:
        cached = await redis.get(key)
        if cached is not None:
            data = json.loads(cached)
            list_local_cache[key] = data # 填回本地缓存
            redis_logger.debug("商品列表Redis缓存命中 key=%s", key)
            return data
    except Exception:
        redis_logger.exception("商品列表Redis缓存读取失败 key=%s", key)

    # MySQL
    lock = _LIST_LOCKS[hash(key) % len(_LIST_LOCKS)]
    async with lock:
        # 双重检查
        data = list_local_cache.get(key)
        if data is not None:
            redis_logger.debug("商品列表等锁后本地缓存命中 key=%s", key)
            return data
        mysql_logger.debug("商品列表缓存未命中，查询MySQL key=%s", key)
        result = await get_products_list_from_mysql(page,page_size)
        data = jsonable_encoder(result)

        try:
            await redis.set(key,json.dumps(data,ensure_ascii=False),ex = 60 + random.randint(0,15))
        except Exception:
            redis_logger.exception("商品列表Redis缓存写入失败 key=%s", key)

        list_local_cache[key] = data
        return data



""" 获取商品详情 """
async def get_product_info_from_mysql(product_id:int,viewer_id: int | None = None) -> tuple[dict | None, str | None, bool, str | None]:
    """
    从MySQL中查询商品详细信息,并判断商品是否公开
    :param viewer_id: 浏览者id
    :param product_id: 商品id
    :return: 商品信息、是否公开、商品出售者id
    """
    async with async_session_maker() as session:
        product = (await session.execute(select(Product).options(
                selectinload(Product.category),
                selectinload(Product.seller),
                selectinload(Product.images),
            ).where(Product.id == product_id)
        )).scalar_one_or_none()

        # 商品不存在
        if product is None:
            return None, None, False, None

        # 判断商品状态
        if product.review_status != "approved":
            state = "unapproved"
        elif product.status == "sold":
            state = "sold"
        elif product.status != "on_sale":
            state = "off_sale"
        else:
            state = "public"

        # 判断访问者是否能查看
        visible = state == "public"
        if not visible and viewer_id is not None:
            if product.seller_id == viewer_id:
                visible = True
            else:
                related_order = await session.scalar(
                    select(Order.id).where(
                        Order.product_id == product_id,or_(
                            Order.buyer_id == viewer_id,Order.seller_id == viewer_id
                        )
                    ).limit(1)
                )
                visible = related_order is not None

        # 没有权限查看
        if not visible:
            return None,state,False,None

        active_order_status = await session.scalar(
            select(Order.status).where(Order.product_id == product_id,
            Order.status.in_(["pending","received"]
                )
            ).order_by(Order.created_at.desc()).limit(1)
        )
        return build_product_detail(product), state, True, active_order_status

detail_local_cache = TTLCache(maxsize=1000, ttl=30)
_detail_locks = [asyncio.Lock() for _ in range(64)] # 分片锁

def detail_cache_key(product_id) -> str:
    """
    获取商品缓存key
    :param product_id:商品id
    :return: 商品缓存key
    """
    return f"product:detail:{product_id}"

def not_found() -> HTTPException:
    """
    商品不存在、没有查看权限统一返回码
    :return: 404
    """
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="商品不存在")

async def finish(redis,detail:dict,active_order_status,viewer_id,client_ip: str | None = None,) -> dict[str,Any]:
    """ 统一出口 记录浏览器 + 拼响应 """
    seller_id = (detail.get("seller") or {}).get("id")
    who = f"u{viewer_id}" if viewer_id else f"ip{client_ip or 'unknown'}"
    if viewer_id != seller_id:
        try:
            first_view = await redis.set(f"product:viewed:{detail['id']}:{who}", 1, nx=True, ex=600)
            if first_view:
                await redis.hincrby("product:view_delta", str(detail["id"]), 1)
        except Exception:
            redis_logger.exception(
                "记录商品浏览量失败 product_id=%s viewer=%s",
                detail.get("id"),
                who
            )
    return {
        "code":200,
        "message":"获取成功",
        "data":{**detail,"active_order_status":active_order_status}
    }

def state_cache_key(product_id: int) -> str:
    """ 生成商品状态key """
    return f"product:state:{product_id}"

async def get_product_info_from_cache(redis,product_id: int,viewer_id: int | None = None,client_ip: str | None = None) -> dict[str, Any]:
    """从缓存中获取商品详细信息：布隆过滤器 → 本地缓存 → Redis → MySQL"""

    # 布隆过滤器
    if product_id not in products_bloom:
        redis_logger.debug("商品详情被布隆过滤器拦截 product_id=%s", product_id)
        raise not_found()

    key = detail_cache_key(product_id)

    # 本地缓存
    local_detail: dict | None = detail_local_cache.get(product_id)
    if local_detail is not None:
        redis_logger.debug("商品详情本地缓存命中 product_id=%s", product_id)
        return await finish(redis, local_detail, None, viewer_id,client_ip)

    # Redis
    cached: str | bytes | None = None
    try:
        cached = await redis.get(key)
    except Exception:
        redis_logger.exception(
            "商品详情Redis读取失败，降级查询MySQL product_id=%s",
            product_id
        )

    if cached is not None:
        if cached in ("null", b"null"):
            redis_logger.debug("商品详情Redis命中空值 product_id=%s", product_id)
            raise not_found()
        redis_detail: dict = json.loads(cached)
        detail_local_cache[product_id] = redis_detail
        redis_logger.debug("商品详情Redis缓存命中 product_id=%s", product_id)
        return await finish(redis, redis_detail, None, viewer_id,client_ip)

    # 游客快速拒绝 非公开商品 不查询MySQL 游客直接返回404
    if viewer_id is None:
        hidden_state = None
        try:
            hidden_state = await redis.get(state_cache_key(product_id))
        except Exception:
            redis_logger.exception(
                "商品状态标记读取失败 product_id=%s",
                product_id
            )
        if hidden_state is not None:
            redis_logger.debug(
                "商品非公开状态命中 product_id=%s state=%s",
                product_id,
                hidden_state
            )
            raise not_found()

    # MySQL
    async with _detail_locks[product_id % len(_detail_locks)]:
        local_detail = detail_local_cache.get(product_id)
        if local_detail is not None:
            redis_logger.debug(
                "商品详情等锁后本地缓存命中 product_id=%s",
                product_id
            )
            return await finish(redis, local_detail, None, viewer_id,client_ip)

        mysql_logger.debug("商品详情缓存未命中，查询MySQL product_id=%s", product_id)
        data, state, visible, active = await get_product_info_from_mysql(
            product_id, viewer_id
        )

        try:
            if state is None:  # 商品真的不存在
                await redis.set(key, "null", ex=make_null_ttl())
            elif state == "public":  # 公开商品
                await redis.set(
                    key,
                    json.dumps(data, ensure_ascii=False),
                    ex=make_products_ttl(),
                )
            else:  # 存在但非公开 写状态标记
                await redis.set(
                    state_cache_key(product_id), state, ex=make_state_ttl(state)
                )
        except Exception:
            redis_logger.exception(
                "商品详情Redis缓存写入失败 product_id=%s",
                product_id
            )

        if data is None or not visible:
            raise not_found()
        if state == "public":
            detail_local_cache[product_id] = data
        return await finish(redis, data, active, viewer_id, client_ip)



""" 发布商品 """
_RELEASE_LOCK_LUA = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    if tonumber(ARGV[2]) > 0 then
        return redis.call('expire', KEYS[1], ARGV[2])
    end
    return redis.call('del', KEYS[1])
end
return 0
"""
async def release_publish_lock(redis, lock_key: str, token: str | None, keep: int = 0) -> None:
    """ 只处理自己持有的锁 keep>0 时不删除 只把剩余时间缩短到 keep 秒 """
    if token is None:
        return
    try:
        await redis.eval(_RELEASE_LOCK_LUA, 1, lock_key, token, keep)
    except Exception:
        pass

# 发布限制 每小时最多发布20个
PUBLISH_LIMIT = 20
MAX_PUBLISH_IMAGES = 9
PUBLISH_WINDOW = 3600

async def publish_produce(redis,user_id: int,produce_name: str,price: Decimal,original_price: Decimal | None,
description: str,category_id: int,campus: str,publish_province: str,images: list[UploadFile]) -> dict[str, Any]:
    """
    发布商品
    :param publish_province:
    :param redis: Redis连接
    :param images: 图片列表
    :param user_id: 用户id
    :param produce_name: 商品名称
    :param price: 商品价格
    :param original_price: 商品原价
    :param description: 商品描述
    :param category_id: 分类id
    :param campus: 校区
    :return: 商品信息
    """
    # 图片张数检查
    if not 1 <= len(images) <= MAX_PUBLISH_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"请上传 1-{MAX_PUBLISH_IMAGES} 张图片"
        )

    # 频率检查
    count_key = f"publish:count:{user_id}"
    used = 0
    try:
        raw = await redis.get(count_key)
        used = int(raw) if raw else 0
    except Exception:
        redis_logger.exception(
            "商品发布频率检查失败，本次放行 user_id=%s",
            user_id
        )
    if used >= PUBLISH_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="发布过于频繁,请稍后重试"
        )

    # 防止重复提交
    lock_key = f"publish:lock:{user_id}"
    lock_token: str | None = None
    published = False
    uploaded_names: list[str] = []
    token = uuid.uuid4().hex
    try:
        got = await redis.set(lock_key, token, nx=True, ex=60)  # 10 秒 → 60 秒,覆盖多图上传
    except Exception:
        redis_logger.exception(
            "商品发布防重复锁失败，本次继续 user_id=%s",
            user_id
        )
    else:
        if not got:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="正在发布中,请勿重复提交"
            )
        lock_token = token

    async with async_session_maker() as session:
        try:
            review_passed,review_reason = await validate_product(
                produce_name=produce_name,price=price,
                original_price=original_price,description=description,
                category_id=category_id,campus=campus
            )
            if not review_passed:
                # 让用户改完立刻重试
                return {
                    "code": 400,
                    "message": "商品信息不符合要求",
                    "data": {"reason": review_reason},
                }
            product = Product(
                seller_id=user_id, name=produce_name, price=price,
                original_price=original_price, description=description,
                category_id=category_id, campus=campus,
                publish_province=publish_province,
                review_status="pending", review_reason=None,
                reviewed_at=None, status="on_sale", view_count=0,
            )
            session.add(product)
            await session.flush()

            product_id = product.id
            image_urls = []

            for image in images:
                result = await upload_image(product_id=product_id,file=image)
                uploaded_names.append(result["data"]["filename"])
                image_url = normalize_image_url(result["data"]["image_url"])
                if not image_url:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="图片服务器返回地址无效"
                    )
                image_urls.append(image_url)
                session.add(ProductImage(product_id=product_id,image_url=image_url))

            await session.commit()
            published = True

            # 加入布隆过滤器、发布计数
            products_bloom.add(product_id)
            app_logger.info(
                "商品发布成功 user_id=%s product_id=%s name=%s",
                user_id,
                product_id,
                produce_name
            )
            # 清理我的商品列表缓存
            await clear_my_product_cache(redis=redis,user_id=user_id)
            try:
                n = await redis.incr(count_key)
                if n == 1 or await redis.ttl(count_key) == -1:
                    await redis.expire(count_key, PUBLISH_WINDOW)
            except Exception:
                redis_logger.exception(
                    "商品发布计数更新失败 user_id=%s product_id=%s",
                    user_id,
                    product_id
                )

            return {
                "code": 200,
                "message": "商品发布成功，等待后台审核",
                "data": {
                    "id": product.id,
                    "name": product.name,
                    "price": str(product.price),
                    "original_price": (
                        str(product.original_price)
                        if product.original_price is not None else None
                    ),
                    "description": product.description,
                    "category_id": product.category_id,
                    "campus": product.campus,
                    "publish_province": product.publish_province,
                    "review_status": product.review_status,
                    "status": product.status,
                    "images": image_urls,
                },
            }


        except Exception:
            await session.rollback()
            # 失败时清理已经写到磁盘的图片 避免留下孤儿文件
            for name in uploaded_names:
                try:
                    await delete_image(product_id, name)
                except Exception:
                    app_logger.exception(
                        "发布失败后清理图片失败 product_id=%s filename=%s",
                        product_id,
                        name
                    )
            raise
        finally:
            await release_publish_lock(
                redis, lock_key, lock_token, keep=5 if published else 0
            )


""" 搜索商品 """
# 每个用户每分钟最多搜 20 次
SEARCH_KEYWORD_MAX_LEN = 50
SEARCH_RATE_LIMIT = 20
SEARCH_RATE_WINDOW = 60

# 搜索结果本地缓存
search_local_cache = TTLCache(maxsize=200,ttl=10)
# 分片锁
search_locks = [asyncio.Lock() for _ in range(32)]

async def check_search_rate_limit(redis, who: str) -> None:
    """ 搜索限流 挡住每次随机换关键词绕过缓存的请求 """
    await check_rate_limit(
        redis,
        f"ratelimit:search:{who}",
        SEARCH_RATE_LIMIT,
        SEARCH_RATE_WINDOW,
        "搜索过于频繁"
    )

async def search_product_from_mysql(product_name: str) -> dict[str, Any]:
    """
    从MySQL中搜索商品
    :param product_name: 商品名称
    :return: 搜索结果
    """
    products_name = product_name.strip()

    if not products_name:
        return {
            "code": 400,
            "message": "搜索关键词不能为空",
            "data": []
        }

    async with async_session_maker() as session:
        stmt = (
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.seller),
                selectinload(Product.images)
            )
            .where(
                Product.name.contains(
                    products_name,
                    autoescape=True
                ),
                Product.status == "on_sale",
                Product.review_status == "approved"
            )
            .order_by(Product.created_at.desc()).limit(50)
        )

        products_class = await session.execute(stmt)
        products = products_class.scalars().all()

        products_list = []

        for product in products:
            products_list.append({
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "original_price": product.original_price,
                "description": product.description,
                "status": product.status,
                "view_count": product.view_count,
                "campus": product.campus,
                "publish_province": product.publish_province,
                "created_at": product.created_at,

                # 统一转换图片地址
                "images": [
                    normalize_image_url(image.image_url)
                    for image in product.images
                ],

                "category": {
                    "id": product.category.id,
                    "key": product.category.key,
                    "name": product.category.name
                } if product.category else None,

                "seller": {
                    "id": product.seller.id,
                    "username": product.seller.username
                } if product.seller else None
            })

        return {
            "code": 200,
            "message": "搜索成功",
            "data": products_list
        }

async def search_product_from_cache(redis,product_name: str,who:str) -> dict[str, int | str | list[Any]] | None | Any:
    """
    搜索商品: 本地缓存 -> Redis -> MySQL
    :param who: 谁搜索的
    :param redis: Redis连接
    :param product_name: 商品名称
    :return: 搜索结果
    """
    keyword = product_name.strip().lower()

    # 不合法的关键词直接返回
    if not keyword:
        return {
            "code":400,
            "message":"搜索关键词不能为空",
            "data":[]
        }
    if len(keyword) > SEARCH_KEYWORD_MAX_LEN:
        return {
            "code": 400,
            "message": "搜索关键词过长",
            "data": []
        }

    await check_search_rate_limit(redis,who)

    digest = hashlib.md5(keyword.encode("utf-8")).hexdigest()
    version = await get_product_cache_version(redis)
    key = f"product:search:v{version}:{digest}"

    # 本地缓存
    data = search_local_cache.get(key)
    if data is not None:
        redis_logger.debug("商品搜索本地缓存命中 keyword=%s", keyword)
        return data

    # Redis
    try:
        cached = await redis.get(key)
        if cached is not None:
            parsed = json.loads(cached)
            if isinstance(parsed, dict) and parsed.get("code") == 200:
                search_local_cache[key] = parsed
                redis_logger.debug("商品搜索Redis缓存命中 keyword=%s", keyword)
                return parsed
            # 内容异常删掉当作没命中
            redis_logger.warning("商品搜索缓存内容异常，已删除 key=%s", key)
            await redis.delete(key)
    except Exception:
        redis_logger.exception("商品搜索Redis缓存读取失败 key=%s", key)

    # MySQL
    async with search_locks[int(digest,16) % len(search_locks)]:
        data = search_local_cache.get(key)
        if data is not None:
            return data

        mysql_logger.debug("商品搜索缓存未命中，查询MySQL keyword=%s", keyword)
        result = await search_product_from_mysql(keyword)
        mysql_logger.debug(
            "商品搜索MySQL返回 keyword=%s type=%s",
            keyword,
            type(result).__name__
        )
        data = jsonable_encoder(result)

        if isinstance(data,dict) and data.get("code") == 200:
            # 缓存
            ttl = 60 + random.randint(0,15) if data["data"] else 30
            try:
                await redis.set(key,json.dumps(data,ensure_ascii=False),ex=ttl)
            except Exception:
                redis_logger.exception(
                    "商品搜索Redis缓存写入失败 key=%s",
                    key
                )
            search_local_cache[key] = data

        return data



""" 我的商品 """
# 我的商品本地缓存
my_products_local_cache = TTLCache(maxsize=1000,ttl=10)

def my_products_ver_key(user_id: int) -> str:
    return f"my_products:ver:{user_id}"

async def get_my_products_version(redis, user_id: int) -> str:
    """ 读取我的商品缓存版本号 没有就是 0 """
    try:
        return await redis.get(my_products_ver_key(user_id)) or "0"
    except Exception:
        return "0"


async def get_my_products(redis,user_id: int,page: int,page_size: int) -> Any | None:
    """
    获取我的商品  本地缓存 -> Redis -> MySQL
    :param redis: Redis连接
    :param page_size: 页数大小
    :param page: 页数
    :param user_id: 用户id
    :return: 所有商品信息
    """
    page = max(1,page)
    page_size = max(1,min(page_size,100))

    # Key
    cache_key = (
        f"my_products:{user_id}:"
        f"page:{page}:size:{page_size}"
    )

    # 本地缓存
    local_data = my_products_local_cache.get(cache_key)

    if local_data is not None:
        redis_logger.debug("我的商品本地缓存命中 key=%s", cache_key)
        return copy.deepcopy(local_data)
    redis_logger.debug("我的商品本地缓存未命中 key=%s", cache_key)

    ver = await get_my_products_version(redis, user_id)
    redis_key = f"my_products:{user_id}:v{ver}:page:{page}:size:{page_size}"
    # Redis
    try:
        cached_data = await redis.get(redis_key)

        if cached_data is not None:
            try:
                result = json.loads(cached_data)

                if isinstance(result,dict) and result.get("code") == 200:
                    redis_logger.debug("我的商品Redis缓存命中 key=%s", redis_key)

                    my_products_local_cache[cache_key] = copy.deepcopy(result)

                    return result

                # 格式不符合预期值 删除
                await redis.delete(redis_key)

            except (json.JSONDecodeError, TypeError):
                await redis.delete(redis_key)

        redis_logger.debug("我的商品Redis缓存未命中 key=%s", redis_key)

    except Exception:
        redis_logger.exception("我的商品Redis缓存读取失败 key=%s", redis_key)

    # MySQL
    async with async_session_maker() as session:

        stmt = (
            select(Product)
            .where(Product.seller_id == user_id)
            .options(
                selectinload(Product.category),
                selectinload(Product.seller),
                selectinload(Product.images)
            )
            .order_by(Product.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        products_result = await session.execute(stmt)
        products = products_result.scalars().all()

        count_stmt = select(func.count(Product.id)).where(
            Product.seller_id == user_id
        )

        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        products_list = []

        for product in products:
            products_list.append({
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "original_price": product.original_price,
                "description": product.description,
                "status": product.status,
                "review_status": product.review_status,
                "view_count": product.view_count,
                "campus": product.campus,
                "publish_province": product.publish_province,
                "created_at": product.created_at,
                "seller_id": product.seller_id,

                "images": [
                    normalize_image_url(image.image_url)
                    for image in product.images
                ],

                "category": {
                    "id": product.category.id,
                    "key": product.category.key,
                    "name": product.category.name
                } if product.category else None,

                "seller": {
                    "id": product.seller.id,
                    "username": product.seller.username
                } if product.seller else None
            })

        result = {
            "code": 200,
            "message": "获取我的商品成功",
            "data": products_list,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    # 写入Redis
    try:
        cache_data = json.dumps(
            jsonable_encoder(result),
            ensure_ascii=False
        )
        ttl = 60 + random.randint(0, 15) if products_list else 30

        await redis.set(
            redis_key,
            cache_data,
            ex=ttl
        )
        redis_logger.debug(
            "我的商品Redis缓存写入成功 key=%s ttl=%s",
            redis_key,
            ttl
        )
    except Exception:
        redis_logger.exception("我的商品Redis缓存写入失败 key=%s", redis_key)

    # 写入本地缓存
    my_products_local_cache[cache_key] = copy.deepcopy(result)

    redis_logger.debug("我的商品本地缓存写入成功 key=%s", cache_key)

    return result

# 我的商品详细信息本地缓存
my_product_info_local_cache = TTLCache(maxsize=1000,ttl=10)

async def get_my_product_info(redis,user_id: int,product_id: int) -> Any | None:
    """
    获取本人商品详细信息
    与商品列表接口不同，这里不限制商品状态，
    审核中/已下架/已售出的商品卖家本人都能查看和编辑。
    :param redis: Redis连接
    :param user_id: 用户id
    :param product_id: 商品id
    :return: 商品详细信息
    """
    # 缓存键
    cache_key = f"my_product_info:{user_id}:{product_id}"

    # 本地缓存
    local_data = my_product_info_local_cache.get(cache_key)

    if local_data is not None:
        redis_logger.debug("本人商品详情本地缓存命中 key=%s", cache_key)
        return copy.deepcopy(local_data)
    redis_logger.debug("本人商品详情本地缓存未命中 key=%s", cache_key)

    # Redis
    try:
        cached_data = await redis.get(cache_key)

        if cached_data is not None:
            result = json.loads(cached_data)

            redis_logger.debug("本人商品详情Redis缓存命中 key=%s", cache_key)

            # 回填本地缓存
            my_product_info_local_cache[cache_key] = copy.deepcopy(result)

            return result
    except Exception:
        redis_logger.exception("本人商品详情Redis缓存读取失败 key=%s", cache_key)


    # MySQL
    async with async_session_maker() as session:
        stmt = (select(Product).where(Product.id == product_id,
                Product.seller_id == user_id
            )
            .options(
                selectinload(Product.category),
                selectinload(Product.seller),
                selectinload(Product.images)
            )
        )

        product_class = await session.execute(stmt)
        product = product_class.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在或无权查看"
            )

        result = {
            "code": 200,
            "message": "获取成功",
            "data": {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "original_price": product.original_price,
                "description": product.description,
                "status": product.status,
                "review_status": product.review_status,
                "review_reason": product.review_reason,
                "view_count": product.view_count,
                "campus": product.campus,
                "publish_province": product.publish_province,
                "created_at": product.created_at,
                "seller_id": product.seller_id,

                "images": [
                    normalize_image_url(image.image_url)
                    for image in product.images
                ],

                "category": {
                    "id": product.category.id,
                    "key": product.category.key,
                    "name": product.category.name
                } if product.category else None,

                "seller": {
                    "id": product.seller.id,
                    "username": product.seller.username
                } if product.seller else None
            }
        }

        # 写入 Redis
        try:
            cache_data = json.dumps(
                jsonable_encoder(result),
                ensure_ascii=False
            )

            await redis.set(
                cache_key,
                cache_data,
                ex=300 + random.randint(0,100)
            )

            redis_logger.debug("本人商品详情Redis缓存写入成功 key=%s", cache_key)

        except Exception:
            redis_logger.exception("本人商品详情Redis缓存写入失败 key=%s", cache_key)

        # 写入本地缓存
        my_product_info_local_cache[cache_key] = result

        redis_logger.debug("本人商品详情本地缓存写入成功 key=%s", cache_key)

        return result



""" 我的收藏 """
def favorites_key(user_id: int) -> str:
    return f"user:favorites:{user_id}"

async def get_my_favorite(redis,user_id: int) -> list[Any]:
    """
    获取我的收藏
    :param redis: Redis
    :param user_id: 用户id
    :return: 用户收藏
    """
    key = favorites_key(user_id)

    # Redis
    try:
        cached = await redis.get(key)
        if cached is not None:
            data = json.loads(cached)
            if isinstance(data,list):
                redis_logger.debug("收藏列表Redis缓存命中 user_id=%s", user_id)
                return data
            redis_logger.warning("收藏列表缓存内容异常 user_id=%s", user_id)
    except Exception:
        redis_logger.exception("收藏列表Redis缓存读取失败 user_id=%s", user_id)

    # MySQL
    mysql_logger.debug("收藏列表缓存未命中，查询MySQL user_id=%s", user_id)
    async with async_session_maker() as session:
        stmt = (
            select(Favorite.product_id)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        ).limit(500)
        my_favorite_class = await session.execute(stmt)
        my_favorites = list(my_favorite_class.scalars().all())

    # 写入Redis
    try:
        await redis.set(key,json.dumps(my_favorites),ex=600 + random.randint(0,300))
    except Exception:
        redis_logger.exception("收藏列表Redis缓存写入失败 user_id=%s", user_id)
    return my_favorites

async def favorite_produce(redis,user_id: int,product_id: int) -> None:
    """
    收藏商品
    :param redis: Redis
    :param user_id: 用户id
    :param product_id: 商品id
    :return: None
    """
    # 布隆过滤器
    if product_id not in products_bloom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品不存在"
        )

    async with async_session_maker() as session:
        product_exists = await session.scalar(
            select(Product.id).where(
                Product.id == product_id
            )
        )

        if product_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )

        favorite_id = await session.scalar(
            select(Favorite.id).where(
                Favorite.user_id == user_id,
                Favorite.product_id == product_id
            )
        )
        if favorite_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品已收藏"
            )
        session.add(Favorite(user_id=user_id,product_id=product_id))

        try:
            await session.commit()
        except IntegrityError:
            # 连续点击两下
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品已收藏"
            )
    app_logger.info(
        "商品收藏成功 user_id=%s product_id=%s",
        user_id,
        product_id
    )
    # 删除收藏缓存
    try:
        await redis.delete(favorites_key(user_id))
    except Exception:
        redis_logger.exception("收藏商品后清理缓存失败 user_id=%s", user_id)

async def unfavorite_produce(redis,user_id: int,product_id: int) -> None:
    """
    取消收藏商品

    :param redis: Redis
    :param user_id: 用户id
    :param product_id: 商品id
    :return: None
    """
    async with async_session_maker() as session:
        stmt = select(Favorite).where(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        )

        favorite_class = await session.execute(stmt)
        favorite = favorite_class.scalar_one_or_none()

        if favorite is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品尚未收藏"
            )

        await session.delete(favorite)
        await session.commit()
    app_logger.info(
        "取消收藏成功 user_id=%s product_id=%s",
        user_id,
        product_id
    )

    # 删除收藏缓存
    try:
        await redis.delete(favorites_key(user_id))
    except Exception:
        redis_logger.exception("取消收藏后清理缓存失败 user_id=%s", user_id)



""" 商品分类列表 """
# 本地缓存
product_category_list_local_cache = TTLCache(maxsize=1000,ttl=10)

def product_category_lis_key() -> str:
    return "product:categories"

async def get_products_category(redis) -> dict[str, Any]:
    """
    获取商品分类列表
    :return: 商品分类列表
    """
    # 本地缓存
    categories_data = product_category_list_local_cache.get(product_category_lis_key())

    if categories_data is not None:
        redis_logger.debug("商品分类本地缓存命中")
        return {
            "code":200,
            "message":"获取成功",
            "data":categories_data
        }

    # Redis
    try:
        redis_data: str | bytes | None = await redis.get(product_category_lis_key())
    except Exception:
        redis_logger.exception("商品分类Redis缓存读取失败")
        redis_data = None

    if redis_data is not None:
        # 写入本地缓存
        try:
            categories_data: list[dict[str, Any]] = json.loads(redis_data)
            redis_logger.debug("商品分类Redis缓存命中")
            product_category_list_local_cache[product_category_lis_key()] = categories_data
            return {
                "code": 200,
                "message": "获取分类成功",
                "data": categories_data
            }
        except Exception:
            redis_logger.exception("商品分类缓存内容解析失败")

    # MySQL
    mysql_logger.debug("商品分类缓存未命中，查询MySQL")
    async with async_session_maker() as session:
        stmt = (
            select(Category)
            .order_by(
                Category.sort_order.asc(),
                Category.id.asc()
            )
        )
        categories_class = await session.execute(stmt)
        categories = categories_class.scalars().all()
        categories_data = [
            {"id":c.id,
             "key":c.key,
             "name":c.name,
             "sort_order":c.sort_order}
            for c in categories
        ]

    # 写入Redis
    try:
        await redis.set(product_category_lis_key(),json.dumps(categories_data,ensure_ascii=False),ex = 3600)
    except Exception:
        redis_logger.exception("商品分类Redis缓存写入失败")

    # 写入本地缓存
    product_category_list_local_cache[product_category_lis_key()] = categories_data

    return {
        "code": 200,
        "message": "获取分类成功",
        "data": categories_data
    }



""" 获取他人商品 """
# 他人商品列表本地缓存
other_products_local_cache = TTLCache(maxsize=1000,ttl=10)

# 分片锁
others_products_locks = [asyncio.Lock()for _ in range(32)]

def other_products_cache_key(
    other_user_id: int,
    page: int,
    page_size: int,
    version: str | int = "0"
) -> str:
    """ 获取他人商品列表缓存key """
    return f"others_products:v{version}:{other_user_id}:{page}:{page_size}"

async def get_others_products(redis,other_user_id: int,page: int,page_size: int) -> Any | None:
    """
    获取他人商品
    :param redis: Redis连接
    :param other_user_id: 用户id
    :param page: 页数
    :param page_size: 页数大小
    :return: 其他用户商品
    """
    user = await get_user_cached(redis, other_user_id)  # ← 新增
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    version = await get_product_cache_version(redis)
    cache_key = other_products_cache_key(
        other_user_id,
        page,
        page_size,
        version
    )

    # 本地缓存
    local_data = other_products_local_cache.get(cache_key)

    if local_data is not None:
        redis_logger.debug(
            "他人商品列表本地缓存命中 seller_id=%s page=%s size=%s",
            other_user_id,
            page,
            page_size
        )
        return local_data

    # Redis
    try:
        redis_data:str | bytes | None = await redis.get(cache_key)
        if redis_data is not None:
            redis_logger.debug("他人商品列表Redis缓存命中 key=%s", cache_key)

            result = json.loads(redis_data)

            # 写入本地缓存
            other_products_local_cache[cache_key] = result

            return result
    except Exception:
        redis_logger.exception("他人商品列表Redis缓存读取失败 key=%s", cache_key)

    # Redis未命中 获取分片锁
    lock = others_products_locks[hash(cache_key) % len(others_products_locks)]

    async with lock:
        # 双重检查
        local_data = other_products_local_cache.get(cache_key)
        if local_data is not None:
            return local_data

        try:
            redis_data = await redis.get(cache_key)
            if redis_data is not None:
                result = json.loads(redis_data)
                other_products_local_cache[cache_key] = result
                return result
        except Exception:
            redis_logger.exception(
                "他人商品列表等锁后Redis读取失败 key=%s",
                cache_key
            )

        # MySQL
        mysql_logger.debug("他人商品列表缓存未命中，查询MySQL key=%s", cache_key)
        async with async_session_maker() as session:
            stmt = (select(Product).where(Product.seller_id == other_user_id,
                                          Product.status == "on_sale",
                                          Product.review_status == "approved"
                                          ).options(
                selectinload(Product.images)
            ).order_by(
                Product.created_at.desc(),
                Product.id.desc()
            ).offset((page - 1) * page_size).limit(page_size)
                    )

            count_stmt = select(func.count(Product.id)).where(
                Product.seller_id == other_user_id,
                Product.status == "on_sale",
                Product.review_status == "approved"
            )

            total = (await session.execute(count_stmt)).scalar_one()

            products_result = await session.execute(stmt)

            products = products_result.scalars().all()

            result = {
                "code": 200,
                "message": "获取用户商品成功",
                "data": [
                    {
                        "id": product.id,
                        "name": product.name,
                        "price": float(product.price),
                        "campus": product.campus,
                        "publish_province": product.publish_province,
                        "created_at": product.created_at.isoformat(),

                        "images": [
                            normalize_image_url(image.image_url)
                            for image in product.images
                        ]
                    }
                    for product in products
                ],
                "total": total,
                "page": page,
                "page_size": page_size
            }

    # 写入Redis
    try:
        await redis.set(cache_key,json.dumps(result, ensure_ascii=False),
            ex=60 + random.randint(0, 15))
    except Exception:
        redis_logger.exception("他人商品列表Redis缓存写入失败 key=%s", cache_key)

    # 写入本地缓存
    other_products_local_cache[cache_key] = result

    return result



""" 删除商品 """
async def clear_my_product_cache(redis,user_id: int,product_id: int | None = None) -> None:
    """
    清理卖家的我的商品列表缓存和本人商品详情缓存。
    product_id: 指定商品 ID：同时清理该商品的本人详情缓存。
    None：只清理该卖家的我的商品列表缓存。
    """

    # 先清理本地缓存 避免 Redis 出错时本地仍然返回旧数据
    for key in list(my_products_local_cache.keys()):
        if key.startswith(f"my_products:{user_id}:"):
            my_products_local_cache.pop(key, None)

    if product_id is not None:
        info_key = f"my_product_info:{user_id}:{product_id}"
        my_product_info_local_cache.pop(info_key, None)

    # 清理 Redis
    try:
        pipe = redis.pipeline(transaction=True)
        pipe.incr(my_products_ver_key(user_id))              # 版本号 +1,旧列表缓存作废
        pipe.expire(my_products_ver_key(user_id), 7 * 24 * 3600)
        if product_id is not None:
            pipe.delete(f"my_product_info:{user_id}:{product_id}")
        await pipe.execute()
        redis_logger.debug(
            "我的商品缓存版本已刷新 user_id=%s product_id=%s",
            user_id,
            product_id
        )
    except Exception:
        redis_logger.exception(
            "我的商品缓存清理失败 user_id=%s product_id=%s",
            user_id,
            product_id
        )

async def delete_my_product(redis,user_id: int,product_id: int) -> dict[str, Any]:
    """
    删除商品
    :param redis: Redis
    :param user_id: 用户id
    :param product_id: 商品id
    :return: 商品信息
    """
    async with async_session_maker() as session:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.seller_id == user_id
        ).with_for_update()

        product_class = await session.execute(stmt)
        product = product_class.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品不存在或无权删除"
            )

        order_stmt = select(Order).where(
            Order.product_id == product_id
        )

        order_class = await session.execute(order_stmt)
        orders = order_class.scalars().all()

        now = datetime.datetime.now()
        six_months_ago = get_six_months_ago(now)

        for order in orders:
            # 待完成 买家还没收货 和已收货 等卖家确认完成 都是进行中的订单
            if order.status in ("pending", "received"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="该商品存在进行中的订单，暂时不能删除"
                )

            if order.status == "completed":
                if order.completed_at is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="该商品存在已完成但缺少完成时间的订单，暂时不能删除"
                    )

                if order.completed_at > six_months_ago:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="该商品存在未满6个月的已完成订单，暂时不能删除"
                    )

        # 先记下图片文件名，数据库提交成功之后再删磁盘上的文件
        # 这样即使提交失败，数据库里的图片记录也不会指向已被删除的文件
        image_stmt = select(ProductImage).where(
            ProductImage.product_id == product_id
        )

        images_class = await session.execute(image_stmt)
        images = images_class.scalars().all()

        image_file_names = [
            get_image_filename(image.image_url)
            for image in images
        ]

        # 先删除聊天消息和会话
        # chat_conversations 通过 order_id 关联订单
        order_ids = (
            await session.execute(
                select(Order.id).where(
                    Order.product_id == product_id
                )
            )
        ).scalars().all()

        if order_ids:
            conversation_ids = (
                await session.execute(
                    select(ChatConversation.id).where(
                        ChatConversation.order_id.in_(order_ids)
                    )
                )
            ).scalars().all()

            if conversation_ids:
                await session.execute(
                    delete(ChatMessage).where(
                        ChatMessage.conversation_id.in_(
                            conversation_ids
                        )
                    )
                )

                await session.execute(
                    delete(ChatConversation).where(
                        ChatConversation.id.in_(conversation_ids)
                    )
                )

        # 查询所有收藏过该商品的用户 ID
        favorite_user_ids = (
            await session.execute(
                select(Favorite.user_id).where(
                    Favorite.product_id == product_id
                )
            )
        ).scalars().all()

        # 删除收藏记录
        await session.execute(
            delete(Favorite).where(
                Favorite.product_id == product_id
            )
        )

        # 删除订单
        await session.execute(
            delete(Order).where(
                Order.product_id == product_id
            )
        )

        # 删除商品图片记录
        await session.execute(
            delete(ProductImage).where(
                ProductImage.product_id == product_id
            )
        )

        # 删除商品
        await session.delete(product)

        await session.commit()

        for file_name in image_file_names:
            try:
                await delete_image(
                    product_id=product_id,
                    file_name=file_name
                )
            except Exception:
                app_logger.exception(
                    "商品删除后清理图片文件失败 product_id=%s filename=%s",
                    product_id,
                    file_name
                )


        app_logger.info(
            "商品删除成功 product_id=%s seller_id=%s",
            product_id,
            user_id
        )

        # 清理缓存
        try:
            await invalidate_product(redis,product_id,user_id)

            # 清理所有收藏过该商品的用户的收藏缓存
            if favorite_user_ids:
                await redis.delete(*[favorites_key(uid) for uid in favorite_user_ids])
        except Exception:
            app_logger.exception(
                "删除商品后的缓存清理失败 product_id=%s",
                product_id
            )

        return {
            "code": 200,
            "message": "删除成功"
        }



""" 修改商品 """
async def invalidate_product(redis, product_id: int, seller_id: int | None = None) -> None:
    """ 商品状态或内容变化后调用 """
    detail_local_cache.pop(product_id, None)
    # 这三个本地缓存很小 TTL 只有 10~15 秒 整体清掉即可
    list_local_cache.clear()
    search_local_cache.clear()
    other_products_local_cache.clear()

    try:
        await redis.delete(
            detail_cache_key(product_id),
            state_cache_key(product_id)
        )
        await bump_product_cache_version(redis)
    except Exception:
        redis_logger.exception("商品详情缓存删除失败 product_id=%s", product_id)

    # 同时清卖家自己的 我的商品 缓存
    if seller_id is not None:
        await clear_my_product_cache(redis, seller_id, product_id)
async def change_my_product(redis,user_id: int,product_id: int,product_name: str | None = None,
price: Decimal | None = None,original_price: Decimal | None = None,description: str | None = None,
category_id: int | None = None,campus: str | None = None,) -> dict[str, Any]:
    """
    修改商品信息，修改后重新进入待审核状态
    """
    async with async_session_maker() as session:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.seller_id == user_id
        ).with_for_update()

        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在"
            )

        if product.status == "sold":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已售出的商品不能修改"
            )

        # 有进行中的订单时不能修改，避免买家下单后卖家改价格 / 描述
        active_order_id = await session.scalar(
            select(Order.id).where(
                Order.product_id == product_id,
                Order.status.in_(["pending", "received"])
            ).limit(1)
        )

        if active_order_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品有进行中的订单，暂时不能修改"
            )

        # 先合并出修改后的最终值 再统一校验
        new_name = (
            product.name
            if product_name is None
            else product_name.strip()
        )

        new_price = (
            product.price
            if price is None
            else price
        )

        new_original_price = (
            product.original_price
            if original_price is None
            else original_price
        )

        new_description = (
            product.description
            if description is None
            else description.strip()
        ) or ""

        new_category_id = (
            product.category_id
            if category_id is None
            else category_id
        )

        new_campus = (
            product.campus
            if campus is None
            else campus.strip()
        ) or ""

        review_passed, review_reason = await validate_product(
            produce_name=new_name,
            price=new_price,
            original_price=new_original_price,
            description=new_description,
            category_id=new_category_id,
            campus=new_campus
        )

        if not review_passed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=review_reason
            )

        if new_category_id != product.category_id:
            category_exists = await session.scalar(
                select(Category.id).where(
                    Category.id == new_category_id
                )
            )

            if category_exists is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="商品分类不存在"
                )

        changed = False

        if product.name != new_name:
            product.name = new_name
            changed = True

        if product.price != new_price:
            product.price = new_price
            changed = True

        if product.original_price != new_original_price:
            product.original_price = new_original_price
            changed = True

        if (product.description or "") != new_description:
            product.description = new_description
            changed = True

        if product.category_id != new_category_id:
            product.category_id = new_category_id
            changed = True

        if (product.campus or "") != new_campus:
            product.campus = new_campus
            changed = True

        if changed:
            # 被驳回的商品修改后重新提交审核：回到「待审核」（对外仍不可见），
            # 审核通过后才会重新上架
            product.status = status_after_resubmit(product.status, product.review_status)
            product.review_status = "pending"
            product.review_reason = None
            product.reviewed_at = None
            product.reviewed_by = None

        await session.commit()
        await session.refresh(product)

        result = {
            "code": 200,
            "message": (
                "商品修改成功，等待重新审核"
                if changed
                else "商品信息未发生变化"
            ),
            "data": {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "original_price": product.original_price,
                "description": product.description,
                "category_id": product.category_id,
                "campus": product.campus,
                "publish_province": product.publish_province,
                "status": product.status,
                "review_status": product.review_status
            }
        }

    # commit 成功后清理缓存
    if changed:
        await invalidate_product(redis,product_id,user_id)
        app_logger.info(
            "商品信息修改成功 product_id=%s seller_id=%s",
            product_id,
            user_id
        )
    return result



""" 商品标记售出 """
async def mark_as_sold(redis,user_id: int,product_id: int) -> dict[str, Any]:
    """
    商品标记售出

    :param redis: Redis
    :param user_id: 用户id
    :param product_id: 商品id
    :return: 商品信息
    """
    async with async_session_maker() as session:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.seller_id == user_id,
            Product.status == "on_sale",
            Product.review_status == "approved"
        ).with_for_update()

        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在或当前状态不允许标记售出"
            )

        product.status = "sold"
        product.sold_at = datetime.datetime.now()

        await session.commit()
        await session.refresh(product)

        response = {
            "code": 200,
            "message": "商品已标记为售出",
            "data": {
                "id": product.id,
                "status": product.status,
                "review_status": product.review_status,
                "sold_at": product.sold_at
            }
        }

    # commit成功之后清缓存 删掉公开详情 游客不能再看到这个商品
    await invalidate_product(redis, product_id,user_id)
    app_logger.info(
        "商品标记售出 product_id=%s seller_id=%s",
        product_id,
        user_id
    )

    return response





























