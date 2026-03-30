# Implementation Plan Feasibility Review

**Reviewer role:** Senior Engineer
**Plan reviewed:** `04-impl-plan.md`
**Requirement:** `requirement.md`
**Date:** 2026-03-31

---

## 1. Parallel Task Independence Analysis

### G2: Task 2 (Backend Scaffold) + Task 11 (Frontend Scaffold) -- PASS

These are truly independent. Backend creates `backend/` directory tree; frontend runs `create-next-app` in `frontend/`. No shared files, no shared state. Both only depend on Task 1 (git init + `.gitignore`).

**Verdict:** Safe to parallelize.

### G4: Task 4 (Pydantic Schemas) + Task 12 (Frontend Types + API) + Task 13 (Shared UI Components) -- PASS with caveat

- Task 4 depends on Task 3 (models). Task 12 depends on Task 11. Task 13 depends on Task 11. No cross-dependencies between them.
- **Caveat:** Task 12 (TypeScript types) should ideally be written *after* Task 4 (Pydantic schemas) to ensure field names match exactly. But since the plan specifies exact field names in both, a subagent can implement Task 12 from its description alone. If schemas change during Task 4 implementation, Task 12 would need updating.

**Verdict:** Safe to parallelize as written, since both are fully specified.

### G6: Task 6, 7, 8, 9 (Route files) -- FINDING (Major)

**Severity: Major**

Task 9 (Respondent Routes) lists a dependency on Task 6 (`imports _build_test_with_questions`). The dependency table at line 1242 confirms: "Dependencies: Task 5, Task 6". However, the parallelism table at line 78 places Task 9 in group G6 alongside Tasks 6, 7, and 8, claiming they "are independent of each other."

This is a contradiction. Task 9 imports a helper function from `app/routes/tests.py` (Task 6). If Task 9 runs before Task 6 completes, it will fail with an ImportError.

**Recommendation:** Move Task 9 out of G6 into a separate group that runs after Task 6 completes, or inline the `_build_test_with_questions` helper into `respond.py`.

### G6 internal: Tasks 6, 7, 8 -- PASS

Tasks 6, 7, and 8 all depend on Task 5 (Image Service) but not on each other. Each creates its own route file and adds its own router to `main.py`.

**However:** All three tasks modify `backend/main.py` to add router imports. If three subagents run concurrently and each appends lines to `main.py`, they will create merge conflicts or overwrite each other.

**Severity: Major**

**Recommendation:** Either (a) have a single agent handle all `main.py` modifications, (b) pre-create `main.py` with placeholder imports in Task 5, or (c) defer all `main.py` router additions to Task 20 (which already does this). Option (c) is already in the plan -- Task 20 writes the final consolidated `main.py`. So the individual `main.py` modifications in Tasks 6-9 are redundant and conflict-prone during parallel execution. Each task should only create its route file and skip the `main.py` modification.

### G9: Tasks 15, 16, 17, 18 (Frontend pages) -- FINDING (Major)

**Severity: Major**

Task 17 (Test Detail Page) lists dependencies: "Task 12, Task 13, Task 16". It imports `QuestionEditor` and `TestMetaForm` components created in Task 16. The plan places Task 17 in the same parallel group G9 as Task 16.

If Task 17 runs before Task 16 finishes, the imported components will not exist, causing build/compile failures.

**Recommendation:** Task 17 must run after Task 16. Either remove it from G9 and run it sequentially after 15/16/18 complete, or restructure so Task 17 does not import Task 16 components (unlikely given the design).

### G9 internal: Tasks 15, 16, 18 -- PASS

Tasks 15 (Dashboard), 16 (Test Builder), and 18 (Respondent Flow) are genuinely independent. They create different page files and different component directories with no cross-imports.

---

## 2. API Correctness per Current Docs

### FastAPI

#### SessionDep Pattern -- CORRECT
**Verified via Context7.** The plan uses `SessionDep = Annotated[Session, Depends(get_session)]` which matches the current FastAPI + SQLModel recommended pattern exactly. The official docs show this identical pattern.

#### Lifespan Events -- CORRECT
**Verified via Context7.** The plan uses `@asynccontextmanager async def lifespan(app: FastAPI)` and passes it to `FastAPI(lifespan=lifespan)`. This is the recommended modern approach. The deprecated `@app.on_event("startup")` is correctly avoided.

