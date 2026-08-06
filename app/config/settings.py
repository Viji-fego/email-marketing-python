"""
Application Settings

Loads configuration from environment variables.
All settings are centralized here for easy management.
"""

import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration settings."""

    # ============================================================================
    # Brevo (Email Service Provider)
    # ============================================================================
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL: str = os.getenv("BREVO_SENDER_EMAIL", "")
    BREVO_SENDER_NAME: str = os.getenv("BREVO_SENDER_NAME", "University Outreach")

    # ============================================================================
    # Server Configuration
    # ============================================================================
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # ============================================================================
    # Email Tracking Configuration
    # ============================================================================
    OPEN_PREFETCH_THRESHOLD_SECONDS: int = int(os.getenv("OPEN_PREFETCH_THRESHOLD_SECONDS", "10"))
    # Opens faster than this threshold are flagged as likely prefetch by mail providers

    # ============================================================================
    # Database Configuration (Individual Variables - Node.js Style)
    # ============================================================================
    DB_DRIVER: str = os.getenv("DB_DRIVER", "mysql+pymysql")
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "email_marketing_python")

    @property
    def DATABASE_URL(self) -> str:
        """
        Construct SQLAlchemy database URL from individual environment variables.

        Format: driver://user:password@host:port/database
        Example: mysql+pymysql://root@127.0.0.1:3306/email_marketing_python

        User and password are percent-encoded so that reserved URL
        characters (@, :, /, %, ...) in either one don't get misread as
        part of the host — e.g. a password like "K4d4p@kk4m" would
        otherwise truncate at the "@" and break the connection.
        """
        user_part = quote_plus(self.DB_USER)
        password_part = f":{quote_plus(self.DB_PASSWORD)}" if self.DB_PASSWORD else ""
        return f"{self.DB_DRIVER}://{user_part}{password_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # ============================================================================
    # JWT (Authentication)
    # ============================================================================
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-insecure-default-change-me-in-env-file-32bytes")
    JWT_EXPIRES_HOURS: int = int(os.getenv("JWT_EXPIRES_HOURS", "8"))
    JWT_ALGORITHM: str = "HS256"

    # ============================================================================
    # Application Info
    # ============================================================================
    APP_NAME: str = "University Outreach — Python API"
    APP_VERSION: str = "0.2.0"
    APP_DESCRIPTION: str = "Email outreach API for university student engagement"

    def __repr__(self) -> str:
        """String representation of settings."""
        return (
            f"Settings(\n"
            f"  APP_NAME={self.APP_NAME}\n"
            f"  DATABASE={self.DB_NAME}\n"
            f"  DB_HOST={self.DB_HOST}\n"
            f"  PORT={self.PORT}\n"
            f")"
        )


# Create singleton instance
settings = Settings()
