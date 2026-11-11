"""举报接口模型类"""
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    target_type:str
    target_id:int
    reason:str = Field(min_length=1,max_length=500)