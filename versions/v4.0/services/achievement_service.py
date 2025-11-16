"""
Сервис для работы с достижениями и уровнями пользователей.
Содержит логику проверки достижений и расчета уровней.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AchievementService:
    """Сервис для работы с достижениями и уровнями."""

    def __init__(self):
        """Инициализация сервиса."""
        pass

    def calculate_level(self, xp: int, levels: List[Dict]) -> int:
        """Определение уровня по опыту."""
        try:
            for lvl in sorted(levels, key=lambda l: int(l.get('min_xp', 0))):
                if xp < int(lvl.get('min_xp', 0)):
                    break
            # Найти максимальный уровень, чей min_xp <= xp
            eligible = [int(l.get('level', 1)) for l in levels if xp >= int(l.get('min_xp', 0))]
            return max(eligible) if eligible else 1
        except Exception:
            return 1

    def check_achievements(
        self,
        user_id: int,
        session: Dict[str, Any],
        stats: Dict[str, Any],
        achievements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Проверка и разблокировка достижений."""
        # Создаем контекст для eval с данными из сессии и статистики
        eval_context = stats.copy()
        eval_context.update({
            'question_count': session.get('question_count', 0),
            'contextual_questions': session.get('contextual_questions', 0),
            'last_contextual_questions': session.get('contextual_questions', 0),
        })

        newly_unlocked = []
        for ach in achievements:
            if ach.get('id') in stats.get('achievements_unlocked', []):
                continue
            condition = ach.get('condition', '')
            try:
                if eval(condition, {"__builtins__": {}}, eval_context):
                    stats['achievements_unlocked'].append(ach['id'])
                    newly_unlocked.append(ach)
                    logger.info(f"🎖️ Достижение разблокировано: {ach.get('name')}")
            except Exception as e:
                logger.error(f"Ошибка проверки достижения {ach.get('id')}: {e}")
        return newly_unlocked

    def get_newly_unlocked_achievements(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Получение новых достижений для отчёта."""
        user_id = user.get('user_id')  # Нужно передавать user_id в user
        if not user_id:
            return []

        # Получаем данные пользователя
        session = user.get('session', {})
        stats = user.get('stats', {})

        # Получаем конфигурацию достижений из сценария
        # Это должно передаваться извне, но для совместимости оставим как есть
        achievements = []  # Будет передаваться извне

        # Проверяем и разблокируем достижения
        newly_unlocked = self.check_achievements(user_id, session, stats, achievements)

        # Сбрасываем флаг показа уведомления о повышении уровня
        if stats.get('level_up_notification', {}).get('should_show'):
            stats['level_up_notification']['should_show'] = False

        return newly_unlocked

    def check_achievements_with_config(
        self,
        user_id: int,
        session: Dict[str, Any],
        stats: Dict[str, Any],
        achievements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Проверка достижений с передачей конфигурации достижений."""
        return self.check_achievements(user_id, session, stats, achievements)
