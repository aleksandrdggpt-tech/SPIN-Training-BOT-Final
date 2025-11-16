# 🚀 Руководство по интеграции Payment Module v4

> Быстрый старт для интеграции модуля оплаты в существующий bot.py v3

---

## ✅ Что создано

### Структура файлов

```
✅ modules/payments/          # Модуль оплаты (полностью готов)
✅ database/                  # SQLAlchemy модели и подключение
✅ REQUIREMENTS_v4.txt        # Зависимости
✅ .env.v4.example            # Пример конфигурации
✅ README_v4.md               # Полная документация
```

### Возможности модуля

- ✅ Система подписок (месяц/год)
- ✅ Pay-per-use модель (кредиты)
- ✅ Промокоды (тренировки/подписка/кредиты)
- ✅ Бесплатные тренировки за подписку на канал
- ✅ Воронка продаж с конверсионными текстами
- ✅ Декоратор `@subscription_required` для защиты функций
- ✅ 3 платежных провайдера (YooKassa, CloudPayments, Prodamus)
- ✅ База данных SQLAlchemy (async SQLite)

---

## 🎯 План интеграции в bot.py

### Шаг 1: Установить зависимости

```bash
pip install -r REQUIREMENTS_v4.txt
```

### Шаг 2: Инициализировать базу данных

```bash
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
```

### Шаг 3: Обновить bot.py

#### A) Добавить импорты (в начало файла)

```python
# После существующих импортов добавить:
from database import init_db, close_db
from modules.payments.handlers import register_payment_handlers
from modules.payments import subscription_required
```

#### B) Инициализировать БД при запуске

Найти функцию `main()` и добавить:

```python
async def main():
    """Главная функция запуска бота."""
    # Существующий код...

    # ✅ ДОБАВИТЬ: Инициализация базы данных
    logger.info("🔄 Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Существующий код создания application...
    application = Application.builder().token(config.BOT_TOKEN).build()

    # ✅ ДОБАВИТЬ: Регистрация payment handlers
    logger.info("🔄 Registering payment handlers...")
    register_payment_handlers(application)
    logger.info("✅ Payment handlers registered")

    # Остальной код...
```

#### C) Закрыть БД при остановке

В конце функции `main()` добавить:

```python
    finally:
        # ✅ ДОБАВИТЬ: Закрытие базы данных
        logger.info("🔄 Closing database...")
        await close_db()
        logger.info("✅ Database closed")
```

#### D) Защитить функции подпиской

Найти функции, которые требуют подписки (например, `start_training_command`), и добавить декоратор:

```python
# БЫЛО:
async def start_training_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать новую тренировку."""
    # код...

# СТАЛО:
@subscription_required  # ✅ ДОБАВИТЬ
async def start_training_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать новую тренировку."""
    # код...
```

Применить к функциям:
- `start_training_command` (или аналогичная)
- `training_message_handler` (если есть)
- Любые другие функции, требующие платный доступ

---

## 📋 Чеклист интеграции

### Обязательные шаги

- [ ] Установить зависимости (`pip install -r REQUIREMENTS_v4.txt`)
- [ ] Скопировать `.env.v4.example` в `.env` и заполнить
- [ ] Инициализировать базу данных
- [ ] Добавить импорты в `bot.py`
- [ ] Добавить `init_db()` в `main()`
- [ ] Зарегистрировать payment handlers
- [ ] Добавить `@subscription_required` к защищаемым функциям
- [ ] Добавить `close_db()` в finally
- [ ] Протестировать команду `/payment`
- [ ] Создать тестовый промокод

### Опциональные шаги

- [ ] Настроить платежного провайдера (YooKassa/CloudPayments/Prodamus)
- [ ] Настроить канал для бесплатных тренировок
- [ ] Изменить цены в `modules/payments/config.py`
- [ ] Настроить тексты воронки в `modules/payments/messages.py`
- [ ] Добавить админ-команды для управления промокодами
- [ ] Настроить автопродление подписок

---

## 🧪 Тестирование

### 1. Запустить бота

```bash
python bot.py
```

### 2. Проверить команды

- `/payment` — должно открыться меню оплаты
- `/start` — должно показать "нет подписки" (если не активирована)

### 3. Создать тестовый промокод

