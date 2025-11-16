#!/usr/bin/env python3
"""
Скрипт для удаления пользователя из базы данных по telegram_id.

Использование:
    python scripts/delete_user.py <telegram_id>

Пример:
    python scripts/delete_user.py 123456789
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

from database.database import get_session, init_db
from database.repositories import UserRepository
from sqlalchemy import select
from database import User

async def delete_user(telegram_id: int):
    """Удалить пользователя из БД по telegram_id."""
    print(f"🔍 Ищу пользователя с telegram_id={telegram_id}...")

    async with get_session() as session:
        user_repo = UserRepository(session)

        # Находим пользователя
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            print(f"❌ Пользователь с telegram_id={telegram_id} не найден в БД")
            return False

        print(f"✅ Найден пользователь:")
        print(f"   ID: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Username: {user.username or 'не указан'}")
        print(f"   Имя: {user.first_name or 'не указано'}")
        print(f"   Уровень: {user.level}")
        print(f"   XP: {user.total_xp}")

        # Подтверждение
        confirm = input(f"\n⚠️  Удалить пользователя {user.telegram_id}? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Удаление отменено")
            return False

        # Удаляем пользователя (cascade удалит все связанные данные)
        await session.delete(user)
        await session.flush()

        print(f"✅ Пользователь {telegram_id} успешно удален из БД")
        print("   (Все связанные данные также удалены: сессии, бейджи, подписки и т.д.)")
        return True

async def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("❌ Ошибка: не указан telegram_id")
        print(f"\nИспользование: python {sys.argv[0]} <telegram_id>")
        print(f"Пример: python {sys.argv[0]} 123456789")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Ошибка: '{sys.argv[1]}' не является числом")
        sys.exit(1)

    # Инициализируем БД
    await init_db()

    # Удаляем пользователя
    success = await delete_user(telegram_id)

    if success:
        print("\n✅ Готово! Теперь вы можете протестировать бота с нуля.")
    else:
        print("\n❌ Пользователь не был удален")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())

