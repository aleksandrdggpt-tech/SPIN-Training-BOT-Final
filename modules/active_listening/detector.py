"""
Active Listening Detector.
Detects when user references information from previous responses.
"""

import re
import logging
from typing import Optional, Callable, Awaitable, Dict, Any

from .config import ActiveListeningConfig

logger = logging.getLogger(__name__)


class ActiveListeningDetector:
    """
    Detects active listening (contextual questions).

    Contextual questions are questions that reference or build upon
    information from the previous response.
    """

    def __init__(self, config: Optional[ActiveListeningConfig] = None):
        """
        Initialize detector.

        Args:
            config: Configuration for active listening detection
        """
        self.config = config or ActiveListeningConfig()

    async def check_context_usage(
        self,
        question: str,
        last_response: str,
        call_llm_func: Optional[Callable[[str, str, str], Awaitable[str]]] = None
    ) -> bool:
        """
        Check if question uses context from last response.

        Args:
            question: User's current question
            last_response: Last response from AI/client
            call_llm_func: Optional LLM function for detection
                         Signature: (kind: str, prompt: str, description: str) -> str

        Returns:
            True if question is contextual, False otherwise
        """
        if not self.config.enabled:
            return False

        if not last_response:
            return False

        # Try LLM detection first
        if self.config.use_llm and call_llm_func:
            try:
                result = await self._check_with_llm(
                    question,
                    last_response,
                    call_llm_func
                )
                if result is not None:
                    return result
            except Exception as e:
                logger.warning(f"LLM context check failed: {e}")
                if not self.config.llm_fallback:
                    return False

        # Fallback to heuristic detection
        return self._check_with_heuristic(question, last_response)

    async def _check_with_llm(
        self,
        question: str,
        last_response: str,
        call_llm_func: Callable[[str, str, str], Awaitable[str]]
    ) -> Optional[bool]:
        """
        Check context usage with LLM.

        Returns:
            True/False if detection successful, None if failed
        """
        try:
            prompt = self.config.get_llm_prompt(question, last_response)
            raw = await call_llm_func('context', prompt, 'Check context usage')
            label = (raw or '').strip().lower()

            if 'yes' in label and 'no' not in label:
                logger.info("✅ LLM detected active listening")
                return True
            if 'no' in label:
                logger.info("❌ LLM: no active listening")
                return False

            logger.warning(f"Unrecognized LLM response: {raw}")
            return None

        except Exception as e:
            logger.error(f"LLM context check error: {e}")
            return None

    def _check_with_heuristic(self, question: str, last_response: str) -> bool:
        """
        Check context usage with heuristic rules.

        Rules:
        1. Question contains numbers mentioned in last response
        2. Question contains context markers (e.g., "as you said")
        3. Question references specific facts from response

        Args:
            question: User's question
            last_response: Last response

        Returns:
            True if contextual, False otherwise
        """
        q = question.lower()
        resp = last_response.lower()

        # Rule 1: Numbers from response
        numbers = re.findall(r"\b\d+[\d\s.,]*\b", resp)
        for num in numbers:
            cleaned_num = num.strip()
            if cleaned_num and cleaned_num in q:
                logger.info(f"👂 Active listening detected: number '{cleaned_num}'")
                return True

        # Rule 2: Context markers
        for marker in self.config.context_markers:
            if marker.lower() in q:
                logger.info(f"👂 Active listening detected: marker '{marker}'")
                return True

        # Rule 3: Repeated keywords (at least 3 common non-trivial words)
        # Extract meaningful words (3+ chars, not common stop words)
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
            'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get',
            'это', 'что', 'как', 'для', 'или', 'мне', 'вас', 'нас',
            'все', 'там', 'вот', 'еще', 'где', 'уже', 'так', 'вот'
        }

        resp_words = {
            w for w in re.findall(r'\b\w{4,}\b', resp)
            if w not in stop_words
        }
        q_words = {
            w for w in re.findall(r'\b\w{4,}\b', q)
            if w not in stop_words
        }

        common_words = resp_words & q_words
        if len(common_words) >= 3:
            logger.info(f"👂 Active listening detected: {len(common_words)} common words")
            return True

        return False

    def format_stats(
        self,
        contextual_count: int,
        total_questions: int
    ) -> str:
        """
        Format active listening statistics.

        Args:
            contextual_count: Number of contextual questions
            total_questions: Total number of questions

        Returns:
            Formatted statistics string
        """
        if total_questions == 0:
            percentage = 0
        else:
            percentage = int((contextual_count / total_questions) * 100)

        return f"""{self.config.emoji} АКТИВНОЕ СЛУШАНИЕ:
Контекстуальных вопросов: {contextual_count}/{total_questions} ({percentage}%)"""

    def get_bonus_points(self) -> int:
        """
        Get bonus points for contextual question.

        Returns:
            Bonus points value
        """
        return self.config.bonus_points

    def format_badge(self) -> str:
        """
        Format active listening badge for display next to question type.

        Returns:
            " 👂 (Успешное активное слушание)" or " 👂 (Successful active listening)"

        Example:
            "Ситуационный вопрос 👂 (Успешное активное слушание)"
        """
        if self.config.language == "en":
            return f" {self.config.emoji} (Successful active listening)"
        else:
            return f" {self.config.emoji} (Успешное активное слушание)"
