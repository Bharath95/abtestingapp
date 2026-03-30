# backend/app/config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

CORS_ORIGINS = ["http://localhost:3000"]
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_PIXELS = 25_000_000  # 25 megapixels -- decompression bomb guard
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
THUMBNAIL_MAX_WIDTH = 800

# Rate limiting
RATE_LIMIT_RESPONDENT = "30/minute"
