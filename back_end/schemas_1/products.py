"""商品路由的模型类"""
from decimal import Decimal

from pydantic import BaseModel


class ProductUpdate(BaseModel):
    product_name: str | None = None
    price: Decimal | None = None
    original_price: Decimal | None = None
    description: str | None = None
    category_id: int | None = None
    campus: str | None = None