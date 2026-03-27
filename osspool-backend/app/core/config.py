from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str

    github_token: str

    redis_url: str = "redis://localhost:6379/0"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "usd"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    github_api_base: str = "https://api.github.com"
    github_rate_limit_buffer: int = 10

    ranking_cache_ttl: int = 300

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
