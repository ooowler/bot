from .enums import Chain
from .base import Base
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, JSON
from sqlalchemy.orm import relationship


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    owner_tid = Column(BigInteger, nullable=False, index=True)
    parent_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )

    name = Column(String, nullable=False, unique=True)
    exchange = Column(String, nullable=False, default="backpack")
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    country = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    parent = relationship("Account", remote_side=[id], backref="sub_accounts")

    deposit_addresses = relationship(
        "DepositAddress", back_populates="account", cascade="all, delete-orphan"
    )

    proxy = relationship(
        "Proxy", back_populates="account", uselist=False, cascade="all, delete-orphan"
    )

    fake_header = relationship(
        "FakeHeader",
        back_populates="account",
        uselist=False,
        cascade="all, delete-orphan",
    )

    users = relationship(
        "UserAccountLink", back_populates="account", cascade="all, delete-orphan"
    )

    @property
    def is_sub(self) -> bool:
        return self.parent_id is not None


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"))
    ip = Column(String, nullable=False)
    port = Column(Integer, nullable=False)
    login = Column(String, nullable=False)
    password = Column(String, nullable=False)
    country = Column(String, nullable=False)

    in_use = Column(Boolean, default=False, nullable=False)
    fails = Column(Integer, default=0, nullable=False)

    account = relationship("Account", back_populates="proxy", uselist=False)


class FakeHeader(Base):
    __tablename__ = "fake_headers"

    id = Column(Integer, primary_key=True)
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True
    )
    headers = Column(JSON, nullable=False)
    cookies = Column(JSON, nullable=False)

    account = relationship("Account", back_populates="fake_header", uselist=False)


class DepositAddress(Base):
    __tablename__ = "deposit_addresses"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    chain = Column(ENUM(Chain, name="blockchain_enum"), nullable=False)
    address = Column(String, nullable=False)
    memo = Column(String)
    is_whitelisted = Column(Boolean, default=False)
    meta = Column(JSONB)

    account = relationship("Account", back_populates="deposit_addresses")

    __table_args__ = (UniqueConstraint("chain", "address", name="uq_chain_address"),)
