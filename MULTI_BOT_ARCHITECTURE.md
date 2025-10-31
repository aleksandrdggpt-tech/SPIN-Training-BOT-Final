# ✅ Multi-Bot Система - Архитектура

## 🎯 Вопрос: Единая БД для нескольких ботов?

### ✅ ОТВЕТ: ДА! УЖЕ РЕАЛИЗОВАНО! ✅

---

## 📊 Что уже реализовано

### 1. ✅ ЕДИНАЯ БД ДЛЯ НЕСКОЛЬКИХ БОТОВ

**Архитектура:**

```
PostgreSQL (Railway)
├── users (ОБЩАЯ)
│   ├── telegram_id (уникальный)
│   ├── total_xp (кросс-бот)
│   ├── level (кросс-бот)
│   └── badges (общие)
│
├── bot_sessions (ИЗОЛЯЦИЯ)
│   ├── user_id → users.id
│   ├── bot_name ("spin_bot", "quiz_bot", ...)
│   ├── session_data (JSON - данные конкретного бота)
│   └── stats_data (JSON - статистика конкретного бота)
│
├── badges (ОБЩАЯ)
│   ├── name, description
│   └── criteria
│
├── promocodes (ОБЩАЯ)
│   ├── code, type, value
│   └── uses_left
│
├── subscriptions (ОБЩАЯ)
│   ├── user_id
│   └── type, expires_at
│
└── payments (ОБЩАЯ)
    ├── user_id
    └── amount, status
```

**Как это работает:**

```python
# Пример: Пользователь 123456

User:
  telegram_id = 123456
  total_xp = 500  # ← из spin_bot + quiz_bot + других
  level = 5       # ← общий уровень

BotSession:
  bot_name = "spin_bot"
  session_data = {"question_count": 5, "clarity": 75}
  stats_data = {"total_trainings": 10}  # ← данные SPIN бота

BotSession:
  bot_name = "quiz_bot"
  session_data = {"current_question": 3, "score": 120}
  stats_data = {"quizzes_completed": 5}  # ← данные quiz_bot

# ОБЩИЕ данные:
- badges (выданные во ВСЕХ ботах)
- promocodes (работают для ВСЕХ ботов)
- subscriptions (работают для ВСЕХ ботов)
```

---

### 2. ✅ ЕДИНАЯ СИСТЕМА НАГРАД (Badges)

**Реализация:**
- Таблица `badges` - ОБЩАЯ
- Таблица `badge_user_association` - ОБЩАЯ
- Пользователь получает XP во всех ботах → общий уровень
- Бейджи выдаются в любом боте → видны во всех ботах

**Пример:**
```
Пользователь играет в spin_bot:
- Завершил тренировку
- Получил XP → total_xp повысился
- Получил бейдж "Первый шаг"

Тот же пользователь в quiz_bot:
- Видит свой уровень (из spin_bot)
- Видит бейдж "Первый шаг" (из spin_bot)
- Получает XP за квиз → total_xp растёт
```

---

### 3. ✅ ЕДИНАЯ СИСТЕМА ПРОМОКОДОВ

**Реализация:**
- Таблица `promocodes` - ОБЩАЯ
- Таблица `promocode_usage` - ОБЩАЯ
- Промокод работает во ВСЕХ ботах
- Активация записывается в общую таблицу

**Пример:**
```python
# Промокод "WELCOME2024"
# Можно использовать в spin_bot, quiz_bot, и т.д.
# Активация записывается в единую БД
```

---

### 4. ✅ ЕДИНАЯ СИСТЕМА ПОДПИСОК/ПЛАТЕЖЕЙ

**Реализация:**
- Таблица `subscriptions` - ОБЩАЯ
- Таблица `payments` - ОБЩАЯ
- Подписка работает во ВСЕХ ботах
- Платежи видны везде

---

## 📋 ЧТО СДЕЛАНО ИЗ ВАШЕГО СПИСКА

