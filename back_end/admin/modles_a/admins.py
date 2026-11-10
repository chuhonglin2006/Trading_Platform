"""管理员数据库模型"""

from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, Enum, text
from sqlalchemy.orm import Mapped, mapped_column
from modles_1.base import Base


class Admin(Base):
    """管理员账户表"""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(
            BigInteger(), "mysql"
        ),
        primary_key=True,
        autoincrement=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        Enum("normal", "banned"),
        nullable=False,
        server_default=text("'normal'")
    )

    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True
    )

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text(
            "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
        )
    )

    role: Mapped[str] = mapped_column(
        Enum("super_admin", "admin"),
        nullable=False,
        server_default=text("'admin'")
    )