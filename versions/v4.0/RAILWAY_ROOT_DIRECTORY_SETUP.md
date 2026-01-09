# 🔧 Настройка Root Directory в Railway

## Проблема
Railway не может найти корневую директорию `/versions/v4.0` при деплое.

## Решение

### Вариант 1: Настроить Root Directory в Railway Dashboard (РЕКОМЕНДУЕТСЯ)

1. Откройте https://railway.app
2. Выберите проект **"peaceful-dedication"**
3. Выберите сервис **"SPIN-Training-BOT-Final"**
4. Перейдите в **Settings** → **Build & Deploy**
5. Найдите раздел **"Root Directory"**
6. Установите значение: `versions/v4.0` (относительно корня репозитория)
7. Сохраните изменения
8. Railway автоматически перезапустит деплой

### Вариант 2: Использовать railway.json (если поддерживается)

Если Railway поддерживает `rootDirectory` в `railway.json`, можно добавить:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "rootDirectory": "versions/v4.0",
  "build": {
    "builder": "RAILPACK"
  },
  "deploy": {
    "startCommand": "python bot.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Но лучше использовать Dashboard, так как это более надежно.

### Вариант 3: Деплой из корня репозитория

Если настройка Root Directory не работает, можно:
1. Скопировать все файлы из `versions/v4.0` в корень репозитория
2. Или настроить Railway на деплой из корня и указать правильный путь к `bot.py`

## Проверка

После настройки Root Directory:
1. Railway должен найти файлы в `versions/v4.0/`
2. Деплой должен пройти успешно
3. В логах должно появиться: "Using custom creator function to filter sslmode"

## Текущий статус

- ✅ Исправлен `database.py` с функцией creator
- ✅ Убран `rootDirectory` из `railway.json` (настраивается в Dashboard)
- ⏳ Ожидается настройка Root Directory в Railway Dashboard