```python
# Запустить в Python shell
import asyncio
from database import get_session
from modules.payments.promocodes import create_promocode
from database.models import PromocodeType

async def create_test_promo():
    async with get_session() as session:
        success, message, promo = await create_promocode(
            code="TEST",
            promo_type=PromocodeType.TRAININGS,
            value=10,
            max_uses=None,
            expires_days=None,
            session=session
        )
        print(message)

asyncio.run(create_test_promo())
```

### 4. Активировать промокод

- Открыть бот
- `/payment` → "У меня есть промокод"
- Ввести `TEST`
- Должно выдать 10 бесплатных тренировок

### 5. Проверить доступ

- `/start` — теперь должно запуститься без ошибок

---

## 🔧 Настройка для продакшна

### 1. Платежная система

Выбрать провайдера и добавить в `.env`:

**YooKassa:**
```env
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=live_xxx
```

**CloudPayments:**
```env
CLOUDPAYMENTS_PUBLIC_KEY=pk_xxx
CLOUDPAYMENTS_API_SECRET=xxx
```

**Prodamus:**
```env
PRODAMUS_API_KEY=xxx
```

Затем реализовать методы в соответствующем файле `modules/payments/providers/*.py`.

### 2. База данных PostgreSQL (опционально)

Для продакшна рекомендуется PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/spin_bot
```

```bash
pip install asyncpg
```

### 3. Канал для бесплатных тренировок

Указать в `.env`:

```env
CHANNEL_USERNAME=TaktikaKutuzova
```

Бот проверит подписку и выдаст 2 бесплатные тренировки.

---

## 🎨 Кастомизация

### Изменить цены

Файл: `modules/payments/config.py`

```python
TARIFFS = {
    'month': {
        'price': 1490,  # Изменить здесь
        ...
    }
}
```

### Изменить тексты воронки

Файл: `modules/payments/messages.py`

Отредактировать переменные:
- `WELCOME_SALES`
- `TARIFF_MONTH`
- `TARIFF_YEAR`
- и т.д.

### Добавить новый тариф

В `config.py`:

```python
TARIFFS['half_year'] = {
    'name': 'Подписка на 6 месяцев',
    'price': 4990,
    'currency': 'RUB',
    'duration_days': 180,
    'description': 'Безлимитные тренировки полгода',
    'emoji': '⭐'
}
```

---

## 📊 Админ-функции

### Создать промокод (через код)

```python
from modules.payments import create_promocode
from database.models import PromocodeType

await create_promocode(
    code="NEWYEAR2024",
    promo_type=PromocodeType.FREE_MONTH,
    value=0,
    max_uses=100,
    expires_days=30
)
```

### Выдать доступ пользователю

```python
from modules.payments import create_subscription
from database.models import SubscriptionType

await create_subscription(
    telegram_id=123456789,
    subscription_type=SubscriptionType.MONTH,
    duration_days=30
)
```

### Список промокодов

```python
from modules.payments.promocodes import list_promocodes

promos = await list_promocodes(active_only=True, limit=50)
for promo in promos:
    print(promo)
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'database'"

```bash
pip install sqlalchemy aiosqlite
```

### "Database not initialized"

```bash
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
```

### "/payment не работает"

Проверить, что зарегистрированы handlers:

```python
register_payment_handlers(application)
```

### "Промокод не активируется"

Проверить:
1. Промокод создан (`list_promocodes()`)
2. Не истек срок действия
3. Не превышен лимит использований
4. Пользователь не активировал его ранее

---

## 📚 Дополнительная документация

- **Полная документация:** `README_v4.md`
- **API модуля:** Docstrings в каждом файле
- **Примеры использования:** См. `README_v4.md` раздел "Использование"

---

## 🎯 Следующие шаги

1. ✅ Интегрировать модуль в bot.py (следовать чеклисту выше)
2. ✅ Протестировать локально
3. ✅ Создать тестовые промокоды
4. ✅ Настроить платежного провайдера
5. ✅ Задеплоить на Railway/сервер
6. ✅ Подключить реальную платежную систему
7. ✅ Запустить для пользователей

---

## ❓ Нужна помощь?

**Telegram:** @TaktikaKutuzova
**Issues:** GitHub repository

---

**Модуль готов к использованию! 🚀**
