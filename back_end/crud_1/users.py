"""用户接口函数"""
from typing import Any
from database_1.mysql_config import async_session_maker
from modles_1.user import User
from sqlalchemy import select
from tools_1.password_hash import check_password,password_hash
from tools_1.create_token import create_token,decode_token
from fastapi import HTTPException, status, Header,Depends
from datetime import datetime
from tools_1.email import send_email
import secrets,asyncio
from collections import defaultdict, deque
from threading import Lock
from tools_1.check_student_id import check_student_id
from tools_1.email_hash import hash_email
from cachetools import TTLCache
import json,random
from fastapi.encoders import jsonable_encoder
from database_1.redis_config import get_redis
from sqlalchemy.exc import IntegrityError
from tools_1.warm_up_cache import user_name_bloom,normalize_username
from tools_1.logger import get_logger
from tools_1.ip_region import get_ip_province


logger = get_logger(__name__, "redis")
app_logger = get_logger(__name__, "python")


_LOGIN_MAX_FAILURES = 5
_LOGIN_WINDOW_SECONDS = 300
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_login_lock = Lock()


# 用户本地缓存
user_local_cache = TTLCache(maxsize=2000, ttl=10)


def user_cache_key(user_id:int) -> str:
    """ 生成用户缓存key """
    return f"user:info:v2:{user_id}"

def _login_fail_key(login_ip: str, user_email: str) -> str:
    email_id = hash_email((user_email or "").strip().lower())
    return f"ratelimit:login:{(login_ip or 'unknown').strip()}:{email_id}"

async def _check_login_rate(redis, login_ip: str, user_email: str) -> None:
    """ 登录前检查 失败次数达到上限就拒绝 """
    key = _login_fail_key(login_ip, user_email)
    try:
        raw = await redis.get(key)
        if raw is not None and int(raw) >= _LOGIN_MAX_FAILURES:
            retry_after = max(await redis.ttl(key), 1)
            logger.warning(
                "登录失败次数达到上限 ip=%s retry_after=%s",
                login_ip,
                retry_after
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录失败次数过多，请 {retry_after} 秒后再试",
                headers={"Retry-After": str(retry_after)}
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "登录限流读取失败，本次请求放行 ip=%s",
            login_ip
        )

async def _record_login_failure(redis, login_ip: str, user_email: str) -> None:
    key = _login_fail_key(login_ip, user_email)
    try:
        pipe = redis.pipeline(transaction=True)
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
        if count == 1 or ttl == -1:           # 首次失败 或 key 没有过期时间
            await redis.expire(key, _LOGIN_WINDOW_SECONDS)
    except Exception:
        logger.exception("记录登录失败次数出错 ip=%s", login_ip)

async def _clear_login_failures(redis, login_ip: str, user_email: str) -> None:
    try:
        await redis.delete(_login_fail_key(login_ip, user_email))
    except Exception:
        logger.exception("清除登录失败记录出错 ip=%s", login_ip)

async def invalidate_user(redis, user_id: int) -> None:
    """用户状态、信用分等变化后删除用户缓存"""
    user_local_cache.pop(user_id, None)
    try:
        await redis.delete(user_cache_key(user_id))
    except Exception:
        logger.exception("用户缓存删除失败 user_id=%s", user_id)

async def load_user_from_mysql(redis,user_id:int) -> dict | None:
    """ 从MySQL中查询用户信息 """
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(
            User.id == user_id
        ))
        if user is None:
            return None
        ip_province = await get_ip_province(
            redis,
            user.last_login_ip or user.register_ip
        )
        return {
            "id": user.id,
            "username": user.username,
            "studentId": user.student_id,
            "campus": user.campus,
            "score": user.credit_score,
            "ip_province": ip_province,
            "status": user.status,
        }

async def get_user_cached(redis,user_id:int) -> dict | None:
    """ 从缓存中获取用户信息 本地缓存 -> Redis -> MySQL """
    # 本地缓存
    data = user_local_cache.get(user_id)
    if data is not None:
        return data

    # Redis
    try:
        cached = await redis.get(user_cache_key(user_id))
        if cached is not None:
            if cached in ("null",b"null"):
                return None
            data = json.loads(cached)
            if "ip_province" not in data:
                data = None
                await redis.delete(user_cache_key(user_id))
            if data is not None:
                user_local_cache[user_id] = data
                return data
    except Exception:
        logger.exception("用户缓存读取失败 user_id=%s", user_id)

    # MySQL
    data = await load_user_from_mysql(redis,user_id)

    # 写入Redis
    try:
        await redis.set(user_cache_key(user_id),
            json.dumps(jsonable_encoder(data)) if data else "null",
            ex=60 + random.randint(0, 15) if data else 30,
        )
    except Exception:
        logger.exception("用户缓存写入失败 user_id=%s", user_id)

    if data:
        user_local_cache[user_id] = data
    return data

