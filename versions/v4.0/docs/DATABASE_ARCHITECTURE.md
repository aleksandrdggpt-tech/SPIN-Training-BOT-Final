# 🗄️ Архитектура базы данных SPIN Training Bot

## 📋 Содержание

- [Обзор](#обзор)
- [Тип базы данных](#тип-базы-данных)
- [Структура подключения](#структура-подключения)
- [Архитектура слоев](#архитектура-слоев)
- [Модели данных](#модели-данных)
- [Инициализация БД](#инициализация-бд)
- [Использование в коде](#использование-в-коде)
- [Потоки данных](#потоки-данных)
- [Примеры использования](#примеры-использования)

---

## 🎯 Обзор

Бот использует **SQLAlchemy с async поддержкой** для работы с базой данных. Поддерживаются две СУБД:

- **PostgreSQL** (production) - через `asyncpg`
- **SQLite** (development/testing) - через `aiosqlite`

### Ключевые особенности:

- ✅ **Async/await** - все операции асинхронные
- ✅ **Multi-bot архитектура** - изоляция данных по ботам
- ✅ **Кросс-бот геймификация** - общие XP, level, badges
- ✅ **Repository pattern** - разделение логики и доступа к данным
- ✅ **Service layer** - высокоуровневый API для bot.py

---

## 🗄️ Тип базы данных

### Определение типа БД

Тип базы данных определяется через переменную окружения `DATABASE_URL`:

```python
# database/database.py
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./spin_bot.db')
```

### Варианты подключения:

#### 1. SQLite (локальная разработка)
```bash
DATABASE_URL=sqlite+aiosqlite:///./spin_bot.db
```

**Характеристики:**
- Файловая БД (создается автоматически)
- Не требует настройки сервера
- Работает без event loop конфликтов
- Подходит для тестирования

#### 2. PostgreSQL (production)
```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

**Характеристики:**
- Серверная БД (Railway, Heroku, etc.)
- Высокая производительность
- Поддержка транзакций
- Автоматическое преобразование URL

### Автоматическое преобразование URL

```python
# database/database.py (строки 27-31)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)
```

**Логика:**
- `postgres://` → `postgresql://` (совместимость с Railway/Heroku)
- `postgresql://` → `postgresql+asyncpg://` (добавление async драйвера)

---

## 🔌 Структура подключения

### 1. Создание Engine

```python
# database/database.py (строки 34-40)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,              # Логирование SQL запросов
    future=True,             # Использование SQLAlchemy 2.0 API
    pool_pre_ping=True,     # Проверка соединения перед использованием
    pool_recycle=3600,      # Переподключение каждый час
)
```

**Параметры:**
- `pool_pre_ping=True` - проверяет соединение перед использованием (предотвращает "connection lost" ошибки)
- `pool_recycle=3600` - переподключение каждые 3600 секунд (предотвращает таймауты)

### 2. Создание Session Factory

```python
# database/database.py (строки 45-49)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Объекты остаются доступными после commit
)
```

**Параметры:**
- `expire_on_commit=False` - объекты остаются доступными после commit (удобно для работы с данными)

### 3. Context Manager для сессий

```python
# database/database.py (строки 71-103)
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()  # Автоматический commit при успехе
        except Exception as e:
            await session.rollback()  # Автоматический rollback при ошибке
            raise
```

**Использование:**
```python
async with get_session() as session:
    # Ваши операции с БД
    user = await session.get(User, user_id)
    # Автоматический commit при выходе из блока
```

---

## 🏗️ Архитектура слоев

### Схема взаимодействия:

```
┌─────────────────────────────────────────────────────────┐
│  bot.py (Telegram handlers)                              │
│  - handle_message()                                       │
│  - start_command()                                       │
│  - process_question()                                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  services/user_service_db.py (UserServiceDB)            │
│  - Адаптер для обратной совместимости                    │
│  - Конвертирует sync → async                            │
│  - Использует DatabaseService                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  services/database_service.py (DatabaseService)         │
│  - Высокоуровневый API                                   │
│  - get_user_session()                                    │
│  - save_session()                                         │
│  - add_xp_and_check_level_up()                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  database/repositories/*.py (Repositories)              │
│  - UserRepository                                        │
│  - SessionRepository                                     │
│  - BadgeRepository                                       │
│  - SubscriptionRepository                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  database/database.py (get_session)                     │
│  - Context manager для сессий                            │
│  - Автоматический commit/rollback                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  database/base_models.py (SQLAlchemy Models)            │
│  - User                                                  │
│  - BotSession                                            │
│  - UserBadge                                             │
│  - Subscription                                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL / SQLite                                     │
└─────────────────────────────────────────────────────────┘
```

### Описание слоев:

#### 1. **bot.py** (Telegram handlers)
- Обрабатывает команды и сообщения от пользователей
- Использует `UserServiceDB` для работы с данными
- Не знает о деталях БД

#### 2. **UserServiceDB** (Адаптер)
- Предоставляет sync API для обратной совместимости
- Конвертирует sync вызовы в async через `nest_asyncio`
- Использует `DatabaseService` внутри

#### 3. **DatabaseService** (Высокоуровневый API)
- Упрощенный интерфейс для работы с БД
- Комбинирует несколько репозиториев
- Обрабатывает общие workflow (создание пользователя + сессии)

#### 4. **Repositories** (CRUD операции)
- Низкоуровневые операции с БД
- Один репозиторий = одна модель
- Использует SQLAlchemy ORM

#### 5. **Models** (SQLAlchemy Models)
- Определение структуры таблиц
- Relationships между моделями
- Валидация данных

---

## 📊 Модели данных

### Основные таблицы:

#### 1. **users** - Универсальный пользователь

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int]                    # Primary Key
    telegram_id: Mapped[int]            # Unique, Indexed
    username: Mapped[Optional[str]]
    first_name: Mapped[Optional[str]]
    last_name: Mapped[Optional[str]]
    
    # Кросс-бот геймификация
    total_xp: Mapped[int] = 0           # Общий XP из всех ботов
    level: Mapped[int] = 1              # Общий уровень
    
    # Legacy статистика
    total_trainings: Mapped[int] = 0
    total_score: Mapped[int] = 0
    
    # Relationships
    badges: Mapped[list["UserBadge"]]
    subscriptions: Mapped[list["Subscription"]]
    bot_sessions: Mapped[list["BotSession"]]
```

**Назначение:** Центральная модель для всех ботов. Хранит общие данные пользователя.

#### 2. **bot_sessions** - Изоляция сессий по ботам

```python
class BotSession(Base):
    __tablename__ = "bot_sessions"
    
    id: Mapped[int]
    user_id: Mapped[int]                # FK → users.id
    bot_name: Mapped[str]               # "spin_bot", "quiz_bot" (indexed)
    
    # JSON данные
    session_data: Mapped[dict]          # Текущая сессия
    stats_data: Mapped[dict]            # Статистика бота
    
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]        # Auto-update
```

**Назначение:** Хранит bot-specific данные. Каждый бот имеет свою запись для каждого пользователя.

**Пример session_data:**
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

#### 3. **user_badges** - Кросс-бот бейджи

```python
class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id: Mapped[int]
    user_id: Mapped[int]                # FK → users.id
    badge_type: Mapped[str]             # "spin_master", "quiz_guru"
    earned_in_bot: Mapped[str]          # "spin_bot", "quiz_bot"
    earned_at: Mapped[datetime]
    metadata: Mapped[Optional[dict]]    # JSON доп. данные
```

**Назначение:** Бейджи, заработанные в любом боте, видны во всех ботах.

#### 4. **subscriptions** - Подписки

```python
class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id: Mapped[int]
    user_id: Mapped[int]                # FK → users.id
    subscription_type: Mapped[SubscriptionType]  # MONTH, YEAR, CREDITS
    start_date: Mapped[datetime]
    end_date: Mapped[Optional[datetime]]
    is_active: Mapped[bool]
    
    # Для кредитов
    credits_total: Mapped[Optional[int]]
    credits_left: Mapped[Optional[int]]
```

**Назначение:** Управление подписками и доступом к тренировкам.

#### 5. **free_trainings** - Бесплатные тренировки

```python
class FreeTraining(Base):
    __tablename__ = "free_trainings"
    
    id: Mapped[int]
    user_id: Mapped[int]                # FK → users.id
    trainings_left: Mapped[int]         # Счетчик
    source: Mapped[FreeTrainingSource]  # CHANNEL, PROMOCODE, ADMIN
```

**Назначение:** Хранит количество бесплатных тренировок от разных источников.

#### 6. **training_history** - История тренировок (SPIN-specific)

```python
class TrainingHistory(Base):
    __tablename__ = "training_history"
    
    id: Mapped[int]
    user_id: Mapped[int]
    telegram_id: Mapped[int]            # Indexed
    training_date: Mapped[datetime]     # Indexed
    
    # Метрики
    total_score: Mapped[int]
    clarity_level: Mapped[int]
    question_count: Mapped[int]
    
    # JSON данные
    per_type_counts: Mapped[dict]
    case_data: Mapped[dict]
    session_snapshot: Mapped[dict]
```

**Назначение:** История всех тренировок пользователя (bot-specific модель).

---

## 🚀 Инициализация БД

### 1. Вызов в bot.py

```python
# bot.py (строки 642-646)
async def initialize_database():
    """Initialize database asynchronously."""
    logger.info("🔄 Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")
```

### 2. Вызов в main()

```python
# bot.py (строки 707-716)
# Инициализация базы данных в существующем loop
try:
    loop.run_until_complete(initialize_database())
except Exception as e:
    logger.error(f"Ошибка инициализации БД: {e}")
    print(f"❌ Не удалось инициализировать базу данных: {e}")
    remove_pid_file()
    return
```

### 3. Функция init_db()

```python
# database/database.py (строки 52-68)
async def init_db() -> None:
    """
    Initialize database: create all tables.
    Should be called once at application startup.
    """
    logger.info("🔵 init_db() STARTED")
    try:
        async with engine.begin() as conn:
            logger.info("🔵 Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("🔵 Tables created successfully")
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"🔴 ERROR in init_db(): {e}")
        raise
    finally:
        logger.info("🔵 init_db() FINISHED")
```

**Что происходит:**
1. Создается транзакция через `engine.begin()`
2. Вызывается `Base.metadata.create_all` для создания всех таблиц
3. Таблицы создаются автоматически на основе моделей из `base_models.py`

### 4. Закрытие БД при завершении

```python
# bot.py (строки 649-665)
async def cleanup_resources():
    """Cleanup resources on shutdown."""
    logger.info("🔄 Cleaning up resources...")
    
    try:
        await close_db()
        logger.info("✅ Database closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
```

```python
# database/database.py (строки 106-118)
async def close_db() -> None:
    """
    Close database connection.
    Should be called on application shutdown.
    """
    logger.info("🔵 close_db() STARTED")
    try:
        await engine.dispose()  # Закрывает все соединения
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"🔴 ERROR in close_db(): {e}")
    finally:
        logger.info("🔵 close_db() FINISHED")
```

---

## 💻 Использование в коде

### 1. В bot.py (через UserServiceDB)

```python
# bot.py (строка 70)
user_service = UserServiceDB(bot_name="spin_bot")

# Использование в обработчиках
# bot.py (строка 272)
user_data = user_service.get_user_data(user_id)

# bot.py (строка 545)
user_service.save_user_data(user_id, session, user_data['stats'])
```

**Особенности:**
- Sync API (для обратной совместимости)
- Внутри конвертируется в async через `nest_asyncio`
- Использует `DatabaseService`

### 2. В modules/payments (напрямую через get_session)

```python
# modules/payments/handlers.py (строка 13)
from database.database import get_session

# modules/payments/handlers.py (строка 46)
async with get_session() as session:
    # Прямая работа с репозиториями
    from database.repositories import UserRepository
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    # Автоматический commit при выходе из блока
```

**Особенности:**
- Async API (нативный async/await)
- Прямой доступ к репозиториям
- Полный контроль над транзакциями

### 3. В services/database_service.py (высокоуровневый API)

```python
# services/database_service.py (строки 88-109)
async with get_session() as session:
    user_repo = UserRepository(session)
    session_repo = SessionRepository(session)
    
    # Get or create user
    user = await user_repo.get_or_create(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )
    
    # Get or create bot session
    bot_session = await session_repo.get_or_create(
        user_id=user.id,
        bot_name=self.bot_name
    )
```

**Особенности:**
- Комбинирует несколько репозиториев
- Упрощенный API для общих операций
- Автоматическое создание пользователя и сессии

---

## 🔄 Потоки данных

### Поток 1: Получение данных пользователя

```
1. bot.py: handle_message()
   ↓
2. user_service.get_user_data(user_id)
   ↓
3. UserServiceDB._run_async()
   ↓
4. DatabaseService.get_user_session()
   ↓
5. get_session() → создает сессию
   ↓
6. UserRepository.get_or_create() → получает/создает User
   ↓
7. SessionRepository.get_or_create() → получает/создает BotSession
   ↓
8. Возврат {'user': {...}, 'session': {...}, 'stats': {...}}
   ↓
9. Автоматический commit через get_session()
```

### Поток 2: Сохранение данных

```
1. bot.py: process_question()
   ↓
2. user_service.save_user_data(user_id, session_data, stats_data)
   ↓
3. UserServiceDB._run_async()
   ↓
4. DatabaseService.save_session()
   ↓
5. get_session() → создает сессию
   ↓
6. SessionRepository.update_both() → обновляет session_data и stats_data
   ↓
7. Автоматический commit через get_session()
```

### Поток 3: Проверка подписки (modules/payments)

```
1. modules/payments/handlers.py: check_subscription_callback()
   ↓
2. get_session() → создает сессию
   ↓
3. SubscriptionRepository.check_access() → проверяет подписку
   ↓
4. SubscriptionRepository.get_active_subscription() → получает активную подписку
   ↓
5. Возврат результата
   ↓
6. Автоматический commit через get_session()
```

---

## 📝 Примеры использования

### Пример 1: Получение данных пользователя

```python
# В bot.py
user_data = user_service.get_user_data(user_id)

# Результат:
{
    'session': {
        'question_count': 5,
        'clarity_level': 75,
        'chat_state': 'in_progress',
        ...
    },
    'stats': {
        'total_trainings': 10,
        'best_score': 185,
        ...
    }
}
```

### Пример 2: Сохранение данных

```python
# В bot.py
user_data = user_service.get_user_data(user_id)
user_data['session']['question_count'] = 6
user_data['session']['clarity_level'] = 80

user_service.save_user_data(
    user_id,
    user_data['session'],
    user_data['stats']
)
```

### Пример 3: Прямая работа с репозиториями

```python
# В modules/payments/handlers.py
from database.database import get_session
from database.repositories import UserRepository, SubscriptionRepository

async with get_session() as session:
    user_repo = UserRepository(session)
    sub_repo = SubscriptionRepository(session)
    
    # Получить пользователя
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    # Проверить подписку
    subscription = await sub_repo.get_active_subscription(telegram_id)
    
    # Автоматический commit при выходе из блока
```

### Пример 4: Добавление XP и проверка level up

```python
# В services/database_service.py
result = await db_service.add_xp_and_check_level_up(
    telegram_id=123456,
    xp_to_add=150,
    levels_config=[
        {"level": 1, "min_xp": 0},
        {"level": 2, "min_xp": 100},
        {"level": 3, "min_xp": 300}
    ]
)

# Результат:
{
    'leveled_up': True,
    'old_level': 1,
    'new_level': 2,
    'total_xp': 150
}
```

### Пример 5: Выдача бейджа

```python
# В services/database_service.py
awarded = await db_service.award_badge(
    telegram_id=123456,
    badge_type="spin_master",
    metadata={"score": 185, "date": "2025-01-15"}
)

# Результат: True (бейдж выдан) или False (уже есть)
```

---

## 🔍 Важные детали

### 1. Транзакции

Все операции выполняются в транзакциях через `get_session()`:

```python
async with get_session() as session:
    # Все операции здесь - одна транзакция
    user = await user_repo.get_or_create(...)
    session_data = await session_repo.update(...)
    # Автоматический commit при успешном выходе
    # Автоматический rollback при ошибке
```

### 2. Изоляция данных по ботам

Каждый бот имеет свою запись в `bot_sessions`:

```python
# SPIN бот
bot_session_spin = await session_repo.get_or_create(
    user_id=user.id,
    bot_name="spin_bot"
)

# Quiz бот (тот же пользователь, но другая сессия)
bot_session_quiz = await session_repo.get_or_create(
    user_id=user.id,
    bot_name="quiz_bot"
)
```

### 3. Кросс-бот геймификация

XP и level хранятся в общей таблице `users`:

```python
# SPIN бот добавляет XP
await user_repo.add_xp(telegram_id, 100)

# Quiz бот видит ТОТ ЖЕ XP
user = await user_repo.get_by_telegram_id(telegram_id)
print(user.total_xp)  # 100 (общий для всех ботов)
```

### 4. Автоматическое создание пользователя

При первом обращении пользователь создается автоматически:

```python
# Если пользователя нет - создается автоматически
user = await user_repo.get_or_create(
    telegram_id=123456,
    username="johndoe",
    first_name="John"
)
```

### 5. JSON поля

`session_data` и `stats_data` хранятся как JSON:

- **PostgreSQL**: Использует тип `JSONB` (бинарный JSON)
- **SQLite**: Использует тип `TEXT` (текстовый JSON)

SQLAlchemy автоматически конвертирует Python dict ↔ JSON.

---

## 🛠️ Отладка

### Включение SQL логирования

```python
# database/database.py (строка 36)
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Включить логирование SQL запросов
    ...
)
```

### Проверка подключения

```python
# Проверить, что БД подключена
from database.database import engine

async def test_connection():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(result.scalar())  # Должно вывести: 1
```

### Просмотр данных

**SQLite:**
```bash
sqlite3 spin_bot.db
.tables
SELECT * FROM users;
```

**PostgreSQL:**
```bash
psql $DATABASE_URL
\dt
SELECT * FROM users;
```

---

## 📚 Дополнительная документация

- **Полное API репозиториев:** `database/README.md`
- **Примеры использования:** `database/README.md` (раздел Examples)
- **Модели данных:** `database/base_models.py` (docstrings)
- **Миграции:** `scripts/migrate_from_json.py`

---

*Последнее обновление: 2025-01-16*

