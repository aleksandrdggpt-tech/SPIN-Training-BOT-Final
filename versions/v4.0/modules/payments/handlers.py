"""
Payment handlers for SPIN Training Bot v4.
Telegram command handlers for payment flow.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    FREE_ACCESS_PROMO, PAYMENT_SUCCESS,
    SPIN_S_SITUATION, SPIN_P_PROBLEM, SPIN_I_IMPLICATION, SPIN_N_NEED_PAYOFF,
    SOCIAL_PROOF_SHORT, BENEFITS_SHORT, HOW_IT_WORKS
)
from .keyboards import (
    get_payment_menu_keyboard, get_tariffs_keyboard,
    get_free_access_keyboard, get_promo_cancel_keyboard,
    get_access_denied_keyboard,
    get_spin_s_keyboard, get_spin_p_keyboard, get_spin_i_keyboard, get_spin_n_keyboard
)
from .states import PaymentStates, PromoInputStates
from .config import TARIFFS, format_price

logger = logging.getLogger(__name__)


# ==================== MAIN PAYMENT COMMAND ====================

async def payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /payment command - show payment menu with subscription status."""
    telegram_id = update.effective_user.id

    from .subscription import get_active_subscription, get_or_create_user
    from .messages import get_subscription_status_text, WELCOME_SALES

    async with get_session() as session:
        user = await get_or_create_user(telegram_id, session)
        subscription = await get_active_subscription(user.id, session)

        # Проверяем, что подписка действительно активна (не истекла)
        has_active_subscription = False
        if subscription and subscription.is_active:
            from datetime import datetime
            if subscription.end_date and subscription.end_date > datetime.utcnow():
                has_active_subscription = True

        status_text = get_subscription_status_text(subscription if has_active_subscription else None)
        access_info = await get_user_access_info(telegram_id, session)

    # Формируем стартовое сообщение (как в /start)
    from .keyboards import get_start_menu_keyboard, get_start_training_keyboard

    welcome_message = WELCOME_SALES

    # Добавляем информацию о статусе пользователя
    status_message = ""
    if access_info['has_access']:
        if access_info['access_type'] == 'free_trainings':
            trainings_left = access_info['details'].get('trainings_left', 0)
            source = access_info['details'].get('source', 'unknown')
            status_message = f"\n\n📊 **Ваш статус:**\n🎁 Бесплатных тренировок: {trainings_left} (источник: {source})"
        elif access_info['access_type'] == 'subscription':
            status_message = "\n\n🔑 У вас есть активная подписка."
    else:
        status_message = "\n\n🔑 У вас нет активной подписки."

    full_message = welcome_message + status_message

    # Определяем клавиатуру
    if access_info['has_access']:
        keyboard = get_start_training_keyboard()
    else:
        keyboard = get_start_menu_keyboard()

    await update.message.reply_text(
        full_message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return PaymentStates.MAIN_MENU


# ==================== CALLBACK HANDLERS ====================

async def show_tariffs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tariffs (v4.0 - перенаправляет на бесплатный доступ)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Перенаправляю...")

    # В v4.0 оплата отключена, перенаправляем на бесплатный доступ
    from .messages import FREE_ACCESS_CHANNEL
    from .keyboards import get_free_access_keyboard

    await query.edit_message_text(
        FREE_ACCESS_CHANNEL,
        reply_markup=get_free_access_keyboard()
    )
    return PaymentStates.CHECKING_SUBSCRIPTION


async def select_tariff_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tariff selection."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Выбираю тариф...")

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
    # Немедленный ответ для лучшего UX
    await query.answer("Подготавливаю оплату...")

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

    # В v4.0 возвращаем к стартовому меню
    from .keyboards import get_start_menu_keyboard
    await query.edit_message_text(
        message,
        reply_markup=get_start_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


# ==================== FREE ACCESS ====================

async def free_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопки "🎁 Бесплатный доступ" на главном экране.

    Показывает меню с предложением подписаться на канал @TaktikaKutuzova
    для получения 2 бесплатных тренировок.

    В меню есть:
    - Кнопка "📢 Подписаться на канал" (открывает канал в Telegram)
    - Кнопка "✅ Я подписался, проверить" (проверяет подписку через getChatMember)
    - Кнопка "🎟️ Ввести промокод"
    - Кнопка "« Назад"
    """
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Загружаю опции...")

    # Показываем меню с предложением подписаться на канал
    await query.edit_message_text(
        FREE_ACCESS_CHANNEL,
        reply_markup=get_free_access_keyboard()
    )
    return PaymentStates.CHECKING_SUBSCRIPTION


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик кнопки "✅ Я подписался, проверить".

    Проверяет подписку пользователя на канал @TaktikaKutuzova используя метод getChatMember.

    Логика работы:
    1. Проверяет подписку через check_channel_subscription (использует bot.get_chat_member)
    2. Если не подписан - показывает сообщение с просьбой подписаться
    3. Если подписан - выдает бонус (2 бесплатные тренировки) через grant_channel_subscription_bonus
    4. Проверяет доступ пользователя через check_access
    5. Если есть доступ - показывает кнопку "Начать тренировку"
    6. Если доступа нет - показывает меню оплаты
    """
    query = update.callback_query
    telegram_id = update.effective_user.id

    try:
        await query.answer("Проверяем подписку...")
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")

    try:
        async with get_session() as session:
            # ШАГ 1: Проверяем, подписан ли пользователь на канал
            # Используется метод getChatMember Telegram Bot API
            try:
                is_subscribed = await check_channel_subscription(context.bot, telegram_id)
            except Exception as e:
                logger.error(f"Error checking channel subscription: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await query.edit_message_text(
                    "❌ Ошибка при проверке подписки. Попробуйте позже.",
                    reply_markup=get_free_access_keyboard()
                )
                return PaymentStates.MAIN_MENU

            # ШАГ 2: Если пользователь не подписан - просим подписаться
            if not is_subscribed:
                message = """
❌ **ПОДПИСКА НЕ НАЙДЕНА**

Пожалуйста:
1. 📢 Подпишитесь на канал @TaktikaKutuzova
2. ✅ Нажмите "Я подписался" еще раз для проверки
"""
                try:
                    await query.edit_message_text(message, reply_markup=get_free_access_keyboard())
                except Exception as edit_error:
                    # Обрабатываем ошибку "Message is not modified" - это нормально,
                    # если пользователь нажал кнопку повторно с тем же результатом
                    if "not modified" in str(edit_error).lower():
                        logger.debug(f"Message not modified for user {telegram_id} - same content")
                    else:
                        logger.error(f"Error editing message: {edit_error}")
                return PaymentStates.MAIN_MENU

            # ШАГ 3: Пользователь подписан - выдаем бонус (если еще не получал)
            # grant_channel_subscription_bonus проверяет, получал ли пользователь бонус ранее
            # и выдает 2 бесплатные тренировки только один раз
            try:
                granted = await grant_channel_subscription_bonus(
                    context.bot,
                    telegram_id,
                    session
                )
            except Exception as e:
                logger.error(f"Error granting channel subscription bonus: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                granted = False  # Продолжаем работу даже если не удалось выдать бонус

            # Проверяем доступ пользователя
            try:
                access_info = await check_access(telegram_id, session)
            except Exception as e:
                logger.error(f"Error checking access: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                await query.edit_message_text(
                    "❌ Ошибка при проверке доступа. Попробуйте позже.",
                    reply_markup=get_free_access_keyboard()
                )
                return PaymentStates.MAIN_MENU

            if granted:
                # Бонус только что выдан
                message = """
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

Вы получили 2 бесплатные тренировки!
"""
            else:
                # Бонус уже был выдан ранее, но пользователь подписан
                if access_info['has_access']:
                    # У пользователя еще есть доступ
                    trainings_left = access_info['details'].get('trainings_left', 0)
                    message = f"""
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

У вас осталось {trainings_left} бесплатных тренировок.
"""
                else:
                    # Доступ закончился, но подписка есть
                    message = """
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

Вы уже получали бонус за подписку, но бесплатные тренировки закончились.
"""

            # Проверяем, пришел ли пользователь через кнопку канала
            channel_button_link = context.user_data.get('channel_button_link')
            channel_button_type = context.user_data.get('channel_button_type')
            
            if channel_button_link:
                # Пользователь пришел через кнопку канала - выдаем ссылку
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                if channel_button_type == "external":
                    # Внешняя ссылка - показываем кнопку со ссылкой
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔗 Получить доступ", url=channel_button_link)]
                    ])
                    success_message = """
✅ **ПОДПИСКА ПОДТВЕРЖДЕНА!**

Ваша ссылка готова! Нажмите на кнопку ниже, чтобы получить доступ.
"""
                else:
                    # Доступ к боту - показываем кнопку "Начать тренировку" если есть доступ
                    if access_info['has_access']:
                        from .keyboards import get_start_training_keyboard
                        keyboard = get_start_training_keyboard()
                        success_message = message + "\n\nНажмите кнопку ниже, чтобы начать тренировку:"
                    else:
                        # Доступа нет, но подписка подтверждена
                        from .keyboards import get_start_menu_keyboard
                        keyboard = get_start_menu_keyboard()
                        success_message = message + "\n\nВы можете получить бесплатный доступ:"
                
                try:
                    await query.edit_message_text(
                        success_message,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                    # Очищаем данные о кнопке после выдачи ссылки
                    context.user_data.pop('channel_button_link', None)
                    context.user_data.pop('channel_button_type', None)
                    context.user_data.pop('channel_button_id', None)
                    logger.info(f"✅ Link issued to user {telegram_id}: {channel_button_link}, type: {channel_button_type}")
                except Exception as edit_error:
                    if "not modified" in str(edit_error).lower():
                        logger.debug(f"Message not modified for user {telegram_id} - same content")
                    else:
                        logger.error(f"Error editing message: {edit_error}")
            else:
                # Обычная проверка подписки (не через кнопку канала)
                # Если у пользователя есть доступ - показываем кнопку "Начать тренировку"
                if access_info['has_access']:
                    from .keyboards import get_start_training_keyboard
                    try:
                        await query.edit_message_text(
                            message + "\nНажмите кнопку ниже, чтобы начать тренировку:",
                            reply_markup=get_start_training_keyboard()
                        )
                    except Exception as edit_error:
                        # Обрабатываем ошибку "Message is not modified" - это нормально,
                        # если пользователь нажал кнопку повторно с тем же результатом
                        if "not modified" in str(edit_error).lower():
                            logger.debug(f"Message not modified for user {telegram_id} - same content")
                        else:
                            logger.error(f"Error editing message: {edit_error}")
                else:
                    # Если доступа нет - показываем стартовое меню
                    from .keyboards import get_start_menu_keyboard
                    try:
                        await query.edit_message_text(
                            message + "\nВы можете получить бесплатный доступ:",
                            reply_markup=get_start_menu_keyboard()
                        )
                    except Exception as edit_error:
                        # Обрабатываем ошибку "Message is not modified"
                        if "not modified" in str(edit_error).lower():
                            logger.debug(f"Message not modified for user {telegram_id} - same content")
                        else:
                            logger.error(f"Error editing message: {edit_error}")
    except Exception as e:
        logger.error(f"Unexpected error in check_subscription_callback: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        try:
            await query.edit_message_text(
                "❌ Произошла ошибка при проверке подписки. Попробуйте позже.",
                reply_markup=get_free_access_keyboard()
            )
        except Exception as e2:
            # Обрабатываем ошибку "Message is not modified" и другие ошибки
            if "not modified" in str(e2).lower():
                logger.debug(f"Message not modified for user {telegram_id} - same content")
            else:
                logger.error(f"Error sending error message: {e2}")

    return PaymentStates.MAIN_MENU


# ==================== PROMOCODE ====================

async def enter_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start promocode input."""
    query = update.callback_query
    telegram_id = query.from_user.id

    logger.info("=" * 80)
    logger.info(f"🔍 ENTER_PROMO_CALLBACK: Пользователь {telegram_id}")
    logger.info("=" * 80)

    # Немедленный ответ для лучшего UX
    await query.answer("Введите промокод...")

    # Очищаем флаг, если он был установлен ранее
    context.user_data.pop('promocode_just_entered', None)
    logger.info(f"✅ Очищен флаг promocode_just_entered")

    await query.edit_message_text(
        FREE_ACCESS_PROMO,
        reply_markup=get_promo_cancel_keyboard()
    )

    logger.info(f"✅ Сообщение отправлено, возвращаю состояние: {PromoInputStates.WAITING_CODE}")
    logger.info(f"✅ Conversation state будет установлен в: {PromoInputStates.WAITING_CODE}")
    logger.info("=" * 80)
    logger.info(f"🏁 ENTER_PROMO_CALLBACK завершен для пользователя {telegram_id}")
    logger.info("=" * 80)

    return PromoInputStates.WAITING_CODE


async def process_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process entered promocode."""
    code = update.message.text.strip().upper()
    telegram_id = update.effective_user.id

    logger.info("=" * 80)
    logger.info(f"🔍 PROCESS_PROMOCODE: Пользователь {telegram_id}, промокод: {code}")
    logger.info("=" * 80)

    async with get_session() as session:
        logger.info(f"📝 Вызываю activate_promocode(code={code}, telegram_id={telegram_id})")
        success, message = await activate_promocode(code, telegram_id, session)
        logger.info(f"✅ activate_promocode вернул: success={success}, message={message[:100]}...")

        if success:
            logger.info("✅ Промокод успешно активирован, проверяю доступ...")
            # ВАЖНО: Убеждаемся, что изменения закоммичены перед проверкой доступа
            await session.commit()
            # Проверяем, есть ли у пользователя доступ после активации промокода
            access_info = await check_access(telegram_id, session)
            logger.info(f"🔍 check_access вернул: {access_info}")

            # ВАЖНО: Очищаем флаг ПЕРЕД отправкой сообщений, чтобы handle_message не перехватил следующее сообщение
            context.user_data.pop('promocode_just_entered', None)
            logger.info(f"✅ Очищен флаг promocode_just_entered после успешной активации промокода")

            # Если у пользователя есть доступ - показываем сообщение с кнопкой "Начать тренировку"
            if access_info['has_access']:
                logger.info(f"✅ У пользователя есть доступ: {access_info['access_type']}, показываю кнопку 'Начать тренировку'")
                from .keyboards import get_start_training_keyboard
                # Отправляем сообщение об успехе с кнопкой в одном сообщении
                await update.message.reply_text(
                    message,
                    reply_markup=get_start_training_keyboard()
                )
            else:
                logger.warning(f"⚠️ У пользователя НЕТ доступа после активации промокода! access_info={access_info}")
                logger.warning("⚠️ Это не должно происходить - промокод должен давать доступ!")
                # В v4.0 возвращаем к стартовому меню
                from .keyboards import get_start_menu_keyboard
                await update.message.reply_text(
                    f"{message}\n\nОбратитесь к администратору, если проблема сохраняется.",
                    reply_markup=get_start_menu_keyboard()
                )

            # Завершаем ConversationHandler после успешной активации
            logger.info("✅ Завершаю ConversationHandler после успешной активации промокода")
            logger.info("=" * 80)
            logger.info(f"🏁 PROCESS_PROMOCODE завершен для пользователя {telegram_id}")
            logger.info("=" * 80)
            return ConversationHandler.END
        else:
            # Неверный промокод - показываем ошибку с кнопками
            # ВАЖНО: НЕ проверяем доступ при неверном промокоде, даже если он есть из другого источника
            # Пользователь должен понять, что промокод неверный, и не должен видеть кнопку "Начать тренировку"
            logger.warning(f"❌ НЕВЕРНЫЙ ПРОМОКОД для пользователя {telegram_id}: {code}")
            logger.warning(f"❌ Сообщение об ошибке: {message}")

            # НЕ проверяем доступ при неверном промокоде!
            logger.info("⚠️ НЕ проверяю доступ при неверном промокоде (даже если он есть из другого источника)")

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            # Устанавливаем флаг, чтобы handle_message не обрабатывал следующее сообщение
            context.user_data['promocode_just_entered'] = True
            logger.info(f"✅ Установлен флаг promocode_just_entered=True для пользователя {telegram_id}")

            error_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data="payment:enter_promo")],
                [InlineKeyboardButton("« Назад в меню", callback_data="payment:back_to_menu")]
            ])

            error_message = f"{message}\n\nПопробуйте ввести промокод еще раз или вернитесь в меню."
            logger.info(f"📤 Отправляю сообщение об ошибке с кнопками: {error_message[:100]}...")
            await update.message.reply_text(
                error_message,
                reply_markup=error_keyboard
            )
            logger.info("✅ Сообщение об ошибке отправлено")

            # Завершаем ConversationHandler после ошибки
            logger.info("✅ Завершаю ConversationHandler после ошибки промокода")
            logger.info("=" * 80)
            logger.info(f"🏁 PROCESS_PROMOCODE завершен для пользователя {telegram_id}")
            logger.info("=" * 80)
            return ConversationHandler.END


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /promo command - activate promocode."""
    telegram_id = update.effective_user.id

    logger.info("=" * 80)
    logger.info(f"🔍 PROMO_COMMAND: Пользователь {telegram_id}")
    logger.info("=" * 80)

    if not context.args:
        logger.info("❌ Промокод не указан в команде")
        await update.message.reply_text(
            "🎟️ **АКТИВАЦИЯ ПРОМОКОДА**\n\n"
            "Использование: `/promo <код>`\n\n"
            "Пример: `/promo WINTER2025`\n\n"
            "Или используйте команду /payment для просмотра всех способов получения доступа."
        )
        return

    code = context.args[0].strip().upper()
    logger.info(f"📝 Промокод из команды: {code}")

    async with get_session() as session:
        logger.info(f"📝 Вызываю activate_promocode(code={code}, telegram_id={telegram_id})")
        success, message = await activate_promocode(code, telegram_id, session)
        logger.info(f"✅ activate_promocode вернул: success={success}, message={message[:100]}...")

        if success:
            logger.info("✅ Промокод успешно активирован, проверяю доступ...")
            # ВАЖНО: Убеждаемся, что изменения закоммичены перед проверкой доступа
            await session.commit()
            # Проверяем, есть ли у пользователя доступ после активации промокода
            access_info = await check_access(telegram_id, session)
            logger.info(f"🔍 check_access вернул: {access_info}")

            # Если у пользователя есть доступ - показываем сообщение с кнопкой "Начать тренировку"
            if access_info['has_access']:
                logger.info(f"✅ У пользователя есть доступ: {access_info['access_type']}, показываю кнопку 'Начать тренировку'")
                from .keyboards import get_start_training_keyboard
                # Отправляем сообщение об успехе с кнопкой в одном сообщении
                await update.message.reply_text(
                    message,
                    reply_markup=get_start_training_keyboard()
                )
            else:
                logger.warning(f"⚠️ У пользователя НЕТ доступа после активации промокода! access_info={access_info}")
                logger.warning("⚠️ Это не должно происходить - промокод должен давать доступ!")
                # В v4.0 возвращаем к стартовому меню
                from .keyboards import get_start_menu_keyboard
                await update.message.reply_text(
                    f"{message}\n\nОбратитесь к администратору, если проблема сохраняется.",
                    reply_markup=get_start_menu_keyboard()
                )
        else:
            # Неверный промокод - показываем ошибку с кнопками
            # ВАЖНО: НЕ проверяем доступ при неверном промокоде, даже если он есть из другого источника
            # Пользователь должен понять, что промокод неверный, и не должен видеть кнопку "Начать тренировку"
            logger.warning(f"❌ НЕВЕРНЫЙ ПРОМОКОД для пользователя {telegram_id}: {code}")
            logger.warning(f"❌ Сообщение об ошибке: {message}")

            # НЕ проверяем доступ при неверном промокоде!
            logger.info("⚠️ НЕ проверяю доступ при неверном промокоде (даже если он есть из другого источника)")

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            # Устанавливаем флаг, чтобы handle_message не обрабатывал следующее сообщение
            context.user_data['promocode_just_entered'] = True
            logger.info(f"✅ Установлен флаг promocode_just_entered=True для пользователя {telegram_id}")

            error_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data="payment:enter_promo")],
                [InlineKeyboardButton("« Назад в меню", callback_data="payment:back_to_menu")]
            ])

            error_message = f"{message}\n\nПопробуйте ввести промокод еще раз или вернитесь в меню."
            logger.info(f"📤 Отправляю сообщение об ошибке с кнопками: {error_message[:100]}...")
            await update.message.reply_text(
                error_message,
                reply_markup=error_keyboard
            )
            logger.info("✅ Сообщение об ошибке отправлено")

    logger.info("=" * 80)
    logger.info(f"🏁 PROMO_COMMAND завершен для пользователя {telegram_id}")
    logger.info("=" * 80)


async def cancel_promo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel promocode input (v4.0 - возвращает к стартовому меню)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Отменено")

    # В v4.0 возвращаем к стартовому меню
    from .keyboards import get_start_menu_keyboard
    await query.edit_message_text(
        "Ввод промокода отменен.",
        reply_markup=get_start_menu_keyboard()
    )
    return PaymentStates.MAIN_MENU


# ==================== BACK NAVIGATION ====================

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to start menu (v4.0 - free access and how it works)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Возвращаемся в меню...")

    # Очищаем флаг, если он был установлен
    context.user_data.pop('promocode_just_entered', None)

    telegram_id = update.effective_user.id
    async with get_session() as session:
        from .subscription import check_access
        access_info = await check_access(telegram_id, session)

    # Формируем стартовое сообщение (как в /start)
    from .messages import WELCOME_SALES
    from .keyboards import get_start_menu_keyboard, get_start_training_keyboard

    welcome_message = WELCOME_SALES

    # Добавляем информацию о статусе пользователя
    status_message = ""
    if access_info['has_access']:
        if access_info['access_type'] == 'free_trainings':
            trainings_left = access_info['details'].get('trainings_left', 0)
            source = access_info['details'].get('source', 'unknown')
            status_message = f"\n\n📊 **Ваш статус:**\n🎁 Бесплатных тренировок: {trainings_left} (источник: {source})"
        elif access_info['access_type'] == 'subscription':
            status_message = "\n\n🔑 У вас есть активная подписка."
    else:
        status_message = "\n\n🔑 У вас нет активной подписки."

    full_message = welcome_message + status_message

    # Определяем клавиатуру
    if access_info['has_access']:
        keyboard = get_start_training_keyboard()
    else:
        keyboard = get_start_menu_keyboard()

    await query.edit_message_text(
        full_message,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return PaymentStates.MAIN_MENU


async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Close payment menu."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Закрываю...")

    await query.delete_message()
    return ConversationHandler.END


# ==================== SPIN SALES FUNNEL HANDLERS ====================

async def how_it_works_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show social proof and benefits with options - гибридная воронка."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Загружаю информацию...")

    try:
        # Комбинированное сообщение: SOCIAL_PROOF_SHORT + BENEFITS_SHORT
        message = f"{SOCIAL_PROOF_SHORT}\n\n{BENEFITS_SHORT}"

        # v4.0: Убраны кнопки оплаты, оставлены только возражения и бесплатный доступ
        keyboard = [
            [InlineKeyboardButton("🤔 Звучит хорошо, но есть сомнения", callback_data="payment:objections")],
            [InlineKeyboardButton("⚙️ Как именно это работает?", callback_data="payment:mechanics")],
            [InlineKeyboardButton("🎁 Хочу попробовать бесплатно", callback_data="payment:free_access")],
            [InlineKeyboardButton("« Назад", callback_data="payment:back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error in how_it_works_callback: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.edit_message_text(
                f"❌ Произошла ошибка: {str(e)}"
            )
        except Exception as e2:
            logger.error(f"❌ Error in error handler: {e2}")
            try:
                await query.message.reply_text(
                    f"❌ Произошла ошибка: {str(e)}"
                )
            except Exception as e3:
                logger.error(f"❌ Error in fallback error handler: {e3}")
    return


async def objections_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle objections - start SPIN funnel (sport metaphor)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Проверяю...")

    try:
        # Запускаем SPIN S (существующее сообщение со спортивной метафорой)
        keyboard = [
            [InlineKeyboardButton("👍 Да, это про меня", callback_data="payment:spin:yes")],
            [InlineKeyboardButton("🤔 У меня всё неплохо", callback_data="payment:spin:no")],
            [InlineKeyboardButton("« Назад", callback_data="payment:how_it_works")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=SPIN_S_SITUATION,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error in objections_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def mechanics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed mechanics - HOW_IT_WORKS."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Загружаю детали...")

    try:
        # v4.0: Убрана кнопка оплаты, оставлены только возражения и бесплатный доступ
        keyboard = [
            [InlineKeyboardButton("🎁 Бесплатный доступ", callback_data="payment:free_access")],
            [InlineKeyboardButton("🤔 Звучит хорошо, но есть сомнения", callback_data="payment:objections")],
            [InlineKeyboardButton("« Назад", callback_data="payment:how_it_works")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=HOW_IT_WORKS,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Error in mechanics_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def spin_s_yes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User agrees with S screen - move to P (Problem)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Продолжаем...")

    try:
        await query.edit_message_text(
            SPIN_P_PROBLEM,
            reply_markup=get_spin_p_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in spin_s_yes_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def spin_s_no_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User disagrees with S screen - still move to P (Problem)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Продолжаем...")

    try:
        await query.edit_message_text(
            SPIN_P_PROBLEM,
            reply_markup=get_spin_p_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in spin_s_no_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def spin_p_continue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Continue from P to I (Implication)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Продолжаем...")

    try:
        await query.edit_message_text(
            SPIN_I_IMPLICATION,
            reply_markup=get_spin_i_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in spin_p_continue_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def spin_i_continue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Continue from I to N (Need-payoff)."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Продолжаем...")

    try:
        await query.edit_message_text(
            SPIN_N_NEED_PAYOFF,
            reply_markup=get_spin_n_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in spin_i_continue_callback: {e}")
        import traceback
        traceback.print_exc()
    return


async def spin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back in SPIN funnel."""
    query = update.callback_query
    # Немедленный ответ для лучшего UX
    await query.answer("Возвращаемся...")

    try:
        # Determine current state from context or go back to S
        # For simplicity, always go back to S
        await query.edit_message_text(
            SPIN_S_SITUATION,
            reply_markup=get_spin_s_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in spin_back_callback: {e}")
        import traceback
        traceback.print_exc()
    return


# ==================== REGISTER HANDLERS ====================

def register_free_access_handlers(application):
    """
    Регистрация handlers для бесплатного доступа и возражений (v4.0 - без оплаты и промокодов).
    """
    from telegram.ext import CallbackQueryHandler

    logger.info("🔧 Начинаем регистрацию free access handlers...")

    # Бесплатный доступ
    application.add_handler(CallbackQueryHandler(
        free_access_callback,
        pattern="^payment:free_access$"
    ))
    logger.info("  ✅ payment:free_access callback зарегистрирован")

    # Проверка подписки на канал
    application.add_handler(CallbackQueryHandler(
        check_subscription_callback,
        pattern="^payment:check_subscription$"
    ))
    logger.info("  ✅ payment:check_subscription callback зарегистрирован")

    # Возражения (SPIN funnel)
    application.add_handler(CallbackQueryHandler(
        objections_callback,
        pattern="^payment:objections$"
    ))
    logger.info("  ✅ payment:objections callback зарегистрирован")

    # Механика работы
    application.add_handler(CallbackQueryHandler(
        mechanics_callback,
        pattern="^payment:mechanics$"
    ))
    logger.info("  ✅ payment:mechanics callback зарегистрирован")

    # SPIN funnel handlers
    application.add_handler(CallbackQueryHandler(
        spin_s_yes_callback,
        pattern="^payment:spin:yes$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_s_no_callback,
        pattern="^payment:spin:no$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_p_continue_callback,
        pattern="^payment:spin:p_continue$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_i_continue_callback,
        pattern="^payment:spin:i_continue$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_back_callback,
        pattern="^payment:spin:back$"
    ))
    logger.info("  ✅ SPIN funnel callbacks зарегистрированы")

    # Навигация назад
    application.add_handler(CallbackQueryHandler(
        back_to_menu_callback,
        pattern="^payment:back_to_menu$"
    ))
    logger.info("  ✅ payment:back_to_menu callback зарегистрирован")

    logger.info("🔧 Регистрация free access handlers завершена")


def register_payment_handlers(application):
    """Регистрирует все обработчики платежей."""
    logger.info("🔧 Начинаем регистрацию payment handlers...")

    # Обработчик команды /payment
    application.add_handler(CommandHandler("payment", payment_command))
    logger.info("  ✅ /payment command зарегистрирован")

    application.add_handler(CommandHandler("buy", payment_command))
    application.add_handler(CommandHandler("subscribe", payment_command))

    # Promocode command
    application.add_handler(CommandHandler("promo", promo_command))

    # Callback handlers for payment flow
    # НЕ регистрируем how_it_works_callback здесь, он уже зарегистрирован в bot.py
    # application.add_handler(CallbackQueryHandler(how_it_works_callback, pattern="^payment:how_it_works$"))

    application.add_handler(CallbackQueryHandler(
        show_tariffs_callback,
        pattern="^payment:show_tariffs$"
    ))
    logger.info("  ✅ payment:show_tariffs callback зарегистрирован")
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

    # Гибридная воронка - обработчики для how_it_works
    logger.info("Registering hybrid funnel handlers...")
    application.add_handler(CallbackQueryHandler(
        objections_callback,
        pattern="^payment:objections$"
    ))
    application.add_handler(CallbackQueryHandler(
        mechanics_callback,
        pattern="^payment:mechanics$"
    ))

    # SPIN sales funnel handlers - регистрируем ПЕРЕД ConversationHandler
    # чтобы они имели приоритет и не перехватывались ConversationHandler
    # ПРИМЕЧАНИЕ: how_it_works_callback регистрируется в bot.py для максимального приоритета
    logger.info("Registering SPIN funnel handlers...")
    application.add_handler(CallbackQueryHandler(
        spin_s_yes_callback,
        pattern="^payment:spin:yes$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_s_no_callback,
        pattern="^payment:spin:no$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_p_continue_callback,
        pattern="^payment:spin:p_continue$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_i_continue_callback,
        pattern="^payment:spin:i_continue$"
    ))
    application.add_handler(CallbackQueryHandler(
        spin_back_callback,
        pattern="^payment:spin:back$"
    ))

    # Conversation handler for promocode input
    # Важно: fallbacks должны быть специфичными, чтобы не перехватывать другие callbacks
    # ConversationHandler НЕ должен перехватывать callbacks, если пользователь НЕ в состоянии conversation
    logger.info("📝 Создаю ConversationHandler для промокодов...")
    logger.info(f"   Entry point: payment:enter_promo")
    logger.info(f"   State: {PromoInputStates.WAITING_CODE}")
    logger.info(f"   Handler: process_promocode")

    promo_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(enter_promo_callback, pattern="^payment:enter_promo$")],
        states={
            PromoInputStates.WAITING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_promocode)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_promo_callback, pattern="^payment:cancel_promo$")
        ],
        per_chat=True,
        per_user=True,
        per_message=False,
        # Важно: conversation_timeout должен быть установлен, чтобы conversation не висел вечно
        conversation_timeout=300  # 5 минут
    )
    logger.info("✅ ConversationHandler для промокодов создан")
    # Регистрируем ConversationHandler с высоким приоритетом (group=-1)
    # чтобы он перехватывал сообщения раньше обычных MessageHandler
    application.add_handler(promo_conversation, group=-1)
    logger.info("✅ promo_conversation зарегистрирован с приоритетом group=-1")

    logger.info("🔧 Регистрация payment handlers завершена")

    # Register admin handlers
    from .admin_handlers import register_admin_handlers
    register_admin_handlers(application)
