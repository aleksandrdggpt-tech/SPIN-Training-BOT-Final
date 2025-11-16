"""
User Repository - CRUD operations for User model.

Handles:
- User creation and retrieval
- XP and level management
- Leaderboards
- User statistics
"""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Get existing user or create new one.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username (optional)
            first_name: User's first name (optional)
            last_name: User's last name (optional)

        Returns:
            User object
        """
        # Try to find existing user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update last activity
            user.last_activity = datetime.utcnow()
            # Update username/name if provided and changed
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name
            await self.session.flush()
            logger.debug(f"Found existing user: {telegram_id}")
        else:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                total_xp=0,
                level=1
            )
            self.session.add(user)
            await self.session.flush()
            logger.info(f"Created new user: {telegram_id}")

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User object or None if not found
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by internal ID.

        Args:
            user_id: Internal user ID

        Returns:
            User object or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_xp(self, telegram_id: int, xp: int) -> bool:
        """
        Add XP to user.

        Args:
            telegram_id: Telegram user ID
            xp: Amount of XP to add

        Returns:
            True if successful, False if user not found
        """
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(total_xp=User.total_xp + xp)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount > 0:
            logger.info(f"Added {xp} XP to user {telegram_id}")
            return True
        else:
            logger.warning(f"User {telegram_id} not found for XP update")
            return False

    async def update_level(self, telegram_id: int, new_level: int) -> bool:
        """
        Update user's level.

        Args:
            telegram_id: Telegram user ID
            new_level: New level value

        Returns:
            True if successful, False if user not found
        """
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(level=new_level)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount > 0:
            logger.info(f"Updated user {telegram_id} level to {new_level}")
            return True
        else:
            logger.warning(f"User {telegram_id} not found for level update")
            return False

    async def increment_training_count(self, telegram_id: int) -> bool:
        """
        Increment total_trainings counter.

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if successful
        """
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(total_trainings=User.total_trainings + 1)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def add_score(self, telegram_id: int, score: int) -> bool:
        """
        Add score to total_score.

        Args:
            telegram_id: Telegram user ID
            score: Score to add

        Returns:
            True if successful
        """
        stmt = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(total_score=User.total_score + score)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_leaderboard(self, limit: int = 10, offset: int = 0) -> List[User]:
        """
        Get top users by XP.

        Args:
            limit: Number of users to return
            offset: Offset for pagination

        Returns:
            List of User objects
        """
        stmt = (
            select(User)
            .order_by(User.total_xp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def get_user_rank(self, telegram_id: int) -> Optional[int]:
        """
        Get user's rank by XP (1 = highest XP).

        Args:
            telegram_id: Telegram user ID

        Returns:
            Rank (1-based) or None if user not found
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None

        # Count users with higher XP
        stmt = select(User).where(User.total_xp > user.total_xp)
        result = await self.session.execute(stmt)
        higher_users = len(list(result.scalars()))

        return higher_users + 1

    async def count_total_users(self) -> int:
        """
        Get total number of users.

        Returns:
            Total count
        """
        from sqlalchemy import func
        stmt = select(func.count(User.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def delete(self, telegram_id: int) -> bool:
        """
        Delete user (use with caution - cascades to all related data).

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if deleted, False if not found
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            await self.session.delete(user)
            await self.session.flush()
            logger.warning(f"Deleted user {telegram_id}")
            return True
        return False
