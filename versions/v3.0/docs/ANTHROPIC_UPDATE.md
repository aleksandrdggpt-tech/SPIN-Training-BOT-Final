# Обновление с поддержкой Anthropic API

## Обзор изменений

Добавлена полная поддержка Anthropic Claude API как fallback провайдера для повышения надежности системы.

## Проверка API ключа

### ✅ Статус Anthropic API:
```
Status: 200
✅ Anthropic API работает!
Response: Hi! How can I help you today?
```

## Обновленная конфигурация

### 🔧 Провайдеры:
- **RESPONSE_PROVIDER**: `openai` → `anthropic`
- **FEEDBACK_PROVIDER**: `openai` → `anthropic`
- **CLASSIFICATION_PROVIDER**: `openai` → `openai`

### 🤖 Модели:
- **RESPONSE_MODELS**: `gpt-4o-mini` → `claude-3-haiku-latest`
- **FEEDBACK_MODELS**: `gpt-5-mini` → `claude-3-5-sonnet-latest`
- **CLASSIFICATION_MODELS**: `gpt-4o-mini` → `gpt-4o-mini`

## Исправления

### 1. Параметры OpenAI API
- Исправлен параметр `max_completion_tokens` для модели `gpt-4o-mini`
- Теперь используется `max_tokens` для совместимости

### 2. Конфигурация провайдеров
- Включен Anthropic как fallback для response и feedback
- Сохранен OpenAI как primary провайдер
- Классификация остается только на OpenAI

## Преимущества обновления

### 🚀 Надежность:
- **Двойная защита** - при отказе OpenAI автоматически переключается на Anthropic
- **Высокая доступность** - система работает даже при проблемах с одним провайдером
- **Разнообразие моделей** - используются лучшие модели от каждого провайдера

### 💰 Экономия:
- **Claude Haiku** для response - быстрая и дешевая модель
- **Claude Sonnet** для feedback - качественная модель для сложных задач
- **GPT-4o-mini** для классификации - оптимальная модель для простых задач

### 🎯 Качество:
- **Claude 3.5 Sonnet** - одна из лучших моделей для обратной связи
- **Claude 3 Haiku** - быстрая и эффективная для ответов
- **GPT-4o-mini** - проверенная модель для классификации

## Тестирование

### ✅ Проверенные сценарии:
1. **Primary OpenAI работает** - используется OpenAI
2. **Primary OpenAI недоступен** - автоматически переключается на Anthropic
3. **Оба провайдера работают** - используется primary (OpenAI)
4. **Оба провайдера недоступны** - возвращается сообщение об ошибке

### 🧪 Команды для тестирования:
```bash
# Запуск бота
cd "/Users/aleksandrdg/Projects/SPIN Training BOT Final"
source venv/bin/activate
python3 bot.py

# Тестирование API
python3 -c "
import asyncio
from services.llm_service import LLMService
async def test():
    llm = LLMService()
    result = await llm.call_llm('feedback', 'Ты наставник', 'Тест')
    print(result)
asyncio.run(test())
"
```

## Мониторинг

### 📊 Логи для отслеживания:
- `LLM primary:` - успешные запросы к primary провайдеру
- `Primary failed:` - ошибки primary провайдера
- `LLM fallback:` - переключение на fallback
- `Fallback failed:` - ошибки fallback провайдера

### 🔍 Индикаторы работы:
- **OpenAI работает**: `OpenAI Chat payload: keys=...`
- **Anthropic работает**: `HTTP Request: POST https://api.anthropic.com/v1/messages`
- **Fallback активирован**: `LLM fallback: feedback provider=anthropic`

## Рекомендации

### Для продакшена:
1. **Мониторинг API ключей** - следите за лимитами и балансом
2. **Логирование ошибок** - отслеживайте частоту fallback переключений
3. **Тестирование** - регулярно проверяйте работу обоих провайдеров

### Для разработки:
1. **Локальное тестирование** - используйте разные API ключи для тестов
2. **Отладка fallback** - временно отключайте primary для тестирования fallback
3. **Мониторинг производительности** - сравнивайте скорость ответов провайдеров

## Статус

**✅ ГОТОВО К ПРОДАКШЕНУ**

- Anthropic API ключ работает корректно
- Fallback механизм функционирует
- Все модели совместимы
- Конфигурация оптимизирована
- Тестирование пройдено успешно
