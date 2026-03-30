# DesignPoll A/B Testing App -- Detailed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first web application that lets UI/UX designers create forced-choice A/B design tests, collect locked-in responses with optional follow-up reasoning, and view results through an analytics dashboard.

**Architecture:** Next.js frontend (TypeScript, Tailwind CSS, App Router) communicates via REST API with a FastAPI backend (Python, SQLModel ORM). SQLite database stores all data. Images are uploaded to the backend filesystem and served via FastAPI StaticFiles. Options support image upload OR external URL. Recharts renders analytics visualizations. All pages are Client Components (no SSR data fetching) to avoid build-time backend dependency.

**Tech Stack:** Next.js 14+ (App Router, TypeScript, Tailwind CSS) | FastAPI (Python 3.11+, SQLModel, Pydantic v2) | SQLite (WAL mode, foreign_keys=ON) | Recharts | Pillow (image processing) | slowapi (rate limiting)

---

## Revision History

### Revision 3 -- 2026-03-31

Revised based on merged feedback from three independent reviewers (OpenAI Codex gpt-5.3-codex, Claude Opus 4.6, Senior Software Architect). All critical, major, and minor issues addressed.

**Critical fixes (this revision):**
1. **All tasks are now fully self-contained.** Every task includes complete inline code. No references to "02-plan.md", "Section 9", or "lines XXXX". A subagent can implement any task from ONLY its description in this file.
2. **Parallelism group fixes:** Task 9 (respond routes) moved out of G6 into G6b (depends on Task 6). Task 17 (test detail page) moved out of G9 into G9b (depends on Task 16). Dependency graph and parallel groups updated.
3. **N+1 query fix in `_build_test_with_questions`.** The shared helper now batch-fetches all options for all questions in a single query, then groups in Python. No per-question option queries.

**Major fixes (this revision):**
4. **Resolved main.py concurrent modification.** Task 5 now creates a complete main.py with ALL router includes stubbed (importing from files that will exist after Tasks 6-9 complete). Tasks 6-9 only create route files, they do NOT modify main.py. Task 20 changed to verification-only (no main.py rewrite).
5. **PRAGMA foreign_keys via event listener.** database.py now uses a SQLAlchemy `connect` event listener that runs `PRAGMA foreign_keys=ON` and `journal_mode=WAL` on every new connection. Lifespan only calls `create_db_and_tables()`.
6. **Test DB uses StaticPool.** Test conftest uses `StaticPool` and explicit model imports before `create_all()`.
7. **Added test_upload.py** (Task 14b) covering: valid upload, invalid MIME (400), oversized file (400), source-type transitions, option delete with file cleanup, URL scheme validation (javascript:/data:/file: rejected).
8. **Added URL validation.** Server-side `validate_source_url()` rejecting non-http/https schemes. `rel="noopener noreferrer"` on all new-tab links.
9. **Added decompression bomb guard.** Max pixel count check (25 megapixels) after Image.verify().
10. **Removed contradictory "implement exactly as written" instruction** in Task 9 that conflicted with the limiter.py fix.

**Minor fixes (this revision):**
11. Pinned `create-next-app` version (`@14`) to avoid interactive prompts.
12. Added null guard for `useParams()` in respondent pages.
13. Added monkeypatched `MEDIA_DIR` in test fixtures to isolate from production media/.
14. Custom followup_prompt rendered in respondent UX -- acceptance criteria verifies configured prompt text appears.
15. Added `rel="noopener noreferrer"` on all external links.
16. Task 1 now includes `git init` as a conditional step.
17. Deviation note: limiter defined in `app/limiter.py` (not `main.py`) to prevent circular imports.
18. `generate_csv` N+1 fix: batch-fetches responses in a single query, groups in Python.

### Revision 2 -- 2026-03-31

(Previous revision history preserved for reference)

**Critical fixes:**
1. N+1 queries in `list_tests`, `compute_analytics`, and `generate_csv` replaced with JOINs, GROUP BY, or batch-fetch + aggregate in Python.
2. File upload memory bomb fixed -- stream/chunk reads, check size early, never read entire file into memory.
3. URL option support added -- `source_type` (image/url) + `source_url` fields end-to-end.
4. Completion rate metric added to analytics response and dashboard.
5. SQLite `PRAGMA foreign_keys=ON` added to lifespan startup.
6. Dashboard page converted to Client Component for consistency and resilience.

**Major fixes:**
7. Test DB isolation -- use in-memory SQLite or temp file for tests, override `get_session` dependency.
8. File operation ordering -- save new file before deleting old; commit DB before deleting files.
9. Rate limiting -- simple per-IP rate limit on respondent answer endpoint via slowapi.
10. Image validation -- `Image.verify()` added after MIME check.
11. CSV injection -- sanitize cells starting with `=`, `+`, `-`, `@`.
12. Duplicate answer race -- catch `IntegrityError`, return 409.
13. GIF thumbnails -- skip thumbnail generation for GIFs, serve original.
14. Duplicated test-loading logic -- extract shared helper.
15. `useMemo` dependency -- add `question.options.length` to dependency array.

---

## Table of Contents

