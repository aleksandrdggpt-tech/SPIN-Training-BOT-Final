"""
UserService с PostgreSQL/SQLAlchemy БД.

Адаптер над DatabaseService для обратной совместимости с UserServicePersistent API.
Этот класс позволяет использовать PostgreSQL без изменения bot.py.
"""

import logging
from typing import Dict, Any
import asyncio
import nest_asyncio

from .database_service import DatabaseService

logger = logging.getLogger(__name__)


class UserServiceDB:
    """
    UserService с БД, совместимый с UserServicePersistent API.

    Этот класс - адаптер, который:
    1. Предоставляет те же методы, что и UserServicePersistent
    2. Внутри использует DatabaseService
    3. Конвертирует sync вызовы в async (для совместимости)
    """

    def __init__(self, bot_name: str = "spin_bot"):
        """
        Инициализация сервиса.

        Args:
            bot_name: Имя бота для изоляции данных
        """
        self.db_service = DatabaseService(bot_name=bot_name)
        logger.info(f"UserServiceDB initialized with bot_name={bot_name}")

    def _run_async(self, coro):
        """
        Helper для запуска async функций в sync контексте.
        
        Использует nest_asyncio для поддержки вложенных event loops.
        
        Args:
            coro: Coroutine to run

        Returns:
            Result of coroutine
        """
        # Применяем nest_asyncio для поддержки вложенных run()
        # Временно патчим asyncio
        nest_asyncio.apply()
        
        try:
            # Пытаемся использовать asyncio.run()
            # nest_asyncio должен разрешить это даже в запущенном loop
            return asyncio.run(coro)
        finally:
            # Возвращаем asyncio к исходному состоянию
            # (опционально, nest_asyncio обычно глобально применяется)
            pass

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """
        Получение данных пользователя с инициализацией session/stats.

        Args:
            user_id: Telegram user ID

        Returns:
            dict with 'session' and 'stats' keys
        """
        result = self._run_async(self.db_service.get_user_session(user_id))

        # Конвертируем формат DatabaseService -> UserServicePersistent формат
        return {
            'session': result['session'],
            'stats': result['stats']
        }
    
    def save_user_data(self, user_id: int, session_data: Dict[str, Any], stats_data: Dict[str, Any]) -> None:
        """
        Сохранение данных пользователя.

        Args:
            user_id: Telegram user ID
            session_data: Session data
            stats_data: Stats data
        """
        self._run_async(self.db_service.save_session(user_id, session_data, stats_data))

    def reset_session(self, user_id: int, scenario_config: Dict[str, Any]) -> None:
        """
        Очистка данных текущей сессии и возврат в ожидание старта.

        Args:
            user_id: Telegram user ID
            scenario_config: Scenario configuration
        """
        # Get current data
        user_data = self.get_user_data(user_id)

        # Reset session to default
        user_data['session'] = {
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

        # Save back
        self._run_async(self.db_service.save_session(
            user_id,
            user_data['session'],
            user_data['stats']
        ))

        logger.info(f"Reset session for user {user_id}")

    def update_stats(self, user_id: int, session_score: int, scenario_config: Dict[str, Any]) -> None:
        """
        Обновление общей статистики пользователя на основе завершенной сессии.

        Args:
            user_id: Telegram user ID
            session_score: Score from completed session
            scenario_config: Scenario configuration
        """
        # Get current data
        user_data = self.get_user_data(user_id)
        s = user_data['session']
        st = user_data['stats']

        # Update stats
        st['total_trainings'] = st.get('total_trainings', 0) + 1
        st['total_questions'] = st.get('total_questions', 0) + int(s.get('question_count', 0))
        st['best_score'] = max(int(st.get('best_score', 0)), int(session_score))

        from datetime import datetime
        st['last_training_date'] = datetime.now().isoformat()

        # XP and level
        st['total_xp'] = st.get('total_xp', 0) + session_score
        old_level = st.get('current_level', 1)

        # Calculate new level using DatabaseService
        level_result = self._run_async(
            self.db_service.add_xp_and_check_level_up(
                user_id,
                session_score,
                scenario_config.get('ranking', {}).get('levels', [])
            )
        )

        new_level = level_result['new_level']
        st['current_level'] = new_level

        # Maestro streak
        if session_score >= 221:
            st['maestro_streak'] = st.get('maestro_streak', 0) + 1
        else:
            st['maestro_streak'] = 0

        # Level up notification
        if new_level > old_level:
            st['level_up_notification'] = {
                'should_show': True,
                'old_level': old_level,
                'new_level': new_level
            }
            logger.info(f"🎊 Пользователь {user_id} повысил уровень: {old_level} → {new_level}")

        # Save updated stats
        self._run_async(self.db_service.save_session(
            user_id,
            user_data['session'],
            st
        ))

        # Save training history
        self._run_async(self.db_service.save_training_history(
            telegram_id=user_id,
            total_score=session_score,
            clarity_level=s.get('clarity_level', 0),
            question_count=s.get('question_count', 0),
            contextual_questions=s.get('contextual_questions', 0),
            per_type_counts=s.get('per_type_counts', {}),
            case_data=s.get('case_data'),
            session_snapshot=s,
            scenario_name=scenario_config.get('id', 'unknown')
        ))

        # Update user-level stats
        self._run_async(self.db_service.update_user_stats_after_training(
            user_id,
            session_score,
            scenario_config
        ))

        logger.info(f"Updated stats for user {user_id}, score: {session_score}")

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """
        Получает данные пользователя по ID (для совместимости).

        Args:
            user_id: Telegram user ID

        Returns:
            User data
        """
        return self.get_user_data(user_id)

    def has_user(self, user_id: int) -> bool:
        """
        Проверяет, существует ли пользователь.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user exists
        """
        try:
            self.get_user_data(user_id)
            return True
        except Exception:
            return False

    def get_all_users(self) -> Dict[int, Dict[str, Any]]:
        """
        Возвращает всех пользователей (для отладки).

        Note: This is not efficient for large databases.
        Use DatabaseService.get_leaderboard() instead.

        Returns:
            Dict of user_id -> user_data
        """
        logger.warning("get_all_users() is not efficient with database storage")
        return {}

    def save_now(self) -> None:
        """
        Принудительное сохранение (для совместимости).

        С БД не требуется, так как данные сохраняются сразу.
        """
        logger.info("save_now() called (no-op with database storage)")
        pass
