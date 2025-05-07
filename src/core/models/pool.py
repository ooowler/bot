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
    JSON,
)
from src.core.models.base import Base


class PoolStatus(StrEnum):
    STOPPED = "stopped"
    RUNNING = "running"


class PoolType(StrEnum):
    SUB_ACC_REQUIRED = "sub_required"
    MARKET_STRATEGY = "market_strategy"


class Pool(Base):
    __tablename__ = "pools"
    __table_args__ = (UniqueConstraint("label", "owner_id", name="uq_pool_owner"),)

    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    pool_type = Column(
        String,
        nullable=False,
        default=PoolType.SUB_ACC_REQUIRED.value,
    )
    is_active = Column(Boolean, default=False, nullable=False)
    status = Column(
        String,
        default=PoolStatus.STOPPED.value,
        nullable=False,
    )
    settings = Column(
        JSON,
        nullable=False,
        default=lambda: {},
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class PoolAccountLink(Base):
    __tablename__ = "pool_account_link"
    __table_args__ = (
        UniqueConstraint("pool_id", "account_id", name="uq_pool_account"),
    )

    id = Column(Integer, primary_key=True)
    pool_id = Column(
        Integer, ForeignKey("pools.id", ondelete="CASCADE"), nullable=False
    )
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
