"""管理员接口"""
from admin.curd_a.admins import admin_login,get_admin_info,create_admin,get_supper_admin_info,get_admin_account,update_admin_role,\
update_admin_status
from fastapi import APIRouter,Depends,Request
from typing import Any
from admin.shemas_a.admins import AdminLoginRequest,AdminCreateRequest,AdminRoleRequest,AdminStatusRequest

admin = APIRouter()


""" 获取当前管理员用户信息接口"""
@admin.get("/api/admin/me")
async def get_current_admin(current_admin = Depends(get_admin_info)) -> dict[str,Any]:
    return {
        "code": 200,
        "message": "获取管理员信息成功",
        "data": {
            "id": current_admin["admin_id"],
            "username": current_admin["admin_name"],
            "role": current_admin["role"]
        }
    }

"""管理员登录接口"""
@admin.post("/api/admin/login")
async def login(data:AdminLoginRequest,request:Request) -> dict[str,Any]:
    login_ip = (request.client.host
        if request.client
        else "unknown")
    result = await admin_login(
        admin_username=data.username,
        admin_password=data.password,
        login_ip=login_ip
    )
    return result

"""创建管理员接口"""
@admin.post("/api/admin/accounts")
async def create_admin_account(data:AdminCreateRequest,
        current_admin: dict = Depends(get_supper_admin_info)) -> dict[str,Any]:
    result = await create_admin(
        admin_username=data.username,
        admin_password=data.password,
        admin_role=data.role
    )
    return result

"""获取所有管理员接口"""
@admin.get("/api/admin/accounts")
async def get_all_admin(current_admin: dict = Depends(get_supper_admin_info)) -> dict[str,Any]:
    result = await get_admin_account()
    return result

"""修改管理员权限接口"""
@admin.patch("/api/admin/accounts/{admin_id}/role")
async def change_admin_role(
        admin_id:int,data:AdminRoleRequest,
        current_admin: dict = Depends(get_supper_admin_info)
) -> dict[str,Any]:
    result = await update_admin_role(
        admin_id=admin_id,
        role=data.role,
        operator_id=current_admin["admin_id"]
    )
    return result

"""修改管理员状态接口"""
@admin.patch("/api/admin/accounts/{admin_id}/status")
async def change_admin_status(admin_id:int,data:AdminStatusRequest,
                            current_admin: dict = Depends(get_supper_admin_info)) -> dict[str,Any]:
    result = await update_admin_status(
        admin_id=admin_id,
        new_status=data.status,
        operator_id=current_admin["admin_id"]
    )
    return result








































