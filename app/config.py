import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "University Outreach")
    PORT = int(os.getenv("PORT", "8000"))

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-default-change-me-in-env-file-32bytes")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "8"))


settings = Settings()
