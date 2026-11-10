""" 订单自动收货 """
import asyncio
from crud_1.orders import auto_receive_orders
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")



async def order_auto_receive_loop() -> None:
    """
    订单自动收货
    :return:None
    """
    while True:
        try:
            result = await auto_receive_orders()
            count = result.get("data", {}).get("count", 0)
            if count:
                logger.info("订单自动收货完成 count=%s", count)
        except Exception:
            logger.exception("订单自动收货任务执行失败")
        await asyncio.sleep(30)
