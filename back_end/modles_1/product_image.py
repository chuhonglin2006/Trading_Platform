"""商品图片模型类"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modles_1.base import Base


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[int] = mapped_column(BigInteger(),primary_key=True,autoincrement=True)
    product_id: Mapped[int] = mapped_column(BigInteger(),ForeignKey("products.id",ondelete="CASCADE"),nullable=False,index=True)
    image_url: Mapped[str] = mapped_column(String(500),nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer(),nullable=False,default=0,index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.current_timestamp())
    product: Mapped["Product"] = relationship("Product",back_populates="images")