#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы БД.
Запуск: python test_database.py
"""

import asyncio
import sys
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()

from database import init_db, close_db, get_session
from database.repositories import UserRepository, BadgeRepository, SessionRepository
from services.database_service import DatabaseService

print("=" * 60)
print("🧪 ТЕСТ БАЗЫ ДАННЫХ - SPIN Training Bot v4")
print("=" * 60)


async def test_database():
    """Основная функция тестирования."""

    # 1. Инициализация БД
    print("\n📊 Шаг 1: Инициализация базы данных...")
    try:
        await init_db()
        print("✅ База данных успешно инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

    # 2. Тест создания пользователя
    print("\n👤 Шаг 2: Создание тестового пользователя...")
    try:
        async with get_session() as session:
            user_repo = UserRepository(session)

            # Создаем пользователя
            user = await user_repo.get_or_create(
                telegram_id=999999999,
                username="test_user",
                first_name="Test",
                last_name="User"
            )

            print(f"✅ Пользователь создан:")
            print(f"   - ID: {user.id}")
            print(f"   - Telegram ID: {user.telegram_id}")
            print(f"   - Username: {user.username}")
            print(f"   - XP: {user.total_xp}")
            print(f"   - Level: {user.level}")
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Тест DatabaseService
    print("\n🔧 Шаг 3: Тест DatabaseService...")
    try:
        db_service = DatabaseService(bot_name="spin_bot")

        # Получить сессию пользователя
        user_data = await db_service.get_user_session(
            telegram_id=999999999,
            username="test_user",
            first_name="Test"
        )

        print(f"✅ DatabaseService работает:")
        print(f"   - User: {user_data['user']['telegram_id']}")
        print(f"   - Session keys: {list(user_data['session'].keys())}")
        print(f"   - Stats keys: {list(user_data['stats'].keys())}")
    except Exception as e:
        print(f"❌ Ошибка DatabaseService: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Тест сохранения сессии
    print("\n💾 Шаг 4: Тест сохранения сессии...")
    try:
        test_session = {
            'question_count': 5,
            'clarity_level': 75,
            'chat_state': 'in_progress'
        }
        test_stats = {
            'total_trainings': 1,
            'best_score': 100
        }

        success = await db_service.save_session(
            telegram_id=999999999,
            session_data=test_session,
            stats_data=test_stats
        )

        if success:
            print("✅ Сессия сохранена")

            # Загрузить обратно
            user_data2 = await db_service.get_user_session(telegram_id=999999999)

            if user_data2['session'] == test_session:
                print("✅ Сессия загружена корректно")
            else:
                print("❌ Сессия загружена с ошибкой")
        else:
            print("❌ Не удалось сохранить сессию")
    except Exception as e:
        print(f"❌ Ошибка сохранения сессии: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 5. Тест XP и Level
    print("\n🎮 Шаг 5: Тест геймификации (XP, Level)...")
    try:
        levels_config = [
            {"level": 1, "min_xp": 0},
            {"level": 2, "min_xp": 100},
            {"level": 3, "min_xp": 300}
        ]

        result = await db_service.add_xp_and_check_level_up(
            telegram_id=999999999,
            xp_to_add=150,
            levels_config=levels_config
        )

        print(f"✅ XP добавлен:")
        print(f"   - Leveled up: {result['leveled_up']}")
        print(f"   - Old level: {result['old_level']}")
        print(f"   - New level: {result['new_level']}")
        print(f"   - Total XP: {result['total_xp']}")
    except Exception as e:
        print(f"❌ Ошибка XP/Level: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 6. Тест бейджей
    print("\n🏆 Шаг 6: Тест системы бейджей...")
    try:
        awarded = await db_service.award_badge(
            telegram_id=999999999,
            badge_type="test_badge",
            metadata={"score": 185, "test": True}
        )

        if awarded:
            print("✅ Бейдж выдан")
        else:
            print("⚠️  Бейдж уже был выдан")

        # Получить бейджи
        badges = await db_service.get_user_badges(telegram_id=999999999)
        print(f"✅ Всего бейджей: {len(badges)}")
        for badge in badges:
            print(f"   - {badge['badge_type']} (from {badge['earned_in_bot']})")
    except Exception as e:
        print(f"❌ Ошибка системы бейджей: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 7. Тест TrainingHistory
    print("\n📚 Шаг 7: Тест сохранения истории тренировок...")
    try:
        success = await db_service.save_training_history(
            telegram_id=999999999,
            total_score=185,
            clarity_level=92,
            question_count=8,
            contextual_questions=3,
            per_type_counts={"situation": 2, "problem": 3, "implication": 2, "need_payoff": 1},
            case_data={"client": "TestCorp", "product": "CRM"},
            session_snapshot={"test": True},
            scenario_name="test_scenario"
        )

        if success:
            print("✅ История тренировки сохранена")

            # Получить историю
            history = await db_service.get_user_training_history(telegram_id=999999999, limit=5)
            print(f"✅ Записей в истории: {len(history)}")
            if history:
                print(f"   - Последняя: {history[0]['total_score']} баллов")
        else:
            print("❌ Не удалось сохранить историю")
    except Exception as e:
        print(f"❌ Ошибка сохранения истории: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 8. Проверка количества пользователей
    print("\n📊 Шаг 8: Статистика БД...")
    try:
        async with get_session() as session:
            user_repo = UserRepository(session)
            total_users = await user_repo.count_total_users()
            print(f"✅ Всего пользователей в БД: {total_users}")

            if total_users > 0:
                leaderboard = await user_repo.get_leaderboard(limit=5)
                print(f"✅ Топ-5 по XP:")
                for i, user in enumerate(leaderboard, 1):
                    print(f"   {i}. User {user.telegram_id}: {user.total_xp} XP, Level {user.level}")
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Закрытие БД
    print("\n🔒 Закрытие соединения с БД...")
    try:
        await close_db()
        print("✅ Соединение закрыто")
    except Exception as e:
        print(f"❌ Ошибка закрытия БД: {e}")

    return True


async def main():
    """Главная функция."""
    print("\n🚀 Начинаем тестирование...\n")

    success = await test_database()

    print("\n" + "=" * 60)
    if success:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 60)
        print("\n✅ База данных работает корректно")
        print("✅ Модуль готов к использованию в bot.py")
        print("\n📝 Следующий шаг: Запустите бота командой 'python bot.py'")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 60)
        print("\n⚠️  Проверьте логи выше для деталей")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
