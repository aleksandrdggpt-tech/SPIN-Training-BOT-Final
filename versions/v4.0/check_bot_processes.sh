#!/bin/bash
# Скрипт для проверки запущенных процессов бота

echo "🔍 Проверка запущенных процессов бота..."
echo ""

# Проверка по PID файлу
if [ -f bot.pid ]; then
    PID=$(cat bot.pid 2>/dev/null)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Найден процесс по PID файлу: $PID"
        ps -p $PID -o pid,command
    else
        echo "⚠️ PID файл существует, но процесс не найден. Удаляю файл..."
        rm -f bot.pid
    fi
else
    echo "ℹ️ PID файл не найден"
fi

echo ""
echo "🔍 Поиск процессов python с bot.py..."
ps aux | grep -E "python.*bot\.py" | grep -v grep | while read line; do
    echo "  $line"
done

echo ""
echo "💡 Для остановки всех процессов бота используйте:"
echo "   pkill -f 'python.*bot.py'"
