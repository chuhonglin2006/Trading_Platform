"""生成用户登录token"""
from datetime import datetime,timezone,timedelta
from typing import Any
from jose import jwt
from fastapi import HTTPException,status
import os
from dotenv import load_dotenv
from pathlib import Path
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")

key_env_path = Path(__file__).resolve().parent.parent / "keys.env"
load_dotenv(key_env_path)
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_token(data:dict) -> str:
    """
    生成用户登录时的token
    :param data:登录时的数据
    :return:token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes = ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, str(SECRET_KEY), algorithm=str(ALGORITHM))

def decode_token(token:str) -> dict[str, Any]:
    """
    解码token
    :param token:token
    :return:解码后的数据
    """
    try:
        payload = jwt.decode(token,str(SECRET_KEY),algorithms = [ALGORITHM])
        return payload
    except Exception:
        logger.warning("Token解码失败或已过期")
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED,
                            detail='token无效或已过期')


