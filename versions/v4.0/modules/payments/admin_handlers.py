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


class AdminButtonStates(IntEnum):
    """States for button addition dialog."""
    WAITING_POST_URL = 1
    WAITING_BUTTON_TEXT = 2
    WAITING_LEAD_MAGNET_TYPE = 3
    WAITING_EXTERNAL_LINK = 4


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
`/add_button` - Установить кнопку в канал

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
            
            # Count channel button clicks
            from database import ChannelButtonClick, ChannelButton
            from sqlalchemy import func
            clicks_result = await session.execute(
                select(func.count(ChannelButtonClick.id))
            )
            total_clicks = clicks_result.scalar() or 0
            
            # Count unique users who clicked
            unique_users_result = await session.execute(
                select(func.count(func.distinct(ChannelButtonClick.telegram_id)))
            )
            unique_users = unique_users_result.scalar() or 0
            
            # Count total buttons
            buttons_result = await session.execute(
                select(func.count(ChannelButton.id))
            )
            total_buttons = buttons_result.scalar() or 0

        message = f"""
📊 **СТАТИСТИКА**

**Промокоды:**
📈 Активных: {active_count}
📦 Всего: {total_count}
⏰ Истекло: {expired_count}
🎯 Использований: {usage_count}

**Кнопки в канале:**
🔘 Всего кнопок: {total_buttons}
👆 Всего нажатий: {total_clicks}
👥 Уникальных пользователей: {unique_users}
"""

        keyboard = [
            [InlineKeyboardButton("📊 Статистика по кнопкам", callback_data="admin:button_stats")],
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
`/add_button` - Установить кнопку в канал

**Действия через меню:**
• ➕ Создать промокод
• 📋 Список промокодов
• 🎁 Выдать доступ
• 📊 Статистика
• 📊 Статистика по кнопкам
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


# ==================== CHANNEL BUTTON MANAGEMENT ====================

async def add_button_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /add_button command - установить кнопку выдачи лид магнита в свой канал.
    """
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("❌ У вас нет прав доступа.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔘 **УСТАНОВКА КНОПКИ В КАНАЛЕ**\n\n"
        "Отправьте ссылку на пост, к которому нужно добавить кнопку.\n\n"
        "💡 **Формат ссылки:**\n"
        "`https://t.me/channel_username/123`\n\n"
        "Используйте /cancel для отмены.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    return AdminButtonStates.WAITING_POST_URL


async def add_button_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle post URL input."""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("❌ У вас нет прав доступа.")
        return ConversationHandler.END
    
    post_url = update.message.text.strip()
    
    # Парсим URL поста
    from services.channel_button_service import ChannelButtonService
    parsed = ChannelButtonService.parse_post_url(post_url)
    
    if not parsed:
        await update.message.reply_text(
            "❌ Неверный формат ссылки.\n\n"
            "Отправьте ссылку на пост в формате:\n"
            "`https://t.me/channel_username/123`"
        )
        return AdminButtonStates.WAITING_POST_URL
    
    channel_id, message_id = parsed
    
    # Сохраняем в context для следующего шага
    context.user_data['button_channel_id'] = channel_id
    context.user_data['button_message_id'] = message_id
    
    await update.message.reply_text(
        "✅ Ссылка на пост получена!\n\n"
        "Теперь отправьте текст для кнопки.\n\n"
        "Например: \"Получить лид-магнит\" или \"Попробовать бота\""
    )
    
    return AdminButtonStates.WAITING_BUTTON_TEXT




async def add_button_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button text input."""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("❌ У вас нет прав доступа.")
        return ConversationHandler.END
    
    button_text = update.message.text.strip()
    
    if not button_text:
        await update.message.reply_text("❌ Текст кнопки не может быть пустым.")
        return AdminButtonStates.WAITING_BUTTON_TEXT
    
    # Сохраняем текст кнопки
    context.user_data['button_text'] = button_text
    
    # Показываем выбор типа лид-магнита
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Доступ к боту", callback_data="button:type:bot")],
        [InlineKeyboardButton("🔗 Внешняя ссылка", callback_data="button:type:external")],
    ])
    
    await update.message.reply_text(
        "✅ Текст кнопки сохранен!\n\n"
        "Теперь выберите тип лид-магнита:",
        reply_markup=keyboard
    )
    
    return AdminButtonStates.WAITING_LEAD_MAGNET_TYPE


async def add_button_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle lead magnet type selection."""
    query = update.callback_query
    await query.answer()
    
    telegram_id = query.from_user.id
    
    if not is_admin(telegram_id):
        await query.edit_message_text("❌ У вас нет прав доступа.")
        return ConversationHandler.END
    
    # Извлекаем тип из callback_data
    lead_magnet_type = query.data.split(":")[-1]  # "bot", "file", или "poll"
    
    # Сохраняем тип
    context.user_data['lead_magnet_type'] = lead_magnet_type
    
    if lead_magnet_type == "bot":
        # Для бота не нужна дополнительная ссылка
        # Сразу добавляем кнопку
        try:
            channel_id = context.user_data.get('button_channel_id')
            message_id = context.user_data.get('button_message_id')
            button_text = context.user_data.get('button_text')
            
            if not all([channel_id, message_id, button_text]):
                await query.edit_message_text("❌ Ошибка: данные не найдены. Начните заново.")
                return ConversationHandler.END
            
            # Получаем информацию о боте
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
            
            # Генерируем ссылку на бота
            from services.channel_button_service import ChannelButtonService
            bot_link = ChannelButtonService.generate_bot_link(bot_username, message_id)
            
            # Добавляем кнопку
            success = await ChannelButtonService.add_button_to_post(
                bot=context.bot,
                channel_id=channel_id,
                message_id=message_id,
                button_text=button_text,
                link=bot_link,
                lead_magnet_type="bot"
            )
            
            if success:
                # Сохраняем информацию о кнопке в БД
                try:
                    from database import ChannelButton, get_session
                    # Используем дефолтное название поста (можно будет улучшить позже)
                    post_title = f"Пост {message_id}"
                    
                    async with get_session() as session:
                        button = ChannelButton(
                            channel_id=str(channel_id),
                            message_id=message_id,
                            post_title=post_title,
                            button_text=button_text,
                            lead_magnet_type="bot",
                            link=bot_link,
                            created_by=telegram_id
                        )
                        session.add(button)
                        await session.commit()
                        logger.info(f"Button info saved: ID {button.id}")
                except Exception as e:
                    logger.error(f"Error saving button info: {e}")
                
                # Используем HTML для безопасного отображения пользовательского текста
                import html
                escaped_button_text = html.escape(button_text)
                escaped_bot_link = html.escape(bot_link)
                
                await query.edit_message_text(
                    f"✅ <b>Кнопка добавлена!</b>\n\n"
                    f"📊 ID поста: <code>{message_id}</code>\n"
                    f"🔘 Текст: {escaped_button_text}\n"
                    f"🤖 Тип: Доступ к боту\n"
                    f"🔗 Ссылка: <code>{escaped_bot_link}</code>\n\n"
                    f"<i>Примечание: Если пост был создан другим пользователем, кнопка отправлена новым сообщением под постом.</i>",
                    parse_mode=ParseMode.HTML
                )
                logger.info(f"Button '{button_text}' (bot) added to post {message_id} by admin {telegram_id}")
            else:
                await query.edit_message_text(
                    f"❌ <b>Ошибка при добавлении кнопки.</b>\n\n"
                    "Возможные причины:\n"
                    "• Бот не является администратором канала\n"
                    "• У бота нет прав на отправку сообщений\n"
                    "• Недостаточно прав для работы с каналом",
                    parse_mode=ParseMode.HTML
                )
            
            # Очищаем данные
            context.user_data.pop('button_channel_id', None)
            context.user_data.pop('button_message_id', None)
            context.user_data.pop('post_title', None)
            context.user_data.pop('button_text', None)
            context.user_data.pop('lead_magnet_type', None)
            
        except Exception as e:
            logger.error(f"Error adding button: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await query.edit_message_text(f"❌ Ошибка: {e}")
        
        return ConversationHandler.END
    
    else:
        # Для внешней ссылки нужна ссылка
        await query.edit_message_text(
            f"✅ Тип выбран: Внешняя ссылка\n\n"
            f"Отправьте ссылку.\n\n"
            f"Примеры:\n"
            f"• Google Drive: `https://drive.google.com/file/d/...`\n"
            f"• Опрос: `https://t.me/poll/...`\n"
            f"• Любая другая ссылка",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return AdminButtonStates.WAITING_EXTERNAL_LINK


async def add_button_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle external link input (for file or poll)."""
    telegram_id = update.effective_user.id
    
    if not is_admin(telegram_id):
        await update.message.reply_text("❌ У вас нет прав доступа.")
        return ConversationHandler.END
    
    external_link = update.message.text.strip()
    
    if not external_link or not (external_link.startswith('http://') or external_link.startswith('https://')):
        await update.message.reply_text(
            "❌ Неверный формат ссылки. Отправьте полную ссылку (начинается с http:// или https://)"
        )
        return AdminButtonStates.WAITING_EXTERNAL_LINK
    
    try:
        channel_id = context.user_data.get('button_channel_id')
        message_id = context.user_data.get('button_message_id')
        button_text = context.user_data.get('button_text')
        lead_magnet_type = context.user_data.get('lead_magnet_type')
        
        if not all([channel_id, message_id, button_text, lead_magnet_type]):
            await update.message.reply_text("❌ Ошибка: данные не найдены. Начните заново.")
            return ConversationHandler.END
        
        # Добавляем кнопку
        from services.channel_button_service import ChannelButtonService
        
        success = await ChannelButtonService.add_button_to_post(
            bot=context.bot,
            channel_id=channel_id,
            message_id=message_id,
            button_text=button_text,
            link=external_link,
            lead_magnet_type=lead_magnet_type
        )
        
        if success:
            # Сохраняем информацию о кнопке в БД
            try:
                from database import ChannelButton, get_session
                # Используем дефолтное название поста
                post_title = f"Пост {message_id}"
                async with get_session() as session:
                    button = ChannelButton(
                        channel_id=str(channel_id),
                        message_id=message_id,
                        post_title=post_title,
                        button_text=button_text,
                        lead_magnet_type=lead_magnet_type,
                        link=external_link,
                        created_by=telegram_id
                    )
                    session.add(button)
                    await session.commit()
                    logger.info(f"Button info saved: ID {button.id}")
            except Exception as e:
                logger.error(f"Error saving button info: {e}")
            
            # Используем HTML для безопасного отображения пользовательского текста
            import html
            escaped_button_text = html.escape(button_text)
            escaped_external_link = html.escape(external_link)
            
            await update.message.reply_text(
                f"✅ <b>Кнопка добавлена!</b>\n\n"
                f"📊 ID поста: <code>{message_id}</code>\n"
                f"🔘 Текст: {escaped_button_text}\n"
                f"🔗 Тип: Внешняя ссылка\n"
                f"🔗 Ссылка: <code>{escaped_external_link}</code>\n\n"
                f"<i>Примечание: Если пост был создан другим пользователем, кнопка отправлена новым сообщением под постом.</i>",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Button '{button_text}' (external) added to post {message_id} by admin {telegram_id}")
        else:
            await update.message.reply_text(
                f"❌ <b>Ошибка при добавлении кнопки.</b>\n\n"
                "Возможные причины:\n"
                "• Бот не является администратором канала\n"
                "• У бота нет прав на отправку сообщений\n"
                "• Недостаточно прав для работы с каналом",
                parse_mode=ParseMode.HTML
            )
        
        # Очищаем данные
        context.user_data.pop('button_channel_id', None)
        context.user_data.pop('button_message_id', None)
        context.user_data.pop('button_text', None)
        context.user_data.pop('lead_magnet_type', None)
        
    except Exception as e:
        logger.error(f"Error adding button: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await update.message.reply_text(f"❌ Ошибка: {e}")
    
    return ConversationHandler.END


async def cancel_button_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel button addition."""
    # Очищаем сохраненные данные
    if 'user_data' in update:
        update.user_data.pop('button_channel_id', None)
        update.user_data.pop('button_message_id', None)
    
    await update.message.reply_text("❌ Добавление кнопки отменено.")
    return ConversationHandler.END


async def admin_button_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed statistics for each button."""
    query = update.callback_query
    await query.answer()

    telegram_id = query.from_user.id

    if not is_admin(telegram_id):
        await query.edit_message_text("❌ Нет прав доступа.")
        return

    try:
        async with get_session() as session:
            from database import ChannelButton, ChannelButtonClick
            from sqlalchemy import func
            
            # Получаем все кнопки
            buttons_result = await session.execute(
                select(ChannelButton).order_by(ChannelButton.created_at.desc())
            )
            buttons = buttons_result.scalars().all()
            
            if not buttons:
                await query.edit_message_text(
                    "📊 **СТАТИСТИКА ПО КНОПКАМ**\n\n"
                    "Кнопки еще не созданы.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("◀️ Назад", callback_data="admin:stats")]
                    ])
                )
                return
            
            # Собираем статистику по каждой кнопке
            stats_lines = []
            for button in buttons:
                # Считаем нажатия для этой кнопки
                clicks_result = await session.execute(
                    select(func.count(ChannelButtonClick.id))
                    .where(ChannelButtonClick.button_id == button.id)
                )
                clicks_count = clicks_result.scalar() or 0
                
                # Считаем уникальных пользователей
                unique_result = await session.execute(
                    select(func.count(func.distinct(ChannelButtonClick.telegram_id)))
                    .where(ChannelButtonClick.button_id == button.id)
                )
                unique_count = unique_result.scalar() or 0
                
                # Форматируем тип
                type_emoji = "🤖" if button.lead_magnet_type == "bot" else "🔗"
                type_name = "Бот" if button.lead_magnet_type == "bot" else "Внешняя ссылка"
                
                # Обрезаем длинные тексты
                post_title_short = button.post_title[:40] + "..." if len(button.post_title) > 40 else button.post_title
                button_text_short = button.button_text[:30] + "..." if len(button.button_text) > 30 else button.button_text
                
                stats_lines.append(
                    f"**🔘 {button_text_short}**\n"
                    f"📝 Пост: {post_title_short}\n"
                    f"{type_emoji} Тип: {type_name}\n"
                    f"👆 Нажатий: {clicks_count} | 👥 Уникальных: {unique_count}\n"
                )
            
            # Формируем сообщение (ограничиваем длину)
            message = "📊 **СТАТИСТИКА ПО КНОПКАМ**\n\n"
            message += "\n".join(stats_lines[:10])  # Показываем первые 10
            
            if len(buttons) > 10:
                message += f"\n\n... и еще {len(buttons) - 10} кнопок"
            
            await query.edit_message_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад к статистике", callback_data="admin:stats")]
                ])
            )

    except Exception as e:
        logger.error(f"Error getting button stats: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await query.edit_message_text("❌ Ошибка загрузки статистики.")


# ==================== REGISTER ADMIN HANDLERS ====================

def register_admin_handlers(application):
    """
    Register admin handlers.

    Args:
        application: Telegram Application instance
    """
    # Admin command
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Channel button management command
    button_management_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("add_button", add_button_command)
        ],
        states={
            AdminButtonStates.WAITING_POST_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_url_handler)
            ],
            AdminButtonStates.WAITING_BUTTON_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_text_handler)
            ],
            AdminButtonStates.WAITING_LEAD_MAGNET_TYPE: [
                CallbackQueryHandler(add_button_type_callback, pattern="^button:type:")
            ],
            AdminButtonStates.WAITING_EXTERNAL_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_link_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_button_command)
        ]
    )
    application.add_handler(button_management_conversation)

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
        admin_button_stats_callback,
        pattern="^admin:button_stats$"
    ))
    application.add_handler(CallbackQueryHandler(
        admin_commands_callback,
        pattern="^admin:commands$"
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

