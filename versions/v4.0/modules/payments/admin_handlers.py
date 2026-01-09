"""
Admin handlers for SPIN Training Bot v4.
Handles admin panel, promocode management, and user management.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)
from telegram.constants import ParseMode
from sqlalchemy import select
from enum import Enum, IntEnum

from database.database import get_session
from database import Promocode, PromocodeType
from .promocodes import (
    create_promocode, list_promocodes,
    get_promocode_stats, format_promocode_info
)
from .keyboards import get_admin_promo_keyboard
from .config import CHANNEL_USERNAME
from config import Config

logger = logging.getLogger(__name__)
config = Config()


class AdminPromoStates(IntEnum):
    """States for promocode creation dialog."""
    WAITING_CODE = 1
    WAITING_TYPE = 2
    WAITING_VALUE = 3
    WAITING_MAX_USES = 4
    WAITING_EXPIRES = 5




# ==================== ADMIN AUTHENTICATION ====================

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    admin_ids = config.ADMIN_USER_IDS
    if not admin_ids:
        return False
    return user_id in admin_ids


# ==================== ADMIN COMMAND ====================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - show admin panel."""
    telegram_id = update.effective_user.id
    
    # Check if user is admin
    if not is_admin(telegram_id):
        await update.message.reply_text(
            "❌ У вас нет прав доступа к админ-панели.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show admin panel with all commands
    message = """
🔧 **АДМИН-ПАНЕЛЬ**

**Доступные команды:**
`/admin` - Админ-панель

**Действия через меню:**
Выберите действие ниже:
"""
    
    await update.message.reply_text(
        message,
        reply_markup=get_admin_promo_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ==================== ADMIN CALLBACK HANDLERS ====================

async def admin_list_promos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of promocodes."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return

    try:
        # Get promocodes
        async with get_session() as session:
            promos = await list_promocodes(active_only=False, limit=20, session=session)

        if not promos:
            await query.edit_message_text("📭 Промокодов пока нет.")
            return

        # Format message
        lines = ["📋 **Список промокодов:**\n"]
        for promo in promos[:10]:  # Show first 10
            info = format_promocode_info(promo)
            lines.append(info)

        if len(promos) > 10:
            lines.append(f"\n... и ещё {len(promos) - 10}")

        message = "\n\n".join(lines)

        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Назад", callback_data="admin:back")]
            ])
        )

    except Exception as e:
        logger.error(f"Error listing promocodes: {e}")
        await query.edit_message_text("❌ Ошибка загрузки промокодов.")


