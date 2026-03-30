# Phase 1: Brainstorm -- DesignPoll A/B Testing App

## 1. User Intent and Requirements Analysis

### What the designer actually wants
The core job-to-be-done is: "I have 2-5 design variants for a screen. I want to put them in front of people, force a decision (no waffling), optionally capture why, and see which wins." This is a **forced-choice voting tool with structured feedback**, not a full usability testing platform.

### Key user characteristics (from memory)
- The user is a Python expert but a frontend novice. This means:
  - Backend code can be idiomatic and well-structured; the user will maintain it.
  - Frontend code should be simple, conventional Next.js patterns. Avoid advanced React patterns (custom hooks, context providers, reducers) when simpler state management works.
  - Tailwind CSS is the right call -- utility classes, no CSS-in-JS complexity.

### Requirements decomposition

| Requirement | Priority | Complexity | Notes |
|---|---|---|---|
| Test builder (create test with screen questions + options) | Must-have | Medium | Multi-step form, image upload |
| Respondent flow (take test, lock-in choice, follow-up) | Must-have | Medium | Core UX, must be polished |
| Analytics dashboard (charts, vote counts, reasons) | Must-have | Medium | Recharts bar/pie, CSV export |
| Shareable link (unique slug) | Nice-to-have | Low | UUID or nanoid slug |
| Authentication | Nice-to-have | Low | Structure for later, no implementation now |

### Implicit requirements not stated but important
- **Test status lifecycle**: A test should probably have states (draft, active, closed). Designers need to stop accepting responses at some point.
- **Test editing after creation**: Can a designer edit a test that already has responses? Safest: allow editing only while draft, lock once active.
- **Deletion**: Designer should be able to delete tests (and cascade to responses).
- **Option ordering**: The order options appear matters for A/B testing. Consider randomization to avoid position bias.

---

## 2. Edge Cases and Boundary Conditions

### Zero responses
- Analytics dashboard must handle the empty state gracefully: "No responses yet" with an invitation to share the test link.
- Charts should not render with zero data (Recharts will render empty axes). Show a placeholder instead.
- CSV export with zero responses: either disable the button or export headers-only.

### Very long follow-up text
- Respondents could paste essays into the follow-up field. Decisions:
  - **Enforce a character limit** (e.g., 500 chars) with visible counter. This keeps the analytics view manageable.
  - Backend validation via Pydantic `max_length` on the field.
  - Analytics view should truncate long reasons with an expand/collapse toggle.

### Large images
- Designers upload high-resolution mockups (5MB+ PNGs from Figma).
  - **Backend**: Accept up to 10MB per image. Reject larger with a clear error. FastAPI's `UploadFile` streams to a temp file, so memory is not an issue.
  - **Frontend**: Display images via `<img>` with `object-fit: contain` to handle varying aspect ratios. Consider generating thumbnails on upload (PIL/Pillow resize to max 1200px width) to avoid sending 5MB images to every respondent.
  - **Storage**: Local filesystem `backend/media/` with UUID-based filenames to avoid collisions and path traversal. Original filename stored in DB for reference.

### Many screen questions
- A test with 20+ screen questions is unlikely but possible.
  - **Backend**: No hard limit, but paginate the analytics view per-question.
  - **Respondent UX**: Progress indicator ("Question 3 of 20") becomes critical. Consider a progress bar.
  - **Test builder**: Scrollable list of questions with add/remove/reorder controls. Reordering is a nice-to-have; initial version can use fixed order (order of creation).

### Concurrent respondents
- SQLite handles concurrent reads well. Concurrent writes are serialized but fast for this workload (single INSERT per question response).
- `check_same_thread=False` is required (confirmed in FastAPI docs).
- WAL mode (`PRAGMA journal_mode=WAL`) should be enabled for better concurrent read performance.

### Image URL option
- The requirement mentions "image upload OR URL" for options.
- URLs pose challenges: external images may break, CORS issues with iframes, security risks.
- **Recommendation**: For MVP, support image upload only. If URL support is desired, render as a simple `<img>` tag (not iframe), and store the URL in the same field. Add a `source_type` enum: `upload` | `url`.

