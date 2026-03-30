# Architectural Review: DesignPoll Implementation Plan

**Reviewer:** Senior Software Architect
**Date:** 2026-03-31
**Plan reviewed:** `02-plan.md`
**Requirement reviewed:** `requirement.md`
**Libraries verified via Context7:** FastAPI, Next.js, Recharts

---

## Critical

- **Dashboard page fetches from external backend inside a Server Component, which will fail at build time and may fail at runtime.** The plan makes `app/(designer)/page.tsx` an async Server Component calling `fetchTests()` which hits `http://localhost:8000`. Next.js Server Components using `fetch()` to an external backend work at runtime only if the backend is running, but `export const dynamic = "force-dynamic"` (which the plan does include) is required to prevent build-time fetch attempts. However, the bigger problem is that `API_BASE_URL` defaults to `http://localhost:8000` -- when Next.js SSR runs this on the server side, it calls `localhost:8000` from the Node.js process. This works locally but is fragile: if the backend is not up when the frontend starts, the page will hard-error with no recovery. --> Make the dashboard page a Client Component (like all other data-fetching pages in the plan already are), or add robust error boundaries. Client Component is simpler and consistent with the rest of the plan. The plan already has `try/catch` with error display, which mitigates this, but switching to a Client Component would be more resilient and consistent.

- **The `list_tests` endpoint performs N+1 queries inside a loop.** For each test, two additional COUNT queries are executed (one for question count, one for response count). With 50 tests, this becomes 101 queries per request. --> Use a single query with JOINs and GROUP BY, or use subqueries in the SELECT clause. Example: `select(Test, func.count(distinct(ScreenQuestion.id)), func.count(distinct(Response.session_id))).outerjoin(...).group_by(Test.id)`.

- **The `compute_analytics` function has severe N+1 query issues.** For every option within every question, it runs two separate queries (one for votes, one for followup texts). A test with 5 questions and 3 options each triggers ~35 queries. --> Batch-fetch all responses for the test in a single query, then aggregate in Python. This is simpler and faster: `select(Response).where(Response.screen_question_id.in_(question_ids))`.

## Major

- **SQLModel `cascade_delete=True` requires SQLAlchemy-level cascade config for SQLite.** SQLite does not enforce foreign key constraints by default. The plan enables WAL mode via `PRAGMA journal_mode=WAL` but never executes `PRAGMA foreign_keys=ON`. Without this pragma, `ON DELETE CASCADE` in the schema will be silently ignored, and deleting a Test will orphan all its ScreenQuestion, Option, and Response rows. --> Add `conn.execute(text("PRAGMA foreign_keys=ON"))` in the lifespan function. Alternatively, handle cascade deletes manually in application code (which the plan partially does by calling `session.delete(test)` with SQLAlchemy cascade, but the DB-level constraint should still be enabled for data integrity).

- **The integration test (`test_workflow.py`) uses the production database.** The test imports `engine` from `app.database` and calls `drop_all`/`create_all` on it. This will destroy any existing data in `backend/data/app.db`. --> Use a separate in-memory SQLite database for tests. Override the `get_session` dependency with a test database fixture. This is standard FastAPI testing practice.

- **No error handling for failed image operations in route handlers.** The `save_image` function reads the entire file into memory (`content = await file.read()`) before checking the size. A malicious or accidental 500MB upload would consume 500MB of server RAM before being rejected. --> Use a streaming approach: read in chunks and abort early if the accumulated size exceeds the limit. Alternatively, use Starlette's `request.form(max_files=1, max_fields=10)` with size limits, or check `file.size` (available on `UploadFile`) before reading.

- **Thumbnail generation for animated GIFs silently breaks.** Pillow's `Image.resize()` on a GIF only processes the first frame. The plan lists GIF as an allowed type but the thumbnail logic will produce a static thumbnail from an animated GIF. --> Either exclude GIF from thumbnail generation (serve the original), or document this as a known limitation. For an MVP, just copying the original GIF as the thumbnail (which the fallback already does if an exception occurs, but the resize path does not raise) is acceptable if documented.

- **The `generate_csv` function fetches option details inside a loop.** For each response, it calls `session.get(Option, r.option_id)`. For a test with 1000 responses, that is 1000 individual queries. --> Pre-fetch all options for the test in a single query and build a lookup dictionary.

- **No question reordering API.** The plan supports setting `order` on questions and options, but there is no bulk reorder endpoint. Reordering question 3 to position 1 requires patching three questions individually, each requiring a separate HTTP request. --> Add a `POST /api/v1/tests/{test_id}/questions/reorder` endpoint that accepts an ordered list of question IDs. This is a common pattern for drag-and-drop UIs. Not strictly MVP-blocking, but the QuestionEditor component implies ordering is important.

- **`useMemo` dependency array in `QuestionView` is incomplete.** The shuffle is memoized with `[question.id, question.randomize_options]` but `question.options` is not in the dependency array. If options change (e.g., options are added/removed while the component is mounted), the memo will be stale. For the respondent flow this is fine since options are fixed, but it is a subtle bug if this component is ever reused. --> Add `question.options` to the dependency array, or more precisely, `question.options.length`.

- **The respondent page does not hide the Navbar initially.** Task 18 restructures the app to use route groups, but this restructuring changes the file paths of all designer pages established in Tasks 13-17. This means Tasks 13-17 create pages at paths like `app/tests/...` but Task 18 moves them to `app/(designer)/tests/...`. If an implementor commits after each task (as instructed), they will need to do significant file moves in Task 18. --> Either restructure from the start (set up route groups in Task 11) or mention that Task 18 will require moving files. The plan does mention the file moves in Task 18, so this is more of a recommendation to restructure earlier.

