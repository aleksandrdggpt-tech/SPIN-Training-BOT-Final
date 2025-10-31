"""
Subscription logic for SPIN Training Bot v4.
Handles access checks, subscription management, and decorator for protected functions.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from functools import wraps
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, Subscription, FreeTraining, SubscriptionType, FreeTrainingSource
from database.database import get_session
from .config import CHANNEL_USERNAME, FREE_TRAININGS_FOR_SUBSCRIPTION

logger = logging.getLogger(__name__)


# ==================== ACCESS CHECKING ====================

async def check_access(telegram_id: int, session: AsyncSession) -> Dict[str, Any]:
    """
    Check if user has access to training.

    Returns:
        dict with keys:
            - has_access: bool
            - access_type: str ('subscription', 'free_trainings', 'credits', None)
            - details: dict with additional info
    """
    user = await get_or_create_user(telegram_id, session)

    # Check active subscriptions
    active_sub = await get_active_subscription(user.id, session)
    if active_sub:
        if active_sub.subscription_type in [SubscriptionType.MONTH, SubscriptionType.YEAR]:
            # Time-based subscription
            if active_sub.end_date and active_sub.end_date > datetime.utcnow():
                return {
                    'has_access': True,
                    'access_type': 'subscription',
                    'details': {
                        'subscription_type': active_sub.subscription_type.value,
                        'end_date': active_sub.end_date,
                        'days_left': (active_sub.end_date - datetime.utcnow()).days
                    }
                }
        elif active_sub.subscription_type == SubscriptionType.CREDITS:
            # Credits-based subscription
            if active_sub.credits_left and active_sub.credits_left > 0:
                return {
                    'has_access': True,
                    'access_type': 'credits',
                    'details': {
                        'credits_left': active_sub.credits_left
                    }
                }

    # Check free trainings
    free_training = await get_free_training(user.id, session)
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


async def consume_access(telegram_id: int, session: AsyncSession) -> bool:
    """
    Consume one training access (for credits or free trainings).

    Returns:
        bool: True if access was consumed, False if no access available.
    """
    user = await get_or_create_user(telegram_id, session)

    # Try to consume credit
    active_sub = await get_active_subscription(user.id, session)
    if active_sub and active_sub.subscription_type == SubscriptionType.CREDITS:
        if active_sub.credits_left and active_sub.credits_left > 0:
            active_sub.credits_left -= 1
            await session.commit()
            logger.info(f"Consumed 1 credit for user {telegram_id}. {active_sub.credits_left} left.")
            return True

    # Try to consume free training
    free_training = await get_free_training(user.id, session)
    if free_training and free_training.trainings_left > 0:
        free_training.trainings_left -= 1
        await session.commit()
        logger.info(f"Consumed 1 free training for user {telegram_id}. {free_training.trainings_left} left.")
        return True

    return False


async def get_user_access_info(telegram_id: int, session: AsyncSession) -> str:
    """
    Get formatted access information for user.

    Returns:
        Formatted string with user's access status.
    """
    access_info = await check_access(telegram_id, session)

    if not access_info['has_access']:
        return "🔒 У вас нет активной подписки"

    access_type = access_info['access_type']
    details = access_info['details']

    if access_type == 'subscription':
        days_left = details['days_left']
        end_date = details['end_date'].strftime('%d.%m.%Y')
        return f"✅ Активная подписка до {end_date} (осталось {days_left} дней)"

    elif access_type == 'credits':
        credits_left = details['credits_left']
        return f"✅ Доступно тренировок: {credits_left}"

    elif access_type == 'free_trainings':
        trainings_left = details['trainings_left']
        source = details['source']
        return f"🎁 Бесплатных тренировок: {trainings_left} (источник: {source})"

    return "❓ Неизвестный статус доступа"


# ==================== SUBSCRIPTION DECORATOR ====================

def subscription_required(func: Callable) -> Callable:
    """
    Decorator to protect functions that require subscription.

    Usage:
        @subscription_required
        async def start_training(update, context):
            # Your code
            pass
    """
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        telegram_id = update.effective_user.id

        async with get_session() as session:
            access_info = await check_access(telegram_id, session)

            if not access_info['has_access']:
                # No access - show payment menu
                from .messages import NO_ACCESS
                from .keyboards import get_access_denied_keyboard

                await update.message.reply_text(
                    NO_ACCESS,
                    reply_markup=get_access_denied_keyboard()
                )
                return None

            # Check if we need to consume access (for credits/free trainings)
            access_type = access_info['access_type']
            if access_type in ['credits', 'free_trainings']:
                await consume_access(telegram_id, session)

        # User has access - execute function
        return await func(update, context, *args, **kwargs)

    return wrapper


# ==================== DATABASE HELPERS ====================

async def get_or_create_user(telegram_id: int, session: AsyncSession, username: Optional[str] = None, first_name: Optional[str] = None) -> User:
    """Get existing user or create new one."""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: {telegram_id}")

    return user


async def get_active_subscription(user_id: int, session: AsyncSession) -> Optional[Subscription]:
    """Get user's active subscription."""
    result = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.is_active == True)
        .order_by(Subscription.created_at.desc())
    )
    return result.scalar_one_or_none()


