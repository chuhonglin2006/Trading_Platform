"""商品模型类"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modles_1.base import Base
from modles_1.category import Category
from modles_1.product_image import ProductImage
from modles_1.user import User


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_list", "status", "review_status", "created_at", "id"),
        Index("ix_products_seller_created", "seller_id", "created_at"),
    )


    id: Mapped[int] = mapped_column(
        BigInteger(),
        primary_key=True,
        autoincrement=True
    )

    seller_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.id),
        nullable=False,
        index=True
    )

    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Category.id),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        Enum("on_sale", "off_sale", "sold"),
        nullable=False,
        default="on_sale"
    )

    view_count: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        default=0
    )

    campus: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    publish_province: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    sold_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order"
    )

    seller: Mapped["User"] = relationship(
        "User",
        foreign_keys=[seller_id],
        back_populates="products"
    )

    category: Mapped["Category"] = relationship(
        "Category"
    )

    review_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending"
    )

    review_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id"),
        nullable=True
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    orders = relationship(
        "Order",
        back_populates="product"
    )
