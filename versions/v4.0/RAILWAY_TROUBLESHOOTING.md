# 🔧 Решение проблем с деплоем v4.0 на Railway

## ❌ Частые проблемы и решения

### Проблема 1: "No build plan found" или "Cannot detect build"

**Решение:**
1. Убедитесь, что `requirements.txt` находится в `versions/v4.0/`
2. Проверьте, что `Procfile` находится в `versions/v4.0/`
3. В Railway: **Settings** → **Build & Deploy** → **Root Directory**: `versions/v4.0`

### Проблема 2: "Module not found" или ошибки импорта

**Решение:**
1. Проверьте, что все зависимости в `requirements.txt`
2. Убедитесь, что `Root Directory` установлен правильно: `versions/v4.0`
3. Railway должен запускать команды из `versions/v4.0/`, а не из корня

### Проблема 3: "DATABASE_URL not found"

**Решение:**
1. В Railway: **Variables** → добавьте `DATABASE_URL`
2. Используйте: `${{Postgres.DATABASE_URL}}` (автоматическое подключение)
3. Или скопируйте значение из сервиса Postgres
4. Убедитесь, что `DEV_MODE=0` установлен

### Проблема 4: "Cannot find bot.py"

**Решение:**
1. Проверьте **Root Directory**: должен быть `versions/v4.0`
2. Проверьте, что файл `bot.py` находится в `versions/v4.0/bot.py`
3. В **Settings** → **Build & Deploy** → **Start Command**: `python bot.py`

### Проблема 5: Деплой запускается, но падает

**Проверьте логи:**
1. Откройте **Deployments** → выберите деплой → **View logs**
2. Ищите ошибки:
   - `DATABASE_URL is not set` → добавьте переменную
   - `ModuleNotFoundError` → проверьте `requirements.txt`
   - `SyntaxError` → проверьте код

## ✅ Правильная настройка в Railway

### 1. Settings → Source
```
Repository: aleksandrdggpt-tech/SPIN-Training-BOT-Final
Branch: v4.0
Root Directory: versions/v4.0
```

### 2. Settings → Build & Deploy
```
Root Directory: versions/v4.0
Start Command: python bot.py
(или оставьте пустым, если используется Procfile)
```

### 3. Variables (обязательные)
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
DEV_MODE=0
BOT_TOKEN=ваш_токен
OPENAI_API_KEY=ваш_ключ
ANTHROPIC_API_KEY=ваш_ключ
```

## 📋 Чеклист файлов для деплоя

Убедитесь, что в `versions/v4.0/` есть:
- [ ] `bot.py` - главный файл
- [ ] `requirements.txt` - зависимости
- [ ] `Procfile` - команда запуска
- [ ] `railway.json` - конфигурация Railway (опционально)
- [ ] `nixpacks.toml` - конфигурация сборки (опционально)

## 🔍 Проверка перед деплоем

```bash
cd versions/v4.0

# 1. Проверка файлов
ls -la bot.py requirements.txt Procfile

# 2. Проверка синтаксиса
python3 -m py_compile bot.py

# 3. Проверка зависимостей
cat requirements.txt | head -10
```

## 🚀 Альтернативный способ: Dockerfile

Если Nixpacks не работает, можно создать Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

## 📝 Логи для диагностики

Если деплой не работает, проверьте логи:
1. **Deployments** → выберите деплой
2. **View logs** → ищите ошибки
3. Типичные ошибки:
   - `FileNotFoundError: bot.py` → неправильный Root Directory
   - `ModuleNotFoundError` → отсутствует зависимость в requirements.txt
   - `DATABASE_URL is not set` → не добавлена переменная

