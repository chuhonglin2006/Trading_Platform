"""管理员公告请求模型。"""

from pydantic import BaseModel, Field


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class AnnouncementUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
