"""PostgreSQL database connection management for EV-DDSS.

Provides a DatabaseManager class that creates and manages the
SQLAlchemy engine and session factory using synchronous psycopg2.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.logger import logger
from config import get_settings


class DatabaseManager:
    """Manages the PostgreSQL database connection.

    Usage:
        db = DatabaseManager()
        db.connect()
        with db.get_session() as session:
            result = session.execute(text("SELECT 1"))
        db.disconnect()
    """

    def __init__(self, database_url: Optional[str] = None) -> None:
        """Initialize the database manager.

        Args:
            database_url: PostgreSQL connection string. Uses settings if not provided.
        """
        settings = get_settings()
        self._database_url: str = database_url or settings.database.url
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker[Session]] = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Whether the database engine is initialized and connected."""
        return self._connected

    def connect(self) -> None:
        """Create the database engine and session factory.

        Raises:
            Exception: If the connection fails.
        """
        settings = get_settings()
        self._engine = create_engine(
            self._database_url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_pre_ping=settings.database.pool_pre_ping,
            echo=settings.database.echo,
        )

        # Verify connectivity with a simple query
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT 1 AS health"))
                row = result.fetchone()
                if row and row[0] == 1:
                    logger.info("Database connection verified successfully")
                    self._connected = True
                else:
                    raise ConnectionError("Database health check returned unexpected result")
        except Exception as exc:
            logger.error("Database connection failed: {}", exc)
            self._connected = False
            raise

        self._session_factory = sessionmaker(bind=self._engine, class_=Session)

    def disconnect(self) -> None:
        """Dispose of the database engine and release resources."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._connected = False
            logger.info("Database connection closed")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a database session as a context manager.

        Yields:
            A SQLAlchemy Session instance.

        Raises:
            RuntimeError: If the database is not connected.
        """
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Module-level singleton
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Return the global DatabaseManager singleton.

    Returns:
        The DatabaseManager instance.
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