async def user_register(redis,username:str,student_id:str,user_email:str,
password:str,email_code:str,register_ip:str = '') -> dict[Any, Any]:
    """
    用户注册接口
    1.验证学号
    2.查询邮箱是否已经注册
    3.查询最新注册验证码
    4.检查验证码是否存在
    5.检查验证码是否过期
    6.检查验证码是否正确
    7.创建用户
    8.将验证码标记为已使用
    :param redis:Redis连接
    :param student_id:学号
    :param username:用户名
    :param register_ip:注册ip地址
    :param email_code:邮箱验证码
    :param user_email:用户邮箱
    :param password:用户密码
    :return:用户信息
    """
    username = (username or "").strip()
    user_email = (user_email or "").strip().lower()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能为空")
    if len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能超过50个字符")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱不能为空")
    if len(user_email) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱长度不能超过100个字符")
    if not password or len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少需要6位")
    if len(password) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码不能超过64位")
    if not check_student_id(student_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号格式错误"
        )

    async with async_session_maker() as session:
        # 重复检查
        for column, value, msg in (
                (User.email, user_email, "邮箱已注册"),
                (User.username, username, "用户名已存在"),
                (User.student_id, student_id, "学号已注册"),
        ):
            if await session.scalar(select(User.id).where(column == value)):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)

        # 验证码校验
        email_id = hash_email(user_email)
        code_key = f"captcha:register:{email_id}"
        fail_key = f"captcha:register:fail:{email_id}"

        saved_code = await redis.get(code_key)
        if saved_code is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码不存在或已过期"
            )

        input_code = (email_code or "").strip()
        # 转为 bytes 再比较,防止非 ASCII 字符触发 TypeError
        if not secrets.compare_digest(
            saved_code.encode("utf-8"), input_code.encode("utf-8")
        ):
            failures = await redis.incr(fail_key)
            # 首次失败,或旧数据里没有过期时间的 key,都补上 TTL
            if failures == 1 or await redis.ttl(fail_key) == -1:
                await redis.expire(fail_key, 300)
            if failures >= 5:
                await redis.delete(code_key, fail_key)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="验证码错误次数过多,请重新获取"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误"
            )

        # 创建用户
        hash_password = password_hash(password)
        user = User(
            username=username,
            email=user_email,
            password_hash=hash_password,
            student_id=student_id,
            register_ip=register_ip
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱、用户名或学号已被注册"
            )
        await session.refresh(user)
        await redis.delete(code_key, fail_key)
        user_name_bloom.add(normalize_username(username))
        ip_province = await get_ip_province(redis, register_ip)
        app_logger.info(
            "用户注册成功 user_id=%s username=%s",
            user.id,
            user.username
        )

        token = create_token({"user_id": user.id})

        return {
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "studentId": user.student_id,
                "campus": user.campus,
                "score": user.credit_score,
                "ipProvince": ip_province
            }
        }

async def user_login(redis,user_email:str,password:str,login_ip:str) -> dict[str, str | dict[str, Any]]:
    """
    用户登录接口
    1.先查询用户是否存在
    2.若存在判断用户是否封禁
    3.账号不存在时也统一返回“用户名或密码错误”
    4.若用户未封禁则检查用户密码,否则禁止登录
    5.密码对比错误则返回密码错误
    :param redis: Redis
    :param login_ip:登录ip
    :param user_email:用户邮箱
    :param password:密码
    :return:用户token,id,邮箱
    """
    await _check_login_rate(redis, login_ip, user_email)

    async with async_session_maker() as session:
        stmt = select(User).where(User.email == user_email)
        user_class = await session.execute(stmt)
        user = user_class.scalar_one_or_none()
        if user is None:
            await _record_login_failure(redis, login_ip, user_email)
            app_logger.warning("用户登录失败原因=账号不存在 ip=%s", login_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='用户名或密码错误'
            )
        if user.status == "banned":
            if user.banned_until is None:
                raise HTTPException(
                    status_code=400,
                    detail="账号已被永久封禁"
                )
            if datetime.now() < user.banned_until:
                app_logger.warning(
                    "被封禁用户尝试登录 user_id=%s ip=%s",
                    user.id,
                    login_ip
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"账号已被封禁至 {user.banned_until}"
                )
            user.status = "normal"
            user.banned_until = None
        if not check_password(password, user.password_hash):
            await _record_login_failure(redis, login_ip, user_email)
            app_logger.warning(
                "用户登录失败原因=密码错误 user_id=%s ip=%s",
                user.id,
                login_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='用户名或密码错误'
            )
        await _clear_login_failures(redis, login_ip, user_email)
        user.last_login_at = datetime.now()
        user.last_login_ip = login_ip
        await session.commit()
        ip_province = await get_ip_province(redis, login_ip)
        await invalidate_user(redis,user.id)
        app_logger.info(
            "用户登录成功 user_id=%s ip=%s",
            user.id,
            login_ip
        )
        token = create_token({
            "user_id": user.id
        })
        return {
            "access_token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "studentId": user.student_id,
                "campus": user.campus,
                "score": user.credit_score,
                "ipProvince": ip_province
            }
        }

