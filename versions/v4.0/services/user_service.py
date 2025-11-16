"""
Сервис для управления пользователями и их данными.
Содержит логику работы с сессиями, статистикой и состояниями пользователей.
"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для управления пользователями."""

    def __init__(self):
        """Инициализация сервиса."""
        self._user_data: Dict[int, Dict[str, Any]] = {}

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        """Получение данных пользователя с инициализацией session/stats."""
        if user_id not in self._user_data:
            self._user_data[user_id] = self._init_user_data()
        return self._user_data[user_id]

    def _init_user_data(self) -> Dict[str, Any]:
        """Инициализирует структуру данных нового пользователя."""
        return {
            'session': {
                'question_count': 0,
                'clarity_level': 0,
                'per_type_counts': {},
                'client_case': '',
                'case_data': None,  # Сохраним данные кейса
                'last_question_type': '',
                'chat_state': 'new',
                'contextual_questions': 0,
                'last_client_response': '',
                'context_streak': 0
            },
            'stats': {
                'total_trainings': 0,
                'total_questions': 0,
                'best_score': 0,
                'total_xp': 0,
                'current_level': 1,
                'achievements_unlocked': [],
                'level_up_notification': {
                    'should_show': False,
                    'old_level': 1,
                    'new_level': 1
                },
                'maestro_streak': 0,
                'last_training_date': None
            }
        }

    def reset_session(self, user_id: int, scenario_config: Dict[str, Any]) -> None:
        """Очистка данных текущей сессии и возврат в ожидание старта."""
        u = self.get_user_data(user_id)
        u['session'] = {
            'question_count': 0,
            'clarity_level': 0,
            'per_type_counts': {t['id']: 0 for t in scenario_config['question_types']},
            'client_case': '',
            'case_data': None,  # Очищаем данные кейса
            'last_question_type': '',
            'chat_state': 'waiting_start',
            'contextual_questions': 0,
            'last_client_response': '',
            'context_streak': 0
        }

    def update_stats(self, user_id: int, session_score: int, scenario_config: Dict[str, Any]) -> None:
        """Обновление общей статистики пользователя на основе завершенной сессии."""
        u = self.get_user_data(user_id)
        s = u['session']
        st = u['stats']

        # Базовая статистика
        st['total_trainings'] += 1
        st['total_questions'] += int(s.get('question_count', 0))
        st['best_score'] = max(int(st.get('best_score', 0)), int(session_score))
        st['last_training_date'] = datetime.now().isoformat()

        # XP и уровень
        st['total_xp'] = int(st.get('total_xp', 0)) + int(session_score)
        old_level = int(st.get('current_level', 1))
        new_level = self._calculate_level(int(st['total_xp']), scenario_config.get('ranking', {}).get('levels', []))
        st['current_level'] = new_level

        # Серия Маэстро
        if int(session_score) >= 221:
            st['maestro_streak'] = int(st.get('maestro_streak', 0)) + 1
        else:
            st['maestro_streak'] = 0

        # Уведомление о повышении уровня
        if new_level > old_level:
            st['level_up_notification'] = {
                'should_show': True,
                'old_level': old_level,
                'new_level': new_level
            }
            logger.info(f"🎊 Пользователь {user_id} повысил уровень: {old_level} → {new_level}")

    def _calculate_level(self, xp: int, levels: list) -> int:
        """Вычисляет уровень пользователя на основе XP."""
        try:
            eligible = [int(l.get('level', 1)) for l in levels if xp >= int(l.get('min_xp', 0))]
            return max(eligible) if eligible else 1
        except Exception:
            return 1

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        """Получает данные пользователя по ID (для совместимости)."""
        return self.get_user_data(user_id)

    def has_user(self, user_id: int) -> bool:
        """Проверяет, существует ли пользователь."""
        return user_id in self._user_data

    def get_all_users(self) -> Dict[int, Dict[str, Any]]:
        """Возвращает всех пользователей (для отладки)."""
        return self._user_data.copy()
