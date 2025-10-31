# 🔌 Подключение к PostgreSQL на Railway

## Текущая ситуация

**Локальная версия (v4.0):**
- Использует SQLite: `DATABASE_URL=sqlite+aiosqlite:///./spin_bot_test.db`
- База данных локальная
- Данные не синхронизируются с Railway

**Railway (v3.0 в production):**
- Имеет PostgreSQL базу данных
- Нужно узнать DATABASE_URL от Railway
- Затем обновить .env

---

## Как подключить PostgreSQL на Railway

### 1. Получить DATABASE_URL с Railway

**Вариант А: Через Railway Dashboard**
1. Откройте https://railway.app
2. Войдите в проект
3. Перейдите в раздел "Variables"
4. Найдите переменную `DATABASE_URL` или `POSTGRES_URL`
5. Скопируйте значение

**Вариант Б: Через Railway CLI**
```bash
# Установить Railway CLI
npm i -g @railway/cli

# Войти
railway login

# Получить DATABASE_URL
railway variables
```

---

### 2. Обновить .env файл

Скопируйте полученный URL PostgreSQL и вставьте в `.env`:

```bash
# Замените текущую строку
DATABASE_URL=sqlite+aiosqlite:///./spin_bot_test.db

# На PostgreSQL URL от Railway
DATABASE_URL=postgresql://user:password@host:port/dbname
# Или
DATABASE_URL=${{ DATABASE_URL }}  # если Railway автоматически добавляет
```

**Формат Railway:**
```
postgres://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

**Это нужно преобразовать в:**
```
postgresql+asyncpg://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

**Или код сам преобразует** (строки 28-31 в `database/database.py`):
```python
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)
```

---

### 3. Установить asyncpg для PostgreSQL

```bash
pip install asyncpg
```

Проверьте, что установлен:
```bash
pip list | grep asyncpg
```

---

### 4. Проверить подключение

После обновления DATABASE_URL запустите бота:

```bash
python bot.py
```

**Ожидаемый вывод:**
```
🔄 Initializing database...
✅ Database initialized successfully
```

Если ошибка подключения - проверьте:
- Правильность DATABASE_URL
- Доступность хоста Railway
- Правильность пароля

---

## 🔄 Синхронизация данных

### Локальная разработка
- Использует SQLite
- База: `spin_bot_test.db`
- Данные локальные

### Production (Railway)
- Использует PostgreSQL
- База данных Railway
- Данные общие для всех пользователей

### Важно:
- **Локальная и Railway БД НЕ синхронизируются автоматически!**
- Это разные базы данных
- Для production используйте Railway PostgreSQL
- Для разработки можно использовать локальный SQLite

---

## 🚀 Деплой на Railway с PostgreSQL

Если деплоите v4.0 на Railway:

1. **Обновите variables в Railway:**
   ```
   DATABASE_URL=postgresql://... (уже есть от Railway)
   BOT_TOKEN=ваш_токен
   OPENAI_API_KEY=ваш_ключ
   ```

2. **Push изменений:**
   ```bash
   git push origin main
   ```

3. **Railway автоматически:**
   - Подхватит изменения
   - Использует PostgreSQL из variables
   - Создаст таблицы автоматически при первом запуске

---

## 📝 Текущий статус

**Локально (v4.0):**
- ✅ Бот работает
- ✅ SQLite подключен
- ✅ Все функции работают
- 📦 База: `spin_bot_test.db`

**На Railway (v3.0):**
- ✅ Бот работает
- ✅ PostgreSQL подключен
- 📦 База данных Railway

**Нужно сделать для синхронизации v4.0 → Railway:**
1. Получить DATABASE_URL с Railway
2. Обновить .env
3. Задеплоить v4.0 на Railway

---

## ⚠️ Важные замечания

1. **Не забудьте сделать backup** локальной БД перед переключением
2. **Railway PostgreSQL** автоматически делает бэкапы
3. **Миграция данных** v3→v4 может потребоваться при обновлении
4. **Тестирование** лучше делать на локальной БД

---

## 🎯 Рекомендации

### Для разработки:
- Используйте SQLite локально
- Быстро, удобно, не требует network
- Легко сбросить БД для тестов

### Для production:
- Используйте PostgreSQL на Railway
- Надежность, автоматические бэкапы
- Масштабируемость

---

**Теперь вы знаете как настроить PostgreSQL на Railway для бота!**

