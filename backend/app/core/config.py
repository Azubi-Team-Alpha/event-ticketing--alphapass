from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Ticket Hub API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str
    DB_SCHEMA: str = "ticket_hub"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AWS
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "ticket-hub-dev"
    SES_SENDER_EMAIL: str = "noreply@ticket-hub.com"

    # Platform settings (can be overridden via DB)
    PLATFORM_COMMISSION_PERCENT: float = 5.0  # 5% default
    REQUIRE_EVENT_APPROVAL: bool = False       # if True, events go to pending first

    # Email verification
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 2

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()  # type: ignore
