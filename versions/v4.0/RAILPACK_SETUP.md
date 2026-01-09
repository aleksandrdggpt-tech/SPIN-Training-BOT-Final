# 🚂 Настройка с Railpack Builder

## ✅ Builder изменен на RAILPACK

Railway теперь будет использовать **RAILPACK** вместо NIXPACKS для сборки проекта.

## 📋 Настройки в Railway

### 1. Settings → Build & Deploy
- **Builder:** `RAILPACK` (автоматически определяется из `railway.json`)
- **Root Directory:** `versions/v4.0`
- **Start Command:** оставьте пустым (используется `Procfile`)

### 2. Settings → Source
- **Branch:** `v4.0`
- **Root Directory:** `versions/v4.0`

### 3. Variables
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
DEV_MODE=0
BOT_TOKEN=ваш_токен
OPENAI_API_KEY=ваш_ключ
ANTHROPIC_API_KEY=ваш_ключ
```

## 🔍 Как Railpack работает

Railpack автоматически:
- Определяет Python проект по наличию `requirements.txt`
- Устанавливает зависимости из `requirements.txt`
- Использует `Procfile` для команды запуска
- Или команду из `railway.json` → `deploy.startCommand`

## ✅ Файлы для Railpack

Все необходимые файлы на месте:
- ✅ `requirements.txt` - зависимости
- ✅ `Procfile` - команда запуска (`worker: python bot.py`)
- ✅ `railway.json` - конфигурация (builder: RAILPACK)
- ✅ `bot.py` - главный файл

## 🚀 После обновления

1. Railway автоматически перезапустит деплой
2. Или нажмите **"Deploy"** вручную
3. Проверьте логи в **Deployments** → **View logs**

## 📝 Проверка логов

После деплоя ищите в логах:
- ✅ `Installing dependencies from requirements.txt`
- ✅ `Database engine created: postgresql+asyncpg://...`
- ✅ `Application started`

