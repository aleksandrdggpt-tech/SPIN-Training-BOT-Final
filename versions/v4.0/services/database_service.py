"""
Database Service - High-level API for database operations.

This service provides a simple, unified interface for bot.py to interact with the database.
It combines multiple repositories and handles common workflows.

Key features:
- Bot-agnostic design (works with any bot via bot_name parameter)
- Simplified API for common operations
- Transaction management
- Automatic user creation
- Cross-bot compatibility

Usage in bot.py:
    db_service = DatabaseService(bot_name="spin_bot")
    user_data = await db_service.get_user_session(telegram_id)
    await db_service.save_session(telegram_id, session_data, stats_data)
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import (
    get_session,
    User,
    UserBadge,
    BotSession,
    Subscription,
    SubscriptionType,
    FreeTrainingSource,
    TrainingHistory
)
from database.repositories import (
    UserRepository,
    BadgeRepository,
    SessionRepository,
    SubscriptionRepository
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Universal database service for bot operations.

    This service can be used in any bot - just change bot_name parameter.
    """

    def __init__(self, bot_name: str = None):
        """
        Initialize database service.

        Args:
            bot_name: Bot identifier (e.g., "spin_bot", "quiz_bot")
                        If not provided, uses BOT_NAME from environment
        """
        self.bot_name = bot_name or os.getenv('BOT_NAME', 'spin_bot')
        logger.info(f"DatabaseService initialized for bot: {self.bot_name}")

    # ==================== USER SESSION OPERATIONS ====================

    async def get_user_session(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete user session data for current bot.

        This is the main method for bot.py to get user data.
        Returns UserService-compatible format.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username (optional, for user creation/update)
            first_name: User's first name (optional)

        Returns:
            dict with keys:
                - user: User info (id, telegram_id, xp, level, etc.)
                - session: Current session data (bot-specific)
                - stats: Bot-specific statistics
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            session_repo = SessionRepository(session)

            # Get or create user
            user = await user_repo.get_or_create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )

            # Get or create bot session
            bot_session = await session_repo.get_or_create(
                user_id=user.id,
                bot_name=self.bot_name
            )

            return {
                'user': user.to_dict(),
                'session': bot_session.session_data,
                'stats': bot_session.stats_data
            }

    async def save_session(
        self,
        telegram_id: int,
        session_data: dict,
        stats_data: dict
    ) -> bool:
        """
        Save session and stats data.

        Args:
            telegram_id: Telegram user ID
            session_data: Session data to save
            stats_data: Stats data to save

        Returns:
            True if successful
        """
        async with get_session() as session:
            session_repo = SessionRepository(session)

            success = await session_repo.update_both(
                telegram_id=telegram_id,
                bot_name=self.bot_name,
                session_data=session_data,
                stats_data=stats_data
            )

            if success:
                logger.debug(f"Saved session for user {telegram_id}")
            else:
                logger.warning(f"Failed to save session for user {telegram_id}")

            return success

    async def reset_session(
        self,
        telegram_id: int,
        scenario_config: Optional[Dict] = None
    ) -> bool:
        """
        Reset user's session to default state.

        Args:
            telegram_id: Telegram user ID
            scenario_config: Optional scenario config for custom reset

        Returns:
            True if successful
        """
        async with get_session() as session:
            session_repo = SessionRepository(session)

            # Reset session, keep stats
            success = await session_repo.reset_session(
                telegram_id=telegram_id,
                bot_name=self.bot_name,
                keep_stats=True
            )

            if success:
                logger.info(f"Reset session for user {telegram_id}")

            return success

    # ==================== GAMIFICATION OPERATIONS ====================

    async def add_xp_and_check_level_up(
        self,
        telegram_id: int,
        xp_to_add: int,
        levels_config: Optional[List[dict]] = None
    ) -> Dict[str, Any]:
        """
        Add XP to user and check for level up.

        Args:
            telegram_id: Telegram user ID
            xp_to_add: Amount of XP to add
            levels_config: Level configuration from scenario

        Returns:
            dict with:
                - leveled_up: bool
                - old_level: int
                - new_level: int
                - total_xp: int
        """
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_telegram_id(telegram_id)
            if not user:
                logger.warning(f"User {telegram_id} not found for XP addition")
                return {
                    'leveled_up': False,
                    'old_level': 1,
                    'new_level': 1,
                    'total_xp': 0
                }

            old_level = user.level
            old_xp = user.total_xp

            # Add XP
            await user_repo.add_xp(telegram_id, xp_to_add)

            # Calculate new level
            new_xp = old_xp + xp_to_add
            new_level = self._calculate_level(new_xp, levels_config)

            # Update level if changed
            leveled_up = False
            if new_level > old_level:
                await user_repo.update_level(telegram_id, new_level)
                leveled_up = True
                logger.info(f"🎊 User {telegram_id} leveled up: {old_level} → {new_level}")

            return {
                'leveled_up': leveled_up,
                'old_level': old_level,
                'new_level': new_level,
                'total_xp': new_xp
            }

    def _calculate_level(self, xp: int, levels_config: Optional[List[dict]]) -> int:
        """
        Calculate level based on XP and levels configuration.

        Args:
            xp: Total XP
            levels_config: List of level configs from scenario

        Returns:
            Level number
        """
        if not levels_config:
            # Default: level = xp // 100 + 1
            return min(xp // 100 + 1, 100)

        try:
            eligible = [
                int(l.get('level', 1))
                for l in levels_config
                if xp >= int(l.get('min_xp', 0))
            ]
            return max(eligible) if eligible else 1
        except Exception as e:
            logger.error(f"Error calculating level: {e}")
            return 1

    async def award_badge(
        self,
        telegram_id: int,
        badge_type: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Award a badge to user.

        Args:
            telegram_id: Telegram user ID
            badge_type: Badge identifier (e.g., "spin_master", "first_training")
            metadata: Optional metadata (score, streak, etc.)

        Returns:
            True if badge awarded (False if user already has it)
        """
        async with get_session() as session:
            badge_repo = BadgeRepository(session)

            # Check if user already has this badge
            has_badge = await badge_repo.has_badge(
                telegram_id=telegram_id,
                badge_type=badge_type,
                bot_name=self.bot_name
            )

            if has_badge:
                logger.debug(f"User {telegram_id} already has badge {badge_type}")
                return False

            # Award badge
            badge = await badge_repo.award_badge_by_telegram_id(
                telegram_id=telegram_id,
                badge_type=badge_type,
                earned_in_bot=self.bot_name,
                metadata=metadata
            )

            if badge:
                logger.info(f"🏆 Awarded badge '{badge_type}' to user {telegram_id}")
                return True

            return False

    async def get_user_badges(
        self,
        telegram_id: int,
        all_bots: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's badges.

        Args:
            telegram_id: Telegram user ID
            all_bots: If True, returns badges from all bots. If False, only from current bot.

        Returns:
            List of badge dictionaries
        """
        async with get_session() as session:
            badge_repo = BadgeRepository(session)

            badges = await badge_repo.get_user_badges(
                telegram_id=telegram_id,
                bot_name=None if all_bots else self.bot_name
            )

            return [
                {
                    'badge_type': b.badge_type,
                    'earned_in_bot': b.earned_in_bot,
                    'earned_at': b.earned_at.isoformat(),
                    'metadata': b.badge_metadata
                }
                for b in badges
            ]

    # ==================== SUBSCRIPTION & ACCESS OPERATIONS ====================

    async def check_access(self, telegram_id: int) -> Dict[str, Any]:
        """
        Check if user has access to training.

        Returns:
            dict with keys:
                - has_access: bool
                - access_type: str or None ('subscription', 'credits', 'free_trainings')
                - details: dict with additional info
        """
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)
            return await sub_repo.check_access(telegram_id)

    async def consume_access(self, telegram_id: int) -> bool:
        """
        Consume one training access (for credits or free trainings).

        For time-based subscriptions, does nothing (unlimited).

        Args:
            telegram_id: Telegram user ID

        Returns:
            True if access consumed or not needed
        """
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)
            return await sub_repo.consume_access(telegram_id)

    async def create_subscription(
        self,
        telegram_id: int,
        subscription_type: SubscriptionType,
        duration_days: Optional[int] = None,
        credits: Optional[int] = None
    ) -> bool:
        """
        Create subscription for user.

        Args:
            telegram_id: Telegram user ID
            subscription_type: Type of subscription
            duration_days: Duration in days (for time-based)
            credits: Number of credits (for credits-based)

        Returns:
            True if successful
        """
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)

            subscription = await sub_repo.create_subscription(
                telegram_id=telegram_id,
                subscription_type=subscription_type,
                duration_days=duration_days,
                credits=credits
            )

            return subscription is not None

    async def add_free_trainings(
        self,
        telegram_id: int,
        count: int,
        source: FreeTrainingSource
    ) -> bool:
        """
        Add free trainings to user.

        Args:
            telegram_id: Telegram user ID
            count: Number of trainings
            source: Source of free trainings

        Returns:
            True if successful
        """
        async with get_session() as session:
            sub_repo = SubscriptionRepository(session)

            free_training = await sub_repo.add_free_trainings(
                telegram_id=telegram_id,
                count=count,
                source=source
            )

            return free_training is not None

    # ==================== TRAINING HISTORY OPERATIONS ====================

    async def save_training_history(
        self,
        telegram_id: int,
        total_score: int,
        clarity_level: int,
        question_count: int,
        contextual_questions: int,
        per_type_counts: Optional[dict] = None,
        case_data: Optional[dict] = None,
        session_snapshot: Optional[dict] = None,
        scenario_name: Optional[str] = None
    ) -> bool:
        """
        Save completed training session to history.

        Args:
            telegram_id: Telegram user ID
            total_score: Final score
            clarity_level: Clarity level achieved
            question_count: Number of questions asked
            contextual_questions: Number of contextual questions
            per_type_counts: Question type breakdown
            case_data: Case details
            session_snapshot: Full session state
            scenario_name: Scenario name

        Returns:
            True if successful
        """
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Get user
            user = await user_repo.get_by_telegram_id(telegram_id)
            if not user:
                logger.warning(f"User {telegram_id} not found for history save")
                return False

            # Create history record
            history = TrainingHistory(
                user_id=user.id,
                telegram_id=telegram_id,
                total_score=total_score,
                clarity_level=clarity_level,
                question_count=question_count,
                contextual_questions=contextual_questions,
                per_type_counts=per_type_counts or {},
                case_data=case_data,
                session_snapshot=session_snapshot,
                scenario_name=scenario_name
            )

            session.add(history)
            await session.flush()

            logger.info(f"Saved training history for user {telegram_id}, score: {total_score}")
            return True

    async def get_user_training_history(
        self,
        telegram_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's training history.

        Args:
            telegram_id: Telegram user ID
            limit: Number of records to return

        Returns:
            List of training history dictionaries
        """
        from sqlalchemy import select

        async with get_session() as session:
            stmt = (
                select(TrainingHistory)
                .where(TrainingHistory.telegram_id == telegram_id)
                .order_by(TrainingHistory.training_date.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            history = list(result.scalars())

            return [h.to_dict() for h in history]

    # ==================== STATISTICS OPERATIONS ====================

    async def update_user_stats_after_training(
        self,
        telegram_id: int,
        session_score: int,
        scenario_config: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Update all user statistics after training completion.

        This method:
        1. Increments training count
        2. Adds score to total
        3. Adds XP and checks level up
        4. Updates last training date in bot session

        Args:
            telegram_id: Telegram user ID
            session_score: Score from completed session
            scenario_config: Scenario configuration (for level calculation)

        Returns:
            dict with update results (leveled_up, new_level, etc.)
        """
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Increment counters
            await user_repo.increment_training_count(telegram_id)
            await user_repo.add_score(telegram_id, session_score)

        # Add XP and check level up (in separate transaction)
        levels_config = scenario_config.get('ranking', {}).get('levels', []) if scenario_config else []
        level_result = await self.add_xp_and_check_level_up(
            telegram_id=telegram_id,
            xp_to_add=session_score,
            levels_config=levels_config
        )

        logger.info(f"Updated stats for user {telegram_id}: score={session_score}, level={level_result['new_level']}")

        return level_result

    async def get_user_info(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete user information.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User info dict or None if not found
        """
        async with get_session() as session:
            user_repo = UserRepository(session)

            user = await user_repo.get_by_telegram_id(telegram_id)
            if not user:
                return None

            return user.to_dict()

    async def get_leaderboard(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get top users by XP.

        Args:
            limit: Number of users
            offset: Offset for pagination

        Returns:
            List of user dictionaries
        """
        async with get_session() as session:
            user_repo = UserRepository(session)

            users = await user_repo.get_leaderboard(limit=limit, offset=offset)
            return [u.to_dict() for u in users]

    async def get_user_rank(self, telegram_id: int) -> Optional[int]:
        """
        Get user's rank in leaderboard.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Rank (1 = highest) or None if user not found
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            return await user_repo.get_user_rank(telegram_id)

    # ==================== UTILITY METHODS ====================

    async def ensure_user_exists(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> bool:
        """
        Ensure user exists in database.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name

        Returns:
            True if user exists or was created
        """
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            return user is not None
