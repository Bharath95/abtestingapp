# backend/app/schemas/response.py
from datetime import datetime
from pydantic import BaseModel, Field


class AnswerCreate(BaseModel):
    session_id: str = Field(max_length=36)
    question_id: int
    option_id: int
    followup_text: str | None = Field(default=None, max_length=500)


class FollowUpEntry(BaseModel):
    text: str
    created_at: datetime


class OptionAnalytics(BaseModel):
    option_id: int
    label: str
    source_type: str
    image_url: str | None
    source_url: str | None
    votes: int
    percentage: float
    is_winner: bool
    followup_texts: list[FollowUpEntry]


class QuestionAnalytics(BaseModel):
    question_id: int
    title: str
    total_votes: int
    options: list[OptionAnalytics]


class AnalyticsResponse(BaseModel):
    test_id: int
    test_name: str
    total_sessions: int
    total_answers: int
    completed_sessions: int
    completion_rate: float
    questions: list[QuestionAnalytics]
