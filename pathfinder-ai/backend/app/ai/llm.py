"""LLM provider abstraction (OpenAI / Gemini via LangChain) with safe fallbacks.

Design rules:
  * Every structured call is validated against a Pydantic schema; invalid output is
    treated like a provider failure and the caller falls back to the deterministic engine.
  * Missing API keys are not an error: ``available`` is False and features degrade gracefully.
  * Rate limits and timeouts surface as typed errors, never raw stack traces.
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.errors import AIProviderError, InvalidAIOutput, RateLimited

log = logging.getLogger("pathfinder.llm")
T = TypeVar("T", bound=BaseModel)


class LLMClient:
    def __init__(self) -> None:
        s = get_settings()
        self.provider = s.resolved_llm_provider
        self.timeout = s.llm_timeout_seconds
        self._chat = None
        if s.langsmith_api_key:  # LangSmith tracing is picked up by LangChain from env vars
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_API_KEY", s.langsmith_api_key)
            os.environ.setdefault("LANGCHAIN_PROJECT", s.langsmith_project)

    @property
    def available(self) -> bool:
        return self.provider != "none"

    @property
    def model_name(self) -> str:
        s = get_settings()
        return {"openai": s.openai_model, "gemini": s.gemini_model}.get(self.provider, "offline-rules")

    def _model(self, temperature: float = 0.2):
        if self._chat is not None:
            return self._chat
        s = get_settings()
        if self.provider == "openai":
            from langchain_openai import ChatOpenAI

            self._chat = ChatOpenAI(model=s.openai_model, api_key=s.openai_api_key, temperature=temperature,
                                    timeout=self.timeout, max_retries=2)
        elif self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            self._chat = ChatGoogleGenerativeAI(model=s.gemini_model, google_api_key=s.gemini_api_key,
                                                temperature=temperature, timeout=self.timeout, max_retries=2)
        else:
            raise AIProviderError("No AI provider is configured.", code="ai_not_configured")
        return self._chat

    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        text = f"{type(exc).__name__}: {exc}".lower()
        if "rate" in text and "limit" in text or "429" in text or "quota" in text:
            return RateLimited("The AI provider is rate-limiting requests. Please try again in a minute.")
        if "timeout" in text or "timed out" in text:
            return AIProviderError("The AI provider took too long to respond.", code="ai_timeout")
        if "api key" in text or "401" in text or "authentication" in text:
            return AIProviderError("The AI provider rejected the API key. Check your configuration.", code="ai_auth")
        return AIProviderError("The AI provider is unavailable right now.")

    async def structured(self, system: str, user: str, schema: type[T]) -> T:
        from langchain_core.messages import HumanMessage, SystemMessage

        model = self._model().with_structured_output(schema)
        try:
            result = await asyncio.wait_for(model.ainvoke([SystemMessage(system), HumanMessage(user)]), timeout=self.timeout)
        except ValidationError as exc:
            raise InvalidAIOutput("The AI returned data in an unexpected format.") from exc
        except asyncio.TimeoutError as exc:
            raise AIProviderError("The AI provider took too long to respond.", code="ai_timeout") from exc
        except Exception as exc:  # provider SDK errors
            log.warning("structured LLM call failed: %s", exc)
            raise self._map_error(exc) from exc
        if isinstance(result, dict):
            try:
                result = schema.model_validate(result)
            except ValidationError as exc:
                raise InvalidAIOutput("The AI returned data in an unexpected format.") from exc
        if not isinstance(result, schema):
            raise InvalidAIOutput("The AI returned data in an unexpected format.")
        return result

    async def stream(self, system: str, history: list[tuple[str, str]], user: str) -> AsyncIterator[str]:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        msgs = [SystemMessage(system)]
        for role, content in history[-10:]:
            msgs.append(HumanMessage(content) if role == "user" else AIMessage(content))
        msgs.append(HumanMessage(user))
        try:
            async for chunk in self._model(0.4).astream(msgs):
                text = chunk.content if isinstance(chunk.content, str) else "".join(
                    p.get("text", "") for p in chunk.content if isinstance(p, dict))
                if text:
                    yield text
        except Exception as exc:
            log.warning("streaming LLM call failed: %s", exc)
            raise self._map_error(exc) from exc


async def try_structured(system: str, user: str, schema: type[T]) -> T | None:
    """Structured call that returns None (instead of raising) when AI is unavailable or fails."""
    client = get_llm()
    if not client.available:
        return None
    try:
        return await client.structured(system, user, schema)
    except (AIProviderError, InvalidAIOutput, RateLimited) as exc:
        log.info("AI enrichment skipped: %s", exc.message)
        return None


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
