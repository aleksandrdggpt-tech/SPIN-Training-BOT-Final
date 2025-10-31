"""
Скрипт миграции данных из users_data.json в PostgreSQL.

Использование:
    python scripts/migrate_from_json.py [путь к JSON файлу]

Пример:
    python scripts/migrate_from_json.py users_data.json
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db, get_session
from database.repositories import UserRepository, SessionRepository
from services.database_service import DatabaseService


async def migrate_json_to_db(json_file: str = "users_data.json", bot_name: str = "spin_bot"):
    """
    Миграция данных из JSON в PostgreSQL.

    Args:
        json_file: Путь к JSON файлу с данными
        bot_name: Имя бота для создания сессий
    """
    print("=" * 60)
    print("МИГРАЦИЯ ДАННЫХ ИЗ JSON В POSTGRESQL")
    print("=" * 60)

    # Проверка существования файла
    if not os.path.exists(json_file):
        print(f"❌ Файл {json_file} не найден!")
        return

    # Загрузка данных из JSON
    print(f"\n📂 Загрузка данных из {json_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        print(f"✅ Загружено {len(old_data)} пользователей")
    except Exception as e:
        print(f"❌ Ошибка чтения JSON: {e}")
        return

    # Инициализация БД
    print(f"\n🔄 Инициализация базы данных...")
    try:
        await init_db()
        print("✅ База данных инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return

    # Миграция данных
    print(f"\n🔄 Начинаем миграцию...")
    migrated_count = 0
    errors = []

    for telegram_id_str, data in old_data.items():
        try:
            telegram_id = int(telegram_id_str)
            session_data = data.get('session', {})
            stats_data = data.get('stats', {})

            async with get_session() as session:
                user_repo = UserRepository(session)
                session_repo = SessionRepository(session)

                # Создаем пользователя
                user = await user_repo.get_or_create(
                    telegram_id=telegram_id,
                    username=None,
                    first_name=None
                )

                # Устанавливаем XP и level из stats
                total_xp = stats_data.get('total_xp', 0)
                current_level = stats_data.get('current_level', 1)
                total_trainings = stats_data.get('total_trainings', 0)
                total_score = stats_data.get('total_score', 0)

                # Обновляем user
                user.total_xp = total_xp
                user.level = current_level
                user.total_trainings = total_trainings
                user.total_score = total_score

                await session.flush()

                # Создаем сессию бота
                bot_session = await session_repo.get_or_create(
                    user_id=user.id,
                    bot_name=bot_name
                )

                # Сохраняем session и stats
                bot_session.session_data = session_data
                bot_session.stats_data = stats_data

                await session.flush()

            migrated_count += 1
            print(f"  ✅ Пользователь {telegram_id}: XP={total_xp}, Level={current_level}")

        except Exception as e:
            error_msg = f"Ошибка для пользователя {telegram_id_str}: {e}"
            errors.append(error_msg)
            print(f"  ❌ {error_msg}")

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ МИГРАЦИИ")
    print("=" * 60)
    print(f"✅ Успешно мигрировано: {migrated_count} пользователей")
    if errors:
        print(f"❌ Ошибок: {len(errors)}")
        print("\nОшибки:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Миграция завершена без ошибок!")

    print(f"\n📊 Статистика:")
    print(f"  - Исходный файл: {json_file}")
    print(f"  - Бот: {bot_name}")
    print(f"  - Мигрировано: {migrated_count}/{len(old_data)}")

    # Создаем бэкап
    backup_file = f"{json_file}.backup"
    try:
        import shutil
        shutil.copy(json_file, backup_file)
        print(f"\n💾 Создан бэкап: {backup_file}")
    except Exception as e:
        print(f"\n⚠️  Не удалось создать бэкап: {e}")

    print("\n✅ Готово!")


async def test_migration():
    """
    Тестирование миграции - проверка данных в БД.
    """
    print("\n" + "=" * 60)
    print("ПРОВЕРКА МИГРАЦИИ")
    print("=" * 60)

    db_service = DatabaseService(bot_name="spin_bot")

    # Получаем пользователей
    async with get_session() as session:
        user_repo = UserRepository(session)
        total_users = await user_repo.count_total_users()
        print(f"\n📊 Всего пользователей в БД: {total_users}")

        if total_users > 0:
            # Показываем топ-5
            leaderboard = await user_repo.get_leaderboard(limit=5)
            print(f"\n🏆 Топ-5 по XP:")
            for i, user in enumerate(leaderboard, 1):
                print(f"  {i}. User {user.telegram_id}: {user.total_xp} XP, Level {user.level}")


def main():
    """Главная функция."""
    # Получаем путь к JSON из аргументов
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = "users_data.json"

    bot_name = os.getenv('BOT_NAME', 'spin_bot')

    print(f"\n🤖 Бот: {bot_name}")
    print(f"📂 JSON файл: {json_file}\n")

    # Запускаем миграцию
    asyncio.run(migrate_json_to_db(json_file, bot_name))

    # Тестируем
    asyncio.run(test_migration())


if __name__ == "__main__":
    main()
