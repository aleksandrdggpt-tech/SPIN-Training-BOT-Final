"""
UserService с поддержкой SQLAlchemy БД (упрощенная async версия).

Async методы для использования в bot.py (который уже async).
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select

from database import TrainingUser, TrainingHistory, get_session

logger = logging.getLogger(__name__)


class UserServiceDB:
    """
    Async сервис для управления пользователями с БД.
    """

    def __init__(self):
        """Инициализация сервиса."""
        # Кэш для производительности
        self._cache: Dict[int, Dict[str, Any]] = {}

    async def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получение данных пользователя с инициализацией session/stats.
        """
        # Проверяем кэш
        if user_id in self._cache:
            return self._cache[user_id]

        # Загружаем из БД
        async for session in get_session():
            # Ищем пользователя
            stmt = select(TrainingUser).where(TrainingUser.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                # Создаем нового пользователя
                user = TrainingUser(
                    telegram_id=user_id,
                    session_data=TrainingUser._get_default_session(),
                    stats_data=TrainingUser._get_default_stats()
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"Created new training user: {user_id}")

            # Обновляем last_activity
            user.last_activity = datetime.utcnow()
            await session.commit()

            user_data = user.to_dict()
            self._cache[user_id] = user_data
            return user_data

    async def save_user_data(self, user_id: int, user_data: Dict[str, Any]) -> None:
        """
        Сохранение данных пользователя в БД.

        Вызывайте после изменения session или stats.
        """
        async for session in get_session():
            stmt = select(TrainingUser).where(TrainingUser.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.session_data = user_data.get('session', {})
                user.stats_data = user_data.get('stats', {})
                await session.commit()

                # Обновляем кэш
                self._cache[user_id] = user_data
                logger.debug(f"Saved user data for {user_id}")

    async def reset_session(self, user_id: int, scenario_config: Dict[str, Any]) -> None:
        """Очистка данных текущей сессии."""
        async for session in get_session():
            stmt = select(TrainingUser).where(TrainingUser.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                user.session_data = {
                    'question_count': 0,
                    'clarity_level': 0,
                    'per_type_counts': {t['id']: 0 for t in scenario_config['question_types']},
                    'client_case': '',
                    'case_data': None,
                    'last_question_type': '',
                    'chat_state': 'waiting_start',
                    'contextual_questions': 0,
                    'last_client_response': '',
                    'context_streak': 0
                }
                await session.commit()

                # Обновляем кэш
                if user_id in self._cache:
                    self._cache[user_id]['session'] = user.session_data

                logger.info(f"Reset session for user {user_id}")

    async def update_stats(self, user_id: int, session_score: int, scenario_config: Dict[str, Any]) -> None:
        """Обновление общей статистики пользователя."""
        async for session in get_session():
            stmt = select(TrainingUser).where(TrainingUser.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User {user_id} not found for stats update")
                return

            # Получаем текущие данные
            session_data = user.session_data or {}
            stats_data = user.stats_data or TrainingUser._get_default_stats()

            # Обновляем статистику
            stats_data['total_trainings'] = stats_data.get('total_trainings', 0) + 1
            stats_data['total_questions'] = stats_data.get('total_questions', 0) + int(session_data.get('question_count', 0))
            stats_data['best_score'] = max(stats_data.get('best_score', 0), session_score)
            stats_data['last_training_date'] = datetime.now().isoformat()

            # XP и уровень
            stats_data['total_xp'] = stats_data.get('total_xp', 0) + session_score
            old_level = stats_data.get('current_level', 1)
            new_level = self._calculate_level(stats_data['total_xp'], scenario_config.get('ranking', {}).get('levels', []))
            stats_data['current_level'] = new_level

            # Серия Маэстро
            if session_score >= 221:
                stats_data['maestro_streak'] = stats_data.get('maestro_streak', 0) + 1
            else:
                stats_data['maestro_streak'] = 0

            # Уведомление о повышении уровня
            if new_level > old_level:
                stats_data['level_up_notification'] = {
                    'should_show': True,
                    'old_level': old_level,
                    'new_level': new_level
                }
                logger.info(f"🎊 Пользователь {user_id} повысил уровень: {old_level} → {new_level}")

            # Сохраняем в БД
            user.stats_data = stats_data
            await session.commit()

            # Обновляем кэш
            if user_id in self._cache:
                self._cache[user_id]['stats'] = stats_data

            # Сохраняем историю тренировки
            history = TrainingHistory(
                telegram_id=user_id,
                total_score=session_score,
                clarity_level=session_data.get('clarity_level', 0),
                question_count=session_data.get('question_count', 0),
                contextual_questions=session_data.get('contextual_questions', 0),
                per_type_counts=session_data.get('per_type_counts', {}),
                case_data=session_data.get('case_data'),
                session_snapshot=session_data
            )
            session.add(history)
            await session.commit()
            logger.info(f"Saved training history for user {user_id}, score: {session_score}")

    def _calculate_level(self, xp: int, levels: list) -> int:
        """Вычисляет уровень пользователя на основе XP."""
        try:
            eligible = [int(l.get('level', 1)) for l in levels if xp >= int(l.get('min_xp', 0))]
            return max(eligible) if eligible else 1
        except Exception:
            return 1

    async def has_user(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь."""
        async for session in get_session():
            stmt = select(TrainingUser).where(TrainingUser.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return user is not None

    def clear_cache(self) -> None:
        """Очистить кэш."""
        self._cache.clear()
        logger.info("User cache cleared")
