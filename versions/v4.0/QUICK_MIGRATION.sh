#!/bin/bash
# Скрипт для быстрой миграции на v4.0 с сохранением резервной копии

set -e  # Остановить при ошибке

echo "🔄 Миграция на v4.0 с сохранением резервной копии"
echo ""

# Проверка, что мы в правильной директории
if [ ! -d "versions/v4.0" ]; then
    echo "❌ Ошибка: Запустите скрипт из корневой директории проекта"
    exit 1
fi

# Текущая ветка
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
echo "📍 Текущая ветка: $CURRENT_BRANCH"
echo ""

# Вариант 1: Создать новую ветку v4.0
echo "📋 Вариант 1: Создать новую ветку v4.0 (РЕКОМЕНДУЕТСЯ)"
echo ""
read -p "Создать ветку backup-main с текущим состоянием? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Создание резервной ветки..."
    git checkout -b backup-main
    git push origin backup-main 2>/dev/null || echo "⚠️  Ветка backup-main уже существует или нет удаленного репозитория"
    git checkout $CURRENT_BRANCH
    echo "✅ Резервная ветка backup-main создана"
    echo ""
fi

echo "🚀 Создание ветки v4.0..."
git checkout -b v4.0 2>/dev/null || {
    echo "⚠️  Ветка v4.0 уже существует. Переключение на неё..."
    git checkout v4.0
}

echo "📝 Добавление файлов v4.0..."
git add versions/v4.0/

# Проверка .env
if git status --short | grep -q "\.env"; then
    echo "⚠️  ВНИМАНИЕ: .env файл обнаружен! Удаляю из индекса..."
    git reset HEAD versions/v4.0/.env 2>/dev/null || true
fi

echo "✅ Файлы добавлены"
echo ""

# Показываем статус
echo "📊 Статус перед коммитом:"
git status --short | head -10
echo ""

read -p "Создать коммит? (y/n): " -n 1 -r
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
    
    read -p "Запушить ветку v4.0 в GitHub? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin v4.0
        echo "✅ Ветка v4.0 запушена в GitHub"
        echo ""
        echo "🎯 Следующие шаги:"
        echo "1. В Railway Dashboard: Settings → Source → Branch: v4.0"
        echo "2. Settings → Build & Deploy → Root Directory: versions/v4.0"
        echo "3. Проверьте переменные окружения (DEV_MODE=0 для production)"
    fi
else
    echo "⏸️  Коммит не создан. Вы можете сделать это вручную."
fi

echo ""
echo "✅ Готово!"

