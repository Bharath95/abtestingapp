# backend/app/schemas/test.py
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.screen_question import QuestionPublic


class TestCreate(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class TestUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(draft|active|closed)$")


class TestPublic(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class TestListItem(TestPublic):
    question_count: int = 0
    response_count: int = 0


class TestDetail(TestPublic):
    questions: list[QuestionPublic] = []


class RespondentTest(BaseModel):
    id: int
    name: str
    description: str | None
    questions: list[QuestionPublic] = []
