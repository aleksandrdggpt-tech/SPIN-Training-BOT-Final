"""
Payment module for SPIN Training Bot v4.
Portable payment system with subscriptions, credits, and promocodes.

This module is designed to be easily transferable to other bots.
"""

from .config import TARIFFS, CHANNEL_USERNAME, FREE_TRAININGS_FOR_SUBSCRIPTION
from .subscription import check_access, subscription_required, get_user_access_info, create_subscription
from .promocodes import validate_promocode, activate_promocode, create_promocode
from .handlers import register_payment_handlers

__all__ = [
    'TARIFFS',
    'CHANNEL_USERNAME',
    'FREE_TRAININGS_FOR_SUBSCRIPTION',
    'check_access',
    'subscription_required',
    'get_user_access_info',
    'create_subscription',
    'validate_promocode',
    'activate_promocode',
    'create_promocode',
    'register_payment_handlers'
]
