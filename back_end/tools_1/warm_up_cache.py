""" 预热Redis、布隆过滤器 """
import asyncio
import json
import random

from database_1.mysql_config import async_session_maker
from fastapi.encoders import jsonable_encoder
from modles_1.category import Category
from modles_1.products import Product
from modles_1.user import User
from pybloom_live import ScalableBloomFilter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tools_1.add_ttl_for_products import make_products_ttl
from tools_1.logger import get_logger
from tools_1.product_cache_version import get_product_cache_version
from tools_1.product_serializer import build_product_detail

mysql_logger = get_logger(__name__, "mysql")
redis_logger = get_logger(__name__, "redis")



# 商品布隆过滤器
products_bloom = ScalableBloomFilter(
    error_rate=0.01
)
# 用户名布隆过滤器
user_name_bloom = ScalableBloomFilter(
    error_rate=0.01
)


def normalize_username(name: str) -> str:
    """ add_all_user_name_to_bloom函数工具函数 """
    return name.strip().lower()

async def add_all_user_name_to_bloom() ->None:
    """ 将所有用户名添加到布隆过滤器中 """

    last_user_id = 0 # 游标
    total_users = 0

    async with async_session_maker() as session:
        while True:
            stmt = select(User.id,User.username).where(
                User.id > last_user_id
            ).order_by(User.id).limit(500)

            rows = (await session.execute(stmt)).all()
            if not rows:
                break

            for _,user_name in rows:
                user_name_bloom.add(normalize_username(user_name))
                total_users += 1

            last_user_id = rows[-1][0]
            await asyncio.sleep(0)
    mysql_logger.info("用户名布隆过滤器加载完成 users=%s", total_users)

async def add_all_products_id_to_bloom() -> None:
    """ 初始化布隆过滤器 """

    # 游标
    last_id = 0
    total_products = 0

    async with async_session_maker() as session:
        while True:
            stmt = select(Product.id).where(
                Product.id > last_id
            ).order_by(Product.id).limit(500)

            result = await session.execute(stmt)

            rows = result.scalars().all()
            if not rows:
                break

            # 存入布隆过滤器
            for product_id in rows:
                products_bloom.add(product_id)
                total_products += 1

            await asyncio.sleep(0)

            last_id = rows[-1]
    mysql_logger.info(
        "商品ID布隆过滤器加载完成 products=%s",
        total_products
    )

async def warming_up_products(redis) -> None:
    """ 预热商品分类、热门商品缓存 """

    async with async_session_maker() as session:

        # 商品分类
        categories = (await session.execute(
            select(Category).order_by(Category.sort_order,Category.id)
        )).scalars().all()
        category_data = [
            {"id":category.id,"key":category.key,"name":category.name,"sort_order":category.sort_order}
            for category in categories
        ]

        # 热门商品
        products = (await session.execute(
            select(Product).where(Product.status == "on_sale",Product.review_status == "approved").options(
                selectinload(Product.images),selectinload(Product.category),selectinload(Product.seller)
            ).order_by(
                Product.view_count.desc()).limit(300)
        )).scalars().all()
        # 转换为字典
        products_dict = [(
            product.id,
            build_product_detail(product)
        )for product in products]

    # 使用pipeline一次性写入
    pipe = redis.pipeline()
    pipe.set(
        "product:categories",
        json.dumps(category_data,ensure_ascii=False),
        ex=3600 + random.randint(0,1800)
    )
    for pid,data in products_dict:
        pipe.set(
            f"product:detail:{pid}",
            json.dumps(data,ensure_ascii=False),
            ex=make_products_ttl()
        )
    await pipe.execute()
    redis_logger.info(
        "商品分类和热门商品缓存预热完成 categories=%s products=%s",
        len(category_data),
        len(products_dict)
    )

def list_cache_key(
    page: int,
    page_size: int,
    version: str | int = "0"
) -> str:
    """ warming_up_products_list函数的工具函数 """
    return f"product:list:v{version}:{page}:{page_size}"

async def warming_up_products_list(redis,page_size:int) -> None:
    """ 预热首页前1~5页列表 """
    from crud_1.produces import get_products_list_from_mysql  # 局部导入 防止冲突
    MAX_CACHE_PAGE = 5 # 只存前5页
    MAX_CACHE_PAGE_SIZE = 50 # page_size上限


    if page_size > MAX_CACHE_PAGE_SIZE:
        return
    pages_data = []

    for page in range(1,MAX_CACHE_PAGE + 1):
        result = await get_products_list_from_mysql(page,page_size)
        pages_data.append((page,jsonable_encoder(result)))

        if page * page_size >= result["total"]:
            break

    version = await get_product_cache_version(redis)
    pipe = redis.pipeline()
    for page,data in pages_data:
        pipe.set(
            list_cache_key(page, page_size, version),
            json.dumps(data,ensure_ascii=False),
            ex=60 + random.randint(0,15)
        )
    await pipe.execute()
    redis_logger.info(
        "商品列表缓存预热完成 pages=%s page_size=%s version=%s",
        len(pages_data),
        page_size,
        version
    )







async def warming_blooms_main() -> None:
    """ 布隆过滤器初始化主函数 """
    # 初始化用户名布隆过滤器
    await add_all_user_name_to_bloom()
    # 初始化商品ID布隆过滤器
    await add_all_products_id_to_bloom()

async def warming_redis_main(redis) -> None:
    """ Redis预热主函数 """

    # 预热商品分类、热门商品缓存
    await warming_up_products(redis)
    # 预热首页前1~5页列表
    await warming_up_products_list(redis,page_size=20)





























































































































