"""
Subscription Repository - CRUD operations for Subscription and related models.

Handles:
- Subscription creation and management
- Access checking
- Credits consumption
- Free trainings management
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_models import (
    Subscription,
    FreeTraining,
    User,
    SubscriptionType,
    FreeTrainingSource
)

logger = logging.getLogger(__name__)


class SubscriptionRepository:
    """Repository for Subscription and FreeTraining operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    # ==================== SUBSCRIPTION OPERATIONS ====================

    async def get_active_subscription(
        self,
        telegram_id: int
    ) -> Optional[Subscription]:
        """
        Get user's active subscription.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Active Subscription or None
        """
        stmt = (
            select(Subscription)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .where(Subscription.is_active == True)
            .order_by(Subscription.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_subscription(
        self,
        telegram_id: int,
        subscription_type: SubscriptionType,
        duration_days: Optional[int] = None,
        credits: Optional[int] = None,
        auto_renew: bool = False
    ) -> Optional[Subscription]:
        """
        Create new subscription for user.

        Args:
            telegram_id: Telegram user ID
            subscription_type: Type of subscription
            duration_days: Duration in days (for time-based)
            credits: Number of credits (for credits-based)
            auto_renew: Auto-renewal flag

        Returns:
            Created Subscription or None if user not found
        """
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {telegram_id} not found for subscription creation")
            return None

        # Deactivate previous subscriptions
        await self._deactivate_user_subscriptions(user.id)

        # Create new subscription
        start_date = datetime.utcnow()
        end_date = None
        if duration_days:
            end_date = start_date + timedelta(days=duration_days)

        subscription = Subscription(
            user_id=user.id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            auto_renew=auto_renew,
            credits_total=credits,
            credits_left=credits
        )

        self.session.add(subscription)
        await self.session.flush()

        logger.info(
            f"Created subscription for user {telegram_id}: "
            f"type={subscription_type.value}, duration={duration_days}, credits={credits}"
        )

        return subscription

    async def _deactivate_user_subscriptions(self, user_id: int) -> None:
        """
        Deactivate all subscriptions for user.

        Args:
            user_id: Internal user ID
        """
        stmt = (
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def consume_credit(self, telegram_id: int) -> bool:
        """
        Consume one credit from active credits-based subscription.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if credit consumed, False if no credits or subscription
        """
        subscription = await self.get_active_subscription(telegram_id)

        if not subscription:
            return False

        if subscription.subscription_type != SubscriptionType.CREDITS:
            # Not a credits-based subscription, no consumption needed
            return True

        if not subscription.credits_left or subscription.credits_left <= 0:
            # No credits left
            subscription.is_active = False
            await self.session.flush()
            logger.info(f"Deactivated subscription for {telegram_id} - no credits left")
            return False

        # Consume one credit
        subscription.credits_left -= 1
        await self.session.flush()

        logger.info(f"Consumed 1 credit for {telegram_id}. {subscription.credits_left} left.")

        # Deactivate if no credits left
        if subscription.credits_left == 0:
            subscription.is_active = False
            await self.session.flush()

        return True

    async def check_subscription_valid(self, telegram_id: int) -> bool:
        """
        Check if user has valid active subscription.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if subscription is valid
        """
        subscription = await self.get_active_subscription(telegram_id)

        if not subscription:
            return False

        # Check time-based subscriptions
        if subscription.subscription_type in [SubscriptionType.MONTH, SubscriptionType.YEAR]:
            if subscription.end_date and subscription.end_date > datetime.utcnow():
                return True
            else:
                # Expired, deactivate
                subscription.is_active = False
                await self.session.flush()
                return False

        # Check credits-based
        if subscription.subscription_type == SubscriptionType.CREDITS:
            if subscription.credits_left and subscription.credits_left > 0:
                return True
            else:
                subscription.is_active = False
                await self.session.flush()
                return False

        return False

    # ==================== FREE TRAINING OPERATIONS ====================

    async def get_free_training(
        self,
        telegram_id: int
    ) -> Optional[FreeTraining]:
        """
        Get user's free training record.

        Args:
            telegram_id: Telegram user ID

        Returns:
            FreeTraining with trainings_left > 0 or None
        """
        stmt = (
            select(FreeTraining)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .where(FreeTraining.trainings_left > 0)
            .order_by(FreeTraining.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_free_trainings(
        self,
        telegram_id: int,
        count: int,
        source: FreeTrainingSource
    ) -> Optional[FreeTraining]:
        """
        Add free trainings to user.

        Args:
            telegram_id: Telegram user ID
            count: Number of trainings to add
            source: Source of free trainings

        Returns:
            FreeTraining object or None if user not found
        """
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {telegram_id} not found for free trainings")
            return None

        # Check if user already has free trainings from this source
        existing = await self.get_free_training(telegram_id)

        if existing and existing.source == source:
            # Add to existing
            existing.trainings_left += count
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.info(
                f"Added {count} free trainings to user {telegram_id}. "
                f"Total: {existing.trainings_left}"
            )
            return existing
        else:
            # Create new record
            free_training = FreeTraining(
                user_id=user.id,
                trainings_left=count,
                source=source
            )
            self.session.add(free_training)
            await self.session.flush()
            logger.info(
                f"Created {count} free trainings for user {telegram_id} "
                f"from {source.value}"
            )
            return free_training

    async def consume_free_training(self, telegram_id: int) -> bool:
        """
        Consume one free training.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if training consumed, False if no trainings available
        """
        free_training = await self.get_free_training(telegram_id)

        if not free_training or free_training.trainings_left <= 0:
            return False

        free_training.trainings_left -= 1
        free_training.updated_at = datetime.utcnow()
        await self.session.flush()

        logger.info(
            f"Consumed 1 free training for {telegram_id}. "
            f"{free_training.trainings_left} left."
        )

        return True

    # ==================== ACCESS CHECKING ====================

    async def check_access(self, telegram_id: int) -> dict:
        """
        Comprehensive access check.

        Returns dict with:
        - has_access: bool
        - access_type: str or None
        - details: dict with additional info

        Args:
            telegram_id: Telegram user ID

        Returns:
            Access info dictionary
        """
        # Check subscription
        subscription = await self.get_active_subscription(telegram_id)
        if subscription:
            if subscription.subscription_type in [SubscriptionType.MONTH, SubscriptionType.YEAR]:
                if subscription.end_date and subscription.end_date > datetime.utcnow():
                    return {
                        'has_access': True,
                        'access_type': 'subscription',
                        'details': {
                            'subscription_type': subscription.subscription_type.value,
                            'end_date': subscription.end_date,
                            'days_left': (subscription.end_date - datetime.utcnow()).days
                        }
                    }

            elif subscription.subscription_type == SubscriptionType.CREDITS:
                if subscription.credits_left and subscription.credits_left > 0:
                    return {
                        'has_access': True,
                        'access_type': 'credits',
                        'details': {
                            'credits_left': subscription.credits_left
                        }
                    }

        # Check free trainings
        free_training = await self.get_free_training(telegram_id)
        if free_training and free_training.trainings_left > 0:
            return {
                'has_access': True,
                'access_type': 'free_trainings',
                'details': {
                    'trainings_left': free_training.trainings_left,
                    'source': free_training.source.value
                }
            }

        # No access
        return {
            'has_access': False,
            'access_type': None,
            'details': {}
        }

    async def consume_access(self, telegram_id: int) -> bool:
        """
        Consume one access (credit or free training).

        For time-based subscriptions, does nothing (unlimited access).

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if access consumed or not needed
        """
        # Check subscription first
        subscription = await self.get_active_subscription(telegram_id)
        if subscription:
            if subscription.subscription_type == SubscriptionType.CREDITS:
                return await self.consume_credit(telegram_id)
            else:
                # Time-based subscription, no consumption needed
                return True

        # Try free trainings
        return await self.consume_free_training(telegram_id)
