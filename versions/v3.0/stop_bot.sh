#!/bin/bash

# Остановка бота SPIN Training
echo "🛑 Остановка SPIN Training Bot..."

# Проверяем наличие PID файла
if [ -f "bot.pid" ]; then
    BOT_PID=$(cat bot.pid)
    echo "📋 Найден PID файл с PID: $BOT_PID"
    
    # Проверяем, существует ли процесс
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "🔄 Останавливаем процесс..."
        kill $BOT_PID
        
        # Ждем корректной остановки
        sleep 3
        
        # Проверяем, остановился ли процесс
        if ps -p $BOT_PID > /dev/null 2>&1; then
            echo "⚠️ Процесс не остановился, принудительная остановка..."
            kill -9 $BOT_PID
            sleep 1
        fi
        
        # Удаляем PID файл
        rm -f bot.pid
        echo "✅ Бот остановлен"
    else
        echo "⚠️ Процесс с PID $BOT_PID не найден, удаляем устаревший PID файл"
        rm -f bot.pid
    fi
else
    echo "📋 PID файл не найден, ищем процесс по имени..."
    
    # Поиск процесса бота по имени
    BOT_PID=$(ps aux | grep "python.*bot.py" | grep -v grep | awk '{print $2}')
    
    if [ -z "$BOT_PID" ]; then
        echo "❌ Процесс бота не найден"
        exit 1
    fi
    
    echo "📋 Найден процесс бота с PID: $BOT_PID"
    
    # Остановка процесса
    kill $BOT_PID
    
    # Проверка успешности остановки
    sleep 2
    if ps -p $BOT_PID > /dev/null 2>&1; then
        echo "⚠️ Процесс не остановился, принудительная остановка..."
        kill -9 $BOT_PID
    fi
    
    echo "✅ Бот остановлен"
fi
