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
from sqlalchemy.orm import relationship, Mapped


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    accounts = relationship("UserAccountLink", back_populates="user")

    friends = relationship(
        "UserFriend",
        foreign_keys="[UserFriend.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (UniqueConstraint("telegram_id", name="uq_user_telegram_id"),)


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


class UserFriend(Base):
    __tablename__ = "user_friends"

    user_id = Column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    friend_id = Column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )

    confirmed: Mapped[bool] = Column(Boolean, default=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="friends")
    friend = relationship("User", foreign_keys=[friend_id])
