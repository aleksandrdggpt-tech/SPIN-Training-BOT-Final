"""
Конфигурация приложения SPIN Training Bot.
Содержит все настройки из переменных окружения.
"""

import os
from typing import Optional


class Config:
    """Класс конфигурации приложения."""

    # Секретные ключи из .env
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY: str = os.getenv('ANTHROPIC_API_KEY', '')
    # Список админов (идентификаторы Telegram), через запятую в .env: ADMIN_USER_IDS=123,456
    _ADMIN_IDS_RAW: str = os.getenv('ADMIN_USER_IDS', '')
    ADMIN_USER_IDS = []
    if _ADMIN_IDS_RAW:
        try:
            ADMIN_USER_IDS = [int(x.strip()) for x in _ADMIN_IDS_RAW.split(',') if x.strip().isdigit()]
        except Exception:
            ADMIN_USER_IDS = []

    # Настройки приложения (по умолчанию)
    SCENARIO_PATH: str = 'scenarios/spin_sales/config.json'
    PORT: int = 8080
    LLM_TIMEOUT_SEC: float = 30.0
    LLM_MAX_RETRIES: int = 1

    # Логика провайдеров LLM (фиксированная в коде)
    # Ответы клиента
    RESPONSE_PRIMARY_PROVIDER: str = 'openai'
    RESPONSE_PRIMARY_MODEL: str = 'gpt-4o-mini'
    RESPONSE_FALLBACK_PROVIDER: str = 'anthropic'
    RESPONSE_FALLBACK_MODEL: str = 'claude-3-haiku-latest'

    # Обратная связь наставника
    FEEDBACK_PRIMARY_PROVIDER: str = 'openai'
    FEEDBACK_PRIMARY_MODEL: str = 'gpt-5-mini'
    FEEDBACK_FALLBACK_PROVIDER: str = 'anthropic'
    FEEDBACK_FALLBACK_MODEL: str = 'claude-3-5-sonnet-latest'

    # Классификация вопросов
    CLASSIFICATION_PRIMARY_PROVIDER: str = 'openai'
    CLASSIFICATION_PRIMARY_MODEL: str = 'gpt-4o-mini'
    CLASSIFICATION_FALLBACK_PROVIDER: str = 'openai'
    CLASSIFICATION_FALLBACK_MODEL: str = 'gpt-4o-mini'

    @classmethod
    def validate(cls) -> None:
        """Проверяет критичные параметры конфигурации."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")

        if not cls.OPENAI_API_KEY and not cls.ANTHROPIC_API_KEY:
            raise ValueError("Необходим хотя бы один API ключ (OPENAI_API_KEY или ANTHROPIC_API_KEY)")

    @classmethod
    def print_config(cls) -> None:
        """Безопасно выводит конфигурацию (скрывает API ключи)."""
        print("🔧 Конфигурация приложения:")
        print(f"  BOT_TOKEN: {cls._mask_token(cls.BOT_TOKEN)}")
        print(f"  OPENAI_API_KEY: {cls._mask_token(cls.OPENAI_API_KEY)}")
        print(f"  ANTHROPIC_API_KEY: {cls._mask_token(cls.ANTHROPIC_API_KEY)}")
        print(f"  SCENARIO_PATH: {cls.SCENARIO_PATH}")
        print(f"  PORT: {cls.PORT}")
        print(f"  LLM_TIMEOUT_SEC: {cls.LLM_TIMEOUT_SEC}")
        print(f"  LLM_MAX_RETRIES: {cls.LLM_MAX_RETRIES}")
        print(f"  RESPONSE_PROVIDER: {cls.RESPONSE_PRIMARY_PROVIDER} -> {cls.RESPONSE_FALLBACK_PROVIDER}")
        print(f"  FEEDBACK_PROVIDER: {cls.FEEDBACK_PRIMARY_PROVIDER} -> {cls.FEEDBACK_FALLBACK_PROVIDER}")
        print(f"  CLASSIFICATION_PROVIDER: {cls.CLASSIFICATION_PRIMARY_PROVIDER} -> {cls.CLASSIFICATION_FALLBACK_PROVIDER}")

    @staticmethod
    def _mask_token(token: str) -> str:
        """Маскирует токен для безопасного вывода."""
        if not token:
            return "НЕ УСТАНОВЛЕН"
        return f"{token[:20]}..." if len(token) > 20 else f"{token[:10]}..."


# Валидация будет вызвана в main() при запуске бота
