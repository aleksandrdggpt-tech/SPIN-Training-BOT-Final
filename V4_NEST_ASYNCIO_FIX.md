# ✅ Исправление event loop для PostgreSQL + asyncpg

**Дата:** 27 октября 2025  
**Проблема:** RuntimeError с event loops при работе с PostgreSQL  
**Решение:** Использование `nest_asyncio`  

---

## ❌ Ошибка

```
RuntimeError: got Future attached to a different loop
RuntimeError: This event loop is already running
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**Причина:**
- Telegram bot уже запускает event loop
- `_run_async` в `user_service_db.py` пытался создать новый loop
- asyncpg создавал Future'ы в разных loops

---

## ✅ Решение

**Установлено:** `nest_asyncio`

```bash
pip install nest_asyncio
```

**Изменения в `services/user_service_db.py`:**

1. Добавлен импорт и применение:
```python
import nest_asyncio

# Разрешаем вложенные event loops для работы с asyncpg
nest_asyncio.apply()
```

2. Упрощён `_run_async()`:

**Было** (сложная логика с ThreadPoolExecutor):
```python
def _run_async(self, coro):
    try:
        asyncio.get_running_loop()
        # Использовал ThreadPoolExecutor с новым loop
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result()
    except RuntimeError:
        # Сложная fallback логика
        ...
```

**Стало** (просто):
```python
def _run_async(self, coro):
    """
    Helper для запуска async функций в sync контексте.
    Работает даже если event loop уже запущен благодаря nest_asyncio.
    """
    # Благодаря nest_asyncio.apply() можем использовать asyncio.run()
    # даже когда уже есть запущенный event loop
    return asyncio.run(coro)
```

---

## 🎯 Как это работает

`nest_asyncio` патчит `asyncio`, чтобы разрешить вложенные event loops:

- ✅ Можно вызывать `asyncio.run()` когда уже есть запущенный loop
- ✅ Не нужно создавать новые loops в потоках
- ✅ asyncpg корректно работает с существующим loop
- ✅ Все async операции выполняются в одном loop

---

## ✅ Результат

- ✅ Бот импортируется без ошибок
- ✅ PostgreSQL подключение работает
- ✅ Команды обрабатываются корректно
- ✅ Нет конфликтов event loops

---

**Статус:** ✅ ИСПРАВЛЕНО


