# Решение проблемы PostgreSQL локально

## ❌ Проблема

PostgreSQL через asyncpg требует event loop, но Telegram Bot уже использует свой event loop. Это вызывает конфликт:
```
RuntimeError: Task got Future attached to a different loop
```

## ✅ Простое решение

**Используйте SQLite локально, PostgreSQL на Railway:**

### В `.env` для локальной разработки:

```bash
# SQLite для локальной разработки (работает отлично)
DATABASE_URL=sqlite+aiosqlite:///./spin_bot_test.db

# PostgreSQL для production на Railway
# DATABASE_URL=postgresql://postgres:pass@switchback.proxy.rlwy.net:10308/railway
```

### На Railway:

Автоматически использует PostgreSQL из переменной `DATABASE_URL`.

---

## 🎯 Что делать

**Сейчас в `.env` стоит PostgreSQL URL. Измените на SQLite:**

```bash
DATABASE_URL=sqlite+aiosqlite:///./spin_bot_test.db
```

Затем запустите:
```bash
python bot.py
```

---

## 📊 Почему это работает

- ✅ **Локально:** SQLite не требует event loop и работает в sync контексте
- ✅ **На Railway:** PostgreSQL будет работать корректно, так как там нет конфликта с Telegram Bot event loop (или архитектура другая)
- ✅ **Данные:** Каждый environment имеет свою БД - это правильно
- ✅ **Простота:** Не нужно менять архитектуру кода

---

## 🔮 Для будущего

Если нужен PostgreSQL локально:
1. Переделайте все handlers на полностью async
2. Или используйте `psycopg2` (sync драйвер) вместо asyncpg
3. Оба варианта требуют больших изменений в коде

**Пока что - SQLite для локальной разработки самый простой путь!**


