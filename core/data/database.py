import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.data.models import create_tables

load_dotenv()


def get_database_url() -> str:
    required = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Check your .env file."
        )

    # URL-encode password to handle special characters like @, !, #
    password = quote_plus(os.getenv("DB_PASSWORD"))

    return (
        f"postgresql://{os.getenv('DB_USER')}:{password}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )


def get_engine():
    """Create and return SQLAlchemy engine."""
    url = get_database_url()
    engine = create_engine(url, echo=False)
    logger.debug(f"Database engine created: {os.getenv('DB_NAME')}")
    return engine


def get_session() -> Session:
    """
    Get a database session.

    Usage:
        with get_session() as session:
            session.add(record)
            session.commit()
    """
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def init_database():
    """
    Initialize database — create all tables if they don't exist.
    Safe to run multiple times.
    """
    engine = get_engine()
    create_tables(engine)
    logger.success("Database initialized — all tables created")
