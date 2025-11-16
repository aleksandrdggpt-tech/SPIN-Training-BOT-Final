"""
Сервис для работы с LLM провайдерами.
Содержит логику вызова OpenAI и Anthropic API с fallback механизмом.
"""

import asyncio
import logging
from typing import Literal

import httpx
import openai

from config import Config

logger = logging.getLogger(__name__)


class LLMService:
    """Сервис для работы с различными LLM провайдерами."""

    def __init__(self):
        """Инициализация сервиса."""
        self.config = Config()
        # Единый HTTP клиент для всех провайдеров (keep-alive + HTTP/2 + лимиты)
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.LLM_TIMEOUT_SEC),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=10),
            http2=True,
        )
        # Единый OpenAI клиент, использующий общий httpx.AsyncClient
        import os
        api_key = self.config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.openai_client = openai.AsyncOpenAI(api_key=api_key, http_client=self.http_client)

    async def call_llm(
        self,
        kind: Literal['response', 'feedback', 'classification', 'context'],
        system_prompt: str,
        user_message: str
    ) -> str:
        """Вызов LLM по конвейеру kind с фолбэком и провайдерами."""
        assert kind in ('response', 'feedback', 'classification', 'context')

        # Определяем конфигурацию провайдеров для данного типа запроса
        pipeline_config = self._get_pipeline_config(kind)

        # Кол-во ретраев: для feedback — без ретраев (сразу fallback)
        retries = 0 if kind == 'feedback' else self.config.LLM_MAX_RETRIES
        for attempt in range(retries + 1):
            try:
                logger.info(f"LLM primary: {kind} provider={pipeline_config['primary_provider']} model={pipeline_config['primary_model']} attempt={attempt+1}")
                return await self._invoke(pipeline_config['primary_provider'], pipeline_config['primary_model'], kind, system_prompt, user_message)
            except Exception as e:
                logger.warning(f"Primary failed ({kind}): {type(e).__name__}: {e}")
                if attempt < self.config.LLM_MAX_RETRIES:
                    continue

        # Fallback
        try:
            logger.info(f"LLM fallback: {kind} provider={pipeline_config['fallback_provider']} model={pipeline_config['fallback_model']}")
            return await self._invoke(pipeline_config['fallback_provider'], pipeline_config['fallback_model'], kind, system_prompt, user_message)
        except Exception as e:
            logger.error(f"Fallback failed ({kind}): {type(e).__name__}: {e}")
            return "Произошла ошибка при генерации ответа. Попробуйте ещё раз позже."

    async def stream_feedback(self, system_prompt: str, user_message: str):
        """Стриминг фидбека. Возвращает async-итератор строк.
        - GPT-5: стрим отключен (поднимем исключение, чтобы вызвать нестримовый путь).
        - GPT-4 серии (chat): стрим через Chat Completions.
        - Anthropic: стрим через Messages SSE.
        """
        pipeline = self._get_pipeline_config('feedback')
        provider = pipeline['primary_provider']
        model = pipeline['primary_model']

        # GPT-5 — стрим отключён по требованию
        if provider == 'openai' and str(model).startswith('gpt-5'):
            raise RuntimeError('Streaming disabled for GPT-5')

        if provider == 'openai':
            # Поддерживаемые chat-модели для стрима
            temperature = 0.0  # для фидбека детерминированный
            # При использовании SDK .stream(...) параметр stream передавать не нужно
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
            }
            try:
                stream = self.openai_client.chat.completions.stream(**payload)
                async with stream as s:
                    async for event in s:
                        try:
                            # В новых SDK event может иметь типы, но надёжнее собрать deltas
                            choice = None
                            if hasattr(event, 'choices') and event.choices:
                                choice = event.choices[0]
                            if choice and hasattr(choice, 'delta'):
                                delta = getattr(choice.delta, 'content', None)
                                if isinstance(delta, str) and delta:
                                    yield delta
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"OpenAI Chat stream failed model={model} error={e}")
                raise

        elif provider == 'anthropic':
            # Anthropic SSE streaming
            import json as _json
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "accept": "text/event-stream",
            }
            payload = {
                "model": model,
                "max_tokens": 400,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
                "temperature": 0.0,
                "stream": True,
            }
            try:
                async with self.http_client.stream('POST', url, headers=headers, json=payload) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line or not line.startswith('data: '):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            evt = _json.loads(data_str)
                        except Exception:
                            continue
                        if evt.get('type') == 'content_block_delta':
                            delta = (evt.get('delta') or {}).get('text')
                            if isinstance(delta, str) and delta:
                                yield delta
            except Exception as e:
                logger.error(f"Anthropic stream failed model={model} error={e}")
                raise
        else:
            raise RuntimeError(f"Streaming not supported for provider: {provider}")

    def _get_pipeline_config(self, kind: str) -> dict:
        """Получает конфигурацию провайдеров для данного типа запроса."""
        if kind == 'response':
            return {
                'primary_provider': self.config.RESPONSE_PRIMARY_PROVIDER,
                'primary_model': self.config.RESPONSE_PRIMARY_MODEL,
                'fallback_provider': self.config.RESPONSE_FALLBACK_PROVIDER,
                'fallback_model': self.config.RESPONSE_FALLBACK_MODEL,
            }
        elif kind == 'feedback':
            return {
                'primary_provider': self.config.FEEDBACK_PRIMARY_PROVIDER,
                'primary_model': self.config.FEEDBACK_PRIMARY_MODEL,
                'fallback_provider': self.config.FEEDBACK_FALLBACK_PROVIDER,
                'fallback_model': self.config.FEEDBACK_FALLBACK_MODEL,
            }
        else:  # classification, context
            return {
                'primary_provider': self.config.CLASSIFICATION_PRIMARY_PROVIDER,
                'primary_model': self.config.CLASSIFICATION_PRIMARY_MODEL,
                'fallback_provider': self.config.CLASSIFICATION_FALLBACK_PROVIDER,
                'fallback_model': self.config.CLASSIFICATION_FALLBACK_MODEL,
            }

    async def _invoke(self, provider: str, model: str, kind: str, system_prompt: str, user_message: str) -> str:
        """Вызывает указанный провайдер с указанной моделью."""
        if provider == 'openai':
            return await self._invoke_openai(model, kind, system_prompt, user_message)
        elif provider == 'anthropic':
            return await self._invoke_anthropic(model, kind, system_prompt, user_message)
        else:
            raise RuntimeError(f"Unknown provider: {provider}")

    async def _invoke_openai(self, model_name: str, kind: str, system_prompt: str, user_message: str) -> str:
        """Вызов OpenAI API с роутингом по семействам моделей."""
        if str(model_name).startswith("gpt-5"):
            return await self._invoke_openai_gpt5(model_name, kind, system_prompt, user_message)
        if model_name in ['gpt-4o', 'gpt-4o-2024-07-18', 'gpt-4o-2024-08-06', 'gpt-4o-2024-11-20']:
            return await self._invoke_openai_gpt4o_new(model_name, kind, system_prompt, user_message)
        return await self._invoke_openai_chat_standard(model_name, kind, system_prompt, user_message)

    async def _invoke_openai_gpt5(self, model_name: str, kind: str, system_prompt: str, user_message: str) -> str:
        """GPT-5 через Responses API (без temperature)."""
        # Проверяем наличие API ключа
        import os
        api_key = self.config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OpenAI API key not set")
        client = self.openai_client
        if kind in ('classification', 'context'):
            max_tokens = 20 if kind == 'classification' else 64
        else:  # 'response' | 'feedback'
            max_tokens = 2000
        payload = {
            "model": model_name,
            # Для GPT-5 Responses используем instructions вместо system role
            "instructions": system_prompt,
            # input может быть строкой; для простого запроса это рекомендуемый формат
            "input": user_message,
            "max_output_tokens": max_tokens,
        }
        # Для фидбека пробуем включить лёгкое рассуждение; при отказе API удалим и повторим
        if kind == 'feedback':
            payload_with_reasoning = dict(payload)
            payload_with_reasoning["reasoning"] = {"effort": "low"}
        else:
            payload_with_reasoning = None
        logger.debug(f"OpenAI Responses payload keys={list(payload.keys())}")
        try:
            try_payload = payload_with_reasoning or payload
            resp = await client.responses.create(**try_payload)

            # Пробуем несколько способов получить ответ
            content = None

            # Способ 1 (рекомендуемый): output_text
            if getattr(resp, "output_text", None):
                try:
                    content = resp.output_text.strip()
                except Exception:
                    content = None

            # Способ 2: output (массив/строка) — собираем text items
            if not content and hasattr(resp, "output") and resp.output:
                try:
                    if isinstance(resp.output, list):
                        parts = []
                        for item in resp.output:
                            if getattr(item, "type", None) == "text":
                                txt = getattr(item, "content", None)
                                if isinstance(txt, str) and txt.strip():
                                    parts.append(txt.strip())
                        if parts:
                            content = " ".join(parts).strip()
                    elif isinstance(resp.output, str):
                        content = resp.output.strip()
                except Exception:
                    pass

            # Способ 3: choices (chat-подобный формат)
            if not content and hasattr(resp, "choices") and resp.choices:
                try:
                    if len(resp.choices) > 0 and hasattr(resp.choices[0], "message") and resp.choices[0].message:
                        content = (resp.choices[0].message.content or "").strip()
                except Exception:
                    pass

            # Способ 4: text (может быть объектом-конфигом — игнорируем такие repr)
            if not content and hasattr(resp, "text") and resp.text is not None:
                try:
                    # В новых SDK это объект, берем .value, если это строка
                    value = getattr(resp.text, "value", None)
                    if isinstance(value, str):
                        candidate = value.strip()
                        # Отсеиваем конфигурационный repr
                        if not candidate.startswith("ResponseTextConfig("):
                            content = candidate
                except Exception:
                    pass

            # Компактная отладка
            logger.debug(f"GPT-5 resp type={type(resp)} status={getattr(resp,'status',None)} has_text={bool(getattr(resp,'output_text',None))}")

            if not content:
                logger.warning("GPT-5 empty response — triggering fallback")
                raise RuntimeError("Empty LLM response from GPT-5")

            logger.debug(f"GPT-5 response length: {len(content)} chars")
            return content
        except Exception as e:
            # Если пробовали с reasoning и получили отказ — повторим без reasoning один раз
            msg = str(e)
            if payload_with_reasoning is not None and (
                'Unknown parameter' in msg or 'reasoning' in msg or 'invalid_parameter' in msg or '400' in msg
            ):
                logger.warning("GPT-5 reasoning not accepted, retrying without reasoning")
                resp = await client.responses.create(**payload)
                # Повторное извлечение контента (скопировано для краткости):
                content = None
                if getattr(resp, "output_text", None):
                    try:
                        content = resp.output_text.strip()
                    except Exception:
                        content = None
                if not content and hasattr(resp, "output") and resp.output:
                    try:
                        if isinstance(resp.output, list):
                            parts = []
                            for item in resp.output:
                                if getattr(item, "type", None) == "text":
                                    txt = getattr(item, "content", None)
                                    if isinstance(txt, str) and txt.strip():
                                        parts.append(txt.strip())
                            if parts:
                                content = " ".join(parts).strip()
                        elif isinstance(resp.output, str):
                            content = resp.output.strip()
                    except Exception:
                        pass
                if not content and hasattr(resp, "choices") and resp.choices:
                    try:
                        if len(resp.choices) > 0 and hasattr(resp.choices[0], "message") and resp.choices[0].message:
                            content = (resp.choices[0].message.content or "").strip()
                    except Exception:
                        pass
                if not content and hasattr(resp, "text") and resp.text is not None:
                    try:
                        value = getattr(resp.text, "value", None)
                        if isinstance(value, str):
                            candidate = value.strip()
                            if not candidate.startswith("ResponseTextConfig("):
                                content = candidate
                    except Exception:
                        pass
                if not content:
                    logger.warning("GPT-5 empty response after retry — triggering fallback")
                    raise RuntimeError("Empty LLM response from GPT-5")
                return content
            logger.error(f"OpenAI Responses request failed model={model_name} error={e}")
            raise

    async def _invoke_openai_gpt4o_new(self, model_name: str, kind: str, system_prompt: str, user_message: str) -> str:
        """GPT-4o (новые) — Chat Completions с max_completion_tokens и temperature."""
        client = self.openai_client
        temperature = 0.0 if kind == 'classification' else 0.7
        max_tokens = 20 if kind == 'classification' else 400
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        logger.info(f"OpenAI Chat payload: keys={list(payload.keys())}")
        try:
            resp = await client.chat.completions.create(**payload)
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                raise RuntimeError("Empty LLM response")
            return content
        except Exception as e:
            logger.error(f"OpenAI Chat request failed model={model_name} error={e}")
            raise

    async def _invoke_openai_chat_standard(self, model_name: str, kind: str, system_prompt: str, user_message: str) -> str:
        """Стандартные модели — Chat Completions с max_tokens и temperature."""
        client = self.openai_client
        temperature = 0.0 if kind == 'classification' else 0.7
        max_tokens = 20 if kind == 'classification' else 400
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        logger.info(f"OpenAI Chat payload: keys={list(payload.keys())}")
        try:
            resp = await client.chat.completions.create(**payload)
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                raise RuntimeError("Empty LLM response")
            return content
        except Exception as e:
            logger.error(f"OpenAI Chat request failed model={model_name} error={e}")
            raise

    async def _invoke_anthropic(self, model_name: str, kind: str, system_prompt: str, user_message: str) -> str:
        """Вызов Anthropic API."""
        if not self.config.ANTHROPIC_API_KEY:
            raise RuntimeError("Anthropic API key not set")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model_name,
            "max_tokens": 10 if kind == 'context' else (20 if kind == 'classification' else 400),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
            "temperature": 0.0 if kind in ('classification','context') else 0.7
        }

        r = await self.http_client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        # content: [{"type":"text","text":"..."}, ...]
        content = data.get('content', [])
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text'].strip()
        raise RuntimeError("Anthropic response format unexpected")

    async def aclose(self) -> None:
        """Закрывает общий HTTP клиент."""
        try:
            await self.http_client.aclose()
        except Exception:
            pass

    async def warmup(self) -> None:
        """Прогревает основные модели короткими запросами с минимальным расходом токенов."""
        try:
            # gpt-5-mini (через non-stream, маленький вывод)
            try:
                await self._invoke_openai_gpt5('gpt-5-mini', 'context', 'ok', 'ok')
            except Exception:
                pass
            # gpt-4o-mini (через chat, маленький вывод)
            try:
                await self._invoke_openai_chat_standard('gpt-4o-mini', 'context', 'ok', 'ok')
            except Exception:
                pass
        except Exception:
            pass
