"""管理员接口模型类"""
from pydantic import BaseModel,Field
from typing import Literal

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12)
    role: Literal["admin", "super_admin"] = "admin"

class AdminRoleRequest(BaseModel):
    role: Literal["admin", "super_admin"]

class AdminStatusRequest(BaseModel):
    status: Literal["normal", "banned"]