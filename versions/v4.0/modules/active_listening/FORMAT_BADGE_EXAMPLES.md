# 👂 format_badge() — Примеры использования

## Новый метод для явного отображения активного слушания

Метод `format_badge()` возвращает **полный бейдж** с текстом вместо просто emoji.

---

## До и После

### ❌ Было (только emoji):

```python
context_badge = " 👂"
result = f"Ситуационный вопрос{context_badge}"
# Output: "Ситуационный вопрос 👂"
```

**Проблема:** Не очевидно, что это означает активное слушание.

---

### ✅ Стало (emoji + текст):

```python
context_badge = active_listening_detector.format_badge()
result = f"Ситуационный вопрос{context_badge}"
# Output: "Ситуационный вопрос 👂 (Успешное активное слушание)"
```

**Преимущество:** Сразу понятно, что пользователь использовал активное слушание!

---

## Примеры вывода

### Без активного слушания:

```
📝 Тип вопроса: Ситуационный вопрос

💬 Ответ клиента:
У нас компания на 50 человек.
```

### С активным слушанием:

```
📝 Тип вопроса: Проблемный вопрос 👂 (Успешное активное слушание)

💬 Ответ клиента:
Из этих 50 человек примерно 15 работают в продажах.
```

---

## Код для интеграции

### Вариант 1: В training_service.py

```python
from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Инициализация (один раз)
active_listening = ActiveListeningDetector(
    ActiveListeningConfig(enabled=True, use_llm=True)
)

# В обработчике вопроса
async def process_question(self, user_id, question):
    session = self.get_session(user_id)

    # Проверка активного слушания
    is_contextual = await active_listening.check_context_usage(
        question=question,
        last_response=session.get('last_client_response', ''),
        call_llm_func=self.llm_service.call_llm
    )

    # ✅ НОВЫЙ КОД: Форматирование бейджа
    context_badge = ""
    if is_contextual:
        session['contextual_questions'] += 1
        session['score'] += active_listening.get_bonus_points()
        context_badge = active_listening.format_badge()
        # Returns: " 👂 (Успешное активное слушание)"

    # Отображение
    question_type_name = "Ситуационный вопрос"
    feedback = f"Тип вопроса: {question_type_name}{context_badge}"

    return feedback
```

### Вариант 2: Замена существующего кода

**Найти в коде:**
```python
context_badge = " 👂"
```

**Заменить на:**
```python
context_badge = active_listening.format_badge()
```

---

## На разных языках

### Русский (по умолчанию):
```python
config = ActiveListeningConfig(language="ru")
detector = ActiveListeningDetector(config)

badge = detector.format_badge()
# Returns: " 👂 (Успешное активное слушание)"
```

### English:
```python
config = ActiveListeningConfig(language="en")
detector = ActiveListeningDetector(config)

badge = detector.format_badge()
# Returns: " 👂 (Successful active listening)"
```

---

## Кастомизация

### Изменить emoji:
```python
config = ActiveListeningConfig(emoji="🎧")
detector = ActiveListeningDetector(config)

badge = detector.format_badge()
# Returns: " 🎧 (Успешное активное слушание)"
```

### Без текста (только emoji):
Если нужен старый вариант (только emoji), не используйте `format_badge()`:

```python
if is_contextual:
    context_badge = f" {detector.config.emoji}"
    # Returns: " 👂"
```

Но **рекомендуется использовать полный бейдж** для ясности!

---

## Полный пример

```python
from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Setup
config = ActiveListeningConfig(
    enabled=True,
    use_llm=True,
    bonus_points=5,
    emoji="👂",
    language="ru"
)
detector = ActiveListeningDetector(config)

# Usage
async def show_feedback(question, last_response, question_type):
    # Check
    is_contextual = await detector.check_context_usage(
        question=question,
        last_response=last_response
    )

    # Format
    badge = ""
    if is_contextual:
        badge = detector.format_badge()

    # Display
    print(f"Тип вопроса: {question_type}{badge}")

# Examples
await show_feedback(
    question="Сколько у вас сотрудников?",
    last_response="Мы большая компания.",
    question_type="Ситуационный"
)
# Output: "Тип вопроса: Ситуационный"

await show_feedback(
    question="Вы сказали 50 сотрудников. Сколько в продажах?",
    last_response="У нас 50 человек.",
    question_type="Ситуационный"
)
# Output: "Тип вопроса: Ситуационный 👂 (Успешное активное слушание)"
```

---

## Сравнение вариантов

| Вариант | Код | Результат | Ясность |
|---------|-----|-----------|---------|
| **Старый** | `" 👂"` | "Ситуационный 👂" | ⚠️ Не очень |
| **Новый** | `format_badge()` | "Ситуационный 👂 (Успешное активное слушание)" | ✅ Отлично |

---

## Отключение

Если активное слушание не нужно:

```python
config = ActiveListeningConfig(enabled=False)
detector = ActiveListeningDetector(config)

# check_context_usage() всегда вернет False
# format_badge() вернет пустую строку ""
```

---

## Заключение

✅ **Используйте `format_badge()`** для явного отображения активного слушания
✅ **Более понятно** для пользователей
✅ **Легко интегрировать** — одна строка кода

См. также:
- `INTEGRATION_EXAMPLE.py` — полные примеры кода
- `README.md` — полная документация модуля
