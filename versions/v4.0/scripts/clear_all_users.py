#!/usr/bin/env python3
"""
Скрипт для удаления всех пользователей из базы данных.

⚠️  ВНИМАНИЕ: Это удалит ВСЕХ пользователей и все связанные данные!
Используйте только для тестирования/разработки.

Использование:
    python scripts/clear_all_users.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

from database.database import get_session, init_db
from database.repositories import UserRepository
from sqlalchemy import select, delete
from database import User

async def clear_all_users(auto_confirm: bool = False):
    """Удалить всех пользователей из БД."""
    print("🔍 Подсчитываю количество пользователей...")

    async with get_session() as session:
        user_repo = UserRepository(session)

        # Подсчитываем пользователей
        total_count = await user_repo.count_total_users()

        if total_count == 0:
            print("✅ В БД нет пользователей")
            return True

        print(f"⚠️  Найдено пользователей: {total_count}")
        print("\n⚠️  ВНИМАНИЕ: Это удалит ВСЕХ пользователей и все связанные данные:")
        print("   - Всех пользователей")
        print("   - Все сессии (bot_sessions)")
        print("   - Все бейджи (user_badges)")
        print("   - Все подписки (subscriptions)")
        print("   - Все платежи (payments)")
        print("   - Все промокоды (promocode_usages)")
        print("   - Все бесплатные тренировки (free_trainings)")
        print("   - Всю историю тренировок (training_history)")

        # Подтверждение
        if not auto_confirm:
            confirm = input(f"\n❓ Удалить всех {total_count} пользователей? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Удаление отменено")
                return False
        else:
            print(f"\n✅ Автоматическое подтверждение: удаляю всех {total_count} пользователей...")

        print("\n🗑️  Удаляю всех пользователей...")

        # Удаляем всех пользователей (cascade удалит все связанные данные)
        stmt = delete(User)
        await session.execute(stmt)
        await session.flush()

        # Проверяем результат
        remaining = await user_repo.count_total_users()

        if remaining == 0:
            print(f"✅ Все {total_count} пользователей успешно удалены из БД")
            print("   (Все связанные данные также удалены)")
            return True
        else:
            print(f"⚠️  Удалено пользователей, но осталось: {remaining}")
            return False

async def main():
    """Главная функция."""
    print("=" * 60)
    print("🗑️  ОЧИСТКА ВСЕХ ПОЛЬЗОВАТЕЛЕЙ ИЗ БД")
    print("=" * 60)

    # Проверяем флаг --yes
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    # Инициализируем БД
    await init_db()

    # Удаляем всех пользователей
    success = await clear_all_users(auto_confirm=auto_confirm)

    if success:
        print("\n✅ Готово! БД очищена. Теперь вы можете протестировать бота с нуля.")
    else:
        print("\n❌ Очистка не завершена")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())

