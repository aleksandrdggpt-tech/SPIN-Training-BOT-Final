"""
Базовый сервис для управления тренировками.

Содержит общую логику, которая переиспользуется во всех тренировочных ботах:
- SPIN Sales Training
- Challenger Sale Training
- MEDDIC Training
- Objection Handling Training
- и др.

Наследуйте этот класс и переопределите методы для специфичной логики.
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .user_service import UserService
from .llm_service import LLMService
from .achievement_service import AchievementService

logger = logging.getLogger(__name__)


class BaseTrainingService(ABC):
    """
    Базовый сервис для всех тренировочных ботов.

    Содержит общую логику:
    - Управление пользователями
    - Интеграция с LLM
    - Проверка достижений
    - Активное слушание
    - Управление сессией

    Специфичная логика (переопределяется в наследниках):
    - Генерация кейсов (start_training)
    - Классификация вопросов (process_question)
    - Генерация ответов клиента (_generate_client_response)
    - Формирование промптов для фидбека (build_feedback_prompt)
    - Генерация отчетов (complete_training)
    """

    def __init__(
        self,
        user_service: UserService,
        llm_service: LLMService,
        achievement_service: AchievementService,
        active_listening_detector=None
    ):
        """
        Инициализация базового сервиса.

        Args:
            user_service: Сервис управления пользователями
            llm_service: Сервис LLM (OpenAI/Anthropic)
            achievement_service: Сервис достижений
            active_listening_detector: Детектор активного слушания (опционально)
        """
        self.user_service = user_service
        self.llm_service = llm_service
        self.achievement_service = achievement_service
        self.active_listening_detector = active_listening_detector

    # ==================== АБСТРАКТНЫЕ МЕТОДЫ ====================
    # Должны быть переопределены в наследниках

    @abstractmethod
    async def start_training(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Генерация нового кейса и начало тренировки.

        Специфично для каждой методологии:
        - SPIN: генерация B2B кейса с клиентом
        - Challenger: генерация кейса с insight
        - MEDDIC: генерация B2B сделки

        Args:
            user_id: ID пользователя
            scenario_config: Конфигурация сценария

        Returns:
            Текст кейса для пользователя
        """
        pass

    @abstractmethod
    async def process_question(
        self,
        user_id: int,
        question: str,
        scenario_config: Dict[str, Any]
    ) -> str:
        """
        Обработка вопроса/сообщения пользователя.

        Специфично для каждой методологии:
        - SPIN: классификация SPIN-вопросов
        - Challenger: оценка Teaching, Tailoring, Taking Control
        - MEDDIC: проверка Metrics, Economic Buyer, Decision Criteria, и т.д.

        Args:
            user_id: ID пользователя
            question: Вопрос/сообщение пользователя
            scenario_config: Конфигурация сценария

        Returns:
            Ответное сообщение с фидбеком
        """
        pass

    @abstractmethod
    async def build_feedback_prompt(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Формирует промпт для обратной связи.

        Специфично для каждой методологии.

        Args:
            user_id: ID пользователя
            scenario_config: Конфигурация сценария

        Returns:
            Промпт для LLM
        """
        pass

    @abstractmethod
    async def complete_training(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Завершение тренировки и генерация отчёта.

        Специфично для каждой методологии (разные метрики в отчете).

        Args:
            user_id: ID пользователя
            scenario_config: Конфигурация сценария

        Returns:
            Финальный отчет
        """
        pass

    # ==================== ОБЩИЕ МЕТОДЫ ====================
    # Переиспользуются всеми наследниками

    async def check_active_listening(
        self,
        question: str,
        last_response: str
    ) -> tuple[bool, str]:
        """
        Проверка активного слушания (общая для всех ботов).

        Args:
            question: Вопрос пользователя
            last_response: Последний ответ клиента

        Returns:
            (is_contextual, context_badge)
        """
        is_contextual = False
        context_badge = ""

        if self.active_listening_detector and last_response:
            is_contextual = await self.active_listening_detector.check_context_usage(
                question=question,
                last_response=last_response,
                call_llm_func=self.llm_service.call_llm
            )

        if is_contextual:
            context_badge = self.active_listening_detector.format_badge()

        return is_contextual, context_badge

    def apply_active_listening_bonus(
        self,
        session: Dict[str, Any],
        is_contextual: bool
    ) -> None:
        """
        Применяет бонус за активное слушание (общее для всех ботов).

        Args:
            session: Сессия пользователя
            is_contextual: Является ли вопрос контекстуальным
        """
        if is_contextual and self.active_listening_detector:
            session['contextual_questions'] = int(session.get('contextual_questions', 0)) + 1
            bonus_points = self.active_listening_detector.get_bonus_points()
            session['clarity_level'] = min(100, session.get('clarity_level', 0) + bonus_points)

    async def get_feedback(self, user_id: int, scenario_config: Dict[str, Any]) -> str:
        """
        Получение обратной связи по последнему вопросу (общее для всех ботов).

        Использует кэширование с TTL 20 минут.

        Args:
            user_id: ID пользователя
            scenario_config: Конфигурация сценария

        Returns:
            Сообщение с обратной связью
        """
        try:
            # Получаем данные пользователя
            user_data = self.user_service.get_user_data(user_id)
            session = user_data['session']

            if not session.get('last_question_type'):
                return 'Сначала задайте вопрос клиенту.'

            # Формируем промпт (специфичный для методологии)
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
                # Наследник должен форматировать сообщение
                return self._format_feedback_message(cached_text, scenario_config)

            # Получаем обратную связь через LLM
            feedback = await self.llm_service.call_llm('feedback', feedback_prompt, 'Проанализируй ситуацию')

            # Сохраняем в кэш
            session['feedback_cache'] = {
                'prompt_hash': prompt_hash,
                'ts': _time.time(),
                'text': feedback,
            }

            return self._format_feedback_message(feedback, scenario_config)

        except Exception as e:
            logger.error(f"Ошибка получения обратной связи: {e}")
            raise

    def check_training_completion(
        self,
        user_id: int,
        scenario_config: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Проверяет условия завершения тренировки (общее для всех ботов).

        Args:
            user_id: ID пользователя
            scenario_config: Конфигурация сценария

        Returns:
            (is_completed, completion_reason)
        """
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

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получить данные пользователя (общее)."""
        return self.user_service.get_user_data(user_id)

    def reset_session(self, user_id: int, scenario_config: Dict[str, Any]) -> None:
        """Сбросить сессию пользователя (общее)."""
        self.user_service.reset_session(user_id, scenario_config)

    def update_stats(self, user_id: int, total_score: int, scenario_config: Dict[str, Any]) -> None:
        """Обновить статистику пользователя (общее)."""
        self.user_service.update_stats(user_id, total_score, scenario_config)

    # ==================== ХЕЛПЕРЫ ====================
    # Могут быть переопределены в наследниках

    def _format_feedback_message(self, feedback: str, scenario_config: Dict[str, Any]) -> str:
        """
        Форматирует сообщение с обратной связью.

        По умолчанию возвращает просто текст фидбека.
        Наследники могут переопределить для добавления форматирования.
        """
        return f"💬 Обратная связь:\n\n{feedback}"
