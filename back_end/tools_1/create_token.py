"""生成用户登录token"""
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import HTTPException, status
from jose import jwt

from tools_1.logger import get_logger

logger = get_logger(__name__, "python")

key_env_path = Path(__file__).resolve().parent.parent / "keys.env"
load_dotenv(key_env_path)
SECRET_KEY = os.getenv('SECRET_KEY', '')
ALGORITHM = os.getenv('ALGORITHM', '')
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# 启动时检查配置 缺失或太弱就直接报错退出
ALLOWED_ALGORITHMS = {"HS256", "HS384", "HS512"}
if len(SECRET_KEY.strip()) < 32:
    raise RuntimeError("SECRET_KEY 缺失或太短")
if ALGORITHM not in ALLOWED_ALGORITHMS:
    raise RuntimeError(f"ALGORITHM 必须是 {sorted(ALLOWED_ALGORITHMS)} 之一")


def create_token(data:dict) -> str:
    """
    生成用户登录时的token
    :param data:登录时的数据
    :return:token
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=str(ALGORITHM))

def decode_token(token:str) -> dict[str, Any]:
    """
    解码token
    :param token:token
    :return:解码后的数据
    """
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms = [ALGORITHM])
        return payload
    except Exception:  # noqa: BLE001
        logger.warning("Token解码失败或已过期")
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,  # noqa: B904
                            detail='token无效或已过期')


