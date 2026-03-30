# backend/app/models/response.py
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion
    from app.models.option import Option


class Response(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("session_id", "screen_question_id", name="uq_session_question"),
    )

    id: int | None = Field(default=None, primary_key=True)
    screen_question_id: int = Field(foreign_key="screenquestion.id", index=True)
    option_id: int = Field(foreign_key="option.id")
    session_id: str = Field(max_length=36, index=True)
    followup_text: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utcnow)

    question: Optional["ScreenQuestion"] = Relationship(back_populates="responses")
    option: Optional["Option"] = Relationship(back_populates="responses")
