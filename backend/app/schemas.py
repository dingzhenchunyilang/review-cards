"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_CATEGORY_ID = 1
DEFAULT_CATEGORY_NAME = "未分类"


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("分类名不能为空")
        return v


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    card_count: int = 0


# ---------- Card ----------
class CardBase(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)

    @field_validator("question", "answer")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("内容不能为空")
        return v


class CardCreate(CardBase):
    category_id: int = DEFAULT_CATEGORY_ID


class CardUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category_id: int | None = None

    @field_validator("question", "answer")
    @classmethod
    def strip_optional_text(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("内容不能为空")
        return v


class CardRestore(BaseModel):
    """Payload for undoing a card deletion.

    The UI keeps a snapshot of the deleted card and posts it back here so the
    original id and review_count survive the undo. `id` is honoured only when
    that id is still free; otherwise a fresh one is assigned.
    """

    id: int | None = None
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    category_id: int | None = None
    review_count: int = 0

    @field_validator("question", "answer")
    @classmethod
    def strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("内容不能为空")
        return v

    @field_validator("review_count")
    @classmethod
    def clamp_review_count(cls, v: int) -> int:
        return max(0, v)


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    question: str
    answer: str
    review_count: int
    created_at: datetime
    updated_at: datetime


class CardPage(BaseModel):
    items: list[CardOut]
    total: int
    page: int
    page_size: int
