"""
Координирующий сервис для управления тренировками.
Объединяет все остальные сервисы для выполнения тренировочных операций.
"""

import logging
from typing import Dict, Any

from .user_service import UserService
from .llm_service import LLMService
from .achievement_service import AchievementService
from engine.question_analyzer import QuestionAnalyzer
from engine.report_generator import ReportGenerator
from engine.case_generator import CaseGenerator
from engine.scenario_loader import ScenarioLoader

logger = logging.getLogger(__name__)


class TrainingService:
    """Координирующий сервис для управления тренировками."""

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
        """Инициализация сервиса с зависимостями."""
        self.user_service = user_service
        self.llm_service = llm_service
        self.achievement_service = achievement_service
        self.question_analyzer = question_analyzer
        self.report_generator = report_generator
        self.case_generator = case_generator
        self.scenario_loader = scenario_loader
        self.active_listening_detector = active_listening_detector

    async def start_training(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """Генерация нового кейса и начало тренировки."""
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
            === КЕЙС СГЕНЕРИРОВАН МГНОВЕННО ===
            Метод: Прямая подстановка (без GPT)
            User ID: {user_id}
            Должность: {case_data['position']}
            Компания: {case_data['company']['type']}
            Продукт: {case_data['product']['name']}
            Время генерации: < 0.001 сек
            ====================================
            """)

            return client_case

        except Exception as e:
            logger.error(f"Ошибка генерации кейса: {e}")
            raise

    async def process_question(
        self,
        user_id: int,
        question: str,
        scenario_config: Dict[str, Any]
    ) -> str:
        """Обработка вопроса пользователя."""
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']
            rules = scenario_config['game_rules']

            # Определяем тип вопроса через анализатор
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

            # Генерируем ответ клиента с учетом данных кейса
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
                f"ПРИНЦИПЫ ОТВЕТОВ:\n"
                f"- Отвечайте нейтрально и сдержанно, как реальный занятой руководитель\n"
                f"- НЕ раскрывайте проблемы сами - только на конкретные SPIN-вопросы\n"
                f"- На ситуационные вопросы: давайте факты и цифры\n"
                f"- На проблемные: признавайте проблемы, но не драматизируйте\n"
                f"- На извлекающие: раскрывайте последствия постепенно, намёками\n"
                f"- На направляющие: подтверждайте ценность предложенных решений\n\n"
                f"СТИЛЬ: Короткие реалистичные ответы (2-4 предложения), профессиональный тон.\n\n"
                f"Вопрос продавца: {question}"
            )
            client_response = await self.llm_service.call_llm('response', enriched_prompt, "Ответь на вопрос как клиент")

            # Проверяем контекстуальность вопроса (активное слушание)
            is_contextual = False
            last_resp = session.get('last_client_response', '')

            if self.active_listening_detector and last_resp:
                is_contextual = await self.active_listening_detector.check_context_usage(
                    question=question,
                    last_response=last_resp,
                    call_llm_func=self.llm_service.call_llm
                )

            context_badge = ""
            if is_contextual:
                session['contextual_questions'] = int(session.get('contextual_questions', 0)) + 1
                bonus_points = self.active_listening_detector.get_bonus_points()
                session['clarity_level'] = min(100, session['clarity_level'] + bonus_points)
                context_badge = self.active_listening_detector.format_badge()
                # Вернет: " 👂 (Успешное активное слушание)"

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

            return response_message

        except Exception as e:
            logger.error(f"Ошибка обработки вопроса: {e}")
            raise

    async def get_feedback(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """Получение обратной связи по последнему вопросу."""
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']

            if not session['last_question_type']:
                return 'Сначала задайте вопрос клиенту.'

            feedback_prompt = await self.build_feedback_prompt(user_id, scenario_config)

            # TTL-кэш фидбека на сессию пользователя (20 минут)
            import time as _time, hashlib as _hashlib
            ttl_sec = 20 * 60
            cache = session.get('feedback_cache') or {}
            prompt_hash = _hashlib.sha256(feedback_prompt.encode('utf-8')).hexdigest()
            cached_hash = cache.get('prompt_hash')
            cached_ts = float(cache.get('ts') or 0)
            cached_text = cache.get('text')
            if cached_hash == prompt_hash and (_time.time() - cached_ts) < ttl_sec and cached_text:
                logger.info("Feedback cache hit")
                return self.scenario_loader.get_message('feedback_response', feedback=cached_text)

            # Получаем обратную связь через LLM
            feedback = await self.llm_service.call_llm('feedback', feedback_prompt, 'Проанализируй ситуацию')

            # Формируем сообщение с обратной связью
            feedback_message = self.scenario_loader.get_message(
                'feedback_response',
                feedback=feedback
            )

            # Сохраняем в кэш
            session['feedback_cache'] = {
                'prompt_hash': prompt_hash,
                'ts': _time.time(),
                'text': feedback,
            }

            return feedback_message

        except Exception as e:
            logger.error(f"Ошибка получения обратной связи: {e}")
            raise

    async def build_feedback_prompt(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """Формирует промпт для обратной связи (используется и для стриминга)."""
        user_data = self.user_service.get_user_data(user_id)
        session = user_data['session']
        if not session['last_question_type']:
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
        """Завершение тренировки и генерация отчёта."""
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']
            stats = user_data['stats']

            # Подсчитываем общий балл
            total_score = self.question_analyzer.calculate_score(session, scenario_config['question_types'])

            # Обновляем статистику
            self.user_service.update_stats(user_id, total_score, scenario_config)

            # Проверяем достижения
            achievements = scenario_config.get('achievements', {}).get('list', [])
            newly_unlocked = self.achievement_service.check_achievements_with_config(
                user_id, session, stats, achievements
            )

            # Подготавливаем данные для отчёта
            user_with_id = user_data.copy()
            user_with_id['user_id'] = user_id

            report_data = {
                'session': session,
                'stats': stats,
                'case_data': session.get('case_data'),
                'total_score': total_score,
                'achievements': newly_unlocked,
                'level_up': stats.get('level_up_notification'),
            }

            # Генерируем отчёт
            report = self.report_generator.generate_final_report(report_data, scenario_config)

            # Диагностика наличия промо-блока
            try:
                if 'Тактика Кутузова' in report or 'TaktikaKutuzova' in report:
                    logger.info("Final report: promo block PRESENT")
                else:
                    logger.warning("Final report: promo block MISSING")
            except Exception:
                pass

            # Сбрасываем сессию
            self.user_service.reset_session(user_id, scenario_config)

            return report

        except Exception as e:
            logger.error(f"Ошибка завершения тренировки: {e}")
            raise

    def check_training_completion(self, user_id: int, scenario_config: Dict[str, Any]) -> tuple[bool, str]:
        """Проверяет условия завершения тренировки."""
        user_data = self.user_service.get_user_data(user_id)
        session = user_data['session']
        rules = scenario_config['game_rules']

        # Проверяем максимальное количество вопросов
        if session['question_count'] >= rules['max_questions']:
            return True, "max_questions"

        # Проверяем достижение целевой ясности
        if (session['clarity_level'] >= rules['target_clarity'] and
            session['question_count'] >= rules['min_questions_for_completion']):
            return True, "clarity_reached"

        return False, ""
