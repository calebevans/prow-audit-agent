"""Database schema utilities and initialization."""

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine

from .models import Base


def get_database_url(db_path: Optional[Path] = None) -> str:
    """Get the SQLite database URL.

    Args:
        db_path: Optional path to database file

    Returns:
        SQLite database URL
    """
    if db_path is None:
        db_path = Path("prow_audit.db")

    return f"sqlite:///{db_path.absolute()}"


def initialize_database(db_path: Optional[Path] = None) -> str:
    """Initialize the database schema.

    Args:
        db_path: Optional path to database file

    Returns:
        Database URL
    """
    database_url = get_database_url(db_path)
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return database_url


def drop_all_tables(database_url: str) -> None:
    """Drop all tables in the database.

    Args:
        database_url: SQLAlchemy database URL

    Warning:
        This will delete all data!
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.drop_all(engine)
