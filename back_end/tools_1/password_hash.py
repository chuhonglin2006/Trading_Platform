"""密码加密,对比工具"""
from passlib.context import CryptContext

password_context = CryptContext(schemes = ["bcrypt"],deprecated = "auto")

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


