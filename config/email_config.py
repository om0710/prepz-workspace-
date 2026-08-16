import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    class EmailConfig(BaseSettings):
        GMAIL_USERNAME: Optional[str] = os.getenv("GMAIL_USERNAME") or os.getenv("SMTP_USER")
        GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD")
        MAIL_FROM: str = os.getenv("MAIL_FROM") or os.getenv("SMTP_FROM", "BU Prepz AI <noreply@prepz.app>")
        MAIL_SERVER: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        MAIL_PORT: int = int(os.getenv("SMTP_PORT", 587))
        MAIL_STARTTLS: bool = True
        MAIL_SSL_TLS: bool = False
        MAIL_TIMEOUT: int = 10

        class Config:
            extra = "ignore"
            env_file = ".env"

    email_config = EmailConfig()
except Exception:
    class EmailConfigFallback:
        GMAIL_USERNAME: Optional[str] = os.getenv("GMAIL_USERNAME") or os.getenv("SMTP_USER")
        GMAIL_APP_PASSWORD: Optional[str] = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD")
        MAIL_FROM: str = os.getenv("MAIL_FROM") or os.getenv("SMTP_FROM", "BU Prepz AI <noreply@prepz.app>")
        MAIL_SERVER: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        MAIL_PORT: int = int(os.getenv("SMTP_PORT", 587))
        MAIL_STARTTLS: bool = True
        MAIL_SSL_TLS: bool = False
        MAIL_TIMEOUT: int = 10

    email_config = EmailConfigFallback()
