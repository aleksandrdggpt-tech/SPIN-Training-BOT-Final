"""
Payment handlers for SPIN Training Bot v4.
Telegram command handlers for payment flow.
"""

import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ConversationHandler
)

from database.database import get_session
from .subscription import (
    check_access, get_user_access_info,
    check_channel_subscription, grant_channel_subscription_bonus
)
from .promocodes import validate_promocode, activate_promocode
from .messages import (
    WELCOME_SALES, NO_ACCESS, FREE_ACCESS_CHANNEL,
    FREE_ACCESS_PROMO, PAYMENT_SUCCESS
)
from .keyboards import (
    get_payment_menu_keyboard, get_tariffs_keyboard,
    get_free_access_keyboard, get_promo_cancel_keyboard,
    get_access_denied_keyboard
)
from .states import PaymentStates, PromoInputStates
from .config import TARIFFS, format_price

logger = logging.getLogger(__name__)


# ==================== MAIN PAYMENT COMMAND ====================

async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /payment command - show payment menu."""
    telegram_id = update.effective_user.id

    async with get_session() as session:
        access_info = await get_user_access_info(telegram_id, session)

    message = f"""
{WELCOME_SALES}

📊 **Ваш статус:**
{access_info}

Выберите действие:
"""

    await update.message.reply_text(
        message,
        reply_markup=get_payment_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


# ==================== CALLBACK HANDLERS ====================

async def show_tariffs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tariffs."""
    query = update.callback_query
    await query.answer()

    message = """
💎 **ВЫБЕРИТЕ ТАРИФ:**

Все тарифы включают:
✅ Безлимитные тренировки
✅ Персональная обратная связь от AI
✅ Детальная статистика прогресса
✅ Доступ ко всем кейсам
"""

    await query.edit_message_text(
        message,
        reply_markup=get_tariffs_keyboard(show_credits=False)
    )
    return PaymentStates.SELECTING_TARIFF


async def select_tariff_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tariff selection."""
    query = update.callback_query
    await query.answer()

    # Extract tariff_id from callback_data: "payment:select_tariff:month"
    tariff_id = query.data.split(':')[-1]
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        await query.edit_message_text("❌ Тариф не найден")
        return PaymentStates.MAIN_MENU

    # Store selected tariff in user context
    context.user_data['selected_tariff'] = tariff_id

    price = format_price(tariff_id)
    discount_text = f"\n🔥 **Скидка:** {tariff['discount']}" if 'discount' in tariff else ""

    message = f"""
{tariff['emoji']} **{tariff['name']}**

💰 **Цена:** {price}{discount_text}
📝 {tariff['description']}

Нажмите "Оплатить" для перехода к оплате.
"""

    from .keyboards import get_tariff_confirmation_keyboard
    await query.edit_message_text(
        message,
        reply_markup=get_tariff_confirmation_keyboard(tariff_id)
    )
    return PaymentStates.CONFIRMING_TARIFF


async def pay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment initiation."""
    query = update.callback_query
    await query.answer()

    tariff_id = query.data.split(':')[-1]
    tariff = TARIFFS.get(tariff_id)

    if not tariff:
        await query.edit_message_text("❌ Тариф не найден")
        return PaymentStates.MAIN_MENU

    # TODO: Integrate with actual payment provider
    # For now, show stub message

    message = """
🚧 **ИНТЕГРАЦИЯ С ПЛАТЕЖНОЙ СИСТЕМОЙ**

В данный момент модуль оплаты готов к интеграции с:
• YooKassa
• CloudPayments
• Prodamus

Для завершения интеграции необходимо:
1. Добавить API ключи в .env
2. Реализовать методы в providers/
3. Настроить вебхуки для уведомлений

**Для тестирования:**
Используйте промокод TEST для получения бесплатного доступа.
"""

    from .keyboards import get_payment_menu_keyboard
    await query.edit_message_text(
        message,
        reply_markup=get_payment_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


# ==================== FREE ACCESS ====================

async def free_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show free access options."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        FREE_ACCESS_CHANNEL,
        reply_markup=get_free_access_keyboard()
    )
    return PaymentStates.CHECKING_SUBSCRIPTION


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user subscribed to channel."""
    query = update.callback_query
    telegram_id = update.effective_user.id

    await query.answer("Проверяем подписку...")

    async with get_session() as session:
        granted = await grant_channel_subscription_bonus(
            context.bot,
            telegram_id,
            session
        )

    if granted:
        message = """
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

