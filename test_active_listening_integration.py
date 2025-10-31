"""
Тест интеграции модуля активного слушания в SPIN Training Bot.
"""

import asyncio
import sys
from pathlib import Path

# Добавить путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.llm_service import LLMService
from services.user_service import UserService
from services.achievement_service import AchievementService
from services.training_service import TrainingService

from engine.scenario_loader import ScenarioLoader
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator

from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig


async def test_active_listening_integration():
    """Тест интеграции активного слушания."""

    print("=" * 60)
    print("ТЕСТ ИНТЕГРАЦИИ АКТИВНОГО СЛУШАНИЯ")
    print("=" * 60)

    # 1. Инициализация
    print("\n✓ Test 1: Инициализация компонентов")
    config = Config()
    llm_service = LLMService()
    user_service = UserService()
    achievement_service = AchievementService()

    scenario_loader = ScenarioLoader()
    question_analyzer = QuestionAnalyzer()
    report_generator = ReportGenerator()

    active_listening_config = ActiveListeningConfig(
        enabled=True,
        use_llm=False,  # Без LLM для быстрого теста
        bonus_points=5,
        emoji="👂",
        language="ru"
    )
    active_listening_detector = ActiveListeningDetector(active_listening_config)

    loaded_scenario = scenario_loader.load_scenario(config.SCENARIO_PATH)
    scenario_config = loaded_scenario.config
    case_generator = CaseGenerator(scenario_config['case_variants'])

    training_service = TrainingService(
        user_service=user_service,
        llm_service=llm_service,
        achievement_service=achievement_service,
        question_analyzer=question_analyzer,
        report_generator=report_generator,
        case_generator=case_generator,
        scenario_loader=scenario_loader,
        active_listening_detector=active_listening_detector
    )

    print("  ✅ Все компоненты инициализированы")

    # 2. Проверка, что детектор передан в сервис
    print("\n✓ Test 2: Детектор доступен в TrainingService")
    assert training_service.active_listening_detector is not None
    print("  ✅ active_listening_detector найден")

    # 3. Тест format_badge()
    print("\n✓ Test 3: Метод format_badge()")
    badge = training_service.active_listening_detector.format_badge()
    expected = " 👂 (Успешное активное слушание)"
    assert badge == expected, f"Expected '{expected}', got '{badge}'"
    print(f"  ✅ format_badge() = \"{badge}\"")

    # 4. Тест get_bonus_points()
    print("\n✓ Test 4: Метод get_bonus_points()")
    bonus = training_service.active_listening_detector.get_bonus_points()
    assert bonus == 5
    print(f"  ✅ get_bonus_points() = {bonus}")

    # 5. Тест детекции (эвристика, без LLM)
    print("\n✓ Test 5: Детекция активного слушания (эвристика)")

    # 5.1: Без контекста
    result = await training_service.active_listening_detector.check_context_usage(
        question="Сколько у вас сотрудников?",
        last_response="",
        call_llm_func=None
    )
    assert result == False
    print("  ✅ Без last_response: False")

    # 5.2: С числом из контекста
    result = await training_service.active_listening_detector.check_context_usage(
        question="Вы сказали 50 человек. Сколько из них в продажах?",
        last_response="У нас 50 сотрудников.",
        call_llm_func=None
    )
    assert result == True
    print("  ✅ С числом из контекста: True")

    # 5.3: С маркером
    result = await training_service.active_listening_detector.check_context_usage(
        question="Как вы сказали, у вас есть проблемы с логистикой?",
        last_response="Мы работаем с логистикой.",
        call_llm_func=None
    )
    assert result == True
    print("  ✅ С маркером 'как вы сказали': True")

    # 6. Проверка, что старый метод удален из QuestionAnalyzer
    print("\n✓ Test 6: Старый код удален из QuestionAnalyzer")
    assert not hasattr(question_analyzer, 'check_context_usage_fallback'), \
        "check_context_usage_fallback() должен быть удален"
    print("  ✅ check_context_usage_fallback() удален")

    # 7. Тест полного flow (имитация)
    print("\n✓ Test 7: Симуляция процесса обработки вопроса")

    user_id = 12345
    user_data = user_service.get_user_data(user_id)
    session = user_data['session']

    # Имитируем предыдущий ответ клиента
    session['last_client_response'] = "У нас компания на 100 человек."

    # Проверяем контекстуальность нового вопроса
    question = "Вы сказали 100 человек. Сколько работает в продажах?"

    is_contextual = await training_service.active_listening_detector.check_context_usage(
        question=question,
        last_response=session['last_client_response'],
        call_llm_func=None
    )

    assert is_contextual == True
    print(f"  ✅ Вопрос определен как контекстуальный: {is_contextual}")

    # Симулируем начисление бонуса
    if is_contextual:
        session['contextual_questions'] = session.get('contextual_questions', 0) + 1
        bonus_points = training_service.active_listening_detector.get_bonus_points()
        session['clarity_level'] = min(100, session.get('clarity_level', 0) + bonus_points)
        context_badge = training_service.active_listening_detector.format_badge()

        print(f"  ✅ Бонус начислен: +{bonus_points} очков")
        print(f"  ✅ Бейдж: \"{context_badge}\"")
        print(f"  ✅ Контекстуальных вопросов: {session['contextual_questions']}")
        print(f"  ✅ Clarity level: {session['clarity_level']}")

    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 60)
    print("\n🎉 Интеграция активного слушания успешна!")
    print("\nРезультаты:")
    print(f"  • Детектор интегрирован в TrainingService")
    print(f"  • Бейдж отображается с текстом: \"{badge}\"")
    print(f"  • Бонусные очки: {bonus}")
    print(f"  • Детекция работает корректно")
    print(f"  • Старый код удален из QuestionAnalyzer")
    print("\n✅ Готово к использованию в боте!\n")


if __name__ == "__main__":
    asyncio.run(test_active_listening_integration())
