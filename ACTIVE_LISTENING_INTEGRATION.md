# 👂 Active Listening Module — Integration Guide

## ✅ Создан переносимый модуль активного слушания

Модуль вынесен из основного кода и может быть легко подключен или отключен в любом боте.

---

## 📦 Что создано

```
modules/active_listening/
├── __init__.py              # Экспорты модуля
├── config.py                # Конфигурация
├── detector.py              # Логика детекции
├── README.md                # Полная документация
└── test_active_listening.py # Тесты
```

---

## 🚀 Быстрая интеграция в SPIN Bot

### Шаг 1: Инициализация (в bot.py или main)

```python
from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Создать конфигурацию
active_listening_config = ActiveListeningConfig(
    enabled=True,        # Включить модуль
    use_llm=True,        # Использовать LLM для точности
    bonus_points=5,      # Бонусные очки за контекстный вопрос
    emoji="👂"           # Emoji для отображения
)

# Создать детектор
active_listening_detector = ActiveListeningDetector(active_listening_config)
```

### Шаг 2: Использование в training_service.py

Найти место, где обрабатывается вопрос пользователя (примерно строка 140-160):

```python
async def process_question(self, user_id: int, question: str, scenario_config):
    session = self.user_service.get_session(user_id)

    # ✅ ДОБАВИТЬ: Проверка активного слушания
    last_response = session.get('last_client_response', '')

    is_contextual = await active_listening_detector.check_context_usage(
        question=question,
        last_response=last_response,
        call_llm_func=self.llm_service.call_llm  # LLM для детекции
    )

    # ✅ ДОБАВИТЬ: Дать бонусные очки
    if is_contextual:
        session['contextual_questions'] = session.get('contextual_questions', 0) + 1
        bonus = active_listening_detector.get_bonus_points()
        session['clarity_level'] += bonus

    # ... существующий код генерации ответа ...

    # ✅ ДОБАВИТЬ: Сохранить ответ для следующей проверки
    session['last_client_response'] = client_response
```

### Шаг 3: Обновить report_generator.py

Найти метод генерации статистики активного слушания (примерно строка 124):

```python
def format_active_listening(self, session: Dict[str, Any]) -> str:
    """Статистика активного слушания."""
    contextual_count = session.get('contextual_questions', 0)
    total_questions = session.get('question_count', 0)

    # ✅ ИСПОЛЬЗОВАТЬ: Метод модуля для форматирования
    return active_listening_detector.format_stats(
        contextual_count=contextual_count,
        total_questions=total_questions
    )
```

---

## 🔧 Отключение модуля (если не нужен)

### Вариант 1: Конфигурация

```python
active_listening_config = ActiveListeningConfig(enabled=False)
active_listening_detector = ActiveListeningDetector(active_listening_config)

# Все вызовы check_context_usage() вернут False
```

### Вариант 2: Не импортировать

Просто не используйте модуль в боте — удалите импорт и вызовы.

---

## 🌍 Использование в другом боте

### Копирование модуля

```bash
# Скопировать в новый бот
cp -r modules/active_listening /path/to/new/bot/modules/

# Готово!
```

### Использование

```python
from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Настроить под свой бот
config = ActiveListeningConfig(
    enabled=True,
    use_llm=False,  # Без LLM для легковесного бота
    bonus_points=10,
    language="en"   # Английский бот
)

detector = ActiveListeningDetector(config)

# В обработчике вопросов
is_contextual = await detector.check_context_usage(
    question=user_question,
    last_response=previous_ai_response
)

if is_contextual:
    user_score += detector.get_bonus_points()
```

---

## 🎯 Преимущества модульного подхода

### ✅ Переносимость
- Копируй папку `modules/active_listening/` в любой бот
- Работает независимо от SPIN-логики

### ✅ Гибкость
- Включить/выключить одной строкой
- Настроить под любой язык
- Использовать с LLM или без

### ✅ Чистота кода
- Вся логика активного слушания в одном месте
- Легко тестировать отдельно
- Не засоряет основной код

### ✅ Масштабируемость
- Легко добавить новые маркеры
- Легко изменить алгоритм детекции
- Легко расширить на другие языки

---

## 📊 Примеры использования

### Пример 1: SPIN Sales Bot (с LLM)

```python
config = ActiveListeningConfig(
    enabled=True,
    use_llm=True,
    bonus_points=5
)
```

### Пример 2: Легковесный бот (без LLM)

```python
config = ActiveListeningConfig(
    enabled=True,
    use_llm=False,  # Только эвристика
    bonus_points=3
)
```

### Пример 3: English Coaching Bot

```python
config = ActiveListeningConfig(
    enabled=True,
    language="en",
    bonus_points=10,
    emoji="🎧"
)
```

### Пример 4: Отключено

```python
config = ActiveListeningConfig(enabled=False)
```

---

## 🧪 Тестирование

Запустить тесты модуля:

```bash
python modules/active_listening/test_active_listening.py
```

Результат:
```
✅ ALL TESTS PASSED!

Module is ready to use! 🚀
```

---

## 📖 Документация

Полная документация: `modules/active_listening/README.md`

Включает:
- Подробное описание работы
- Все параметры конфигурации
- Примеры для разных языков
- FAQ

---

## 🎉 Итого

Модуль активного слушания:
- ✅ Полностью протестирован (6 тестов)
- ✅ Работает с LLM и без
- ✅ Поддерживает русский и английский
- ✅ Легко интегрируется в любой бот
- ✅ Легко отключается

**Готов к использованию!** 🚀

---

Если нужна помощь с интеграцией — см. `modules/active_listening/README.md`
