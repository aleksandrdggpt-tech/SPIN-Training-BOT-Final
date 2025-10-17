# SPIN TRAINING BOT v.3.0 — Конструктор обучающих ботов

Универсальный Telegram-бот для обучающих сценариев. Логика вынесена в конфигурации сценариев — создавайте новые обучающие боты без правок кода.

## Архитектура

```
engine/
  scenario_loader.py     # загрузка и валидация конфигов
  question_analyzer.py   # определение типа вопроса и очков ясности
  report_generator.py    # финальный отчёт, бейджи, рекомендации
services/
  llm_service.py         # OpenAI/Anthropic + fallback, HTTP/2, pooling
  training_service.py    # сессия тренировки, фидбек, TTL‑кэш
  user_service.py        # данные пользователя и статистика
infrastructure/
  health_server.py       # health‑check HTTP
scenarios/
  spin_sales/            # продакшн‑сценарий SPIN
  template/              # шаблон
bot.py                   # хендлеры Telegram и координация
```

## Что нового в v3.0 (кратко)
- Единые клиенты: httpx AsyncClient (HTTP/2, pooling) + AsyncOpenAI
- Антидублирование «ДА», TTL‑кэш фидбека, прогрев моделей при старте
- Стриминг фидбека для GPT‑4‑серии и Anthropic (GPT‑5 — обычная генерация)
- Новые команды: `/caseinfo`, `/author`; `/validate` — только для админов
- .env упрощена — только секреты; остальное сконфигурировано в коде

## Быстрый старт

1) Установить зависимости (рекомендуется в venv):
```bash
pip install -r REQUIREMENTS.txt
```

2) Создать и заполнить `.env` (только секреты и админы):
```
BOT_TOKEN=...                # токен Telegram‑бота
OPENAI_API_KEY=...           # ключ OpenAI
# (опционально) Anthropic для fallback
ANTHROPIC_API_KEY=...
# (опционально) список Telegram‑ID админов для /validate
ADMIN_USER_IDS=123456789,987654321
```

3) Запуск:
```bash
python3 bot.py
```

Команды в чате:
- `/start`, `/help`, `/stats`, `/rank`, `/caseinfo`, `/author`
- текстовые: «начать», «завершить», «ДА»
- `/validate` — доступна только админам (если указан `ADMIN_USER_IDS`)

## Создание нового сценария

1) Скопируйте `scenarios/template` в новую папку, например `scenarios/my_course`.

2) Заполните `scenarios/my_course/config.json`:
- `scenario_info`: метаданные сценария
- `messages`: тексты интерфейса и прогресса
- `prompts`: системные промпты (генерация кейса, ответы клиента, обратная связь)
- `question_types`: типы вопросов/ходов (ключевые слова, очки ясности, множители)
- `game_rules`: правила сессии (максимум вопросов, цель ясности и т.п.)
- `scoring`: бейджи по шкале очков
- `ui`: формат прогресса, набор команд

3) Укажите путь к новому сценарию в коде/конфиге при необходимости (по умолчанию используется `scenarios/spin_sales/config.json`).

4) Перезапустите бота.

## Структура config.json (обязательные секции)

```json
{
  "scenario_info": { "name": "...", "version": "1.0", "description": "..." },
  "messages": { "welcome": "...", "case_generated": "{client_case}", "training_complete": "{report}", "error_generic": "...", "progress": "...", "question_feedback": "...", "clarity_reached": "..." },
  "prompts": { "case_generation": "...", "client_response": "...", "feedback": "..." },
  "question_types": [ { "id": "...", "name": "...", "emoji": "", "keywords": ["..."], "clarity_points": 0, "score_multiplier": 0 } ],
  "game_rules": { "max_questions": 10, "min_questions_for_completion": 5, "target_clarity": 80, "short_question_threshold": 5 },
  "scoring": { "badges": [ { "min_score": 0, "max_score": 100, "name": "...", "emoji": "🥉" } ] },
  "ui": { "progress_format": "...", "commands": ["начать", "старт", "завершить"] }
}
```

## Совместимость и обработка ошибок
- Вся предметная логика вынесена в `scenarios/.../config.json`.
- Health‑check доступен на локальном порту (см. вывод запуска).
- При ошибках загрузки сценария бот отвечает понятным сообщением и логирует детали.

## Примечания
- Для смены домена обучения правьте только конфиг сценария — код бота менять не нужно.
- Рекомендуется хранить `venv/`, `__pycache__/`, `logs/`, `.env` вне репозитория (см. `.gitignore`).

