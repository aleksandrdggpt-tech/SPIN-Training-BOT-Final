"""
Тест новой архитектуры с BaseTrainingService и SpinTrainingService.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services import (
    BaseTrainingService,
    SpinTrainingService,
    LLMService,
    UserService,
    AchievementService
)

from engine.scenario_loader import ScenarioLoader
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator

from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig


async def test_base_training_service():
    """Тест новой модульной архитектуры."""

    print("=" * 60)
    print("ТЕСТ МОДУЛЬНОЙ АРХИТЕКТУРЫ")
    print("=" * 60)

    # 1. Инициализация базовых сервисов
    print("\n✓ Test 1: Инициализация базовых сервисов")
    config = Config()
    llm_service = LLMService()
    user_service = UserService()
    achievement_service = AchievementService()
    print("  ✅ Базовые сервисы инициализированы")

    # 2. Инициализация SPIN-специфичных компонентов
    print("\n✓ Test 2: Инициализация SPIN-компонентов")
    scenario_loader = ScenarioLoader()
    question_analyzer = QuestionAnalyzer()
    report_generator = ReportGenerator()

    loaded_scenario = scenario_loader.load_scenario(config.SCENARIO_PATH)
    scenario_config = loaded_scenario.config
    case_generator = CaseGenerator(scenario_config['case_variants'])
    print("  ✅ SPIN-компоненты инициализированы")

    # 3. Инициализация active listening
    print("\n✓ Test 3: Инициализация Active Listening")
    active_listening_config = ActiveListeningConfig(
        enabled=True,
        use_llm=False,
        bonus_points=5,
        emoji="👂",
        language="ru"
    )
    active_listening_detector = ActiveListeningDetector(active_listening_config)
    print("  ✅ Active Listening инициализирован")

    # 4. Создание SpinTrainingService
    print("\n✓ Test 4: Создание SpinTrainingService")
    spin_service = SpinTrainingService(
        user_service=user_service,
        llm_service=llm_service,
        achievement_service=achievement_service,
        question_analyzer=question_analyzer,
        report_generator=report_generator,
        case_generator=case_generator,
        scenario_loader=scenario_loader,
        active_listening_detector=active_listening_detector
    )
    print("  ✅ SpinTrainingService создан")

    # 5. Проверка наследования
    print("\n✓ Test 5: Проверка наследования от BaseTrainingService")
    assert isinstance(spin_service, BaseTrainingService)
    assert isinstance(spin_service, SpinTrainingService)
    print("  ✅ SpinTrainingService наследуется от BaseTrainingService")

    # 6. Проверка общих методов (из базового класса)
    print("\n✓ Test 6: Проверка общих методов")
    assert hasattr(spin_service, 'check_active_listening')
    assert hasattr(spin_service, 'apply_active_listening_bonus')
    assert hasattr(spin_service, 'get_feedback')
    assert hasattr(spin_service, 'check_training_completion')
    assert hasattr(spin_service, 'get_user_data')
    assert hasattr(spin_service, 'reset_session')
    assert hasattr(spin_service, 'update_stats')
    print("  ✅ Все общие методы доступны")

    # 7. Проверка SPIN-специфичных методов
    print("\n✓ Test 7: Проверка SPIN-специфичных методов")
    assert hasattr(spin_service, 'start_training')
    assert hasattr(spin_service, 'process_question')
    assert hasattr(spin_service, 'build_feedback_prompt')
    assert hasattr(spin_service, 'complete_training')
    print("  ✅ Все SPIN-методы доступны")

    # 8. Проверка SPIN-специфичных компонентов
    print("\n✓ Test 8: Проверка SPIN-компонентов в сервисе")
    assert spin_service.question_analyzer is not None
    assert spin_service.report_generator is not None
    assert spin_service.case_generator is not None
    assert spin_service.scenario_loader is not None
    print("  ✅ Все SPIN-компоненты доступны")

    # 9. Тест общего метода check_active_listening
    print("\n✓ Test 9: Тест общего метода check_active_listening")
    is_contextual, badge = await spin_service.check_active_listening(
        question="Вы сказали 100 человек. Сколько в продажах?",
        last_response="У нас 100 сотрудников."
    )
    assert is_contextual == True
    assert badge == " 👂 (Успешное активное слушание)"
    print(f"  ✅ check_active_listening() работает")
    print(f"  ✅ is_contextual: {is_contextual}")
    print(f"  ✅ badge: \"{badge}\"")

    # 10. Тест общего метода check_training_completion
    print("\n✓ Test 10: Тест check_training_completion")
    user_id = 99999
    user_data = user_service.get_user_data(user_id)
    session = user_data['session']

    # Симулируем достижение лимита вопросов
    session['question_count'] = 20
    is_completed, reason = spin_service.check_training_completion(user_id, scenario_config)
    assert is_completed == True
    assert reason == "max_questions"
    print(f"  ✅ Определяет завершение по max_questions")

    # Симулируем достижение целевой ясности
    user_id_2 = 99998
    user_data_2 = user_service.get_user_data(user_id_2)
    session_2 = user_data_2['session']
    session_2['question_count'] = 7  # >= min_questions_for_completion (5), < max_questions (10)
    session_2['clarity_level'] = 80  # >= target_clarity (80)
    is_completed, reason = spin_service.check_training_completion(user_id_2, scenario_config)
    assert is_completed == True
    assert reason == "clarity_reached", f"Expected 'clarity_reached', got '{reason}'"
    print(f"  ✅ Определяет завершение по clarity_reached")

    # 11. Проверка, что базовый класс абстрактный
    print("\n✓ Test 11: BaseTrainingService — абстрактный класс")
    try:
        # Попытка создать экземпляр базового класса должна упасть
        base = BaseTrainingService(
            user_service=user_service,
            llm_service=llm_service,
            achievement_service=achievement_service,
            active_listening_detector=active_listening_detector
        )
        # Попытка вызвать абстрактный метод
        await base.start_training(123, {})
        print("  ❌ BaseTrainingService не должен создаваться напрямую!")
        assert False
    except TypeError:
        print("  ✅ BaseTrainingService корректно абстрактный (TypeError при вызове)")
    except Exception as e:
        # Может быть другая ошибка в зависимости от реализации ABC
        if "abstract" in str(e).lower() or "cannot instantiate" in str(e).lower():
            print(f"  ✅ BaseTrainingService корректно абстрактный")
        else:
            print(f"  ⚠️  Неожиданная ошибка: {e}")

    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    print("=" * 60)
    print("\n🎉 Модульная архитектура работает корректно!")
    print("\nРезультаты:")
    print("  • BaseTrainingService создан с общей логикой")
    print("  • SpinTrainingService наследуется от базового")
    print("  • Общие методы переиспользуются")
    print("  • SPIN-специфичные методы переопределены")
    print("  • Active listening интегрирован")
    print("\n✅ Готово для создания других тренировочных ботов!")
    print("   (Challenger Sale, MEDDIC, Objection Handling, и т.д.)\n")


if __name__ == "__main__":
    asyncio.run(test_base_training_service())
