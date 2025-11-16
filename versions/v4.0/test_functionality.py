#!/usr/bin/env python3
"""
Комплексная проверка функциональности бота v4.0.
Проверяет импорты, структуру, основные функции.
"""

import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Проверка всех критических импортов."""
    print("=" * 80)
    print("🔍 ТЕСТ 1: Проверка импортов")
    print("=" * 80)

    errors = []

    try:
        from bot import (
            start_command, handle_message, stats_command,
            rank_command, case_command, help_command,
            start_training_callback, scenario_command,
            validate_config_command, author_command
        )
        print("✅ Все основные функции импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта основных функций: {e}")
        print(f"❌ Ошибка: {e}")

    try:
        from config import Config
        print("✅ Config импортируется")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта Config: {e}")

    try:
        from services.database_service import DatabaseService
        from services.spin_training_service import SpinTrainingService
        from services.llm_service import LLMService
        from services.achievement_service import AchievementService
        print("✅ Все сервисы импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта сервисов: {e}")

    try:
        from engine.scenario_loader import ScenarioLoader
        from engine.case_generator import CaseGenerator
        from engine.question_analyzer import QuestionAnalyzer
        from engine.report_generator import ReportGenerator
        print("✅ Все компоненты engine импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта engine: {e}")

    try:
        from database.database import init_db, close_db, get_session
        print("✅ Database модули импортируются")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта database: {e}")

    try:
        from modules.active_listening import ActiveListeningDetector
        print("✅ Active listening модуль импортируется")
    except Exception as e:
        errors.append(f"❌ Ошибка импорта active_listening: {e}")

    # Проверяем, что payment модули НЕ используются в основных функциях
    try:
        import bot
        bot_source = open('bot.py', 'r').read()

        # Проверяем, что нет активных импортов payment (только закомментированные)
        if 'from modules.payments' in bot_source and '# from modules.payments' not in bot_source:
            # Ищем незакомментированные импорты
            lines = bot_source.split('\n')
            for i, line in enumerate(lines):
                if 'from modules.payments' in line and not line.strip().startswith('#'):
                    errors.append(f"❌ Найдена незакомментированная строка {i+1}: {line.strip()}")
        else:
            print("✅ Payment модули правильно закомментированы")
    except Exception as e:
        errors.append(f"❌ Ошибка проверки payment модулей: {e}")

    if errors:
        print("\n❌ ОШИБКИ:")
        for error in errors:
            print(f"   {error}")
        return False
    else:
        print("\n✅ Все импорты работают корректно")
        return True


def test_structure():
    """Проверка структуры файлов."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 2: Проверка структуры файлов")
    print("=" * 80)

    required_files = [
        'bot.py',
        'config.py',
        'requirements.txt',
        'Dockerfile',
        'railway.json',
        'README.md',
        'CHANGELOG.md',
        '.gitignore',
        'env.v4.example',
        'database/__init__.py',
        'database/database.py',
        'engine/__init__.py',
        'services/__init__.py',
        'scenarios/spin_sales/config.json',
    ]

    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
        else:
            print(f"✅ {file}")

    if missing:
        print(f"\n❌ Отсутствуют файлы: {', '.join(missing)}")
        return False
    else:
        print("\n✅ Все необходимые файлы присутствуют")
        return True


def test_payment_comments():
    """Проверка, что payment функционал правильно закомментирован."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 3: Проверка закомментированного функционала оплаты")
    print("=" * 80)

    try:
        with open('bot.py', 'r') as f:
            content = f.read()

        issues = []

        # Проверяем, что нет активных вызовов register_payment_handlers
        if 'register_payment_handlers(application)' in content:
            if '# register_payment_handlers(application)' not in content:
                issues.append("❌ register_payment_handlers вызывается без комментария")
            else:
                print("✅ register_payment_handlers закомментирован")

        # Проверяем, что нет активных вызовов get_payment_menu_keyboard
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'get_payment_menu_keyboard()' in line and not line.strip().startswith('#'):
                issues.append(f"❌ Строка {i+1}: активный вызов get_payment_menu_keyboard")

        if not issues:
            print("✅ Все вызовы payment функций закомментированы")

        # Проверяем наличие комментариев о возможности вернуть функционал
        if 'Раскомментировать когда нужно вернуть функционал оплаты' in content:
            print("✅ Комментарии о возврате функционала присутствуют")
        else:
            issues.append("⚠️ Нет комментариев о возврате функционала")

        if issues:
            print("\n⚠️ ПРОБЛЕМЫ:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print("\n✅ Функционал оплаты правильно закомментирован")
            return True

    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False


def test_basic_functionality():
    """Проверка базовой функциональности без запуска бота."""
    print("\n" + "=" * 80)
    print("🔍 ТЕСТ 4: Проверка базовой функциональности")
    print("=" * 80)

    try:
        from bot import start_command, handle_message
        from config import Config

        config = Config()

        # Проверяем, что конфигурация загружается
        if config.BOT_TOKEN:
            print("✅ BOT_TOKEN загружен")
        else:
            print("⚠️ BOT_TOKEN не установлен (нормально для теста)")

        if config.SCENARIO_PATH:
            print(f"✅ SCENARIO_PATH: {config.SCENARIO_PATH}")

        # Проверяем, что функции определены
        if callable(start_command):
            print("✅ start_command определена")
        else:
            print("❌ start_command не является функцией")
            return False

        if callable(handle_message):
            print("✅ handle_message определена")
        else:
            print("❌ handle_message не является функцией")
            return False

        print("\n✅ Базовая функциональность проверена")
        return True

    except Exception as e:
        print(f"❌ Ошибка проверки функциональности: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов."""
    print("🚀 КОМПЛЕКСНАЯ ПРОВЕРКА ФУНКЦИОНАЛЬНОСТИ БОТА v4.0")
    print("=" * 80)

    results = []

    results.append(("Импорты", test_imports()))
    results.append(("Структура файлов", test_structure()))
    results.append(("Закомментированный функционал", test_payment_comments()))
    results.append(("Базовая функциональность", test_basic_functionality()))

    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 80)

    for name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ НЕ ПРОЙДЕН"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())

