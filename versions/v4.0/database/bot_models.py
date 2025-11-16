"""
Bot-specific models for SPIN Training Bot.

These models store SPIN-specific training data:
- TrainingHistory: completed training sessions with detailed metrics
- Future: SPIN-specific achievements, case library, etc.

This file is bot-specific and won't be shared with other bots.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_models import Base


class TrainingHistory(Base):
    """
    Training history for SPIN bot - stores completed training sessions.

    Useful for:
    - Analytics and progress tracking
    - Detailed performance reports
    - Case-by-case analysis
    """
    __tablename__ = "training_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Training session details
    training_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    scenario_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Scores and metrics
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    clarity_level: Mapped[int] = mapped_column(Integer, default=0)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    contextual_questions: Mapped[int] = mapped_column(Integer, default=0)

    # Question type breakdown (stored as JSON)
    # Example: {"situation": 2, "problem": 3, "implication": 2, "need_payoff": 1}
    per_type_counts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Case details (stored as JSON)
    # Example: {"client_name": "TechStartup", "problem": "Low sales", "context": "..."}
    case_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Full session data (for detailed analysis)
    # Snapshot of the entire session state at completion
    session_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TrainingHistory(telegram_id={self.telegram_id}, score={self.total_score}, date={self.training_date})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'training_date': self.training_date.isoformat() if self.training_date else None,
            'scenario_name': self.scenario_name,
            'total_score': self.total_score,
            'clarity_level': self.clarity_level,
            'question_count': self.question_count,
            'contextual_questions': self.contextual_questions,
            'per_type_counts': self.per_type_counts,
            'case_data': self.case_data
        }


# Future bot-specific models can be added here:
# - SPINAchievement (bot-specific achievements)
# - SPINCase (custom cases library)
# - SPINChallenge (daily/weekly challenges)
# - etc.
