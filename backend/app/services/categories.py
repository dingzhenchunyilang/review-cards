"""Category business logic."""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import DEFAULT_CATEGORY_ID, DEFAULT_CATEGORY_NAME


def ensure_default_category(db: Session) -> models.Category:
    """Create the default category if missing. Fixed id, rename-protected."""
    cat = db.get(models.Category, DEFAULT_CATEGORY_ID)
    if cat is None:
        existing = db.scalar(
            select(models.Category).where(models.Category.name == DEFAULT_CATEGORY_NAME)
        )
        if existing is not None:
            return existing
        cat = models.Category(id=DEFAULT_CATEGORY_ID, name=DEFAULT_CATEGORY_NAME)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat


def list_categories(db: Session) -> list[dict]:
    """Return all categories with card counts, default category first."""
    counts = dict(
        db.execute(
            select(models.Card.category_id, func.count(models.Card.id)).group_by(
                models.Card.category_id
            )
        ).all()
    )
    rows = db.scalars(
        select(models.Category).order_by(models.Category.id)
    ).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "created_at": c.created_at,
            "card_count": counts.get(c.id, 0),
        }
        for c in rows
    ]


def create_category(db: Session, name: str) -> models.Category:
    name = name.strip()
    _assert_name_available(db, name)
    cat = models.Category(name=name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def rename_category(db: Session, category_id: int, name: str) -> models.Category:
    cat = get_category_or_404(db, category_id)
    name = name.strip()
    if cat.id == DEFAULT_CATEGORY_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"「{DEFAULT_CATEGORY_NAME}」不允许重命名",
        )
    if name != cat.name:
        _assert_name_available(db, name)
    cat.name = name
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, category_id: int) -> None:
    cat = get_category_or_404(db, category_id)
    if cat.id == DEFAULT_CATEGORY_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"「{DEFAULT_CATEGORY_NAME}」不允许删除",
        )
    db.query(models.Card).filter(models.Card.category_id == cat.id).update(
        {models.Card.category_id: DEFAULT_CATEGORY_ID}, synchronize_session=False
    )
    db.delete(cat)
    db.commit()


def get_category_or_404(db: Session, category_id: int) -> models.Category:
    cat = db.get(models.Category, category_id)
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类 {category_id} 不存在",
        )
    return cat


def category_payload(db: Session, cat: models.Category) -> dict:
    """Serialize one category with its card count (single targeted COUNT)."""
    card_count = db.scalar(
        select(func.count(models.Card.id)).where(models.Card.category_id == cat.id)
    ) or 0
    return {
        "id": cat.id,
        "name": cat.name,
        "created_at": cat.created_at,
        "card_count": card_count,
    }


def _assert_name_available(db: Session, name: str) -> None:
    existing = db.scalar(select(models.Category).where(models.Category.name == name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类名「{name}」已存在",
        )