async def get_free_training(user_id: int, session: AsyncSession) -> Optional[FreeTraining]:
    """Get user's free training record."""
    result = await session.execute(
        select(FreeTraining)
        .where(FreeTraining.user_id == user_id)
        .where(FreeTraining.trainings_left > 0)
        .order_by(FreeTraining.created_at.desc())
    )
    return result.scalar_one_or_none()


async def create_subscription(
    telegram_id: int,
    subscription_type: SubscriptionType,
    duration_days: Optional[int] = None,
    credits: Optional[int] = None,
    session: Optional[AsyncSession] = None
) -> Subscription:
    """
    Create new subscription for user.

    Args:
        telegram_id: User's Telegram ID
        subscription_type: Type of subscription
        duration_days: Duration in days (for time-based subscriptions)
        credits: Number of credits (for credits-based subscriptions)
        session: Database session (if None, will create new one)

    Returns:
        Created Subscription object
    """
    close_session = False
    ctx_manager = None
    if session is None:
        ctx_manager = get_session()
        session = await ctx_manager.__aenter__()
        close_session = True

    try:
        user = await get_or_create_user(telegram_id, session)

        # Deactivate previous subscriptions
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        for old_sub in result.scalars():
            old_sub.is_active = False

        # Create new subscription
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=duration_days) if duration_days else None

        subscription = Subscription(
            user_id=user.id,
            subscription_type=subscription_type,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            credits_total=credits,
            credits_left=credits
        )

        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)

        logger.info(f"Created subscription for user {telegram_id}: {subscription_type.value}")
        return subscription

    finally:
        if close_session and ctx_manager:
            await ctx_manager.__aexit__(None, None, None)


async def add_free_trainings(
    telegram_id: int,
    trainings_count: int,
    source: FreeTrainingSource,
    session: Optional[AsyncSession] = None
) -> FreeTraining:
    """
    Add free trainings to user.

    Args:
        telegram_id: User's Telegram ID
        trainings_count: Number of free trainings to add
        source: Source of free trainings
        session: Database session

    Returns:
        FreeTraining object
    """
    close_session = False
    ctx_manager = None
    if session is None:
        ctx_manager = get_session()
        session = await ctx_manager.__aenter__()
        close_session = True

    try:
        user = await get_or_create_user(telegram_id, session)

        # Check if user already has free trainings from this source
        existing = await get_free_training(user.id, session)

        if existing:
            existing.trainings_left += trainings_count
            await session.commit()
            logger.info(f"Added {trainings_count} free trainings for user {telegram_id}. Total: {existing.trainings_left}")
            return existing
        else:
            free_training = FreeTraining(
                user_id=user.id,
                trainings_left=trainings_count,
                source=source
            )
            session.add(free_training)
            await session.commit()
            await session.refresh(free_training)
            logger.info(f"Created free trainings for user {telegram_id}: {trainings_count} from {source.value}")
            return free_training

    finally:
        if close_session and ctx_manager:
            await ctx_manager.__aexit__(None, None, None)


# ==================== CHANNEL SUBSCRIPTION CHECK ====================

async def check_channel_subscription(bot, telegram_id: int) -> bool:
    """
    Check if user is subscribed to the channel.

    Args:
        bot: Telegram bot instance
        telegram_id: User's Telegram ID

    Returns:
        bool: True if subscribed, False otherwise
    """
    try:
        member = await bot.get_chat_member(
            chat_id=f'@{CHANNEL_USERNAME}',
            user_id=telegram_id
        )
        is_subscribed = member.status in ['member', 'administrator', 'creator']
        logger.info(f"User {telegram_id} channel subscription: {is_subscribed}")
        return is_subscribed
    except Exception as e:
        logger.error(f"Error checking channel subscription for {telegram_id}: {e}")
        return False


async def grant_channel_subscription_bonus(bot, telegram_id: int, session: AsyncSession) -> bool:
    """
    Grant free trainings for channel subscription.

    Returns:
        bool: True if bonus was granted, False if user is not subscribed or already got bonus
    """
    # Check if user is subscribed
    if not await check_channel_subscription(bot, telegram_id):
        return False

    user = await get_or_create_user(telegram_id, session)

    # Check if user already got bonus from channel
    result = await session.execute(
        select(FreeTraining)
        .where(FreeTraining.user_id == user.id)
        .where(FreeTraining.source == FreeTrainingSource.CHANNEL)
    )
    existing_bonus = result.scalar_one_or_none()

    if existing_bonus:
        logger.info(f"User {telegram_id} already got channel subscription bonus")
        return False

    # Grant bonus
    await add_free_trainings(
        telegram_id,
        FREE_TRAININGS_FOR_SUBSCRIPTION,
        FreeTrainingSource.CHANNEL,
        session
    )

    return True
