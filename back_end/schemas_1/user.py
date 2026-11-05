"""用户路由的模型类"""
from pydantic import BaseModel, EmailStr, Field




"""用户登录模型类"""
class Logion(BaseModel):
    user_email:str
    password:str

"""发送验证码模型类"""
class SendCodeRequest(BaseModel):
    user_email:EmailStr

"""用户注册模型类"""
class Register(BaseModel):
    username:str
    student_id:str
    email:EmailStr
    code:str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$",
    )
    password:str
