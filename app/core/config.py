"""Application configuration.

A single typed settings object, populated from environment variables (and the
local ``.env`` file in development). Import ``settings`` everywhere; never read
``os.environ`` directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    app_name: str = "xuanwu"
    log_level: str = "info"
    cors_origins: str = "http://localhost:3000"  # comma-separated

    # --- Database (MySQL 8) ---
    database_url: str
    database_url_sync: str

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # --- Crypto / secrets ---
    secret_key: str
    blind_index_key: str
    jwt_private_key_path: str = "config/keys/jwt_private.pem"
    jwt_public_key_path: str = "config/keys/jwt_public.pem"

    # --- Token / session policy ---
    access_token_ttl: int = 900  # 15 minutes
    refresh_token_ttl: int = 604800  # 7 days
    login_max_attempts: int = 5
    login_lockout_ttl: int = 900  # 15 minutes

    # --- Password policy ---
    password_min_length: int = 8
    password_max_length: int = 80

    # --- Email ---
    email_provider: str = "smtp"
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    email_from: str = "no-reply@rarevintage.com.au"
    sendgrid_api_key: str = ""

    # --- SMS ---
    sms_provider: str = "mock"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""

    # --- Object storage ---
    storage_provider: str = "local"
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "xuanwu-dev"
    s3_region: str = "us-east-1"

    # --- Captcha ---
    captcha_provider: str = "none"
    recaptcha_secret: str = ""
    recaptcha_site_key: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    # Values are supplied at runtime via the environment / .env file.
    return Settings()


settings = get_settings()