#### File + Form Multipart -- CORRECT
**Verified via Context7.** The plan correctly notes that `File()` and `Form()` parameters result in `multipart/form-data` and that you cannot also accept a JSON body in the same endpoint. The option routes use `async def` with `await file.read()` which is correct for async handlers.

#### check_same_thread=False -- CORRECT
The plan correctly sets `connect_args={"check_same_thread": False}` for SQLite with FastAPI. This is shown in the official SQLModel tutorial.

#### CORS Middleware Order -- MINOR CONCERN

**Severity: Minor**

The plan adds `SlowAPIMiddleware` before `CORSMiddleware`. FastAPI middleware executes in reverse order of addition (last added = first to execute). This means CORS headers will be processed first (added last), then SlowAPI. This is actually the correct order -- CORS needs to run before rate limiting so that preflight OPTIONS requests get proper CORS headers. No issue.

#### Rate Limiter Decorator Order -- FINDING (Minor)

**Severity: Minor**

The plan states at line 1283: "The `@limiter.limit()` decorator must come AFTER `@router.post()`." This is correct for slowapi -- the route decorator must be outermost. However, the code snippet at line 1271-1273 shows:

```python
@router.post("/{slug}/answers", status_code=201)
@limiter.limit(RATE_LIMIT_RESPONDENT)
def submit_answer(...):
```

This is the correct order (route decorator first/outermost, limiter second/innermost). No issue with the code itself, but the English description "must come AFTER" is ambiguous -- it means "after in reading order" (below), which is "inner" in decorator nesting. A subagent might misinterpret this. The code example is authoritative.

#### PRAGMA foreign_keys=ON Timing -- FINDING (Minor)

**Severity: Minor**

The plan executes `PRAGMA foreign_keys=ON` once in the lifespan handler via `engine.connect()`. The gotcha notes (line 211) acknowledge this only works because of a "single connection pool." However, SQLAlchemy's default pool for SQLite is `StaticPool` only when using in-memory databases. For file-based SQLite, it uses `QueuePool` by default, which can create multiple connections. A new connection from the pool would NOT have `foreign_keys=ON`.

**Recommendation:** Add a SQLAlchemy event listener to execute the pragma on every new connection:

