"""管理员界面举报接口"""
from fastapi import APIRouter,Depends
from admin.curd_a.reports import get_all_reports,get_report_info
from admin.curd_a.admins import get_admin_info
from typing import Any
from admin.shemas_a.reports import ReportHandleRequest, ReportRejectRequest
from admin.curd_a.reports import handle_report, reject_report
from database_1.redis_config import get_redis
admin_reports = APIRouter()



"""获取所有举报接口"""
@admin_reports.get("/api/admin/reports")
async def admin_get_all_reports(admin = Depends(get_admin_info)) -> dict[str,Any]:
    result = await get_all_reports()
    return result

"""获取举报详情接口"""
@admin_reports.get("/api/admin/reports/{report_id}")
async def get_report_msg(report_id:int,admin = Depends(get_admin_info)) -> dict[str,Any]:
    result = await get_report_info(report_id)
    return result

"""处理举报接口"""
@admin_reports.patch("/api/admin/reports/{report_id}/handle")
async def handle_report_api(
    report_id: int,
    data: ReportHandleRequest,
    admin=Depends(get_admin_info),
    redis = Depends(get_redis)) -> dict[str,Any]:
    result = await handle_report(
        redis=redis,
        report_id=report_id,
        handle_type=data.handle_type,
        punish_score=data.punish_score,
        ban_days=data.ban_days,
        handle_note=data.handle_note
    )
    return result

@admin_reports.patch("/api/admin/reports/{report_id}/status")
async def reject_report_api(
    report_id: int,
    data: ReportRejectRequest,
    admin=Depends(get_admin_info)
) -> dict[str, Any]:
    return await reject_report(
        report_id=report_id,
        handle_note=data.handle_note
    )
