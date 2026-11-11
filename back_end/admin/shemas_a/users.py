"""管理界面用户模型类"""
from typing import Literal

from pydantic import BaseModel


class UserStatusRequest(BaseModel):
    status: Literal["normal", "banned"]