"""
FinSentinel AI - LLM Provider Factory
Pluggable, provider-agnostic LLM abstraction layer.
Supports: Ollama (local), OpenAI, Anthropic, Azure OpenAI
"""
from __future__ import annotations
import abc
import hashlib
import json
import logging
from typing import Any, AsyncIterator, Optional

import redis.asyncio as aioredis
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


# ─── Abstract Base ─────────────────────────────────────────────────────────────

class BaseLLMProvider(abc.ABC):
    """Abstract LLM provider. All concrete providers implement this interface."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @abc.abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        """Return a LangChain-compatible chat model."""

    @abc.abstractmethod
    def get_embedding_model(self) -> Any:
        """Return a LangChain-compatible embedding model."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""


# ─── Ollama Provider (Local / Default) ─────────────────────────────────────────

class OllamaProvider(BaseLLMProvider):
    """Local LLM via Ollama. Zero cost. Fully offline. CPU-compatible."""

    provider_name = "ollama"

    def get_chat_model(self) -> BaseChatModel:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=self.settings.OLLAMA_BASE_URL,
            model=self.settings.LLM_MODEL,
            temperature=self.settings.LLM_TEMPERATURE,
            num_predict=self.settings.LLM_MAX_TOKENS,
            timeout=self.settings.LLM_TIMEOUT,
        )

    def get_embedding_model(self) -> Any:
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(
            base_url=self.settings.OLLAMA_BASE_URL,
            model=self.settings.OLLAMA_EMBED_MODEL,
        )


# ─── OpenAI Provider ───────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def get_chat_model(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            model=self.settings.OPENAI_MODEL,
            temperature=self.settings.LLM_TEMPERATURE,
            max_tokens=self.settings.LLM_MAX_TOKENS,
            timeout=self.settings.LLM_TIMEOUT,
        )

    def get_embedding_model(self) -> Any:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(api_key=self.settings.OPENAI_API_KEY)


# ─── Anthropic Provider ────────────────────────────────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"

    def get_chat_model(self) -> BaseChatModel:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            api_key=self.settings.ANTHROPIC_API_KEY,
            model=self.settings.ANTHROPIC_MODEL,
            temperature=self.settings.LLM_TEMPERATURE,
            max_tokens=self.settings.LLM_MAX_TOKENS,
            timeout=self.settings.LLM_TIMEOUT,
        )

    def get_embedding_model(self) -> Any:
        # Anthropic doesn't provide embeddings; fall back to local
        logger.warning("Anthropic has no embedding API. Falling back to Ollama embeddings.")
        return OllamaProvider(self.settings).get_embedding_model()


# ─── Azure OpenAI Provider ─────────────────────────────────────────────────────

class AzureOpenAIProvider(BaseLLMProvider):
    provider_name = "azure_openai"

    def get_chat_model(self) -> BaseChatModel:
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=self.settings.AZURE_OPENAI_DEPLOYMENT,
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
            temperature=self.settings.LLM_TEMPERATURE,
            max_tokens=self.settings.LLM_MAX_TOKENS,
        )

    def get_embedding_model(self) -> Any:
        from langchain_openai import AzureOpenAIEmbeddings
        return AzureOpenAIEmbeddings(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            api_key=self.settings.AZURE_OPENAI_API_KEY,
            azure_deployment="text-embedding-3-large",
            api_version=self.settings.AZURE_OPENAI_API_VERSION,
        )


# ─── Factory ───────────────────────────────────────────────────────────────────

_PROVIDER_REGISTRY: dict[str, type[BaseLLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "azure_openai": AzureOpenAIProvider,
}


def get_llm_provider(settings: Optional[Settings] = None) -> BaseLLMProvider:
    """
    Factory: returns the configured LLM provider.
    Switch providers via LLM_PROVIDER env var — no code changes required.
    """
    settings = settings or get_settings()
    provider_key = settings.LLM_PROVIDER.lower()

    if provider_key not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown LLM provider '{provider_key}'. "
            f"Supported: {list(_PROVIDER_REGISTRY.keys())}"
        )

    provider_cls = _PROVIDER_REGISTRY[provider_key]
    provider = provider_cls(settings)
    logger.info(f"[LLM] Using provider: {provider.provider_name} | model: {settings.LLM_MODEL}")
    return provider


# ─── Cached LLM Client (with Redis semantic cache) ─────────────────────────────

class CachedLLMClient:
    """Wraps any provider with Redis-backed response caching to reduce latency/cost."""

    def __init__(self, provider: BaseLLMProvider, redis_url: str, ttl: int = 3600):
        self.model = provider.get_chat_model()
        self.redis_url = redis_url
        self.ttl = ttl
        self._redis: Optional[aioredis.Redis] = None

    async def _get_redis(self) -> aioredis.Redis:
        if not self._redis:
            self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _cache_key(self, messages: list[BaseMessage]) -> str:
        content = json.dumps([{"role": m.type, "content": m.content} for m in messages])
        return f"llm:cache:{hashlib.sha256(content.encode()).hexdigest()}"

    async def invoke(
        self,
        system_prompt: str,
        user_message: str,
        use_cache: bool = True,
    ) -> str:
        messages: list[BaseMessage] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        cache_key = self._cache_key(messages)

        if use_cache:
            redis = await self._get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.debug(f"[LLM Cache] HIT for key {cache_key[:16]}...")
                return cached

        response = await self.model.ainvoke(messages)
        result = response.content

        if use_cache:
            redis = await self._get_redis()
            await redis.setex(cache_key, self.ttl, result)

        return result
