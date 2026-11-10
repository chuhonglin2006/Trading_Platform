"""订单模型类"""
from pydantic import BaseModel
from datetime import datetime

class CreateOrderRequest(BaseModel):
    product_id: int

class MeetingRequest(BaseModel):
    meeting_time: datetime
    meeting_location: str