""" 订单自动收货 """
import asyncio

from crud_1.orders import auto_complete_orders, auto_receive_orders

from tools_1.logger import get_logger

logger = get_logger(__name__, "python")


async def order_auto_receive_loop(redis) -> None:
    """
    订单自动处理：自动收货 + 自动完成
    :param redis: Redis（自动完成订单后需要清理商品缓存）
    :return:None
    """
    while True:
        # 两个任务分开捕获异常，一个失败不影响另一个
        try:
            result = await auto_receive_orders()
            count = result.get("data", {}).get("count", 0)
            if count:
                logger.info("订单自动收货完成 count=%s", count)
        except Exception:
            logger.exception("订单自动收货任务执行失败")

        try:
            result = await auto_complete_orders(redis)
            count = result.get("data", {}).get("count", 0)
            if count:
                logger.info("订单自动完成 count=%s", count)
        except Exception:
            logger.exception("订单自动完成任务执行失败")

        await asyncio.sleep(30)   # 时间精度要求不高，30 秒足够