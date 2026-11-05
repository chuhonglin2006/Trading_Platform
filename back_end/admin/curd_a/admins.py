"""管理员接口函数"""
import datetime
from sqlalchemy.exc import IntegrityError
from tools_1.create_token import create_token,decode_token
from database_1.mysql_config import async_session_maker
from admin.modles_a.admins import Admin
from sqlalchemy import select,func
from typing import Any
from fastapi import HTTPException,status,Header,Depends
from tools_1.password_hash import check_password,password_hash
from tools_1.logger import get_logger


logger = get_logger(__name__, "python")


async def admin_login(admin_username:str,admin_password:str,login_ip:str) -> dict[str,Any]:
    """
    管理员登录
    :param login_ip:登录ip
    :param admin_username: 管理员账户
    :param admin_password:管理员账户哈希密码
    :return:管理员信息
    """
    async with async_session_maker() as session:
        stmt = select(Admin).where(
            Admin.username == admin_username
        )
        result = await session.execute(stmt)
        admin_account = result.scalar_one_or_none()
        if (
            admin_account is None or not
            check_password(
                admin_password,admin_account.password_hash
            )
        ):
            logger.warning(
                "管理员登录失败 username=%s ip=%s",
                admin_username,
                login_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        if admin_account.status == "banned":
            logger.warning(
                "被封禁管理员尝试登录 admin_id=%s ip=%s",
                admin_account.id,
                login_ip
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账户已被封禁,请联系网站所有者"
            )
        admin_account.last_login_at = datetime.datetime.now()
        admin_account.last_login_ip = login_ip
        await session.commit()
        logger.info(
            "管理员登录成功 admin_id=%s username=%s ip=%s",
            admin_account.id,
            admin_account.username,
            login_ip
        )
        token = create_token({
            "admin_id":admin_account.id,
            "token_type":"admin"
        })
        return {
            "code": 200,
            "message": "管理员登录成功",
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "admin": {
                    "id": admin_account.id,
                    "username": admin_account.username,
                    "role": admin_account.role
                }
            }
        }

async def get_admin_info(authorization:str = Header(...)) -> dict[str,Any]:
    """
    获取当前管理员账户信息
    :param authorization:token
    :return:管理员信息
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证头格式错误，应为: Bearer <token>"
        )
    token = authorization.split(" ",1)[1]
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=" token不能为空"
        )
    payload  = decode_token(token)
    admin_id = payload.get("admin_id")
    token_type = payload.get("token_type")
    if admin_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少必要信息"
        )
    if token_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token类型错误"
        )
    async with async_session_maker() as session:
        stmt = select(Admin).where(
            Admin.id == admin_id
        )
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()
        if admin is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="账户不存在"
            )
        if admin.status == "banned":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="账户已被封禁"
            )
        return {
            'admin_id':admin.id,
            "admin_name":admin.username,
            "role": admin.role
        }

async def create_admin(admin_username:str,admin_password:str,admin_role:str = "admin") -> dict[str,Any]:
    """
    创建管理员账户接口
    :param admin_role:管理员类型
    :param admin_username:用户名
    :param admin_password:密码
    :return:信息
    """
    admin_username = admin_username.strip()
    if not 3 <= len(admin_username) <= 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名长度必须为3到50个字符"
        )
    if len(admin_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码至少需要12个字符"
        )
    if admin_role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员角色不合法"
        )
    async with async_session_maker() as session:
        stmt = select(Admin.id).where(
            Admin.username == admin_username
        )
        result = await session.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="管理员账户已经存在"
            )
        admin = Admin(
            username=admin_username,
            password_hash=password_hash(admin_password),
            role=admin_role,
            status="normal"
        )
        session.add(admin)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="管理员账户已经存在"
            )
        await session.refresh(admin)
        logger.info(
            "管理员账户创建成功 admin_id=%s username=%s role=%s",
            admin.id,
            admin.username,
            admin.role
        )
        return {
            "code": 200,
            "message": "管理员创建成功",
            "data": {
                "id": admin.id,
                "username": admin.username,
                "role": admin.role,
                "status": admin.status
            }
        }

async def get_supper_admin_info(current_admin = Depends(get_admin_info)) -> dict[str,Any]:
    """
    判断当前是不是超级管理员
    :param current_admin:当前用户
    :return:
    """
    if current_admin["role"] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )
    return current_admin

async def get_admin_account() -> dict[str,Any]:
    """
    获取所有管理员
    :return:管理员列表
    """
    async with async_session_maker() as session:
        stmt = select(Admin).order_by(
            Admin.id.asc()
        )
        result = await session.execute(stmt)
        admins = result.scalars().all()
        return {
            "code": 200,
            "message": "获取管理员列表成功",
            "data": [
                {
                    "id": account.id,
                    "username": account.username,
                    "role": account.role,
                    "status": account.status,
                    "last_login_ip": account.last_login_ip,
                    "last_login_at": (
                        account.last_login_at.isoformat()
                        if account.last_login_at else None
                    ),
                    "created_at": account.created_at.isoformat()
                }
                for account in admins
            ]
        }

async def update_admin_role(admin_id:int,role:str,operator_id:int) -> dict[str,Any]:
    """
    修改管理员权限
    :param admin_id:普通管理员id
    :param role:权限
    :param operator_id:超级管理员权限
    :return:
    """
    if admin_id == operator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的权限"
        )
    async with async_session_maker() as session:
        async with session.begin():
            stmt = select(Admin).where(
                Admin.id == admin_id
            ).with_for_update()
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="管理员账户不存在"
                )
            if account.role == "super_admin" and role == "admin":
                await check_last_super_admin(session, account)
            account.role = role
        logger.info(
            "管理员角色修改成功 admin_id=%s role=%s operator_id=%s",
            account.id,
            account.role,
            operator_id
        )
        return {
            "code": 200,
            "message": "管理员角色修改成功",
            "data": {
                "id": account.id,
                "username": account.username,
                "role": account.role
            }
        }

async def check_last_super_admin(session, target_admin):
    """
    检查目标管理员是否为最后一位正常的超级管理员
    :param session:数据库会话
    :param target_admin:剩余管理员数量
    :return:
    """
    if (target_admin.role != "super_admin"
        or target_admin.status != "normal"
    ):
        return
    stmt = select(func.count(Admin.id)).where(
        Admin.role == "super_admin",
        Admin.status == "normal"
    )
    result = await session.execute(stmt)
    count = result.scalar_one()
    if count <= 1:
        raise HTTPException(
            status_code=400,
            detail="系统至少需要保留一位正常状态的超级管理员"
        )

async def update_admin_status(admin_id:int,new_status:str,operator_id:int) -> dict[str,Any]:
    """
    修改管理员状态
    :param admin_id:普通管理员id
    :param new_status:新状态
    :param operator_id:超级管理员id
    :return:
    """
    if admin_id == operator_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的状态"
        )

    async with async_session_maker() as session:
        async with session.begin():
            stmt = select(Admin).where(
                Admin.id == admin_id
            ).with_for_update()
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="管理员账户不存在"
                )
            if account.status == new_status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="管理员账户已处于该状态"
                )
            if new_status == "banned":
                await check_last_super_admin(session,account)
            account.status = new_status
            result_data = {
                "id": account.id,
                "username": account.username,
                "status": account.status
            }
        logger.info(
            "管理员状态修改成功 admin_id=%s status=%s operator_id=%s",
            result_data["id"],
            result_data["status"],
            operator_id
        )
        return {
            "code": 200,
            "message": "管理员状态修改成功",
            "data": result_data
        }























