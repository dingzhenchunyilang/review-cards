"""Review routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CardOut
from app.services import cards as service

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/random", response_model=CardOut | None)
def random_card(
    category_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return a random card, or null when the pool is empty (never errors)."""
    return service.pick_random_card(db, category_id)
