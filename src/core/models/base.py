from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ─────────────────────────── Telegram‑user ───────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    username = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    accounts = relationship("UserAccountLink", back_populates="user")

    __table_args__ = (UniqueConstraint("telegram_id", name="uq_user_telegram_id"),)


# ─────────────────────────── Account (main / sub) ────────────────────
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    name = Column(String, nullable=False)
    exchange = Column(String, nullable=False, default="backpack")
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    country = Column(String)
    wallet = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # self‑relation for sub‑accounts
    parent = relationship("Account", remote_side=[id], back_populates="children")
    children = relationship("Account", back_populates="parent")

    deposit_addresses = relationship("DepositAddress", back_populates="account")
    users = relationship("UserAccountLink", back_populates="account")

    @property
    def is_sub(self) -> bool:
        return self.parent_id is not None


# ─────────────────────────── Chains enum ─────────────────────────────
class Chain(str, Enum):
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"


# ───────────────── Deposit address for account ───────────────────────
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


# ─────────────────── Link user ↔ account with role ───────────────────
class UserAccountLink(Base):
    __tablename__ = "user_account_link"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    is_admin = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="accounts")
    account = relationship("Account", back_populates="users")

    __table_args__ = (
        UniqueConstraint("user_id", "account_id", name="uq_user_account"),
    )
