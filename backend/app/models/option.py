# backend/app/models/option.py
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion
    from app.models.response import Response


class Option(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    screen_question_id: int = Field(foreign_key="screenquestion.id", index=True)
    label: str = Field(max_length=200)
    source_type: str = Field(default="upload", max_length=10)  # "upload" or "url"
    image_filename: str | None = Field(default=None, max_length=255)
    original_filename: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2000)
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)

    question: Optional["ScreenQuestion"] = Relationship(back_populates="options")
    responses: list["Response"] = Relationship(
        back_populates="option",
        cascade_delete=True,
    )
