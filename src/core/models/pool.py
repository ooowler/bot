from __future__ import annotations
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped
from src.core.models.base import Base, Account


class PoolStatus(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"


class PoolType(StrEnum):
    """Пока только один тип – «все аккаунты с sub‑акком»."""

    SUB_ACC_REQUIRED = "sub_required"


class Pool(Base):
    __tablename__ = "pools"
    __table_args__ = (UniqueConstraint("label", "owner_id", name="uq_pool_owner"),)

    id: Mapped[int] = Column(Integer, primary_key=True)
    label: Mapped[str] = Column(String, nullable=False)  # имя для пользователя
    owner_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), nullable=False)
    pool_type: Mapped[str] = Column(
        String, nullable=False, default=PoolType.SUB_ACC_REQUIRED
    )
    is_active: Mapped[bool] = Column(Boolean, default=False)
    status: Mapped[str] = Column(String, default=PoolStatus.STOPPED)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["PoolAccountLink"]] = relationship(back_populates="pool")


class PoolAccountLink(Base):
    __tablename__ = "pool_account_link"
    __table_args__ = (UniqueConstraint("pool_id", "account_id"),)

    id: Mapped[int] = Column(Integer, primary_key=True)
    pool_id: Mapped[int] = Column(Integer, ForeignKey("pools.id"), nullable=False)
    account_id: Mapped[int] = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # backrefs
    pool: Mapped["Pool"] = relationship(back_populates="accounts")
    account: Mapped[Account] = relationship()
