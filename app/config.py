from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache
def get_settings():
    return EnvSettings()


class Settings(BaseSettings):
    app_name: str = "Agent Service APP"


class EnvSettings(Settings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=("app-config.conf", ".env"),
        env_file_encoding="utf-8",
    )
    # BOT
    DISCORD_TOKEN: str = Field(env="DISCORD_TOKEN")
    YOUTUBE_TOKEN: str = Field(env="YOUTUBE_TOKEN")
    LLM_API_KEY: str = Field(env="LLM_API_KEY")
    LLM_MAX_TOKENS: int = Field(env="LLM_MAX_TOKENS", default=5000)
    LLM_MODEL: str = Field(env="LLM_MODEL", default="gpt-5.4-mini")
    LLM_MAX_RESPONSE_TOKENS: int = Field(env="LLM_MAX_RESPONSE_TOKENS", default=500)
    DEFAULT_VOLUME: float = Field(env="DEFAULT_VOLUME", default=0.5)
    IDLE_DISCONNECT_SECONDS: int = Field(env="IDLE_DISCONNECT_SECONDS", default=5 * 60)

    STORAGE_PATH: str = Field(env="STORAGE_PATH", default="./tmp/music")

    LOG_LEVEL: str = Field(env="LOG_LEVEL", default="INFO")

    # Database
    POSTGRES_USER: str = Field(env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(env="POSTGRES_DB")
    POSTGRES_HOST: str = Field(env="POSTGRES_HOST", default="localhost")
    POSTGRES_PORT: int = Field(env="POSTGRES_PORT", default=5432)

    @property
    def POSTGRES_DB_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Logger
    LOG_PATH: str = Field(env="LOG_PATH", default="logs/app_log.json")
    LOG_FORMAT: str = Field(
        env="LOG_FORMAT",
        default="{time} | {level} | {name}:{function}:{line} | {message}",
    )

    # REDIS
    REDIS_URL: str = Field(env="REDIS_URL", default="redis://localhost:6379/0")


config = get_settings()
