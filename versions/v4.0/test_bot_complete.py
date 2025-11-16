#!/usr/bin/env python3
"""
Полная проверка работоспособности бота v4.0.
Проверяет все компоненты без реального запуска бота.
"""

import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

def test_syntax():
    """Проверка синтаксиса."""
    print("=" * 80)
    print("🔍 ТЕСТ 1: Проверка синтаксиса")
    print("=" * 80)

    import py_compile

    files_to_check = [
        'bot.py',
        'config.py',
        'modules/payments/handlers.py',
        'modules/payments/keyboards.py',
        'modules/payments/messages.py',
        'modules/payments/subscription.py',
    ]

    errors = []
    for file in files_to_check:
        try:
            py_compile.compile(file, doraise=True)
            print(f"✅ {file}")
        except py_compile.PyCompileError as e:
            errors.append(f"❌ {file}: {e}")
            print(f"❌ {file}: {e}")

    if errors:
        return False
    print("\n✅ Синтаксис всех файлов корректен")
    return True


def test_imports():
    """Проверка импортов."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 2: Проверка импортов")
    print("=" * 80)

    errors = []

    # Основные функции бота
    try:
        from bot import (
            start_command, handle_message, stats_command,
            rank_command, case_command, help_command,
            start_training_callback
        )
        print("✅ Все основные функции импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта основных функций: {e}")

    # Payment handlers
    try:
        from modules.payments.handlers import (
            register_free_access_handlers,
            free_access_callback,
            check_subscription_callback,
            how_it_works_callback,
            objections_callback,
            mechanics_callback,
            back_to_menu_callback
        )
        print("✅ Все payment handlers импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта payment handlers: {e}")

    # Keyboards
    try:
        from modules.payments.keyboards import (
            get_start_menu_keyboard,
            get_start_training_keyboard,
            get_free_access_keyboard,
            get_access_denied_keyboard
        )
        print("✅ Все keyboards импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта keyboards: {e}")

    # Messages
    try:
        from modules.payments.messages import WELCOME_SALES
        print("✅ Messages импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта messages: {e}")

    # Subscription
    try:
        from modules.payments.subscription import (
            check_access,
            get_or_create_user,
            check_channel_subscription
        )
        print("✅ Subscription модуль импортируется")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта subscription: {e}")

    if errors:
        print("\n❌ ОШИБКИ:")
        for error in errors:
            print(f"   {error}")
        return False
    else:
        print("\n✅ Все импорты работают корректно")
        return True


def test_keyboards():
    """Проверка клавиатур."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 3: Проверка клавиатур")
    print("=" * 80)

    from modules.payments.keyboards import (
        get_start_menu_keyboard,
        get_start_training_keyboard,
        get_free_access_keyboard,
        get_access_denied_keyboard,
        get_subscription_info_keyboard
    )

    issues = []

    # Проверка start_menu_keyboard
    kb = get_start_menu_keyboard()
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    if any('show_tariffs' in str(btn.callback_data) for btn in buttons):
        issues.append("❌ get_start_menu_keyboard содержит кнопку оплаты")
    else:
        print("✅ get_start_menu_keyboard - нет кнопок оплаты")

    # Проверка free_access_keyboard
    kb = get_free_access_keyboard()
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    if any('enter_promo' in str(btn.callback_data) for btn in buttons):
        issues.append("❌ get_free_access_keyboard содержит кнопку промокода")
    else:
        print("✅ get_free_access_keyboard - нет кнопок промокодов")

    # Проверка access_denied_keyboard
    kb = get_access_denied_keyboard()
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    if any('show_tariffs' in str(btn.callback_data) for btn in buttons):
        issues.append("❌ get_access_denied_keyboard содержит кнопку оплаты")
    else:
        print("✅ get_access_denied_keyboard - нет кнопок оплаты")

    # Проверка subscription_info_keyboard
    kb = get_subscription_info_keyboard(has_subscription=False)
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    if any('show_tariffs' in str(btn.callback_data) for btn in buttons):
        issues.append("❌ get_subscription_info_keyboard содержит кнопку оплаты")
    else:
        print("✅ get_subscription_info_keyboard - нет кнопок оплаты")

    if issues:
        print("\n❌ ПРОБЛЕМЫ:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("\n✅ Все клавиатуры проверены")
        return True


def test_handlers_registration():
    """Проверка регистрации handlers."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 4: Проверка регистрации handlers")
    print("=" * 80)

    from modules.payments.handlers import register_free_access_handlers

    # Создаем mock application
    class MockApplication:
        def __init__(self):
            self.handlers = []
        def add_handler(self, handler):
            self.handlers.append(handler)

    mock_app = MockApplication()

    try:
        register_free_access_handlers(mock_app)
        print(f"✅ register_free_access_handlers зарегистрировала {len(mock_app.handlers)} handlers")

        # Проверяем, что show_tariffs_callback НЕ зарегистрирован
        handler_patterns = []
        for handler in mock_app.handlers:
            if hasattr(handler, 'pattern'):
                handler_patterns.append(str(handler.pattern))

        if any('show_tariffs' in pattern for pattern in handler_patterns):
            print("❌ show_tariffs_callback зарегистрирован (не должен быть)")
            return False
        else:
            print("✅ show_tariffs_callback НЕ зарегистрирован (правильно)")

        return True
    except Exception as e:
        print(f"❌ Ошибка регистрации handlers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Проверка конфигурации."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 5: Проверка конфигурации")
    print("=" * 80)

    try:
        from config import Config
        config = Config()

        print(f"✅ BOT_TOKEN: {'установлен' if config.BOT_TOKEN else 'НЕ установлен'}")
        print(f"✅ SCENARIO_PATH: {config.SCENARIO_PATH}")
        print(f"✅ PORT: {config.PORT}")

        if not config.BOT_TOKEN:
            print("⚠️  BOT_TOKEN не установлен - бот не сможет запуститься")
            return False

        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False


def test_database():
    """Проверка базы данных."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 6: Проверка базы данных")
    print("=" * 80)

    try:
        from database.database import init_db, get_session
        import asyncio

        async def test():
            await init_db()
            async with get_session() as session:
                pass
            return True

        result = asyncio.run(test())
        if result:
            print("✅ База данных работает")
            return True
    except Exception as e:
        print(f"❌ Ошибка работы с БД: {e}")
        return False


