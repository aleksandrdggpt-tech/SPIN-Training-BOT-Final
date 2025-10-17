# План рефакторинга отчётов для v3.0

## Цель
Переместить всю логику форматирования финальных отчётов из bot.py в engine/report_generator.py

## Проблема текущей архитектуры (v2.0)

Сейчас формирование финального отчёта раздроблено между двумя файлами:

**engine/report_generator.py:**
- Базовый отчёт (результаты, типы вопросов, бейджи, рекомендации)

**bot.py:**
- Информация о кейсе
- Общая статистика пользователя
- Активное слушание
- Ранги и XP
- Достижения
- Склейка всех частей вместе

**Проблемы:**
- ❌ Логика представления данных размазана по двум местам
- ❌ Сложно поддерживать и изменять порядок элементов
- ❌ `bot.py` знает слишком много о форматировании
- ❌ Дублирование логики (текст про канал был в двух местах)

## Правильная архитектура для v3.0

### Принцип разделения ответственности:

**bot.py** - только бизнес-логика:
```python
async def send_final_report(update: Update, user: Dict[str, Any]):
    cfg = _ensure_scenario_loaded()
    
    # Собираем ВСЕ данные
    report_data = {
        'session': user['session'],
        'stats': user['stats'],
        'case_data': user['session'].get('case_data'),
        'achievements': _get_newly_unlocked_achievements(user),
        'level_up': user['stats'].get('level_up_notification'),
    }
    
    # Генератор делает ВСЮ работу по форматированию
    report = ReportGenerator().generate_final_report(report_data, cfg)
    
    # Просто отправляем
    await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)
```

**engine/report_generator.py** - вся логика форматирования:
```python
class ReportGenerator:
    def generate_final_report(self, data: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Генерирует ПОЛНЫЙ финальный отчёт со всеми секциями."""
        sections = []
        
        # 1. Базовые результаты
        sections.append(self._format_basic_results(data, config))
        
        # 2. Информация о кейсе
        if data.get('case_data'):
            sections.append(self._format_case_info(data['case_data']))
        
        # 3. Общая статистика
        sections.append(self._format_overall_stats(data['stats']))
        
        # 4. Активное слушание
        sections.append(self._format_listening_stats(data['session']))
        
        # 5. Ранг и XP
        sections.append(self._format_rank_info(data['stats'], config))
        
        # 6. Уведомление о повышении уровня
        if data.get('level_up', {}).get('should_show'):
            sections.append(self._format_level_up(data['level_up'], config))
        
        # 7. Новые достижения
        if data.get('achievements'):
            sections.append(self._format_achievements(data['achievements']))
        
        # 8. Призыв к действию + промо
        sections.append(self._format_footer(config))
        
        return "\n\n".join(sections)
```

## Этапы

### Этап 1: Расширить ReportGenerator
- [ ] Добавить методы для всех секций отчёта
- [ ] Реализовать _format_case_info()
- [ ] Реализовать _format_overall_stats()
- [ ] Реализовать _format_listening_stats()
- [ ] Реализовать _format_rank_info()
- [ ] Реализовать _format_level_up()
- [ ] Реализовать _format_achievements()
- [ ] Реализовать _format_footer()

### Этап 2: Упростить bot.py
- [ ] Убрать форматирование из send_final_report()
- [ ] Оставить только подготовку данных
- [ ] Вызов генератора
- [ ] Отправка сообщения

### Этап 3: Конфигурация
- [ ] Добавить promo_text в config.json
- [ ] Сделать промо-блок включаемым/выключаемым

### Этап 4: Тестирование
- [ ] Проверить все секции отчёта
- [ ] Проверить разный порядок секций
- [ ] Проверить с промо и без промо

## Конфигурация промо-блока

В файле `scenarios/spin_sales/config.json` добавить:

```json
{
  "ui": {
    "promo_text": {
      "enabled": true,
      "title": "ПОЛЕЗНЫЙ КОНТЕНТ ПО ПРОДЖАМ И ИИ:",
      "text": "вы сможете найти на канале Тактика Кутузова @TaktikaKutuzova"
    }
  }
}
```

## Выгоды новой архитектуры

✅ **Единая точка формирования отчёта** - всё в `ReportGenerator`
✅ **Лёгко менять порядок секций** - просто переставить строки в массиве `sections`
✅ **Лёгко добавлять новые секции** - новый метод `_format_xxx` и добавить в список
✅ **Лёгко тестировать** - можно тестировать каждую секцию отдельно
✅ **Чистый bot.py** - только бизнес-логика, никакого форматирования
✅ **Гибкая конфигурация** - промо-блок можно включить/выключить через config.json

## Детальная структура методов ReportGenerator

### _format_basic_results(data, config)
```python
def _format_basic_results(self, data, config):
    """Базовые результаты тренировки."""
    # Текущая логика из generate_final_report()
    # Результаты, типы вопросов, бейджи, рекомендации
```

### _format_case_info(case_data)
```python
def _format_case_info(self, case_data):
    """Информация о кейсе."""
    return f"""📋 ИНФОРМАЦИЯ О КЕЙСЕ:
Должность: {case_data['position']}
Компания: {case_data['company']['type']}
Продукт: {case_data['product']['name']}
Объём: {case_data['volume']}"""
```

### _format_overall_stats(stats)
```python
def _format_overall_stats(self, stats):
    """Общая статистика пользователя."""
    return f"""📈 ВАША ОБЩАЯ СТАТИСТИКА:
Пройдено тренировок: {stats['total_trainings']}
Всего вопросов задано: {stats['total_questions']}
Лучший результат: {stats['best_score']} баллов"""
```

### _format_listening_stats(session)
```python
def _format_listening_stats(self, session):
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
```

### _format_rank_info(stats, config)
```python
def _format_rank_info(self, stats, config):
    """Информация о ранге и уровне."""
    levels = config.get('ranking', {}).get('levels', [])
    current_level = stats.get('current_level', 1)
    current_xp = stats.get('total_xp', 0)
    
    level_data = next((l for l in levels if l['level'] == current_level), levels[0])
    next_level_data = next((l for l in levels if l['level'] == current_level + 1), None)
    
    xp_progress = ""
    if next_level_data:
        xp_to_next = next_level_data['min_xp'] - current_xp
        if xp_to_next > 0:
            xp_progress = f"\nДо следующего уровня: {xp_to_next} XP"
    
    return f"""⭐ ВАШ РАНГ:
{level_data['emoji']} Уровень {level_data['level']}: {level_data['name']}
Опыт (XP): {current_xp}{xp_progress}
{level_data.get('description', '')}

💡 Используйте /rank для детального просмотра прогресса и достижений"""
```

### _format_level_up(notif, config)
```python
def _format_level_up(self, notif, config):
    """Уведомление о повышении уровня."""
    levels = config.get('ranking', {}).get('levels', [])
    level_data = next((l for l in levels if l['level'] == notif['new_level']), None)
    
    emoji = level_data.get('emoji', '🎉') if level_data else '🎉'
    name = level_data.get('name', '') if level_data else ''
    
    return f"""🎊 ПОЗДРАВЛЯЕМ! ВЫ ПОВЫСИЛИ УРОВЕНЬ!
{emoji} Уровень {notif['old_level']} → Уровень {notif['new_level']}: {name}

Используйте /rank для подробностей"""
```

### _format_achievements(achievements)
```python
def _format_achievements(self, achievements):
    """Новые достижения."""
    lines = ["🎖️ НОВЫЕ ДОСТИЖЕНИЯ:"]
    for ach in achievements:
        lines.append(f"{ach['emoji']} {ach['name']} - {ach['description']}")
    return "\n".join(lines)
```

### _format_footer(config)
```python
def _format_footer(self, config):
    """Призыв к действию и промо-блок."""
    promo = config.get('ui', {}).get('promo_text', {})
    
    footer = "🎯 Для новой тренировки напишите \"начать\" или используйте /help для справки"
    
    if promo.get('enabled', True):
        footer += f"\n\n🚀 {promo.get('title', 'ПОЛЕЗНЫЙ КОНТЕНТ ПО ПРОДЖАМ И ИИ:')}"
        footer += f"\n{promo.get('text', 'вы сможете найти на канале Тактика Кутузова @TaktikaKutuzova')}"
    
    return footer
```

## Миграция с v2.0 на v3.0

1. **Создать новую ветку** `feature/v3-report-refactoring`
2. **Скопировать текущую логику** из `bot.py` в соответствующие методы `ReportGenerator`
3. **Упростить `send_final_report()`** в `bot.py`
4. **Добавить конфигурацию** промо-блока в `config.json`
5. **Протестировать** все сценарии
6. **Создать PR** с подробным описанием изменений

## Обратная совместимость

- Все существующие функции должны работать без изменений
- Порядок секций в отчёте должен остаться тем же
- Промо-блок должен отображаться по умолчанию (enabled: true)
