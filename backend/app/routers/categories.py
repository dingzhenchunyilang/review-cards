"""Category routes — request/response only, logic lives in services."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import categories as service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return service.list_categories(db)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    cat = service.create_category(db, payload.name)
    return service.category_payload(db, cat)


@router.put("/{category_id}", response_model=CategoryOut)
def rename_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
):
    cat = service.rename_category(db, category_id, payload.name)
    return service.category_payload(db, cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    service.delete_category(db, category_id)
    return None
