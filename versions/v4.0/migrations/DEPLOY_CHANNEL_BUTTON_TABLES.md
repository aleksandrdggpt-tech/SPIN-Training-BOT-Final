# Миграция: Создание таблиц для отслеживания кнопок канала

## Проблема
Таблицы `channel_buttons` и `channel_button_clicks` не существуют в базе данных, что вызывает ошибку:
```
relation "channel_button_clicks" does not exist
```

## Решение

### Вариант 1: Автоматическое создание (рекомендуется)
После деплоя обновленного кода, таблицы будут созданы автоматически при следующем запуске бота через `init_db()`.

**Что было исправлено:**
1. `models.py` теперь использует `Base` из `base_models.py` (все модели в одной метаданной)
2. `init_db()` теперь явно импортирует все модели перед созданием таблиц

### Вариант 2: Ручное создание через SQL
Если нужно создать таблицы вручную, выполните SQL скрипт:

```bash
# Подключитесь к базе данных Railway
railway connect postgres

# Выполните миграцию
\i migrations/create_channel_button_tables.sql
```

Или через psql напрямую:
```bash
railway connect postgres < migrations/create_channel_button_tables.sql
```

## SQL скрипт
Скрипт находится в: `versions/v4.0/migrations/create_channel_button_tables.sql`

Он создает:
- Таблицу `channel_buttons` с индексами
- Таблицу `channel_button_clicks` с индексами и внешними ключами

## Проверка
После применения миграции, проверьте что таблицы созданы:

```sql
-- Проверка таблиц
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('channel_buttons', 'channel_button_clicks');

-- Должно вернуть:
-- channel_buttons
-- channel_button_clicks
```

## После миграции
После создания таблиц, функционал отслеживания кнопок канала будет работать корректно:
- ✅ `/add_button` - добавление кнопки в пост
- ✅ Статистика по кнопкам в админ-панели
- ✅ Отслеживание кликов по кнопкам
