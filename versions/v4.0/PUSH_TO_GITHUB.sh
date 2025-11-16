#!/bin/bash
# Скрипт для пуша ветки v4.0 в GitHub

set -e

echo "🚀 Пуш ветки v4.0 в GitHub"
echo ""

cd /Users/aleksandrdg/Projects/SPIN\ Training\ BOT\ Final

# Проверка текущей ветки
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Текущая ветка: $CURRENT_BRANCH"

# Создать или переключиться на v4.0
if git branch | grep -q "v4.0"; then
    echo "✅ Ветка v4.0 существует, переключаюсь..."
    git checkout v4.0
else
    echo "📦 Создаю ветку v4.0..."
    git checkout -b v4.0
fi

# Добавить файлы
echo "📝 Добавляю файлы versions/v4.0/..."
git add versions/v4.0/

# Проверка .env
if git status --short | grep -q "\.env"; then
    echo "⚠️  .env обнаружен! Удаляю из индекса..."
    git reset HEAD versions/v4.0/.env 2>/dev/null || true
    echo "✅ .env удален из индекса"
else
    echo "✅ .env не добавлен (правильно)"
fi

# Показать статус
echo ""
echo "📊 Статус:"
git status --short | head -10
echo ""

# Коммит
read -p "Создать коммит и запушить? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "feat: Add v4.0 version with Railway deployment support

- PostgreSQL/asyncpg support with SSL
- Optional SQLite for local development (DEV_MODE=1)
- Railway deployment configuration (Procfile)
- PEP8 formatted code (all 61 Python files)
- Statistics functionality
- Free access flow (no payments in v4.0)"
    
    echo "✅ Коммит создан"
    echo ""
    
    echo "🚀 Пушим в GitHub..."
    git push origin v4.0 --set-upstream
    
    echo ""
    echo "✅ Готово! Ветка v4.0 запушена в GitHub"
    echo ""
    echo "🎯 Следующие шаги в Railway:"
    echo "1. Settings → Source → Branch: v4.0"
    echo "2. Settings → Build & Deploy → Root Directory: versions/v4.0"
    echo "3. Проверьте переменные окружения (DEV_MODE=0 для production)"
else
    echo "⏸️  Коммит не создан. Выполните вручную:"
    echo "   git commit -m 'feat: Add v4.0 version'"
    echo "   git push origin v4.0"
fi

