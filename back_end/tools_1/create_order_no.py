"""自动生成订单号"""
import uuid


def create_order_number() -> str:
    return uuid.uuid4().hex