## Minor

- **Pinned dependency versions may be stale by implementation time.** The plan pins `fastapi==0.115.6`, `uvicorn==0.34.0`, `sqlmodel==0.0.22`, `pillow==11.1.0`, `python-multipart==0.0.20`. These are reasonable versions, but Context7 confirms FastAPI and its ecosystem move quickly. --> Use compatible release operators (e.g., `fastapi~=0.115`) or verify versions at implementation time. The pinned versions are fine for reproducibility.

- **The `secrets.token_urlsafe(8)` generates 11-character slugs.** The plan says "11-char URL-safe slugs with low collision probability," which is correct, but with ~10^14 possible values, collision probability is effectively zero for a local app. However, the `slug` field is only `String(16)`. This is fine (11 < 16), but worth noting that `token_urlsafe(8)` can actually produce 10-12 characters due to base64 encoding variation. --> No action needed; the margin is sufficient.

- **`OptionPublic` schema includes `created_at` but the `Option` interface in `types.ts` also includes it.** The respondent does not need `created_at` on options, and it is minor data leakage. --> For the respondent endpoint, consider a slimmer response schema without timestamps. Not worth fixing for MVP.

- **The `apiFetch` utility in `api.ts` returns `undefined as T` for 204 responses.** This is a type-unsafe cast. If a caller expects a non-null return type, this could cause runtime errors. --> Return `null` and adjust function signatures to `Promise<T | null>` for DELETE operations, or use overloads.

- **`VoteChart` tooltip formatter has a bug.** The formatter uses `data.find((d) => d.votes === value)` to look up the percentage, but if two options have the same vote count, it will always find the first one. --> Pass the `percentage` field directly via the data or use the entry index.

- **Image URLs are hardcoded with `http://localhost:8000` in several places.** The `OptionCard` component uses `API_BASE_URL` from constants (correct), but `ImageUploader` and the test detail page use `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` inline. --> Consistently use the `API_BASE_URL` constant from `lib/constants.ts` everywhere to avoid duplication and make future deployment easier.

- **The `ConfirmDialog` does not trap focus or handle Escape key.** This is a minor accessibility issue. --> Add `onKeyDown` handler for Escape key and `aria-modal="true"` attributes. Consider using the native `<dialog>` element or a headless UI library. Not MVP-blocking.

- **No loading spinners or skeleton states.** All loading states show plain "Loading..." text. --> Consider adding simple skeleton components for the dashboard and analytics pages. This is polish, not MVP-blocking.

- **CORS allows all headers (`allow_headers=["*"]`) but restricts methods.** This is fine for local development but slightly inconsistent security posture. --> No action needed for local-only MVP.

- **`utcnow()` helper function is duplicated across all four model files.** --> Extract to a shared utility module (e.g., `app/utils.py`) and import.

- **No `completion_rate` in analytics.** The requirement mentions "completion rate" in the analytics summary bar, but the analytics response only includes `total_sessions` and `total_answers`. Completion rate = sessions that answered all questions / total sessions. --> Add a `completion_rate` field to `AnalyticsResponse`. Calculate as: count of session_ids that have a response for every question / total distinct session_ids. This can be deferred to post-MVP but is explicitly in the requirement.

## What's Good

- **Clean separation of concerns.** The backend has a well-organized structure with models, schemas, routes, and services in separate modules. The frontend follows Next.js App Router conventions with a clear component hierarchy.

- **Data model is sound.** The entity relationships (Test -> ScreenQuestion -> Option, Response linking to both ScreenQuestion and Option) correctly model the domain. The unique constraint on `(session_id, screen_question_id)` properly prevents double-voting. Indexes are placed on foreign key columns and frequently-queried fields.

- **Test lifecycle state machine is well-defined.** The draft -> active -> closed progression with clear transition rules and validation requirements (at least 1 question with 2+ options to activate) is exactly right for this use case. Enforcement at both backend (API validation) and frontend (disabled buttons with tooltips) is good defense-in-depth.

- **Image handling strategy is thorough.** UUID filenames prevent collisions and path traversal. Thumbnail generation at upload time avoids per-request image processing. Cleanup on delete prevents orphaned files. The security considerations are appropriate.

- **API design is RESTful and well-documented.** Every endpoint has clear request/response examples, validation rules, and error cases. The respondent-facing API correctly limits exposed data (no status, slug, or timestamps). The 409 Conflict response for duplicate answers is correct HTTP semantics.

- **TypeScript types mirror backend schemas.** The `lib/types.ts` interfaces match the Pydantic response schemas exactly, minimizing type mismatch bugs across the stack.

- **Respondent UX flow is well-thought-out.** The lock-in mechanic with visual feedback, inline follow-up input, progress bar, and phase-based state machine are all appropriate for forced-choice testing. The Fisher-Yates shuffle for option randomization is correctly implemented.

- **Tech stack choices are appropriate for the requirements.** FastAPI + SQLModel for a Python developer, Next.js + Tailwind for rapid frontend development, SQLite for zero-cost local-first operation, and Recharts for simple charting all align with the project's constraints. Context7 confirms all libraries are actively maintained and well-documented.

- **The integration test covers the full happy path.** Creating a test, adding questions/options, activating, responding, checking analytics, exporting CSV, and closing -- all in one test function -- provides good confidence that the core flow works.

- **The plan correctly dropped URL-based options from MVP.** The requirement mentioned "image upload OR URL" for options, but the plan simplified to upload-only, noting this in the design notes. This is the right call for MVP complexity management.

- **Phase ordering is logical.** Backend-first (testable via Swagger and pytest), then frontend scaffolding, then pages, then polish. Each phase produces working software.
