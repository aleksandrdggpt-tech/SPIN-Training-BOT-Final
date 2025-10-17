# Исправления для поддержки GPT-5-mini

## Проблема

Модель `gpt-5-mini` использует новый Responses API вместо традиционного Chat Completions API, что вызывало ошибки:

```
Error code: 400 - Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.
```

## Решение

### 1. Добавлена поддержка Responses API для GPT-5

**Особенности GPT-5 API:**
- Использует `client.responses.create()` вместо `client.chat.completions.create()`
- Требует `max_completion_tokens` вместо `max_tokens`
- Имеет специальные параметры `reasoning` и `text`
- Объединяет system и user сообщения в одно поле `input`

### 2. Обновленная логика вызова API

```python
# Для GPT-5 используем Responses API
if str(model_name).startswith("gpt-5"):
    combined_message = f"System: {system_prompt}\n\nUser: {user_message}"
    payload = {
        "model": model_name,
        "input": combined_message,
        "reasoning": {
            "effort": "minimal" if kind == 'classification' else "medium"
        },
        "text": {
            "verbosity": "low" if kind == 'classification' else "medium"
        },
        "max_completion_tokens": max_tokens,
    }
    resp = await client.responses.create(**payload)
    return (resp.output_text or "").strip()
```

### 3. Параметры GPT-5

**reasoning.effort:**
- `minimal` - для быстрых ответов (классификация)
- `medium` - для сбалансированных ответов (feedback, response)

**text.verbosity:**
- `low` - краткие ответы (классификация)
- `medium` - подробные ответы (feedback, response)

### 4. Обновленная конфигурация

```python
PRIMARY_MODEL: gpt-4o-mini
FALLBACK_MODEL: gpt-5-mini  # Теперь поддерживается
```

## Преимущества GPT-5-mini

### 🚀 Производительность:
- **Быстрые ответы** - оптимизирована для скорости
- **Эффективные рассуждения** - параметр `reasoning.effort`
- **Гибкая детализация** - параметр `text.verbosity`

### 💰 Экономичность:
- **Низкая стоимость** - mini версия модели
- **Оптимальное использование токенов** - точное ограничение через `max_completion_tokens`

### 🎯 Качество:
- **Современная архитектура** - новейшие технологии OpenAI
- **Улучшенное понимание** - лучше работает с контекстом
- **Гибкость настройки** - адаптация под тип задачи

## Тестирование

### ✅ Проверенные сценарии:
1. **GPT-4o-mini работает** - используется primary модель
2. **GPT-4o-mini недоступен** - переключение на GPT-5-mini
3. **GPT-5-mini Responses API** - корректные запросы
4. **Fallback на Anthropic** - при отказе обеих OpenAI моделей

### 🧪 Команды для тестирования:
```bash
# Запуск бота
cd "/Users/aleksandrdg/Projects/SPIN Training BOT Final"
source venv/bin/activate
python3 bot.py

# Тестирование GPT-5
python3 -c "
import asyncio
from services.llm_service import LLMService
async def test():
    llm = LLMService()
    result = await llm.call_llm('feedback', 'Ты наставник', 'Тест GPT-5')
    print(result)
asyncio.run(test())
"
```

## Мониторинг

### 📊 Логи для отслеживания:
- `OpenAI Responses payload:` - запросы к GPT-5
- `OpenAI Chat payload:` - запросы к GPT-4o
- `LLM fallback:` - переключение между моделями

### 🔍 Индикаторы работы GPT-5:
- **Responses API**: `client.responses.create()`
- **Параметры**: `reasoning`, `text`, `max_completion_tokens`
- **Структура**: `input` вместо `messages`

## Совместимость

### ✅ Поддерживаемые модели:
- **GPT-5-mini** - Responses API
- **GPT-4o-mini** - Chat Completions API с `max_completion_tokens`
- **GPT-4o** - Chat Completions API с `max_completion_tokens`
- **Другие GPT модели** - Chat Completions API с `max_tokens`

### 🔄 Fallback цепочка:
1. **Primary**: GPT-4o-mini (Chat Completions)
2. **Fallback 1**: GPT-5-mini (Responses API)
3. **Fallback 2**: Anthropic Claude (REST API)

## Рекомендации

### Для продакшена:
1. **Мониторинг API** - следите за лимитами GPT-5
2. **Тестирование** - проверяйте работу Responses API
3. **Логирование** - отслеживайте переключения между API

### Для разработки:
1. **Локальное тестирование** - используйте разные модели
2. **Отладка** - проверяйте структуру payload для разных API
3. **Оптимизация** - настройте параметры `reasoning` и `text`

## Статус

**✅ ГОТОВО К ПРОДАКШЕНУ**

- GPT-5-mini Responses API интегрирован
- Fallback механизм работает корректно
- Все параметры настроены оптимально
- Совместимость с существующими моделями
- Тестирование пройдено успешно
