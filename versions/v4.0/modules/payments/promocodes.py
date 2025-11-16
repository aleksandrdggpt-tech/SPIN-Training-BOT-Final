"""
Promocode system for SPIN Training Bot v4.
Handles promocode creation, validation, and activation.
"""

import logging
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    Promocode, PromocodeUsage, PromocodeType,
    FreeTrainingSource, SubscriptionType
)
from database.database import get_session
from .subscription import get_or_create_user, create_subscription, add_free_trainings

logger = logging.getLogger(__name__)


# ==================== PROMOCODE VALIDATION ====================

async def validate_promocode(code: str, telegram_id: int, session: AsyncSession) -> Dict[str, Any]:
    """
    Validate promocode.

    Returns:
        dict with keys:
            - valid: bool
            - promo: Promocode object or None
            - error: str (if not valid)
    """
    # Find promocode
    result = await session.execute(
        select(Promocode).where(Promocode.code == code.upper())
    )
    promo = result.scalar_one_or_none()

    if not promo:
        return {
            'valid': False,
            'promo': None,
            'error': '❌ Промокод не найден'
        }

    # Check expiration
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return {
            'valid': False,
            'promo': promo,
            'error': '⏰ Промокод истек'
        }

    # Check max uses
    if promo.max_uses and promo.current_uses >= promo.max_uses:
        return {
            'valid': False,
            'promo': promo,
            'error': '🚫 Промокод уже использован максимальное количество раз'
        }

    # Check if user already used this promocode
    user = await get_or_create_user(telegram_id, session)
    result = await session.execute(
        select(PromocodeUsage)
        .where(PromocodeUsage.user_id == user.id)
        .where(PromocodeUsage.promocode_id == promo.id)
    )
    usage = result.scalar_one_or_none()

    if usage:
        return {
            'valid': False,
            'promo': promo,
            'error': '🔒 Вы уже использовали этот промокод'
        }

    # Valid
    return {
        'valid': True,
        'promo': promo,
        'error': None
    }


# ==================== PROMOCODE ACTIVATION ====================

async def activate_promocode(code: str, telegram_id: int, session: AsyncSession) -> Tuple[bool, str]:
    """
    Activate promocode for user.

    Returns:
        Tuple of (success: bool, message: str)
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info(f"🔍 ACTIVATE_PROMOCODE: code={code}, telegram_id={telegram_id}")
    logger.info("=" * 80)

    # Validate
    logger.info(f"📝 Вызываю validate_promocode(code={code}, telegram_id={telegram_id})")
    validation = await validate_promocode(code, telegram_id, session)
    logger.info(f"✅ validate_promocode вернул: valid={validation['valid']}, error={validation.get('error', 'None')}")

    if not validation['valid']:
        logger.warning(f"❌ Промокод не прошел валидацию: {validation.get('error', 'Unknown error')}")
        logger.info("=" * 80)
        logger.info(f"🏁 ACTIVATE_PROMOCODE завершен: success=False")
        logger.info("=" * 80)
        return False, validation['error']

    promo = validation['promo']
    logger.info(f"✅ Промокод найден: id={promo.id}, type={promo.type}, value={promo.value}")
    user = await get_or_create_user(telegram_id, session)
    logger.info(f"✅ Пользователь найден/создан: user_id={user.id}")

    try:
        # Apply promocode based on type
        logger.info(f"📝 Применяю промокод типа: {promo.type}")
        if promo.type == PromocodeType.TRAININGS.value:
            # Add free trainings
            await add_free_trainings(
                telegram_id,
                promo.value,
                FreeTrainingSource.PROMOCODE,
                session
            )
            message = f"✅ Промокод активирован!\n\nВы получили {promo.value} бесплатных тренировок!"

        elif promo.type == PromocodeType.FREE_MONTH.value:
            # Add free month subscription
            await create_subscription(
                telegram_id,
                SubscriptionType.MONTH,
                duration_days=30,
                session=session
            )
            message = "✅ Промокод активирован!\n\nВы получили месячную подписку (30 дней)!"

        elif promo.type == PromocodeType.CREDITS.value:
            # Add credits
            await create_subscription(
                telegram_id,
                SubscriptionType.CREDITS,
                credits=promo.value,
                session=session
            )
            message = f"✅ Промокод активирован!\n\nВы получили {promo.value} тренировок!"

        else:
            return False, "❌ Неизвестный тип промокода"

        # Record usage
        logger.info(f"📝 Создаю запись об использовании промокода: user_id={user.id}, promocode_id={promo.id}")
        usage = PromocodeUsage(
            user_id=user.id,
            promocode_id=promo.id
        )
        session.add(usage)

        # Update promocode stats
        logger.info(f"📝 Обновляю статистику промокода: current_uses={promo.current_uses}, max_uses={promo.max_uses}")
        promo.current_uses += 1

        await session.commit()

        logger.info(f"Promocode '{code}' activated by user {telegram_id}")
        return True, message

    except Exception as e:
        await session.rollback()
        logger.error(f"Error activating promocode '{code}' for user {telegram_id}: {e}")
        return False, "❌ Ошибка активации промокода. Попробуйте позже."


# ==================== PROMOCODE CREATION (ADMIN) ====================

async def create_promocode(
    code: str,
    promo_type: PromocodeType,
    value: int,
    max_uses: Optional[int] = None,
    expires_days: Optional[int] = None,
    session: Optional[AsyncSession] = None
) -> Tuple[bool, str, Optional[Promocode]]:
    """
    Create new promocode (admin function).

    Args:
        code: Promocode string (will be uppercased)
        promo_type: Type of promocode
        value: Number of trainings/credits
        max_uses: Maximum number of uses (None = unlimited)
        expires_days: Expiration in days (None = never expires)
        session: Database session

    Returns:
        Tuple of (success: bool, message: str, promocode: Promocode or None)
    """
    close_session = False
    ctx_manager = None
    if session is None:
        ctx_manager = get_session()
        session = await ctx_manager.__aenter__()
        close_session = True

    try:
        code = code.upper().strip()

        # Check if code already exists
        result = await session.execute(
            select(Promocode).where(Promocode.code == code)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return False, f"❌ Промокод '{code}' уже существует", None

        # Calculate expiration date
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        # Create promocode
        promo = Promocode(
            code=code,
            type=promo_type.value,  # Convert enum to string
            value=value,
            max_uses=max_uses,
            expires_at=expires_at
        )

        session.add(promo)
        await session.commit()
        await session.refresh(promo)

        logger.info(f"Created promocode: {code} ({promo_type.value}, value={value})")

        expires_text = f" до {expires_at.strftime('%d.%m.%Y')}" if expires_at else ""
        uses_text = f" (макс. использований: {max_uses})" if max_uses else ""

        message = f"""✅ Промокод создан!

