# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

DesignPoll — A/B testing web app for UI/UX designers. Designers create forced-choice design tests with multiple screen questions, each with 2-5 options (image upload or URL). Respondents select options (locked-in, no undo), optionally provide reasoning, and designers view results via an analytics dashboard.

## Commands

### Backend (from `backend/`)
```bash
source venv/bin/activate          # Activate virtualenv
uvicorn main:app --reload         # Start dev server on :8000
python -m pytest tests/ -v        # Run all tests
python -m pytest tests/test_workflow.py -v  # Run specific test file
```

### Frontend (from `frontend/`)
```bash
npm run dev                       # Start Next.js dev server on :3000
npx tsc --noEmit                  # Type check
```

### Both Together
Start backend first (port 8000), then frontend (port 3000). Frontend calls backend API via `http://localhost:8000`.

## Architecture

**Frontend:** Next.js 14 (App Router, TypeScript, Tailwind CSS) — all data-fetching pages are Client Components
**Backend:** FastAPI (Python, SQLModel ORM, Pydantic v2)
**Database:** SQLite (WAL mode, `PRAGMA foreign_keys=ON` via event listener on every connection)
**Charts:** Recharts
**Image storage:** Local filesystem at `backend/media/{test_id}/`

### Key Design Decisions
- **No SSR data fetching** — all pages use `"use client"` with `useEffect` + `useState` to avoid build-time backend dependency
- **Route groups** — `(designer)` has Navbar layout; `respond/[slug]` has clean layout without Navbar
- **PRAGMA foreign_keys via event listener** — runs on every new SQLAlchemy connection, not just at startup
- **Rate limiting** — `slowapi` on respondent answer endpoint, limiter defined in `app/limiter.py` (not main.py) to avoid circular imports
- **File operation ordering** — save new file before deleting old; commit DB before deleting files
- **Test lifecycle** — draft → active → closed. Questions/options locked once active.
- **Batch-fetch pattern** — `_build_test_with_questions()` in `routes/tests.py` loads all options in one query, groups in Python (no N+1)

### API Endpoints
All under `/api/v1/`:
- `tests/` — CRUD for tests
- `tests/{id}/questions` — add questions
- `questions/{id}/options` — add options (multipart/form-data)
- `respond/{slug}` — respondent: get test + submit answers
- `tests/{id}/analytics` — analytics JSON
- `tests/{id}/export` — CSV download