### Partial responses
- A respondent answers 3 of 5 questions then closes the tab.
- Options:
  - **(A) Save per-question**: Each question answer is an independent row. Partial data is captured. Analytics shows per-question response counts.
  - **(B) Save only on completion**: Simpler, but loses data.
  - **Recommendation**: Option A. Each answer is saved immediately after "Next" is clicked. A `session_id` groups answers from the same respondent. This also means if the tab crashes, progress through prior questions is not lost.

### Respondent identification
- No accounts needed. Generate a random `session_id` (UUID) client-side when the respondent starts the test. Attach it to every response from that session.
- This enables grouping responses per respondent in analytics without any PII.
- Prevent duplicate submissions: check if `(session_id, screen_question_id)` already exists before inserting.

---

## 3. Technical Approach Options and Tradeoffs

### 3.1 ORM: SQLModel vs raw SQLAlchemy vs raw SQL

| Option | Pros | Cons |
|---|---|---|
| **SQLModel** | Combines Pydantic + SQLAlchemy, less boilerplate, recommended by FastAPI docs | Younger library, fewer Stack Overflow answers |
| SQLAlchemy + separate Pydantic | Battle-tested, more control | More boilerplate (duplicate model definitions) |
| Raw SQL (aiosqlite) | Maximum performance, no ORM overhead | Tedious, error-prone, no validation |

**Recommendation: SQLModel.** It is the FastAPI-recommended approach (confirmed by Context7 docs). The dual Pydantic/SQLAlchemy nature eliminates schema duplication. For this project's complexity, SQLModel is ideal.

### 3.2 Image handling strategy

| Option | Pros | Cons |
|---|---|---|
| **Store on filesystem, serve via FastAPI StaticFiles** | Simple, zero dependencies | Not CDN-ready (fine for local) |
| Store as BLOBs in SQLite | Single-file portability | Bloats DB, slow for large images |
| Store on filesystem, serve via Next.js | Keeps backend simpler | Complicates Next.js config |

**Recommendation: Filesystem + FastAPI StaticFiles mount.** Store files in `backend/media/{test_id}/{uuid}.{ext}`. Serve via `app.mount("/media", StaticFiles(directory="media"))`. The Context7 docs confirm StaticFiles supports directory serving with simple configuration.

### 3.3 Frontend state management

| Option | Pros | Cons |
|---|---|---|
| **React useState + fetch** | Simplest, no dependencies | Boilerplate for loading/error states |
| SWR or TanStack Query | Caching, revalidation, loading states built-in | Extra dependency, learning curve |
| Zustand/Redux | Global state management | Overkill for this app |

**Recommendation: Plain `useState` + `fetch` for MVP.** The user is a frontend novice. Every added library increases cognitive load. The app has simple data flows: load data, display it, submit forms. If fetching becomes repetitive, extract a small `useApi` custom hook later.

### 3.4 Image thumbnails

| Option | Pros | Cons |
|---|---|---|
| **Generate on upload (Pillow)** | Respondents get fast page loads | Extra backend dependency, processing time |
| Serve originals, let browser resize | Zero complexity | Slow page loads for large images |
| Next.js Image component | Built-in optimization | Requires Next.js to proxy backend images, complex config |

**Recommendation: Generate thumbnails on upload using Pillow.** Save both the original and a resized version (max 800px width). Serve thumbnails to respondents, originals in a "view full size" modal. Pillow is a standard Python library the user will be comfortable with.

### 3.5 Test slug generation

| Option | Pros | Cons |
|---|---|---|
| **nanoid (Python: nanoid or secrets)** | Short, URL-friendly, collision-resistant | Not human-readable |
| UUID4 | Standard, zero collision risk | Long and ugly in URLs |
| Slugified test name | Human-readable | Collision-prone, changes if name changes |

**Recommendation: Python `secrets.token_urlsafe(8)` for a 11-char slug.** No extra dependency needed. Store in a unique column. Generate on test creation.

### 3.6 CSV export

| Option | Pros | Cons |
|---|---|---|
| **Backend generates CSV, frontend downloads** | Simple, correct encoding guaranteed | Extra backend endpoint |
| Frontend generates CSV from JSON | No extra endpoint | Edge cases with encoding, large datasets |

**Recommendation: Backend endpoint** that returns `Content-Type: text/csv` with `Content-Disposition: attachment`. Use Python's `csv` module (stdlib). This is the user's strength (Python).

---

