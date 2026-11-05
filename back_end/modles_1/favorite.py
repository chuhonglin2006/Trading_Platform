"""收藏模型类"""
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import BigInteger,DateTime,func,ForeignKey,UniqueConstraint
from datetime import datetime
from modles_1.base import Base
from modles_1.user import User
from modles_1.products import Product


class Favorite(Base):
    __tablename__ = 'favorites'
    __table_args__ = (UniqueConstraint(
        "user_id",
            "product_id",
            name="uq_favorite_user_product"
    ),)
    id:Mapped[int] = mapped_column(BigInteger,primary_key=True,autoincrement=True)
    user_id:Mapped[int] = mapped_column(BigInteger,ForeignKey(User.id),index=True,nullable=False)
    product_id:Mapped[int] = mapped_column(BigInteger,ForeignKey(Product.id),index=True,nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime,server_default=func.now())
