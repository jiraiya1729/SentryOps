from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    DEBUG: bool = False
    APP_NAME: str = "SentryOps"

    DATABASE_URL: str = "postgresql+asyncpg://sentryops:sentryops@localhost:5432/sentryops"

    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "sentryops"


    REDIS_URL: str = "redis://localhost:6379"

    # AWS Bedrock
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "us.anthropic.claude-sonnet-4-6-20250514-v1:0"

    # Langfuse (optional)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    OTLP_GRPC_PORT: int = 4317
    PROMETHEUS_SCRAPE_INTERVAL: int = 30

    K8S_CONTEXT: str | None = None

    CORS_ORIGIN: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()