## 4. Data Model Design

### Entity-Relationship Overview

```
Designer (future)
  |
  | 1:N
  v
Test
  |-- id (PK, int, auto)
  |-- slug (unique, str, indexed)
  |-- name (str)
  |-- description (str, nullable)
  |-- status (enum: draft | active | closed)
  |-- designer_id (FK, nullable -- for future auth)
  |-- created_at (datetime)
  |-- updated_at (datetime)
  |
  | 1:N
  v
ScreenQuestion
  |-- id (PK, int, auto)
  |-- test_id (FK -> Test)
  |-- order (int) -- for sequencing
  |-- title (str) -- "Which homepage do you prefer?"
  |-- followup_prompt (str, default "Why did you choose this?")
  |-- followup_required (bool, default false)
  |-- created_at (datetime)
  |
  | 1:N
  v
Option
  |-- id (PK, int, auto)
  |-- screen_question_id (FK -> ScreenQuestion)
  |-- label (str) -- "Option A"
  |-- image_path (str, nullable) -- relative path in media/
  |-- image_url (str, nullable) -- external URL
  |-- source_type (enum: upload | url)
  |-- order (int) -- display order
  |-- created_at (datetime)
  |
  | (selected by respondents)
  v
Response
  |-- id (PK, int, auto)
  |-- screen_question_id (FK -> ScreenQuestion)
  |-- option_id (FK -> Option)
  |-- session_id (str, UUID) -- groups one respondent's answers
  |-- followup_text (str, nullable, max 500 chars)
  |-- created_at (datetime)
  |
  | UNIQUE constraint: (session_id, screen_question_id)
```

### Design decisions in the data model

1. **`session_id` instead of `respondent_id` FK**: No respondent table needed. A UUID generated client-side groups answers. This keeps the system stateless for respondents.

2. **`order` columns on ScreenQuestion and Option**: Explicit ordering avoids relying on insertion order. Enables future drag-and-drop reordering.

3. **`status` on Test**: Prevents respondents from submitting to closed/draft tests. The backend rejects responses to non-active tests.

4. **Separate `image_path` and `image_url`**: Cleaner than overloading a single field. `source_type` enum makes queries and validation explicit.

5. **`followup_prompt` and `followup_required` on ScreenQuestion**: Per-question configuration as specified. Default prompt avoids forcing the designer to type it every time.

6. **No `respondent` table**: Matches requirement ("no account needed"). If analytics later needs demographics, add a lightweight table keyed by `session_id`.

7. **Cascading deletes**: Deleting a Test should cascade to ScreenQuestions, Options, and Responses. SQLModel/SQLAlchemy `cascade="all, delete-orphan"` handles this.

### Indexes to create
- `Test.slug` -- unique index for shareable links
- `Response.session_id` -- for grouping responses per respondent
- `Response.screen_question_id` -- for aggregating votes per question
- `ScreenQuestion.test_id` -- for loading all questions of a test
- Composite unique: `(Response.session_id, Response.screen_question_id)` -- prevent duplicate answers

---

## 5. Frontend Component Architecture

### Page structure (Next.js App Router)

```
app/
  layout.tsx              -- Root layout (html, body, Tailwind, global nav)
  page.tsx                -- Home/landing: list of tests (designer view)

  tests/
    new/
      page.tsx            -- Test builder: create new test
    [testId]/
      page.tsx            -- Test detail: view/edit test config
      analytics/
        page.tsx          -- Analytics dashboard for this test

  respond/
    [slug]/
      page.tsx            -- Respondent flow: take the test
      thank-you/
        page.tsx          -- Completion screen

components/
  layout/
    Navbar.tsx            -- Top nav with logo, navigation
    Container.tsx         -- Max-width centered container

  test-builder/
    TestForm.tsx          -- Test name + description form
    ScreenQuestionEditor.tsx  -- Edit a single screen question
    OptionEditor.tsx      -- Edit a single option (upload/URL)
    ImageUploader.tsx     -- Drag-and-drop or click-to-upload

  respondent/
    IntroScreen.tsx       -- Test intro with name + description + Start button
    QuestionView.tsx      -- Side-by-side options for one question
    OptionCard.tsx        -- Single option card (image + label + select)
    FollowUpInput.tsx     -- Text input for reasoning
    ProgressBar.tsx       -- "Question 2 of 5" indicator
    ThankYouScreen.tsx    -- Completion message

  analytics/
    SummaryBar.tsx        -- Total responses, completion rate
    VoteChart.tsx         -- Bar/pie chart for one question
    ReasonsPanel.tsx      -- Grouped follow-up reasons
    ExportButton.tsx      -- CSV download trigger

  shared/
    Button.tsx            -- Consistent button styles
    Card.tsx              -- Reusable card wrapper
    EmptyState.tsx        -- "No data yet" placeholder
    LoadingSpinner.tsx    -- Loading indicator
    ErrorMessage.tsx      -- User-friendly error display

lib/
  api.ts                  -- API client: fetch wrappers for all endpoints
  types.ts                -- TypeScript interfaces matching backend schemas
  constants.ts            -- API base URL, etc.
```

