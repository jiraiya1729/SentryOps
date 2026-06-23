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

    K8S_CONTEXT: str | None = None

    CORS_ORIGIN: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()