"""
Payment configuration for SPIN Training Bot v4.
Tariff plans, prices, and payment settings.
"""

from typing import Dict, Any

# ==================== TARIFF PLANS ====================

TARIFFS: Dict[str, Dict[str, Any]] = {
    # Monthly subscription (for SPIN Bot)
    'month': {
        'name': 'Месячная подписка',
        'price': 990,
        'currency': 'RUB',
        'duration_days': 30,
        'description': 'Безлимитные тренировки 30 дней',
        'emoji': '📅'
    },

    # Yearly subscription (for SPIN Bot)
    'year': {
        'name': 'Годовая подписка',
        'price': 6990,
        'currency': 'RUB',
        'duration_days': 365,
        'description': 'Безлимитные тренировки год + скидка 42%',
        'discount': '42%',
        'emoji': '🎯'
    },

    # Credits packages (for pay-per-use bots, architecture support)
    'credits_5': {
        'name': '5 тренировок',
        'price': 250,
        'currency': 'RUB',
        'credits': 5,
        'description': 'Для тех, кто хочет попробовать',
        'emoji': '🔹'
    },

    'credits_10': {
        'name': '10 тренировок',
        'price': 450,
        'currency': 'RUB',
        'credits': 10,
        'description': 'Популярный пакет',
        'emoji': '🔷'
    },

    'credits_20': {
        'name': '20 тренировок',
        'price': 800,
        'currency': 'RUB',
        'credits': 20,
        'description': 'Оптимальный пакет',
        'emoji': '💎'
    },

    'credits_50': {
        'name': '50 тренировок',
        'price': 1800,
        'currency': 'RUB',
        'credits': 50,
        'description': 'Максимальная выгода',
        'emoji': '👑'
    }
}

# ==================== FREE ACCESS SETTINGS ====================

# Channel for free trainings
CHANNEL_USERNAME = 'TaktikaKutuzova'

# Number of free trainings for channel subscription
FREE_TRAININGS_FOR_SUBSCRIPTION = 2

# ==================== PAYMENT PROVIDERS ====================

# Available payment providers
PAYMENT_PROVIDERS = {
    'cloudpayments': {
        'name': 'CloudPayments',
        'enabled': False,  # Enable when API keys are configured
        'description': 'Оплата картой через CloudPayments'
    },
    'yookassa': {
        'name': 'ЮKassa',
        'enabled': False,  # Enable when API keys are configured
        'description': 'Оплата через ЮKassa'
    },
    'prodamus': {
        'name': 'Prodamus',
        'enabled': False,  # Enable when API keys are configured
        'description': 'Оплата через Prodamus'
    }
}

# Default payment provider
DEFAULT_PAYMENT_PROVIDER = 'yookassa'

# ==================== MONETIZATION MODEL ====================

# Monetization type for this bot
# Options: 'subscription' (SPIN Bot), 'credits' (pay-per-use)
MONETIZATION_MODEL = 'subscription'

# ==================== REFUND POLICY ====================

REFUND_POLICY = """
🔄 ПОЛИТИКА ВОЗВРАТА:

Мы гарантируем возврат денег в течение 7 дней с момента покупки, если:
• Вы не использовали больше 2 тренировок
• Технические проблемы мешают пользоваться ботом

Для возврата свяжитесь с поддержкой: @TaktikaKutuzova
"""

# ==================== HELPER FUNCTIONS ====================

def get_tariff(tariff_id: str) -> Dict[str, Any]:
    """Get tariff information by ID."""
    return TARIFFS.get(tariff_id, {})


def get_subscription_tariffs() -> Dict[str, Dict[str, Any]]:
    """Get only subscription-based tariffs (month, year)."""
    return {
        k: v for k, v in TARIFFS.items()
        if k in ['month', 'year']
    }


def get_credits_tariffs() -> Dict[str, Dict[str, Any]]:
    """Get only credits-based tariffs."""
    return {
        k: v for k, v in TARIFFS.items()
        if k.startswith('credits_')
    }


def format_price(tariff_id: str) -> str:
    """Format tariff price for display."""
    tariff = get_tariff(tariff_id)
    if not tariff:
        return "Цена не указана"

    price = tariff.get('price', 0)
    currency = tariff.get('currency', 'RUB')

    if currency == 'RUB':
        return f"{price} ₽"
    elif currency == 'USD':
        return f"${price}"
    else:
        return f"{price} {currency}"
