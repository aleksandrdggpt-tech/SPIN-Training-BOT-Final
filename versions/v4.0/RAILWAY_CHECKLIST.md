# ✅ Чеклист настройки Railway для v4.0

## 🔍 Проверка перед деплоем

### 1. Файлы в репозитории
- [ ] `versions/v4.0/bot.py` - существует
- [ ] `versions/v4.0/requirements.txt` - существует
- [ ] `versions/v4.0/Procfile` - существует
- [ ] `versions/v4.0/railway.json` - существует (опционально)
- [ ] `versions/v4.0/nixpacks.toml` - существует (опционально)

### 2. Настройки Railway → Source
- [ ] **Repository:** `aleksandrdggpt-tech/SPIN-Training-BOT-Final`
- [ ] **Branch:** `v4.0` ✅
- [ ] **Root Directory:** `versions/v4.0` ✅

### 3. Настройки Railway → Build & Deploy
- [ ] **Root Directory:** `versions/v4.0` ✅
- [ ] **Start Command:** `python bot.py` (или пусто, если используется Procfile)

### 4. Variables (обязательные)
- [ ] `DATABASE_URL=${{Postgres.DATABASE_URL}}` или значение из Postgres
- [ ] `DEV_MODE=0` (ВАЖНО! Не `1`)
- [ ] `BOT_TOKEN=ваш_токен`
- [ ] `OPENAI_API_KEY=ваш_ключ`
- [ ] `ANTHROPIC_API_KEY=ваш_ключ`

### 5. Variables (опциональные)
- [ ] `BOT_NAME=spin_bot`
- [ ] `PORT=8080`
- [ ] `SCENARIO_PATH=scenarios/spin_sales/config.json`
- [ ] `DB_POOL_SIZE=5`
- [ ] `DB_MAX_OVERFLOW=0`
- [ ] `WRITE_PID_FILE=0`
- [ ] `ADMIN_USER_IDS=759603598`

## 🚨 Частые ошибки

### Ошибка: "No build plan found"
**Решение:** Убедитесь, что `requirements.txt` в `versions/v4.0/`

### Ошибка: "Cannot find bot.py"
**Решение:** Проверьте **Root Directory**: `versions/v4.0`

### Ошибка: "DATABASE_URL is not set"
**Решение:** Добавьте `DATABASE_URL` в Variables

### Ошибка: "ModuleNotFoundError"
**Решение:** Проверьте, что все зависимости в `requirements.txt`

## 📝 Правильная структура

```
versions/v4.0/
├── bot.py              ✅ Главный файл
├── requirements.txt     ✅ Зависимости
├── Procfile            ✅ Команда запуска
├── railway.json        ✅ Конфигурация Railway
├── nixpacks.toml       ✅ Конфигурация сборки
├── database/           ✅ Модели БД
├── services/           ✅ Сервисы
├── modules/            ✅ Модули
└── ...
```

## 🎯 После настройки

1. Нажмите **"Deploy"** в Railway
2. Проверьте логи в **Deployments** → **View logs**
3. Ищите сообщения:
   - ✅ `Database engine created: postgresql+asyncpg://...`
   - ✅ `Database initialized successfully`
   - ✅ `Application started`

