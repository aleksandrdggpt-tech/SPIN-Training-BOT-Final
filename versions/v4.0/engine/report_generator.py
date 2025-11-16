from typing import Any, Dict, List


class ReportGenerator:
    """Generates complete final report with all sections."""

    def get_badge(self, score: int, badges: List[Dict[str, Any]]) -> str:
        for b in badges:
            min_score = int(b.get("min_score", 0))
            max_score = int(b.get("max_score", 999999))
            if min_score <= score <= max_score:
                name = b.get("name", "")
                emoji = b.get("emoji", "")
                return f"{emoji} {name}".strip()
        return ""

    def get_recommendations(self, user_stats: Dict[str, Any], config: Dict[str, Any]) -> List[str]:
        recs: List[str] = []
        per_type = user_stats.get("per_type_counts", {})
        clarity = int(user_stats.get("clarity_level", 0))

        # Basic heuristics similar to the legacy implementation
        if per_type.get("situational", 0) > (per_type.get("problem", 0) or 0) * 2:
            recs.append("• Сокращайте количество ситуационных вопросов")
        if (per_type.get("problem", 0) or 0) == 0:
            recs.append("• Обязательно задавайте проблемные вопросы для выявления потребностей")
        if (per_type.get("implication", 0) or 0) == 0:
            recs.append("• Используйте извлекающие вопросы для развития проблем")
        if (per_type.get("need_payoff", 0) or 0) == 0:
            recs.append("• Добавьте направляющие вопросы для обсуждения выгод решения")
        if clarity < 50:
            recs.append("• Глубже исследуйте потребности клиента")

        if not recs:
            recs.append("• Отличная работа! Все типы вопросов использованы правильно.")
        return recs

    def generate_final_report(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Генерирует ПОЛНЫЙ финальный отчёт со всеми секциями."""
        sections = []

        # 1. Базовые результаты
        sections.append(self._format_basic_results(data, config))

        # 2. Общая статистика
        sections.append(self._format_overall_stats(data['stats']))

        # 3. Активное слушание
        sections.append(self._format_listening_stats(data['session']))

        # 4. Ранг и XP
        sections.append(self._format_rank_info(data['stats'], config))

        # 5. Уведомление о повышении уровня
        level_up = data.get('level_up')
        if level_up and level_up.get('should_show'):
            sections.append(self._format_level_up(level_up, config))

        # 6. Новые достижения
        if data.get('achievements'):
            sections.append(self._format_achievements(data['achievements']))

        # 7. Призыв к действию + промо
        sections.append(self._format_footer(config))

        return "\n\n".join(sections)

    def _format_basic_results(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Базовые результаты тренировки."""
        session = data['session']
        scoring = config.get("scoring", {})
        badges = scoring.get("badges", [])
        total_score = int(data.get('total_score', 0))

        badge = self.get_badge(total_score, badges)
        recs = self.get_recommendations(session, config)

        lines: List[str] = []
        lines.append("🏁 ТРЕНИРОВКА ЗАВЕРШЕНА!")
        lines.append("")
        lines.append("📊 РЕЗУЛЬТАТЫ:")
        lines.append(f"Задано вопросов: {session.get('question_count', 0)}/{config['game_rules']['max_questions']}")
        lines.append(f"Уровень ясности: {session.get('clarity_level', 0)}%")
        lines.append("")
        lines.append("📈 ПО ТИПАМ:")

        per_type_counts = session.get("per_type_counts", {})
        type_names = {t["id"]: t.get("name", t["id"]) for t in config.get("question_types", [])}
        type_emojis = {t["id"]: t.get("emoji", "") for t in config.get("question_types", [])}
        for tid, count in per_type_counts.items():
            name = type_names.get(tid, tid)
            emoji = type_emojis.get(tid, "")
            lines.append(f"{emoji} {name}: {count}")

        lines.append("")
        lines.append(f"🏅 Ваш результат: {badge}")
        lines.append(f"Общий балл: {total_score}")
        lines.append("")
        lines.append("💡 РЕКОМЕНДАЦИИ:")
        lines.append("\n".join(recs))

        return "\n".join(lines)

    def _format_case_info(self, case_data: Dict[str, Any]) -> str:
        """Информация о кейсе."""
        return f"""📋 ИНФОРМАЦИЯ О КЕЙСЕ:
Должность: {case_data['position']}
Компания: {case_data['company']['type']}
Продукт: {case_data['product']['name']}
Объём: {case_data['volume']}"""

    def _format_overall_stats(self, stats: Dict[str, Any]) -> str:
        """Общая статистика пользователя."""
        return f"""📈 ВАША ОБЩАЯ СТАТИСТИКА:
Пройдено тренировок: {stats['total_trainings']}
Всего вопросов задано: {stats['total_questions']}
Лучший результат: {stats['best_score']} баллов"""

    def _format_listening_stats(self, session: Dict[str, Any]) -> str:
        """Статистика активного слушания."""
        contextual_q = session.get('contextual_questions', 0)
        total_q = session.get('question_count', 0)
        pct = int((contextual_q / total_q) * 100) if total_q > 0 else 0

        result = f"""👂 АКТИВНОЕ СЛУШАНИЕ:
Контекстуальных вопросов: {contextual_q}/{total_q} ({pct}%)"""

        if pct >= 70:
            result += "\n🏆 Отлично! Вы внимательно слушаете клиента!"
        elif pct >= 40:
            result += "\n💡 Хорошо, но можно чаще использовать факты из ответов"
        else:
            result += "\n⚠️ Совет: стройте вопросы на основе ответов клиента"

        return result

    def _format_rank_info(self, stats: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Информация о ранге и уровне."""
        levels = config.get('ranking', {}).get('levels', [])
        current_level = stats.get('current_level', 1)
        current_xp = stats.get('total_xp', 0)

        level_data = next((l for l in levels if l.get('level') == current_level),
                        levels[0] if levels else {'level': 1, 'name': 'Новичок', 'emoji': '🌱', 'min_xp': 0, 'description': ''})
        next_level_data = next((l for l in levels if l.get('level') == current_level + 1), None)

        xp_progress = ""
        if next_level_data:
            xp_to_next = int(next_level_data.get('min_xp', 0)) - current_xp
            if xp_to_next > 0:
                xp_progress = f"\nДо следующего уровня: {xp_to_next} XP"

        return f"""⭐ ВАШ РАНГ:
{level_data.get('emoji', '')} Уровень {level_data.get('level', 1)}: {level_data.get('name', '')}
Опыт (XP): {current_xp}{xp_progress}
{level_data.get('description', '')}

💡 Используйте /rank для детального просмотра прогресса и достижений"""

    def _format_level_up(self, notif: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Уведомление о повышении уровня."""
        levels = config.get('ranking', {}).get('levels', [])
        level_data = next((l for l in levels if l.get('level') == notif['new_level']), None)

        emoji = level_data.get('emoji', '🎉') if level_data else '🎉'
        name = level_data.get('name', '') if level_data else ''

        return f"""🎊 ПОЗДРАВЛЯЕМ! ВЫ ПОВЫСИЛИ УРОВЕНЬ!
{emoji} Уровень {notif['old_level']} → Уровень {notif['new_level']}: {name}

Используйте /rank для подробностей"""

    def _format_achievements(self, achievements: List[Dict[str, Any]]) -> str:
        """Новые достижения."""
        lines = ["🎖️ НОВЫЕ ДОСТИЖЕНИЯ:"]
        for ach in achievements:
            lines.append(f"{ach.get('emoji', '')} {ach.get('name', '')} - {ach.get('description', '')}")
        return "\n".join(lines)

    def _format_footer(self, config: Dict[str, Any]) -> str:
        """Призыв к действию и промо-блок."""
        promo = config.get('ui', {}).get('promo_text', {})

        footer = "🎯 Для новой тренировки напишите \"начать\" или используйте /help для справки"

        if promo.get('enabled', True):
            footer += f"\n\n🚀 {promo.get('title', 'ПОЛЕЗНЫЙ КОНТЕНТ ПО ПРОДЖАМ И ИИ:')}"
            footer += f"\n{promo.get('text', 'вы сможете найти на канале Тактика Кутузова @TaktikaKutuzova')}"

        return footer


