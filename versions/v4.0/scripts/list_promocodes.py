#!/usr/bin/env python3
"""
Скрипт для просмотра всех промокодов в базе данных.

Использование:
    python scripts/list_promocodes.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

from database.database import get_session, init_db
from database import Promocode, PromocodeUsage
from sqlalchemy import select, func

async def list_promocodes():
    """Показать все промокоды в БД."""
    print("🔍 Загружаю промокоды из БД...")

    async with get_session() as session:
        # Получаем все промокоды
        stmt = select(Promocode).order_by(Promocode.created_at.desc())
        result = await session.execute(stmt)
        promocodes = list(result.scalars())

        if not promocodes:
            print("✅ В БД нет промокодов")
            return

        print(f"\n📋 Найдено промокодов: {len(promocodes)}\n")
        print("=" * 80)

        for i, promo in enumerate(promocodes, 1):
            print(f"\n{i}. ПРОМОКОД: {promo.code}")
            # promo.type хранится как строка (для SQLite совместимости)
            print(f"   Тип: {promo.type}")
            print(f"   Значение: {promo.value}")
            print(f"   Максимум использований: {promo.max_uses or 'безлимит'}")
            print(f"   Текущее использование: {promo.current_uses}")

            if promo.max_uses:
                remaining = promo.max_uses - promo.current_uses
                print(f"   Осталось использований: {remaining}")
                if remaining <= 0:
                    print(f"   ⚠️  ПРОМОКОД ИСПОЛЬЗОВАН ПОЛНОСТЬЮ")

            if promo.expires_at:
                expires_str = promo.expires_at.strftime('%Y-%m-%d %H:%M:%S')
                now = datetime.utcnow()
                if promo.expires_at < now:
                    print(f"   ❌ Истек: {expires_str} (просрочен)")
                else:
                    days_left = (promo.expires_at - now).days
                    print(f"   Действителен до: {expires_str} (осталось {days_left} дней)")
            else:
                print(f"   Действителен: бессрочно")

            print(f"   Создан: {promo.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

            # Определяем статус промокода
            is_expired = promo.expires_at and promo.expires_at < datetime.utcnow()
            is_used_up = promo.max_uses and promo.current_uses >= promo.max_uses
            is_active = not is_expired and not is_used_up
            print(f"   Статус: {'✅ Активен' if is_active else '❌ Неактивен'}")

            # Подсчитываем реальное количество использований
            usage_stmt = select(func.count(PromocodeUsage.id)).where(
                PromocodeUsage.promocode_id == promo.id
            )
            usage_result = await session.execute(usage_stmt)
            real_uses = usage_result.scalar() or 0

            if real_uses > 0:
                print(f"   Реальное использование: {real_uses}")

            print("-" * 80)

        # Итоговая статистика
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        expired_count = sum(1 for p in promocodes if p.expires_at and p.expires_at < datetime.utcnow())
        used_up_count = sum(1 for p in promocodes if p.max_uses and p.current_uses >= p.max_uses)
        active_count = len(promocodes) - expired_count - used_up_count

        print(f"   Всего промокодов: {len(promocodes)}")
        print(f"   Активных: {active_count}")
        print(f"   Просроченных: {expired_count}")
        print(f"   Использованных полностью: {used_up_count}")

async def main():
    """Главная функция."""
    print("=" * 80)
    print("📋 СПИСОК ПРОМОКОДОВ В БД")
    print("=" * 80)

    # Инициализируем БД
    await init_db()

    # Показываем промокоды
    await list_promocodes()

if __name__ == '__main__':
    asyncio.run(main())

