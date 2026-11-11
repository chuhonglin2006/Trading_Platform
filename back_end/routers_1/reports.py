"""举报接口"""
from typing import Any

from crud_1.reports import report_user
from crud_1.users import get_user_info
from fastapi import APIRouter, Depends
from schemas_1.reports import ReportCreate
from tools_1.limit import ip_rate_limit

report = APIRouter()


"""举报接口"""
@report.post("/api/reports", dependencies=[Depends(ip_rate_limit("report", 10, 3600))])
async def submit_report(data:ReportCreate,current_user = Depends(get_user_info)) -> dict[str,Any]:
    result = await report_user(
        reporter_id=current_user["id"],
        target_id=data.target_id,
        target_type=data.target_type,
        reason=data.reason
    )
    return result