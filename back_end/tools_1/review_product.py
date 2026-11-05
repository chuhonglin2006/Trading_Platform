"""审核商品的信息"""
from decimal import Decimal


async def validate_product(produce_name: str,
    price: Decimal,
    original_price: Decimal | None,
    description: str,category_id: int,campus: str,) -> tuple[bool, str | None]:
    """
    审核商品信息
    :param produce_name:商品名称
    :param price:商品价格
    :param original_price:商品原价
    :param description:商品描述
    :param category_id:分类 ID
    :param campus:校区
    :return:审核是否通过,审核原因
    """
    if not produce_name.strip():
        return False, "商品名称不能为空"

    if len(produce_name) > 100:
        return False, "商品名称不能超过100个字符"

    if price <= 0:
        return False, "商品价格必须大于0"

    if original_price is not None:
        if original_price <= 0:
            return False, "商品原价必须大于0"

    if not description.strip():
        return False, "商品描述不能为空"

    if len(description) > 5000:
        return False, "商品描述不能超过5000个字符"

    if category_id <= 0:
        return False, "商品分类无效"

    if not campus.strip():
        return False, "校区不能为空"

    return True, None