"""举报模型类"""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from modles_1.base import Base


class Report(Base):
    __tablename__ = "reports"

    # 举报ID
    id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True
    )

    # 举报人ID
    reporter_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # 举报目标类型
    # user：用户
    # product：商品
    target_type: Mapped[str] = mapped_column(
        Enum("user", "product"),
        nullable=False,
        default="user"
    )

    # 被举报目标ID
    # target_type=user    -> 用户ID
    # target_type=product -> 商品ID
    target_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        nullable=False
    )

    # 举报原因
    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    # 处理状态
    # pending   -> 待处理
    # resolved  -> 已处理
    # rejected  -> 已驳回
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "resolved",
            "rejected"
        ),
        nullable=False,
        default="pending"
    )

    # 处理方式
    # deduct_score -> 扣除信用分
    # ban          -> 封号
    handle_type: Mapped[str | None] = mapped_column(
        Enum(
            "deduct_score",
            "ban"
        ),
        nullable=True
    )

    # 扣除的信用分
    #
    # 当 handle_type == "deduct_score" 时使用
    punish_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 封号天数
    #
    # 当 handle_type == "ban" 时使用
    #
    # 例如：
    # 7   -> 封禁7天
    # 30  -> 封禁30天
    # -1  -> 永久封禁
    ban_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 管理员处理备注
    handle_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    # 举报创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )