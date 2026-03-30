# backend/app/models/screen_question.py
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.test import Test
    from app.models.option import Option
    from app.models.response import Response


class ScreenQuestion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    test_id: int = Field(foreign_key="test.id", index=True)
    order: int = Field(default=0)
    title: str = Field(max_length=500)
    followup_prompt: str = Field(default="Why did you choose this?", max_length=500)
    followup_required: bool = Field(default=False)
    randomize_options: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)

    test: Optional["Test"] = Relationship(back_populates="questions")
    options: list["Option"] = Relationship(
        back_populates="question",
        cascade_delete=True,
    )
    responses: list["Response"] = Relationship(
        back_populates="question",
        cascade_delete=True,
    )
