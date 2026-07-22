from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AlphaPass API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AWS
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "alphapass-assets-dev"
    SES_SENDER_EMAIL: str = "noreply@alphapass.alphateam.live"

    # DynamoDB Table Names (resolved from environment variables injected by Lambda/Terraform)
    EVENTS_TABLE: str = "alphapass-events-dev"
    REGISTRATIONS_TABLE: str = "alphapass-registrations-dev"
    ORGANIZERS_TABLE: str = "alphapass-organizers-dev"
    ADMINS_TABLE: str = "alphapass-admins-dev"
    ORDERS_TABLE: str = "alphapass-orders-dev"
    TICKETS_TABLE: str = "alphapass-tickets-dev"
    PROMO_CODES_TABLE: str = "alphapass-promo-codes-dev"
    RESALE_LISTINGS_TABLE: str = "alphapass-resale-listings-dev"
    TRANSFERS_TABLE: str = "alphapass-transfers-dev"
    PAYOUTS_TABLE: str = "alphapass-payouts-dev"
    PLATFORM_SETTINGS_TABLE: str = "alphapass-platform-settings-dev"
    AUDIT_LOGS_TABLE: str = "alphapass-audit-logs-dev"
    EVENT_CATEGORIES_TABLE: str = "alphapass-event-categories-dev"

    # SNS
    CONFIRMATION_TOPIC: str = ""

    # Platform settings
    PLATFORM_COMMISSION_PERCENT: float = 5.0
    REQUIRE_EVENT_APPROVAL: bool = False

    # Email verification
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 2

    # Frontend URL (for email links)
    FRONTEND_URL: str = "https://alphapass.alphateam.live"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()  # type: ignore
