import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "code_intelligence"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/code_intelligence"

    # Redis/Celery Configuration
    REDIS_URL: str = "redis://redis:6379/0"

    # OpenSearch Configuration
    OPENSEARCH_HOST: str = "opensearch"
    OPENSEARCH_PORT: int = 9200
    OPENSEARCH_USER: str = "admin"
    OPENSEARCH_PASSWORD: str = "AdminPassword123!"
    DISABLE_SECURITY: bool = True

    # Ollama / AI Configuration
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:1.5b"

    # Local Storage
    DATA_DIR: str = "/workspace/data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Instantiate settings
settings = Settings()

# Ensure storage directories exist
os.makedirs(os.path.join(settings.DATA_DIR, "repos"), exist_ok=True)
os.makedirs(os.path.join(settings.DATA_DIR, "indices"), exist_ok=True)