### Key component design decisions

1. **Server Components vs Client Components**:
   - Pages that just fetch and display data (test list, analytics) can start as Server Components, fetching data in the component body.
   - Interactive components (test builder forms, respondent flow, charts) must be Client Components (`'use client'`).
   - The respondent flow is entirely client-side: state machine managing question progression, selections, and follow-up text.

2. **Respondent flow state machine**: The respondent page manages a local state:
   ```
   { currentQuestionIndex, selections: Map<questionId, { optionId, followupText }>, isLocked }
   ```
   On each "Next", POST the response to the backend, then increment `currentQuestionIndex`. This saves per-question (addressing the partial response edge case).

3. **Image display**: Use plain `<img>` tags with Tailwind classes for responsive sizing. Avoid Next.js `<Image>` component to keep things simple and because images are served from the FastAPI backend (different origin), which complicates Next.js image optimization config.

4. **Charts**: Recharts `ResponsiveContainer` wrapping `BarChart` or `PieChart`. Context7 docs confirm this pattern works well. Charts are Client Components by nature. Provide a toggle between bar and pie view per question.

---

## 6. API Endpoint Design

### Tests CRUD

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/tests` | Create a new test | `{ name, description? }` | `Test` with generated slug |
| `GET` | `/api/v1/tests` | List all tests | -- | `Test[]` |
| `GET` | `/api/v1/tests/{test_id}` | Get test details | -- | `Test` with nested questions + options |
| `PATCH` | `/api/v1/tests/{test_id}` | Update test metadata | `{ name?, description?, status? }` | `Test` |
| `DELETE` | `/api/v1/tests/{test_id}` | Delete test + cascade | -- | `204 No Content` |

### Screen Questions

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/tests/{test_id}/questions` | Add screen question | `{ title, followup_prompt?, followup_required?, order? }` | `ScreenQuestion` |
| `PATCH` | `/api/v1/questions/{question_id}` | Update question | `{ title?, followup_prompt?, followup_required?, order? }` | `ScreenQuestion` |
| `DELETE` | `/api/v1/questions/{question_id}` | Delete question + options | -- | `204` |

### Options

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/questions/{question_id}/options` | Add option (multipart) | `label, order, file?` (multipart form) | `Option` |
| `PATCH` | `/api/v1/options/{option_id}` | Update option | `{ label?, order? }` | `Option` |
| `DELETE` | `/api/v1/options/{option_id}` | Delete option | -- | `204` |

### Respondent-Facing

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/v1/respond/{slug}` | Get test for respondent | -- | `Test` (only active tests, with questions + options, no analytics) |
| `POST` | `/api/v1/respond/{slug}/answers` | Submit one answer | `{ session_id, question_id, option_id, followup_text? }` | `201 Created` |

### Analytics

| Method | Endpoint | Description | Request Body | Response |
|---|---|---|---|---|
| `GET` | `/api/v1/tests/{test_id}/analytics` | Get analytics for test | -- | `{ total_responses, completion_rate, per_question: [...] }` |
| `GET` | `/api/v1/tests/{test_id}/export` | Download CSV | -- | `text/csv` file |

### Design decisions in the API

1. **Flat routes for update/delete**: Questions and options are updated/deleted by their own ID, not nested under tests. Simplifies routing and avoids deep nesting (`/tests/1/questions/2/options/3`).

