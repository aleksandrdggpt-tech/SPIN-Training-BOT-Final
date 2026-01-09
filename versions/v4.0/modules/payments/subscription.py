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
from telegram.error import BadRequest

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
    logger.info(f"🔍 CHECK_ACCESS: telegram_id={telegram_id}")
    user = await get_or_create_user(telegram_id, session)
    logger.info(f"✅ Пользователь найден/создан: user_id={user.id}")

    # Check active subscriptions
    logger.info(f"📝 Проверяю активные подписки для user_id={user.id}")
    active_sub = await get_active_subscription(user.id, session)
    if active_sub:
        logger.info(f"✅ Найдена подписка: type={active_sub.subscription_type}, end_date={active_sub.end_date}, credits_left={getattr(active_sub, 'credits_left', None)}")
        if active_sub.subscription_type in [SubscriptionType.MONTH, SubscriptionType.YEAR]:
            # Time-based subscription
            logger.info(f"📝 Проверяю временную подписку: end_date={active_sub.end_date}, now={datetime.utcnow()}")
            if active_sub.end_date and active_sub.end_date > datetime.utcnow():
                result = {
                    'has_access': True,
                    'access_type': 'subscription',
                    'details': {
                        'subscription_type': active_sub.subscription_type.value,
                        'end_date': active_sub.end_date,
                        'days_left': (active_sub.end_date - datetime.utcnow()).days
                    }
                }
                logger.info(f"✅ ДОСТУП ЕСТЬ (подписка): {result}")
                return result
            else:
                logger.info(f"❌ Подписка истекла: end_date={active_sub.end_date}")
        elif active_sub.subscription_type == SubscriptionType.CREDITS:
            # Credits-based subscription
            logger.info(f"📝 Проверяю подписку на кредиты: credits_left={active_sub.credits_left}")
            if active_sub.credits_left and active_sub.credits_left > 0:
                result = {
                    'has_access': True,
                    'access_type': 'credits',
                    'details': {
                        'credits_left': active_sub.credits_left
                    }
                }
                logger.info(f"✅ ДОСТУП ЕСТЬ (кредиты): {result}")
                return result
            else:
                logger.info(f"❌ Кредиты закончились: credits_left={active_sub.credits_left}")

    # Check free trainings
    logger.info(f"📝 Проверяю бесплатные тренировки для user_id={user.id}")
    free_training = await get_free_training(user.id, session)
    if free_training:
        logger.info(f"✅ Найдена запись о бесплатных тренировках: trainings_left={free_training.trainings_left}, source={free_training.source}")
        if free_training.trainings_left > 0:
            result = {
                'has_access': True,
                'access_type': 'free_trainings',
                'details': {
                    'trainings_left': free_training.trainings_left,
                    'source': free_training.source.value
                }
            }
            logger.info(f"✅ ДОСТУП ЕСТЬ (бесплатные тренировки): {result}")
            return result
        else:
            logger.info(f"❌ Бесплатные тренировки закончились: trainings_left={free_training.trainings_left}")
    else:
        logger.info("❌ Запись о бесплатных тренировках не найдена")

    # No access
    result = {
        'has_access': False,
        'access_type': None,
        'details': {}
    }
    logger.info(f"❌ ДОСТУПА НЕТ: {result}")
    return result


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
    Проверяет, подписан ли пользователь на канал @TaktikaKutuzova.

    Использует метод getChatMember Telegram Bot API для проверки статуса пользователя в канале.

    Args:
        bot: Экземпляр Telegram бота (python-telegram-bot)
        telegram_id: Telegram ID пользователя

    Returns:
        bool: True если пользователь подписан (member, administrator, creator), False иначе

    Note:
        Статусы участников чата в python-telegram-bot:
        - ChatMemberStatus.MEMBER - обычный участник
        - ChatMemberStatus.ADMINISTRATOR - администратор
        - ChatMemberStatus.CREATOR - создатель канала
        - ChatMemberStatus.LEFT - покинул канал
        - ChatMemberStatus.KICKED - заблокирован
    """
    try:
        # Используем getChatMember для проверки статуса пользователя в канале
        # Это официальный метод Telegram Bot API
        member = await bot.get_chat_member(
            chat_id=f'@{CHANNEL_USERNAME}',  # Канал @TaktikaKutuzova
            user_id=telegram_id
        )

        # Проверяем статус участника
        # В python-telegram-bot статус возвращается как строка
        # Активные статусы: 'member', 'administrator', 'creator'
        # Неактивные: 'left', 'kicked', 'restricted'
        #
        # ВАЖНО: В некоторых версиях python-telegram-bot константа CREATOR может отсутствовать,
        # поэтому используем строковые значения для совместимости
        active_statuses = [
            'member',           # Обычный участник
            'administrator',    # Администратор
            'creator'           # Создатель канала (owner)
        ]

        # Проверяем статус (может быть строкой или константой)
        status_str = str(member.status).lower() if hasattr(member.status, 'lower') else str(member.status)
        is_subscribed = status_str in active_statuses or member.status in active_statuses
        logger.info(f"User {telegram_id} channel subscription status: {member.status}, subscribed: {is_subscribed}")
        return is_subscribed

    except BadRequest as e:
        # Обработка специфичных ошибок Telegram API
        error_message = str(e).lower()
        
        if 'member list is inaccessible' in error_message:
            # Бот не может получить доступ к списку участников канала
            # Это может быть из-за настроек приватности канала или прав бота
            # В этом случае считаем, что проверка невозможна, возвращаем False
            # (пользователь должен будет использовать кнопку "Я подписался" для подтверждения)
            logger.warning(f"Cannot check channel subscription for {telegram_id}: Member list is inaccessible. "
                         f"Bot may not have admin rights or channel privacy settings prevent access.")
            return False
        
        # Другие BadRequest ошибки (канал не найден, пользователь не найден и т.д.)
        logger.warning(f"BadRequest when checking channel subscription for {telegram_id}: {e}")
        return False
        
    except Exception as e:
        # Если произошла другая ошибка (например, канал не существует),
        # возвращаем False
        logger.error(f"Error checking channel subscription for {telegram_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
