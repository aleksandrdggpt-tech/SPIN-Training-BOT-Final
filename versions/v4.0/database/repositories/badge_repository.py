"""
Badge Repository - CRUD operations for UserBadge model.

Handles:
- Badge creation and awarding
- Badge retrieval (all badges, by bot, by user)
- Cross-bot badge visibility
"""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_models import UserBadge, User

logger = logging.getLogger(__name__)


class BadgeRepository:
    """Repository for UserBadge model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def award_badge(
        self,
        user_id: int,
        badge_type: str,
        earned_in_bot: str,
        metadata: Optional[dict] = None
    ) -> UserBadge:
        """
        Award a badge to user.

        Args:
            user_id: Internal user ID (not telegram_id)
            badge_type: Type of badge (e.g., "spin_master", "active_listener")
            earned_in_bot: Bot name where badge was earned (e.g., "spin_bot")
            metadata: Optional additional data (score, streak, etc.)

        Returns:
            Created UserBadge object
        """
        badge = UserBadge(
            user_id=user_id,
            badge_type=badge_type,
            earned_in_bot=earned_in_bot,
            badge_metadata=metadata or {}
        )
        self.session.add(badge)
        await self.session.flush()

        logger.info(f"Awarded badge '{badge_type}' to user {user_id} from {earned_in_bot}")
        return badge

    async def award_badge_by_telegram_id(
        self,
        telegram_id: int,
        badge_type: str,
        earned_in_bot: str,
        metadata: Optional[dict] = None
    ) -> Optional[UserBadge]:
        """
        Award a badge to user by telegram_id.

        Args:
            telegram_id: Telegram user ID
            badge_type: Type of badge
            earned_in_bot: Bot name
            metadata: Optional metadata

        Returns:
            Created UserBadge or None if user not found
        """
        # Find user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {telegram_id} not found for badge award")
            return None

        return await self.award_badge(user.id, badge_type, earned_in_bot, metadata)

    async def has_badge(
        self,
        telegram_id: int,
        badge_type: str,
        bot_name: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific badge.

        Args:
            telegram_id: Telegram user ID
            badge_type: Badge type to check
            bot_name: Optional - check only badges from specific bot

        Returns:
            True if user has the badge
        """
        stmt = (
            select(UserBadge)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .where(UserBadge.badge_type == badge_type)
        )

        if bot_name:
            stmt = stmt.where(UserBadge.earned_in_bot == bot_name)

        result = await self.session.execute(stmt)
        badge = result.scalar_one_or_none()

        return badge is not None

    async def get_user_badges(
        self,
        telegram_id: int,
        bot_name: Optional[str] = None
    ) -> List[UserBadge]:
        """
        Get all badges for a user.

        Args:
            telegram_id: Telegram user ID
            bot_name: Optional - filter by bot name

        Returns:
            List of UserBadge objects
        """
        stmt = (
            select(UserBadge)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .order_by(UserBadge.earned_at.desc())
        )

        if bot_name:
            stmt = stmt.where(UserBadge.earned_in_bot == bot_name)

        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_all_badges_by_type(self, badge_type: str) -> List[UserBadge]:
        """
        Get all instances of a specific badge type.

        Useful for analytics - "How many users have 'spin_master'?"

        Args:
            badge_type: Badge type to query

        Returns:
            List of UserBadge objects
        """
        stmt = (
            select(UserBadge)
            .where(UserBadge.badge_type == badge_type)
            .order_by(UserBadge.earned_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def count_badges_by_type(self, badge_type: str) -> int:
        """
        Count how many users earned a specific badge.

        Args:
            badge_type: Badge type

        Returns:
            Count
        """
        from sqlalchemy import func
        stmt = select(func.count(UserBadge.id)).where(UserBadge.badge_type == badge_type)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_user_badge_count(self, telegram_id: int) -> int:
        """
        Get total number of badges for user.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Badge count
        """
        from sqlalchemy import func
        stmt = (
            select(func.count(UserBadge.id))
            .join(User)
            .where(User.telegram_id == telegram_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete_badge(self, badge_id: int) -> bool:
        """
        Delete a specific badge.

        Args:
            badge_id: Badge ID

        Returns:
            True if deleted
        """
        stmt = select(UserBadge).where(UserBadge.id == badge_id)
        result = await self.session.execute(stmt)
        badge = result.scalar_one_or_none()

        if badge:
            await self.session.delete(badge)
            await self.session.flush()
            logger.info(f"Deleted badge {badge_id}")
            return True

        return False