async def admin_create_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start promocode creation dialog."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return ConversationHandler.END

    # Initialize context
    context.user_data['promo_data'] = {}

    # Start step-by-step creation
    message = """
➕ **СОЗДАНИЕ ПРОМОКОДА**

Шаг 1/5: Введите код промокода

Например: WINTER2025, SPRING50, SUMMER100

Или нажмите "Отмена" чтобы вернуться в меню.
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_promo")]
    ])

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return AdminPromoStates.WAITING_CODE


async def admin_promo_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle code input."""
    code = update.message.text.strip().upper()
    logger.info(f"Admin promocode handler received code: {code}")

    # Validate code
    if not code:
        await update.message.reply_text("❌ Код не может быть пустым. Попробуйте снова:")
        return AdminPromoStates.WAITING_CODE

    if not code.isalnum():
        await update.message.reply_text("❌ Код должен содержать только буквы и цифры. Попробуйте снова:")
        return AdminPromoStates.WAITING_CODE

    # Check if exists
    async with get_session() as session:
        result = await session.execute(
            select(Promocode).where(Promocode.code == code)
        )
        existing = result.scalar_one_or_none()

    if existing:
        await update.message.reply_text(f"❌ Промокод '{code}' уже существует. Попробуйте другой:")
        return AdminPromoStates.WAITING_CODE

    # Store code
    context.user_data['promo_data']['code'] = code

    # Show type selection
    message = """
🎁 **ВЫБЕРИТЕ ТИП ПРОМОКОДА**

Выберите тип награды для промокода:
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Бесплатные тренировки", callback_data="admin:promo_type:trainings")],
        [InlineKeyboardButton("📅 Бесплатный месяц", callback_data="admin:promo_type:free_month")],
        [InlineKeyboardButton("💎 Кредиты", callback_data="admin:promo_type:credits")],
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_promo")]
    ])

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return AdminPromoStates.WAITING_TYPE


async def admin_promo_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle type selection."""
    query = update.callback_query
    await query.answer()

    # Extract type from callback_data: "admin:promo_type:trainings"
    promo_type_str = query.data.split(':')[-1]

    type_mapping = {
        'trainings': PromocodeType.TRAININGS,
        'free_month': PromocodeType.FREE_MONTH,
        'credits': PromocodeType.CREDITS
    }

    promo_type = type_mapping.get(promo_type_str)
    if not promo_type:
        await query.edit_message_text("❌ Неизвестный тип")
        return ConversationHandler.END

    context.user_data['promo_data']['type'] = promo_type

    # Ask for value - send as new message
    message = f"""
💎 **ВВЕДИТЕ ЗНАЧЕНИЕ**

Выбран тип: {promo_type.value}

Введите количество:
• Для тренировок: количество бесплатных тренировок
• Для месяца: можно ввести 0 (типа будет бесплатный месяц)
• Для кредитов: количество кредитов

Или введите "пропустить" для значения 0.
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_promo")]
    ])

    # Edit the callback query message to show "Type selected"
    await query.edit_message_text(
        f"✅ Тип выбран: {promo_type.value}",
        parse_mode=ParseMode.MARKDOWN
    )

    # Send new message asking for value
    await query.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return AdminPromoStates.WAITING_VALUE


async def admin_promo_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle value input."""
    text = update.message.text.strip().lower()

    # Check for skip
    if text in ['пропустить', 'skip', '0']:
        value = 0
    else:
        try:
            value = int(text)
            if value < 0:
                await update.message.reply_text("❌ Значение не может быть отрицательным. Попробуйте снова:")
                return AdminPromoStates.WAITING_VALUE
        except ValueError:
            await update.message.reply_text("❌ Введите число или 'пропустить'. Попробуйте снова:")
            return AdminPromoStates.WAITING_VALUE

    context.user_data['promo_data']['value'] = value

    # Ask for max uses
    message = """
👥 **МАКСИМАЛЬНОЕ КОЛИЧЕСТВО ИСПОЛЬЗОВАНИЙ**

Введите максимальное количество использований.
Или введите "безлимит" для неограниченного использования.

Примеры:
• 100 - промокод можно использовать 100 раз
• безлимит - неограниченно
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_promo")]
    ])

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return AdminPromoStates.WAITING_MAX_USES


async def admin_promo_max_uses_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle max uses input."""
    text = update.message.text.strip().lower()

    # Check for unlimited
    if text in ['безлимит', 'unlimited', 'бесконечно']:
        max_uses = None
    else:
        try:
            max_uses = int(text)
            if max_uses <= 0:
                await update.message.reply_text("❌ Значение должно быть больше 0. Попробуйте снова:")
                return AdminPromoStates.WAITING_MAX_USES
        except ValueError:
            await update.message.reply_text("❌ Введите число или 'безлимит'. Попробуйте снова:")
            return AdminPromoStates.WAITING_MAX_USES

    context.user_data['promo_data']['max_uses'] = max_uses

    # Ask for expiration
    message = """
⏰ **СРОК ДЕЙСТВИЯ**

Введите срок действия в днях.
Или введите "без срока" для бессрочного промокода.

Примеры:
• 30 - действует 30 дней
• 7 - действует неделю
• без срока - не истекает
"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Отмена", callback_data="admin:cancel_promo")]
    ])

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    return AdminPromoStates.WAITING_EXPIRES


async def admin_promo_expires_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expiration input and create promocode."""
    text = update.message.text.strip().lower()

    # Check for no expiration
    if text in ['без срока', 'never', 'бессрочно']:
        expires_days = None
    else:
        try:
            expires_days = int(text)
            if expires_days <= 0:
                await update.message.reply_text("❌ Количество дней должно быть больше 0. Попробуйте снова:")
                return AdminPromoStates.WAITING_EXPIRES
        except ValueError:
            await update.message.reply_text("❌ Введите число или 'без срока'. Попробуйте снова:")
            return AdminPromoStates.WAITING_EXPIRES

    # Get all data
    promo_data = context.user_data.get('promo_data', {})
    code = promo_data.get('code')
    promo_type = promo_data.get('type')
    value = promo_data.get('value', 0)
    max_uses = promo_data.get('max_uses')

    # Create promocode
    async with get_session() as session:
        success, message_text, promo = await create_promocode(
            code=code,
            promo_type=promo_type,
            value=value,
            max_uses=max_uses,
            expires_days=expires_days,
            session=session
        )

    if success:
        final_message = f"""
✅ **ПРОМОКОД УСПЕШНО СОЗДАН!**

{message_text}

Теперь его можно использовать!
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в админ-панель", callback_data="admin:back")]
        ])
    else:
        final_message = f"""
