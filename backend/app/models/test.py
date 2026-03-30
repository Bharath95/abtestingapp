# backend/app/models/test.py
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion


def generate_slug() -> str:
    return secrets.token_urlsafe(8)


class Test(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    slug: str = Field(default_factory=generate_slug, unique=True, index=True, max_length=16)
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="draft", max_length=10)  # draft, active, closed
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    questions: list["ScreenQuestion"] = Relationship(
        back_populates="test",
        cascade_delete=True,
    )
