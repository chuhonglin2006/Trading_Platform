"""商品分类模型类"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from modles_1.base import Base


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    key: Mapped[str] = mapped_column(String(30),nullable=False,unique=True)
    name: Mapped[str] = mapped_column(String(50),nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer,nullable=False,default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.current_timestamp())
