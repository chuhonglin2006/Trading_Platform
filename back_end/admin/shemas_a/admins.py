"""管理员接口模型类"""
from typing import Literal

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
    captcha_id: str = Field(min_length=1, max_length=64)
    captcha_code: str = Field(min_length=1, max_length=8)

class AdminCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12)
    role: Literal["admin", "super_admin"] = "admin"

class AdminRoleRequest(BaseModel):
    role: Literal["admin", "super_admin"]

class AdminStatusRequest(BaseModel):
    status: Literal["normal", "banned"]