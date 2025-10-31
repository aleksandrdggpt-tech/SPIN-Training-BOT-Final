# SPIN Training Bot v4.0 — Модульная система оплаты

> Профессиональная архитектура с переносимым модулем платежей

## Что нового в v4.0

### 🎯 Модульная система оплаты
- **Переносимый модуль** `modules/payments/` — работает в любом боте
- Поддержка подписок (месяц/год) и pay-per-use (кредиты)
- 3 платежных провайдера: YooKassa, CloudPayments, Prodamus
- Система промокодов с гибкими настройками
- Бесплатные тренировки за подписку на канал

### 💾 База данных SQLAlchemy
- Async SQLite (aiosqlite) по умолчанию
- Легкая миграция на PostgreSQL для продакшна
- Полная история платежей и подписок
- Отслеживание использования промокодов

### 📊 Воронка продаж
- Оптимизированные тексты на основе Random Coffee People
- Пошаговое убеждение: ценность → социальное доказательство → выгоды
- Гарантия возврата денег
- Конверсионные клавиатуры

---

## Установка

### 1. Требования
```bash
Python 3.11+
```

### 2. Клонирование и зависимости
```bash
# Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установить зависимости v4
pip install -r REQUIREMENTS_v4.txt
```

### 3. Настройка окружения
```bash
# Скопировать пример
cp .env.v4.example .env

# Заполнить обязательные поля
nano .env
```

**Минимальные настройки:**
```env
BOT_TOKEN=your_bot_token
OPENAI_API_KEY=your_openai_key
DATABASE_URL=sqlite+aiosqlite:///./spin_bot.db
```

### 4. Инициализация базы данных
```bash
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
```

### 5. Запуск
```bash
python bot.py
```

---

## Архитектура v4

### Структура модуля оплаты

```
modules/payments/          # 🎯 ПЕРЕНОСИМЫЙ МОДУЛЬ
├── __init__.py           # Экспорты модуля
├── config.py             # Тарифы и настройки
├── messages.py           # Воронка продаж
├── keyboards.py          # Telegram клавиатуры
├── states.py             # FSM состояния
├── subscription.py       # Логика подписок + декоратор @subscription_required
├── promocodes.py         # Система промокодов
├── handlers.py           # Telegram обработчики
└── providers/            # Платежные провайдеры
    ├── base.py           # Базовый класс
    ├── yookassa.py       # YooKassa
    ├── cloudpayments.py  # CloudPayments
    └── prodamus.py       # Prodamus
```

### База данных

```
database/
├── models.py             # SQLAlchemy модели
│   ├── User              # Пользователи
│   ├── Subscription      # Подписки
│   ├── Payment           # Платежи
│   ├── Promocode         # Промокоды
│   ├── PromocodeUsage    # Использование промокодов
│   └── FreeTraining      # Бесплатные тренировки
└── database.py           # Подключение и сессии
```

---

## Использование модуля оплаты

### Защита функций декоратором

```python
from modules.payments import subscription_required

@subscription_required
async def start_training(update, context):
    """Эта функция доступна только с подпиской."""
    # Ваш код тренировки
    pass
```

Декоратор автоматически:
1. Проверяет наличие доступа
2. Показывает меню оплаты, если доступа нет
3. Списывает кредит/тренировку (для pay-per-use)
4. Пропускает пользователя к функции

### Проверка доступа вручную

```python
from modules.payments import check_access
from database import get_session

async with get_session() as session:
    access_info = await check_access(telegram_id, session)

    if access_info['has_access']:
        access_type = access_info['access_type']  # 'subscription', 'credits', 'free_trainings'
        details = access_info['details']
```

### Создание подписки (программно)

```python
from modules.payments import create_subscription
from database.models import SubscriptionType

# Месячная подписка
await create_subscription(
    telegram_id=123456789,
    subscription_type=SubscriptionType.MONTH,
    duration_days=30
)

# Кредитная подписка (pay-per-use)
await create_subscription(
    telegram_id=123456789,
    subscription_type=SubscriptionType.CREDITS,
    credits=20
)
```

### Активация промокода