async def get_user_info(redis = Depends(get_redis),authorization: str | None = Header(default=None)) -> dict[str, Any | None]:
    """
    获取当前用户信息
    1.获取Authorization 请求头
    2.检查Bearer 格式
    3.解码JWT
    4.获取user_id
    5.根据user_id查询数据库
    6.返回最新用户信息
    :param redis: Redis
    :param authorization:授权码
    :return:用户信息
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证头格式错误，应为: Bearer <token>"
        )
    token = authorization.split(" ", 1)[1]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token不能为空"
        )
    payload  = decode_token(token)
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少必要信息"
        )
    user = await get_user_cached(redis,user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user["status"] == "banned":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被封禁")
    # 重新组装一个新字典 不把缓存里的对象交出去
    return {
        "id": user["id"],
        "username": user["username"],
        "studentId": user["studentId"],
        "campus": user["campus"],
        "score": user["score"],
        "ipProvince": user.get("ip_province", "未知"),
    }

async def get_optional_user_info(redis = Depends(get_redis),authorization:str | None = Header(default=None)) -> dict[str, Any] | None:
    """
    可选登录信息

    用于既允许游客访问、又需要识别登录用户的接口。
    未携带 token、token 无效或账户不可用时返回 None,
    由调用方按游客身份处理,不抛出异常。
    :param redis: Redis
    :param authorization:授权码
    :return:用户信息或None
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = decode_token(token)
    except HTTPException:
        return None
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        return None
    user = await get_user_cached(redis, user_id)
    if user is None or user["status"] == "banned":
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "studentId": user["studentId"],
        "campus": user["campus"],
        "score": user["score"],
        "ipProvince": user.get("ip_province", "未知"),
    }

async def verify_websocket_user(redis, token: str) -> dict[str, Any]:
    """
    WebSocket 鉴权: 解码 token → 用户缓存
    :param redis: Redis
    :param token: 客户端发来的 JWT
    :return: 用户 id 和用户名
    """
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token缺少用户id"
        )

    user = await get_user_cached(redis, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    if user["status"] == "banned":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被封禁"
        )

    return {"id": user["id"], "username": user["username"]}

async def send_code(redis,user_email:str,client_ip:str) -> None:
    """
    发送邮箱验证码,并将验证码存入Redis
    1.确认60秒的限制时间
    2.60秒未过则抛出异常,过了就查找以前已经发送的验证码
    3.将以前已经发送但是未过期的验证码全部作废
    4.生成验证码和邮件内容
    5.将验证码信息存入Redis
    6.发送验证码
    :param client_ip:注册ip
    :param redis:Redis连接
    :param user_email:用户邮箱
    :return:
    """

    user_email = (user_email or "").strip().lower()
    email_id = hash_email(user_email)
    code_key = f"captcha:register:{email_id}"
    cooldown_key = f"captcha:register:cooldown:{email_id}"
    fail_key = f"captcha:register:fail:{email_id}"

    # IP限流 半小时最多 20次
    ip_key = f"captcha:register:ip:{client_ip or 'unknown'}"
    count = await redis.incr(ip_key)
    if count == 1 or await redis.ttl(ip_key) == -1:
        await redis.expire(ip_key,1800)
    if count > 20:
        ttl = await redis.ttl(ip_key)
        minutes = max(1,(max(ttl,0) + 59) // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁,请{minutes}分钟后重试"
        )

    # 冷却 key不存在才设置成功
    ok = await redis.set(cooldown_key,1,ex=60,nx=True)
    if not ok:
        ttl = await redis.ttl(cooldown_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请{max(ttl,1)}秒后重试"
        )

    # 生成并保存验证码
    email_code = str(secrets.randbelow(900000) + 100000)
    await redis.set(code_key,email_code,ex=300)
    await redis.delete(fail_key)

    # 发送邮件
    mail_content = f"你的验证码为{email_code},5分钟内有效,请勿将验证码告诉他人"

    try:
        await asyncio.to_thread(send_email,user_email,mail_content)
        app_logger.info("注册验证码邮件已发送 ip=%s", client_ip)
    except Exception:
        # 发送失败 撤销 让用户可以立即重试
        await redis.delete(code_key,cooldown_key)
        app_logger.exception("注册验证码邮件发送失败 ip=%s", client_ip)
        raise

async def get_seller_public_info(redis,seller_id:int) -> dict[str,Any]:
    """
    获取其他卖家公共信息
    :param redis: Redis
    :param seller_id:用户id
    :return:其他用户公共信息
    """
    user = await get_user_cached(redis, seller_id)
    if user is None or user["status"] != "normal":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在或已被封禁"
        )
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "id": user["id"],
            "username": user["username"],
            "campus": user["campus"],
            "score": user["score"],
            "ip_province": user.get("ip_province", "未知"),
        }
    }































