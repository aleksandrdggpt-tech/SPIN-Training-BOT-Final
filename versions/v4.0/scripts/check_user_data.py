#!/usr/bin/env python3
"""
Скрипт для проверки данных пользователя в БД.

Использование:
    python scripts/check_user_data.py <telegram_id>
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
from database import User, Subscription, FreeTraining, UserBadge, BotSession
from sqlalchemy import select

async def check_user_data(telegram_id: int):
    """Проверить данные пользователя в БД."""
    print(f"🔍 Проверяю данные пользователя telegram_id={telegram_id}...")

    async with get_session() as session:
        user_repo = UserRepository(session)

        # Находим пользователя
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            print(f"❌ Пользователь с telegram_id={telegram_id} не найден в БД")
            return

        print(f"\n✅ Пользователь найден:")
        print(f"   ID: {user.id}")
        print(f"   Telegram ID: {user.telegram_id}")
        print(f"   Username: {user.username or 'не указан'}")
        print(f"   Имя: {user.first_name or 'не указано'}")
        print(f"   Уровень: {user.level}")
        print(f"   XP: {user.total_xp}")
        print(f"   Дата регистрации: {user.registration_date}")
        print(f"   Последняя активность: {user.last_activity}")

        # Проверяем подписки
        sub_result = await session.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
        subscriptions = list(sub_result.scalars())
        print(f"\n📋 Подписки: {len(subscriptions)}")
        for sub in subscriptions:
            print(f"   - Тип: {sub.subscription_type.value}")
            print(f"     Активна: {sub.is_active}")
            print(f"     Начало: {sub.start_date}")
            print(f"     Конец: {sub.end_date}")
            if sub.subscription_type.value == 'credits':
                print(f"     Кредиты: {sub.credits_left}/{sub.credits_total}")

        # Проверяем бесплатные тренировки
        ft_result = await session.execute(
            select(FreeTraining).where(FreeTraining.user_id == user.id)
        )
        free_trainings = list(ft_result.scalars())
        print(f"\n🎁 Бесплатные тренировки: {len(free_trainings)}")
        for ft in free_trainings:
            print(f"   - Источник: {ft.source.value}")
            print(f"     Осталось: {ft.trainings_left}")
            print(f"     Создано: {ft.created_at}")

        # Проверяем бейджи
        badge_result = await session.execute(
            select(UserBadge).where(UserBadge.user_id == user.id)
        )
        badges = list(badge_result.scalars())
        print(f"\n🏆 Бейджи: {len(badges)}")
        for badge in badges:
            print(f"   - {badge.badge_type} (из {badge.earned_in_bot})")

        # Проверяем сессии
        session_result = await session.execute(
            select(BotSession).where(BotSession.user_id == user.id)
        )
        bot_sessions = list(session_result.scalars())
        print(f"\n💾 Сессии ботов: {len(bot_sessions)}")
        for bs in bot_sessions:
            print(f"   - Бот: {bs.bot_name}")
            print(f"     Обновлено: {bs.updated_at}")
            session_data = bs.session_data or {}
            stats_data = bs.stats_data or {}
            print(f"     Состояние: {session_data.get('chat_state', 'unknown')}")
            print(f"     Вопросов: {session_data.get('question_count', 0)}")
            print(f"     Ясность: {session_data.get('clarity_level', 0)}")
            print(f"     Тренировок: {stats_data.get('total_trainings', 0)}")

        # Проверяем доступ
        from modules.payments.subscription import check_access
        access_info = await check_access(telegram_id, session)
        print(f"\n🔐 Статус доступа:")
        print(f"   Есть доступ: {access_info['has_access']}")
        print(f"   Тип доступа: {access_info['access_type']}")
        print(f"   Детали: {access_info['details']}")

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

    # Проверяем данные пользователя
    await check_user_data(telegram_id)

if __name__ == '__main__':
    asyncio.run(main())

