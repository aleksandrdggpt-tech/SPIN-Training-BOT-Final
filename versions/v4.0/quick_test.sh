#!/bin/bash
# Быстрая проверка бота v4.0

echo "🧪 Быстрая проверка бота v4.0"
echo "================================"
echo ""

# Проверка Python
echo "1. Проверка Python..."
if command -v python3 &> /dev/null; then
    echo "   ✅ Python3 установлен: $(python3 --version)"
else
    echo "   ❌ Python3 не найден"
    exit 1
fi

# Проверка виртуального окружения
echo ""
echo "2. Проверка виртуального окружения..."
if [ -d "venv" ]; then
    echo "   ✅ venv существует"
    source venv/bin/activate 2>/dev/null || true
else
    echo "   ⚠️  venv не найден (создайте: python3 -m venv venv)"
fi

# Проверка .env
echo ""
echo "3. Проверка .env..."
if [ -f ".env" ]; then
    echo "   ✅ .env существует"
    if grep -q "BOT_TOKEN" .env; then
        echo "   ✅ BOT_TOKEN найден в .env"
    else
        echo "   ⚠️  BOT_TOKEN не найден в .env"
    fi
else
    echo "   ⚠️  .env не найден (создайте из env.v4.example)"
fi

# Проверка зависимостей
echo ""
echo "4. Проверка зависимостей..."
if [ -f "requirements.txt" ]; then
    echo "   ✅ requirements.txt существует"
    if python3 -c "import telegram" 2>/dev/null; then
        echo "   ✅ Основные зависимости установлены"
    else
        echo "   ⚠️  Зависимости не установлены (установите: pip install -r requirements.txt)"
    fi
else
    echo "   ❌ requirements.txt не найден"
fi

# Проверка импортов
echo ""
echo "5. Проверка импортов..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from bot import start_command, handle_message
    from config import Config
    print('   ✅ Все основные импорты работают')
except Exception as e:
    print(f'   ❌ Ошибка импорта: {e}')
    sys.exit(1)
" 2>&1

# Проверка синтаксиса
echo ""
echo "6. Проверка синтаксиса..."
if python3 -m py_compile bot.py 2>/dev/null; then
    echo "   ✅ Синтаксис корректен"
else
    echo "   ❌ Ошибка синтаксиса"
    exit 1
fi

# Итог
echo ""
echo "================================"
echo "✅ Проверка завершена!"
echo ""
echo "Для запуска бота выполните:"
echo "  python3 bot.py"
echo ""
