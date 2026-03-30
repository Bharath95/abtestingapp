# backend/app/schemas/option.py
from datetime import datetime
from pydantic import BaseModel


class OptionPublic(BaseModel):
    id: int
    label: str
    source_type: str  # "upload" or "url"
    image_url: str | None = None
    source_url: str | None = None
    order: int
    created_at: datetime
