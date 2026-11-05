"""处理举报模型类"""
from pydantic import BaseModel,Field
from typing import Literal




class ReportHandleRequest(BaseModel):
    handle_type: Literal["deduct_score", "ban"]
    punish_score: int | None = None
    ban_days: int | None = None
    handle_note: str | None = Field(
        default=None,
        max_length=500
    )

class ReportRejectRequest(BaseModel):
    status: Literal["rejected"] = "rejected"
    handle_note: str | None = Field(
        default=None,
        max_length=500
    )
