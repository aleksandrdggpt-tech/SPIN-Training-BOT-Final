"""
SPIN Training Service - специфичная реализация для тренировки SPIN-продаж.

Наследуется от BaseTrainingService и переопределяет методы для SPIN-методологии:
- Генерация B2B кейсов с клиентом
- Классификация SPIN-вопросов (Situational, Problem, Implication, Need-Payoff)
- Генерация ответов клиента с учетом SPIN-логики
- Формирование отчетов по SPIN-метрикам
"""

import logging
from typing import Dict, Any

from .base_training_service import BaseTrainingService
from .user_service import UserService
from .llm_service import LLMService
from .achievement_service import AchievementService
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator
from engine.scenario_loader import ScenarioLoader

logger = logging.getLogger(__name__)


class SpinTrainingService(BaseTrainingService):
    """
    SPIN Training Service.

    Специфичная реализация для тренировки SPIN-продаж.
    """

    def __init__(
        self,
        user_service: UserService,
        llm_service: LLMService,
        achievement_service: AchievementService,
        question_analyzer: QuestionAnalyzer,
        report_generator: ReportGenerator,
        case_generator: CaseGenerator,
        scenario_loader: ScenarioLoader,
        active_listening_detector=None
    ):
        """
        Инициализация SPIN Training Service.

        Args:
            user_service: Сервис управления пользователями
            llm_service: Сервис LLM
            achievement_service: Сервис достижений
            question_analyzer: Анализатор SPIN-вопросов
            report_generator: Генератор SPIN-отчетов
            case_generator: Генератор B2B кейсов
            scenario_loader: Загрузчик сценариев
            active_listening_detector: Детектор активного слушания
        """
        # Инициализация базового класса
        super().__init__(
            user_service=user_service,
            llm_service=llm_service,
            achievement_service=achievement_service,
            active_listening_detector=active_listening_detector
        )

        # SPIN-специфичные компоненты
        self.question_analyzer = question_analyzer
        self.report_generator = report_generator
        self.case_generator = case_generator
        self.scenario_loader = scenario_loader

    # ==================== SPIN-СПЕЦИФИЧНЫЕ МЕТОДЫ ====================

    async def start_training(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Генерация нового B2B кейса и начало SPIN-тренировки.

        Args:
            user_id: ID пользователя
            scenario_config: SPIN scenario configuration

        Returns:
            Текст B2B кейса для пользователя
        """
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            stats = user_data['stats']

            # Получаем список недавних кейсов для исключения повторов
            recent_cases = stats.get('recent_cases', [])

            # Генерируем случайный уникальный кейс
            case_data = self.case_generator.generate_random_case(exclude_recent=recent_cases)

            # Сохраняем данные кейса в сессию
            session = user_data['session']
            session['case_data'] = case_data

            # Генерируем кейс напрямую без GPT (мгновенно)
            client_case = self.case_generator.build_case_direct(case_data)

            # Сохраняем сгенерированный кейс
            session['client_case'] = client_case
            session['chat_state'] = 'training_active'

            # Добавляем хеш кейса в историю
            case_hash = self.case_generator._get_case_hash(case_data)
            recent_cases.append(case_hash)
            if len(recent_cases) > 5:
                recent_cases.pop(0)
            stats['recent_cases'] = recent_cases

            # Логируем статистику кейса
            logger.info(f"""
            === SPIN КЕЙС СГЕНЕРИРОВАН ===
            User ID: {user_id}
            Должность: {case_data['position']}
            Компания: {case_data['company']['type']}
            Продукт: {case_data['product']['name']}
            ====================================
            """)
            
            # ВАЖНО: Сохраняем обновленную сессию в БД
            if hasattr(self.user_service, 'save_user_data'):
                self.user_service.save_user_data(user_id, session, stats)

            return client_case

        except Exception as e:
            logger.error(f"Ошибка генерации SPIN кейса: {e}")
            raise

    async def process_question(
        self,
        user_id: int,
        question: str,
        scenario_config: Dict[str, Any]
    ) -> str:
        """
        Обработка SPIN-вопроса пользователя.

        Классифицирует вопрос на: Situational, Problem, Implication, Need-Payoff.

        Args:
            user_id: ID пользователя
            question: SPIN-вопрос пользователя
            scenario_config: SPIN scenario configuration

        Returns:
            Ответное сообщение с классификацией и ответом клиента
        """
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']
            rules = scenario_config['game_rules']

            # Определяем тип SPIN-вопроса через анализатор
            qtype = await self.question_analyzer.classify_question(
                question,
                scenario_config['question_types'],
                session.get('client_case', ''),
                lambda kind, sys, usr: self.llm_service.call_llm(kind, sys, usr),
                scenario_config.get('prompts', {})
            )
            question_type_name = qtype.get('name', qtype.get('id'))

            # Обновляем счетчики
            session['question_count'] += 1
            session['last_question_type'] = question_type_name

            qid = qtype.get('id')
            session['per_type_counts'][qid] = int(session['per_type_counts'].get(qid, 0)) + 1
            session['clarity_level'] += self.question_analyzer.calculate_clarity_increase(qtype)
            session['clarity_level'] = min(session['clarity_level'], 100)

            # Генерируем ответ клиента (SPIN-специфичная логика)
            client_response = await self._generate_client_response(session, question)

            # Проверяем активное слушание (общий метод из базового класса)
            last_resp = session.get('last_client_response', '')
            is_contextual, context_badge = await self.check_active_listening(question, last_resp)

            # Применяем бонус (общий метод из базового класса)
            self.apply_active_listening_bonus(session, is_contextual)

            # Сохраняем последний ответ клиента
            session['last_client_response'] = client_response

            # Формируем ответное сообщение
            progress_line = self.scenario_loader.get_message(
                'progress',
                count=session['question_count'],
                max=rules['max_questions'],
                clarity=session['clarity_level']
            )

            response_message = self.scenario_loader.get_message(
                'question_feedback',
                question_type=question_type_name + context_badge,
                client_response=client_response,
                progress_line=progress_line
            )
            
            # ВАЖНО: Сохраняем обновленную сессию в БД
            if hasattr(self.user_service, 'save_user_data'):
                self.user_service.save_user_data(user_id, session, user_data['stats'])

            return response_message

        except Exception as e:
            logger.error(f"Ошибка обработки SPIN-вопроса: {e}")
            raise

    async def build_feedback_prompt(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Формирует промпт для обратной связи по SPIN-вопросам.

        Args:
            user_id: ID пользователя
            scenario_config: SPIN scenario configuration

        Returns:
            Промпт для LLM с SPIN-контекстом
        """
        user_data = self.user_service.get_user_data(user_id)
        session = user_data['session']

        if not session.get('last_question_type'):
            return 'Сначала задайте вопрос клиенту.'

        per_type = session.get('per_type_counts', {})
        situational_q = int(per_type.get('situational', 0))
        problem_q = int(per_type.get('problem', 0))
        implication_q = int(per_type.get('implication', 0))
        need_payoff_q = int(per_type.get('need_payoff', 0))

        return self.scenario_loader.get_prompt(
            'feedback',
            last_question_type=session['last_question_type'],
            question_count=session['question_count'],
            clarity_level=session['clarity_level'],
            situational_q=situational_q,
            problem_q=problem_q,
            implication_q=implication_q,
            need_payoff_q=need_payoff_q,
        )

    async def complete_training(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Завершение SPIN-тренировки и генерация отчёта.

        Args:
            user_id: ID пользователя
            scenario_config: SPIN scenario configuration

        Returns:
            Финальный SPIN-отчет
        """
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']
            stats = user_data['stats']

            # Подсчитываем общий балл (SPIN-специфичный)
            total_score = self.question_analyzer.calculate_score(session, scenario_config['question_types'])

            # Обновляем статистику (общий метод)
            self.update_stats(user_id, total_score, scenario_config)

            # ВАЖНО: Перечитываем данные после update_stats, так как он мог изменить stats
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']
            stats = user_data['stats']

            # Проверяем достижения
            achievements = scenario_config.get('achievements', {}).get('list', [])
            newly_unlocked = self.achievement_service.check_achievements_with_config(
                user_id, session, stats, achievements
            )

            # ВАЖНО: Сохраняем разблокированные достижения в БД ПЕРЕД сбросом сессии
            if newly_unlocked or stats.get('level_up_notification', {}).get('should_show'):
                if hasattr(self.user_service, 'save_user_data'):
                    self.user_service.save_user_data(user_id, session, stats)
                    if newly_unlocked:
                        logger.info(f"🎖️ Сохранено достижений: {len(newly_unlocked)}")

            # Подготавливаем данные для SPIN-отчёта
            report_data = {
                'session': session,
                'stats': stats,
                'case_data': session.get('case_data'),
                'total_score': total_score,
                'achievements': newly_unlocked,
                'level_up': stats.get('level_up_notification'),
            }

            # Генерируем SPIN-отчёт
            report = self.report_generator.generate_final_report(report_data, scenario_config)

            # Диагностика наличия промо-блока
            try:
                if 'Тактика Кутузова' in report or 'TaktikaKutuzova' in report:
                    logger.info("SPIN report: promo block PRESENT")
                else:
                    logger.warning("SPIN report: promo block MISSING")
            except Exception:
                pass

            # Сбрасываем сессию (общий метод) - это НЕ затирает достижения в stats!
            self.reset_session(user_id, scenario_config)

            return report

        except Exception as e:
            logger.error(f"Ошибка завершения SPIN-тренировки: {e}")
            raise

    # ==================== ПРИВАТНЫЕ МЕТОДЫ ====================

    async def _generate_client_response(self, session: Dict[str, Any], question: str) -> str:
        """
        Генерирует ответ клиента на SPIN-вопрос.

        Использует данные кейса и SPIN-принципы ответов.

        Args:
            session: Сессия пользователя
            question: SPIN-вопрос

        Returns:
            Ответ клиента
        """
        case_data = session.get('case_data') or {}

        enriched_prompt = (
            f"Вы клиент из кейса со следующими параметрами:\n\n"
            f"РОЛЬ: {case_data.get('position', '')} в компании \"{(case_data.get('company') or {}).get('type', '')}\"\n"
            f"КОНТЕКСТ: {session.get('client_case', '')}\n\n"
            f"ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:\n"
            f"- Объём закупок: {case_data.get('volume', '')}\n"
            f"- Частота: {case_data.get('frequency', '')}\n"
            f"- Количество поставщиков: {case_data.get('suppliers_count', '')}\n"
            f"- Тип ситуации: {(case_data.get('situation') or {}).get('type', '')}\n"
            f"- Характер закупки: {case_data.get('urgency', '')}\n\n"
            f"ПРИНЦИПЫ ОТВЕТОВ (SPIN):\n"
            f"- Отвечайте нейтрально и сдержанно, как реальный занятой руководитель\n"
            f"- НЕ раскрывайте проблемы сами - только на конкретные SPIN-вопросы\n"
            f"- На ситуационные вопросы: давайте факты и цифры\n"
            f"- На проблемные: признавайте проблемы, но не драматизируйте\n"
            f"- На извлекающие: раскрывайте последствия постепенно, намёками\n"
            f"- На направляющие: подтверждайте ценность предложенных решений\n\n"
            f"СТИЛЬ: Короткие реалистичные ответы (2-4 предложения), профессиональный тон.\n\n"
            f"Вопрос продавца: {question}"
        )

        return await self.llm_service.call_llm('response', enriched_prompt, "Ответь на вопрос как клиент")

    def _format_feedback_message(self, feedback: str, scenario_config: Dict[str, Any]) -> str:
        """
        Форматирует сообщение с обратной связью (SPIN-специфичное).

        Переопределяет базовый метод для использования scenario_loader.

        Args:
            feedback: Текст обратной связи
            scenario_config: SPIN scenario configuration

        Returns:
            Отформатированное сообщение
        """
        return self.scenario_loader.get_message(
            'feedback_response',
            feedback=feedback
        )
