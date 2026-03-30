# backend/app/schemas/screen_question.py
from pydantic import BaseModel, Field
from app.schemas.option import OptionPublic


class QuestionCreate(BaseModel):
    title: str = Field(max_length=500)
    followup_prompt: str = Field(default="Why did you choose this?", max_length=500)
    followup_required: bool = False
    randomize_options: bool = True


class QuestionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    followup_prompt: str | None = Field(default=None, max_length=500)
    followup_required: bool | None = None
    randomize_options: bool | None = None
    order: int | None = None


class QuestionPublic(BaseModel):
    id: int
    order: int
    title: str
    followup_prompt: str
    followup_required: bool
    randomize_options: bool
    options: list[OptionPublic] = []
