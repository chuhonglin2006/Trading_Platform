"""评价请求模型"""
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5, description="1~5 星")
    comment: str | None = Field(default=None, max_length=200, description="评价留言，可不填")