def test_services():
    """Проверка сервисов."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 7: Проверка сервисов")
    print("=" * 80)

    try:
        from services.database_service import DatabaseService
        from services.llm_service import LLMService
        from services.achievement_service import AchievementService
        from services.user_service_db import UserServiceDB

        db_service = DatabaseService(bot_name='spin_bot')
        print("✅ DatabaseService инициализирован")

        llm_service = LLMService()
        print("✅ LLMService инициализирован")

        achievement_service = AchievementService()
        print("✅ AchievementService инициализирован")

        user_service = UserServiceDB(bot_name='spin_bot')
        print("✅ UserServiceDB инициализирован")

        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации сервисов: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scenario():
    """Проверка загрузки сценария."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 8: Проверка загрузки сценария")
    print("=" * 80)

    try:
        from engine.scenario_loader import ScenarioLoader
        from config import Config

        config = Config()
        # ScenarioLoader инициализируется без параметров, путь передается в load_scenario()
        scenario_loader = ScenarioLoader()
        loaded_scenario = scenario_loader.load_scenario(config.SCENARIO_PATH)
        scenario_config = loaded_scenario.config

        print(f"✅ Сценарий загружен: {scenario_config.get('name', 'Unknown')}")
        print(f"✅ Правила игры: {len(scenario_config.get('game_rules', {}))} правил")

        return True
    except Exception as e:
        print(f"❌ Ошибка загрузки сценария: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов."""
    print("🚀 ПОЛНАЯ ПРОВЕРКА РАБОТОСПОСОБНОСТИ БОТА v4.0")
    print("=" * 80)

    results = []

    results.append(("Синтаксис", test_syntax()))
    results.append(("Импорты", test_imports()))
    results.append(("Клавиатуры", test_keyboards()))
    results.append(("Регистрация handlers", test_handlers_registration()))
    results.append(("Конфигурация", test_config()))
    results.append(("База данных", test_database()))
    results.append(("Сервисы", test_services()))
    results.append(("Сценарий", test_scenario()))

    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 80)

    for name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Бот готов к запуску")
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())

