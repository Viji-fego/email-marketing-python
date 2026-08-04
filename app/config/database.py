"""
Database Configuration

Sets up SQLAlchemy engine, session factory, and base class.
All database setup is centralized here.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.models.base import Base

# ============================================================================
# Database Engine Setup
# ============================================================================

# Determine if SQLite or MySQL based on driver
is_sqlite = settings.DB_DRIVER.startswith("sqlite")

# Connection arguments - SQLite needs special handling
connect_args = {"check_same_thread": False} if is_sqlite else {}

# Create engine with appropriate settings
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using
)

# ============================================================================
# Session Factory
# ============================================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# ============================================================================
# Dependency Injection
# ============================================================================


def get_db():
    """
    Database session dependency for FastAPI routes.

    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
