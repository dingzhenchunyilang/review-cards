"""Database engine, session factory and initialization helpers."""
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# PROJECT_ROOT/backend/app/database.py -> PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB_PATH = DATA_DIR / "flashcards.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"

DATABASE_URL = DEFAULT_DB_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and ensure the default category exists."""
    from app import models  # noqa: F401  (register mappers before create_all)
    from app.services import categories as category_service

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        category_service.ensure_default_category(db)


def reset_database_url(url: str) -> None:
    """Rebind the module-level engine/session factory (used by tests)."""
    global DATABASE_URL, engine, SessionLocal
    DATABASE_URL = url
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False}
        if url.startswith("sqlite")
        else {},
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


__all__ = [
    "Base",
    "DATA_DIR",
    "DATABASE_URL",
    "DEFAULT_CATEGORY_ID",
    "DEFAULT_CATEGORY_NAME",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
    "reset_database_url",
    "text",
]

DEFAULT_CATEGORY_ID = 1
DEFAULT_CATEGORY_NAME = "未分类"
