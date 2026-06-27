"""Database engine + session helpers. Works with SQLite (default) or Postgres."""

from sqlmodel import SQLModel, Session, create_engine

from .config import settings

# SQLite needs check_same_thread=False to be used across FastAPI's threadpool.
_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    """Create tables if they do not exist. Safe to call repeatedly."""
    # Import models so SQLModel.metadata is populated before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a short-lived session."""
    with Session(engine) as session:
        yield session
