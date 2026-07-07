"""Database session dependency for FastAPI.

Provides dependency injection helpers for obtaining database sessions
in API route handlers.
"""

from typing import Generator

from sqlalchemy.orm import Session

from database.connection import get_database


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Usage in route handlers:

        @router.get("/items")
        def list_items(db: Session = Depends(get_session)):
            ...

    Yields:
        A SQLAlchemy Session that is automatically closed after the request.
    """
    db = get_database()

    if not db.is_connected:
        raise RuntimeError("Database is not connected")

    with db.get_session() as session:
        yield session


# Convenience alias
get_db = get_session
"""Alias for get_session for shorter imports."""
