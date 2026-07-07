"""SQLAlchemy declarative base for all database models.

Import this to create new ORM models:

    from database.base import Base
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for EV-DDSS database models."""
    pass
