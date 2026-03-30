# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware
from app.config import CORS_ORIGINS, MEDIA_DIR
from app.database import create_db_and_tables
from app.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # PRAGMAs (foreign_keys=ON, journal_mode=WAL) are handled by the
    # SQLAlchemy connect event listener in database.py, so they apply
    # to every new connection automatically.
    create_db_and_tables()
    yield


app = FastAPI(title="DesignPoll API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
