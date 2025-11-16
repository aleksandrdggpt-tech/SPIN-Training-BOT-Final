#!/usr/bin/env python3
"""
Скрипт для удаления бесплатных тренировок пользователя.

Использование:
    python scripts/delete_free_trainings.py <telegram_id> [--source <source>]

Примеры:
    python scripts/delete_free_trainings.py 123456789
    python scripts/delete_free_trainings.py 123456789 --source channel
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
from database import User, FreeTraining, FreeTrainingSource
from sqlalchemy import select, delete

async def delete_free_trainings(telegram_id: int, source: str = None):
    """Удалить бесплатные тренировки пользователя."""
    print(f"🔍 Ищу бесплатные тренировки для пользователя telegram_id={telegram_id}...")

    async with get_session() as session:
        user_repo = UserRepository(session)

        # Находим пользователя
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            print(f"❌ Пользователь с telegram_id={telegram_id} не найден в БД")
            return False

        print(f"✅ Пользователь найден: {user.id}")

        # Находим бесплатные тренировки
        if source:
            # Фильтруем по источнику
            source_enum = FreeTrainingSource[source.upper()]
            stmt = (
                select(FreeTraining)
                .where(FreeTraining.user_id == user.id)
                .where(FreeTraining.source == source_enum)
            )
        else:
            # Все бесплатные тренировки
            stmt = select(FreeTraining).where(FreeTraining.user_id == user.id)

        result = await session.execute(stmt)
        free_trainings = list(result.scalars())

        if not free_trainings:
            print(f"✅ У пользователя нет бесплатных тренировок" + (f" от источника '{source}'" if source else ""))
            return True

        print(f"⚠️  Найдено бесплатных тренировок: {len(free_trainings)}")
        for ft in free_trainings:
            print(f"   - Источник: {ft.source.value}, осталось: {ft.trainings_left}")

        # Подтверждение
        auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
        if not auto_confirm:
            confirm = input(f"\n❓ Удалить все бесплатные тренировки? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Удаление отменено")
                return False
        else:
            print(f"\n✅ Автоматическое подтверждение: удаляю бесплатные тренировки...")

        # Удаляем
        if source:
            delete_stmt = (
                delete(FreeTraining)
                .where(FreeTraining.user_id == user.id)
                .where(FreeTraining.source == source_enum)
            )
        else:
            delete_stmt = delete(FreeTraining).where(FreeTraining.user_id == user.id)

        await session.execute(delete_stmt)
        await session.flush()

        print(f"✅ Бесплатные тренировки успешно удалены")
        return True

async def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("❌ Ошибка: не указан telegram_id")
        print(f"\nИспользование: python {sys.argv[0]} <telegram_id> [--source <source>]")
        print(f"Пример: python {sys.argv[0]} 123456789")
        print(f"Пример: python {sys.argv[0]} 123456789 --source channel")
        sys.exit(1)

    try:
        telegram_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ Ошибка: '{sys.argv[1]}' не является числом")
        sys.exit(1)

    # Проверяем флаг --source
    source = None
    if '--source' in sys.argv:
        idx = sys.argv.index('--source')
        if idx + 1 < len(sys.argv):
            source = sys.argv[idx + 1]

    # Инициализируем БД
    await init_db()

    # Удаляем бесплатные тренировки
    success = await delete_free_trainings(telegram_id, source)

    if success:
        print("\n✅ Готово!")
    else:
        print("\n❌ Операция не завершена")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())

