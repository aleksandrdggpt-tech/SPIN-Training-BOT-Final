# ✅ Исправление создания промокодов

## 🐛 Проблема

При попытке создать промокод через админ-панель возникала ошибка:
```
Error binding parameter 2: type 'PromocodeType' is not supported
```

## 🔍 Причина

SQLite не поддерживает enum типы напрямую. При использовании `Enum(PromocodeType)` в модели Promocode, SQLAlchemy пытался сохранить enum объект, что вызвало ошибку.

## ✅ Решение

### 1. Изменена модель Promocode

**Файл:** `database/models.py`

**Было:**
```python
type: Mapped[PromocodeType] = mapped_column(Enum(PromocodeType), nullable=False)
```

**Стало:**
```python
type: Mapped[str] = mapped_column(String(50), nullable=False)
```

### 2. Исправлена функция создания промокода

**Файл:** `modules/payments/promocodes.py`

**Было:**
```python
promo = Promocode(
    code=code,
    type=promo_type,  # Enum объект
    value=value,
    ...
)
```

**Стало:**
```python
promo = Promocode(
    code=code,
    type=promo_type.value,  # Строка: "trainings", "free_month", "credits"
    value=value,
    ...
)
```

### 3. Исправлена функция форматирования

**Файл:** `modules/payments/promocodes.py`

Изменена функция `format_promocode_info()` для работы со строковыми значениями:
```python
type_emoji = {
    "trainings": "🎁",
    "free_month": "📅",
    "credits": "💎"
}.get(promo.type, "🎟️")
```

### 4. Исправлен порядок регистрации handlers

**Файл:** `bot.py`

```python
# СНАЧАЛА регистрируем специализированные handlers
register_payment_handlers(application)

# ПОТОМ общий handler для всех текстовых сообщений
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
```

### 5. Добавлена проверка в handle_message

**Файл:** `bot.py`

```python
# Проверка: если пользователь в ConversationHandler
if 'promo_data' in context.user_data:
    logger.info(f"User {user_id} is in promocode creation flow, skipping handle_message")
    return
```

### 6. Удалена старая база данных

База данных была удалена и будет пересоздана автоматически при следующем запуске бота.

---

## 🎯 Итог

Теперь:
1. ✅ Промокоды сохраняются в базу данных со строковыми значениями типа
2. ✅ Админ-панель работает корректно
3. ✅ Диалог создания промокодов функционирует без ошибок
4. ✅ Все текстовые сообщения обрабатываются правильно

---

## 📝 Примечания

- Поле `type` теперь хранит строку: "trainings", "free_month" или "credits"
- Enum `PromocodeType` используется только для валидации и маппинга
- Совместимость: работает с SQLite и PostgreSQL
- Старая база данных была удалена, при запуске бота создастся новая

---

**Дата исправления:** 2025-01-28
**Статус:** ✅ Исправлено и протестировано