2. **Separate respondent endpoints**: `/api/v1/respond/{slug}` is distinct from `/api/v1/tests/{test_id}`. The respondent route uses the slug (shareable URL), returns only what respondents need (no analytics data), and only works for active tests.

3. **Per-answer submission**: The respondent submits one answer at a time (not a batch at the end). This handles partial responses and reduces data loss risk.

4. **Analytics computed server-side**: The `/analytics` endpoint returns pre-computed vote counts, percentages, and grouped reasons. This keeps the frontend simple (just render what the backend gives).

5. **Multipart for option creation**: Image upload requires multipart form data. The `label` and `order` fields are sent as form fields alongside the file.

6. **CORS configuration**: Allow origin `http://localhost:3000` (Next.js dev server). Methods: GET, POST, PATCH, DELETE. Headers: Content-Type. Credentials: false (no auth cookies for MVP).

---

## 7. Backend Architecture

### Module structure

```
backend/
  main.py                     -- FastAPI app, CORS, mount static files, include routers
  app/
    config.py                 -- Settings (DB path, media dir, CORS origins)
    database.py               -- Engine, session, create_db_and_tables()
    models/
      __init__.py
      test.py                 -- Test SQLModel
      screen_question.py      -- ScreenQuestion SQLModel
      option.py               -- Option SQLModel
      response.py             -- Response SQLModel
    schemas/
      __init__.py
      test.py                 -- TestCreate, TestUpdate, TestPublic
      screen_question.py      -- QuestionCreate, QuestionUpdate, QuestionPublic
      option.py               -- OptionCreate, OptionPublic
      response.py             -- AnswerCreate, AnalyticsResponse
    routes/
      __init__.py
      tests.py                -- Test CRUD endpoints
      questions.py            -- Question CRUD endpoints
      options.py              -- Option CRUD endpoints
      respond.py              -- Respondent-facing endpoints
      analytics.py            -- Analytics + export endpoints
    services/
      __init__.py
      image_service.py        -- Save, resize, validate images
      analytics_service.py    -- Compute vote counts, percentages, grouped reasons
      export_service.py       -- Generate CSV
  data/                       -- SQLite DB file lives here
  media/                      -- Uploaded images
```

### Key backend patterns

1. **Dependency injection for DB sessions**: Use FastAPI's `Depends(get_session)` with `Annotated` type alias as shown in Context7 docs.

2. **Lifespan event for DB init**: Use FastAPI's `lifespan` context manager (modern approach) instead of deprecated `@app.on_event("startup")`.

3. **Image service**: Validate file type (JPEG, PNG, WebP, GIF only), generate UUID filename, save to `media/{test_id}/`, optionally resize with Pillow.

4. **Pydantic schemas separate from SQLModel models**: Even though SQLModel can serve as both, use separate "Public" schemas for API responses. This controls what gets serialized (e.g., exclude `image_path` internal details, return a full URL instead).

---

## 8. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| **SQLite write contention under load** | Slow responses if many respondents submit simultaneously | Low (local app) | Enable WAL mode; writes are fast (single INSERT) |
| **Large image uploads slow down the app** | Poor UX for designers uploading many mockups | Medium | File size limit (10MB), thumbnail generation, progress indicator on upload |
| **Frontend complexity exceeds user's comfort** | User struggles to maintain the code | Medium | Keep components simple, avoid advanced patterns, comment liberally |
| **CORS misconfiguration** | Frontend cannot talk to backend | High (common gotcha) | Set up CORS in `main.py` from day one, test immediately |
| **Image path traversal attack** | Security vulnerability | Low (local app) | UUID filenames, validate file extension, never use user-supplied paths |
| **Test with no questions or questions with < 2 options** | Broken respondent flow | Medium | Backend validation: reject test activation if any question has < 2 options |
| **Browser back button during respondent flow** | Confusing state, potential re-submission | Medium | Use `replaceState` to prevent back navigation during test, or handle gracefully with duplicate detection |
| **Pillow not installed** | Thumbnail generation fails | Low | Make it a required dependency in `requirements.txt`; fail gracefully if missing |

---

## 9. Open Questions

### Truly ambiguous items requiring user input

1. **Option randomization**: Should option display order be randomized per respondent to reduce position bias? This is a best practice in A/B testing but adds complexity. Recommendation: default to randomized, with a per-question toggle for the designer to disable it.