```python
from modules.payments import activate_promocode

success, message = await activate_promocode(
    code="SPIN2024",
    telegram_id=123456789,
    session=session
)
```

---

## Команды пользователя

### Основные
- `/start` — Начать тренировку (требует подписку)
- `/payment` или `/buy` — Меню оплаты
- `/stats` — Статистика
- `/rank` — Достижения

### Оплата
- Выбор тарифа (месяц/год)
- Бесплатный доступ (канал/промокод)
- Проверка статуса подписки

---

## Админ-функции

### Создание промокода

```python
from modules.payments import create_promocode
from database.models import PromocodeType

success, message, promo = await create_promocode(
    code="NEWYEAR2024",
    promo_type=PromocodeType.FREE_MONTH,
    value=0,  # Для FREE_MONTH value не используется
    max_uses=100,  # Макс. 100 использований
    expires_days=30  # Истекает через 30 дней
)
```

### Типы промокодов

1. **TRAININGS** — Бесплатные тренировки
   ```python
   promo_type=PromocodeType.TRAININGS
   value=3  # 3 тренировки
   ```

2. **FREE_MONTH** — Бесплатный месяц подписки
   ```python
   promo_type=PromocodeType.FREE_MONTH
   value=0
   ```

3. **CREDITS** — Кредиты (для pay-per-use ботов)
   ```python
   promo_type=PromocodeType.CREDITS
   value=10  # 10 кредитов
   ```

---

## Конфигурация тарифов

Файл: `modules/payments/config.py`

```python
TARIFFS = {
    'month': {
        'name': 'Месячная подписка',
        'price': 990,
        'currency': 'RUB',
        'duration_days': 30,
        'description': 'Безлимитные тренировки 30 дней',
        'emoji': '📅'
    },
    'year': {
        'name': 'Годовая подписка',
        'price': 6990,
        'currency': 'RUB',
        'duration_days': 365,
        'description': 'Безлимитные тренировки год + скидка 42%',
        'discount': '42%',
        'emoji': '🎯'
    }
}
```

**Изменить цены:**
Просто измените значения в `config.py` — никаких изменений кода не требуется.

---

## Интеграция платежных систем

### YooKassa

1. Зарегистрируйтесь на https://yookassa.ru/
2. Получите `SHOP_ID` и `SECRET_KEY`
3. Добавьте в `.env`:
   ```env
   YOOKASSA_SHOP_ID=123456
   YOOKASSA_SECRET_KEY=live_xxx
   ```
4. Установите библиотеку:
   ```bash
   pip install yookassa
   ```
5. Реализуйте методы в `modules/payments/providers/yookassa.py`

### CloudPayments

1. Зарегистрируйтесь на https://cloudpayments.ru/
2. Получите публичный ключ и API secret
3. Добавьте в `.env`:
   ```env
   CLOUDPAYMENTS_PUBLIC_KEY=pk_xxx
   CLOUDPAYMENTS_API_SECRET=xxx
   ```
4. Реализуйте методы в `modules/payments/providers/cloudpayments.py`

### Prodamus

1. Зарегистрируйтесь на https://prodamus.ru/
2. Получите API ключ
3. Добавьте в `.env`:
   ```env
   PRODAMUS_API_KEY=xxx
   ```
4. Реализуйте методы в `modules/payments/providers/prodamus.py`

---

## Перенос модуля в другой бот

### Шаг 1: Скопировать файлы

```bash
# Скопировать модуль оплаты
cp -r modules/payments /path/to/new/bot/modules/

# Скопировать базу данных
cp -r database /path/to/new/bot/
```

### Шаг 2: Установить зависимости

```bash
pip install sqlalchemy aiosqlite python-telegram-bot
```

### Шаг 3: Зарегистрировать handlers

```python
# В вашем bot.py
from modules.payments.handlers import register_payment_handlers

# При инициализации приложения
application = Application.builder().token(TOKEN).build()
register_payment_handlers(application)
```

### Шаг 4: Защитить функции

```python
from modules.payments import subscription_required

@subscription_required
async def protected_function(update, context):
    # Ваш код
    pass
```

