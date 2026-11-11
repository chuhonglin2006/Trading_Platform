""" Redis中邮箱加密 """
import hashlib
import hmac
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "keys.env")

SECRET = os.getenv("REDIS_KEY_SECRET", "").encode()
if not SECRET:
    raise RuntimeError("缺少REDIS_KEY_SECRET")




def hash_email(email: str) -> str:
    """ 将邮箱转为不可逆的哈希 用于拼接Redis Key """
    email = email.strip().lower()
    return hmac.new(SECRET, email.encode(), hashlib.sha256).hexdigest()
