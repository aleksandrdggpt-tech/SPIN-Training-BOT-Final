# 🚀 Деплой v4.0 на GitHub

## 📋 Подготовка к деплою

### 1. Проверка .gitignore
Убедитесь, что `.env` файлы не попадут в git:
```bash
# Проверка
grep "\.env" .gitignore

# Должно быть:
.env
.env.*
```

### 2. Проверка изменений
```bash
cd /Users/aleksandrdg/Projects/SPIN\ Training\ BOT\ Final
git status
```

### 3. Создание ветки для v4.0 (опционально)
Если хотите отдельную ветку:
```bash
git checkout -b v4.0
# или
git checkout -b release/v4.0
```

## 📦 Что включить в коммит

### ✅ Включить:
- Все файлы из `versions/v4.0/` (кроме .env)
- Обновленный `.gitignore` (если нужно)
- Документацию (README.md, RAILWAY_DEPLOYMENT.md и т.д.)
- Procfile для Railway
- requirements.txt

### ❌ НЕ включать:
- `.env` файлы
- `*.db` файлы (SQLite базы данных)
- `__pycache__/` директории
- `venv/` или `.venv/` директории
- `*.pyc` файлы

## 🔧 Команды для деплоя

### Вариант 1: Деплой всей папки versions/v4.0
```bash
cd /Users/aleksandrdg/Projects/SPIN\ Training\ BOT\ Final

# Проверка статуса
git status

# Добавление файлов v4.0
git add versions/v4.0/

# Проверка, что .env не добавлен
git status | grep -i "\.env" && echo "⚠️  ВНИМАНИЕ: .env файл добавлен!" || echo "✅ .env не добавлен"

# Коммит
git commit -m "feat: Add v4.0 version with Railway deployment support

- PostgreSQL/asyncpg support with SSL
- Optional SQLite for local development (DEV_MODE=1)
- Railway deployment configuration
- PEP8 formatted code
- All statistics functionality
- Free access flow (no payments in v4.0)"

# Пуш в текущую ветку
git push origin <branch-name>

# Или создать новую ветку
git push origin v4.0
```

### Вариант 2: Создание тега для релиза
```bash
# После коммита
git tag -a v4.0.0 -m "Release v4.0.0 - Railway ready version"
git push origin v4.0.0
```

## 🚨 Важные проверки перед пушем

### 1. Проверка .env файлов
```bash
# Убедитесь, что .env не попадет в git
git status | grep "\.env"
# Должно быть пусто

# Или явно исключить
git reset HEAD versions/v4.0/.env 2>/dev/null || true
```

### 2. Проверка секретов
```bash
# Проверка на случайные токены в коде
grep -r "BOT_TOKEN=" versions/v4.0/ --exclude-dir=__pycache__ | grep -v ".env" | grep -v ".gitignore"
# Должно быть пусто (токены только в .env)
```

### 3. Проверка размера файлов
```bash
# Проверка больших файлов
find versions/v4.0 -type f -size +1M ! -path "*/venv/*" ! -path "*/__pycache__/*"
```

## 📝 Создание .env.example

Создайте файл `.env.example` для других разработчиков:
```bash
cd versions/v4.0
cat > .env.example << 'EOF'
# Development mode (uses SQLite instead of PostgreSQL)
DEV_MODE=1

# Telegram Bot Token (получите у @BotFather в Telegram)
BOT_TOKEN=your_bot_token_here

# LLM Providers
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Admin Configuration
ADMIN_USER_IDS=your_telegram_id_here

# Bot Name
BOT_NAME=spin_bot

# Application Settings
PORT=8080
SCENARIO_PATH=scenarios/spin_sales/config.json

# LLM Settings
LLM_TIMEOUT_SEC=30.0
LLM_MAX_RETRIES=1
RESPONSE_PROVIDER=anthropic
FEEDBACK_PROVIDER=anthropic
CLASSIFICATION_PROVIDER=openai

# Database Pool Configuration
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=0

# PID File
WRITE_PID_FILE=0
EOF
```

## 🔗 После деплоя на GitHub

### Для Railway деплоя:
1. Подключите GitHub репозиторий к Railway
2. Railway автоматически найдет `Procfile` в `versions/v4.0/`
3. Установите переменные окружения в Railway Dashboard:
   - `BOT_TOKEN`
   - `DATABASE_URL` (автоматически создается при добавлении PostgreSQL)
   - `DEV_MODE=0` (для production)
   - Остальные переменные по необходимости

### Для локального клонирования:
```bash
git clone <repository-url>
cd "SPIN Training BOT Final/versions/v4.0"
cp .env.example .env
# Отредактируйте .env с вашими ключами
python bot.py
```

## ✅ Чеклист перед пушем

- [ ] `.env` файл НЕ добавлен в git
- [ ] `.gitignore` содержит `.env` и `*.db`
- [ ] Все токены удалены из кода (только в .env)
- [ ] Создан `.env.example` файл
- [ ] Код отформатирован (PEP8)
- [ ] Все файлы компилируются без ошибок
- [ ] Документация обновлена
- [ ] `Procfile` создан для Railway
- [ ] `requirements.txt` актуален

