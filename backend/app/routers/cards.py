"""Card routes — request/response only, logic lives in services."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CardCreate, CardOut, CardPage, CardRestore, CardUpdate
from app.services import cards as service

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=CardPage)
def list_cards(
    category_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
    db: Session = Depends(get_db),
):
    return service.list_cards(db, category_id, keyword, page, page_size)


@router.post("", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def create_card(payload: CardCreate, db: Session = Depends(get_db)):
    return service.create_card(db, payload.question, payload.answer, payload.category_id)


@router.post("/restore", response_model=CardOut, status_code=status.HTTP_201_CREATED)
def restore_card(payload: CardRestore, db: Session = Depends(get_db)):
    """Undo a deletion by re-inserting the card snapshot."""
    return service.restore_card(
        db,
        card_id=payload.id,
        question=payload.question,
        answer=payload.answer,
        category_id=payload.category_id,
        review_count=payload.review_count,
    )


@router.get("/{card_id}", response_model=CardOut)
def get_card(card_id: int, db: Session = Depends(get_db)):
    return service.get_card_or_404(db, card_id)


@router.put("/{card_id}", response_model=CardOut)
def update_card(card_id: int, payload: CardUpdate, db: Session = Depends(get_db)):
    return service.update_card(
        db, card_id, payload.question, payload.answer, payload.category_id
    )


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: int, db: Session = Depends(get_db)):
    service.delete_card(db, card_id)
    return None


@router.post("/{card_id}/reviewed", response_model=CardOut)
def mark_reviewed(card_id: int, db: Session = Depends(get_db)):
    return service.mark_reviewed(db, card_id)
