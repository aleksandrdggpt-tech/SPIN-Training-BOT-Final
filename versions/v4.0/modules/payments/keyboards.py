"""
Keyboard layouts for payment module.
Telegram inline keyboards for tariff selection, payment, etc.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Optional
from .config import TARIFFS, get_subscription_tariffs, get_credits_tariffs, format_price


# ==================== MAIN PAYMENT MENU ====================

def get_payment_menu_keyboard() -> InlineKeyboardMarkup:
    """Main payment menu (v4.0 - без оплаты и промокодов, использует start menu)."""
    # В v4.0 эта функция не используется, но для совместимости возвращаем start menu
    return get_start_menu_keyboard()


# ==================== TARIFF SELECTION ====================

def get_tariffs_keyboard(show_credits: bool = False) -> InlineKeyboardMarkup:
    """
    Keyboard with available tariffs.

    Args:
        show_credits: If True, show credit packages (for pay-per-use model).
                    If False, show only subscriptions (for SPIN Bot).
    """
    keyboard = []

    if not show_credits:
        # Subscription tariffs (SPIN Bot default)
        tariffs = get_subscription_tariffs()
        for tariff_id, tariff_data in tariffs.items():
            emoji = tariff_data.get('emoji', '')
            name = tariff_data.get('name', '')
            price = format_price(tariff_id)
            discount = f" 🔥 {tariff_data['discount']}" if 'discount' in tariff_data else ""

            button_text = f"{emoji} {name} — {price}{discount}"
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"payment:select_tariff:{tariff_id}"
            )])
    else:
        # Credits tariffs (pay-per-use model)
        tariffs = get_credits_tariffs()
        for tariff_id, tariff_data in tariffs.items():
            emoji = tariff_data.get('emoji', '')
            name = tariff_data.get('name', '')
            price = format_price(tariff_id)

            button_text = f"{emoji} {name} — {price}"
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"payment:select_tariff:{tariff_id}"
            )])

    # Back button
    keyboard.append([InlineKeyboardButton("« Назад", callback_data="payment:back_to_menu")])

    return InlineKeyboardMarkup(keyboard)


# ==================== TARIFF CONFIRMATION ====================

def get_tariff_confirmation_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    """Keyboard for tariff confirmation (v4.0 - не используется, оплата отключена)."""
    # В v4.0 оплата отключена, возвращаем start menu
    return get_start_menu_keyboard()


# ==================== PAYMENT PROVIDER SELECTION ====================

def get_payment_provider_keyboard(tariff_id: str) -> InlineKeyboardMarkup:
    """Keyboard for selecting payment provider."""
    keyboard = [
        [InlineKeyboardButton("💳 ЮKassa", callback_data=f"payment:provider:yookassa:{tariff_id}")],
        [InlineKeyboardButton("💳 CloudPayments", callback_data=f"payment:provider:cloudpayments:{tariff_id}")],
        [InlineKeyboardButton("💳 Prodamus", callback_data=f"payment:provider:prodamus:{tariff_id}")],
        [InlineKeyboardButton("« Назад", callback_data=f"payment:select_tariff:{tariff_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== FREE ACCESS OPTIONS ====================

def get_free_access_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для меню бесплатного доступа (v4.0 - без промокодов).

    Содержит:
    - Кнопку "📢 Подписаться на канал" - открывает канал @TaktikaKutuzova в Telegram
    - Кнопку "✅ Я подписался, проверить" - проверяет подписку через getChatMember
    - Кнопку "« Назад" - возврат в главное меню

    Используется в обработчике free_access_callback.
    """
    keyboard = [
        # Кнопка со ссылкой на канал - открывает канал в Telegram
        [InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/TaktikaKutuzova")],
        # Кнопка для проверки подписки - вызывает check_subscription_callback
        # который использует bot.get_chat_member для проверки
        [InlineKeyboardButton("✅ Я подписался, проверить", callback_data="payment:check_subscription")],
        [InlineKeyboardButton("« Назад", callback_data="payment:back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== PROMOCODE INPUT ====================

def get_promo_cancel_keyboard() -> InlineKeyboardMarkup:
    """Keyboard to cancel promocode input."""
    keyboard = [
        [InlineKeyboardButton("« Отмена", callback_data="payment:cancel_promo")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== SUBSCRIPTION INFO ====================

def get_subscription_info_keyboard(has_subscription: bool = False) -> InlineKeyboardMarkup:
    """Keyboard for subscription information page (v4.0 - без оплаты)."""
    keyboard = []

    if has_subscription:
        keyboard.append([InlineKeyboardButton("📊 Моя статистика", callback_data="payment:my_stats")])
    else:
        keyboard.append([InlineKeyboardButton("🎁 Бесплатный доступ", callback_data="payment:free_access")])

    keyboard.append([InlineKeyboardButton("« Закрыть", callback_data="payment:close")])

    return InlineKeyboardMarkup(keyboard)


# ==================== PAYMENT STATUS ====================

def get_payment_status_keyboard(payment_id: str) -> InlineKeyboardMarkup:
    """Keyboard for checking payment status."""
    keyboard = [
        [InlineKeyboardButton("🔄 Проверить статус", callback_data=f"payment:check_status:{payment_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"payment:cancel_payment:{payment_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== ACCESS DENIED ====================

def get_access_denied_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when user has no access (v4.0 - без оплаты и промокодов)."""
    keyboard = [
        [InlineKeyboardButton("🎁 Получить бесплатно", callback_data="payment:free_access")],
        [InlineKeyboardButton("❓ Как это работает?", callback_data="payment:how_it_works")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== SPIN SALES FUNNEL KEYBOARDS ====================

def get_spin_s_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for SPIN S (Situation) screen."""
    keyboard = [
        [InlineKeyboardButton("👍 Да, это про меня", callback_data="payment:spin:yes")],
        [InlineKeyboardButton("🤔 У меня всё неплохо", callback_data="payment:spin:no")],
        [InlineKeyboardButton("« Назад", callback_data="payment:back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_spin_p_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for SPIN P (Problem) screen."""
    keyboard = [
        [InlineKeyboardButton("👍 Да, узнаю", callback_data="payment:spin:p_continue")],
        [InlineKeyboardButton("🤔 Не совсем", callback_data="payment:spin:p_continue")],
        [InlineKeyboardButton("« Назад", callback_data="payment:spin:back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_spin_i_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for SPIN I (Implication) screen."""
    keyboard = [
        [InlineKeyboardButton("✅ Да, хочу понять", callback_data="payment:spin:i_continue")],
        [InlineKeyboardButton("« Назад", callback_data="payment:spin:back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_spin_n_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for SPIN N (Need-payoff) screen (v4.0 - без оплаты)."""
    keyboard = [
        [InlineKeyboardButton("🎁 Хочу попробовать бесплатно", callback_data="payment:free_access")],
        [InlineKeyboardButton("« Назад", callback_data="payment:spin:back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_menu_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for new users - free access and how it works buttons."""
    keyboard = [
        [InlineKeyboardButton("🎁 Бесплатный доступ", callback_data="payment:free_access")],
        [InlineKeyboardButton("❓ Как это работает?", callback_data="payment:how_it_works")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_training_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for users with active subscription - start training button."""
    keyboard = [
        [InlineKeyboardButton("▶️ Начать тренировку", callback_data="start:training")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_new_training_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for starting a new training after completion."""
    keyboard = [
        [InlineKeyboardButton("🔄 Начать новую тренировку", callback_data="start:training")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== ADMIN KEYBOARDS ====================

def get_admin_promo_keyboard() -> InlineKeyboardMarkup:
    """Admin keyboard for promocode management."""
    keyboard = [
        [InlineKeyboardButton("➕ Создать промокод", callback_data="admin:create_promo")],
        [InlineKeyboardButton("📋 Список промокодов", callback_data="admin:list_promos")],
        [InlineKeyboardButton("🎁 Выдать доступ", callback_data="admin:give_access")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton("📝 Список команд", callback_data="admin:commands")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== HELPER FUNCTIONS ====================

def build_url_keyboard(url: str, button_text: str = "Перейти") -> InlineKeyboardMarkup:
    """Build simple keyboard with URL button."""
    keyboard = [[InlineKeyboardButton(button_text, url=url)]]
    return InlineKeyboardMarkup(keyboard)


def build_callback_keyboard(buttons: List[tuple]) -> InlineKeyboardMarkup:
    """
    Build keyboard from list of (text, callback_data) tuples.

    Args:
        buttons: List of tuples like [("Button 1", "callback_1"), ("Button 2", "callback_2")]

    Returns:
        InlineKeyboardMarkup
    """
    keyboard = [[InlineKeyboardButton(text, callback_data=callback)] for text, callback in buttons]
    return InlineKeyboardMarkup(keyboard)


def add_back_button(keyboard: List[List[InlineKeyboardButton]], callback_data: str = "payment:back_to_menu") -> List[List[InlineKeyboardButton]]:
    """Add back button to existing keyboard."""
    keyboard.append([InlineKeyboardButton("« Назад", callback_data=callback_data)])
    return keyboard