❌ **ОШИБКА СОЗДАНИЯ ПРОМОКОДА**

{message_text}
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад в админ-панель", callback_data="admin:back")]
        ])

    await update.message.reply_text(
        final_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

    # Clean up
    context.user_data.pop('promo_data', None)

    return ConversationHandler.END


async def admin_cancel_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel promocode creation."""
    query = update.callback_query
    await query.answer()

    # Clean up
    context.user_data.pop('promo_data', None)

    await query.edit_message_text(
        "Создание промокода отменено.",
        reply_markup=get_admin_promo_keyboard()
    )

    return ConversationHandler.END


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return

    try:
        async with get_session() as session:
            # Get active promocodes
            active_promos = await list_promocodes(active_only=True, session=session)
            all_promos = await list_promocodes(active_only=False, limit=1000, session=session)

            # Count usages
            from database import PromocodeUsage
            result = await session.execute(
                select(PromocodeUsage)
            )
            usages = result.scalars().all()

            # Count by status
            active_count = len(active_promos)
            total_count = len(all_promos)
            expired_count = total_count - active_count
            usage_count = len(usages)
            
        message = f"""
📊 **СТАТИСТИКА**

**Промокоды:**
📈 Активных: {active_count}
📦 Всего: {total_count}
⏰ Истекло: {expired_count}
🎯 Использований: {usage_count}
"""

        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="admin:back")]
        ]

        await query.edit_message_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await query.edit_message_text("❌ Ошибка загрузки статистики.")


async def admin_give_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give free access to user."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return

    # TODO: Implement user access management
    message = """
🎁 **ВЫДАЧА ДОСТУПА**

Требуется ввод Telegram ID пользователя.

📝 **TODO:** Реализовать управление доступом.
"""

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="admin:back")]
        ])
    )


async def admin_commands_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of admin commands."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return

    message = """
📝 **СПИСОК АДМИН-КОМАНД**

**Основные команды:**
`/admin` - Админ-панель

**Действия через меню:**
• ➕ Создать промокод
• 📋 Список промокодов
• 🎁 Выдать доступ
• 📊 Статистика
"""

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ Назад", callback_data="admin:back")]
        ])
    )


async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to admin panel."""
    query = update.callback_query
    await query.answer()

    message = """
🔧 **АДМИН-ПАНЕЛЬ**

Выберите действие:
"""

    await query.edit_message_text(
        message,
        reply_markup=get_admin_promo_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


# ==================== REGISTER ADMIN HANDLERS ====================

def register_admin_handlers(application):
    """
    Register admin handlers.

    Args:
        application: Telegram Application instance
    """
    # Admin command
    application.add_handler(CommandHandler("admin", admin_command))

    # Admin callbacks
    application.add_handler(CallbackQueryHandler(
        admin_list_promos_callback,
        pattern="^admin:list_promos$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_stats_callback,
        pattern="^admin:stats$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_give_access_callback,
        pattern="^admin:give_access$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_back_callback,
        pattern="^admin:back$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_commands_callback,
        pattern="^admin:commands$"
    ))

    # ConversationHandler for promocode creation
    promo_creation_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            admin_create_promo_callback,
            pattern="^admin:create_promo$"
        )],
        states={
            AdminPromoStates.WAITING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_code_handler)
            ],
            AdminPromoStates.WAITING_TYPE: [
                CallbackQueryHandler(admin_promo_type_handler, pattern="^admin:promo_type:")
            ],
            AdminPromoStates.WAITING_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_value_handler)
            ],
            AdminPromoStates.WAITING_MAX_USES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_max_uses_handler)
            ],
            AdminPromoStates.WAITING_EXPIRES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_promo_expires_handler)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_cancel_promo_callback, pattern="^admin:cancel_promo$"),
            CallbackQueryHandler(admin_back_callback, pattern="^admin:back$")
        ]
    )
    application.add_handler(promo_creation_conversation)

    logger.info("✅ Admin handlers registered")

