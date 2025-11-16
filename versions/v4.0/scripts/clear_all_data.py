#!/usr/bin/env python3
"""
Скрипт для полной очистки всех данных из базы данных.
Удаляет все записи из всех таблиц, включая те, которые могут остаться после удаления пользователей.

⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные из БД!
Используйте только для тестирования/разработки.

Использование:
    python scripts/clear_all_data.py --yes
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
from database import (
    User, BotSession, Subscription, FreeTraining,
    PromocodeUsage, TrainingHistory, UserBadge, Payment
)
from sqlalchemy import delete, select, func

async def clear_all_data(auto_confirm: bool = False):
    """Удалить все данные из БД."""
    print("=" * 80)
    print("🗑️  ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ ИЗ БД")
    print("=" * 80)

    async with get_session() as session:
        # Подсчитываем записи в каждой таблице
        counts = {}
        tables = {
            'Пользователи': User,
            'Сессии': BotSession,
            'Подписки': Subscription,
            'Бесплатные тренировки': FreeTraining,
            'Использования промокодов': PromocodeUsage,
            'История тренировок': TrainingHistory,
            'Бейджи': UserBadge,
            'Платежи': Payment,
        }

        print("\n🔍 Подсчитываю записи в таблицах...")
        for name, table in tables.items():
            result = await session.execute(select(func.count()).select_from(table))
            count = result.scalar()
            counts[name] = count
            if count > 0:
                print(f"   {name}: {count}")

        total_records = sum(counts.values())

        if total_records == 0:
            print("\n✅ БД уже пуста")
            return True

        print(f"\n⚠️  Всего найдено записей: {total_records}")
        print("\n⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные из БД:")
        for name, count in counts.items():
            if count > 0:
                print(f"   - {name}: {count} записей")

        # Подтверждение
        if not auto_confirm:
            confirm = input(f"\n❓ Удалить все {total_records} записей? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Удаление отменено")
                return False
        else:
            print(f"\n✅ Автоматическое подтверждение: удаляю все {total_records} записей...")

        print("\n🗑️  Удаляю все данные...")

        # Удаляем в правильном порядке (сначала зависимые таблицы)
        deletion_order = [
            ('История тренировок', TrainingHistory),
            ('Бейджи', UserBadge),
            ('Платежи', Payment),
            ('Использования промокодов', PromocodeUsage),
            ('Бесплатные тренировки', FreeTraining),
            ('Подписки', Subscription),
            ('Сессии', BotSession),
            ('Пользователи', User),
        ]

        deleted_counts = {}
        for name, table in deletion_order:
            if counts.get(name, 0) > 0:
                stmt = delete(table)
                result = await session.execute(stmt)
                deleted_counts[name] = result.rowcount
                print(f"   ✅ {name}: удалено {result.rowcount} записей")

        await session.commit()

        # Проверяем результат
        print("\n🔍 Проверяю результат...")
        remaining = {}
        for name, table in tables.items():
            result = await session.execute(select(func.count()).select_from(table))
            count = result.scalar()
            if count > 0:
                remaining[name] = count

        if not remaining:
            print(f"\n✅ Все данные успешно удалены из БД")
            print(f"   Удалено записей: {sum(deleted_counts.values())}")
            return True
        else:
            print(f"\n⚠️  Остались записи:")
            for name, count in remaining.items():
                print(f"   - {name}: {count} записей")
            return False

async def main():
    """Главная функция."""
    # Проверяем флаг --yes
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    # Инициализируем БД
    await init_db()

    # Удаляем все данные
    success = await clear_all_data(auto_confirm=auto_confirm)

    if success:
        print("\n✅ Готово! БД полностью очищена. Теперь вы можете протестировать бота с нуля.")
    else:
        print("\n❌ Очистка не завершена полностью")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())

