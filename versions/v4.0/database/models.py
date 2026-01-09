"""
SQLAlchemy models for SPIN Training Bot v4.
Includes users, subscriptions, payments, promocodes, and free trainings.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, BigInteger, String, Boolean, DateTime, Enum, ForeignKey, Numeric, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

# Use Base from base_models to ensure all models are in the same metadata
from .base_models import Base


class SubscriptionType(enum.Enum):
    """Types of subscriptions."""
    MONTH = "month"
    YEAR = "year"
    CREDITS = "credits"


class PaymentStatus(enum.Enum):
    """Payment status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PromocodeType(enum.Enum):
    """Promocode types."""
    TRAININGS = "trainings"
    FREE_MONTH = "free_month"
    CREDITS = "credits"


class FreeTrainingSource(enum.Enum):
    """Source of free trainings."""
    CHANNEL = "channel"
    PROMOCODE = "promocode"
    ADMIN = "admin"


class User(Base):
    """User model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Statistics
    total_trainings: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    promocode_usages: Mapped[list["PromocodeUsage"]] = relationship("PromocodeUsage", back_populates="user", cascade="all, delete-orphan")
    free_trainings: Mapped[list["FreeTraining"]] = relationship("FreeTraining", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Subscription(Base):
    """Subscription model."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_type: Mapped[SubscriptionType] = mapped_column(Enum(SubscriptionType), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)

    # For credits-based subscriptions
    credits_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    credits_left: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, type={self.subscription_type.value}, active={self.is_active})>"


class Payment(Base):
    """Payment model."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # cloudpayments/yookassa/prodamus
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # ID from payment provider
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    # Product info
    tariff: Mapped[str] = mapped_column(String(50), nullable=False)  # month/year/credits_5 etc.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    payment_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for additional data

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(user_id={self.user_id}, amount={self.amount}, status={self.status.value})>"


class Promocode(Base):
    """Promocode model."""
    __tablename__ = "promocodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # Enum stored as string for SQLite compatibility
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # Number of trainings/credits or 0 for free_month

    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    current_uses: Mapped[int] = mapped_column(Integer, default=0)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    usages: Mapped[list["PromocodeUsage"]] = relationship("PromocodeUsage", back_populates="promocode", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Promocode(code={self.code}, type={self.type}, uses={self.current_uses}/{self.max_uses})>"


class PromocodeUsage(Base):
    """Promocode usage tracking."""
    __tablename__ = "promocode_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    promocode_id: Mapped[int] = mapped_column(Integer, ForeignKey("promocodes.id"), nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="promocode_usages")
    promocode: Mapped["Promocode"] = relationship("Promocode", back_populates="usages")

    def __repr__(self) -> str:
        return f"<PromocodeUsage(user_id={self.user_id}, promocode_id={self.promocode_id})>"


class FreeTraining(Base):
    """Free trainings tracking."""
    __tablename__ = "free_trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    trainings_left: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[FreeTrainingSource] = mapped_column(Enum(FreeTrainingSource), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="free_trainings")

    def __repr__(self) -> str:
        return f"<FreeTraining(user_id={self.user_id}, left={self.trainings_left}, source={self.source.value})>"


class ChannelButton(Base):
    """Information about created channel buttons."""
    __tablename__ = "channel_buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    post_title: Mapped[str] = mapped_column(String(500), nullable=False)  # Название поста
    button_text: Mapped[str] = mapped_column(String(255), nullable=False)  # Название кнопки
    lead_magnet_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "bot" or "external"
    link: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Telegram ID админа

    def __repr__(self) -> str:
        return f"<ChannelButton(message_id={self.message_id}, post='{self.post_title}', button='{self.button_text}', type={self.lead_magnet_type})>"


class ChannelButtonClick(Base):
    """Tracking clicks on channel button."""
    __tablename__ = "channel_button_clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    button_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("channel_buttons.id"), nullable=True, index=True)
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Legacy fields (для обратной совместимости)
    post_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    button: Mapped[Optional["ChannelButton"]] = relationship("ChannelButton")

    def __repr__(self) -> str:
        return f"<ChannelButtonClick(telegram_id={self.telegram_id}, button_id={self.button_id}, clicked_at={self.clicked_at})>"
