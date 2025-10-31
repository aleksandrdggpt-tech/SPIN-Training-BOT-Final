"""
SQLAlchemy models for training data (sessions, stats, achievements).

Separate from payment models to keep concerns separated.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base_models import Base


class TrainingUser(Base):
    """
    Training user model - stores training sessions and statistics.

    Separate from User model (payments) to keep payment and training data independent.
    """
    __tablename__ = "training_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Registration and activity
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Session data (current training session)
    # Stored as JSON to maintain flexibility
    session_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Statistics (historical data across all trainings)
    stats_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TrainingUser(telegram_id={self.telegram_id}, username={self.username})>"

    def to_dict(self) -> dict:
        """Convert to dictionary format compatible with current UserService."""
        return {
            'session': self.session_data or self._get_default_session(),
            'stats': self.stats_data or self._get_default_stats()
        }

    @staticmethod
    def _get_default_session() -> dict:
        """Default session structure."""
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
            'context_streak': 0
        }

    @staticmethod
    def _get_default_stats() -> dict:
        """Default stats structure."""
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


# TrainingHistory model moved to bot_models.py to avoid duplication
