"""生命周期函数。"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from database_1.mysql_config import async_engine
from database_1.redis_config import redis_close, redis_content
from tools_1.flush_view_counts import flush_view_counts, view_count_flush_loop
from tools_1.logger import get_logger
from tools_1.order_auto_receive_loop import order_auto_receive_loop
from tools_1.warm_up_cache import warming_blooms_main, warming_redis_main
from tools_1.ip_region import (
    backfill_product_publish_provinces,
    ensure_product_region_schema,
)
from tools_1.add_ip_data_to_memory import init_ip_region_searcher


app_logger = get_logger(__name__, "python")
redis_logger = get_logger(__name__, "redis")
mysql_logger = get_logger(__name__, "mysql")






@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用启动和关闭过程。"""
    app_logger.info("校园二手交易平台后端正在启动")
    app.state.redis = await redis_content()

    order_task = None
    warm_task = None
    view_task = None
    region_task = None

    try:
        try:
            init_ip_region_searcher()
        except Exception:
            app_logger.exception(
                "IP2Region 数据库加载失败，IP 地区将显示为未知"
            )

        try:
            async with async_engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            mysql_logger.info("MySQL连接成功")
        except Exception:
            mysql_logger.exception("MySQL连接失败")
            raise

        await ensure_product_region_schema()
        region_task = asyncio.create_task(
            backfill_product_publish_provinces(app.state.redis)
        )

        await warming_blooms_main()
        app_logger.info("布隆过滤器初始化完成")

        order_task = asyncio.create_task(order_auto_receive_loop())
        app_logger.info("订单自动处理后台任务已启动")

        view_task = asyncio.create_task(
            view_count_flush_loop(app.state.redis)
        )
        redis_logger.info("浏览量刷新后台任务已启动")

        async def warm_up():
            try:
                await warming_redis_main(app.state.redis)
                redis_logger.info("Redis缓存预热完成")
            except Exception:
                redis_logger.exception("Redis缓存预热失败，已跳过")

        warm_task = asyncio.create_task(warm_up())
        app_logger.info("校园二手交易平台后端启动完成")
        yield

    finally:
        app_logger.info("校园二手交易平台后端正在关闭")

        tasks = [
            task
            for task in (order_task, warm_task, view_task, region_task)
            if task is not None
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        app_logger.info("后台任务已停止")

        try:
            await flush_view_counts(app.state.redis)
            await redis_close(app.state.redis)
        finally:
            await async_engine.dispose()
            mysql_logger.info("MySQL连接池已关闭")
            app_logger.info("校园二手交易平台后端已关闭")
