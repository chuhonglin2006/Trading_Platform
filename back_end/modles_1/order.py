"""订单模型类"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    String,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
    func,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modles_1.base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_auto_receive", "status", "auto_receive_at"),
        Index("ix_orders_auto_complete", "status", "received_at"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    order_no: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True
    )

    buyer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    seller_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "received",
            "completed",
            "cancelled"
        ),
        nullable=False,
        default="pending"
    )

    # =========================
    # 交易安排
    # =========================

    meeting_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    meeting_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # =========================
    # 时间
    # =========================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp()
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    auto_receive_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # =========================
    # 双方交易安排确认
    # =========================

    buyer_meeting_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    seller_meeting_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # =========================
    # 关系
    # =========================

    buyer = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="buyer_orders"
    )

    seller = relationship(
        "User",
        foreign_keys=[seller_id],
        back_populates="seller_orders"
    )

    product = relationship(
        "Product",
        foreign_keys=[product_id],
        back_populates="orders"
    )

    chat_conversation = relationship(
        "ChatConversation",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan"
    )