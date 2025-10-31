# 🚀 Деплой v4.0 на Railway

## ✅ Готово к деплою!

**НЕ НУЖНО ПЕРЕДЕЛЫВАТЬ БОТА!** v4.0 уже настроен для Railway.

---

## 📝 Что изменилось

### 1. `railway.json` обновлен:
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile",
    "buildContext": "."
  }
}
```
- Теперь использует корневую директорию вместо `versions/v3.0`
- Деплоит **v4.0** вместо v3.0

### 2. `REQUIREMENTS.txt` обновлен:
- Добавлены все зависимости v4.0
- Включены `asyncpg`, `nest_asyncio`, `anthropic`

### 3. `Dockerfile` уже готов:
- Базовый образ: `python:3.11-slim`
- Все зависимости устанавливаются
- Health check порт: 8080

---

## 🚀 Инструкция по деплою

### Шаг 1: Push в GitHub

```bash
git add .
git commit -m "v4.0: Ready for Railway deployment"
git push origin main
```

### Шаг 2: Railway автоматически:

1. **Определит изменения** в `railway.json`
2. **Соберёт Docker образ** из корневой директории
3. **Подключится к PostgreSQL** (автоматически через `DATABASE_URL`)
4. **Установит все зависимости** из `REQUIREMENTS.txt`
5. **Запустит бота** командой `python bot.py`

### Шаг 3: Проверка

**Railway автоматически:**
- ✅ Создаст таблицы базы данных
- ✅ Инициализирует подключение к PostgreSQL
- ✅ Запустит health check на порту 8080
- ✅ Бот начнёт принимать сообщения

---

## ⚙️ Переменные окружения

Railway НЕ нужно настраивать ничего дополнительно! Все переменные уже настроены:

- `DATABASE_URL` - автоматически от Railway PostgreSQL
- `BOT_TOKEN` - уже установлен от v3.0
- `OPENAI_API_KEY` - уже установлен
- `ANTHROPIC_API_KEY` - уже установлен
- `PORT`=8080 - для health check

---

## 🔄 Миграция данных

### ВАЖНО: v4.0 создаст НОВЫЕ таблицы!

**Если на Railway уже работает v3.0:**
- v3.0 использует таблицы из `versions/v3.0/`
- v4.0 создаст новые таблицы в той же базе
- Пользователи v3.0 сохранятся, но данные НЕ перенесутся автоматически

**Опция 1:** Деплой v4.0 на новый проект Railway  
**Опция 2:** Использовать одну базу (данные будут разделены)

---

## 📊 Проверка деплоя

### 1. Health Check:
```
https://ваш-проект.railway.app/health
```

**Ожидаемый ответ:**
```json
{"status": "ok", "service": "spin_bot_v4"}
```

### 2. Логи Railway:
```bash
# Смотрим логи
railway logs
```

**Ожидаемый вывод:**
```
✅ Database initialized successfully
✅ Бот успешно запущен!
Application started
```

### 3. Тестируем бота:
Отправьте `/start` боту в Telegram.

---

## 🎯 Что произойдёт

### При первом запуске:

1. **Инициализация БД:**
```
🔄 Initializing database...
✅ Database initialized successfully
```

2. **Создание таблиц v4.0:**
- `users` - пользователи
- `sessions` - сессии бота
- `badges` - бейджи
- `badge_user_association` - связи
- `training_history` - история тренировок
- `subscriptions` - подписки
- `payments` - платежи
- И т.д.

3. **Запуск бота:**
- Health check: порт 8080
- Telegram updates: API polling
- Бот готов принимать команды

---

## 🔧 Если что-то пошло не так

### Ошибка: Event loop conflict

**Решение:** Уже исправлено через `nest_asyncio`!

### Ошибка: PostgreSQL connection failed

**Проверьте:**
1. PostgreSQL сервис подключен к проекту
2. `DATABASE_URL` установлен в переменных Railway

### Ошибка: Module not found

**Решение:** Все зависимости в `REQUIREMENTS.txt` - Railway установит автоматически

---

## ✅ Итог

**НЕ НУЖНО ПЕРЕДЕЛЫВАТЬ БОТА!**

Просто:
1. ✅ `railway.json` обновлён
2. ✅ `REQUIREMENTS.txt` обновлён
3. ✅ `Dockerfile` готов
4. ✅ Код готов

Команда:
```bash
git push origin main
```

Railway сделает всё остальное автоматически! 🚀


