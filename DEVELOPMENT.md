# 🛠️ Руководство по разработке

## Структура управления версиями

### Архив версий
- `versions/v1.0/` - первая версия (только для чтения)
- `versions/v2.0/` - текущая production версия (только для чтения)

### Рабочие файлы
Все изменения для v3.0 вносятся в файлы в корне проекта.

## Начало работы над v3.0

1. Убедитесь, что текущая версия работает
2. Создайте список планируемых изменений
3. Вносите изменения постепенно
4. Тестируйте после каждого изменения
5. Документируйте все изменения в CHANGELOG.md

## Параллельная разработка v3 при проде v2 на Railway

Чтобы v2 продолжала стабильно деплоиться на Railway (из `versions/v2.0`), а мы локально работали над v3 в корне проекта, настройте локальную среду так:

1) Раздельные виртуальные окружения
```bash
# Для v2 (чтение и локальный запуск при необходимости)
python3.11 -m venv venv-v2
source venv-v2/bin/activate
pip install --upgrade pip
pip install -r versions/v2.0/requirements.txt
deactivate

# Для v3 (рабочая разработка)
python3.11 -m venv venv-v3
source venv-v3/bin/activate
pip install --upgrade pip
pip install -r REQUIREMENTS.txt
deactivate
```

2) Раздельные env-файлы в корне repo
- `.env.v2` (используется на Railway и/или локально для v2):
  - `BOT_TOKEN`, `OPENAI_API_KEY`, `SCENARIO_PATH` → путь внутри `versions/v2.0/scenarios/...` при локальном запуске v2
- `.env.v3` (локальная разработка корня):
  - `BOT_TOKEN`, `OPENAI_API_KEY`, `SCENARIO_PATH` → например `scenarios/spin_sales/config.json`

3) Запуск локально
```bash
# v2 локально
cd versions/v2.0
source ../../venv-v2/bin/activate
export $(grep -v '^#' ../../.env.v2 | xargs) 2>/dev/null || true
python bot.py

# v3 локально (в корне)
cd ../..
source venv-v3/bin/activate
export $(grep -v '^#' .env.v3 | xargs) 2>/dev/null || true
python bot.py
```

4) Деплой v2 на Railway
- В UI Railway укажите Root Directory: `versions/v2.0`
- Установите переменные окружения из `.env.v2` в Railway Variables
- Команда запуска по умолчанию: `python bot.py`

Примечание: папку `versions/` не изменяем — это архив версий. Весь код v3 — только в корне.

## Правила разработки

### Перед началом работы
- [ ] Убедитесь, что версия 2.0 заархивирована
- [ ] Создайте список задач для v3.0
- [ ] Определите приоритеты

### Во время разработки
- [ ] Делайте небольшие изменения
- [ ] Тестируйте каждое изменение
- [ ] Обновляйте CHANGELOG.md
- [ ] Коммитите часто с понятными сообщениями

### Перед релизом v3.0
- [ ] Полное тестирование всех функций
- [ ] Обновить README.md
- [ ] Обновить CHANGELOG.md
- [ ] Обновить VERSIONS.md
- [ ] Создать архив v3.0 в папке versions/

## Тестирование

### Локальное тестирование
```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск бота
python bot.py
```

### Тестирование в Docker
```bash
# Сборка образа
docker build -t spin-bot:v3.0 .

# Запуск контейнера
docker run -d --env-file .env spin-bot:v3.0
```

### Деплой на Railway
```bash
# Деплой тестовой версии (пример)
# 1) Создайте проект в Railway
# 2) Подключите репозиторий GitHub
# 3) Добавьте переменные окружения (.env) в Railway Variables
# 4) Запустите деплой из UI Railway или CLI
```

## Чек-лист перед релизом

- [ ] Все функции работают
- [ ] Обновлена документация
- [ ] Обновлен CHANGELOG.md
- [ ] Обновлен VERSIONS.md
- [ ] Протестировано локально
- [ ] Протестировано в Docker
- [ ] Протестировано на Railway (staging)
- [ ] Создан архив версии