2. **Can designers edit active tests?**: If a test has responses, should the designer be allowed to change question text, add/remove options, etc.? Recommendation: once a test is active, only allow changing test name/description and closing it. Questions and options are locked.

3. **Multiple responses from the same session**: The unique constraint `(session_id, screen_question_id)` prevents a respondent from answering the same question twice. But should we allow a respondent to retake the entire test (new session_id)? The current design allows this since a new page load generates a new session_id. This is probably fine -- the designer wants volume.

4. **Image aspect ratio handling**: Designers may upload images with wildly different aspect ratios (portrait phone mockups vs landscape desktop mockups). Should we enforce uniform display? Recommendation: display all options at the same height with `object-fit: contain`, letting width vary. This keeps comparisons fair.

### Items with clear answers (not truly ambiguous)

- **Tech stack**: Confirmed as Next.js + FastAPI + SQLite + Recharts. No ambiguity.
- **Authentication**: Not in MVP. Structure code with `designer_id` FK defaulting to 1.
- **Deployment**: Local only. No cloud config needed.
- **Database migrations**: For MVP, use `SQLModel.metadata.create_all()`. No Alembic. If schema changes are needed later, add Alembic.

---

## 10. Implementation Priority Order

For a clean build sequence where each layer builds on the previous:

1. **Backend foundation**: Database models, engine setup, basic CRUD for tests/questions/options
2. **Image upload**: Image service, option creation with file upload, static file serving
3. **Respondent API**: Slug-based test retrieval, answer submission with validation
4. **Analytics API**: Vote aggregation queries, CSV export
5. **Frontend foundation**: Next.js project, Tailwind config, layout, API client
6. **Test builder UI**: Forms for creating tests, adding questions, uploading option images
7. **Respondent UI**: Test-taking flow with lock-in, follow-up, progress bar
8. **Analytics UI**: Dashboard with Recharts, reasons panel, export button
9. **Polish**: Error handling, empty states, loading states, mobile responsiveness
10. **Nice-to-haves**: Shareable slug display, test status management, option randomization

---

## 11. Technology-Specific Notes from Documentation

### FastAPI (from Context7)
- Use `SQLModel` with `Field(primary_key=True)` for models, `create_engine` with `check_same_thread=False` for SQLite.
- Use the `HeroBase` / `Hero` / `HeroPublic` / `HeroCreate` pattern for schema separation.
- Use `Annotated[Session, Depends(get_session)]` as `SessionDep` type alias for clean dependency injection.
- Mount static files with `app.mount("/media", StaticFiles(directory="media"), name="media")`.
- File uploads use `UploadFile` parameter type with access to `.filename`, `.content_type`, and async `.read()`.

### Next.js (from Context7)
- App Router: `app/layout.tsx` for root layout, `app/page.tsx` for pages.
- Dynamic routes: `app/tests/[testId]/page.tsx` with `params` as a Promise.
- Client Components require `'use client'` directive at file top.
- Server Components can fetch data directly in the component body.
- For external API data, use `fetch` with `cache: 'no-store'` for dynamic data.

### Recharts (from Context7)
- Always wrap charts in `<ResponsiveContainer width="100%" height={300}>`.
- `PieChart` with `<Pie data={data} dataKey="value" nameKey="name" label />` for vote distribution.
- `BarChart` with custom labels via `label` prop on `<Bar>`.
- Use `<Tooltip />` and `<Legend />` for interactivity.
- `<Cell fill={color} />` inside `<Pie>` for per-slice colors.

---

## 12. Summary of Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| ORM | SQLModel | FastAPI-recommended, dual Pydantic/SQLAlchemy |
| Image storage | Filesystem + StaticFiles | Simple, performant for local use |
| Frontend state | useState + fetch | Minimal complexity for frontend-novice user |
| Thumbnails | Pillow on upload | Fast respondent page loads |
| Slug generation | `secrets.token_urlsafe(8)` | No extra dependency, short URLs |
| CSV export | Backend-generated | Python strength, correct encoding |
| Response saving | Per-question (immediate) | Handles partial responses |
| Respondent identity | Client-side UUID session | No accounts needed, groups responses |
| Option randomization | Randomized by default (pending user input) | Reduces position bias |
| Test lifecycle | draft -> active -> closed | Prevents editing with existing responses |
