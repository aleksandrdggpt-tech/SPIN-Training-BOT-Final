"""
Base models for multi-bot system.
These models are shared across all bots and provide:
- Unified user management
- Cross-bot gamification (XP, levels, badges)
- Unified subscription/payment system
- Bot-agnostic data storage

This module can be copied to any bot project.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Boolean, DateTime, Enum, ForeignKey, Numeric, Text, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ==================== ENUMS ====================

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


# ==================== CORE MODELS ====================

class User(Base):
    """
    Universal user model shared across all bots.

    Key features:
    - Unified by telegram_id
    - Cross-bot gamification (total_xp, level)
    - Relationships to badges, subscriptions, payments
    - Bot-specific sessions stored separately (see BotSession)
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Registration and activity
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Cross-bot gamification
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)

    # Legacy statistics (for compatibility with old payment system)
    total_trainings: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    badges: Mapped[list["UserBadge"]] = relationship(
        "UserBadge",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    promocode_usages: Mapped[list["PromocodeUsage"]] = relationship(
        "PromocodeUsage",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    free_trainings: Mapped[list["FreeTraining"]] = relationship(
        "FreeTraining",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    bot_sessions: Mapped[list["BotSession"]] = relationship(
        "BotSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, level={self.level})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'total_xp': self.total_xp,
            'level': self.level,
            'total_trainings': self.total_trainings,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }


class UserBadge(Base):
    """
    Cross-bot badge system.

    A user can earn badges in any bot, and they are visible everywhere.
    Example: "spin_master" badge earned in SPIN bot is shown in Quiz bot.
    """
    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Badge identification
    badge_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Examples: "spin_master", "quiz_guru", "active_listener", "first_training"

    earned_in_bot: Mapped[str] = mapped_column(String(50), nullable=False)
    # Examples: "spin_bot", "quiz_bot", "challenger_bot"

    earned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Optional badge metadata (JSON for flexibility)
    badge_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Example: {"score": 250, "streak": 5, "case_id": "tech_startup"}

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="badges")

    def __repr__(self) -> str:
        return f"<UserBadge(user_id={self.user_id}, type={self.badge_type}, bot={self.earned_in_bot})>"


# ==================== SUBSCRIPTION & PAYMENT MODELS ====================

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

    # Metadata
    payment_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

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
    value: Mapped[int] = mapped_column(Integer, nullable=False)

    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    current_uses: Mapped[int] = mapped_column(Integer, default=0)

    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    usages: Mapped[list["PromocodeUsage"]] = relationship(
        "PromocodeUsage",
        back_populates="promocode",
        cascade="all, delete-orphan"
    )

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


# ==================== BOT-SPECIFIC SESSION MODEL ====================

class BotSession(Base):
    """
    Bot-specific session storage.

    This model stores session data for each bot separately.
    Multiple bots can have sessions for the same user (telegram_id).

    Example:
    - User 123456 has session in "spin_bot" with SPIN training data
    - Same user has session in "quiz_bot" with quiz data
    - But they share the same User record (XP, level, badges)
    """
    __tablename__ = "bot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    bot_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Examples: "spin_bot", "quiz_bot", "challenger_bot"

    # Current session data (flexible JSON)
    session_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Example for SPIN bot:
    # {
    #   "question_count": 5,
    #   "clarity_level": 75,
    #   "chat_state": "in_progress",
    #   "per_type_counts": {"situation": 2, "problem": 3},
    #   "client_case": "tech_startup",
    #   "last_client_response": "..."
    # }

    # Bot-specific statistics (flexible JSON)
    stats_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Example:
    # {
    #   "total_trainings": 10,
    #   "best_score": 185,
    #   "achievements_unlocked": ["spin_master", "active_listener"],
    #   "maestro_streak": 3,
    #   "last_training_date": "2025-01-15T10:30:00"
    # }

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bot_sessions")

    def __repr__(self) -> str:
        return f"<BotSession(user_id={self.user_id}, bot={self.bot_name})>"

    def to_dict(self) -> dict:
        """Convert to UserService-compatible format."""
        return {
            'session': self.session_data,
            'stats': self.stats_data
        }

    @staticmethod
    def get_default_session() -> dict:
        """Default session structure for SPIN bot."""
        return {
            'question_count': 0,
            'clarity_level': 0,
            'per_type_counts': {},
            'client_case': '',
            'case_data': None,
            'last_question_type': '',
            'chat_state': 'new',
            'contextual_questions': 0,
            'last_client_response': '',
            'context_streak': 0,
            'feedback_in_progress': False,
            'last_feedback_ts': 0
        }

    @staticmethod
    def get_default_stats() -> dict:
        """Default stats structure for SPIN bot."""
        return {
            'total_trainings': 0,
            'total_questions': 0,
            'best_score': 0,
            'total_xp': 0,
            'current_level': 1,
            'achievements_unlocked': [],
            'level_up_notification': {
                'should_show': False,
                'old_level': 1,
                'new_level': 1
            },
            'maestro_streak': 0,
            'last_training_date': None,
            'recent_cases': []
        }
