from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache
def get_settings():
    return EnvSettings()


@lru_cache
def get_celery_settings():
    return CelerySettings(_env_file='.env', _env_file_encoding='utf-8')


class Settings(BaseSettings):
    app_name: str = 'Agent Service APP'


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')

    CELERY_BROKER_URL: str = Field(..., env='CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND: str = Field(..., env='CELERY_RESULT_BACKEND')
    task_default_queue: str = 'default'
    task_routes: dict = {
        'app.tasks.music.*': {'queue': 'music'},
    }

    # Serializers
    task_serializer: str = 'json'
    accept_content: list[str] = ['json']
    result_serializer: str = 'json'
    result_expires: int = 60 * 60 * 8  # 8 hours
    result_persistent: bool = False

    # acks
    task_acks_late: bool = True
    task_acks_on_failure_or_timeout: bool = True
    task_reject_on_worker_lost: bool = True
    task_default_delivery_mode: str = 'persistent'  # 2

    # Performance/Backpressure
    worker_prefetch_multiplier: int = 1
    task_time_limit: int = 600  # hard limit
    task_soft_time_limit: int = 540  # soft limit
    broker_connection_retry_on_startup: bool = True
    timezone: str = 'UTC'
    enable_utc: bool = True

    num_retries: int = 3
    retry_backoff_max: int = 600


class EnvSettings(Settings):
    model_config = SettingsConfigDict(
        extra='ignore',
        env_file=('app-config.conf', '.env'),
        env_file_encoding='utf-8',
    )

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
celery_config = get_celery_settings()
