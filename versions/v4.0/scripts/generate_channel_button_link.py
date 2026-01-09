#!/usr/bin/env python3
"""
Скрипт для генерации ссылки на бота с кнопкой для канала.

Использование:
    python scripts/generate_channel_button_link.py

Или с указанием имени бота:
    python scripts/generate_channel_button_link.py --bot @your_bot_username
"""

import os
import sys
import argparse
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv()

from config import Config

def generate_bot_link(bot_username: str = None, post_id: int = None) -> str:
    """
    Генерирует ссылку на бота с параметром для отслеживания нажатий.
    
    Args:
        bot_username: Имя бота (например, @my_bot). Если None, берется из BOT_TOKEN
        post_id: ID поста (опционально, для дополнительной аналитики)
    
    Returns:
        Ссылка на бота вида: https://t.me/bot_username?start=channel_button_123
    """
    if not bot_username:
        # Пытаемся получить из BOT_TOKEN
        bot_token = os.getenv('BOT_TOKEN', '')
        if bot_token:
            # Получаем информацию о боте через API (упрощенный вариант)
            # В реальности нужно использовать getMe, но для простоты используем формат
            # Обычно имя бота можно узнать из настроек или вручную
            print("⚠️  Не указано имя бота. Используйте --bot @your_bot_username")
            print("   Или установите BOT_USERNAME в .env")
            return None
        
        bot_username = os.getenv('BOT_USERNAME', '')
        if not bot_username:
            print("❌ Не указано имя бота. Используйте --bot @your_bot_username")
            return None
    
    # Убираем @ если есть
    if bot_username.startswith('@'):
        bot_username = bot_username[1:]
    
    # Формируем параметр
    if post_id:
        param = f"channel_button_{post_id}"
    else:
        param = "channel_button"
    
    # Генерируем ссылку
    link = f"https://t.me/{bot_username}?start={param}"
    
    return link


def generate_button_html(link: str, button_text: str = "Попробовать бота") -> str:
    """
    Генерирует HTML для кнопки в Telegram канале.
    
    Args:
        link: Ссылка на бота
        button_text: Текст кнопки
    
    Returns:
        HTML код для кнопки
    """
    return f'<a href="{link}">{button_text}</a>'


def generate_markdown_link(link: str, button_text: str = "Попробовать бота") -> str:
    """
    Генерирует Markdown ссылку для кнопки.
    
    Args:
        link: Ссылка на бота
        button_text: Текст кнопки
    
    Returns:
        Markdown ссылка
    """
    return f"[{button_text}]({link})"


def main():
    parser = argparse.ArgumentParser(description='Генерация ссылки на бота для кнопки в канале')
    parser.add_argument('--bot', type=str, help='Имя бота (например, @my_bot)')
    parser.add_argument('--post-id', type=int, help='ID поста (опционально)')
    parser.add_argument('--text', type=str, default='Попробовать бота', help='Текст кнопки')
    parser.add_argument('--format', type=str, choices=['link', 'html', 'markdown'], default='link',
                       help='Формат вывода: link, html или markdown')
    
    args = parser.parse_args()
    
    # Генерируем ссылку
    link = generate_bot_link(args.bot, args.post_id)
    
    if not link:
        sys.exit(1)
    
    # Выводим результат
    print("\n" + "="*60)
    print("🔗 ССЫЛКА НА БОТА ДЛЯ КНОПКИ В КАНАЛЕ")
    print("="*60)
    print(f"\n📎 Ссылка:\n{link}\n")
    
    if args.format == 'html':
        html = generate_button_html(link, args.text)
        print("📝 HTML для кнопки:")
        print(html)
        print("\n💡 Использование: Вставьте этот HTML в пост канала")
    elif args.format == 'markdown':
        md = generate_markdown_link(link, args.text)
        print("📝 Markdown ссылка:")
        print(md)
        print("\n💡 Использование: Вставьте эту ссылку в пост канала")
    else:
        print("💡 Инструкция:")
        print("1. Скопируйте ссылку выше")
        print("2. В Telegram канале создайте пост")
        print("3. Добавьте кнопку с этой ссылкой:")
        print("   - В веб-версии: используйте формат [Текст кнопки](ссылка)")
        print("   - Или используйте бота для создания поста с кнопкой")
        print("\n📊 Статистику нажатий можно посмотреть через /admin → 📊 Статистика")
    
    print("\n" + "="*60 + "\n")
    
    return link


if __name__ == '__main__':
    main()
