"""Card business logic."""
import random

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.database import DEFAULT_CATEGORY_ID
from app.services.categories import get_category_or_404

MAX_PAGE_SIZE = 200


def list_cards(
    db: Session,
    category_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    if category_id is not None:
        get_category_or_404(db, category_id)

    stmt = select(models.Card)
    count_stmt = select(func.count(models.Card.id))

    if category_id is not None:
        stmt = stmt.where(models.Card.category_id == category_id)
        count_stmt = count_stmt.where(models.Card.category_id == category_id)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(models.Card.question.like(like))
        count_stmt = count_stmt.where(models.Card.question.like(like))

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(models.Card.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


def create_card(
    db: Session, question: str, answer: str, category_id: int | None = None
) -> models.Card:
    question, answer = _validate_text(question, answer)
    target_id = _resolve_category(db, category_id)
    card = models.Card(category_id=target_id, question=question, answer=answer)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def get_card_or_404(db: Session, card_id: int) -> models.Card:
    card = db.get(models.Card, card_id)
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"卡片 {card_id} 不存在"
        )
    return card


def update_card(
    db: Session,
    card_id: int,
    question: str | None = None,
    answer: str | None = None,
    category_id: int | None = None,
) -> models.Card:
    card = get_card_or_404(db, card_id)

    if question is not None:
        question = question.strip()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="题目不能为空"
            )
        card.question = question
    if answer is not None:
        answer = answer.strip()
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="答案不能为空"
            )
        card.answer = answer
    if category_id is not None:
        card.category_id = _resolve_category(db, category_id)

    db.commit()
    db.refresh(card)
    return card


def delete_card(db: Session, card_id: int) -> None:
    card = get_card_or_404(db, card_id)
    db.delete(card)
    db.commit()


def restore_card(
    db: Session,
    *,
    question: str,
    answer: str,
    card_id: int | None = None,
    category_id: int | None = None,
    review_count: int = 0,
) -> models.Card:
    """Re-insert a deleted card, used by the UI undo.

    Keeps the original id (and therefore its list position) when that id is
    still free, and always keeps review_count. Falls back to the default
    category if the original one has been deleted in the meantime.
    """
    question, answer = _validate_text(question, answer)

    target_id = (
        category_id
        if category_id is not None and db.get(models.Category, category_id) is not None
        else DEFAULT_CATEGORY_ID
    )
    resolved_id = card_id if card_id and db.get(models.Card, card_id) is None else None

    card = models.Card(
        id=resolved_id,
        category_id=target_id,
        question=question,
        answer=answer,
        review_count=max(0, review_count),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def pick_random_card(db: Session, category_id: int | None = None) -> models.Card | None:
    """Return a random card, or None when the pool is empty."""
    if category_id is not None:
        get_category_or_404(db, category_id)

    stmt = select(models.Card.id)
    if category_id is not None:
        stmt = stmt.where(models.Card.category_id == category_id)

    ids = db.scalars(stmt).all()
    if not ids:
        return None
    return db.get(models.Card, random.choice(list(ids)))


def mark_reviewed(db: Session, card_id: int) -> models.Card:
    card = get_card_or_404(db, card_id)
    card.review_count += 1
    db.commit()
    db.refresh(card)
    return card


def count_reviewed_total(db: Session) -> int:
    return db.scalar(select(func.coalesce(func.sum(models.Card.review_count), 0))) or 0


def _validate_text(question: str, answer: str) -> tuple[str, str]:
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="题目不能为空"
        )
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="答案不能为空"
        )
    return question, answer


def _resolve_category(db: Session, category_id: int | None) -> int:
    if category_id is None:
        return DEFAULT_CATEGORY_ID
    get_category_or_404(db, category_id)
    return category_id
