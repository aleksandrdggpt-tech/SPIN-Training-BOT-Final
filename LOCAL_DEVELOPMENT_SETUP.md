# ✅ Локальная разработка с SQLite

## 📝 Настройка .env

### Откройте файл `.env` и установите:

```bash
DATABASE_URL=sqlite+aiosqlite:///./spin_bot.db
```

**Вот и всё!** Больше ничего не нужно менять.

---

## 🚀 Запуск

```bash
python bot.py
```

**Ожидаемый вывод:**
```
🔄 Initializing database...
✅ Database initialized successfully
✅ База данных инициализирована
✅ Бот успешно запущен!
```

---

## 📊 Как это работает

### Локальная разработка:
- **База:** SQLite (`spin_bot.db`)
- **Расположение:** В корне проекта
- **Скорость:** Очень быстро
- **Нет конфликтов:** С event loops

### Production (Railway):
- **База:** PostgreSQL Railway
- **Подключение:** Автоматически через `DATABASE_URL`
- **Данные:** Работает с реальными пользователями

---

## ⚠️ Важно

**Не добавляйте PostgreSQL URL в локальный .env!**

```bash
# ❌ НЕ ДЕЛАЙТЕ ТАК:
# DATABASE_URL=postgresql://postgres:pass@railway...

# ✅ ДЕЛАЙТЕ ТАК:
DATABASE_URL=sqlite+aiosqlite:///./spin_bot.db
```

Причина: PostgreSQL локально вызывает конфликты event loops.

---

## ✅ Готово!

После установки `DATABASE_URL` в `.env`:
1. Запустите: `python bot.py`
2. Протестируйте бота
3. Всё работает без ошибок!

**На Railway при деплое:**
- Railway автоматически подставит PostgreSQL URL
- Бот будет работать с PostgreSQL
- Никаких изменений в коде не требуется


