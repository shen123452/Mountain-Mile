from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "development-only-change-me"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/mountain_mile"
    dashscope_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen-plus"
    llm_fallback_model: str = "qwen-turbo"
    embedding_model: str = "text-embedding-v3"
    embedding_dim: int = 1024
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_public_base: str = ""
    token_price_input_per_1k: float = 0.0008   # qwen-plus 输入单价估算(元/千 token)
    token_price_output_per_1k: float = 0.002   # qwen-plus 输出单价估算(元/千 token)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def require_production_secret(self) -> "Settings":
        if self.app_env == "production" and self.secret_key == "development-only-change-me":
            raise ValueError("生产环境必须设置 SECRET_KEY")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
