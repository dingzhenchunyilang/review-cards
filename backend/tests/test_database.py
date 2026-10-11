"""T2 — startup behaviour tests (in-memory engine rebinding)."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, models
from app.database import Base, DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME


def test_init_db_creates_tables_and_default_category(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)

    database.init_db()

    tables = set(inspect(engine).get_table_names())
    assert {"categories", "cards"} <= tables

    with TestingSession() as db:
        cat = db.get(models.Category, DEFAULT_CATEGORY_ID)
        assert cat is not None
        assert cat.name == DEFAULT_CATEGORY_NAME


def test_init_db_is_idempotent(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSession)

    database.init_db()
    database.init_db()

    with TestingSession() as db:
        count = db.execute(text("SELECT COUNT(*) FROM categories WHERE id = 1")).scalar()
        assert count == 1


def test_schema_has_expected_columns(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, future=True)
    Base.metadata.create_all(bind=engine)
    insp = inspect(engine)

    card_cols = {c["name"] for c in insp.get_columns("cards")}
    assert {
        "id",
        "category_id",
        "question",
        "answer",
        "review_count",
        "created_at",
        "updated_at",
    } <= card_cols

    cat_cols = {c["name"] for c in insp.get_columns("categories")}
    assert {"id", "name", "created_at"} <= cat_cols

    fks = insp.get_foreign_keys("cards")
    assert any(fk["referred_table"] == "categories" for fk in fks)
