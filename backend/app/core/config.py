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
    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        # 兼容 JSON 数组格式；通常项目初期使用逗号分隔即可。
        if value.startswith("[") and value.endswith("]"):
            import json

            parsed_value = json.loads(value)
            if not isinstance(parsed_value, list):
                raise ValueError(
                    "BACKEND_CORS_ORIGINS 的 JSON 配置必须是字符串数组。"
                )
            return [str(item).strip() for item in parsed_value if str(item).strip()]

        return [item.strip() for item in value.split(",") if item.strip()]

    return value


CorsOrigins = Annotated[
    list[str],
    NoDecode,
    BeforeValidator(parse_cors_origins),
]


class Settings(BaseSettings):
    """应用运行配置，从环境变量及 .env 文件中读取。"""

    # -------------------------
    # Application
    # -------------------------
    PROJECT_NAME: str = "ThinkTank Monitor"
    API_V1_STR: str = "/api/v1"

    # -------------------------
    # PostgreSQL
    # Docker 容器内部使用主机名 postgres；
    # 本机直接运行时使用 localhost。
    # -------------------------
    POSTGRES_USER: str = "thinktank"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "thinktank_monitor"
    DATABASE_URL: str

    # -------------------------
    # Redis / Celery
    # -------------------------
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # -------------------------
    # MinIO
    # -------------------------
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "thinktank-documents"
    MINIO_SECURE: bool = False

    # -------------------------
    # Security
    # -------------------------
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=120,
        gt=0,
    )

    # -------------------------
    # CORS
    # -------------------------
    BACKEND_CORS_ORIGINS: CorsOrigins = [
        "http://localhost:3000",
    ]

    # -------------------------
    # LLM / Translation
    # -------------------------
    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # -------------------------
    # Crawler
    # -------------------------
    CRAWLER_USER_AGENT: str = "ThinkTankMonitor/0.1"
    CRAWLER_REQUEST_TIMEOUT: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        # 从 backend/ 执行时读取 .env 和 ../.env；
        # 从 Docker 容器执行时，Compose 的 env_file 会注入环境变量。
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()