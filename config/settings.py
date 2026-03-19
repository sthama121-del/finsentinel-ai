"""
FinSentinel AI - Central Configuration
LLM Provider-Agnostic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional, Literal
from functools import lru_cache


class Settings(BaseSettings):
    # ─── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "FinSentinel AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    # ─── LLM Provider (Pluggable) ──────────────────────────────────────────────
    LLM_PROVIDER: Literal["ollama", "openai", "anthropic", "azure_openai"] = "ollama"
    LLM_MODEL: str = "mistral:7b-instruct"          # Default: Ollama model
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 120

    # Ollama (Local - Default)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # OpenAI (Optional Cloud)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"

    # Anthropic (Optional Cloud)
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Azure OpenAI (Optional Cloud)
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # ─── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_STORE: Literal["chroma", "qdrant", "azure_cognitive_search"] = "chroma"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    AZURE_SEARCH_ENDPOINT: Optional[str] = None
    AZURE_SEARCH_KEY: Optional[str] = None
    AZURE_SEARCH_INDEX: str = "finsentinel-index"

    # ─── Event Streaming ────────────────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_TRANSACTIONS: str = "fin.transactions.raw"
    KAFKA_TOPIC_ALERTS: str = "fin.alerts"
    KAFKA_TOPIC_AUDIT: str = "fin.audit.logs"
    KAFKA_GROUP_ID: str = "finsentinel-consumer-group"

    # ─── Databases ────────────────────────────────────────────────────────────
    POSTGRES_URL: str = "postgresql://finuser:finpass@localhost:5432/finsentinel"
    REDIS_URL: str = "redis://localhost:6379/0"
    COSMOS_DB_URL: Optional[str] = None           # Azure Cosmos DB
    COSMOS_DB_KEY: Optional[str] = None

    # ─── Storage ─────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "azure_adls"] = "local"
    LOCAL_STORAGE_PATH: str = "./data"
    AZURE_ADLS_ACCOUNT: Optional[str] = None
    AZURE_ADLS_CONTAINER: str = "finsentinel-data"
    AZURE_ADLS_KEY: Optional[str] = None

    # ─── Security ────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-vault"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    PII_MASKING_ENABLED: bool = True
    AUDIT_LOG_ENABLED: bool = True

    # ─── Observability ───────────────────────────────────────────────────────
    OTEL_ENDPOINT: str = "http://localhost:4317"
    LOG_LEVEL: str = "INFO"
    PROMETHEUS_PORT: int = 8002

    # ─── Cache ───────────────────────────────────────────────────────────────
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL: int = 3600
    EMBEDDING_CACHE_ENABLED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