```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

This is a well-known SQLAlchemy pattern and would make foreign key enforcement reliable regardless of connection pool behavior. The current approach may silently fail to enforce foreign keys on pooled connections.

### Next.js App Router

#### `useParams()` from `next/navigation` -- CORRECT
**Verified via Context7.** The plan correctly imports `useParams` from `next/navigation` (not `next/router`). In Next.js 15+, the `params` prop in Server Components became a Promise, but `useParams()` in Client Components still returns synchronously. Since all pages in the plan use `"use client"` + `useParams()`, this is correct.

#### `useParams()` Return Type -- FINDING (Minor)

**Severity: Minor**

The plan (line 219) states: "`useParams()` returns `Record<string, string | string[]>`." The Context7 docs show that `useParams` can be typed with a generic: `useParams<{ slug: string }>()`. The plan's usage `const testId = Number(params.testId)` works fine since `params.testId` will be a string. However, the plan should note that `useParams` can return `null` during initial prerendering (the Context7 docs explicitly show null-checking). If a component renders before params are available, `Number(null)` yields `0`, which would cause a wrong API call.

**Recommendation:** Add a null/undefined guard: `const params = useParams(); if (!params?.testId) return <Loading />;`

#### Route Groups with Parentheses -- CORRECT
**Verified via Context7.** The `(designer)` route group folder convention is correct. It creates layout nesting without affecting the URL path.

#### `'use client'` Directive -- CORRECT
The plan correctly places `"use client"` as the first line before imports. All pages using hooks (useState, useEffect, useParams) are marked as client components.

#### Inter Font Application -- FINDING (Minor)

**Severity: Minor**

The plan applies the Inter font to the `<body>` tag: `<body className={`${inter.className} bg-gray-50 ...`}>`. The Context7 docs show the recommended pattern is to apply it to `<html>`: `<html lang="en" className={inter.className}>`. Applying to `<body>` works but may cause a brief flash of unstyled text on fonts that apply inheritance differently. This is cosmetic only.

### Recharts

#### ResponsiveContainer -- CORRECT
**Verified via Context7.** The plan correctly notes that `ResponsiveContainer` requires a parent with defined dimensions and uses `height={300}`. The Context7 examples confirm `<ResponsiveContainer width="100%" height={300}>` as the standard pattern.

#### Cell Components for Individual Colors -- CORRECT
**Verified via Context7.** The Pie chart example from Context7 shows individual colors via the `fill` property on data items or via `Cell` components mapped over data with an index.

#### Tooltip Formatter -- FINDING (Minor)

**Severity: Minor**

The plan (line 237) states the Tooltip formatter callback signature is `(value, name, props)` where `props.payload` contains the full data item. The Context7 docs show the formatter signature as `(value, name) => [formattedValue, formattedName]`. The third argument `props` is available but not prominently documented. Using `props.payload.percentage` should work but is fragile -- a custom Tooltip component via the `content` prop (as shown in Context7 examples) would be more robust and explicit.

**Recommendation:** Consider using a custom Tooltip component instead of the `formatter` prop for accessing `percentage` from the data payload. This is shown in the Context7 Recharts docs and provides clearer, more maintainable code.

#### `'use client'` for Recharts -- CORRECT
The plan correctly notes Recharts requires client-side rendering. All chart components use `"use client"`.

---

## 3. Test Strategy Adequacy

### Backend Testing -- FINDING (Major)

**Severity: Major**

The entire backend has a single integration test file (`test_workflow.py`) that runs one monolithic test function testing the happy path. This is better than no tests, but has significant gaps:

1. **No unit tests for services.** `image_service.py` has complex logic (bounded reads, Image.verify, thumbnail generation, GIF handling) with zero dedicated tests. The integration test only uses URL-mode options, so image upload code paths are never tested.

2. **No edge case coverage.** The plan does not test:
   - Invalid image types (spoofed content-type)
   - Oversized image uploads (>10MB boundary)
   - Max 5 options enforcement
   - Invalid status transitions (e.g., active -> draft)
   - Empty/whitespace-only labels
   - Missing required followup_text
   - CSV injection sanitization
   - Concurrent duplicate submissions (race condition)

3. **No error path testing.** The integration test only verifies 403 for "cannot add questions to active test" and 409 for duplicate answers. Other error responses (400, 404) are not tested.

**Recommendation:** Add at minimum:
- A unit test for `image_service.py` covering upload, oversized rejection, invalid type, and thumbnail generation
- Error path assertions in the workflow test for 400/404 cases
- A test for the image upload flow (multipart/form-data with a real image file)

### Frontend Testing -- FINDING (Major)

**Severity: Major**

There are zero frontend tests. The plan relies entirely on:
- TypeScript compilation (`tsc --noEmit`)
- Manual visual verification

For an MVP this may be acceptable, but the plan should explicitly acknowledge this is a known gap. TypeScript compilation only catches type errors, not logic bugs (wrong API endpoint, incorrect state transitions, broken form submissions).

**Recommendation:** At minimum, add one smoke test using React Testing Library or Playwright that verifies the dashboard page renders without crashing when the API returns an empty list.

### End-to-End Test (Task 21) -- ADEQUATE with concern

The E2E smoke test is manual (20 verification steps). This is reasonable for an MVP but is not automatable or repeatable. The plan should note this as a one-time verification, not a regression test.

---

## 4. Hidden Dependencies Not in Dependency Graph

### Finding 4.1: Shared `main.py` Modification Conflicts

**Severity: Major** (already noted in Section 1)

Tasks 6, 7, 8, 9 all modify `backend/main.py` to add router imports. Task 20 then rewrites `main.py` entirely. The intermediate modifications are both redundant and conflict-prone for parallel execution.

### Finding 4.2: `create-next-app` Interactive Prompts

**Severity: Minor**

Task 11 runs `npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm`. Depending on the Next.js version, `create-next-app` may prompt additional interactive questions (e.g., "Would you like to use Turbopack?"). The plan mentions answering "No" to Turbopack, but a subagent cannot answer interactive prompts.

**Recommendation:** Add `--no-turbopack` (or `--turbopack=false` if supported) to the command flags, or pipe `echo "No"` into the command. Alternatively, use `npx create-next-app@14` to pin the version and avoid unexpected prompts.

### Finding 4.3: Node.js / npm Version Dependency

**Severity: Minor**

The plan specifies "Next.js 14+" but does not specify required Node.js version. Next.js 14 requires Node.js 18.17+. If the host machine has an older Node.js, `create-next-app` and `npm run dev` will fail.

**Recommendation:** Add a Node.js version check to Task 1 or Task 11.

### Finding 4.4: Python Version Dependency

**Severity: Minor**

The plan uses `int | None` union syntax (PEP 604) which requires Python 3.10+. The plan specifies "Python 3.11+" but does not verify this at setup time. A subagent should verify `python3 --version` in Task 2.

### Finding 4.5: Recharts Install Timing

**Severity: Minor**

Recharts is installed in Task 19 Step 1, but the plan's parallelism notes at line 2506 say Task 19 depends on "T12, T15-T18". This is correct -- Recharts is only used in Task 19 components. No hidden dependency.

### Finding 4.6: `app.mount("/media", ...)` Blocks Catch-All Routes

**Severity: Minor**

The plan mounts static files at `/media` early in `main.py`. In FastAPI, `app.mount()` creates a sub-application that takes priority over regular routes. If a route were ever added at `/media/...`, it would be shadowed. This is not a problem for this project since `/media` is only for static files, but worth noting.

### Finding 4.7: SQLModel Table Name Convention

**Severity: Minor**

The Option model (line 613) uses `foreign_key="screenquestion.id"`. SQLModel/SQLAlchemy auto-generates table names by lowercasing the class name. `ScreenQuestion` becomes `screenquestion` (no underscore). The foreign key references are consistent with this. This is correct but could confuse a subagent who might expect `screen_question` as the table name.

**Recommendation:** The task descriptions should explicitly state the auto-generated table names or set `__tablename__` explicitly.

---

## 5. File Path Correctness

### Backend Paths -- CORRECT

All backend paths follow the structure defined in `requirement.md`:
- `backend/app/models/`, `backend/app/schemas/`, `backend/app/routes/`, `backend/app/services/`
- `backend/main.py` (entry point)
- `backend/data/` and `backend/media/` (gitignored)
- `backend/tests/`

### Frontend Paths -- CORRECT with one note

All frontend paths follow the App Router conventions:
- `frontend/app/(designer)/` -- route group
- `frontend/app/(designer)/tests/new/page.tsx`
- `frontend/app/(designer)/tests/[testId]/page.tsx`
- `frontend/app/(designer)/tests/[testId]/analytics/page.tsx`
- `frontend/app/respond/[slug]/page.tsx`
- `frontend/components/` -- correctly outside `app/`
- `frontend/lib/` -- correctly outside `app/`

**Note:** The `--src-dir=false` flag in `create-next-app` means no `src/` wrapper, which matches the plan's paths. Correct.

---

## 6. Subagent Self-Sufficiency

### Can a subagent implement each task from just its description?

| Task | Self-Sufficient? | Issue |
|------|------------------|-------|
| 1 | Yes | Simple git init + gitignore |
| 2 | Yes | Full code provided inline |
| 3 | Yes | Full code provided inline |
| 4 | Yes | Full code provided inline |
| 5 | Yes | Full code provided inline |
| 6 | **Partially** | Says "code is fully specified at lines 1630-1833" referencing a different document (the "approved plan" which is `02-plan.md`). A subagent given only Task 6's description would NOT have the route file code. |
| 7 | **Partially** | Same issue -- references "approved plan at lines 1877-1993" |
| 8 | **Partially** | Same issue -- references "approved plan at lines 2023-2213" |
| 9 | **Partially** | Same issue -- references "approved plan at lines 2243-2326" |
| 10 | **Partially** | Same issue -- references "approved plan at lines 2358-2574" |
| 11 | Yes | Commands and code provided inline |
| 12 | **Partially** | References "approved plan at lines 638-710" and "lines 922-3049" for types and API client |
| 13 | Yes | Full code provided inline |
| 14 | **Partially** | conftest.py is inline, but test_workflow.py references "approved plan at lines 2649-2778" |
| 15 | **Partially** | References "approved plan at lines 3382-3466" |
| 16 | **Partially** | References "approved plan" for all component code |
| 17 | **Partially** | References "approved plan at lines 4021-4241" |
| 18 | **Partially** | References "approved plan" for component code |
| 19 | **Partially** | References "approved plan" for component code |
| 20 | Yes | Full code provided inline |
| 21 | Yes | Manual verification steps are clear |
| 22 | Yes | Simple verification commands |

**Severity: Critical**

**Finding:** 13 out of 22 tasks reference code from the "approved plan" (`02-plan.md`) by line number. The implementation plan (`04-impl-plan.md`) does NOT contain this code inline -- it only says "Implement exactly as written there." A subagent given only the task description from `04-impl-plan.md` would not be able to write the route handlers, API client, or frontend page code without access to `02-plan.md`.

**Recommendation:** Either:
1. Inline all referenced code into `04-impl-plan.md` so each task is fully self-contained, OR
2. Ensure the subagent execution system provides `02-plan.md` as context for every task that references it, OR
3. Add a note in the task dispatch instructions that subagents must read `02-plan.md` for the referenced line ranges.

Option 1 is strongly preferred -- each task should be fully self-contained for reliable subagent execution.

---

## Summary of Findings

| # | Severity | Finding | Section |
|---|----------|---------|---------|
| 1 | **Critical** | 13 tasks reference code from `02-plan.md` by line number but don't include it inline. Subagents cannot implement these tasks without access to that file. | 6 |
| 2 | **Major** | Task 9 depends on Task 6 (imports `_build_test_with_questions`) but is placed in the same parallel group G6. Will fail with ImportError if run concurrently. | 1 |
| 3 | **Major** | Task 17 depends on Task 16 (imports `QuestionEditor`, `TestMetaForm`) but both are in parallel group G9. Will fail if run concurrently. | 1 |
| 4 | **Major** | Tasks 6-9 all modify `main.py` concurrently. Will cause merge conflicts in parallel execution. Task 20 already rewrites `main.py` in full, making intermediate edits redundant. | 1, 4 |
| 5 | **Major** | Backend test coverage is inadequate: no unit tests for image service, no upload code path tested, no edge case or error path coverage. | 3 |
| 6 | **Major** | Zero frontend tests. Only TypeScript compilation is verified. | 3 |
| 7 | **Minor** | `PRAGMA foreign_keys=ON` executed once in lifespan, but SQLAlchemy uses QueuePool for file-based SQLite. New pooled connections won't have the pragma. Use an event listener instead. | 2 |
| 8 | **Minor** | `create-next-app` may prompt interactive questions a subagent cannot answer. Pin version or add `--no-turbopack` flag. | 4 |
| 9 | **Minor** | `useParams()` can return `null` during prerendering. Plan should add null guards. | 2 |
| 10 | **Minor** | No Node.js or Python version verification in setup tasks. | 4 |
| 11 | **Minor** | Inter font applied to `<body>` instead of `<html>` (cosmetic). | 2 |
| 12 | **Minor** | Rate limiter decorator order description is ambiguous (English vs. code are correct but the wording could mislead). | 2 |
| 13 | **Minor** | SQLModel auto-generated table name `screenquestion` (no underscore) could confuse subagents expecting `screen_question`. | 4 |
| 14 | **Minor** | Consider using custom Tooltip component instead of `formatter` prop for Recharts percentage display. | 2 |

### Blocking Issues (must fix before execution)

1. **Critical #1:** Inline all referenced code from `02-plan.md` into the task descriptions in `04-impl-plan.md`, or ensure subagents receive both files.
2. **Major #2:** Fix parallelism: Move Task 9 to run after Task 6.
3. **Major #3:** Fix parallelism: Move Task 17 to run after Task 16.
4. **Major #4:** Remove `main.py` modifications from Tasks 6-9 (Task 20 handles the final version).

### Recommended Improvements (non-blocking)

5. **Major #5-6:** Add image upload unit tests and at least one frontend smoke test.
6. **Minor #7:** Add SQLAlchemy event listener for `PRAGMA foreign_keys=ON`.
7. **Minor #8-10:** Pin `create-next-app` version, add version checks, add `useParams` null guards.
