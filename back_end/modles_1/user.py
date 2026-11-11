"""用户模型类"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modles_1.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    email: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    student_id: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True
    )

    campus: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="关山校区"
    )

    # 对应数据库：
    status: Mapped[str] = mapped_column(
        Enum("normal", "banned"),
        nullable=False,
        default="normal"
    )

    credit_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100
    )

    register_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True
    )

    last_login_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # 我作为买家的订单
    buyer_orders = relationship(
        "Order",
        foreign_keys="Order.buyer_id",
        back_populates="buyer"
    )

    # 我作为卖家的订单
    seller_orders = relationship(
        "Order",
        foreign_keys="Order.seller_id",
        back_populates="seller"
    )

    # 我作为买家参与的聊天
    buyer_chat_conversations = relationship(
        "ChatConversation",
        foreign_keys="ChatConversation.buyer_id",
        back_populates="buyer"
    )

    # 我作为卖家参与的聊天
    seller_chat_conversations = relationship(
        "ChatConversation",
        foreign_keys="ChatConversation.seller_id",
        back_populates="seller"
    )

    # 我发送的所有消息
    chat_messages = relationship(
        "ChatMessage",
        foreign_keys="ChatMessage.sender_id",
        back_populates="sender"
    )

    # 我发布的商品
    products = relationship(
        "Product",
        foreign_keys="Product.seller_id",
        back_populates="seller"
    )

    banned_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )