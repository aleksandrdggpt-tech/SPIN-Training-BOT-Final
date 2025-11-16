"""
Example of integrating Active Listening module into training_service.py

This shows how to replace existing active listening code with the module.
"""

# ==================== BEFORE (current code) ====================

async def process_question_OLD(self, user_id, question, scenario_config):
    """Old implementation with inline active listening logic."""
    session = self.user_service.get_session(user_id)

    # Old way: inline context check
    is_contextual = False
    last_resp = session.get('last_client_response', '')
    if last_resp:
        is_contextual = await self.question_analyzer.check_context_usage(
            question,
            last_resp,
            lambda kind, sys, usr: self.llm_service.call_llm('context', sys, usr),
            scenario_config.get('prompts', {})
        )

    # Old way: simple emoji badge
    context_badge = ""
    if is_contextual:
        session['contextual_questions'] += 1
        contextual_bonus = 5
        session['clarity_level'] += contextual_bonus
        context_badge = " 👂"  # ❌ Simple emoji only

    # Format response
    response = f"Тип вопроса: Ситуационный{context_badge}"
    # Result: "Тип вопроса: Ситуационный 👂"


# ==================== AFTER (with module) ====================

from modules.active_listening import ActiveListeningDetector, ActiveListeningConfig

# Initialize once (at bot startup)
active_listening_config = ActiveListeningConfig(
    enabled=True,
    use_llm=True,
    bonus_points=5,
    emoji="👂",
    language="ru"
)
active_listening = ActiveListeningDetector(active_listening_config)


async def process_question_NEW(self, user_id, question, scenario_config):
    """New implementation with Active Listening module."""
    session = self.user_service.get_session(user_id)

    # ✅ New way: use module
    last_resp = session.get('last_client_response', '')

    is_contextual = await active_listening.check_context_usage(
        question=question,
        last_response=last_resp,
        call_llm_func=self.llm_service.call_llm
    )

    # ✅ New way: format badge with text
    context_badge = ""
    if is_contextual:
        session['contextual_questions'] += 1
        bonus = active_listening.get_bonus_points()
        session['clarity_level'] += bonus
        context_badge = active_listening.format_badge()  # ✅ Returns full badge

    # Format response
    response = f"Тип вопроса: Ситуационный{context_badge}"
    # Result: "Тип вопроса: Ситуационный 👂 (Успешное активное слушание)"


# ==================== COMPARISON ====================

"""
BEFORE:
├─ context_badge = " 👂"
└─ Result: "Ситуационный 👂"

AFTER:
├─ context_badge = active_listening.format_badge()
└─ Result: "Ситуационный 👂 (Успешное активное слушание)"

✅ More obvious and informative!
"""


# ==================== FULL EXAMPLE ====================

async def handle_user_question_FULL_EXAMPLE(self, user_id: int, question: str):
    """Complete example with all steps."""
    session = self.user_service.get_session(user_id)
    scenario_config = self.scenario_loader.get_config()

    # 1. Classify question type
    question_type = self.question_analyzer.classify_question(
        question=question,
        question_types=scenario_config['question_types']
    )
    question_type_name = question_type.get('name', 'Вопрос')

    # 2. Check active listening
    last_response = session.get('last_client_response', '')

    is_contextual = await active_listening.check_context_usage(
        question=question,
        last_response=last_response,
        call_llm_func=self.llm_service.call_llm
    )

    # 3. Format badge
    context_badge = ""
    if is_contextual:
        session['contextual_questions'] = session.get('contextual_questions', 0) + 1
        bonus_points = active_listening.get_bonus_points()
        session['clarity_level'] = min(100, session['clarity_level'] + bonus_points)
        context_badge = active_listening.format_badge()
        # Returns: " 👂 (Успешное активное слушание)"

    # 4. Generate client response
    client_response = await self.generate_client_response(question)
    session['last_client_response'] = client_response

    # 5. Format feedback message
    feedback = f"""
📝 Тип вопроса: {question_type_name}{context_badge}

💬 Ответ клиента:
{client_response}

📊 Прогресс: {session['question_count']}/{scenario_config['game_rules']['max_questions']}
🎯 Ясность: {session['clarity_level']}%
"""

    return feedback


# ==================== OUTPUT EXAMPLES ====================

"""
Example 1: Regular question (no active listening)
───────────────────────────────────────────────────
📝 Тип вопроса: Ситуационный вопрос

💬 Ответ клиента:
У нас компания на 50 человек.
───────────────────────────────────────────────────

Example 2: With active listening
───────────────────────────────────────────────────
📝 Тип вопроса: Проблемный вопрос 👂 (Успешное активное слушание)

💬 Ответ клиента:
Из этих 50 человек примерно 15 работают в продажах.
───────────────────────────────────────────────────

✅ Much more obvious that active listening was detected!
"""


# ==================== DISABLE MODULE ====================

# If you don't want active listening in a bot:
active_listening_config = ActiveListeningConfig(enabled=False)
active_listening = ActiveListeningDetector(active_listening_config)

# Now format_badge() will return empty string
context_badge = active_listening.format_badge()  # Returns: ""
