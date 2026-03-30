# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware
from app.config import CORS_ORIGINS, MEDIA_DIR
from app.database import create_db_and_tables
from app.limiter import limiter
from app.models import Test, ScreenQuestion, Option, Response  # noqa: F401 -- ensure models registered
from app.routes.tests import router as tests_router
from app.routes.questions import router as questions_router
from app.routes.options import router as options_router
from app.routes.respond import router as respond_router
from app.routes.analytics import router as analytics_router


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

app.include_router(tests_router)
app.include_router(questions_router)
app.include_router(options_router)
app.include_router(respond_router)
app.include_router(analytics_router)
