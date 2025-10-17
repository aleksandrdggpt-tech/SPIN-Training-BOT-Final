# Конфигурация Feedback с GPT-5-mini

## Обзор

Настроена оптимальная конфигурация для обратной связи наставника с использованием GPT-5-mini как primary модели и Anthropic Claude как fallback.

## Текущая конфигурация

### 🎯 Feedback (Обратная связь наставника):
- **Primary**: `openai` → `gpt-5-mini`
- **Fallback**: `anthropic` → `claude-3-5-sonnet-latest`

### 🔄 Response (Ответы клиента):
- **Primary**: `openai` → `gpt-4o-mini`
- **Fallback**: `anthropic` → `claude-3-haiku-latest`

### 🏷️ Classification (Классификация вопросов):
- **Primary**: `openai` → `gpt-4o-mini`
- **Fallback**: `openai` → `gpt-5-mini`

## Преимущества конфигурации

### 🚀 GPT-5-mini для Feedback:
- **Современная архитектура** - новейшие технологии OpenAI
- **Оптимизация для обратной связи** - специально настроена для наставничества
- **Быстрые ответы** - mini версия для эффективности
- **Качественный анализ** - лучше понимает контекст SPIN-продаж

### 🔄 Anthropic Claude как Fallback:
- **Высокая надежность** - при отказе GPT-5-mini
- **Качественная обратная связь** - Claude 3.5 Sonnet отлично подходит для наставничества
- **Разнообразие подходов** - разные AI провайдеры дают разные перспективы

## Технические детали

### 📋 API параметры для GPT-5-mini:
```python
payload = {
    "model": "gpt-5-mini",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ],
    "temperature": 0.7,
    "max_tokens": 400,
}
```

### 🔧 Fallback цепочка для Feedback:
1. **GPT-5-mini** (OpenAI) - primary для обратной связи
2. **Claude 3.5 Sonnet** (Anthropic) - fallback при отказе primary

## Мониторинг

### 📊 Логи для отслеживания Feedback:
- `LLM primary: feedback provider=openai model=gpt-5-mini` - успешный запрос к GPT-5-mini
- `Primary failed (feedback):` - ошибка GPT-5-mini
- `LLM fallback: feedback provider=anthropic` - переключение на Claude
- `Fallback failed (feedback):` - ошибка Anthropic

### 🔍 Индикаторы работы:
- **GPT-5-mini работает**: `OpenAI Chat payload: keys=['model', 'messages', 'temperature', 'max_tokens']`
- **Claude работает**: `HTTP Request: POST https://api.anthropic.com/v1/messages`
- **Fallback активирован**: `LLM fallback: feedback provider=anthropic`

## Тестирование

### ✅ Сценарии тестирования:
1. **GPT-5-mini доступен** - используется для feedback
2. **GPT-5-mini недоступен** - переключение на Claude
3. **Оба провайдера работают** - используется GPT-5-mini
4. **Оба провайдера недоступны** - сообщение об ошибке

### 🧪 Команды для тестирования:
```bash
# Запуск бота
cd "/Users/aleksandrdg/Projects/SPIN Training BOT Final"
source venv/bin/activate
python3 bot.py

# Тестирование feedback
python3 -c "
import asyncio
from services.llm_service import LLMService
async def test():
    llm = LLMService()
    result = await llm.call_llm('feedback', 'Ты наставник SPIN', 'Тест')
    print(result)
asyncio.run(test())
"
```

## Оптимизация

### 🎯 Настройки для разных типов задач:

**Feedback (Обратная связь):**
- Модель: GPT-5-mini
- Temperature: 0.7 (творческий подход)
- Max tokens: 400 (подробная обратная связь)

**Response (Ответы клиента):**
- Модель: GPT-4o-mini
- Temperature: 0.7 (естественные ответы)
- Max tokens: 400 (развернутые ответы)

**Classification (Классификация):**
- Модель: GPT-4o-mini
- Temperature: 0.0 (точная классификация)
- Max tokens: 20 (краткий ответ)

## Рекомендации

### Для продакшена:
1. **Мониторинг GPT-5-mini** - следите за лимитами и производительностью
2. **Тестирование fallback** - регулярно проверяйте переключение на Claude
3. **Логирование** - отслеживайте качество обратной связи

### Для разработки:
1. **A/B тестирование** - сравнивайте качество GPT-5-mini и Claude
2. **Настройка промптов** - оптимизируйте system prompts для GPT-5-mini
3. **Мониторинг токенов** - следите за расходом токенов

## Статус

**✅ ГОТОВО К ПРОДАКШЕНУ**

- GPT-5-mini настроен как primary для feedback
- Anthropic Claude настроен как fallback
- Все API параметры корректны
- Fallback механизм протестирован
- Конфигурация оптимизирована
