from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache
def get_settings():
    return EnvSettings()


class Settings(BaseSettings):
    app_name: str = 'Agent Service APP'


class EnvSettings(Settings):
    model_config = SettingsConfigDict(
        extra='ignore',
        env_file=('app-config.conf', '.env'),
        env_file_encoding='utf-8',
    )
    # BOT
    DISCORD_TOKEN: str = Field(env='DISCORD_TOKEN')
    YOUTUBE_TOKEN: str = Field(env='YOUTUBE_TOKEN')
    DEFAULT_VOLUME: float = Field(env='DISCORD_TOKEN', default=0.5)
    IDLE_DISCONNECT_SECONDS: int = Field(env='DISCORD_TOKEN', default=5 * 60)

    LOG_LEVEL: str = Field(env='LOG_LEVEL', default='INFO')

    # Database
    POSTGRES_DB_URL: str = Field(env='POSTGRES_DB_URL')

    # Logger
    LOG_PATH: str = Field(env='LOG_PATH', default='logs/app_log.json')
    LOG_FORMAT: str = Field(
        env='LOG_FORMAT',
        default='{time} | {level} | {name}:{function}:{line} | {message}',
    )

    # REDIS
    REDIS_URL: str = Field(env='REDIS_URL', default='redis://localhost:6379/0')


config = get_settings()
