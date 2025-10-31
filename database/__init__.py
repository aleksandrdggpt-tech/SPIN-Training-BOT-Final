"""
Database module for SPIN Training Bot v4.
Contains SQLAlchemy models and database connection logic.

New modular structure:
- base_models.py: Shared models across all bots (User, Subscription, BotSession, etc.)
- bot_models.py: SPIN-specific models (TrainingHistory, etc.)
- models.py: Legacy models (kept for backward compatibility)
- training_models.py: Legacy training models (kept for backward compatibility)
"""

from .database import init_db, get_session, close_db

# New modular models (preferred)
from .base_models import (
    Base,
    User,
    UserBadge,
    Subscription,
    Payment,
    Promocode,
    PromocodeUsage,
    FreeTraining,
    BotSession,
    # Enums
    SubscriptionType,
    PaymentStatus,
    PromocodeType,
    FreeTrainingSource
)
from .bot_models import TrainingHistory

# Legacy models (for backward compatibility with existing code)
from .training_models import TrainingUser

__all__ = [
    # Connection
    'init_db',
    'get_session',
    'close_db',
    'Base',

    # Core models (new modular structure)
    'User',
    'UserBadge',
    'BotSession',

    # Subscription & Payment models
    'Subscription',
    'Payment',
    'Promocode',
    'PromocodeUsage',
    'FreeTraining',

    # Bot-specific models
    'TrainingHistory',

    # Legacy models (backward compatibility)
    'TrainingUser',

    # Enums
    'SubscriptionType',
    'PaymentStatus',
    'PromocodeType',
    'FreeTrainingSource'
]
