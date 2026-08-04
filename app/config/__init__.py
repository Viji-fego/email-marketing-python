"""
Configuration Module

Centralized configuration, database, and constants for the application.

Usage:
    from app.config import settings, get_db
    from app.config import CAMPAIGN_STATUS_DRAFT, CONTACT_STATUS_SENT
"""

from app.config.settings import Settings, settings
from app.config.database import Base, engine, SessionLocal, get_db
from app.config import constants

__all__ = [
    # Settings
    "Settings",
    "settings",
    # Database
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    # Constants
    "constants",
]
