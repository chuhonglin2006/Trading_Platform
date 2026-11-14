"""用户路由的模型类"""
from pydantic import BaseModel, EmailStr, Field,field_validator

"""用户登录模型类"""
class Login(BaseModel):
    user_email: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=1, max_length=64)

"""发送验证码模型类"""
class SendCodeRequest(BaseModel):
    user_email:EmailStr
    captcha_id:str = Field(min_length=1, max_length=64)
    captcha_code:str = Field(min_length=1, max_length=8)

"""用户注册模型类"""
class Register(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    student_id: str = Field(min_length=9, max_length=9)
    email: EmailStr
    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$",
    )
    password: str = Field(min_length=6, max_length=64)

"""刷新token / 退出登录模型类"""
class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=128)

"""重置密码模型类"""
class ResetPassword(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    new_password: str = Field(min_length=6, max_length=64)

    @field_validator("new_password")
    @classmethod
    def _check_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:   # bcrypt 只取前 72 字节
            raise ValueError("密码过长")
        return v