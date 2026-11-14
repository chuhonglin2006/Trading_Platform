"""用户接口"""
from typing import Any

from crud_1.users import (
    get_seller_public_info,
    get_user_info,
    refresh_tokens,
    revoke_refresh_token,
    send_code,
    user_login,
    user_register,
)
from database_1.redis_config import get_redis
from fastapi import APIRouter, Depends, Request, Response
from schemas_1.user import Login, RefreshRequest, Register, SendCodeRequest
from tools_1.client_ip import get_client_ip
from tools_1.image_captcha import create_image_captcha, verify_image_captcha
from tools_1.limit import ip_rate_limit

user = APIRouter()


"""用户登录接口"""
@user.post("/api/auth/login",dependencies=[Depends(ip_rate_limit("login", 60, 300))])
async def login(data:Login,request:Request,redis = Depends(get_redis)) -> dict[str,Any]:
    login_ip = get_client_ip(request)
    result = await user_login(redis,data.user_email,data.password,login_ip)
    return result

"""刷新token接口"""
@user.post("/api/auth/refresh",dependencies=[Depends(ip_rate_limit("refresh", 60, 60))])
async def refresh(data:RefreshRequest,redis = Depends(get_redis)) -> dict[str,str]:
    return await refresh_tokens(redis,data.refresh_token)

"""退出登录接口 让 refresh token 失效"""
@user.post("/api/auth/logout")
async def logout(data:RefreshRequest,redis = Depends(get_redis)) -> dict[str,Any]:
    await revoke_refresh_token(redis,data.refresh_token)
    return {"code": 200, "message": "已退出"}

"""获取当前用户信息接口"""
@user.get("/api/auth/me")
async def get_info(user_info:dict = Depends(get_user_info)) -> dict[str,Any]:
    return user_info

"""获取图片验证码接口"""
@user.get("/api/captcha",dependencies=[Depends(ip_rate_limit("captcha", 60, 60))])
async def get_captcha(response: Response, redis = Depends(get_redis)) -> dict[str,Any]:
    response.headers["Cache-Control"] = "no-store"
    return await create_image_captcha(redis)

"""发送验证码接口"""
@user.post("/api/auth/send-code")
async def send_register_code(
    data: SendCodeRequest,
    request: Request,
        redis=Depends(get_redis)
) -> dict[str, int | str]:
    client_ip = get_client_ip(request)
    # 先校验图片验证码
    await verify_image_captcha(redis, data.captcha_id, data.captcha_code)
    await send_code(redis,str(data.user_email), client_ip)
    return {
        "code": 200,
        "message": "验证码发送成功"
    }

"""用户注册接口"""
@user.post("/api/auth/register",dependencies=[Depends(ip_rate_limit("register",30,3600))])
async def register(data:Register,request:Request,redis = Depends(get_redis)) -> dict[Any, Any]:
    register_ip = get_client_ip(request)
    result = await user_register(
        redis,
        data.username,
        data.student_id,
        str(data.email),
        data.password,
        data.code,
        register_ip,
    )
    return result

"""获取其他卖家公共信息"""
@user.get("/api/users/{user_id}",dependencies=[Depends(ip_rate_limit("seller_info", 60, 60))])
async def get_other_seller_info(user_id: int, redis=Depends(get_redis)) -> dict[str, Any]:
    result = await get_seller_public_info(redis,user_id)
    return result

