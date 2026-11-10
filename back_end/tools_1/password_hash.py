"""密码加密,对比工具"""
from passlib.context import CryptContext
import asyncio

password_context = CryptContext(schemes = ["bcrypt"],deprecated = "auto")


# 账号不存在时用来做一次 假对比 让响应时间和账号存在时一样，
# 防止通过响应时间猜出哪些用户名是真实存在的
DUMMY_HASH = password_context.hash("timing-equalizer-not-a-real-password")



def password_hash(password:str) -> str:
    """
    密码加密
    :param password:原始密码
    :return:加密后密码
    """
    return password_context.hash(password)

def check_password(password:str,hash_password:str) -> bool:
    """
    密码对比
    :param password:原始密码
    :param hash_password:加密后的密码
    :return:对比是否成功
    """
    return password_context.verify(password,hash_password)


_hash_semaphore = asyncio.Semaphore(4)

async def password_hash_async(password: str) -> str:
    """密码加密（异步版本，在 async 函数里请用这个）"""
    async with _hash_semaphore:
        return await asyncio.to_thread(password_hash, password)


async def check_password_async(password: str, hash_password: str) -> bool:
    """密码对比（异步版本，在 async 函数里请用这个）"""
    async with _hash_semaphore:
        return await asyncio.to_thread(check_password, password, hash_password)


