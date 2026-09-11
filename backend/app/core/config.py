from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def parse_cors_origins(value: str | list[str]) -> list[str]:
    """
    支持以下两种 CORS 配置形式：

    1. 逗号分隔字符串：
       BACKEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

    2. JSON 数组：
       BACKEND_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        import json

        parsed_value = json.loads(value)

        if not isinstance(parsed_value, list):
            raise ValueError("BACKEND_CORS_ORIGINS 的 JSON 配置必须是字符串数组。")

        return [str(item).strip() for item in parsed_value if str(item).strip()]

    return [item.strip() for item in value.split(",") if item.strip()]


CorsOrigins = Annotated[
    list[str],
    NoDecode,
    BeforeValidator(parse_cors_origins),
]


class Settings(BaseSettings):
    """应用运行配置，从环境变量及 backend/.env 文件中读取。"""

    PROJECT_NAME: str = "ThinkTank Monitor"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = "thinktank"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "thinktank_monitor"
    DATABASE_URL: str

    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_DEFAULT_QUEUE: str = "celery"

    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "thinktank-documents"
    MINIO_SECURE: bool = False

    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=120,
        gt=0,
    )

    BACKEND_CORS_ORIGINS: CorsOrigins = [
        "http://localhost:3000",
    ]

    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_CONNECT_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0)
    LLM_READ_TIMEOUT_SECONDS: float = Field(default=300.0, gt=0)
    LLM_WRITE_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    LLM_POOL_TIMEOUT_SECONDS: float = Field(default=20.0, gt=0)
    AI_TRANSLATION_CHUNK_LENGTH: int = Field(default=5000, ge=1000, le=20000)
    AI_ANALYSIS_CHUNK_LENGTH: int = Field(default=16000, ge=4000, le=40000)
    AI_TRANSLATION_MAX_TOKENS: int = Field(default=9000, ge=1000, le=20000)

    CRAWLER_USER_AGENT: str = "ThinkTankMonitor/0.1"
    CRAWLER_REQUEST_TIMEOUT: int = Field(
        default=30,
        gt=0,
    )

    NOTIFICATION_DAILY_SUMMARY_ENABLED: bool = True
    NOTIFICATION_SUMMARY_LOOKBACK_HOURS: int = Field(default=24, ge=1, le=168)
    NOTIFICATION_EMAIL_ENABLED: bool = False
    NOTIFICATION_EMAIL_TO: str = ""
    NOTIFICATION_SMTP_HOST: str = ""
    NOTIFICATION_SMTP_PORT: int = Field(default=587, gt=0, le=65535)
    NOTIFICATION_SMTP_USERNAME: str = ""
    NOTIFICATION_SMTP_PASSWORD: str = ""
    NOTIFICATION_SMTP_FROM: str = ""
    NOTIFICATION_SMTP_USE_TLS: bool = True
    NOTIFICATION_WECOM_WEBHOOK_URL: str = ""
    NOTIFICATION_FEISHU_WEBHOOK_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
