from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = "policy-compliance-agent"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    policy_data_dir: str = "data/policies"
    local_store_path: str = "storage/chunks.jsonl"
    analytics_path: str = "storage/analytics.json"
    allowed_origins: str = "http://localhost:4173,http://127.0.0.1:4173"
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "policy-compliance-agent"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def policy_dir(self) -> Path:
        path = Path(self.policy_data_dir)
        return path if path.is_absolute() else self.base_dir / path

    @property
    def local_store(self) -> Path:
        path = Path(self.local_store_path)
        return path if path.is_absolute() else self.base_dir / path

    @property
    def analytics_file(self) -> Path:
        path = Path(self.analytics_path)
        return path if path.is_absolute() else self.base_dir / path

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def configure_langsmith(self) -> None:
        if not self.langsmith_tracing:
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
        os.environ["LANGSMITH_ENDPOINT"] = self.langsmith_endpoint
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = self.langsmith_project
        if self.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.configure_langsmith()
    return settings
