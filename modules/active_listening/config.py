"""
Configuration for Active Listening module.
"""

from typing import List, Optional


class ActiveListeningConfig:
    """Configuration for active listening detection."""

    # Context markers (phrases that indicate reference to previous response)
    DEFAULT_CONTEXT_MARKERS = [
        "как вы сказали",
        "вы сказали",
        "вы упомянули",
        "вы говорили",
        "уточните",
        "по поводу",
        "этих",
        "этой проблемы",
        "этой ситуации",
        "той ситуации",
        "этого",
        "того, что вы",
        "в связи с тем",
        "касательно",
        "относительно",
        "о чем вы",
        "что вы имели в виду"
    ]

    # English context markers
    ENGLISH_CONTEXT_MARKERS = [
        "as you said",
        "you said",
        "you mentioned",
        "you spoke about",
        "clarify",
        "regarding",
        "about that",
        "about this",
        "about the",
        "what you meant",
        "what you said"
    ]

    def __init__(
        self,
        enabled: bool = True,
        use_llm: bool = True,
        llm_fallback: bool = True,
        context_markers: Optional[List[str]] = None,
        bonus_points: int = 5,
        emoji: str = "👂",
        language: str = "ru"  # "ru" or "en"
    ):
        """
        Initialize active listening configuration.

        Args:
            enabled: Enable active listening detection
            use_llm: Use LLM for detection (more accurate)
            llm_fallback: Fall back to heuristic if LLM fails
            context_markers: Custom context markers (phrases)
            bonus_points: Bonus clarity/score points for contextual questions
            emoji: Emoji for active listening indicator
            language: Language for default markers ("ru" or "en")
        """
        self.enabled = enabled
        self.use_llm = use_llm
        self.llm_fallback = llm_fallback
        self.bonus_points = bonus_points
        self.emoji = emoji
        self.language = language

        # Set context markers
        if context_markers is not None:
            self.context_markers = context_markers
        elif language == "en":
            self.context_markers = self.ENGLISH_CONTEXT_MARKERS
        else:
            self.context_markers = self.DEFAULT_CONTEXT_MARKERS

    def get_llm_prompt(self, question: str, last_response: str) -> str:
        """
        Generate LLM prompt for context detection.

        Args:
            question: User's question
            last_response: Last response from AI/client

        Returns:
            Formatted prompt for LLM
        """
        if self.language == "en":
            return f"""Determine if the following question references or uses information from the previous response.

Previous response:
{last_response}

Current question:
{question}

Does the question reference specific facts, numbers, or information from the previous response?
Answer with ONLY "yes" or "no"."""
        else:
            return f"""Определи, использует ли следующий вопрос информацию или факты из предыдущего ответа.

Предыдущий ответ:
{last_response}

Текущий вопрос:
{question}

Использует ли вопрос конкретные факты, цифры или информацию из предыдущего ответа?
Ответь ТОЛЬКО "yes" или "no"."""
