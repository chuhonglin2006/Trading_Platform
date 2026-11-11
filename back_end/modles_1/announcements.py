"""公告模型类"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from modles_1.base import Base


class Announcements(Base):
    __tablename__ = "announcements"
    id:Mapped[int] = mapped_column(BigInteger,autoincrement=True,primary_key=True)
    title:Mapped[str] = mapped_column(String(100),nullable=False)
    content:Mapped[String] = mapped_column(Text,nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(),server_onupdate=func.now())

