"""订单模型类"""
from datetime import datetime

from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    product_id: int

class MeetingRequest(BaseModel):
    meeting_time: datetime
    meeting_location: str