Код: `{code}`
Тип: {promo_type.value}
Значение: {value}
Действует{expires_text}{uses_text}"""

        return True, message, promo

    except Exception as e:
        if not close_session:
            await session.rollback()
        logger.error(f"Error creating promocode '{code}': {e}")
        return False, f"❌ Ошибка создания промокода: {e}", None

    finally:
        if close_session and ctx_manager:
            await ctx_manager.__aexit__(None, None, None)


async def generate_random_promocode(prefix: str = "", length: int = 8) -> str:
    """
    Generate random promocode.

    Args:
        prefix: Prefix for the code (e.g., "SPIN")
        length: Length of random part

    Returns:
        Generated code
    """
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    code = f"{prefix}{random_part}" if prefix else random_part
    return code


# ==================== PROMOCODE LISTING ====================

async def list_promocodes(
    active_only: bool = True,
    limit: int = 50,
    session: Optional[AsyncSession] = None
) -> list[Promocode]:
    """
    List promocodes (admin function).

    Args:
        active_only: Show only active (non-expired) promocodes
        limit: Maximum number of promocodes to return
        session: Database session

    Returns:
        List of Promocode objects
    """
    close_session = False
    ctx_manager = None
    if session is None:
        ctx_manager = get_session()
        session = await ctx_manager.__aenter__()
        close_session = True

    try:
        query = select(Promocode).order_by(Promocode.created_at.desc()).limit(limit)

        if active_only:
            query = query.where(
                (Promocode.expires_at == None) | (Promocode.expires_at > datetime.utcnow())
            )

        result = await session.execute(query)
        return list(result.scalars())

    finally:
        if close_session and ctx_manager:
            await ctx_manager.__aexit__(None, None, None)


async def get_promocode_stats(promo_id: int, session: AsyncSession) -> Dict[str, Any]:
    """
    Get usage statistics for a promocode.

    Returns:
        dict with usage info
    """
    result = await session.execute(
        select(Promocode).where(Promocode.id == promo_id)
    )
    promo = result.scalar_one_or_none()

    if not promo:
        return {'error': 'Promocode not found'}

    # Get usage details
    result = await session.execute(
        select(PromocodeUsage)
        .where(PromocodeUsage.promocode_id == promo_id)
        .order_by(PromocodeUsage.used_at.desc())
    )
    usages = list(result.scalars())

    is_expired = promo.expires_at and promo.expires_at < datetime.utcnow()
    is_exhausted = promo.max_uses and promo.current_uses >= promo.max_uses

    return {
        'code': promo.code,
        'type': promo.type.value,
        'value': promo.value,
        'current_uses': promo.current_uses,
        'max_uses': promo.max_uses,
        'expires_at': promo.expires_at,
        'is_expired': is_expired,
        'is_exhausted': is_exhausted,
        'is_active': not (is_expired or is_exhausted),
        'recent_usages': usages[:10]
    }


# ==================== HELPER FUNCTIONS ====================

def format_promocode_info(promo: Promocode) -> str:
    """Format promocode info for display."""
    expires_text = ""
    if promo.expires_at:
        if promo.expires_at < datetime.utcnow():
            expires_text = f"\n❌ Истек: {promo.expires_at.strftime('%d.%m.%Y')}"
        else:
            expires_text = f"\n⏰ Действует до: {promo.expires_at.strftime('%d.%m.%Y')}"

    uses_text = ""
    if promo.max_uses:
        uses_text = f"\n📊 Использований: {promo.current_uses}/{promo.max_uses}"
    else:
        uses_text = f"\n📊 Использований: {promo.current_uses} (безлимит)"

    type_emoji = {
        "trainings": "🎁",
        "free_month": "📅",
        "credits": "💎"
    }.get(promo.type, "🎟️")

    # Get human-readable type name
    type_name = {
        "trainings": "Бесплатные тренировки",
        "free_month": "Бесплатный месяц",
        "credits": "Кредиты"
    }.get(promo.type, promo.type)

    return f"""
{type_emoji} **{promo.code}**
Тип: {type_name}
Значение: {promo.value}{expires_text}{uses_text}
""".strip()