### Шаг 5: Настроить конфиг

Отредактируйте `modules/payments/config.py`:
- Измените тарифы
- Установите `MONETIZATION_MODEL` (`'subscription'` или `'credits'`)
- Укажите имя канала для бесплатного доступа

**Готово!** Модуль оплаты работает в вашем боте.

---

## Модели монетизации

### 1. Подписка (SPIN Bot)

```python
MONETIZATION_MODEL = 'subscription'
```

- Пользователь платит за период (месяц/год)
- Безлимитный доступ на время подписки
- Автопродление опционально

### 2. Pay-per-use (другие боты)

```python
MONETIZATION_MODEL = 'credits'
```

- Пользователь покупает пакеты кредитов (5, 10, 20, 50)
- Каждое использование = 1 кредит
- Подходит для ботов с нерегулярным использованием

### Смена модели

Измените `MONETIZATION_MODEL` в `config.py` и используйте соответствующие тарифы:
- Подписка: `get_subscription_tariffs()`
- Кредиты: `get_credits_tariffs()`

---

## Миграция с v3 на v4

### Данные пользователей

v3 хранит данные в памяти (`dict`). v4 использует SQLAlchemy.

**Миграция:**

```python
# Скрипт миграции данных v3 → v4
from services.user_service import UserService  # v3
from database import get_session
from database.models import User
import asyncio

v3_service = UserService()

async def migrate():
    async with get_session() as session:
        for telegram_id, user_data in v3_service._user_data.items():
            stats = user_data['stats']

            user = User(
                telegram_id=telegram_id,
                total_trainings=stats['total_trainings'],
                total_score=stats['best_score']
            )
            session.add(user)

        await session.commit()

asyncio.run(migrate())
```

### Постепенный переход

1. Запустите v4 **параллельно** с v3
2. v4 работает с новыми пользователями
3. Постепенно мигрируйте старых пользователей
4. После миграции отключите v3

---

## Тестирование

### Локальный запуск

```bash
python bot.py
```

### Тестовый промокод

```python
from modules.payments import create_promocode
from database.models import PromocodeType

# Создать тестовый промокод
await create_promocode(
    code="TEST",
    promo_type=PromocodeType.TRAININGS,
    value=10,
    max_uses=None,  # Безлимит
    expires_days=None  # Не истекает
)
```

Пользователи могут активировать `TEST` для получения 10 бесплатных тренировок.

---

## FAQ

### Как изменить цены?

Отредактируйте `modules/payments/config.py`:

```python
TARIFFS = {
    'month': {
        'price': 1490,  # Было 990
        ...
    }
}
```

### Как добавить новый тариф?

```python
TARIFFS['half_year'] = {
    'name': 'Подписка на полгода',
    'price': 4990,
    'currency': 'RUB',
    'duration_days': 180,
    'description': 'Безлимитные тренировки 6 месяцев',
    'emoji': '⭐'
}
```

### Как выдать бесплатный доступ админу?

```python
from modules.payments import create_subscription
from database.models import SubscriptionType

await create_subscription(
    telegram_id=ADMIN_ID,
    subscription_type=SubscriptionType.YEAR,
    duration_days=9999  # "Вечная" подписка
)
```

### Как отключить оплату для тестирования?

Создайте безлимитный промокод:

```python
await create_promocode(
    code="FREEFOREVER",
    promo_type=PromocodeType.FREE_MONTH,
    value=0,
    max_uses=None,
    expires_days=None
)
```

Или закомментируйте декоратор `@subscription_required`.

---

## Поддержка

- **Telegram канал:** @TaktikaKutuzova
- **GitHub Issues:** [создать issue](https://github.com/your-repo/issues)
- **Email:** support@example.com

---

## Лицензия

MIT License — используйте код в своих проектах свободно.

---

## Roadmap v4.1

- [ ] Автопродление подписок
- [ ] Уведомления об истечении подписки
- [ ] Реферальная программа
- [ ] A/B тестирование воронки
- [ ] Интеграция с Telegram Stars
- [ ] Dashboard админа (web)

---

**Создано с ❤️ для разработчиков Telegram ботов**
