"""用户聊天模型类"""
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """发送消息模型类"""
    content: str = Field(min_length=1, max_length=500)

class WSMessage(BaseModel):
    """WebSocket消息模型类"""
    type:str
    content:str | None = Field(default=None,max_length=500)