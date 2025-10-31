# Database Module Documentation

> **Универсальный модуль БД для multi-bot системы**
> Версия: 4.0 | Поддержка: PostgreSQL, SQLite | Async/await

---

## 📋 Содержание

- [Обзор](#обзор)
- [Архитектура](#архитектура)
- [Модели БД](#модели-бд)
- [Repositories API](#repositories-api)
- [DatabaseService API](#databaseservice-api)
- [Использование в других ботах](#использование-в-других-ботах)
- [Примеры кода](#примеры-кода)
- [Миграции](#миграции)

---

## 🎯 Обзор

Этот модуль предоставляет **переносимую систему БД** для создания нескольких Telegram ботов с:

- ✅ **Единой системой пользователей** (один User на все боты)
- ✅ **Кросс-бот геймификацией** (общие XP, level, badges)
- ✅ **Изоляцией данных по ботам** (каждый бот хранит свои session/stats)
- ✅ **Системой подписок и платежей** (общая для всех ботов)
- ✅ **Async/await** для высокой производительности

### Ключевая идея:

```
Пользователь с telegram_id = 123456:
├── User (ОБЩИЙ)
│   ├── total_xp = 500       ← XP из ВСЕХ ботов
│   ├── level = 5            ← Общий уровень
│   └── badges (ОБЩИЕ)       ← Бейджи из всех ботов
│
├── BotSession (spin_bot)
│   ├── session_data = {...} ← Данные тренировки SPIN
│   └── stats_data = {...}   ← Статистика SPIN
│
└── BotSession (quiz_bot)
    ├── session_data = {...} ← Данные викторины
    └── stats_data = {...}   ← Статистика Quiz
```

---

## 🏗️ Архитектура

### Структура модуля:

```
database/
├── __init__.py              # Экспорты
├── database.py              # Подключение (init_db, get_session, close_db)
├── base_models.py           # Общие модели (User, UserBadge, BotSession, etc.)
├── bot_models.py            # Bot-specific модели (TrainingHistory)
├── models.py                # Legacy модели (backward compatibility)
├── training_models.py       # Legacy TrainingUser
└── repositories/            # CRUD слой
    ├── user_repository.py       # User CRUD
    ├── badge_repository.py      # Badge CRUD
    ├── session_repository.py    # BotSession CRUD
    └── subscription_repository.py # Subscription CRUD
```

### Слои абстракции:

```
┌─────────────────────────────────────┐
│  bot.py (Telegram handlers)         │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│  services/database_service.py       │  ← Высокоуровневый API
│  (DatabaseService)                  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│  database/repositories/*.py         │  ← CRUD операции
│  (UserRepository, BadgeRepository)  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│  database/base_models.py            │  ← SQLAlchemy модели
│  (User, UserBadge, BotSession)      │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│  PostgreSQL / SQLite                │  ← База данных
└─────────────────────────────────────┘
```

---

## 📊 Модели БД

### 1. User - Универсальный пользователь

**Таблица:** `users`

**Назначение:** Центральная модель для всех ботов. Хранит общие данные пользователя.

**Поля:**
```python
id                  # Primary Key
telegram_id         # Unique, Indexed - основной идентификатор
username            # @username в Telegram
first_name          # Имя
last_name           # Фамилия
registration_date   # Дата регистрации
last_activity       # Последняя активность (auto-update)

# Кросс-бот геймификация
total_xp            # Общий XP из ВСЕХ ботов
level               # Общий уровень

# Legacy поля
total_trainings     # Счетчик тренировок
total_score         # Общий счет
```

**Relationships:**
- `badges` → One-to-Many → UserBadge
- `subscriptions` → One-to-Many → Subscription
- `payments` → One-to-Many → Payment
- `bot_sessions` → One-to-Many → BotSession

---

### 2. UserBadge - Кросс-бот бейджи

**Таблица:** `user_badges`

**Назначение:** Бейджи, заработанные в любом боте, видны во всех ботах.

**Поля:**
```python
id              # Primary Key
user_id         # FK → users.id
badge_type      # "spin_master", "quiz_guru", "first_training"
earned_in_bot   # "spin_bot", "quiz_bot" - где заработан
earned_at       # Timestamp
metadata        # JSON - доп. данные {"score": 185, "streak": 5}
```

**Пример:**
```python
# Бейдж "spin_master", заработанный в SPIN боте,
# ВИДЕН в Quiz боте, Challenge боте и т.д.
```

---

### 3. BotSession - Изоляция сессий по ботам

**Таблица:** `bot_sessions`

**Назначение:** Хранит bot-specific данные (сессии, статистику).

**Поля:**
```python
id              # Primary Key
user_id         # FK → users.id
bot_name        # "spin_bot", "quiz_bot" (indexed)
session_data    # JSON - текущая сессия бота
stats_data      # JSON - статистика бота
created_at
updated_at      # Auto-update
```

**Пример session_data для SPIN бота:**
```json
{
  "question_count": 5,
  "clarity_level": 75,
  "chat_state": "in_progress",
  "per_type_counts": {"situation": 2, "problem": 3},
  "case_data": {"client": "TechCorp", "product": "CRM"},
  "last_client_response": "Мы работаем с 5 поставщиками..."
}
```

**Пример stats_data для SPIN бота:**
```json
{
  "total_trainings": 10,
  "best_score": 185,
  "achievements_unlocked": ["spin_master", "active_listener"],
  "maestro_streak": 3,
  "last_training_date": "2025-01-15T10:30:00"
}
```

---

### 4. Subscription - Подписки

**Таблица:** `subscriptions`

**Поля:**
```python
id                  # Primary Key
user_id             # FK → users.id
subscription_type   # Enum: MONTH, YEAR, CREDITS
start_date
end_date            # NULL для credits-based
is_active
auto_renew

# Для кредитов:
credits_total       # Сколько было
credits_left        # Сколько осталось
```

---

### 5. Payment - История платежей

**Таблица:** `payments`

**Поля:**
```python
id              # Primary Key
user_id         # FK → users.id
amount          # Numeric(10, 2)
currency        # "RUB", "USD"
provider        # "cloudpayments", "yookassa", "prodamus"
payment_id      # ID из платежной системы
status          # Enum: PENDING, COMPLETED, FAILED, REFUNDED
tariff          # "month", "year", "credits_5"
```

---

### 6. Promocode & PromocodeUsage - Промокоды

**Таблица:** `promocodes`

**Поля:**
```python
code            # Unique, Indexed - "NEWYEAR2025"
type            # Enum: TRAININGS, FREE_MONTH, CREDITS
value           # Количество
max_uses        # NULL = безлимит
current_uses    # Счетчик
expires_at      # NULL = не истекает
```

---

### 7. FreeTraining - Бесплатные тренировки

**Таблица:** `free_trainings`

**Поля:**
```python
user_id         # FK → users.id
trainings_left  # Счетчик
source          # Enum: CHANNEL, PROMOCODE, ADMIN
```

---

### 8. TrainingHistory - История тренировок (SPIN-specific)

**Таблица:** `training_history`

**Назначение:** Bot-specific модель для хранения истории тренировок SPIN бота.

**Поля:**
```python
id                      # Primary Key
user_id                 # FK → users.id
telegram_id             # Indexed
training_date           # Indexed
scenario_name           # "spin_sales"

# Метрики
total_score             # Балл
clarity_level           # Уровень ясности
question_count          # Количество вопросов
contextual_questions    # Контекстных вопросов

# JSON данные
per_type_counts         # {"situation": 2, "problem": 3, ...}
case_data               # Данные кейса
session_snapshot        # Полный снимок сессии
```

---

## 🔧 Repositories API

### UserRepository

**Создание/получение:**
```python
async def get_or_create(telegram_id, username=None, first_name=None) -> User
async def get_by_telegram_id(telegram_id) -> Optional[User]
async def get_by_id(user_id) -> Optional[User]
```

**Геймификация:**
```python
async def add_xp(telegram_id, xp) -> bool
async def update_level(telegram_id, new_level) -> bool
async def increment_training_count(telegram_id) -> bool
async def add_score(telegram_id, score) -> bool
```

**Рейтинги:**
```python
async def get_leaderboard(limit=10, offset=0) -> List[User]
async def get_user_rank(telegram_id) -> Optional[int]
async def count_total_users() -> int
```

---

### BadgeRepository

```python
async def award_badge(user_id, badge_type, bot_name, metadata=None) -> UserBadge
async def award_badge_by_telegram_id(telegram_id, badge_type, bot_name, metadata=None) -> UserBadge
async def get_user_badges(telegram_id, bot_name=None) -> List[UserBadge]
async def has_badge(telegram_id, badge_type, bot_name) -> bool
async def count_user_badges(telegram_id) -> int
```

---

### SessionRepository

```python
async def get_or_create(user_id, bot_name) -> BotSession
async def get_by_telegram_id(telegram_id, bot_name) -> Optional[BotSession]
async def update_session(telegram_id, bot_name, session_data) -> bool
async def update_stats(telegram_id, bot_name, stats_data) -> bool
async def update_both(telegram_id, bot_name, session_data, stats_data) -> bool
async def reset_session(telegram_id, bot_name, keep_stats=True) -> bool
```

---

### SubscriptionRepository

```python
async def get_active_subscription(telegram_id) -> Optional[Subscription]
async def create_subscription(telegram_id, type, duration_days, credits) -> Subscription
async def check_access(telegram_id) -> Dict[str, Any]
async def consume_access(telegram_id) -> bool
async def add_free_trainings(telegram_id, count, source) -> FreeTraining
```

---

## 🚀 DatabaseService API

**Высокоуровневый API для использования в bot.py**

### Инициализация:

```python
from services.database_service import DatabaseService

db_service = DatabaseService(bot_name="spin_bot")
```

### Основные методы:

**Работа с сессиями:**
```python
# Получить данные пользователя
user_data = await db_service.get_user_session(telegram_id, username, first_name)
# Возвращает: {'user': {...}, 'session': {...}, 'stats': {...}}

# Сохранить сессию
await db_service.save_session(telegram_id, session_data, stats_data)

# Сбросить сессию
await db_service.reset_session(telegram_id, scenario_config)
```

**Геймификация:**
```python
# Добавить XP и проверить level up
result = await db_service.add_xp_and_check_level_up(
    telegram_id, xp_to_add, levels_config
)
# Возвращает: {'leveled_up': bool, 'old_level': int, 'new_level': int, 'total_xp': int}

# Выдать бейдж
awarded = await db_service.award_badge(
    telegram_id, badge_type="spin_master", metadata={"score": 185}
)

# Получить бейджи (из всех ботов или только текущего)
badges = await db_service.get_user_badges(telegram_id, all_bots=True)
```

**История тренировок:**
```python
# Сохранить историю
await db_service.save_training_history(
    telegram_id, total_score, clarity_level, question_count,
    contextual_questions, per_type_counts, case_data, session_snapshot
)

# Получить историю
history = await db_service.get_user_training_history(telegram_id, limit=10)
```

**Подписки:**
```python
# Проверить доступ
access = await db_service.check_access(telegram_id)
# Возвращает: {'has_access': bool, 'access_type': str, 'details': {...}}

# Создать подписку
await db_service.create_subscription(
    telegram_id, SubscriptionType.MONTH, duration_days=30
)

# Добавить бесплатные тренировки
await db_service.add_free_trainings(
    telegram_id, count=3, source=FreeTrainingSource.CHANNEL
)
```

**Статистика:**
```python
# Обновить статистику после тренировки
level_result = await db_service.update_user_stats_after_training(
    telegram_id, session_score, scenario_config
)

# Получить топ пользователей
leaderboard = await db_service.get_leaderboard(limit=10, offset=0)

# Получить ранг пользователя
rank = await db_service.get_user_rank(telegram_id)
```

---

## 🔄 Использование в других ботах

### Шаг 1: Скопировать модуль

```bash
# Скопировать в новый проект
cp -r database/ /path/to/new_bot/
cp services/database_service.py /path/to/new_bot/services/
```

### Шаг 2: Установить зависимости

```bash
pip install sqlalchemy>=2.0.23 asyncpg>=0.30.0 aiosqlite>=0.20.0
```

### Шаг 3: Настроить .env

```bash
DATABASE_URL=postgresql://user:pass@host:5432/dbname
BOT_NAME=my_new_bot  # Уникальное имя бота
```

### Шаг 4: Использовать в bot.py

```python
import asyncio
from database import init_db, close_db
from services.database_service import DatabaseService

# Инициализация БД
async def main():
    await init_db()

    # Создать сервис для вашего бота
    db_service = DatabaseService(bot_name="my_new_bot")

    # Использовать
    user_data = await db_service.get_user_session(telegram_id)

    # ...ваш код...

    await close_db()

if __name__ == '__main__':
    asyncio.run(main())
```

### Шаг 5: Готово!

**Что получаете:**
- ✅ Общие пользователи с первым ботом (по telegram_id)
- ✅ Общие XP, level, badges между ботами
- ✅ Изолированные сессии (каждый бот хранит свои данные)
- ✅ Единая система подписок

---

## 📝 Примеры кода

### Пример 1: Создание нового пользователя

```python
from database import get_session
from database.repositories import UserRepository

async def create_user_example():
    async with get_session() as session:
        user_repo = UserRepository(session)

        user = await user_repo.get_or_create(
            telegram_id=123456,
            username="johndoe",
            first_name="John"
        )

        print(f"User created: {user.telegram_id}, XP: {user.total_xp}, Level: {user.level}")
```

### Пример 2: Работа с сессией

```python
from services.database_service import DatabaseService

async def session_example():
    db_service = DatabaseService(bot_name="spin_bot")

    # Получить сессию
    user_data = await db_service.get_user_session(telegram_id=123456)

    # Модифицировать
    user_data['session']['question_count'] = 5
    user_data['session']['clarity_level'] = 75

    # Сохранить
    await db_service.save_session(
        telegram_id=123456,
        session_data=user_data['session'],
        stats_data=user_data['stats']
    )
```

### Пример 3: Добавление XP и level up

```python
async def xp_example():
    db_service = DatabaseService(bot_name="spin_bot")

    levels_config = [
        {"level": 1, "min_xp": 0},
        {"level": 2, "min_xp": 100},
        {"level": 3, "min_xp": 300}
    ]

    result = await db_service.add_xp_and_check_level_up(
        telegram_id=123456,
        xp_to_add=150,
        levels_config=levels_config
    )

    if result['leveled_up']:
        print(f"🎊 Level up! {result['old_level']} → {result['new_level']}")
```

### Пример 4: Выдача бейджа

```python
async def badge_example():
    db_service = DatabaseService(bot_name="spin_bot")

    # Выдать бейдж
    awarded = await db_service.award_badge(
        telegram_id=123456,
        badge_type="spin_master",
        metadata={"score": 185, "date": "2025-01-15"}
    )

    if awarded:
        print("🏆 Бейдж выдан!")
    else:
        print("Бейдж уже есть у пользователя")

    # Получить все бейджи
    badges = await db_service.get_user_badges(telegram_id=123456, all_bots=True)
    for badge in badges:
        print(f"- {badge['badge_type']} (from {badge['earned_in_bot']})")
```

### Пример 5: Сохранение истории тренировки

```python
async def history_example():
    db_service = DatabaseService(bot_name="spin_bot")

    await db_service.save_training_history(
        telegram_id=123456,
        total_score=185,
        clarity_level=92,
        question_count=8,
        contextual_questions=3,
        per_type_counts={"situation": 2, "problem": 3, "implication": 2, "need_payoff": 1},
        case_data={"client": "TechCorp", "product": "CRM System"},
        session_snapshot={"full": "session", "data": "here"}
    )

    # Получить историю
    history = await db_service.get_user_training_history(telegram_id=123456, limit=5)
    for record in history:
        print(f"Тренировка {record['training_date']}: {record['total_score']} баллов")
```

### Пример 6: Кросс-бот геймификация

```python
async def cross_bot_example():
    # SPIN бот добавляет XP
    db_spin = DatabaseService(bot_name="spin_bot")
    await db_spin.add_xp_and_check_level_up(telegram_id=123456, xp_to_add=100)

    # Quiz бот видит ТОТ ЖЕ XP!
    db_quiz = DatabaseService(bot_name="quiz_bot")
    user_data = await db_quiz.get_user_session(telegram_id=123456)

    print(f"XP в Quiz боте (общий): {user_data['user']['total_xp']}")  # 100!
    print(f"Level в Quiz боте (общий): {user_data['user']['level']}")  # 2!

    # Но сессии РАЗНЫЕ:
    print(f"Session Quiz бота: {user_data['session']}")  # Пустая сессия для quiz_bot
```

---

## 🔄 Миграции

### Миграция из JSON

Если у вас есть старый `users_data.json`, используйте скрипт миграции:

```bash
python scripts/migrate_from_json.py users_data.json
```

**Скрипт:**
- ✅ Загружает данные из JSON
- ✅ Создает пользователей в БД
- ✅ Переносит XP, level, stats
- ✅ Создает BotSession для каждого пользователя
- ✅ Создает бэкап JSON файла

### Создание новой БД

```python
import asyncio
from database import init_db

async def create_db():
    await init_db()
    print("✅ База данных создана!")

asyncio.run(create_db())
```

---

## 🔍 FAQ

### Q: Как работает кросс-бот геймификация?

**A:** Все боты используют ОДНУ таблицу `users` с общим `telegram_id`. XP и level хранятся в этой таблице, поэтому видны во всех ботах. Но каждый бот имеет свою запись в `bot_sessions` для изоляции данных.

### Q: Можно ли использовать модуль с SQLite?

**A:** Да! В `.env` укажите:
```
DATABASE_URL=sqlite+aiosqlite:///./my_bot.db
```

### Q: Как добавить новое поле в User?

**A:**
1. Отредактировать `database/base_models.py`
2. Добавить поле в класс User
3. Создать миграцию через Alembic (опционально)
4. Запустить `await init_db()` для SQLite (создаст новое поле)

### Q: Можно ли создать bot-specific модель?

**A:** Да! Добавьте в `database/bot_models.py`:
```python
class MyBotData(Base):
    __tablename__ = "my_bot_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # ...ваши поля
```

### Q: Как удалить все данные пользователя?

**A:**
```python
async with get_session() as session:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)

    if user:
        await session.delete(user)  # Cascade удалит все связанные данные
        await session.flush()
```

---

## 📚 Дополнительная документация

- **Полное API:** См. docstrings в каждом файле
- **Примеры:** `V4_INTEGRATION_GUIDE.md`, `V4_SUMMARY.md`
- **Архитектура:** `ARCHITECTURE_ANALYSIS.md`

---

## 🤝 Поддержка

Telegram: @TaktikaKutuzova

---

**Модуль готов к использованию! 🚀**
