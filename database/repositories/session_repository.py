"""
Session Repository - CRUD operations for BotSession model.

Handles:
- Bot-specific session creation and retrieval
- Session data updates
- Stats management
- Multi-bot session isolation
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..base_models import BotSession, User

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for BotSession model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_or_create(
        self,
        user_id: int,
        bot_name: str
    ) -> BotSession:
        """
        Get existing bot session or create new one.

        Args:
            user_id: Internal user ID (not telegram_id)
            bot_name: Bot identifier (e.g., "spin_bot", "quiz_bot")

        Returns:
            BotSession object
        """
        # Try to find existing session
        stmt = (
            select(BotSession)
            .where(BotSession.user_id == user_id)
            .where(BotSession.bot_name == bot_name)
        )
        result = await self.session.execute(stmt)
        bot_session = result.scalar_one_or_none()

        if bot_session:
            # Update timestamp
            bot_session.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.debug(f"Found existing session for user {user_id} in {bot_name}")
        else:
            # Create new session
            bot_session = BotSession(
                user_id=user_id,
                bot_name=bot_name,
                session_data=BotSession.get_default_session(),
                stats_data=BotSession.get_default_stats()
            )
            self.session.add(bot_session)
            await self.session.flush()
            logger.info(f"Created new session for user {user_id} in {bot_name}")

        return bot_session

    async def get_by_telegram_id(
        self,
        telegram_id: int,
        bot_name: str
    ) -> Optional[BotSession]:
        """
        Get bot session by telegram_id.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier

        Returns:
            BotSession or None if not found
        """
        stmt = (
            select(BotSession)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .where(BotSession.bot_name == bot_name)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_by_telegram_id(
        self,
        telegram_id: int,
        bot_name: str
    ) -> Optional[BotSession]:
        """
        Get or create session by telegram_id.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier

        Returns:
            BotSession or None if user doesn't exist
        """
        # Find user first
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User {telegram_id} not found for session creation")
            return None

        return await self.get_or_create(user.id, bot_name)

    async def update_session_data(
        self,
        telegram_id: int,
        bot_name: str,
        session_data: dict
    ) -> bool:
        """
        Update session_data field.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier
            session_data: New session data

        Returns:
            True if successful
        """
        stmt = (
            update(BotSession)
            .where(
                BotSession.user_id == select(User.id)
                .where(User.telegram_id == telegram_id)
                .scalar_subquery()
            )
            .where(BotSession.bot_name == bot_name)
            .values(
                session_data=session_data,
                updated_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount > 0:
            logger.debug(f"Updated session_data for user {telegram_id} in {bot_name}")
            return True
        else:
            logger.warning(f"Session not found for user {telegram_id} in {bot_name}")
            return False

    async def update_stats_data(
        self,
        telegram_id: int,
        bot_name: str,
        stats_data: dict
    ) -> bool:
        """
        Update stats_data field.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier
            stats_data: New stats data

        Returns:
            True if successful
        """
        stmt = (
            update(BotSession)
            .where(
                BotSession.user_id == select(User.id)
                .where(User.telegram_id == telegram_id)
                .scalar_subquery()
            )
            .where(BotSession.bot_name == bot_name)
            .values(
                stats_data=stats_data,
                updated_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount > 0:
            logger.debug(f"Updated stats_data for user {telegram_id} in {bot_name}")
            return True
        else:
            logger.warning(f"Session not found for user {telegram_id} in {bot_name}")
            return False

    async def update_both(
        self,
        telegram_id: int,
        bot_name: str,
        session_data: dict,
        stats_data: dict
    ) -> bool:
        """
        Update both session_data and stats_data at once.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier
            session_data: New session data
            stats_data: New stats data

        Returns:
            True if successful
        """
        stmt = (
            update(BotSession)
            .where(
                BotSession.user_id == select(User.id)
                .where(User.telegram_id == telegram_id)
                .scalar_subquery()
            )
            .where(BotSession.bot_name == bot_name)
            .values(
                session_data=session_data,
                stats_data=stats_data,
                updated_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount > 0

    async def reset_session(
        self,
        telegram_id: int,
        bot_name: str,
        keep_stats: bool = True
    ) -> bool:
        """
        Reset session to default state.

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier
            keep_stats: If True, only reset session_data, keep stats_data

        Returns:
            True if successful
        """
        if keep_stats:
            # Only reset session_data
            stmt = (
                update(BotSession)
                .where(
                    BotSession.user_id == select(User.id)
                    .where(User.telegram_id == telegram_id)
                    .scalar_subquery()
                )
                .where(BotSession.bot_name == bot_name)
                .values(
                    session_data=BotSession.get_default_session(),
                    updated_at=datetime.utcnow()
                )
            )
        else:
            # Reset both session and stats
            stmt = (
                update(BotSession)
                .where(
                    BotSession.user_id == select(User.id)
                    .where(User.telegram_id == telegram_id)
                    .scalar_subquery()
                )
                .where(BotSession.bot_name == bot_name)
                .values(
                    session_data=BotSession.get_default_session(),
                    stats_data=BotSession.get_default_stats(),
                    updated_at=datetime.utcnow()
                )
            )

        result = await self.session.execute(stmt)
        await self.session.flush()

        if result.rowcount > 0:
            logger.info(f"Reset session for user {telegram_id} in {bot_name}")
            return True

        return False

    async def delete_session(
        self,
        telegram_id: int,
        bot_name: str
    ) -> bool:
        """
        Delete bot session (use with caution).

        Args:
            telegram_id: Telegram user ID
            bot_name: Bot identifier

        Returns:
            True if deleted
        """
        bot_session = await self.get_by_telegram_id(telegram_id, bot_name)
        if bot_session:
            await self.session.delete(bot_session)
            await self.session.flush()
            logger.warning(f"Deleted session for user {telegram_id} in {bot_name}")
            return True

        return False

    async def get_all_user_sessions(self, telegram_id: int) -> list[BotSession]:
        """
        Get all bot sessions for a user (across all bots).

        Useful for showing user their activity in different bots.

        Args:
            telegram_id: Telegram user ID

        Returns:
            List of BotSession objects
        """
        stmt = (
            select(BotSession)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .order_by(BotSession.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())
