"""管理商品接口模型类"""
from typing import Literal
from pydantic import BaseModel, Field




class ProductReviewRequest(BaseModel):
    review_status: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=500)

class ProductStatusRequest(BaseModel):
    status: Literal["off_sale"]