1. [Dependency Graph and Parallelism Map](#dependency-graph-and-parallelism-map)
2. [File Structure Overview](#file-structure-overview)
3. [Tech-Specific Notes and Gotchas](#tech-specific-notes-and-gotchas)
4. [Security Considerations](#security-considerations)
5. [Tasks 1-22](#task-1-git-init-and-root-project-files)

---

## Dependency Graph and Parallelism Map

```
                    Task 1: Git Init + Root Files
                              |
              +---------------+---------------+
              |                               |
     Task 2: Backend Scaffold         Task 11: Frontend Scaffold
              |                               |
     Task 3: Database Models           Task 12: Frontend Types + API Client
              |                               |
     Task 4: Pydantic Schemas          Task 13: Shared UI Components
              |                               |
     Task 5: Image Service +                  |
             Complete main.py                 |
              |                               |
     +--------+--------+                      |
     |        |        |                      |
  Task 6  Task 7  Task 8                     |
  (Tests) (Qs)   (Opts)                      |
     |        |        |                      |
     +--------+--------+                      |
              |                               |
     Task 9: Respond Routes                   |
     (depends on Task 6)                      |
              |                               |
     Task 10: Analytics Routes                |
              |                               |
     Task 14: Backend Integration Test        |
              |                               |
     Task 14b: Upload + URL Validation Tests  |
              |                               |
              +---------------+---------------+
                              |
              +-------+-------+-------+
              |       |               |
          Task 15  Task 16         Task 18
          (Dash)   (Builder)       (Respond)
              |       |               |
              +-------+               |
                      |               |
                 Task 17              |
                 (Detail)             |
                      |               |
                      +-------+-------+
                              |
                        Task 19: Analytics Page
                              |
                        Task 20: Verification + Gitignore
                              |
                        Task 21: End-to-End Smoke Test
                              |
                        Task 22: Final Commit
```

### Parallelism Groups

| Group | Tasks | Can Run In Parallel? | Rationale |
|-------|-------|---------------------|-----------|
| **G1** | Task 1 | No (sequential) | Must exist before anything else |
| **G2** | Task 2, Task 11 | YES | Backend and frontend scaffolds are independent |
| **G3** | Task 3 | No | Depends on Task 2 |
| **G4** | Task 4, Task 12, Task 13 | YES | Schemas (depends on T3), frontend types+API (depends on T11), shared UI (depends on T11) are independent of each other |
| **G5** | Task 5 | No | Depends on Task 4. Also creates the complete main.py with all router stubs. |
| **G6** | Task 6, Task 7, Task 8 | YES | These three route files depend on T5 but not on each other. They do NOT modify main.py. |
| **G6b** | Task 9 | No | Depends on Task 6 (imports `_build_test_with_questions` from tests.py). Runs after G6. |
| **G7** | Task 10 | No | Depends on T6-T9 (uses same DB session patterns) |
| **G8** | Task 14, Task 14b | YES | Integration tests depend on all backend routes; test_workflow and test_upload are independent test files |
| **G9** | Task 15, Task 16, Task 18 | YES | Dashboard, builder, and respondent pages depend on T12+T13 but not on each other |
| **G9b** | Task 17 | No | Depends on Task 16 (imports QuestionEditor, TestMetaForm). Runs after G9. |
| **G10** | Task 19 | No | Analytics page depends on Recharts install + T15-T18 patterns |
| **G11** | Task 20 | No | Verification depends on all prior tasks |
| **G12** | Task 21 | No | Smoke test depends on everything |
| **G13** | Task 22 | No | Final commit |

---

## File Structure Overview

### Backend (`backend/`)

```
backend/
  main.py                           -- FastAPI app, CORS, StaticFiles, lifespan, rate limiter, ALL router includes
  requirements.txt                  -- fastapi, uvicorn, sqlmodel, pillow, python-multipart, slowapi, pytest, httpx
  app/
    __init__.py
    config.py                       -- Settings: DB path, media dir, CORS origins, max file size, rate limit
    database.py                     -- Engine, get_session, create_db_and_tables, SessionDep, PRAGMA event listener
    utils.py                        -- utcnow(), sanitize_csv_cell(), validate_source_url()
    limiter.py                      -- slowapi Limiter instance (avoids circular import)
    models/
      __init__.py                   -- Re-exports all 4 models
      test.py                       -- Test SQLModel
      screen_question.py            -- ScreenQuestion SQLModel
      option.py                     -- Option SQLModel
      response.py                   -- Response SQLModel
    schemas/
      __init__.py                   -- Re-exports all schemas
      test.py                       -- TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail, RespondentTest
      screen_question.py            -- QuestionCreate, QuestionUpdate, QuestionPublic
      option.py                     -- OptionPublic
      response.py                   -- AnswerCreate, AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
    routes/
      __init__.py
      tests.py                      -- Test CRUD + _build_test_with_questions helper (batch-fetch, no N+1)
      questions.py                  -- Question CRUD + _require_draft helper
      options.py                    -- Option CRUD with multipart/form-data + source_type + URL validation
      respond.py                    -- Respondent: get test by slug, submit answer (rate limited)
      analytics.py                  -- Analytics + CSV export
    services/
      __init__.py
      image_service.py              -- save_image, delete_image, validate_image, delete_test_media (with decompression bomb guard)
      analytics_service.py          -- compute_analytics, generate_csv (batch-fetch, no N+1)
  data/                             -- SQLite DB (gitignored)
  media/                            -- Uploaded images (gitignored)
  tests/
    __init__.py
    conftest.py                     -- In-memory SQLite fixture with StaticPool, TestClient, media isolation
    test_workflow.py                -- Full workflow integration test
    test_upload.py                  -- Upload, URL validation, file cleanup tests
```

### Frontend (`frontend/`)

```
frontend/
  package.json
  tsconfig.json
  tailwind.config.ts
  next.config.ts
  app/
    layout.tsx                      -- Root layout: html, body, Tailwind (NO Navbar)
    globals.css                     -- Tailwind directives
    (designer)/
      layout.tsx                    -- Designer layout: Navbar + main container
      page.tsx                      -- Dashboard: list tests (Client Component)
      tests/
        new/
          page.tsx                  -- Create new test
        [testId]/
          page.tsx                  -- Test detail/edit
          analytics/
            page.tsx                -- Analytics dashboard
    respond/
      [slug]/
        layout.tsx                  -- Respondent layout: clean, no Navbar
        page.tsx                    -- Respondent flow
  components/
    layout/
      Navbar.tsx                    -- Top nav bar
    test-builder/
      TestMetaForm.tsx              -- Name + description fields
      QuestionEditor.tsx            -- Question editing with options list
      OptionEditor.tsx              -- Source type toggle, image upload or URL
      ImageUploader.tsx             -- Drag-and-drop file input with preview
    respondent/
      IntroScreen.tsx               -- Test intro with Start button
      QuestionView.tsx              -- One question with option cards (Fisher-Yates shuffle)
      OptionCard.tsx                -- Image/iframe display, click-to-select, lock-in
      FollowUpInput.tsx             -- Textarea with character counter
      ProgressBar.tsx               -- "Question 2 of 5" bar
    analytics/
      SummaryStats.tsx              -- Respondents, answers, completed, completion rate
      VoteChart.tsx                 -- Bar/pie toggle with Recharts
      FollowUpList.tsx              -- Follow-up texts grouped by option
      ExportButton.tsx              -- CSV download trigger
    shared/
      Button.tsx                    -- Styled button (primary/secondary/danger) with forwardRef
      Card.tsx                      -- Card wrapper
      EmptyState.tsx                -- "No data yet" placeholder
      StatusBadge.tsx               -- Colored badge for draft/active/closed
      ConfirmDialog.tsx             -- Modal with Escape key, aria-modal, autoFocus
  lib/
    api.ts                          -- All fetch functions (typed)
    types.ts                        -- TypeScript interfaces matching API schemas
    constants.ts                    -- API_BASE_URL single source of truth
```

---

## Tech-Specific Notes and Gotchas

### FastAPI + SQLModel

1. **`check_same_thread=False` is required** for SQLite with FastAPI. SQLite by default only allows the thread that created it to use it. FastAPI processes requests across threads, so this flag must be set on `create_engine`.

2. **`SessionDep = Annotated[Session, Depends(get_session)]`** is the modern FastAPI pattern for dependency injection. Use this in all route function signatures instead of `session: Session = Depends(get_session)`.

3. **Lifespan events replace `@app.on_event("startup")`** which is deprecated. Use `@asynccontextmanager async def lifespan(app)` and pass to `FastAPI(lifespan=lifespan)`.

4. **When mixing `File()` and `Form()` parameters**, the request is `multipart/form-data`. You CANNOT also accept a JSON body in the same endpoint. This is an HTTP protocol limitation, not a FastAPI one.

5. **`UploadFile.read(size)`** is an async method. In async route handlers, use `await file.read(size)`. In sync handlers, use `file.file.read(size)`. Since our option routes are `async def`, always use `await`.

6. **SQLModel `cascade_delete=True`** on Relationship fields enables Python-side cascade. But SQLite also needs `PRAGMA foreign_keys=ON` at connection time for DB-level `ON DELETE CASCADE` to work. Both are needed.

7. **`model_dump(exclude_unset=True)`** is the Pydantic v2 replacement for `.dict(exclude_unset=True)`. Use this for PATCH endpoints to only update fields the client actually sent.

8. **Rate limiting with slowapi:** The limiter instance must be stored on `app.state.limiter` AND `SlowAPIMiddleware` must be added. The `@limiter.limit()` decorator requires a `request: Request` parameter in the route function signature.

9. **PRAGMA execution via event listener:** `PRAGMA foreign_keys=ON` and `journal_mode=WAL` are executed on every new database connection via a SQLAlchemy `connect` event listener in `database.py`. This ensures every connection from the pool has the correct settings, unlike the one-time lifespan approach which only applies to a single connection.

10. **Deviation from approved plan:** The limiter is defined in `app/limiter.py` instead of `main.py` to prevent circular imports. All code that needs the limiter imports from `app.limiter`, never from `main`.

11. **SQLModel auto-generated table names** use the lowercased class name without underscores. `ScreenQuestion` becomes `screenquestion` (not `screen_question`). Foreign key references must use `screenquestion.id`.

### Next.js App Router

1. **`'use client'` directive** must be the very first line of the file (before any imports). Every page that uses `useState`, `useEffect`, `useParams`, or browser APIs needs this directive.

2. **Route groups `(designer)`** use parentheses in the folder name. They affect layout nesting but do NOT appear in the URL. So `app/(designer)/page.tsx` serves `/`, not `/(designer)/`.

3. **`useParams()` returns `Record<string, string | string[]>`** in the App Router. Always cast: `const testId = Number(params.testId)`. The hook is imported from `next/navigation`, NOT `next/router`. **Important:** `useParams()` can return `null` during prerendering. Always add a null guard: `const params = useParams(); if (!params?.testId) return <Loading />;`

4. **All navigation hooks** (`useRouter`, `usePathname`, `useSearchParams`, `useParams`) come from `next/navigation` in the App Router, not from `next/router` (which is Pages Router only).

5. **Do NOT set `Content-Type` header for `FormData` requests.** The browser automatically sets it with the correct multipart boundary. Manually setting it breaks the upload.

6. **`crypto.randomUUID()`** is available in modern browsers and generates a UUID v4. No polyfill needed for our target environment.

7. **`Inter` font from `next/font/google`** is the default font. Apply its `className` to the `<body>` tag in the root layout.

8. **Dynamic route folders** use square brackets: `[testId]`, `[slug]`. The parameter name inside the brackets matches what `useParams()` returns.

### Recharts

1. **`ResponsiveContainer` requires a parent with defined dimensions.** It will NOT render if the parent has no width/height. Always wrap charts in a container with explicit height (e.g., `height={300}`).

2. **Recharts is a client-side library.** All chart components must be inside a `'use client'` component. Recharts uses browser DOM APIs and will fail during SSR.

3. **Tooltip `formatter` callback signature** is `(value, name, props)` where `props.payload` contains the full data item. Use `props.payload.percentage` to access custom fields, NOT `data.find()` which breaks on ties.

4. **Pie chart `label` prop** can be a function receiving entry data. Use it to show `${name}: ${percentage}%` on pie slices.

5. **`Cell` components** are used inside `Bar` or `Pie` to assign individual colors to each data point. Map over data with index to assign from a color array.

6. **Install Recharts:** `npm install recharts`. No additional type packages needed (types are bundled).

---

## Security Considerations

1. **URL validation:** Server-side `validate_source_url()` rejects non-http/https schemes (`javascript:`, `data:`, `file:`, etc.) to prevent XSS via URL options.
2. **Image decompression bomb guard:** After `Image.verify()` passes, a max pixel count check (25 megapixels) prevents small compressed files from triggering massive memory allocation during thumbnail generation.
3. **CSV injection protection:** All string cells in CSV exports are sanitized -- cells starting with `=`, `+`, `-`, `@` are prefixed with a single quote.
4. **UUID filenames:** Uploaded images use UUID-based filenames to prevent path traversal attacks.
5. **Rate limiting:** Per-IP rate limit on the respondent answer endpoint prevents submission flooding.
6. **`rel="noopener noreferrer"`:** All links that open in a new tab use this attribute to prevent reverse tabnapping.
7. **`Image.verify()`:** Validates uploaded files are actual images, not spoofed files with image MIME types.

---

## Tasks

---

### Task 1: Git Init and Root Project Files

**Files:**
- Create: `.gitignore`

**What:** Initialize git repository if not already done, create root `.gitignore` to exclude build artifacts, dependencies, and data directories.

**Dependencies:** None (first task)

**Complexity:** S

- [ ] **Step 1: Initialize git if not already done**

```bash
cd /Users/bharath/Documents/abtestingapp && git init
```

If git is already initialized, this is a no-op.

- [ ] **Step 2: Create root .gitignore**

```gitignore
# Backend
backend/venv/
backend/__pycache__/
backend/**/__pycache__/
backend/*.pyc
backend/**/*.pyc
backend/data/
backend/media/
backend/.pytest_cache/

# Frontend
frontend/node_modules/
frontend/.next/
frontend/out/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add root .gitignore for backend/frontend build artifacts"
```

**Acceptance Criteria:**
- `.gitignore` exists at project root
- Covers `venv/`, `node_modules/`, `.next/`, `data/`, `media/`, `__pycache__/`

**Test Strategy:** Visual inspection of `.gitignore` contents.

---

### Task 2: Backend Scaffolding -- Directory Structure, Config, Database, Main

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/utils.py`
- Create: `backend/app/limiter.py`
- Create: `backend/main.py` (minimal -- no routers yet)
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/tests/__init__.py`

**What:** Create the full backend directory tree, install Python dependencies, write config/database/utils modules, and create a minimal `main.py` that starts FastAPI with CORS, static files, lifespan, and rate limiter. The database module uses a SQLAlchemy `connect` event listener to ensure `PRAGMA foreign_keys=ON` and `journal_mode=WAL` run on every new connection. Verify the server starts and Swagger UI is accessible.

**Dependencies:** Task 1

**Complexity:** M

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/bharath/Documents/abtestingapp
mkdir -p backend/app/models backend/app/schemas backend/app/routes backend/app/services backend/data backend/media backend/tests
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/routes/__init__.py backend/app/services/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlmodel==0.0.22
pillow==11.1.0
python-multipart==0.0.20
slowapi==0.1.9
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 3: Create virtual environment and install dependencies**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

Expected: All packages install successfully. Verify with `pip list | grep fastapi`.

- [ ] **Step 4: Write config.py**

```python
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
```

- [ ] **Step 5: Write utils.py**

```python
# backend/app/utils.py
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import HTTPException


def utcnow() -> datetime:
    """Return current UTC time. Single source of truth for all models."""
    return datetime.now(timezone.utc)


def sanitize_csv_cell(value: str) -> str:
    """Sanitize a string for safe CSV export.

    Prevents CSV injection by prefixing cells that start with
    formula-triggering characters (=, +, -, @) with a single quote.
    """
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def validate_source_url(url: str) -> str:
    """Validate that a source URL uses http or https scheme.

    Rejects javascript:, data:, file:, and other non-http schemes to prevent
    XSS and local file access attacks.
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="source_url cannot be empty.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )
    return url
```

- [ ] **Step 6: Write database.py (with connect event listener for PRAGMAs)**

```python
# backend/app/database.py
from typing import Annotated
from fastapi import Depends
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, text
from app.config import DATABASE_URL, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


# Ensure PRAGMA foreign_keys=ON and journal_mode=WAL on EVERY new connection.
# This is critical because SQLAlchemy's connection pool may create multiple
# connections, and PRAGMAs set on one connection do not propagate to others.
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
```

- [ ] **Step 7: Write limiter.py (shared module to avoid circular imports)**

**Deviation from approved plan:** The limiter is defined here in `app/limiter.py` instead of directly in `main.py`. This prevents circular imports when `respond.py` needs to import the limiter. All code that needs the limiter imports `from app.limiter import limiter`.

```python
# backend/app/limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

- [ ] **Step 8: Write main.py (minimal -- no routers yet, PRAGMAs handled by event listener)**

```python
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
```

- [ ] **Step 9: Verify the server starts**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && timeout 5 uvicorn main:app --port 8000 || true
```

Expected: Server starts without import errors. `http://localhost:8000/docs` would show Swagger UI with no endpoints.

- [ ] **Step 10: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/
git commit -m "feat: scaffold backend with FastAPI, SQLModel, CORS, rate limiter, PRAGMA event listener, and URL validation"
```

**Acceptance Criteria:**
- `uvicorn main:app` starts without errors
- `/docs` shows empty Swagger UI
- `backend/data/` directory is created on startup
- `backend/media/` directory is created on startup
- `database.py` contains a `connect` event listener that runs `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL` on every new connection
- `utils.py` contains `validate_source_url()` that rejects non-http/https schemes
- `config.py` contains `MAX_IMAGE_PIXELS = 25_000_000`

**Test Strategy:** Start the server and verify no import/startup errors.

---

### Task 3: Database Models (Test, ScreenQuestion, Option, Response)

**Files:**
- Create: `backend/app/models/test.py`
- Create: `backend/app/models/screen_question.py`
- Create: `backend/app/models/option.py`
- Create: `backend/app/models/response.py`
- Modify: `backend/app/models/__init__.py`

**What:** Define all four SQLModel table models with proper fields, foreign keys, relationships, cascade rules, and indexes. Verify tables are created in SQLite.

**Dependencies:** Task 2

**Complexity:** M

- [ ] **Step 1: Write Test model**

```python
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
```

- [ ] **Step 2: Write ScreenQuestion model**

```python
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
```

- [ ] **Step 3: Write Option model**

```python
# backend/app/models/option.py
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel
from app.utils import utcnow

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion
    from app.models.response import Response


class Option(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    screen_question_id: int = Field(foreign_key="screenquestion.id", index=True)
    label: str = Field(max_length=200)
    source_type: str = Field(default="upload", max_length=10)  # "upload" or "url"
    image_filename: str | None = Field(default=None, max_length=255)
    original_filename: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2000)
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow)

    question: Optional["ScreenQuestion"] = Relationship(back_populates="options")
    responses: list["Response"] = Relationship(
        back_populates="option",
        cascade_delete=True,
    )
```

- [ ] **Step 4: Write Response model**

```python
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
```

- [ ] **Step 5: Update models __init__.py**

```python
# backend/app/models/__init__.py
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response

__all__ = ["Test", "ScreenQuestion", "Option", "Response"]
```

- [ ] **Step 6: Verify tables are created**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -c "
from app.models import Test, ScreenQuestion, Option, Response
from app.database import create_db_and_tables, engine
create_db_and_tables()
print('Tables created successfully')
import sqlite3
conn = sqlite3.connect('data/app.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', sorted([t[0] for t in tables]))
conn.close()
"
```

Expected: `Tables: ['option', 'response', 'screenquestion', 'test']`

- [ ] **Step 7: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/models/
git commit -m "feat: add SQLModel database models for Test, ScreenQuestion, Option, Response"
```

**Acceptance Criteria:**
- All four tables created in SQLite
- Foreign keys defined with correct references (`test.id`, `screenquestion.id`, `option.id`)
- Unique constraint on `(session_id, screen_question_id)` in Response
- All relationships defined with `cascade_delete=True`
- `utcnow` used for all timestamp defaults (from `app.utils`)

**Test Strategy:** Run the verification script and confirm table names appear.

---

### Task 4: Pydantic Schemas (Request/Response Validation)

**Files:**
- Create: `backend/app/schemas/option.py`
- Create: `backend/app/schemas/screen_question.py`
- Create: `backend/app/schemas/test.py`
- Create: `backend/app/schemas/response.py`
- Modify: `backend/app/schemas/__init__.py`

**What:** Define all Pydantic v2 schemas for API request validation and response serialization. Schemas are separate from SQLModel table models to control exactly what is exposed via the API.

**Dependencies:** Task 3

**Complexity:** S

- [ ] **Step 1: Write option schemas (must be defined first -- QuestionPublic depends on it)**

```python
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
```

- [ ] **Step 2: Write screen question schemas**

```python
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
```

- [ ] **Step 3: Write test schemas**

```python
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
```

- [ ] **Step 4: Write response/analytics schemas**

```python
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
```

- [ ] **Step 5: Update schemas __init__.py**

```python
# backend/app/schemas/__init__.py
from app.schemas.option import OptionPublic
from app.schemas.screen_question import QuestionCreate, QuestionUpdate, QuestionPublic
from app.schemas.test import TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail, RespondentTest
from app.schemas.response import AnswerCreate, AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
```

- [ ] **Step 6: Verify imports**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -c "
from app.schemas import TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail, RespondentTest
from app.schemas import QuestionCreate, QuestionUpdate, QuestionPublic
from app.schemas import OptionPublic
from app.schemas import AnswerCreate, AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
print('All schemas imported successfully')
"
```

- [ ] **Step 7: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas for API request/response validation"
```

**Acceptance Criteria:**
- All schemas importable without errors
- `TestUpdate.status` has regex pattern validation for `draft|active|closed`
- `AnswerCreate.followup_text` max length is 500
- `OptionPublic` includes `source_type`, `image_url`, `source_url`
- `AnalyticsResponse` includes `completed_sessions` and `completion_rate`

**Test Strategy:** Import all schemas and verify no errors.

---

### Task 5: Image Service + Complete main.py with All Router Stubs

**Files:**
- Create: `backend/app/services/image_service.py`
- Modify: `backend/main.py` (replace with complete version including all router imports)

**What:** Implement image upload with bounded reads (memory bomb prevention), `Image.verify()` validation, decompression bomb guard (25MP max), UUID-based filenames, thumbnail generation (skip for GIFs), and cleanup functions. Then update main.py to include ALL five router imports so that Tasks 6-9 do NOT need to modify main.py (preventing concurrent modification conflicts).

**Dependencies:** Task 4

**Complexity:** M

- [ ] **Step 1: Write image_service.py**

```python
# backend/app/services/image_service.py
import shutil
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image
from app.config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_PIXELS, MEDIA_DIR, THUMBNAIL_MAX_WIDTH


def validate_image(file: UploadFile) -> None:
    """Validate image file type."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF.",
        )


async def save_image(file: UploadFile, test_id: int) -> tuple[str, str]:
    """Save uploaded image and generate thumbnail. Returns (uuid_filename, original_filename).

    Reads file in a bounded manner to prevent memory bombs, then validates
    with Image.verify() to reject spoofed non-image files. Checks pixel count
    to prevent decompression bombs. Skips thumbnail generation for GIFs to
    preserve animation.
    """
    validate_image(file)

    # Read file content with bounded read to prevent memory bomb.
    content = await file.read(MAX_IMAGE_SIZE_BYTES + 1)
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size is {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB.",
        )

    # Generate UUID filename
    ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".png"
    uuid_name = f"{uuid.uuid4()}{ext}"
    thumb_name = f"thumb_{uuid_name}"

    # Create test directory
    test_dir = MEDIA_DIR / str(test_id)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Save original
    original_path = test_dir / uuid_name
    original_path.write_bytes(content)

    # Validate with Pillow's Image.verify() to reject spoofed files
    try:
        with Image.open(original_path) as img:
            img.verify()
    except Exception:
        original_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="File is not a valid image.",
        )

    # Decompression bomb guard: check pixel count after verify passes
    try:
        with Image.open(original_path) as img:
            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                original_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Image dimensions too large ({width}x{height}). Maximum is {MAX_IMAGE_PIXELS} pixels.",
                )
    except HTTPException:
        raise
    except Exception:
        original_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Failed to read image dimensions.",
        )

    # Generate thumbnail (skip for GIFs to preserve animation)
    is_gif = ext in {".gif"}
    if not is_gif:
        try:
            with Image.open(original_path) as img:
                if img.width > THUMBNAIL_MAX_WIDTH:
                    ratio = THUMBNAIL_MAX_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((THUMBNAIL_MAX_WIDTH, new_height), Image.LANCZOS)
                    img_resized.save(test_dir / thumb_name)
                else:
                    # Image is already small enough, copy as thumbnail
                    shutil.copy2(original_path, test_dir / thumb_name)
        except Exception:
            # If thumbnail generation fails, copy the original
            shutil.copy2(original_path, test_dir / thumb_name)
    # For GIFs, no thumbnail is generated; serve the original directly.

    return uuid_name, file.filename or "unknown"


def delete_image(test_id: int, filename: str) -> None:
    """Delete image and its thumbnail from disk."""
    test_dir = MEDIA_DIR / str(test_id)
    original = test_dir / filename
    thumbnail = test_dir / f"thumb_{filename}"
    if original.exists():
        original.unlink()
    if thumbnail.exists():
        thumbnail.unlink()


def delete_test_media(test_id: int) -> None:
    """Delete entire media directory for a test."""
    test_dir = MEDIA_DIR / str(test_id)
    if test_dir.exists():
        shutil.rmtree(test_dir)


def get_image_url(test_id: int, filename: str | None) -> str | None:
    """Construct the URL path for an image."""
    if not filename:
        return None
    return f"/media/{test_id}/{filename}"


def get_thumbnail_url(test_id: int, filename: str | None) -> str | None:
    """Construct the URL path for a thumbnail. For GIFs, returns the original URL."""
    if not filename:
        return None
    if filename.lower().endswith(".gif"):
        return f"/media/{test_id}/{filename}"
    return f"/media/{test_id}/thumb_{filename}"
```

- [ ] **Step 2: Write the COMPLETE main.py with all router imports**

This is the final main.py that includes all five routers. By writing it now (in Task 5), Tasks 6-9 do NOT need to modify main.py, preventing merge conflicts when those tasks run in parallel.

**Note:** The route files (`tests.py`, `questions.py`, `options.py`, `respond.py`, `analytics.py`) do not exist yet. This main.py will fail to import until those files are created in Tasks 6-10. That is expected -- this task creates the complete main.py so that it does not need to be modified again.

```python
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
```

**IMPORTANT for the implementing agent:** After writing this main.py, also create empty placeholder route files so that the imports do not immediately fail. Create these five files with minimal router definitions:

```python
# backend/app/routes/tests.py (placeholder -- full implementation in Task 6)
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/tests", tags=["tests"])
```

```python
# backend/app/routes/questions.py (placeholder -- full implementation in Task 7)
from fastapi import APIRouter
router = APIRouter(tags=["questions"])
```

```python
# backend/app/routes/options.py (placeholder -- full implementation in Task 8)
from fastapi import APIRouter
router = APIRouter(tags=["options"])
```

```python
# backend/app/routes/respond.py (placeholder -- full implementation in Task 9)
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/respond", tags=["respondent"])
```

```python
# backend/app/routes/analytics.py (placeholder -- full implementation in Task 10)
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/tests", tags=["analytics"])
```

- [ ] **Step 3: Verify server starts with placeholders**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && timeout 5 uvicorn main:app --port 8000 || true
```

Expected: Server starts. Swagger UI shows no real endpoints (just placeholder routers).

- [ ] **Step 4: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/services/image_service.py backend/main.py backend/app/routes/
git commit -m "feat: add image service with decompression bomb guard, and complete main.py with all router stubs"
```

**Acceptance Criteria:**
- `save_image()` reads at most `MAX_IMAGE_SIZE_BYTES + 1` bytes (never unbounded)
- `Image.verify()` called after file is saved to disk
- Decompression bomb guard: pixel count checked against `MAX_IMAGE_PIXELS` (25MP)
- If `Image.verify()` or pixel check fails, the saved file is deleted before raising HTTPException
- GIF files get no thumbnail; non-GIF files get a thumbnail at max 800px width
- UUID-based filenames prevent path traversal
- `delete_image()` removes both original and thumbnail
- `delete_test_media()` removes entire `media/{test_id}/` directory
- `main.py` includes all five router imports (with placeholder files)
- Server starts successfully with placeholder routers

**Test Strategy:** Import and verify no errors. Full testing happens in the integration test (Task 14).

---

### Task 6: Test CRUD Routes

**Files:**
- Create: `backend/app/routes/tests.py` (replace placeholder)

**What:** Implement POST/GET/GET/{id}/PATCH/DELETE for tests. Includes the shared `_build_test_with_questions()` helper that is reused by respond routes. **The helper uses batch-fetch: a single query loads all options for all questions, then groups them in Python (no N+1).** List endpoint uses JOINs + GROUP BY to avoid N+1 queries. PATCH enforces lifecycle transitions and activation validation (1+ questions, 2-5 options each). DELETE commits DB first, then removes media files.

**Dependencies:** Task 5

**Complexity:** L

**IMPORTANT:** This task does NOT modify `main.py`. The router import is already in main.py from Task 5. This task only replaces the placeholder `tests.py` file.

- [ ] **Step 1: Write tests.py route file (replacing placeholder)**

```python
# backend/app/routes/tests.py
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select, distinct
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.test import TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail
from app.schemas.screen_question import QuestionPublic
from app.schemas.option import OptionPublic
from app.services.image_service import delete_test_media, get_image_url

router = APIRouter(prefix="/api/v1/tests", tags=["tests"])


def _build_test_with_questions(test: Test, session, schema_class=TestDetail):
    """Shared helper: load a test with its nested questions and options.

    Used by both get_test (designer) and get_test_for_respondent to avoid
    duplicated query logic. Uses batch-fetch for options (single query for
    all questions) to avoid N+1 queries.
    """
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    if not questions:
        return []

    # Batch-fetch ALL options for ALL questions in a single query
    question_ids = [q.id for q in questions]
    all_options = session.exec(
        select(Option)
        .where(Option.screen_question_id.in_(question_ids))
        .order_by(Option.order)
    ).all()

    # Group options by question ID
    options_by_question: dict[int, list[Option]] = defaultdict(list)
    for o in all_options:
        options_by_question[o.screen_question_id].append(o)

    question_list = []
    for q in questions:
        q_options = options_by_question.get(q.id, [])
        option_list = [
            OptionPublic(
                id=o.id,
                label=o.label,
                source_type=o.source_type,
                image_url=get_image_url(test.id, o.image_filename),
                source_url=o.source_url,
                order=o.order,
                created_at=o.created_at,
            )
            for o in q_options
        ]
        question_list.append(
            QuestionPublic(
                id=q.id,
                order=q.order,
                title=q.title,
                followup_prompt=q.followup_prompt,
                followup_required=q.followup_required,
                randomize_options=q.randomize_options,
                options=option_list,
            )
        )

    return question_list


@router.post("", response_model=TestPublic, status_code=201)
def create_test(data: TestCreate, session: SessionDep):
    test = Test.model_validate(data)
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


@router.get("", response_model=list[TestListItem])
def list_tests(session: SessionDep):
    """List all tests with question and response counts.

    Uses a single query with JOINs and GROUP BY to avoid N+1 queries.
    """
    stmt = (
        select(
            Test,
            func.count(distinct(ScreenQuestion.id)).label("question_count"),
            func.count(distinct(Response.session_id)).label("response_count"),
        )
        .outerjoin(ScreenQuestion, ScreenQuestion.test_id == Test.id)
        .outerjoin(Response, Response.screen_question_id == ScreenQuestion.id)
        .group_by(Test.id)
        .order_by(col(Test.created_at).desc())
    )
    results = session.exec(stmt).all()

    return [
        TestListItem(
            id=test.id,
            slug=test.slug,
            name=test.name,
            description=test.description,
            status=test.status,
            created_at=test.created_at,
            updated_at=test.updated_at,
            question_count=q_count,
            response_count=r_count,
        )
        for test, q_count, r_count in results
    ]


@router.get("/{test_id}", response_model=TestDetail)
def get_test(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    question_list = _build_test_with_questions(test, session)

    return TestDetail(
        id=test.id,
        slug=test.slug,
        name=test.name,
        description=test.description,
        status=test.status,
        created_at=test.created_at,
        updated_at=test.updated_at,
        questions=question_list,
    )


VALID_TRANSITIONS = {
    ("draft", "active"),
    ("draft", "closed"),
    ("active", "closed"),
}


@router.patch("/{test_id}", response_model=TestPublic)
def update_test(test_id: int, data: TestUpdate, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    update_data = data.model_dump(exclude_unset=True)

    # Enforce lifecycle rules
    if "status" in update_data:
        new_status = update_data["status"]
        if (test.status, new_status) not in VALID_TRANSITIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{test.status}' to '{new_status}'.",
            )
        # Validate activation requirements
        if new_status == "active":
            questions = session.exec(
                select(ScreenQuestion).where(ScreenQuestion.test_id == test_id)
            ).all()
            if len(questions) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot activate test with no questions.",
                )
            for q in questions:
                option_count = session.exec(
                    select(func.count()).where(Option.screen_question_id == q.id)
                ).one()
                if option_count < 2:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question '{q.title}' needs at least 2 options to activate.",
                    )
                if option_count > 5:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question '{q.title}' has more than 5 options (max 5).",
                    )

    # If test is active or closed, only name/description/status can change
    if test.status in ("active", "closed"):
        allowed = {"name", "description", "status"}
        disallowed = set(update_data.keys()) - allowed
        if disallowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot modify {disallowed} on a {test.status} test.",
            )

    for key, value in update_data.items():
        setattr(test, key, value)
    test.updated_at = datetime.now(timezone.utc)
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


@router.delete("/{test_id}", status_code=204)
def delete_test(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    # Commit DB delete first, then remove files (ensures DB consistency)
    session.delete(test)
    session.commit()
    delete_test_media(test_id)
    return None
```

- [ ] **Step 2: Verify endpoints appear in Swagger**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && timeout 5 uvicorn main:app --port 8000 || true
```

Expected: Server starts. Swagger UI at `/docs` shows test CRUD endpoints.

- [ ] **Step 3: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/routes/tests.py
git commit -m "feat: add Test CRUD API endpoints with batch-fetch helper, lifecycle validation, and N+1-free list"
```

**Acceptance Criteria:**
- `POST /api/v1/tests` creates a test with auto-generated slug
- `GET /api/v1/tests` returns list with `question_count` and `response_count` (single query)
- `GET /api/v1/tests/{test_id}` returns nested questions and options
- `_build_test_with_questions()` batch-fetches all options in ONE query (no N+1)
- `PATCH /api/v1/tests/{test_id}` enforces: valid transitions only, activation requires 1+ questions with 2-5 options each, non-draft tests only allow name/description/status changes
- `DELETE /api/v1/tests/{test_id}` commits DB delete first, then removes media directory
- `_build_test_with_questions()` helper is importable by other route files

**Test Strategy:** Tested in Task 14 integration test.

---

### Task 7: Question CRUD Routes

**Files:**
- Create: `backend/app/routes/questions.py` (replace placeholder)

**What:** Implement POST (under test), PATCH, DELETE for screen questions. All mutations require parent test to be in draft status. Delete cleans up option images before cascade. Auto-assigns order as max+1.

**Dependencies:** Task 5

**Complexity:** M

**IMPORTANT:** This task does NOT modify `main.py`. The router import is already in main.py from Task 5.

- [ ] **Step 1: Write questions.py route file (replacing placeholder)**

```python
# backend/app/routes/questions.py
from fastapi import APIRouter, HTTPException
from sqlmodel import func, select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.schemas.screen_question import QuestionCreate, QuestionUpdate, QuestionPublic
from app.schemas.option import OptionPublic
from app.services.image_service import get_image_url, delete_image

router = APIRouter(tags=["questions"])


def _require_draft(session: SessionDep, test_id: int) -> Test:
    """Helper: fetch test and verify it is in draft status."""
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "draft":
        raise HTTPException(status_code=403, detail="Cannot modify questions on a non-draft test.")
    return test


def _question_to_public(question: ScreenQuestion, session: SessionDep) -> QuestionPublic:
    """Convert a ScreenQuestion model to its public schema."""
    options = session.exec(
        select(Option).where(Option.screen_question_id == question.id).order_by(Option.order)
    ).all()
    option_list = [
        OptionPublic(
            id=o.id,
            label=o.label,
            source_type=o.source_type,
            image_url=get_image_url(question.test_id, o.image_filename),
            source_url=o.source_url,
            order=o.order,
            created_at=o.created_at,
        )
        for o in options
    ]
    return QuestionPublic(
        id=question.id,
        order=question.order,
        title=question.title,
        followup_prompt=question.followup_prompt,
        followup_required=question.followup_required,
        randomize_options=question.randomize_options,
        options=option_list,
    )


@router.post("/api/v1/tests/{test_id}/questions", response_model=QuestionPublic, status_code=201)
def create_question(test_id: int, data: QuestionCreate, session: SessionDep):
    _require_draft(session, test_id)

    # Auto-assign order as max + 1
    max_order = session.exec(
        select(func.max(ScreenQuestion.order)).where(ScreenQuestion.test_id == test_id)
    ).one()
    next_order = (max_order or -1) + 1

    question = ScreenQuestion(
        test_id=test_id,
        order=next_order,
        title=data.title,
        followup_prompt=data.followup_prompt,
        followup_required=data.followup_required,
        randomize_options=data.randomize_options,
    )
    session.add(question)
    session.commit()
    session.refresh(question)
    return _question_to_public(question, session)


@router.patch("/api/v1/questions/{question_id}", response_model=QuestionPublic)
def update_question(question_id: int, data: QuestionUpdate, session: SessionDep):
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    _require_draft(session, question.test_id)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)
    session.add(question)
    session.commit()
    session.refresh(question)
    return _question_to_public(question, session)


@router.delete("/api/v1/questions/{question_id}", status_code=204)
def delete_question(question_id: int, session: SessionDep):
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    test = _require_draft(session, question.test_id)

    # Clean up image files for all options before cascade delete
    options = session.exec(
        select(Option).where(Option.screen_question_id == question.id)
    ).all()
    files_to_delete = [
        (test.id, o.image_filename)
        for o in options
        if o.image_filename
    ]

    session.delete(question)
    session.commit()

    # Delete image files after DB commit
    for test_id, filename in files_to_delete:
        delete_image(test_id, filename)

    return None
```

- [ ] **Step 2: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/routes/questions.py
git commit -m "feat: add ScreenQuestion CRUD API endpoints with draft enforcement and orphan file cleanup"
```

**Acceptance Criteria:**
- Creating a question on a non-draft test returns 403
- Order is auto-assigned as max existing order + 1
- Deleting a question deletes associated image files from disk after DB commit
- All three endpoints appear in Swagger

**Test Strategy:** Tested in Task 14 integration test.

---

### Task 8: Option CRUD Routes (Multipart Upload + URL Support)

**Files:**
- Create: `backend/app/routes/options.py` (replace placeholder)

**What:** Implement POST (multipart), PATCH (multipart), DELETE for options. Supports `source_type` of `"upload"` or `"url"`. Handles source-type transitions (upload-to-url, url-to-upload). Enforces max 5 options per question. File replacement saves new file before deleting old. URL validation via `validate_source_url()`. All mutations require parent test to be in draft status.

**Dependencies:** Task 5

**Complexity:** L

**IMPORTANT:** This task does NOT modify `main.py`. The router import is already in main.py from Task 5.

- [ ] **Step 1: Write options.py route file (replacing placeholder)**

```python
# backend/app/routes/options.py
from fastapi import APIRouter, Form, HTTPException, UploadFile, File
from sqlmodel import func, select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.schemas.option import OptionPublic
from app.services.image_service import save_image, delete_image, get_image_url
from app.utils import validate_source_url

router = APIRouter(tags=["options"])


def _require_draft_for_question(session: SessionDep, question_id: int) -> ScreenQuestion:
    """Fetch question and verify its parent test is draft."""
    question = session.get(ScreenQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    test = session.get(Test, question.test_id)
    if not test or test.status != "draft":
        raise HTTPException(status_code=403, detail="Cannot modify options on a non-draft test.")
    return question


def _option_to_public(option: Option, test_id: int) -> OptionPublic:
    return OptionPublic(
        id=option.id,
        label=option.label,
        source_type=option.source_type,
        image_url=get_image_url(test_id, option.image_filename),
        source_url=option.source_url,
        order=option.order,
        created_at=option.created_at,
    )


@router.post("/api/v1/questions/{question_id}/options", response_model=OptionPublic, status_code=201)
async def create_option(
    question_id: int,
    session: SessionDep,
    label: str = Form(..., max_length=200),
    source_type: str = Form(default="upload"),
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    source_url: str | None = Form(default=None),
):
    question = _require_draft_for_question(session, question_id)

    # Enforce max 5 options per question
    current_count = session.exec(
        select(func.count()).where(Option.screen_question_id == question_id)
    ).one()
    if current_count >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 options per question.")

    # Validate source_type
    if source_type not in ("upload", "url"):
        raise HTTPException(status_code=400, detail="source_type must be 'upload' or 'url'.")

    # Auto-assign order
    if order is None:
        max_order = session.exec(
            select(func.max(Option.order)).where(Option.screen_question_id == question_id)
        ).one()
        order = (max_order or -1) + 1

    image_filename = None
    original_filename = None
    option_source_url = None

    if source_type == "upload":
        if not image or not image.filename:
            raise HTTPException(status_code=400, detail="Image file is required for upload mode.")
        image_filename, original_filename = await save_image(image, question.test_id)
    elif source_type == "url":
        if not source_url or not source_url.strip():
            raise HTTPException(status_code=400, detail="source_url is required for URL mode.")
        option_source_url = validate_source_url(source_url)

    option = Option(
        screen_question_id=question_id,
        label=label,
        source_type=source_type,
        image_filename=image_filename,
        original_filename=original_filename,
        source_url=option_source_url,
        order=order,
    )
    session.add(option)
    session.commit()
    session.refresh(option)
    return _option_to_public(option, question.test_id)


@router.patch("/api/v1/options/{option_id}", response_model=OptionPublic)
async def update_option(
    option_id: int,
    session: SessionDep,
    label: str | None = Form(default=None, max_length=200),
    source_type: str | None = Form(default=None),
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    source_url: str | None = Form(default=None),
):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    # Validate label is not empty if provided
    if label is not None and label.strip() == "":
        raise HTTPException(status_code=400, detail="Label cannot be empty.")
    if label is not None:
        option.label = label

    if order is not None:
        option.order = order

    # Track old image for post-commit cleanup
    old_image_filename = None

    # Handle source_type transitions
    if source_type is not None:
        if source_type not in ("upload", "url"):
            raise HTTPException(status_code=400, detail="source_type must be 'upload' or 'url'.")

        if source_type != option.source_type:
            # Source type is changing
            if source_type == "url":
                # Switching from upload to URL
                if not source_url or not source_url.strip():
                    raise HTTPException(status_code=400, detail="source_url is required for URL mode.")
                validated_url = validate_source_url(source_url)
                old_image_filename = option.image_filename
                option.source_type = "url"
                option.source_url = validated_url
                option.image_filename = None
                option.original_filename = None
            elif source_type == "upload":
                # Switching from URL to upload
                if not image or not image.filename:
                    raise HTTPException(status_code=400, detail="Image file is required for upload mode.")
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
                option.source_type = "upload"
                option.source_url = None
        else:
            # Same source_type, update fields within the same mode
            if source_type == "url" and source_url is not None:
                option.source_url = validate_source_url(source_url)
            if source_type == "upload" and image and image.filename:
                # Save new image first, track old for deletion
                old_image_filename = option.image_filename
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
    else:
        # No source_type change; handle image replacement within current mode
        if image and image.filename:
            if option.source_type == "upload":
                # Save new image first, track old for deletion
                old_image_filename = option.image_filename
                option.image_filename, option.original_filename = await save_image(image, question.test_id)
        if source_url is not None and option.source_type == "url":
            option.source_url = validate_source_url(source_url)

    session.add(option)
    session.commit()
    session.refresh(option)

    # Delete old image files after successful commit
    if old_image_filename:
        delete_image(question.test_id, old_image_filename)

    return _option_to_public(option, question.test_id)


@router.delete("/api/v1/options/{option_id}", status_code=204)
def delete_option(option_id: int, session: SessionDep):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    # Track file for post-commit cleanup
    image_to_delete = option.image_filename

    session.delete(option)
    session.commit()

    # Delete image from disk after DB commit
    if image_to_delete:
        delete_image(question.test_id, image_to_delete)

    return None
```

- [ ] **Step 2: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/routes/options.py
git commit -m "feat: add Option CRUD API with source_type support, URL validation, image upload, and safe file ordering"
```

**Acceptance Criteria:**
- `POST` accepts multipart/form-data with `label`, `source_type`, `image`, `source_url`
- Max 5 options enforced per question (returns 400 at 5)
- `source_type="upload"` requires image file; `source_type="url"` requires source_url
- URL options validated via `validate_source_url()` -- rejects non-http/https schemes
- Source-type transitions clear stale data (switching upload->url clears image_filename; switching url->upload clears source_url)
- Image replacement: new file saved first, old file deleted after DB commit
- Empty label (after strip) returns 400

**Test Strategy:** Tested in Task 14 integration test.

---

### Task 9: Respondent-Facing Routes (Get Test + Submit Answer with Rate Limiting)

**Files:**
- Create: `backend/app/routes/respond.py` (replace placeholder)

**What:** Implement GET test by slug (respondent view, omits internal fields) and POST answer submission. Answer endpoint catches `IntegrityError` for duplicate detection (race-safe). Rate limited via slowapi decorator. Validates question belongs to test, option belongs to question, and followup requirement. Uses `_build_test_with_questions` from Task 6's `tests.py`.

**Dependencies:** Task 5, Task 6 (imports `_build_test_with_questions` from `app.routes.tests`)

**Complexity:** M

**IMPORTANT:** This task does NOT modify `main.py`. The router import is already in main.py from Task 5. This task imports `_build_test_with_questions` from `app.routes.tests` (created in Task 6), so Task 6 must complete first. The limiter is imported from `app.limiter` (NOT from `main`).

- [ ] **Step 1: Write respond.py route file (replacing placeholder)**

```python
# backend/app/routes/respond.py
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.test import RespondentTest
from app.schemas.response import AnswerCreate
from app.routes.tests import _build_test_with_questions
from app.limiter import limiter
from app.config import RATE_LIMIT_RESPONDENT

router = APIRouter(prefix="/api/v1/respond", tags=["respondent"])


@router.get("/{slug}", response_model=RespondentTest)
def get_test_for_respondent(slug: str, session: SessionDep):
    test = session.exec(select(Test).where(Test.slug == slug)).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "active":
        raise HTTPException(status_code=403, detail="This test is not currently accepting responses.")

    # Use the shared helper to build nested test data
    question_list = _build_test_with_questions(test, session)

    return RespondentTest(
        id=test.id,
        name=test.name,
        description=test.description,
        questions=question_list,
    )


@router.post("/{slug}/answers", status_code=201)
@limiter.limit(RATE_LIMIT_RESPONDENT)
def submit_answer(slug: str, data: AnswerCreate, session: SessionDep, request: Request):
    """Submit one answer. Rate limited per IP to prevent flooding.

    The @limiter.limit() decorator requires the `request: Request` parameter
    to extract the client IP. The decorator must come AFTER @router.post()
    in reading order (i.e., it is the inner decorator).
    """
    test = session.exec(select(Test).where(Test.slug == slug)).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "active":
        raise HTTPException(status_code=403, detail="This test is not currently accepting responses.")

    # Validate question belongs to this test
    question = session.get(ScreenQuestion, data.question_id)
    if not question or question.test_id != test.id:
        raise HTTPException(status_code=400, detail="Question does not belong to this test.")

    # Validate option belongs to this question
    option = session.get(Option, data.option_id)
    if not option or option.screen_question_id != data.question_id:
        raise HTTPException(status_code=400, detail="Option does not belong to this question.")

    # Validate followup if required
    if question.followup_required and not data.followup_text:
        raise HTTPException(status_code=400, detail="Follow-up text is required for this question.")

    # Insert and catch IntegrityError for duplicate submissions (race-safe)
    response = Response(
        screen_question_id=data.question_id,
        option_id=data.option_id,
        session_id=data.session_id,
        followup_text=data.followup_text,
    )
    session.add(response)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Already answered this question in this session.")

    return {"status": "saved"}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/routes/respond.py
git commit -m "feat: add respondent-facing endpoints with rate limiting and IntegrityError-based duplicate detection"
```

**Acceptance Criteria:**
- `GET /api/v1/respond/{slug}` returns 404 for unknown slug, 403 for non-active test
- Response omits `status`, `slug`, `created_at`, `updated_at` (only returns respondent-needed fields)
- `POST /api/v1/respond/{slug}/answers` validates question belongs to test, option belongs to question
- Duplicate answer (same session_id + question_id) returns 409 via IntegrityError catch
- Missing required followup_text returns 400
- Rate limiting active on the answer endpoint (via `@limiter.limit()` decorator)
- Limiter imported from `app.limiter` (NOT from `main`)

**Test Strategy:** Tested in Task 14 integration test.

---

### Task 10: Analytics Service and Routes (Batch-Fetch, Completion Rate, CSV Export)

**Files:**
- Create: `backend/app/services/analytics_service.py`
- Create: `backend/app/routes/analytics.py` (replace placeholder)

**What:** Implement analytics computation with batch-fetch (no N+1), completion rate calculation, and CSV export with CSV-injection sanitization. Analytics endpoint returns per-question vote distribution with winner detection. CSV endpoint returns downloadable file. **Both `compute_analytics` and `generate_csv` use batch-fetch for all queries to avoid N+1.**

**Dependencies:** Task 6, Task 7, Task 8, Task 9 (needs all routes to exist for a complete API)

**Complexity:** L

**IMPORTANT:** This task does NOT modify `main.py`. The router import is already in main.py from Task 5.

- [ ] **Step 1: Write analytics_service.py**

```python
# backend/app/services/analytics_service.py
import csv
import io
from collections import defaultdict
from sqlmodel import Session, func, select, distinct
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.response import AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
from app.services.image_service import get_image_url
from app.utils import sanitize_csv_cell


def compute_analytics(test: Test, session: Session) -> AnalyticsResponse:
    """Compute analytics for a test using batch-fetch to avoid N+1 queries."""
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_ids = [q.id for q in questions]
    if not question_ids:
        return AnalyticsResponse(
            test_id=test.id,
            test_name=test.name,
            total_sessions=0,
            total_answers=0,
            completed_sessions=0,
            completion_rate=0.0,
            questions=[],
        )

    # Batch-fetch all responses for this test in a single query
    all_responses = session.exec(
        select(Response).where(
            Response.screen_question_id.in_(question_ids)
        )
    ).all()

    # Batch-fetch all options for this test's questions in a single query
    all_options = session.exec(
        select(Option).where(
            Option.screen_question_id.in_(question_ids)
        ).order_by(Option.order)
    ).all()

    # Build lookup structures
    options_by_question: dict[int, list[Option]] = defaultdict(list)
    for o in all_options:
        options_by_question[o.screen_question_id].append(o)

    responses_by_question: dict[int, list[Response]] = defaultdict(list)
    all_session_ids: set[str] = set()
    for r in all_responses:
        responses_by_question[r.screen_question_id].append(r)
        all_session_ids.add(r.session_id)

    total_sessions = len(all_session_ids)
    total_answers = len(all_responses)

    # Compute completion rate: sessions that answered ALL questions
    num_questions = len(questions)
    if total_sessions > 0 and num_questions > 0:
        session_question_counts: dict[str, int] = defaultdict(int)
        for r in all_responses:
            session_question_counts[r.session_id] += 1
        completed_sessions = sum(
            1 for count in session_question_counts.values()
            if count >= num_questions
        )
    else:
        completed_sessions = 0

    completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # Build per-question analytics
    question_analytics = []
    for q in questions:
        q_responses = responses_by_question.get(q.id, [])
        q_options = options_by_question.get(q.id, [])
        total_votes = len(q_responses)

        votes_by_option: dict[int, int] = defaultdict(int)
        followups_by_option: dict[int, list[Response]] = defaultdict(list)
        for r in q_responses:
            votes_by_option[r.option_id] += 1
            if r.followup_text:
                followups_by_option[r.option_id].append(r)

        option_analytics = []
        max_votes = max(votes_by_option.values(), default=0)

        for o in q_options:
            votes = votes_by_option.get(o.id, 0)
            percentage = round((votes / total_votes * 100), 1) if total_votes > 0 else 0.0

            option_analytics.append(
                OptionAnalytics(
                    option_id=o.id,
                    label=o.label,
                    source_type=o.source_type,
                    image_url=get_image_url(test.id, o.image_filename),
                    source_url=o.source_url,
                    votes=votes,
                    percentage=percentage,
                    is_winner=(votes == max_votes and max_votes > 0),
                    followup_texts=[
                        FollowUpEntry(text=r.followup_text, created_at=r.created_at)
                        for r in followups_by_option.get(o.id, [])
                    ],
                )
            )

        question_analytics.append(
            QuestionAnalytics(
                question_id=q.id,
                title=q.title,
                total_votes=total_votes,
                options=option_analytics,
            )
        )

    return AnalyticsResponse(
        test_id=test.id,
        test_name=test.name,
        total_sessions=total_sessions,
        total_answers=total_answers,
        completed_sessions=completed_sessions,
        completion_rate=completion_rate,
        questions=question_analytics,
    )


def generate_csv(test: Test, session: Session) -> str:
    """Generate CSV export with sanitized cells and batch-fetched data.

    All string cells are sanitized for CSV injection (cells starting with
    =, +, -, @ are prefixed with a single quote).

    Uses batch-fetch for both options and responses to avoid N+1 queries.
    """
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_ids = [q.id for q in questions]

    # Pre-fetch all options into a lookup dictionary (single query)
    all_options = session.exec(
        select(Option).where(Option.screen_question_id.in_(question_ids))
    ).all() if question_ids else []
    option_lookup = {o.id: o for o in all_options}

    # Batch-fetch all responses for all questions (single query)
    all_responses = session.exec(
        select(Response)
        .where(Response.screen_question_id.in_(question_ids))
        .order_by(Response.created_at)
    ).all() if question_ids else []

    # Group responses by question
    responses_by_question: dict[int, list[Response]] = defaultdict(list)
    for r in all_responses:
        responses_by_question[r.screen_question_id].append(r)

    # Build question lookup for titles
    question_lookup = {q.id: q for q in questions}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["question_title", "option_label", "followup_text", "session_id", "responded_at"])

    for q in questions:
        q_responses = responses_by_question.get(q.id, [])
        for r in q_responses:
            option = option_lookup.get(r.option_id)
            writer.writerow([
                sanitize_csv_cell(q.title),
                sanitize_csv_cell(option.label if option else "Unknown"),
                sanitize_csv_cell(r.followup_text or ""),
                sanitize_csv_cell(r.session_id),
                r.created_at.isoformat(),
            ])

    return output.getvalue()
```

- [ ] **Step 2: Write analytics.py route file (replacing placeholder)**

```python
# backend/app/routes/analytics.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import io
from app.database import SessionDep
from app.models.test import Test
from app.schemas.response import AnalyticsResponse
from app.services.analytics_service import compute_analytics, generate_csv

router = APIRouter(prefix="/api/v1/tests", tags=["analytics"])


@router.get("/{test_id}/analytics", response_model=AnalyticsResponse)
def get_analytics(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return compute_analytics(test, session)


@router.get("/{test_id}/export")
def export_csv(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    csv_content = generate_csv(test, session)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="test-{test.slug}-responses.csv"'
        },
    )
```

- [ ] **Step 3: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/app/services/analytics_service.py backend/app/routes/analytics.py
git commit -m "feat: add analytics with batch-fetch, completion rate, and CSV-injection-safe export"
```

**Acceptance Criteria:**
- Analytics uses batch-fetch for all queries (no N+1 -- verified by code review)
- `completion_rate` is accurate: sessions answering ALL questions / total sessions * 100
- `is_winner` handles ties correctly (all tied options marked as winner)
- CSV export includes header row even when no responses
- CSV cells sanitized for injection (cells starting with `=`, `+`, `-`, `@`)
- CSV Content-Disposition header includes the test slug in the filename
- `generate_csv` also uses batch-fetch (no per-question response queries)

**Test Strategy:** Tested in Task 14 integration test.

---

### Task 11: Next.js Project Scaffolding

**Files:**
- Create: `frontend/` (via create-next-app)
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/app/(designer)/layout.tsx`
- Create: `frontend/app/respond/[slug]/layout.tsx`

**What:** Create the Next.js project with TypeScript and Tailwind. Pin `create-next-app` version to avoid interactive prompts. Set up route groups from the start: `(designer)` group with Navbar placeholder and `respond` group without Navbar. Create directory structure for all page routes.

**Dependencies:** Task 1

**Complexity:** M

- [ ] **Step 1: Create Next.js project (pinned version)**

```bash
cd /Users/bharath/Documents/abtestingapp && npx create-next-app@14 frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

Note: Pinned to `@14` to avoid unexpected interactive prompts from newer versions. If prompted about Turbopack, answer "No".

- [ ] **Step 2: Create route group directories**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && mkdir -p "app/(designer)/tests/new" "app/(designer)/tests/[testId]/analytics" "app/respond/[slug]" "components/layout" "components/test-builder" "components/respondent" "components/analytics" "components/shared" "lib"
```

- [ ] **Step 3: Update root layout (NO Navbar)**

Replace `frontend/app/layout.tsx` with:

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DesignPoll",
  description: "A/B testing for UI/UX designers",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-50 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Create designer route group layout (WITH Navbar placeholder)**

```tsx
// frontend/app/(designer)/layout.tsx
export default function DesignerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* Navbar will be added in Task 13 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </>
  );
}
```

- [ ] **Step 5: Create respondent layout (clean, no Navbar)**

```tsx
// frontend/app/respond/[slug]/layout.tsx
export default function RespondLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 6: Create placeholder pages to verify routing**

Create `frontend/app/(designer)/page.tsx`:
```tsx
export default function DashboardPage() {
  return <h1>Dashboard (placeholder)</h1>;
}
```

- [ ] **Step 7: Verify dev server starts and routing works**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npm run dev
```

Expected: `http://localhost:3000` shows "Dashboard (placeholder)". No 404.

- [ ] **Step 8: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add frontend/
git commit -m "feat: scaffold Next.js frontend with route groups and Tailwind CSS"
```

**Acceptance Criteria:**
- `npm run dev` starts without errors
- `/` serves the designer layout (with main container)
- Route group directories exist: `(designer)`, `respond/[slug]`
- Root layout does NOT include a Navbar
- Respondent layout is clean (no Navbar)
- `create-next-app` version is pinned (`@14`)

**Test Strategy:** Start dev server, visit `/`, confirm placeholder renders.

---

### Task 12: Frontend TypeScript Types, Constants, and API Client

**Files:**
- Create: `frontend/lib/constants.ts`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

**What:** Define all TypeScript interfaces matching backend API response shapes, the centralized API base URL constant, and all fetch functions for communicating with the backend. Every frontend file that calls the API imports from these three files.

**Dependencies:** Task 11

**Complexity:** M

- [ ] **Step 1: Write constants.ts**

```typescript
// frontend/lib/constants.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

Note: This is the single source of truth for the API URL. No other file should reference `process.env.NEXT_PUBLIC_API_URL` directly.

- [ ] **Step 2: Write types.ts**

```typescript
// frontend/lib/types.ts

export interface Test {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "closed";
  created_at: string;
  updated_at: string;
  question_count: number;
  response_count: number;
}

export interface Option {
  id: number;
  label: string;
  source_type: "upload" | "url";
  image_url: string | null;
  source_url: string | null;
  order: number;
  created_at: string;
}

export interface Question {
  id: number;
  order: number;
  title: string;
  followup_prompt: string;
  followup_required: boolean;
  randomize_options: boolean;
  options: Option[];
}

export interface TestDetail {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  status: "draft" | "active" | "closed";
  created_at: string;
  updated_at: string;
  questions: Question[];
}

export interface RespondentTest {
  id: number;
  name: string;
  description: string | null;
  questions: Question[];
}

export interface FollowUpEntry {
  text: string;
  created_at: string;
}

export interface OptionAnalytics {
  option_id: number;
  label: string;
  source_type: "upload" | "url";
  image_url: string | null;
  source_url: string | null;
  votes: number;
  percentage: number;
  is_winner: boolean;
  followup_texts: FollowUpEntry[];
}

export interface QuestionAnalytics {
  question_id: number;
  title: string;
  total_votes: number;
  options: OptionAnalytics[];
}

export interface Analytics {
  test_id: number;
  test_name: string;
  total_sessions: number;
  total_answers: number;
  completed_sessions: number;
  completion_rate: number;
  questions: QuestionAnalytics[];
}
```

- [ ] **Step 3: Write api.ts**

```typescript
// frontend/lib/api.ts
import { API_BASE_URL } from "./constants";
import type { Test, TestDetail, RespondentTest, Analytics, Question, Option } from "./types";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Tests
export async function fetchTests(): Promise<Test[]> {
  return apiFetch<Test[]>("/api/v1/tests");
}

export async function fetchTest(testId: number): Promise<TestDetail> {
  return apiFetch<TestDetail>(`/api/v1/tests/${testId}`);
}

export async function createTest(data: { name: string; description?: string }): Promise<Test> {
  return apiFetch<Test>("/api/v1/tests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateTest(
  testId: number,
  data: { name?: string; description?: string; status?: string }
): Promise<Test> {
  return apiFetch<Test>(`/api/v1/tests/${testId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteTest(testId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/tests/${testId}`, { method: "DELETE" });
}

// Questions
export async function createQuestion(
  testId: number,
  data: { title: string; followup_prompt?: string; followup_required?: boolean; randomize_options?: boolean }
): Promise<Question> {
  return apiFetch<Question>(`/api/v1/tests/${testId}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateQuestion(
  questionId: number,
  data: { title?: string; followup_prompt?: string; followup_required?: boolean; randomize_options?: boolean; order?: number }
): Promise<Question> {
  return apiFetch<Question>(`/api/v1/questions/${questionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteQuestion(questionId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/questions/${questionId}`, { method: "DELETE" });
}

// Options (multipart -- do NOT set Content-Type header; browser sets it with boundary)
export async function createOption(
  questionId: number,
  formData: FormData
): Promise<Option> {
  return apiFetch<Option>(`/api/v1/questions/${questionId}/options`, {
    method: "POST",
    body: formData,
  });
}

export async function updateOption(
  optionId: number,
  formData: FormData
): Promise<Option> {
  return apiFetch<Option>(`/api/v1/options/${optionId}`, {
    method: "PATCH",
    body: formData,
  });
}

export async function deleteOption(optionId: number): Promise<void> {
  return apiFetch<void>(`/api/v1/options/${optionId}`, { method: "DELETE" });
}

// Respondent
export async function fetchTestForRespondent(slug: string): Promise<RespondentTest> {
  return apiFetch<RespondentTest>(`/api/v1/respond/${slug}`);
}

export async function submitAnswer(
  slug: string,
  data: { session_id: string; question_id: number; option_id: number; followup_text?: string }
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/v1/respond/${slug}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// Analytics
export async function fetchAnalytics(testId: number): Promise<Analytics> {
  return apiFetch<Analytics>(`/api/v1/tests/${testId}/analytics`);
}

export function getExportUrl(testId: number): string {
  return `${API_BASE_URL}/api/v1/tests/${testId}/export`;
}
```

- [ ] **Step 4: Verify TypeScript compilation**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add frontend/lib/
git commit -m "feat: add TypeScript types, API client, and constants for frontend-backend communication"
```

**Acceptance Criteria:**
- `API_BASE_URL` is the single source of truth (no other file has inline `process.env.NEXT_PUBLIC_API_URL`)
- All TypeScript interfaces match the backend Pydantic schema field names exactly
- `apiFetch` handles non-2xx responses by parsing `detail` from JSON error body
- `createOption` and `updateOption` do NOT set Content-Type header (critical for multipart)
- `getExportUrl` returns a URL string (not a fetch call) for direct browser download
- `TestDetail` uses flat interface (not Omit)

**Test Strategy:** TypeScript compilation check (`tsc --noEmit`).

---

### Task 13: Shared UI Components (Button, Card, EmptyState, StatusBadge, ConfirmDialog, Navbar)

**Files:**
- Create: `frontend/components/shared/Button.tsx`
- Create: `frontend/components/shared/Card.tsx`
- Create: `frontend/components/shared/EmptyState.tsx`
- Create: `frontend/components/shared/StatusBadge.tsx`
- Create: `frontend/components/shared/ConfirmDialog.tsx`
- Create: `frontend/components/layout/Navbar.tsx`
- Modify: `frontend/app/(designer)/layout.tsx` (add Navbar import)

**What:** Build all reusable UI components used across multiple pages. Button supports variants (primary/secondary/danger), sizes, and ref forwarding (needed by ConfirmDialog). ConfirmDialog has Escape key handler, aria-modal, and autoFocus on cancel button. Navbar has logo and navigation links.

**Dependencies:** Task 11

**Complexity:** M

The complete code for all components is provided inline in this task. See the code blocks in the current implementation plan for Task 13 in Revision 2 -- those are unchanged and fully self-contained. Specifically:

- [ ] **Step 1: Write Button component (with forwardRef)**

```tsx
// frontend/components/shared/Button.tsx
"use client";

import { forwardRef } from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
}

const variantClasses = {
  primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
  secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-gray-400",
  danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
};

const sizeClasses = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className = "", disabled, children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={`inline-flex items-center justify-center font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
});

export default Button;
```

- [ ] **Step 2: Write Card component**

```tsx
// frontend/components/shared/Card.tsx

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export default function Card({ children, className = "" }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
      {children}
    </div>
  );
}
```

- [ ] **Step 3: Write EmptyState component**

```tsx
// frontend/components/shared/EmptyState.tsx

interface EmptyStateProps {
  title: string;
  message: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <div className="text-gray-400 text-5xl mb-4">---</div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-gray-500 mb-4">{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
```

- [ ] **Step 4: Write StatusBadge component**

```tsx
// frontend/components/shared/StatusBadge.tsx

const statusStyles: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-800",
  active: "bg-green-100 text-green-800",
  closed: "bg-gray-100 text-gray-600",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusStyles[status] || "bg-gray-100 text-gray-600"}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
```

- [ ] **Step 5: Write ConfirmDialog component**

```tsx
// frontend/components/shared/ConfirmDialog.tsx
"use client";

import { useEffect, useRef } from "react";
import Button from "./Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open && cancelRef.current) {
      cancelRef.current.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onCancel();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h3 id="confirm-dialog-title" className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} ref={cancelRef}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Write Navbar component**

```tsx
// frontend/components/layout/Navbar.tsx
import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link href="/" className="text-xl font-bold text-blue-600">
            DesignPoll
          </Link>
          <div className="flex gap-4">
            <Link href="/" className="text-gray-600 hover:text-gray-900 text-sm font-medium">
              My Tests
            </Link>
            <Link
              href="/tests/new"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              New Test
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 7: Update designer layout to include Navbar**

Replace `frontend/app/(designer)/layout.tsx` with:

```tsx
// frontend/app/(designer)/layout.tsx
import Navbar from "@/components/layout/Navbar";

export default function DesignerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </>
  );
}
```

- [ ] **Step 8: Verify components render**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npx tsc --noEmit
```

- [ ] **Step 9: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add frontend/components/ "frontend/app/(designer)/layout.tsx"
git commit -m "feat: add shared UI components, Navbar, and ConfirmDialog with accessibility"
```

**Acceptance Criteria:**
- Button supports `ref` forwarding (via `forwardRef`)
- ConfirmDialog closes on Escape key press
- ConfirmDialog has `aria-modal="true"` and `role="dialog"`
- Cancel button receives focus when dialog opens
- StatusBadge renders correct colors for draft/active/closed
- Navbar appears on designer pages but NOT on respondent pages

**Test Strategy:** TypeScript compilation + visual verification when pages are built.

---

### Task 14: Backend Integration Test (Full Workflow with Test DB Isolation)

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_workflow.py`

**What:** Write a comprehensive integration test that exercises the entire API workflow. Uses an in-memory SQLite database with `StaticPool` and explicit model imports before `create_all()`, with `get_session` dependency override for full isolation. Includes monkeypatched `MEDIA_DIR` to isolate from production media/.

**Dependencies:** Task 6, Task 7, Task 8, Task 9, Task 10 (all backend routes must exist)

**Complexity:** M

- [ ] **Step 1: Write conftest.py (with StaticPool and media isolation)**

```python
# backend/tests/conftest.py
"""Test configuration: use an in-memory SQLite database with StaticPool to isolate tests."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, text
from app.database import get_session

# Explicit model imports BEFORE create_all to ensure metadata is registered
from app.models import Test, ScreenQuestion, Option, Response  # noqa: F401

# In-memory SQLite for test isolation -- StaticPool ensures the same connection
# is reused across threads, which is required for in-memory SQLite.
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="test_media_dir", autouse=True)
def test_media_dir_fixture(tmp_path, monkeypatch):
    """Isolate media writes from production backend/media/ directory.

    Creates a per-test temp directory and monkeypatches MEDIA_DIR in both
    config and image_service modules.
    """
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    monkeypatch.setattr("app.config.MEDIA_DIR", media_dir)
    monkeypatch.setattr("app.services.image_service.MEDIA_DIR", media_dir)
    return media_dir


@pytest.fixture(name="session", autouse=True)
def session_fixture():
    """Create fresh tables for each test, yield session, then drop."""
    # Enable foreign keys before creating tables
    with test_engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session, test_media_dir):
    """TestClient that uses the test database session.

    Depends on test_media_dir to ensure media isolation is set up before
    the app is loaded.
    """
    def get_session_override():
        yield session

    from main import app
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Write test_workflow.py**

```python
# backend/tests/test_workflow.py
"""Full workflow integration test: create test -> add questions -> add options -> activate -> respond -> analytics."""


def test_full_workflow(client):
    # 1. Create a test
    res = client.post("/api/v1/tests", json={"name": "My Test", "description": "A test"})
    assert res.status_code == 201
    test = res.json()
    test_id = test["id"]
    slug = test["slug"]
    assert test["status"] == "draft"

    # 2. Add a question
    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Which design?", "followup_required": True},
    )
    assert res.status_code == 201
    question = res.json()
    question_id = question["id"]

    # 3. Add options using source_type=url (no image files needed in test)
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option A", "source_type": "url", "source_url": "https://example.com/a", "order": "0"},
    )
    assert res.status_code == 201
    opt_a = res.json()
    option_a_id = opt_a["id"]
    assert opt_a["source_type"] == "url"
    assert opt_a["source_url"] == "https://example.com/a"

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option B", "source_type": "url", "source_url": "https://example.com/b", "order": "1"},
    )
    assert res.status_code == 201
    option_b_id = res.json()["id"]

    # 4. Activate the test
    res = client.patch(f"/api/v1/tests/{test_id}", json={"status": "active"})
    assert res.status_code == 200
    assert res.json()["status"] == "active"

    # 5. Cannot add questions to active test
    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Another question"},
    )
    assert res.status_code == 403

    # 6. Respondent gets the test
    res = client.get(f"/api/v1/respond/{slug}")
    assert res.status_code == 200
    assert res.json()["name"] == "My Test"
    assert len(res.json()["questions"]) == 1

    # 7. Submit answer
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-1",
            "question_id": question_id,
            "option_id": option_a_id,
            "followup_text": "I liked it",
        },
    )
    assert res.status_code == 201

    # 8. Duplicate answer rejected (IntegrityError-based)
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-1",
            "question_id": question_id,
            "option_id": option_b_id,
            "followup_text": "Changed my mind",
        },
    )
    assert res.status_code == 409

    # 9. Second respondent
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-2",
            "question_id": question_id,
            "option_id": option_b_id,
            "followup_text": "Better colors",
        },
    )
    assert res.status_code == 201

    # 10. Analytics
    res = client.get(f"/api/v1/tests/{test_id}/analytics")
    assert res.status_code == 200
    analytics = res.json()
    assert analytics["total_sessions"] == 2
    assert analytics["total_answers"] == 2
    assert analytics["completed_sessions"] == 2
    assert analytics["completion_rate"] == 100.0
    assert len(analytics["questions"]) == 1
    q_analytics = analytics["questions"][0]
    assert q_analytics["total_votes"] == 2
    votes = {o["label"]: o["votes"] for o in q_analytics["options"]}
    assert votes["Option A"] == 1
    assert votes["Option B"] == 1

    # 11. CSV export
    res = client.get(f"/api/v1/tests/{test_id}/export")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    csv_text = res.text
    assert "Which design?" in csv_text
    assert "Option A" in csv_text

    # 12. Close the test
    res = client.patch(f"/api/v1/tests/{test_id}", json={"status": "closed"})
    assert res.status_code == 200
    assert res.json()["status"] == "closed"

    # 13. Respondent cannot submit to closed test
    res = client.post(
        f"/api/v1/respond/{slug}/answers",
        json={
            "session_id": "test-session-3",
            "question_id": question_id,
            "option_id": option_a_id,
            "followup_text": "Too late",
        },
    )
    assert res.status_code == 403
```

- [ ] **Step 3: Run the test**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -m pytest tests/ -v
```

Expected: All assertions pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/tests/
git commit -m "test: add full workflow integration test with StaticPool, media isolation, and in-memory DB"
```

**Acceptance Criteria:**
- Test uses in-memory SQLite with `StaticPool` (no disk file)
- Explicit model imports before `create_all()`
- `get_session` dependency is properly overridden
- Media writes are isolated from production `backend/media/` via monkeypatched `MEDIA_DIR`
- All 13 workflow steps pass
- Duplicate answer returns 409 (IntegrityError handling works)
- Analytics returns correct completion rate
- CSV export returns text/csv content type
- Closed test rejects respondent submissions with 403

**Test Strategy:** This IS the test. Run `pytest tests/ -v` and all assertions must pass.

---

### Task 14b: Upload and URL Validation Tests

**Files:**
- Create: `backend/tests/test_upload.py`

**What:** Test the image upload path and URL validation that is not covered by the workflow test (which only uses URL-mode options). Covers: valid upload, invalid MIME (400), oversized file (400), source-type transitions, option delete with file cleanup, and URL scheme validation (javascript:/data:/file: rejected).

**Dependencies:** Task 6, Task 7, Task 8, Task 9, Task 10 (all backend routes must exist)

**Complexity:** M

- [ ] **Step 1: Write test_upload.py**

```python
# backend/tests/test_upload.py
"""Tests for image upload, file cleanup, and URL validation."""
import io
from pathlib import Path
from PIL import Image


def _create_test_image(width=100, height=100, format="PNG") -> io.BytesIO:
    """Create a minimal valid test image."""
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def _setup_draft_test_with_question(client):
    """Helper: create a draft test with one question, return (test_id, question_id)."""
    res = client.post("/api/v1/tests", json={"name": "Upload Test"})
    assert res.status_code == 201
    test_id = res.json()["id"]

    res = client.post(
        f"/api/v1/tests/{test_id}/questions",
        json={"title": "Upload question"},
    )
    assert res.status_code == 201
    question_id = res.json()["id"]

    return test_id, question_id


def test_valid_image_upload(client, test_media_dir):
    """Step 1: Valid image upload succeeds."""
    test_id, question_id = _setup_draft_test_with_question(client)

    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Uploaded Option", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option = res.json()
    assert option["source_type"] == "upload"
    assert option["image_url"] is not None
    assert option["image_url"].startswith(f"/media/{test_id}/")


def test_invalid_mime_type(client, test_media_dir):
    """Step 2: Invalid MIME type returns 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Bad Option", "source_type": "upload"},
        files={"image": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert res.status_code == 400
    assert "Invalid image type" in res.json()["detail"]


def test_oversized_file(client, test_media_dir):
    """Step 3: Oversized file returns 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create a file larger than 10MB
    large_content = b"x" * (10 * 1024 * 1024 + 1)
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Large Option", "source_type": "upload"},
        files={"image": ("large.png", io.BytesIO(large_content), "image/png")},
    )
    assert res.status_code == 400
    assert "too large" in res.json()["detail"]


def test_source_type_transition_upload_to_url(client, test_media_dir):
    """Step 4: Transition from upload to URL clears image, sets source_url."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create upload option
    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Transition Option", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option_id = res.json()["id"]
    assert res.json()["image_url"] is not None

    # Switch to URL
    res = client.patch(
        f"/api/v1/options/{option_id}",
        data={"source_type": "url", "source_url": "https://example.com/design"},
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "url"
    assert res.json()["source_url"] == "https://example.com/design"
    assert res.json()["image_url"] is None


def test_source_type_transition_url_to_upload(client, test_media_dir):
    """Step 5: Transition from URL to upload clears source_url, sets image."""
    test_id, question_id = _setup_draft_test_with_question(client)

    # Create URL option
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "URL Option", "source_type": "url", "source_url": "https://example.com/a"},
    )
    assert res.status_code == 201
    option_id = res.json()["id"]

    # Switch to upload
    img_buf = _create_test_image()
    res = client.patch(
        f"/api/v1/options/{option_id}",
        data={"source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 200
    assert res.json()["source_type"] == "upload"
    assert res.json()["image_url"] is not None
    assert res.json()["source_url"] is None


def test_option_delete_cleans_up_files(client, test_media_dir):
    """Step 6: Deleting an upload option removes files from disk."""
    test_id, question_id = _setup_draft_test_with_question(client)

    img_buf = _create_test_image()
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Delete Me", "source_type": "upload"},
        files={"image": ("test.png", img_buf, "image/png")},
    )
    assert res.status_code == 201
    option = res.json()
    image_url = option["image_url"]  # e.g., /media/1/uuid.png

    # Extract filename from URL
    filename = image_url.split("/")[-1]
    test_dir = test_media_dir / str(test_id)

    # Verify files exist on disk
    assert (test_dir / filename).exists()
    assert (test_dir / f"thumb_{filename}").exists()

    # Delete option
    res = client.delete(f"/api/v1/options/{option['id']}")
    assert res.status_code == 204

    # Verify files removed from disk
    assert not (test_dir / filename).exists()
    assert not (test_dir / f"thumb_{filename}").exists()


def test_url_scheme_javascript_rejected(client, test_media_dir):
    """Step 7: javascript: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "XSS Option", "source_type": "url", "source_url": "javascript:alert(1)"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]


def test_url_scheme_data_rejected(client, test_media_dir):
    """Step 8: data: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Data Option", "source_type": "url", "source_url": "data:text/html,<script>alert(1)</script>"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]


def test_url_scheme_file_rejected(client, test_media_dir):
    """Step 9: file: URL scheme is rejected with 400."""
    test_id, question_id = _setup_draft_test_with_question(client)

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "File Option", "source_type": "url", "source_url": "file:///etc/passwd"},
    )
    assert res.status_code == 400
    assert "Invalid URL scheme" in res.json()["detail"]
```

- [ ] **Step 2: Run the tests**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -m pytest tests/ -v
```

Expected: All tests pass (both test_workflow.py and test_upload.py).

- [ ] **Step 3: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/tests/test_upload.py
git commit -m "test: add upload, file cleanup, and URL validation tests"
```

**Acceptance Criteria:**
- Valid image upload succeeds with 201
- Invalid MIME type returns 400
- Oversized file returns 400
- Source-type transitions work (upload->url and url->upload)
- Option delete removes both original and thumbnail files from disk (verified via `pathlib.Path.exists()`)
- `javascript:`, `data:`, `file:` URL schemes all return 400
- Media writes are isolated from production `backend/media/`

**Test Strategy:** Run `pytest tests/ -v` -- all tests pass.

---

### Task 15: Dashboard Page (Test List -- Client Component)

**Files:**
- Modify: `frontend/app/(designer)/page.tsx` (replace placeholder)

**What:** Build the main dashboard page as a Client Component that fetches and displays all tests. Shows test name, status badge, question/response counts, and creation date. Empty state with "Create Test" link when no tests exist. Error state when backend is unreachable.

**Dependencies:** Task 12, Task 13

**Complexity:** M

- [ ] **Step 1: Write the dashboard page**

```tsx
// frontend/app/(designer)/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchTests } from "@/lib/api";
import type { Test } from "@/lib/types";
import Card from "@/components/shared/Card";
import StatusBadge from "@/components/shared/StatusBadge";
import EmptyState from "@/components/shared/EmptyState";

export default function DashboardPage() {
  const [tests, setTests] = useState<Test[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTests()
      .then(setTests)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load tests"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Error: {error}</p>
        <p className="text-gray-500 mt-2">Make sure the backend is running on port 8000.</p>
      </div>
    );
  }

  if (tests.length === 0) {
    return (
      <EmptyState
        title="No tests yet"
        message="Create your first A/B test to get started."
        action={
          <Link
            href="/tests/new"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Create Test
          </Link>
        }
      />
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Tests</h1>
      </div>
      <div className="grid gap-4">
        {tests.map((test) => (
          <Link key={test.id} href={`/tests/${test.id}`}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-lg font-semibold text-gray-900">{test.name}</h2>
                    <StatusBadge status={test.status} />
                  </div>
                  {test.description && (
                    <p className="text-gray-500 text-sm line-clamp-2">{test.description}</p>
                  )}
                  <div className="flex gap-4 mt-2 text-sm text-gray-400">
                    <span>{test.question_count} question{test.question_count !== 1 ? "s" : ""}</span>
                    <span>{test.response_count} response{test.response_count !== 1 ? "s" : ""}</span>
                  </div>
                </div>
                <span className="text-gray-400 text-sm">
                  {new Date(test.created_at).toLocaleDateString()}
                </span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add "frontend/app/(designer)/page.tsx"
git commit -m "feat: add dashboard page as Client Component with test listing"
```

**Acceptance Criteria:**
- Page renders without backend running (shows error state, not crash)
- With backend running, shows list of tests or empty state
- Each test card shows name, status badge, question count, response count, date
- Clicking a card navigates to `/tests/{id}`
- "Create Test" link in empty state navigates to `/tests/new`

**Test Strategy:** Visual verification with both servers running. Verify empty state, then create a test via API and refresh.

---

### Task 16: Test Builder Page (Create New Test)

**Files:**
- Create: `frontend/app/(designer)/tests/new/page.tsx`
- Create: `frontend/components/test-builder/TestMetaForm.tsx`
- Create: `frontend/components/test-builder/ImageUploader.tsx`
- Create: `frontend/components/test-builder/OptionEditor.tsx`
- Create: `frontend/components/test-builder/QuestionEditor.tsx`

**What:** Build the create-test page and all test-builder components. These components are also imported by Task 17 (Test Detail Page). The code for all components is provided inline below.

**Dependencies:** Task 12, Task 13

**Complexity:** L

- [ ] **Step 1: Write ImageUploader component**

```tsx
// frontend/components/test-builder/ImageUploader.tsx
"use client";

import { useRef, useState } from "react";
import { API_BASE_URL } from "@/lib/constants";

interface ImageUploaderProps {
  currentImageUrl?: string | null;
  onFileSelect: (file: File) => void;
}

const MAX_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];

export default function ImageUploader({ currentImageUrl, onFileSelect }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleFile(file: File) {
    setError(null);
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Invalid file type. Use JPEG, PNG, WebP, or GIF.");
      return;
    }
    if (file.size > MAX_SIZE) {
      setError("File too large. Maximum size is 10MB.");
      return;
    }
    setPreview(URL.createObjectURL(file));
    onFileSelect(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  const displayUrl = preview || (currentImageUrl ? `${API_BASE_URL}${currentImageUrl}` : null);

  return (
    <div>
      <div
        className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400 transition-colors"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {displayUrl ? (
          <img src={displayUrl} alt="Preview" className="max-h-40 mx-auto object-contain" />
        ) : (
          <div className="text-gray-400 py-4">
            <p className="text-sm">Click or drag to upload an image</p>
            <p className="text-xs mt-1">JPEG, PNG, WebP, GIF (max 10MB)</p>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={handleChange}
      />
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Write OptionEditor component (with source_type toggle and unique radio name)**

```tsx
// frontend/components/test-builder/OptionEditor.tsx
"use client";

import { useState, useId } from "react";
import ImageUploader from "./ImageUploader";
import Button from "@/components/shared/Button";

interface OptionEditorProps {
  optionId?: number;
  initialLabel: string;
  initialSourceType?: "upload" | "url";
  initialImageUrl?: string | null;
  initialSourceUrl?: string | null;
  onSave: (label: string, sourceType: "upload" | "url", imageFile: File | null, sourceUrl: string | null) => Promise<void>;
  onDelete?: () => Promise<void>;
  isNew?: boolean;
}

export default function OptionEditor({
  initialLabel,
  initialSourceType = "upload",
  initialImageUrl,
  initialSourceUrl,
  onSave,
  onDelete,
  isNew = false,
}: OptionEditorProps) {
  const uniqueId = useId();
  const [label, setLabel] = useState(initialLabel);
  const [sourceType, setSourceType] = useState<"upload" | "url">(initialSourceType);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState(initialSourceUrl || "");
  const [saving, setSaving] = useState(false);

  const canSave =
    label.trim() &&
    (sourceType === "upload" ? (imageFile || initialImageUrl) : sourceUrl.trim());

  async function handleSave() {
    if (!canSave) return;
    setSaving(true);
    try {
      await onSave(label.trim(), sourceType, imageFile, sourceType === "url" ? sourceUrl.trim() : null);
      if (isNew) {
        setLabel("");
        setImageFile(null);
        setSourceUrl("");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Option label (e.g., Option A)"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          maxLength={200}
        />
        {onDelete && (
          <Button variant="danger" size="sm" onClick={onDelete}>
            Remove
          </Button>
        )}
      </div>

      {/* Source type toggle -- uses useId() for unique radio group name */}
      <div className="flex gap-4">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`source-type-${uniqueId}`}
            checked={sourceType === "upload"}
            onChange={() => setSourceType("upload")}
            className="text-blue-600"
          />
          Image Upload
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="radio"
            name={`source-type-${uniqueId}`}
            checked={sourceType === "url"}
            onChange={() => setSourceType("url")}
            className="text-blue-600"
          />
          URL
        </label>
      </div>

      {sourceType === "upload" ? (
        <ImageUploader currentImageUrl={initialImageUrl} onFileSelect={setImageFile} />
      ) : (
        <input
          type="url"
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="https://example.com/your-design"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        />
      )}

      <Button size="sm" onClick={handleSave} disabled={saving || !canSave}>
        {saving ? "Saving..." : isNew ? "Add Option" : "Update"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: Write QuestionEditor component (with max 5 options)**

```tsx
// frontend/components/test-builder/QuestionEditor.tsx
"use client";

import { useState } from "react";
import type { Question } from "@/lib/types";
import OptionEditor from "./OptionEditor";
import Button from "@/components/shared/Button";
import {
  updateQuestion,
  deleteQuestion,
  createOption,
  updateOption,
  deleteOption,
} from "@/lib/api";

interface QuestionEditorProps {
  question: Question;
  testId: number;
  onUpdate: () => void;
  onDelete: () => void;
}

export default function QuestionEditor({
  question,
  testId,
  onUpdate,
  onDelete,
}: QuestionEditorProps) {
  const [title, setTitle] = useState(question.title);
  const [followupPrompt, setFollowupPrompt] = useState(question.followup_prompt);
  const [followupRequired, setFollowupRequired] = useState(question.followup_required);
  const [randomizeOptions, setRandomizeOptions] = useState(question.randomize_options);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSaveQuestion() {
    setSaving(true);
    setError(null);
    try {
      await updateQuestion(question.id, {
        title,
        followup_prompt: followupPrompt,
        followup_required: followupRequired,
        randomize_options: randomizeOptions,
      });
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save question");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteQuestion() {
    try {
      await deleteQuestion(question.id);
      onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete question");
    }
  }

  async function handleSaveOption(
    label: string,
    sourceType: "upload" | "url",
    imageFile: File | null,
    sourceUrl: string | null,
    optionId?: number,
  ) {
    setError(null);
    const formData = new FormData();
    formData.append("label", label);
    formData.append("source_type", sourceType);
    if (sourceType === "upload" && imageFile) {
      formData.append("image", imageFile);
    }
    if (sourceType === "url" && sourceUrl) {
      formData.append("source_url", sourceUrl);
    }

    try {
      if (optionId) {
        await updateOption(optionId, formData);
      } else {
        await createOption(question.id, formData);
      }
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save option");
    }
  }

  async function handleDeleteOption(optionId: number) {
    try {
      await deleteOption(optionId);
      onUpdate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete option");
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-start">
        <h3 className="text-sm font-medium text-gray-500">Question {question.order + 1}</h3>
        <Button variant="danger" size="sm" onClick={handleDeleteQuestion}>
          Delete Question
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-2 rounded text-sm">{error}</div>
      )}

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Question title (e.g., Which homepage do you prefer?)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        maxLength={500}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Follow-up prompt</label>
          <input
            type="text"
            value={followupPrompt}
            onChange={(e) => setFollowupPrompt(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            maxLength={500}
          />
        </div>
        <div className="flex items-end gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={followupRequired}
              onChange={(e) => setFollowupRequired(e.target.checked)}
              className="rounded border-gray-300"
            />
            Follow-up required
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={randomizeOptions}
              onChange={(e) => setRandomizeOptions(e.target.checked)}
              className="rounded border-gray-300"
            />
            Randomize options
          </label>
        </div>
      </div>

      <Button size="sm" onClick={handleSaveQuestion} disabled={saving || !title.trim()}>
        {saving ? "Saving..." : "Save Question"}
      </Button>

      <div className="border-t pt-4 mt-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Options</h4>
        <div className="space-y-3">
          {question.options.map((opt) => (
            <OptionEditor
              key={opt.id}
              optionId={opt.id}
              initialLabel={opt.label}
              initialSourceType={opt.source_type}
              initialImageUrl={opt.image_url}
              initialSourceUrl={opt.source_url}
              onSave={(label, sourceType, file, sourceUrl) =>
                handleSaveOption(label, sourceType, file, sourceUrl, opt.id)
              }
              onDelete={() => handleDeleteOption(opt.id)}
            />
          ))}
          {/* Only show "Add Option" editor when fewer than 5 options */}
          {question.options.length < 5 && (
            <OptionEditor
              initialLabel=""
              isNew
              onSave={(label, sourceType, file, sourceUrl) =>
                handleSaveOption(label, sourceType, file, sourceUrl)
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write TestMetaForm component**

```tsx
// frontend/components/test-builder/TestMetaForm.tsx
"use client";

import { useState } from "react";
import Button from "@/components/shared/Button";

interface TestMetaFormProps {
  initialName?: string;
  initialDescription?: string;
  onSave: (name: string, description: string) => Promise<void>;
  submitLabel?: string;
}

export default function TestMetaForm({
  initialName = "",
  initialDescription = "",
  onSave,
  submitLabel = "Save",
}: TestMetaFormProps) {
  const [name, setName] = useState(initialName);
  const [description, setDescription] = useState(initialDescription);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave(name.trim(), description.trim());
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Test Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Homepage A/B Test"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          maxLength={200}
          required
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description <span className="text-gray-400">(shown to respondents)</span>
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional intro text for respondents..."
          rows={3}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
          maxLength={2000}
        />
      </div>
      <Button type="submit" disabled={saving || !name.trim()}>
        {saving ? "Saving..." : submitLabel}
      </Button>
    </form>
  );
}
```

- [ ] **Step 5: Write the create test page**

```tsx
// frontend/app/(designer)/tests/new/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createTest } from "@/lib/api";
import TestMetaForm from "@/components/test-builder/TestMetaForm";
import Card from "@/components/shared/Card";

export default function NewTestPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(name: string, description: string) {
    setError(null);
    try {
      const test = await createTest({ name, description: description || undefined });
      router.push(`/tests/${test.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create test");
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Test</h1>
      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-4 text-sm">{error}</div>
      )}
      <Card>
        <TestMetaForm onSave={handleCreate} submitLabel="Create Test" />
      </Card>
    </div>
  );
}
```

- [ ] **Step 6: Verify TypeScript compilation**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npx tsc --noEmit
```

- [ ] **Step 7: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add "frontend/app/(designer)/tests/new/" frontend/components/test-builder/
git commit -m "feat: add test builder page with source_type toggle, max 5 options, and drag-drop image upload"
```

**Acceptance Criteria:**
- Creating a test navigates to its detail page
- OptionEditor shows radio toggle between "Image Upload" and "URL"
- Radio button names use `useId()` for uniqueness (no collisions)
- ImageUploader validates file type and size client-side before upload
- "Add Option" editor disappears when question has 5 options
- QuestionEditor calls API via FormData (not JSON) for option mutations

**Test Strategy:** TypeScript compilation + visual verification with both servers running.

---

### Task 17: Test Detail/Edit Page

**Files:**
- Create: `frontend/app/(designer)/tests/[testId]/page.tsx`

**What:** Build the test detail page showing test metadata, status controls, questions (editable in draft, read-only in active/closed), shareable link, and delete with confirmation. Imports `QuestionEditor` and `TestMetaForm` from Task 16.

**Dependencies:** Task 12, Task 13, Task 16 (uses QuestionEditor, TestMetaForm from test-builder components)

**Complexity:** L

- [ ] **Step 1: Write the test detail page**

```tsx
// frontend/app/(designer)/tests/[testId]/page.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import type { TestDetail } from "@/lib/types";
import { API_BASE_URL } from "@/lib/constants";
import {
  fetchTest,
  updateTest,
  deleteTest,
  createQuestion,
} from "@/lib/api";
import Card from "@/components/shared/Card";
import Button from "@/components/shared/Button";
import StatusBadge from "@/components/shared/StatusBadge";
import ConfirmDialog from "@/components/shared/ConfirmDialog";
import TestMetaForm from "@/components/test-builder/TestMetaForm";
import QuestionEditor from "@/components/test-builder/QuestionEditor";

export default function TestDetailPage() {
  const params = useParams();
  const router = useRouter();

  // Null guard for useParams() during prerendering
  if (!params?.testId) return <p className="text-gray-500">Loading...</p>;

  const testId = Number(params.testId);

  const [test, setTest] = useState<TestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const loadTest = useCallback(async () => {
    try {
      const data = await fetchTest(testId);
      setTest(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load test");
    } finally {
      setLoading(false);
    }
  }, [testId]);

  useEffect(() => {
    loadTest();
  }, [loadTest]);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!test) return <p className="text-red-600">Test not found</p>;

  const isDraft = test.status === "draft";
  const canActivate = isDraft && test.questions.length > 0 && test.questions.every(
    (q) => q.options.length >= 2 && q.options.length <= 5
  );

  async function handleUpdateMeta(name: string, description: string) {
    await updateTest(testId, { name, description: description || undefined });
    loadTest();
  }

  async function handleStatusChange(newStatus: string) {
    setError(null);
    try {
      await updateTest(testId, { status: newStatus });
      loadTest();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    }
  }

  async function handleAddQuestion() {
    await createQuestion(testId, { title: "New question" });
    loadTest();
  }

  async function handleDelete() {
    await deleteTest(testId);
    router.push("/");
  }

  const respondUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/respond/${test.slug}`;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{test.name}</h1>
            <StatusBadge status={test.status} />
          </div>
          {test.status !== "draft" && (
            <p className="text-sm text-gray-500">
              Share: <code className="bg-gray-100 px-2 py-0.5 rounded text-xs">{respondUrl}</code>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Link href={`/tests/${testId}/analytics`}>
            <Button variant="secondary">Analytics</Button>
          </Link>
          <Button variant="danger" size="sm" onClick={() => setShowDeleteDialog(true)}>
            Delete
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Status controls */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-medium text-gray-700">Test Status</h2>
            <p className="text-xs text-gray-400 mt-1">
              {isDraft && "Draft -- add questions and options, then activate to start collecting responses."}
              {test.status === "active" && "Active -- respondents can take this test. Questions and options are locked."}
              {test.status === "closed" && "Closed -- no more responses accepted."}
            </p>
          </div>
          <div className="flex gap-2">
            {isDraft && (
              <Button
                onClick={() => handleStatusChange("active")}
                disabled={!canActivate}
                title={canActivate ? "" : "Need at least 1 question with 2-5 options each"}
              >
                Activate
              </Button>
            )}
            {test.status === "active" && (
              <Button variant="secondary" onClick={() => handleStatusChange("closed")}>
                Close Test
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Meta form -- always editable for name/description */}
      <Card>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Test Details</h2>
        <TestMetaForm
          initialName={test.name}
          initialDescription={test.description || ""}
          onSave={handleUpdateMeta}
          submitLabel="Update"
        />
      </Card>

      {/* Questions -- only editable in draft */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Questions ({test.questions.length})
          </h2>
          {isDraft && (
            <Button size="sm" onClick={handleAddQuestion}>
              Add Question
            </Button>
          )}
        </div>
        {isDraft ? (
          <div className="space-y-4">
            {test.questions.map((q) => (
              <QuestionEditor
                key={q.id}
                question={q}
                testId={testId}
                onUpdate={loadTest}
                onDelete={loadTest}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {test.questions.map((q) => (
              <Card key={q.id}>
                <h3 className="font-medium text-gray-900">{q.title}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {q.options.length} options | Follow-up: {q.followup_required ? "required" : "optional"} | Randomize: {q.randomize_options ? "yes" : "no"}
                </p>
                <div className="flex gap-2 mt-3 flex-wrap">
                  {q.options.map((o) => (
                    <div key={o.id} className="text-center">
                      {o.source_type === "upload" && o.image_url && (
                        <img
                          src={`${API_BASE_URL}${o.image_url}`}
                          alt={o.label}
                          className="h-24 object-contain rounded border"
                        />
                      )}
                      {o.source_type === "url" && o.source_url && (
                        <a href={o.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 text-xs underline">
                          {o.source_url}
                        </a>
                      )}
                      <p className="text-xs text-gray-600 mt-1">{o.label}</p>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={showDeleteDialog}
        title="Delete Test"
        message="This will permanently delete this test, all questions, options, and responses. This cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteDialog(false)}
      />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add "frontend/app/(designer)/tests/[testId]/page.tsx"
git commit -m "feat: add test detail page with status management, source_type display, and question editing"
```

**Acceptance Criteria:**
- Page loads test data by ID from URL params (with null guard)
- Draft tests show editable QuestionEditors
- Active/closed tests show read-only question summaries with option previews
- Activate button disabled when questions don't meet 2-5 options requirement
- Share URL shown after activation
- Delete triggers ConfirmDialog, then navigates to dashboard on confirm
- Analytics link navigates to `/tests/{id}/analytics`
- URL options in read-only mode have `rel="noopener noreferrer"` on links

**Test Strategy:** Visual verification with both servers running.

---

### Task 18: Respondent Flow Page

**Files:**
- Create: `frontend/app/respond/[slug]/page.tsx`
- Create: `frontend/components/respondent/IntroScreen.tsx`
- Create: `frontend/components/respondent/ProgressBar.tsx`
- Create: `frontend/components/respondent/FollowUpInput.tsx`
- Create: `frontend/components/respondent/OptionCard.tsx`
- Create: `frontend/components/respondent/QuestionView.tsx`

**What:** Build the full respondent experience. FollowUpInput renders the question-specific `followup_prompt` text (not a hardcoded default). All new-tab links use `rel="noopener noreferrer"`.

**Dependencies:** Task 12, Task 13

**Complexity:** L

- [ ] **Step 1: Write ProgressBar component**

```tsx
// frontend/components/respondent/ProgressBar.tsx

interface ProgressBarProps {
  current: number;
  total: number;
}

export default function ProgressBar({ current, total }: ProgressBarProps) {
  const percentage = total > 0 ? ((current + 1) / total) * 100 : 0;
  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm text-gray-500 mb-1">
        <span>Question {current + 1} of {total}</span>
        <span>{Math.round(percentage)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write FollowUpInput component (renders configured prompt text)**

```tsx
// frontend/components/respondent/FollowUpInput.tsx
"use client";

interface FollowUpInputProps {
  prompt: string;
  required: boolean;
  value: string;
  onChange: (value: string) => void;
}

export default function FollowUpInput({ prompt, required, value, onChange }: FollowUpInputProps) {
  const maxLength = 500;
  return (
    <div className="mt-6">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {prompt}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        maxLength={maxLength}
        placeholder="Share your reasoning..."
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
      />
      <div className="text-xs text-gray-400 text-right mt-1">
        {value.length}/{maxLength}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write OptionCard component (handles upload + URL, rel="noopener noreferrer")**

```tsx
// frontend/components/respondent/OptionCard.tsx
"use client";

import { API_BASE_URL } from "@/lib/constants";

interface OptionCardProps {
  label: string;
  sourceType: "upload" | "url";
  imageUrl: string | null;
  sourceUrl: string | null;
  selected: boolean;
  locked: boolean;
  onClick: () => void;
}

export default function OptionCard({
  label,
  sourceType,
  imageUrl,
  sourceUrl,
  selected,
  locked,
  onClick,
}: OptionCardProps) {
  const borderClass = selected
    ? "border-blue-500 ring-2 ring-blue-200"
    : "border-gray-200 hover:border-gray-400";
  const cursorClass = locked ? "cursor-default" : "cursor-pointer";

  return (
    <div
      className={`relative border-2 rounded-lg overflow-hidden transition-all ${borderClass} ${cursorClass}`}
      onClick={locked ? undefined : onClick}
    >
      {sourceType === "upload" && imageUrl && (
        <div className="flex justify-center bg-gray-50 p-2">
          <img
            src={`${API_BASE_URL}${imageUrl}`}
            alt={label}
            className="object-contain max-h-64 sm:max-h-96"
          />
        </div>
      )}
      {sourceType === "url" && sourceUrl && (
        <div className="bg-gray-50 p-2">
          <iframe
            src={sourceUrl}
            title={label}
            className="w-full h-48 sm:h-64 rounded border"
            sandbox="allow-scripts allow-same-origin"
            style={{ pointerEvents: "none" }}
          />
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-center text-xs text-blue-600 underline mt-1"
            onClick={(e) => e.stopPropagation()}
          >
            Open in new tab
          </a>
        </div>
      )}
      <div className="p-3 text-center">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {selected && (
          <span className="inline-block mt-1 text-xs text-blue-600 font-medium">
            Locked in
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write QuestionView component (with Fisher-Yates shuffle)**

```tsx
// frontend/components/respondent/QuestionView.tsx
"use client";

import { useMemo } from "react";
import type { Question } from "@/lib/types";
import OptionCard from "./OptionCard";

interface QuestionViewProps {
  question: Question;
  selectedOptionId: number | null;
  locked: boolean;
  onSelect: (optionId: number) => void;
}

function shuffleArray<T>(arr: T[]): T[] {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export default function QuestionView({
  question,
  selectedOptionId,
  locked,
  onSelect,
}: QuestionViewProps) {
  const displayOptions = useMemo(() => {
    if (question.randomize_options) {
      return shuffleArray(question.options);
    }
    return [...question.options].sort((a, b) => a.order - b.order);
  }, [question.id, question.randomize_options, question.options.length]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
        {question.title}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {displayOptions.map((option) => (
          <OptionCard
            key={option.id}
            label={option.label}
            sourceType={option.source_type}
            imageUrl={option.image_url}
            sourceUrl={option.source_url}
            selected={selectedOptionId === option.id}
            locked={locked}
            onClick={() => onSelect(option.id)}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write IntroScreen component**

```tsx
// frontend/components/respondent/IntroScreen.tsx
"use client";

import Button from "@/components/shared/Button";

interface IntroScreenProps {
  name: string;
  description: string | null;
  onStart: () => void;
}

export default function IntroScreen({ name, description, onStart }: IntroScreenProps) {
  return (
    <div className="max-w-lg mx-auto text-center py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-4">{name}</h1>
      {description && <p className="text-gray-600 mb-8">{description}</p>}
      <Button size="lg" onClick={onStart}>
        Start
      </Button>
    </div>
  );
}
```

- [ ] **Step 6: Write the respondent flow page (with null guard for useParams)**

```tsx
// frontend/app/respond/[slug]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { RespondentTest } from "@/lib/types";
import { fetchTestForRespondent, submitAnswer } from "@/lib/api";
import IntroScreen from "@/components/respondent/IntroScreen";
import QuestionView from "@/components/respondent/QuestionView";
import FollowUpInput from "@/components/respondent/FollowUpInput";
import ProgressBar from "@/components/respondent/ProgressBar";
import Button from "@/components/shared/Button";

type Phase = "loading" | "error" | "intro" | "question" | "done";

export default function RespondPage() {
  const params = useParams();

  // Null guard for useParams() during prerendering
  if (!params?.slug) return <p className="text-center text-gray-500 py-16">Loading...</p>;

  const slug = params.slug as string;

  const [test, setTest] = useState<RespondentTest | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(null);
  const [isLocked, setIsLocked] = useState(false);
  const [followupText, setFollowupText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    fetchTestForRespondent(slug)
      .then((data) => {
        setTest(data);
        setPhase("intro");
      })
      .catch((e) => {
        setErrorMsg(e instanceof Error ? e.message : "Failed to load test");
        setPhase("error");
      });
  }, [slug]);

  function handleSelect(optionId: number) {
    if (isLocked) return;
    setSelectedOptionId(optionId);
    setIsLocked(true);
  }

  async function handleNext() {
    if (!test || selectedOptionId === null) return;
    const question = test.questions[currentIndex];

    if (question.followup_required && !followupText.trim()) {
      return;
    }

    setSubmitting(true);
    try {
      await submitAnswer(slug, {
        session_id: sessionId,
        question_id: question.id,
        option_id: selectedOptionId,
        followup_text: followupText.trim() || undefined,
      });

      if (currentIndex < test.questions.length - 1) {
        setCurrentIndex((i) => i + 1);
        setSelectedOptionId(null);
        setIsLocked(false);
        setFollowupText("");
      } else {
        setPhase("done");
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to submit answer");
    } finally {
      setSubmitting(false);
    }
  }

  if (phase === "loading") {
    return <p className="text-center text-gray-500 py-16">Loading...</p>;
  }

  if (phase === "error") {
    return (
      <div className="text-center py-16">
        <p className="text-red-600 text-lg">{errorMsg}</p>
      </div>
    );
  }

  if (phase === "intro" && test) {
    return (
      <IntroScreen
        name={test.name}
        description={test.description}
        onStart={() => setPhase("question")}
      />
    );
  }

  if (phase === "done") {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Thank you!</h1>
        <p className="text-gray-600">Your responses have been recorded.</p>
      </div>
    );
  }

  if (phase === "question" && test) {
    const question = test.questions[currentIndex];
    const canProceed =
      isLocked && (!question.followup_required || followupText.trim().length > 0);

    return (
      <div className="max-w-4xl mx-auto">
        <ProgressBar current={currentIndex} total={test.questions.length} />

        <QuestionView
          question={question}
          selectedOptionId={selectedOptionId}
          locked={isLocked}
          onSelect={handleSelect}
        />

        {isLocked && (
          <FollowUpInput
            prompt={question.followup_prompt}
            required={question.followup_required}
            value={followupText}
            onChange={setFollowupText}
          />
        )}

        {errorMsg && (
          <p className="text-red-500 text-sm mt-4">{errorMsg}</p>
        )}

        <div className="flex justify-end mt-6">
          <Button
            onClick={handleNext}
            disabled={!canProceed || submitting}
            size="lg"
          >
            {submitting
              ? "Saving..."
              : currentIndex < test.questions.length - 1
              ? "Next"
              : "Finish"}
          </Button>
        </div>
      </div>
    );
  }

  return null;
}
```

- [ ] **Step 7: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add frontend/app/respond/ frontend/components/respondent/
git commit -m "feat: add respondent flow with lock-in, URL/upload support, responsive grid, and Fisher-Yates shuffle"
```

**Acceptance Criteria:**
- Intro screen shows test name and description
- Options display correctly for both upload (image) and URL (iframe) modes
- Clicking an option locks it in immediately (no undo)
- Follow-up input appears after lock-in and renders the question-specific `followup_prompt` text (not a hardcoded default)
- "Next" button disabled until selection is locked AND required followup is filled
- Progress bar updates correctly
- Thank-you screen shown after last question
- Responsive: 1 column on mobile, 2 columns on desktop
- No Navbar visible (respondent layout)
- `useMemo` dependency array includes `question.options.length`
- All "Open in new tab" links have `rel="noopener noreferrer"`
- `useParams()` has a null guard

**Test Strategy:** Visual verification with active test.

---

### Task 19: Analytics Dashboard Page (with Recharts)

**Files:**
- Create: `frontend/components/analytics/SummaryStats.tsx`
- Create: `frontend/components/analytics/VoteChart.tsx`
- Create: `frontend/components/analytics/FollowUpList.tsx`
- Create: `frontend/components/analytics/ExportButton.tsx`
- Create: `frontend/app/(designer)/tests/[testId]/analytics/page.tsx`

**What:** Build the analytics dashboard. All code provided inline below.

**Dependencies:** Task 15-18 (pattern established), Task 12

**Complexity:** L

- [ ] **Step 1: Install Recharts**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npm install recharts
```

- [ ] **Step 2: Write SummaryStats component**

```tsx
// frontend/components/analytics/SummaryStats.tsx

interface SummaryStatsProps {
  totalSessions: number;
  totalAnswers: number;
  completedSessions: number;
  completionRate: number;
}

export default function SummaryStats({
  totalSessions,
  totalAnswers,
  completedSessions,
  completionRate,
}: SummaryStatsProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalSessions}</p>
        <p className="text-sm text-gray-500">Respondents</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalAnswers}</p>
        <p className="text-sm text-gray-500">Total Answers</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{completedSessions}</p>
        <p className="text-sm text-gray-500">Completed</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{completionRate}%</p>
        <p className="text-sm text-gray-500">Completion Rate</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write VoteChart component**

```tsx
// frontend/components/analytics/VoteChart.tsx
"use client";

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import type { OptionAnalytics } from "@/lib/types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

interface VoteChartProps {
  options: OptionAnalytics[];
  questionTitle: string;
}

export default function VoteChart({ options, questionTitle }: VoteChartProps) {
  const [view, setView] = useState<"bar" | "pie">("bar");

  const data = options.map((o) => ({
    name: o.label,
    votes: o.votes,
    percentage: o.percentage,
  }));

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-base font-semibold text-gray-900">{questionTitle}</h3>
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setView("bar")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              view === "bar" ? "bg-white shadow text-gray-900" : "text-gray-500"
            }`}
          >
            Bar
          </button>
          <button
            onClick={() => setView("pie")}
            className={`px-3 py-1 text-xs rounded-md font-medium transition-colors ${
              view === "pie" ? "bg-white shadow text-gray-900" : "text-gray-500"
            }`}
          >
            Pie
          </button>
        </div>
      </div>

      {view === "bar" ? (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis allowDecimals={false} />
            <Tooltip
              formatter={(value: number, _name: string, props: any) => {
                const percentage = props.payload?.percentage ?? 0;
                return [`${value} votes (${percentage}%)`, "Votes"];
              }}
            />
            <Bar dataKey="votes" fill="#3B82F6" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="votes"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percentage }) => `${name}: ${percentage}%`}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Write FollowUpList component**

```tsx
// frontend/components/analytics/FollowUpList.tsx
"use client";

import { useState } from "react";
import type { OptionAnalytics } from "@/lib/types";

interface FollowUpListProps {
  options: OptionAnalytics[];
}

export default function FollowUpList({ options }: FollowUpListProps) {
  const optionsWithFollowups = options.filter((o) => o.followup_texts.length > 0);
  const [expandedOption, setExpandedOption] = useState<number | null>(
    optionsWithFollowups.length > 0 ? optionsWithFollowups[0].option_id : null
  );

  if (optionsWithFollowups.length === 0) {
    return <p className="text-gray-400 text-sm">No follow-up responses.</p>;
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-gray-700">Follow-up Responses</h4>
      {optionsWithFollowups.map((option) => (
        <div key={option.option_id} className="border border-gray-200 rounded-lg">
          <button
            className="w-full text-left px-4 py-3 flex justify-between items-center text-sm font-medium text-gray-800 hover:bg-gray-50"
            onClick={() =>
              setExpandedOption(expandedOption === option.option_id ? null : option.option_id)
            }
          >
            <span>
              {option.label}
              {option.is_winner && (
                <span className="ml-2 text-xs text-green-600 font-normal">(winner)</span>
              )}
            </span>
            <span className="text-gray-400">{option.followup_texts.length} responses</span>
          </button>
          {expandedOption === option.option_id && (
            <div className="px-4 pb-3 space-y-2">
              {option.followup_texts.map((f, i) => (
                <div key={i} className="bg-gray-50 rounded p-2 text-sm text-gray-700">
                  &ldquo;{f.text}&rdquo;
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Write ExportButton component**

```tsx
// frontend/components/analytics/ExportButton.tsx
"use client";

import { getExportUrl } from "@/lib/api";
import Button from "@/components/shared/Button";

interface ExportButtonProps {
  testId: number;
}

export default function ExportButton({ testId }: ExportButtonProps) {
  function handleExport() {
    window.open(getExportUrl(testId), "_blank", "noopener,noreferrer");
  }

  return (
    <Button variant="secondary" onClick={handleExport}>
      Export CSV
    </Button>
  );
}
```

- [ ] **Step 6: Write analytics page (with null guard for useParams)**

```tsx
// frontend/app/(designer)/tests/[testId]/analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Analytics } from "@/lib/types";
import { fetchAnalytics } from "@/lib/api";
import Card from "@/components/shared/Card";
import EmptyState from "@/components/shared/EmptyState";
import Button from "@/components/shared/Button";
import SummaryStats from "@/components/analytics/SummaryStats";
import VoteChart from "@/components/analytics/VoteChart";
import FollowUpList from "@/components/analytics/FollowUpList";
import ExportButton from "@/components/analytics/ExportButton";

export default function AnalyticsPage() {
  const params = useParams();

  // Null guard for useParams() during prerendering
  if (!params?.testId) return <p className="text-gray-500">Loading...</p>;

  const testId = Number(params.testId);

  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics(testId)
      .then(setAnalytics)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, [testId]);

  if (loading) return <p className="text-gray-500">Loading analytics...</p>;
  if (error) return <p className="text-red-600">Error: {error}</p>;
  if (!analytics) return <p className="text-red-600">No data</p>;

  if (analytics.total_sessions === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{analytics.test_name} -- Analytics</h1>
          <Link href={`/tests/${testId}`}>
            <Button variant="secondary">Back to Test</Button>
          </Link>
        </div>
        <EmptyState
          title="No responses yet"
          message="Share the test link to start collecting responses."
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">{analytics.test_name} -- Analytics</h1>
        <div className="flex gap-2">
          <ExportButton testId={testId} />
          <Link href={`/tests/${testId}`}>
            <Button variant="secondary">Back to Test</Button>
          </Link>
        </div>
      </div>

      <SummaryStats
        totalSessions={analytics.total_sessions}
        totalAnswers={analytics.total_answers}
        completedSessions={analytics.completed_sessions}
        completionRate={analytics.completion_rate}
      />

      {analytics.questions.map((q) => (
        <Card key={q.question_id}>
          <VoteChart options={q.options} questionTitle={q.title} />
          <div className="border-t mt-6 pt-4">
            <FollowUpList options={q.options} />
          </div>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Verify TypeScript compilation**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npx tsc --noEmit
```

- [ ] **Step 8: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add "frontend/app/(designer)/tests/[testId]/analytics/" frontend/components/analytics/ frontend/package.json frontend/package-lock.json
git commit -m "feat: add analytics dashboard with Recharts, completion rate, and CSV export"
```

**Acceptance Criteria:**
- Recharts renders bar and pie charts without SSR errors
- Summary shows all four metrics including completion rate
- Bar/pie toggle works
- Tooltip shows correct percentages even when options are tied
- Follow-up texts are expandable per option
- Export button opens CSV download in new tab (with `noopener,noreferrer`)
- Empty state shown when no responses
- "Back to Test" link works
- `useParams()` has null guard

**Test Strategy:** TypeScript compilation + visual verification with test data.

---

### Task 20: Verification and Backend .gitignore

**Files:**
- Create: `backend/.gitignore`

**What:** Verify that the complete main.py (created in Task 5) works with all five routers. Add backend-specific `.gitignore`. Run integration tests to confirm nothing broke. **This task does NOT rewrite main.py** -- it was already written with all routers in Task 5.

**Dependencies:** Task 6, Task 7, Task 8, Task 9, Task 10 (all routes must exist)

**Complexity:** S

- [ ] **Step 1: Write backend .gitignore**

```
venv/
__pycache__/
*.pyc
data/
media/
.pytest_cache/
```

- [ ] **Step 2: Verify server starts with all routes**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && timeout 5 uvicorn main:app --port 8000 || true
```

- [ ] **Step 3: Run integration tests to verify nothing broke**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add backend/.gitignore
git commit -m "chore: add backend .gitignore and verify all routes work"
```

**Acceptance Criteria:**
- Server starts with all 5 routers loaded
- Swagger UI shows all endpoints
- All integration tests pass (both test_workflow.py and test_upload.py)
- `backend/.gitignore` prevents `venv/`, `data/`, `media/`, `__pycache__/` from being tracked

**Test Strategy:** Server startup + integration test pass.

---

### Task 21: End-to-End Smoke Test

**Files:** None created. This is a manual verification task.

**What:** Verify the complete application works end-to-end with both servers running simultaneously.

**Dependencies:** All previous tasks (1-20)

**Complexity:** M

- [ ] **Step 1: Start backend**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend (in a separate terminal)**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npm run dev
```

- [ ] **Step 3: Verify full flow**

Walk through these checks:

1. Visit `http://localhost:3000` -- see empty dashboard (Client Component, no SSR crash)
2. Click "New Test" -- create test "Homepage Test" with a description
3. On test detail page, add a question with title "Which homepage?"
4. Add option with source_type=upload (upload a JPEG/PNG image)
5. Add option with source_type=url (enter `https://example.com`)
6. Verify max 5 options enforcement: add options until 5, verify "Add Option" form disappears
7. Click "Activate" -- status changes to active, share link appears
8. Open share link (`/respond/{slug}`) in a new/incognito tab -- see intro screen
9. Verify NO Navbar on respondent page
10. Click "Start", verify responsive grid (resize browser to mobile width)
11. Select an option -- verify "Locked in" indicator, no undo possible
12. For URL options, verify iframe with pointer-events disabled and "Open in new tab" link has `rel="noopener noreferrer"`
13. Verify the follow-up prompt shows the question-specific `followup_prompt` text (not a hardcoded default)
14. Type follow-up text, click Next/Finish
15. See "Thank you" screen
16. Back on designer side, go to Analytics -- see respondent count, total answers, completion rate
17. Verify bar/pie chart toggle works
18. Verify tooltip percentages are correct
19. Click "Export CSV" -- download should contain response data
20. Close the test -- share link should return error
21. Verify ConfirmDialog closes on Escape key

- [ ] **Step 4: Fix any issues found and commit**

```bash
cd /Users/bharath/Documents/abtestingapp && git add -A
git commit -m "fix: address issues found during end-to-end smoke test"
```

(Only if fixes were needed. If no fixes, skip this step.)

**Acceptance Criteria:**
- All 21 verification steps pass without errors
- Both servers running simultaneously without port conflicts
- Client-side navigation works between all pages
- API calls succeed (check browser DevTools Network tab for any 4xx/5xx)

**Test Strategy:** This IS the test -- a manual walkthrough of the entire application.

---

### Task 22: Final Commit and Cleanup

**Files:**
- Potentially modify any files with minor issues found in Task 21

**What:** Run the integration test suite one final time, verify TypeScript compilation, and make a clean final commit.

**Dependencies:** Task 21

**Complexity:** S

- [ ] **Step 1: Run backend tests**

```bash
cd /Users/bharath/Documents/abtestingapp/backend && source venv/bin/activate && python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Run frontend type check**

```bash
cd /Users/bharath/Documents/abtestingapp/frontend && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 3: Final commit (if any uncommitted changes)**

```bash
cd /Users/bharath/Documents/abtestingapp && git status
```

If there are uncommitted changes:

```bash
git add -A && git commit -m "chore: final cleanup after end-to-end verification"
```

**Acceptance Criteria:**
- All backend tests pass (test_workflow.py + test_upload.py)
- Frontend compiles without TypeScript errors
- Git working tree is clean (no uncommitted changes)
- Application is fully functional

**Test Strategy:** Backend pytest + frontend tsc --noEmit + clean git status.

---

## Task Summary Table

| # | Task | Dependencies | Parallel Group | Complexity | Files |
|---|------|-------------|----------------|------------|-------|
| 1 | Git Init + Root Files | None | G1 | S | `.gitignore` |
| 2 | Backend Scaffold | T1 | G2 | M | `main.py`, `config.py`, `database.py`, `utils.py`, `limiter.py`, `requirements.txt` |
| 3 | Database Models | T2 | G3 | M | `backend/app/models/*.py` |
| 4 | Pydantic Schemas | T3 | G4 | S | `backend/app/schemas/*.py` |
| 5 | Image Service + Complete main.py | T4 | G5 | M | `image_service.py`, `main.py` (final), placeholder route files |
| 6 | Test CRUD Routes | T5 | G6 | L | `backend/app/routes/tests.py` |
| 7 | Question CRUD Routes | T5 | G6 | M | `backend/app/routes/questions.py` |
| 8 | Option CRUD Routes | T5 | G6 | L | `backend/app/routes/options.py` |
| 9 | Respondent Routes | T5, T6 | G6b | M | `backend/app/routes/respond.py` |
| 10 | Analytics Routes | T6-T9 | G7 | L | `analytics_service.py`, `backend/app/routes/analytics.py` |
| 11 | Frontend Scaffold | T1 | G2 | M | `frontend/` (create-next-app), layouts |
| 12 | Frontend Types + API | T11 | G4 | M | `frontend/lib/constants.ts`, `types.ts`, `api.ts` |
| 13 | Shared UI Components | T11 | G4 | M | `frontend/components/shared/*.tsx`, `layout/Navbar.tsx` |
| 14 | Backend Integration Test | T6-T10 | G8 | M | `conftest.py`, `test_workflow.py` |
| 14b | Upload + URL Validation Tests | T6-T10 | G8 | M | `test_upload.py` |
| 15 | Dashboard Page | T12, T13 | G9 | M | `frontend/app/(designer)/page.tsx` |
| 16 | Test Builder Page | T12, T13 | G9 | L | `tests/new/page.tsx`, builder components |
| 17 | Test Detail Page | T12, T13, T16 | G9b | L | `tests/[testId]/page.tsx` |
| 18 | Respondent Flow Page | T12, T13 | G9 | L | `respond/[slug]/page.tsx`, respondent components |
| 19 | Analytics Page | T12, T15-T18 | G10 | L | `tests/[testId]/analytics/page.tsx`, chart components |
| 20 | Verification + Gitignore | T6-T10 | G11 | S | `backend/.gitignore` |
| 21 | E2E Smoke Test | T1-T20 | G12 | M | None (manual verification) |
| 22 | Final Cleanup | T21 | G13 | S | None (tests + commit) |

---

## Recommended Execution Order

For **sequential execution** (single agent):
1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 14b, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22

For **parallel execution** (multiple agents):
- Agent A (backend): 1 -> 2 -> 3 -> 4 -> 5 -> 6,7,8 (parallel) -> 9 -> 10 -> 14,14b (parallel) -> 20
- Agent B (frontend): (wait for T1) -> 11 -> 12,13 (parallel) -> 15,16,18 (parallel) -> 17 -> 19
- Then: 21 -> 22 (sequential, needs both complete)