Вы получили 2 бесплатные тренировки!

Теперь можете начать тренировку командой /start
"""
        from .keyboards import get_payment_menu_keyboard
        await query.edit_message_text(message, reply_markup=get_payment_menu_keyboard())
    else:
        message = """
❌ Подписка не найдена или вы уже получали бонус.

Пожалуйста:
1. Подпишитесь на канал @TaktikaKutuzova
2. Нажмите "Я подписался" еще раз
"""
        await query.edit_message_text(message, reply_markup=get_free_access_keyboard())

    return PaymentStates.MAIN_MENU


# ==================== PROMOCODE ====================

async def enter_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start promocode input."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        FREE_ACCESS_PROMO,
        reply_markup=get_promo_cancel_keyboard()
    )
    return PromoInputStates.WAITING_CODE


async def process_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process entered promocode."""
    code = update.message.text.strip().upper()
    telegram_id = update.effective_user.id

    async with get_session() as session:
        success, message = await activate_promocode(code, telegram_id, session)

    await update.message.reply_text(message)

    if success:
        await update.message.reply_text(
            "Теперь можете начать тренировку командой /start"
        )

    return ConversationHandler.END


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /promo command - activate promocode."""
    telegram_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🎟️ **АКТИВАЦИЯ ПРОМОКОДА**\n\n"
            "Использование: `/promo <код>`\n\n"
            "Пример: `/promo WINTER2025`\n\n"
            "Или используйте команду /payment для просмотра всех способов получения доступа."
        )
        return
    
    code = context.args[0].strip().upper()
    
    async with get_session() as session:
        success, message = await activate_promocode(code, telegram_id, session)
    
    await update.message.reply_text(message)
    
    if success:
        await update.message.reply_text(
            "Теперь можете начать тренировку командой /start"
        )


async def cancel_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel promocode input."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "Ввод промокода отменен.",
        reply_markup=get_payment_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


# ==================== BACK NAVIGATION ====================

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main payment menu."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    async with get_session() as session:
        access_info = await get_user_access_info(telegram_id, session)

    message = f"""
💳 **МЕНЮ ОПЛАТЫ**

{access_info}

Выберите действие:
"""

    await query.edit_message_text(
        message,
        reply_markup=get_payment_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close payment menu."""
    query = update.callback_query
    await query.answer()

    await query.delete_message()
    return ConversationHandler.END


# ==================== REGISTER HANDLERS ====================

def register_payment_handlers(application):
    """
    Register all payment-related handlers.

    Args:
        application: Telegram Application instance
    """
    # Payment command
    application.add_handler(CommandHandler("payment", payment_command))
    application.add_handler(CommandHandler("buy", payment_command))
    application.add_handler(CommandHandler("subscribe", payment_command))
    
    # Promocode command
    application.add_handler(CommandHandler("promo", promo_command))

    # Callback handlers for payment flow
    application.add_handler(CallbackQueryHandler(
        show_tariffs_callback,
        pattern="^payment:show_tariffs$"
    ))
    application.add_handler(CallbackQueryHandler(
        select_tariff_callback,
        pattern="^payment:select_tariff:"
    ))
    application.add_handler(CallbackQueryHandler(
        pay_callback,
        pattern="^payment:pay:"
    ))
    application.add_handler(CallbackQueryHandler(
        free_access_callback,
        pattern="^payment:free_access$"
    ))
    application.add_handler(CallbackQueryHandler(
        check_subscription_callback,
        pattern="^payment:check_subscription$"
    ))
    application.add_handler(CallbackQueryHandler(
        enter_promo_callback,
        pattern="^payment:enter_promo$"
    ))
    application.add_handler(CallbackQueryHandler(
        cancel_promo_callback,
        pattern="^payment:cancel_promo$"
    ))
    application.add_handler(CallbackQueryHandler(
        back_to_menu_callback,
        pattern="^payment:back_to_menu$"
    ))
    application.add_handler(CallbackQueryHandler(
        close_callback,
        pattern="^payment:close$"
    ))

    # Conversation handler for promocode input
    promo_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(enter_promo_callback, pattern="^payment:enter_promo$")],
        states={
            PromoInputStates.WAITING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_promocode)
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_promo_callback, pattern="^payment:cancel_promo$")]
    )
    application.add_handler(promo_conversation)

    logger.info("✅ Payment handlers registered")
    
    # Register admin handlers
    from .admin_handlers import register_admin_handlers
    register_admin_handlers(application)