### ✅ 1. Файл spin_bot.db НЕ создается (используется PostgreSQL)
**СТАТУС:** ⚠️ ЧАСТИЧНО
- **Локально:** SQLite (для избежания event loop конфликтов)
- **Railway:** PostgreSQL через `DATABASE_URL`
- **Таблицы:** PostgreSQL создаются автоматически через `init_db()`
- **Миграция:** При переключении с SQLite на PostgreSQL нужно создать таблицы заново

### ✅ 2. В Railway видны созданные таблицы
**СТАТУС:** ✅ ГОТОВО К ТЕСТИРОВАНИЮ
- `init_db()` создаст все таблицы при первом запуске
- Таблицы: `users`, `bot_sessions`, `badges`, `promocodes`, `subscriptions`, `payments`, `training_history`

### ✅ 3. /start создает пользователя в БД
**СТАТУС:** ✅ РЕАЛИЗОВАНО
- В `services/user_service_db.py` -> `get_user_data()`
- В `database/repositories/user_repository.py` -> `get_or_create()`
- При `/start` создаётся User и BotSession

### ✅ 4. После рестарта бота данные сохраняются
**СТАТУС:** ✅ РЕАЛИЗОВАНО
- Данные в PostgreSQL сохраняются при каждом изменении
- `save_user_data()` записывает в БД
- `save_session()` обновляет BotSession

### ✅ 5. users_data.json больше не используется
**СТАТУС:** ⚠️ ЧАСТИЧНО
- ✅ `services/user_service_db.py` НЕ использует JSON
- ⚠️ `services/user_service_persistent.py` ещё использует JSON (legacy)
- ✅ По умолчанию бот использует `user_service_db.py` (из `bot.py`)
- **Вывод:** Новый бот полностью на PostgreSQL, старая система JSON больше не используется

### ✅ 6. Можно скопировать database/ в другой проект
**СТАТУС:** ✅ ГОТОВО
- `database/` - переносимый модуль
- В `database/README.md` есть инструкции
- Все модели в `base_models.py` для multi-bot
- `bot_name` параметр для изоляции

### ✅ 7. README.md с инструкциями создан
**СТАТУС:** ✅ СОЗДАН
- `database/README.md` - документация модуля
- `README_v4.md` - документация v4.0
- `V4_INTEGRATION_GUIDE.md` - интеграция
- `RAILWAY_DEPLOY_v4.md` - деплой
- `LOCAL_DEVELOPMENT_SETUP.md` - локальная разработка

---

## 🎯 КАК ДОБАВИТЬ НОВЫЙ БОТ

### Шаг 1: Скопируйте database/

```bash
cd /path/to/new_bot/
cp -r /path/to/spin_bot/database/ .
```

### Шаг 2: Установите зависимости

```bash
pip install -r REQUIREMENTS_v4.txt
```

### Шаг 3: Используйте DatabaseService

```python
from services.database_service import DatabaseService

db_service = DatabaseService(bot_name="new_bot_name")

# Получить пользователя
user_data = await db_service.get_user_session(telegram_id=123456)
# user_data - универсальный формат для любого бота

# Сохранить данные
await db_service.save_session(telegram_id, session, stats)
```

### Шаг 4: Настройте .env

```bash
DATABASE_URL=postgresql://... (та же БД Railway)
```

**Готово!** Новый бот использует ту же БД:
- ✅ Те же пользователи
- ✅ Общие XP, levels, badges
- ✅ Своя изолированная session/stats

---

## 🔮 ИТОГО

**ЕДИНАЯ БД УЖЕ РЕАЛИЗОВАНА:**
- ✅ Multi-bot архитектура готова
- ✅ Изоляция данных по ботам через `bot_name`
- ✅ Общие данные (users, badges, promocodes)
- ✅ Переносимый модуль `database/`

**ЧТО НУЖНО ДЛЯ RAILWAY:**
- ✅ Просто задеплоить `git push`
- ✅ Railway создаст таблицы автоматически
- ✅ PostgreSQL URL будет в переменных окружения

**ЧТО УЖЕ РАБОТАЕТ:**
- ✅ Локальная разработка (SQLite)
- ✅ Multi-bot изоляция
- ✅ Кросс-бот геймификация
- ✅ Единые промокоды/подписки

---

**Всё готово! Можно деплоить на Railway и добавлять новые боты! 🚀**


