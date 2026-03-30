# DesignPoll A/B Testing App -- Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first web application that lets UI/UX designers create forced-choice A/B design tests, collect locked-in responses with optional follow-up reasoning, and view results through an analytics dashboard.

**Architecture:** Next.js frontend (TypeScript, Tailwind CSS, App Router) communicates via REST API with a FastAPI backend (Python, SQLModel ORM). SQLite database stores all data. Images are uploaded to the backend filesystem and served via FastAPI StaticFiles. Recharts renders analytics visualizations.

**Tech Stack:** Next.js 14+ (App Router, TypeScript, Tailwind CSS) | FastAPI (Python 3.11+, SQLModel, Pydantic v2) | SQLite (WAL mode) | Recharts | Pillow (image processing)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Model](#2-data-model)
3. [API Endpoint Design](#3-api-endpoint-design)
4. [Frontend Page/Component Architecture](#4-frontend-pagecomponent-architecture)
5. [Tech Stack Decisions](#5-tech-stack-decisions)
6. [Test Lifecycle Rules](#6-test-lifecycle-rules)
7. [Image Handling Strategy](#7-image-handling-strategy)
8. [File Structure](#8-file-structure)
9. [Implementation Tasks](#9-implementation-tasks)

---

## 1. Architecture Overview

```
+-------------------+         HTTP (REST)        +-------------------+
|                   |  <---------------------->  |                   |
|   Next.js App     |    localhost:3000           |   FastAPI App     |
|   (Frontend)      |    ----requests--->         |   (Backend)       |
|                   |    <---JSON/CSV----         |                   |
|  - App Router     |                            |  - SQLModel ORM   |
|  - Tailwind CSS   |                            |  - Pydantic v2    |
|  - Recharts       |                            |  - Pillow         |
|  - TypeScript     |                            |  - Python 3.11+   |
+-------------------+                            +-------------------+
                                                        |
                                                        | SQLite (WAL)
                                                        v
                                                 +-------------+
                                                 |  data/       |
                                                 |  app.db      |
                                                 +-------------+
                                                        |
                                                 +-------------+
                                                 |  media/      |
                                                 |  {test_id}/  |
                                                 |  images...   |
                                                 +-------------+
```

### How They Connect

- **Frontend to Backend:** The Next.js app makes `fetch()` calls to `http://localhost:8000/api/v1/...`. All pages that need data either fetch in Server Components (for read-only pages like test list, analytics) or use client-side `fetch` in Client Components (for interactive flows like the test builder and respondent flow).
- **CORS:** FastAPI middleware allows origin `http://localhost:3000` with methods GET, POST, PATCH, DELETE.
- **Image Serving:** FastAPI mounts `media/` as a static directory at `/media`. The frontend renders images as `<img src="http://localhost:8000/media/{test_id}/{filename}" />`.
- **Database:** Single SQLite file at `backend/data/app.db`. WAL mode enabled for concurrent read performance. `check_same_thread=False` for FastAPI's threaded request handling.

---

## 2. Data Model

### Entity-Relationship Diagram

```
Test (1) -----> (N) ScreenQuestion (1) -----> (N) Option
                        |                         |
                        |                         |
                        +-------> (N) Response <---+
                                    |
                              session_id (UUID)
                              groups one respondent
```

### Table: `test`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | |
| `slug` | String(16) | UNIQUE, NOT NULL, indexed | Generated via `secrets.token_urlsafe(8)` |
| `name` | String(200) | NOT NULL | Test title |
| `description` | String(2000) | nullable | Intro text shown to respondents |
| `status` | String(10) | NOT NULL, default `"draft"` | Enum: `draft`, `active`, `closed` |
| `created_at` | DateTime | NOT NULL, default `utcnow` | |
| `updated_at` | DateTime | NOT NULL, default `utcnow`, on-update `utcnow` | |

### Table: `screenquestion`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | |
| `test_id` | Integer | FK -> `test.id`, NOT NULL, ON DELETE CASCADE | |
| `order` | Integer | NOT NULL, default 0 | Display sequence |
| `title` | String(500) | NOT NULL | E.g., "Which homepage do you prefer?" |
| `followup_prompt` | String(500) | NOT NULL, default `"Why did you choose this?"` | |
| `followup_required` | Boolean | NOT NULL, default `False` | |
| `randomize_options` | Boolean | NOT NULL, default `True` | Per-question toggle; default randomized |
| `created_at` | DateTime | NOT NULL, default `utcnow` | |

Index: `(test_id)` for loading all questions of a test.

### Table: `option`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | |
| `screen_question_id` | Integer | FK -> `screenquestion.id`, NOT NULL, ON DELETE CASCADE | |
| `label` | String(200) | NOT NULL | E.g., "Option A" |
| `image_filename` | String(255) | nullable | UUID-based filename stored on disk |
| `original_filename` | String(255) | nullable | User's original filename for reference |
| `order` | Integer | NOT NULL, default 0 | Display order (when randomization is off) |
| `created_at` | DateTime | NOT NULL, default `utcnow` | |

Index: `(screen_question_id)` for loading all options of a question.

### Table: `response`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, auto-increment | |
| `screen_question_id` | Integer | FK -> `screenquestion.id`, NOT NULL, ON DELETE CASCADE | |
| `option_id` | Integer | FK -> `option.id`, NOT NULL, ON DELETE CASCADE | |
| `session_id` | String(36) | NOT NULL, indexed | UUID generated client-side |
| `followup_text` | String(500) | nullable | Max 500 chars |
| `created_at` | DateTime | NOT NULL, default `utcnow` | |

Unique constraint: `(session_id, screen_question_id)` -- one answer per question per session.
Index: `(screen_question_id)` for vote aggregation.
Index: `(session_id)` for grouping by respondent.

### Relationships and Cascade Rules

- Deleting a `Test` cascades to all its `ScreenQuestion` rows.
- Deleting a `ScreenQuestion` cascades to all its `Option` and `Response` rows.
- Deleting an `Option` cascades to all `Response` rows referencing it.
- SQLModel/SQLAlchemy `cascade="all, delete-orphan"` on the parent side of each relationship.

### Design Notes

- **No `image_url` field for MVP.** Upload-only keeps things simple and avoids broken external links. Can be added later.
- **No `source_type` enum.** With upload-only, not needed.
- **`randomize_options` on ScreenQuestion.** Default `True` per the decision log. When true, the frontend shuffles option order per page load.
- **`session_id` is a plain string**, not an FK. No respondent table needed.

---

## 3. API Endpoint Design

All endpoints prefixed with `/api/v1`. Request and response bodies are JSON unless noted.

### 3.1 Tests CRUD

#### `POST /api/v1/tests` -- Create a new test

Request:
```json
{
  "name": "Homepage A/B Test",
  "description": "Which homepage layout do users prefer?"
}
```

Response (201):
```json
{
  "id": 1,
  "slug": "aB3x_kM2pQ4",
  "name": "Homepage A/B Test",
  "description": "Which homepage layout do users prefer?",
  "status": "draft",
  "created_at": "2026-03-31T12:00:00Z",
  "updated_at": "2026-03-31T12:00:00Z"
}
```

Validation: `name` required, max 200 chars. `description` optional, max 2000 chars.

#### `GET /api/v1/tests` -- List all tests

Response (200):
```json
[
  {
    "id": 1,
    "slug": "aB3x_kM2pQ4",
    "name": "Homepage A/B Test",
    "description": "Which homepage layout do users prefer?",
    "status": "draft",
    "created_at": "2026-03-31T12:00:00Z",
    "updated_at": "2026-03-31T12:00:00Z",
    "question_count": 3,
    "response_count": 42
  }
]
```

Notes: Includes `question_count` and `response_count` as computed fields for the list view.

#### `GET /api/v1/tests/{test_id}` -- Get test with all questions and options

Response (200):
```json
{
  "id": 1,
  "slug": "aB3x_kM2pQ4",
  "name": "Homepage A/B Test",
  "description": "Which homepage layout do users prefer?",
  "status": "draft",
  "created_at": "2026-03-31T12:00:00Z",
  "updated_at": "2026-03-31T12:00:00Z",
  "questions": [
    {
      "id": 1,
      "order": 0,
      "title": "Which homepage layout?",
      "followup_prompt": "Why did you choose this?",
      "followup_required": false,
      "randomize_options": true,
      "options": [
        {
          "id": 1,
          "label": "Option A",
          "image_url": "/media/1/abc123.png",
          "order": 0
        },
        {
          "id": 2,
          "label": "Option B",
          "image_url": "/media/1/def456.png",
          "order": 1
        }
      ]
    }
  ]
}
```

Notes: `image_url` in the response is a computed URL path (not the raw filename). The backend constructs it from `image_filename` and `test_id`.

#### `PATCH /api/v1/tests/{test_id}` -- Update test

Request (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "status": "active"
}
```

Response (200): Full test object.

Validation rules:
- If test is `active` or `closed`, only `name`, `description`, and `status` can be changed.
- Status transitions allowed: `draft -> active`, `active -> closed`, `draft -> closed`. No going backward.
- To transition `draft -> active`: test must have at least one question, and every question must have at least 2 options.

#### `DELETE /api/v1/tests/{test_id}` -- Delete test

Response (204): No content. Cascades to questions, options, responses. Also deletes the `media/{test_id}/` directory from disk.

### 3.2 Screen Questions

#### `POST /api/v1/tests/{test_id}/questions` -- Add a question

Request:
```json
{
  "title": "Which checkout flow do you prefer?",
  "followup_prompt": "What made you choose this?",
  "followup_required": true,
  "randomize_options": true
}
```

Response (201): Full question object with `id`, `order` (auto-assigned as max+1), `created_at`.

Validation: Test must be in `draft` status. `title` required, max 500 chars. `followup_prompt` defaults to `"Why did you choose this?"`. `randomize_options` defaults to `true`.

#### `PATCH /api/v1/questions/{question_id}` -- Update a question

Request (all fields optional):
```json
{
  "title": "Updated title",
  "followup_prompt": "Updated prompt",
  "followup_required": false,
  "randomize_options": false,
  "order": 2
}
```

Response (200): Full question object.

Validation: Parent test must be in `draft` status.

#### `DELETE /api/v1/questions/{question_id}` -- Delete a question

Response (204): No content. Cascades to options and responses.

Validation: Parent test must be in `draft` status.

### 3.3 Options

#### `POST /api/v1/questions/{question_id}/options` -- Add an option (multipart)

Request: `multipart/form-data`
- `label` (string, required): Option label, max 200 chars
- `order` (integer, optional): Display order, default auto-assigned
- `image` (file, optional): Image file (JPEG, PNG, WebP, GIF; max 10MB)

Response (201):
```json
{
  "id": 1,
  "label": "Option A",
  "image_url": "/media/1/abc123.png",
  "order": 0,
  "created_at": "2026-03-31T12:00:00Z"
}
```

Validation: Parent question's test must be in `draft` status. File validated for type and size.

#### `PATCH /api/v1/options/{option_id}` -- Update an option (multipart)

Request: `multipart/form-data`
- `label` (string, optional)
- `order` (integer, optional)
- `image` (file, optional): Replaces existing image

Response (200): Full option object.

Validation: Parent question's test must be in `draft` status.

#### `DELETE /api/v1/options/{option_id}` -- Delete an option

Response (204): No content. Deletes image file from disk. Cascades to responses.

Validation: Parent question's test must be in `draft` status. Cannot delete if question would drop below 2 options AND test is about to be activated (but allow deletion in draft even if it goes to 0 -- they are still building).

### 3.4 Respondent-Facing

#### `GET /api/v1/respond/{slug}` -- Get test for respondent

Response (200):
```json
{
  "id": 1,
  "name": "Homepage A/B Test",
  "description": "Which homepage layout do users prefer?",
  "questions": [
    {
      "id": 1,
      "order": 0,
      "title": "Which homepage layout?",
      "followup_prompt": "Why did you choose this?",
      "followup_required": false,
      "randomize_options": true,
      "options": [
        {
          "id": 1,
          "label": "Option A",
          "image_url": "/media/1/abc123.png",
          "order": 0
        }
      ]
    }
  ]
}
```

Validation: Returns 404 if slug not found. Returns 403 with message `"This test is not currently accepting responses"` if test status is not `active`.

Notes: This endpoint intentionally omits `status`, `slug`, analytics data, and timestamps. It returns only what the respondent needs.

#### `POST /api/v1/respond/{slug}/answers` -- Submit one answer

Request:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question_id": 1,
  "option_id": 2,
  "followup_text": "I liked the cleaner layout"
}
```

Response (201):
```json
{
  "status": "saved"
}
```

Validation:
- Test must be `active`.
- `question_id` must belong to this test.
- `option_id` must belong to this question.
- `followup_text` max 500 chars. If `followup_required` is true on the question, `followup_text` must be non-empty.
- If `(session_id, question_id)` already exists, return 409 Conflict with message `"Already answered this question in this session"`.

### 3.5 Analytics

#### `GET /api/v1/tests/{test_id}/analytics` -- Get analytics

Response (200):
```json
{
  "test_id": 1,
  "test_name": "Homepage A/B Test",
  "total_sessions": 42,
  "total_answers": 120,
  "questions": [
    {
      "question_id": 1,
      "title": "Which homepage layout?",
      "total_votes": 42,
      "options": [
        {
          "option_id": 1,
          "label": "Option A",
          "image_url": "/media/1/abc123.png",
          "votes": 28,
          "percentage": 66.7,
          "is_winner": true,
          "followup_texts": [
            {"text": "Clean layout", "created_at": "2026-03-31T12:00:00Z"},
            {"text": "Better spacing", "created_at": "2026-03-31T12:01:00Z"}
          ]
        },
        {
          "option_id": 2,
          "label": "Option B",
          "image_url": "/media/1/def456.png",
          "votes": 14,
          "percentage": 33.3,
          "is_winner": false,
          "followup_texts": [
            {"text": "More colorful", "created_at": "2026-03-31T12:02:00Z"}
          ]
        }
      ]
    }
  ]
}
```

Notes: `is_winner` is true for the option with the most votes per question. Ties: all tied options are winners. `percentage` is rounded to 1 decimal. `total_sessions` counts distinct `session_id` values.

#### `GET /api/v1/tests/{test_id}/export` -- Download CSV

Response: `Content-Type: text/csv` with `Content-Disposition: attachment; filename="test-{slug}-responses.csv"`

CSV columns:
```
question_title,option_label,followup_text,session_id,responded_at
"Which homepage layout?","Option A","Clean layout","550e8400...","2026-03-31T12:00:00Z"
```

Notes: One row per response. If no responses, export headers only.

---

## 4. Frontend Page/Component Architecture

### 4.1 Page Structure (Next.js App Router)

```
frontend/
  app/
    layout.tsx                -- Root layout: html, body, Tailwind, Navbar
    page.tsx                  -- Dashboard: list all tests (Server Component)
    tests/
      new/
        page.tsx              -- Test builder: create new test (Client Component)
      [testId]/
        page.tsx              -- Test detail/edit (Client Component)
        analytics/
          page.tsx            -- Analytics dashboard (Client Component -- charts)
    respond/
      [slug]/
        page.tsx              -- Respondent flow (Client Component)
```

### 4.2 Component Tree

```
components/
  layout/
    Navbar.tsx                -- Top navigation bar with logo and links
  test-builder/
    TestMetaForm.tsx          -- Name + description fields
    QuestionEditor.tsx        -- Single question: title, followup config, options list
    OptionEditor.tsx          -- Single option: label input, image upload, delete button
    ImageUploader.tsx         -- File input with drag-and-drop, preview, size validation
  respondent/
    IntroScreen.tsx           -- Test name, description, "Start" button
    QuestionView.tsx          -- Displays one question with all option cards
    OptionCard.tsx            -- Single option: image, label, click-to-select, lock-in state
    FollowUpInput.tsx         -- Text area with character counter (500 max)
    ProgressBar.tsx           -- "Question 2 of 5" with visual bar
  analytics/
    SummaryStats.tsx          -- Total responses, sessions count
    VoteChart.tsx             -- Bar or pie chart for one question (toggle between views)
    FollowUpList.tsx          -- List of follow-up texts grouped by option
    ExportButton.tsx          -- CSV download button
  shared/
    Button.tsx                -- Styled button (variants: primary, secondary, danger)
    Card.tsx                  -- Card wrapper with shadow and padding
    EmptyState.tsx            -- "No data yet" with icon and message
    StatusBadge.tsx           -- Colored badge for draft/active/closed
    ConfirmDialog.tsx         -- "Are you sure?" modal for destructive actions
```

### 4.3 Data Flow

```
lib/
  api.ts                      -- All fetch calls to backend, typed responses
  types.ts                    -- TypeScript interfaces matching API response shapes
  constants.ts                -- API_BASE_URL = "http://localhost:8000"
```

**`lib/api.ts` functions:**

| Function | Method | Endpoint | Returns |
|---|---|---|---|
| `fetchTests()` | GET | `/api/v1/tests` | `Test[]` |
| `fetchTest(testId)` | GET | `/api/v1/tests/{testId}` | `TestDetail` |
| `createTest(data)` | POST | `/api/v1/tests` | `Test` |
| `updateTest(testId, data)` | PATCH | `/api/v1/tests/{testId}` | `Test` |
| `deleteTest(testId)` | DELETE | `/api/v1/tests/{testId}` | `void` |
| `createQuestion(testId, data)` | POST | `/api/v1/tests/{testId}/questions` | `Question` |
| `updateQuestion(questionId, data)` | PATCH | `/api/v1/questions/{questionId}` | `Question` |
| `deleteQuestion(questionId)` | DELETE | `/api/v1/questions/{questionId}` | `void` |
| `createOption(questionId, formData)` | POST | `/api/v1/questions/{questionId}/options` | `Option` |
| `updateOption(optionId, formData)` | PATCH | `/api/v1/options/{optionId}` | `Option` |
| `deleteOption(optionId)` | DELETE | `/api/v1/options/{optionId}` | `void` |
| `fetchTestForRespondent(slug)` | GET | `/api/v1/respond/{slug}` | `RespondentTest` |
| `submitAnswer(slug, data)` | POST | `/api/v1/respond/{slug}/answers` | `{status: string}` |
| `fetchAnalytics(testId)` | GET | `/api/v1/tests/{testId}/analytics` | `Analytics` |
| `exportCSV(testId)` | GET | `/api/v1/tests/{testId}/export` | `Blob` (triggers download) |

**`lib/types.ts` interfaces:**

```typescript
interface Test {
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

interface Option {
  id: number;
  label: string;
  image_url: string | null;
  order: number;
}

interface Question {
  id: number;
  order: number;
  title: string;
  followup_prompt: string;
  followup_required: boolean;
  randomize_options: boolean;
  options: Option[];
}

interface TestDetail extends Omit<Test, "question_count" | "response_count"> {
  questions: Question[];
}

interface RespondentTest {
  id: number;
  name: string;
  description: string | null;
  questions: Question[];
}

interface OptionAnalytics {
  option_id: number;
  label: string;
  image_url: string | null;
  votes: number;
  percentage: number;
  is_winner: boolean;
  followup_texts: { text: string; created_at: string }[];
}

interface QuestionAnalytics {
  question_id: number;
  title: string;
  total_votes: number;
  options: OptionAnalytics[];
}

interface Analytics {
  test_id: number;
  test_name: string;
  total_sessions: number;
  total_answers: number;
  questions: QuestionAnalytics[];
}
```

### 4.4 Key UX Flows

**Respondent Flow State (managed in `respond/[slug]/page.tsx`):**

```
State: {
  currentQuestionIndex: number      // 0-based, which question is shown
  phase: "intro" | "question" | "done"
  selectedOptionId: number | null   // current question's selection
  isLocked: boolean                 // once selected, locked in
  followupText: string              // current question's followup input
  sessionId: string                 // UUID generated on mount
}
```

Flow:
1. Mount: generate `sessionId` via `crypto.randomUUID()`, fetch test data, show intro.
2. User clicks "Start" -> phase = "question", index = 0.
3. User clicks an option -> `selectedOptionId` set, `isLocked = true`, show follow-up input.
4. User types follow-up (optional/required per question), clicks "Next".
5. On "Next": POST answer to backend, increment `currentQuestionIndex`, reset `selectedOptionId`/`isLocked`/`followupText`.
6. After last question: phase = "done", show thank-you screen.

**Option Randomization:** When rendering a question where `randomize_options` is true, shuffle the options array using a Fisher-Yates shuffle before displaying. The shuffle happens once when the question is first shown (not on re-render).

**Image Display:** All option images rendered at a fixed height (e.g., 400px) with `object-fit: contain` and `width: auto`. This ensures fair comparison per the decision log.

---

## 5. Tech Stack Decisions

| Technology | Role | Justification |
|---|---|---|
| **Next.js 14+ (App Router)** | Frontend framework | Modern React with file-based routing. App Router is the current standard. TypeScript for type safety. The user is a frontend novice -- conventional patterns and file-based routing reduce cognitive load. |
| **Tailwind CSS** | Styling | Utility-first CSS, no separate stylesheet management. Works well for developers who are not CSS experts. |
| **FastAPI** | Backend framework | Python (user's strength). Async-capable, auto-generates OpenAPI docs, excellent Pydantic integration for validation. |
| **SQLModel** | ORM | Combines SQLAlchemy + Pydantic in one model definition. FastAPI-recommended. Eliminates schema duplication. |
| **SQLite (WAL mode)** | Database | Zero-cost, no server to manage, local-first. WAL mode handles concurrent reads. Sufficient for a single-designer local app. |
| **Recharts** | Charts | React-native charting library. Simple API with `ResponsiveContainer`, `BarChart`, `PieChart`. Well-documented. |
| **Pillow** | Image processing | Python standard for image manipulation. Used to generate thumbnails on upload for fast respondent page loads. |
| **`secrets.token_urlsafe(8)`** | Slug generation | Python stdlib, no extra dependency. Produces 11-char URL-safe slugs with low collision probability. |
| **`useState` + `fetch`** | Frontend state/data | Minimal complexity. No extra libraries (SWR, TanStack Query). The app has simple data flows that do not justify a state management library. |

---

## 6. Test Lifecycle Rules

### States

| State | Meaning | Allowed Actions |
|---|---|---|
| `draft` | Test is being built. Not visible to respondents. | Full CRUD on test, questions, options. Can transition to `active` or `closed`. |
| `active` | Test is live. Respondents can take it via the shareable link. | Edit test `name` and `description` only. Transition to `closed`. Questions and options are locked. |
| `closed` | Test is archived. No new responses accepted. | Edit test `name` and `description` only. No state transitions (terminal). |

### Transition Rules

```
draft -----> active    (requires: >= 1 question, every question has >= 2 options)
draft -----> closed    (allowed unconditionally)
active ----> closed    (allowed unconditionally)
```

No backward transitions. Once `active`, cannot go back to `draft`. Once `closed`, cannot reopen.

### Enforcement

- **Backend:** The `PATCH /api/v1/tests/{test_id}` endpoint validates all transition rules. Returns 400 with a descriptive error message if a transition is invalid.
- **Backend:** All question/option create/update/delete endpoints check `test.status == "draft"` and return 403 if not.
- **Backend:** The `POST /api/v1/respond/{slug}/answers` endpoint checks `test.status == "active"` and returns 403 if not.
- **Frontend:** The test detail page conditionally renders edit controls based on `test.status`. The "Activate" button is disabled if validation fails (shown with a tooltip explaining why).

---

## 7. Image Handling Strategy

### Upload Flow

1. **Frontend:** User selects a file via `<input type="file">` or drag-and-drop in `ImageUploader.tsx`.
2. **Frontend validation:** Check file size < 10MB and type is JPEG/PNG/WebP/GIF. Show error immediately if invalid.
3. **Frontend:** Construct `FormData` with `label`, `order`, and `image` fields. POST to `/api/v1/questions/{questionId}/options`.
4. **Backend validation:** Verify `content_type` is in `["image/jpeg", "image/png", "image/webp", "image/gif"]`. Verify file size <= 10MB.
5. **Backend processing:**
   - Generate UUID filename: `{uuid4}.{extension}` (e.g., `a1b2c3d4.png`).
   - Create directory `media/{test_id}/` if it does not exist.
   - Save original file to `media/{test_id}/{uuid}.{ext}`.
   - Generate thumbnail: resize to max 800px width (maintaining aspect ratio) using Pillow. Save to `media/{test_id}/thumb_{uuid}.{ext}`.
   - Store `image_filename` (the UUID-based name) in the database.
6. **Backend response:** Return `image_url` as `/media/{test_id}/{uuid}.{ext}`.

### Serving

- FastAPI mounts: `app.mount("/media", StaticFiles(directory="media"), name="media")`.
- Frontend uses `<img>` tags with `src={API_BASE_URL + option.image_url}`.
- Thumbnails served to respondent flow: `src={API_BASE_URL + "/media/{test_id}/thumb_" + filename}`.
- Full-size images shown in test builder and analytics.

### Cleanup

- Deleting an option removes its image files from disk (both original and thumbnail).
- Deleting a test removes the entire `media/{test_id}/` directory.
- Replacing an image (via PATCH) deletes the old files before saving the new ones.

### Security

- UUID filenames prevent path traversal attacks.
- File extension validated against allowlist.
- Original user-supplied filenames stored in DB for display but never used in file paths.
- `StaticFiles` serves from a contained directory -- no escape possible.

---

## 8. File Structure

### Backend

```
backend/
  main.py                           -- FastAPI app creation, CORS, StaticFiles mount, router inclusion, lifespan
  requirements.txt                  -- fastapi, uvicorn, sqlmodel, pillow, python-multipart
  app/
    __init__.py
    config.py                       -- Settings: DB path, media dir, CORS origins, max file size
    database.py                     -- Engine creation, get_session, create_db_and_tables, SessionDep
    models/
      __init__.py                   -- Re-exports all models
      test.py                       -- Test SQLModel (table=True)
      screen_question.py            -- ScreenQuestion SQLModel (table=True)
      option.py                     -- Option SQLModel (table=True)
      response.py                   -- Response SQLModel (table=True)
    schemas/
      __init__.py                   -- Re-exports all schemas
      test.py                       -- TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail
      screen_question.py            -- QuestionCreate, QuestionUpdate, QuestionPublic
      option.py                     -- OptionPublic
      response.py                   -- AnswerCreate, AnalyticsResponse, QuestionAnalytics, OptionAnalytics
    routes/
      __init__.py                   -- Router aggregation
      tests.py                      -- Test CRUD endpoints
      questions.py                  -- Question CRUD endpoints
      options.py                    -- Option CRUD endpoints
      respond.py                    -- Respondent-facing: get test by slug, submit answer
      analytics.py                  -- Analytics + CSV export endpoints
    services/
      __init__.py
      image_service.py              -- save_image(), delete_image(), validate_image()
      analytics_service.py          -- compute_analytics(), compute_csv()
  data/                             -- SQLite DB file (app.db), gitignored
  media/                            -- Uploaded images, gitignored
```

### Frontend

```
frontend/
  package.json
  tsconfig.json
  tailwind.config.ts
  next.config.ts
  app/
    layout.tsx                      -- Root layout: html, body, Tailwind globals, Navbar
    page.tsx                        -- Dashboard: list tests
    globals.css                     -- Tailwind @tailwind directives
    tests/
      new/
        page.tsx                    -- Test builder (create new)
      [testId]/
        page.tsx                    -- Test detail/edit
        analytics/
          page.tsx                  -- Analytics dashboard
    respond/
      [slug]/
        page.tsx                    -- Respondent flow
  components/
    layout/
      Navbar.tsx
    test-builder/
      TestMetaForm.tsx
      QuestionEditor.tsx
      OptionEditor.tsx
      ImageUploader.tsx
    respondent/
      IntroScreen.tsx
      QuestionView.tsx
      OptionCard.tsx
      FollowUpInput.tsx
      ProgressBar.tsx
    analytics/
      SummaryStats.tsx
      VoteChart.tsx
      FollowUpList.tsx
      ExportButton.tsx
    shared/
      Button.tsx
      Card.tsx
      EmptyState.tsx
      StatusBadge.tsx
      ConfirmDialog.tsx
  lib/
    api.ts                          -- All API fetch functions
    types.ts                        -- TypeScript interfaces
    constants.ts                    -- API_BASE_URL
```

---

## 9. Implementation Tasks

The tasks below are ordered for a clean build sequence where each layer builds on the previous.

### Phase 1: Backend Foundation

---

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `backend/main.py`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/routes backend/app/services backend/data backend/media
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/routes/__init__.py backend/app/services/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlmodel==0.0.22
pillow==11.1.0
python-multipart==0.0.20
```

- [ ] **Step 3: Create virtual environment and install dependencies**

```bash
cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

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
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
THUMBNAIL_MAX_WIDTH = 800
```

- [ ] **Step 5: Write database.py**

```python
# backend/app/database.py
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine
from app.config import DATABASE_URL, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
```

- [ ] **Step 6: Write main.py with lifespan, CORS, and static files**

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import CORS_ORIGINS, MEDIA_DIR
from app.database import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Enable WAL mode for better concurrent reads
    from app.database import engine
    from sqlmodel import text
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()
    yield


app = FastAPI(title="DesignPoll API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
```

- [ ] **Step 7: Verify the server starts**

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

Expected: Server starts, `http://localhost:8000/docs` shows Swagger UI with no endpoints yet.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, SQLModel, CORS, and static files"
```

---

### Task 2: Database models

**Files:**
- Create: `backend/app/models/test.py`
- Create: `backend/app/models/screen_question.py`
- Create: `backend/app/models/option.py`
- Create: `backend/app/models/response.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write Test model**

```python
# backend/app/models/test.py
import secrets
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion


def generate_slug() -> str:
    return secrets.token_urlsafe(8)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.test import Test
    from app.models.option import Option
    from app.models.response import Response


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion
    from app.models.response import Response


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Option(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    screen_question_id: int = Field(foreign_key="screenquestion.id", index=True)
    label: str = Field(max_length=200)
    image_filename: str | None = Field(default=None, max_length=255)
    original_filename: str | None = Field(default=None, max_length=255)
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
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.screen_question import ScreenQuestion
    from app.models.option import Option


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
cd backend && source venv/bin/activate && python -c "
from app.models import Test, ScreenQuestion, Option, Response
from app.database import create_db_and_tables, engine
create_db_and_tables()
print('Tables created successfully')
import sqlite3
conn = sqlite3.connect('data/app.db')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print('Tables:', [t[0] for t in tables])
conn.close()
"
```

Expected: `Tables: ['test', 'screenquestion', 'option', 'response']`

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/
git commit -m "feat: add SQLModel database models for Test, ScreenQuestion, Option, Response"
```

---

### Task 3: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/test.py`
- Create: `backend/app/schemas/screen_question.py`
- Create: `backend/app/schemas/option.py`
- Create: `backend/app/schemas/response.py`
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Write test schemas**

```python
# backend/app/schemas/test.py
from datetime import datetime
from pydantic import BaseModel, Field


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

- [ ] **Step 3: Write option schemas**

```python
# backend/app/schemas/option.py
from datetime import datetime
from pydantic import BaseModel


class OptionPublic(BaseModel):
    id: int
    label: str
    image_url: str | None = None
    order: int
    created_at: datetime
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
    image_url: str | None
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
    questions: list[QuestionAnalytics]
```

- [ ] **Step 5: Write test detail schema (depends on QuestionPublic)**

Add to `backend/app/schemas/test.py`:

```python
# Append to the end of backend/app/schemas/test.py
from app.schemas.screen_question import QuestionPublic


class TestDetail(TestPublic):
    questions: list[QuestionPublic] = []


class RespondentTest(BaseModel):
    id: int
    name: str
    description: str | None
    questions: list[QuestionPublic] = []
```

- [ ] **Step 6: Update schemas __init__.py**

```python
# backend/app/schemas/__init__.py
from app.schemas.option import OptionPublic
from app.schemas.screen_question import QuestionCreate, QuestionUpdate, QuestionPublic
from app.schemas.test import TestCreate, TestUpdate, TestPublic, TestListItem, TestDetail, RespondentTest
from app.schemas.response import AnswerCreate, AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas for API request/response validation"
```

---

### Task 4: Image service

**Files:**
- Create: `backend/app/services/image_service.py`

- [ ] **Step 1: Write image service**

```python
# backend/app/services/image_service.py
import shutil
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image
from app.config import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, MEDIA_DIR, THUMBNAIL_MAX_WIDTH


def validate_image(file: UploadFile) -> None:
    """Validate image file type and size."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF.",
        )


async def save_image(file: UploadFile, test_id: int) -> tuple[str, str]:
    """Save uploaded image and generate thumbnail. Returns (uuid_filename, original_filename)."""
    validate_image(file)

    # Read file content
    content = await file.read()
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

    # Generate thumbnail
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
    """Construct the URL path for a thumbnail."""
    if not filename:
        return None
    return f"/media/{test_id}/thumb_{filename}"
```

- [ ] **Step 2: Verify imports work**

```bash
cd backend && source venv/bin/activate && python -c "from app.services.image_service import save_image, delete_image, get_image_url; print('Image service OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/image_service.py
git commit -m "feat: add image service for upload, thumbnail, and cleanup"
```

---

### Task 5: Test CRUD routes

**Files:**
- Create: `backend/app/routes/tests.py`
- Modify: `backend/main.py` (include router)

- [ ] **Step 1: Write tests router**

```python
# backend/app/routes/tests.py
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select
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


@router.post("", response_model=TestPublic, status_code=201)
def create_test(data: TestCreate, session: SessionDep):
    test = Test.model_validate(data)
    session.add(test)
    session.commit()
    session.refresh(test)
    return test


@router.get("", response_model=list[TestListItem])
def list_tests(session: SessionDep):
    tests = session.exec(select(Test).order_by(col(Test.created_at).desc())).all()
    result = []
    for test in tests:
        q_count = session.exec(
            select(func.count()).where(ScreenQuestion.test_id == test.id)
        ).one()
        r_count = session.exec(
            select(func.count(func.distinct(Response.session_id))).where(
                Response.screen_question_id.in_(
                    select(ScreenQuestion.id).where(ScreenQuestion.test_id == test.id)
                )
            )
        ).one()
        item = TestListItem(
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
        result.append(item)
    return result


@router.get("/{test_id}", response_model=TestDetail)
def get_test(test_id: int, session: SessionDep):
    test = session.get(Test, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test_id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_list = []
    for q in questions:
        options = session.exec(
            select(Option)
            .where(Option.screen_question_id == q.id)
            .order_by(Option.order)
        ).all()
        option_list = [
            OptionPublic(
                id=o.id,
                label=o.label,
                image_url=get_image_url(test_id, o.image_filename),
                order=o.order,
                created_at=o.created_at,
            )
            for o in options
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
    delete_test_media(test_id)
    session.delete(test)
    session.commit()
    return None
```

- [ ] **Step 2: Include tests router in main.py**

Add to `backend/main.py` after the `app.mount(...)` line:

```python
from app.routes.tests import router as tests_router
app.include_router(tests_router)
```

Also add the models import so tables are registered:

```python
from app.models import Test, ScreenQuestion, Option, Response  # noqa: F401
```

- [ ] **Step 3: Verify endpoints appear in Swagger**

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs`. Expected: Test CRUD endpoints visible.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routes/tests.py backend/main.py
git commit -m "feat: add Test CRUD API endpoints with lifecycle validation"
```

---

### Task 6: Question CRUD routes

**Files:**
- Create: `backend/app/routes/questions.py`
- Modify: `backend/main.py` (include router)

- [ ] **Step 1: Write questions router**

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
from app.services.image_service import get_image_url

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
    test = session.get(Test, question.test_id)
    option_list = [
        OptionPublic(
            id=o.id,
            label=o.label,
            image_url=get_image_url(question.test_id, o.image_filename),
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
    _require_draft(session, question.test_id)
    session.delete(question)
    session.commit()
    return None
```

- [ ] **Step 2: Include questions router in main.py**

Add to `backend/main.py`:

```python
from app.routes.questions import router as questions_router
app.include_router(questions_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/questions.py backend/main.py
git commit -m "feat: add ScreenQuestion CRUD API endpoints"
```

---

### Task 7: Option CRUD routes (with image upload)

**Files:**
- Create: `backend/app/routes/options.py`
- Modify: `backend/main.py` (include router)

- [ ] **Step 1: Write options router**

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
        image_url=get_image_url(test_id, option.image_filename),
        order=option.order,
        created_at=option.created_at,
    )


@router.post("/api/v1/questions/{question_id}/options", response_model=OptionPublic, status_code=201)
async def create_option(
    question_id: int,
    session: SessionDep,
    label: str = Form(..., max_length=200),
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    question = _require_draft_for_question(session, question_id)

    # Auto-assign order
    if order is None:
        max_order = session.exec(
            select(func.max(Option.order)).where(Option.screen_question_id == question_id)
        ).one()
        order = (max_order or -1) + 1

    image_filename = None
    original_filename = None
    if image and image.filename:
        image_filename, original_filename = await save_image(image, question.test_id)

    option = Option(
        screen_question_id=question_id,
        label=label,
        image_filename=image_filename,
        original_filename=original_filename,
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
    order: int | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    if label is not None:
        option.label = label
    if order is not None:
        option.order = order
    if image and image.filename:
        # Delete old image
        if option.image_filename:
            delete_image(question.test_id, option.image_filename)
        option.image_filename, option.original_filename = await save_image(image, question.test_id)

    session.add(option)
    session.commit()
    session.refresh(option)
    return _option_to_public(option, question.test_id)


@router.delete("/api/v1/options/{option_id}", status_code=204)
def delete_option(option_id: int, session: SessionDep):
    option = session.get(Option, option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    question = _require_draft_for_question(session, option.screen_question_id)

    # Delete image from disk
    if option.image_filename:
        delete_image(question.test_id, option.image_filename)

    session.delete(option)
    session.commit()
    return None
```

- [ ] **Step 2: Include options router in main.py**

Add to `backend/main.py`:

```python
from app.routes.options import router as options_router
app.include_router(options_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/options.py backend/main.py
git commit -m "feat: add Option CRUD API with image upload and thumbnail generation"
```

---

### Task 8: Respondent-facing routes

**Files:**
- Create: `backend/app/routes/respond.py`
- Modify: `backend/main.py` (include router)

- [ ] **Step 1: Write respond router**

```python
# backend/app/routes/respond.py
from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.database import SessionDep
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.test import RespondentTest
from app.schemas.screen_question import QuestionPublic
from app.schemas.option import OptionPublic
from app.schemas.response import AnswerCreate
from app.services.image_service import get_image_url

router = APIRouter(prefix="/api/v1/respond", tags=["respondent"])


@router.get("/{slug}", response_model=RespondentTest)
def get_test_for_respondent(slug: str, session: SessionDep):
    test = session.exec(select(Test).where(Test.slug == slug)).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.status != "active":
        raise HTTPException(status_code=403, detail="This test is not currently accepting responses.")

    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    question_list = []
    for q in questions:
        options = session.exec(
            select(Option).where(Option.screen_question_id == q.id).order_by(Option.order)
        ).all()
        option_list = [
            OptionPublic(
                id=o.id,
                label=o.label,
                image_url=get_image_url(test.id, o.image_filename),
                order=o.order,
                created_at=o.created_at,
            )
            for o in options
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

    return RespondentTest(
        id=test.id,
        name=test.name,
        description=test.description,
        questions=question_list,
    )


@router.post("/{slug}/answers", status_code=201)
def submit_answer(slug: str, data: AnswerCreate, session: SessionDep):
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

    # Check for duplicate submission
    existing = session.exec(
        select(Response).where(
            Response.session_id == data.session_id,
            Response.screen_question_id == data.question_id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already answered this question in this session.")

    response = Response(
        screen_question_id=data.question_id,
        option_id=data.option_id,
        session_id=data.session_id,
        followup_text=data.followup_text,
    )
    session.add(response)
    session.commit()
    return {"status": "saved"}
```

- [ ] **Step 2: Include respond router in main.py**

Add to `backend/main.py`:

```python
from app.routes.respond import router as respond_router
app.include_router(respond_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routes/respond.py backend/main.py
git commit -m "feat: add respondent-facing endpoints for test retrieval and answer submission"
```

---

### Task 9: Analytics and CSV export routes

**Files:**
- Create: `backend/app/services/analytics_service.py`
- Create: `backend/app/routes/analytics.py`
- Modify: `backend/main.py` (include router)

- [ ] **Step 1: Write analytics service**

```python
# backend/app/services/analytics_service.py
import csv
import io
from sqlmodel import Session, func, select
from app.models.test import Test
from app.models.screen_question import ScreenQuestion
from app.models.option import Option
from app.models.response import Response
from app.schemas.response import AnalyticsResponse, QuestionAnalytics, OptionAnalytics, FollowUpEntry
from app.services.image_service import get_image_url


def compute_analytics(test: Test, session: Session) -> AnalyticsResponse:
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    # Total distinct sessions across all questions in this test
    question_ids = [q.id for q in questions]
    if question_ids:
        total_sessions = session.exec(
            select(func.count(func.distinct(Response.session_id))).where(
                Response.screen_question_id.in_(question_ids)
            )
        ).one()
        total_answers = session.exec(
            select(func.count()).where(
                Response.screen_question_id.in_(question_ids)
            )
        ).one()
    else:
        total_sessions = 0
        total_answers = 0

    question_analytics = []
    for q in questions:
        options = session.exec(
            select(Option).where(Option.screen_question_id == q.id).order_by(Option.order)
        ).all()

        total_votes = session.exec(
            select(func.count()).where(Response.screen_question_id == q.id)
        ).one()

        option_analytics = []
        max_votes = 0
        for o in options:
            votes = session.exec(
                select(func.count()).where(
                    Response.screen_question_id == q.id,
                    Response.option_id == o.id,
                )
            ).one()
            if votes > max_votes:
                max_votes = votes

            followups = session.exec(
                select(Response).where(
                    Response.screen_question_id == q.id,
                    Response.option_id == o.id,
                    Response.followup_text.isnot(None),  # type: ignore
                    Response.followup_text != "",
                )
            ).all()

            percentage = round((votes / total_votes * 100), 1) if total_votes > 0 else 0.0

            option_analytics.append(
                OptionAnalytics(
                    option_id=o.id,
                    label=o.label,
                    image_url=get_image_url(test.id, o.image_filename),
                    votes=votes,
                    percentage=percentage,
                    is_winner=False,  # set below
                    followup_texts=[
                        FollowUpEntry(text=r.followup_text, created_at=r.created_at)
                        for r in followups
                    ],
                )
            )

        # Mark winner(s)
        for oa in option_analytics:
            if oa.votes == max_votes and max_votes > 0:
                oa.is_winner = True

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
        questions=question_analytics,
    )


def generate_csv(test: Test, session: Session) -> str:
    questions = session.exec(
        select(ScreenQuestion)
        .where(ScreenQuestion.test_id == test.id)
        .order_by(ScreenQuestion.order)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["question_title", "option_label", "followup_text", "session_id", "responded_at"])

    for q in questions:
        responses = session.exec(
            select(Response).where(Response.screen_question_id == q.id).order_by(Response.created_at)
        ).all()
        for r in responses:
            option = session.get(Option, r.option_id)
            writer.writerow([
                q.title,
                option.label if option else "Unknown",
                r.followup_text or "",
                r.session_id,
                r.created_at.isoformat(),
            ])

    return output.getvalue()
```

- [ ] **Step 2: Write analytics router**

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

- [ ] **Step 3: Include analytics router in main.py**

Add to `backend/main.py`:

```python
from app.routes.analytics import router as analytics_router
app.include_router(analytics_router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/analytics_service.py backend/app/routes/analytics.py backend/main.py
git commit -m "feat: add analytics computation and CSV export endpoints"
```

---

### Task 10: Backend integration test -- full workflow

**Files:**
- Create: `backend/tests/test_workflow.py`

- [ ] **Step 1: Write integration test**

```python
# backend/tests/test_workflow.py
"""Full workflow integration test: create test -> add questions -> add options -> activate -> respond -> analytics."""
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from app.database import engine
from main import app

client = TestClient(app)


def setup_module():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def test_full_workflow():
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

    # 3. Add options (without images for simplicity)
    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option A", "order": "0"},
    )
    assert res.status_code == 201
    option_a_id = res.json()["id"]

    res = client.post(
        f"/api/v1/questions/{question_id}/options",
        data={"label": "Option B", "order": "1"},
    )
    assert res.status_code == 201
    option_b_id = res.json()["id"]

    # 4. Cannot activate with no questions having < 2 options -- already have 2, so activate
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

    # 8. Duplicate answer rejected
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
    assert len(analytics["questions"]) == 1
    q_analytics = analytics["questions"][0]
    assert q_analytics["total_votes"] == 2
    # Each option should have 1 vote
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

- [ ] **Step 2: Run the test**

```bash
cd backend && source venv/bin/activate && pip install pytest && python -m pytest tests/test_workflow.py -v
```

Expected: All assertions pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/
git commit -m "test: add full workflow integration test for backend API"
```

---

### Phase 2: Frontend Foundation

---

### Task 11: Next.js project scaffolding

**Files:**
- Create: `frontend/` (via create-next-app)
- Modify: `frontend/app/globals.css`
- Create: `frontend/lib/constants.ts`
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create Next.js project**

```bash
cd /Users/bharath/Documents/abtestingapp && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

- [ ] **Step 2: Write constants.ts**

```typescript
// frontend/lib/constants.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

- [ ] **Step 3: Write types.ts**

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
  image_url: string | null;
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
  image_url: string | null;
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
  questions: QuestionAnalytics[];
}
```

- [ ] **Step 4: Write api.ts**

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

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with TypeScript types and API client"
```

---

### Task 12: Shared UI components

**Files:**
- Create: `frontend/components/shared/Button.tsx`
- Create: `frontend/components/shared/Card.tsx`
- Create: `frontend/components/shared/EmptyState.tsx`
- Create: `frontend/components/shared/StatusBadge.tsx`
- Create: `frontend/components/shared/ConfirmDialog.tsx`
- Create: `frontend/components/layout/Navbar.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Write Button component**

```tsx
// frontend/components/shared/Button.tsx
"use client";

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

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
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
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={onCancel}>
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

- [ ] **Step 7: Update root layout**

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";

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
        <Navbar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  );
}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/components/ frontend/app/layout.tsx
git commit -m "feat: add shared UI components and Navbar layout"
```

---

### Phase 3: Frontend Pages

---

### Task 13: Dashboard page (test list)

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Write dashboard page**

```tsx
// frontend/app/page.tsx
import Link from "next/link";
import { fetchTests } from "@/lib/api";
import type { Test } from "@/lib/types";
import Card from "@/components/shared/Card";
import StatusBadge from "@/components/shared/StatusBadge";
import EmptyState from "@/components/shared/EmptyState";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let tests: Test[] = [];
  let error: string | null = null;

  try {
    tests = await fetchTests();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load tests";
  }

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

- [ ] **Step 2: Verify the page renders**

Start both servers:
- Backend: `cd backend && uvicorn main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`

Visit `http://localhost:3000`. Expected: "No tests yet" empty state.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: add dashboard page with test listing"
```

---

### Task 14: Test builder page (create new test)

**Files:**
- Create: `frontend/app/tests/new/page.tsx`
- Create: `frontend/components/test-builder/TestMetaForm.tsx`
- Create: `frontend/components/test-builder/QuestionEditor.tsx`
- Create: `frontend/components/test-builder/OptionEditor.tsx`
- Create: `frontend/components/test-builder/ImageUploader.tsx`

- [ ] **Step 1: Write ImageUploader component**

```tsx
// frontend/components/test-builder/ImageUploader.tsx
"use client";

import { useRef, useState } from "react";

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

  const displayUrl = preview || (currentImageUrl ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${currentImageUrl}` : null);

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

- [ ] **Step 2: Write OptionEditor component**

```tsx
// frontend/components/test-builder/OptionEditor.tsx
"use client";

import { useState } from "react";
import ImageUploader from "./ImageUploader";
import Button from "@/components/shared/Button";

interface OptionEditorProps {
  optionId?: number;
  initialLabel: string;
  initialImageUrl?: string | null;
  onSave: (label: string, imageFile: File | null) => Promise<void>;
  onDelete?: () => Promise<void>;
  isNew?: boolean;
}

export default function OptionEditor({
  initialLabel,
  initialImageUrl,
  onSave,
  onDelete,
  isNew = false,
}: OptionEditorProps) {
  const [label, setLabel] = useState(initialLabel);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!label.trim()) return;
    setSaving(true);
    try {
      await onSave(label.trim(), imageFile);
      if (isNew) {
        setLabel("");
        setImageFile(null);
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
      <ImageUploader currentImageUrl={initialImageUrl} onFileSelect={setImageFile} />
      <Button size="sm" onClick={handleSave} disabled={saving || !label.trim()}>
        {saving ? "Saving..." : isNew ? "Add Option" : "Update"}
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: Write QuestionEditor component**

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

  async function handleSaveQuestion() {
    setSaving(true);
    try {
      await updateQuestion(question.id, {
        title,
        followup_prompt: followupPrompt,
        followup_required: followupRequired,
        randomize_options: randomizeOptions,
      });
      onUpdate();
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteQuestion() {
    await deleteQuestion(question.id);
    onDelete();
  }

  async function handleSaveOption(label: string, imageFile: File | null, optionId?: number) {
    const formData = new FormData();
    formData.append("label", label);
    if (imageFile) formData.append("image", imageFile);

    if (optionId) {
      await updateOption(optionId, formData);
    } else {
      await createOption(question.id, formData);
    }
    onUpdate();
  }

  async function handleDeleteOption(optionId: number) {
    await deleteOption(optionId);
    onUpdate();
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-start">
        <h3 className="text-sm font-medium text-gray-500">Question {question.order + 1}</h3>
        <Button variant="danger" size="sm" onClick={handleDeleteQuestion}>
          Delete Question
        </Button>
      </div>

      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Question title (e.g., Which homepage do you prefer?)"
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
        maxLength={500}
      />

      <div className="grid grid-cols-2 gap-4">
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
              initialImageUrl={opt.image_url}
              onSave={(label, file) => handleSaveOption(label, file, opt.id)}
              onDelete={() => handleDeleteOption(opt.id)}
            />
          ))}
          <OptionEditor
            initialLabel=""
            isNew
            onSave={(label, file) => handleSaveOption(label, file)}
          />
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
// frontend/app/tests/new/page.tsx
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

- [ ] **Step 6: Commit**

```bash
git add frontend/app/tests/ frontend/components/test-builder/
git commit -m "feat: add test builder page with question and option editors"
```

---

### Task 15: Test detail/edit page

**Files:**
- Create: `frontend/app/tests/[testId]/page.tsx`

- [ ] **Step 1: Write test detail page**

```tsx
// frontend/app/tests/[testId]/page.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import type { TestDetail } from "@/lib/types";
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
  const canActivate = isDraft && test.questions.length > 0 && test.questions.every((q) => q.options.length >= 2);

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
          {test.status !== "closed" && (
            <Link href={`/tests/${testId}/analytics`}>
              <Button variant="secondary">Analytics</Button>
            </Link>
          )}
          {test.status === "closed" && (
            <Link href={`/tests/${testId}/analytics`}>
              <Button variant="secondary">Analytics</Button>
            </Link>
          )}
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
                title={canActivate ? "" : "Need at least 1 question with 2+ options"}
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
                <div className="flex gap-2 mt-3">
                  {q.options.map((o) => (
                    <div key={o.id} className="text-center">
                      {o.image_url && (
                        <img
                          src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${o.image_url}`}
                          alt={o.label}
                          className="h-24 object-contain rounded border"
                        />
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
git add frontend/app/tests/
git commit -m "feat: add test detail page with status management and question editing"
```

---

### Task 16: Respondent flow page

**Files:**
- Create: `frontend/app/respond/[slug]/page.tsx`
- Create: `frontend/components/respondent/IntroScreen.tsx`
- Create: `frontend/components/respondent/QuestionView.tsx`
- Create: `frontend/components/respondent/OptionCard.tsx`
- Create: `frontend/components/respondent/FollowUpInput.tsx`
- Create: `frontend/components/respondent/ProgressBar.tsx`

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

- [ ] **Step 2: Write FollowUpInput component**

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

- [ ] **Step 3: Write OptionCard component**

```tsx
// frontend/components/respondent/OptionCard.tsx
"use client";

import { API_BASE_URL } from "@/lib/constants";

interface OptionCardProps {
  label: string;
  imageUrl: string | null;
  selected: boolean;
  locked: boolean;
  onClick: () => void;
}

export default function OptionCard({ label, imageUrl, selected, locked, onClick }: OptionCardProps) {
  const borderClass = selected
    ? "border-blue-500 ring-2 ring-blue-200"
    : "border-gray-200 hover:border-gray-400";
  const cursorClass = locked ? "cursor-default" : "cursor-pointer";

  return (
    <div
      className={`relative border-2 rounded-lg overflow-hidden transition-all ${borderClass} ${cursorClass}`}
      onClick={locked ? undefined : onClick}
    >
      {imageUrl && (
        <div className="flex justify-center bg-gray-50 p-2">
          <img
            src={`${API_BASE_URL}${imageUrl}`}
            alt={label}
            className="object-contain"
            style={{ height: "400px" }}
          />
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

- [ ] **Step 4: Write QuestionView component**

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
  // Shuffle once when the question first renders (useMemo with question.id dependency)
  const displayOptions = useMemo(() => {
    if (question.randomize_options) {
      return shuffleArray(question.options);
    }
    return [...question.options].sort((a, b) => a.order - b.order);
  }, [question.id, question.randomize_options]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
        {question.title}
      </h2>
      <div
        className={`grid gap-4 ${
          displayOptions.length === 2
            ? "grid-cols-2"
            : displayOptions.length === 3
            ? "grid-cols-3"
            : "grid-cols-2 lg:grid-cols-3"
        }`}
      >
        {displayOptions.map((option) => (
          <OptionCard
            key={option.id}
            label={option.label}
            imageUrl={option.image_url}
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

- [ ] **Step 6: Write the respondent flow page**

```tsx
// frontend/app/respond/[slug]/page.tsx
"use client";

import { useEffect, useState, useCallback } from "react";
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

    // Validate required followup
    if (question.followup_required && !followupText.trim()) {
      return; // Button should be disabled, but guard anyway
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
git add frontend/app/respond/ frontend/components/respondent/
git commit -m "feat: add respondent flow with lock-in selection, follow-up, and progress bar"
```

---

### Task 17: Analytics dashboard page

**Files:**
- Create: `frontend/app/tests/[testId]/analytics/page.tsx`
- Create: `frontend/components/analytics/SummaryStats.tsx`
- Create: `frontend/components/analytics/VoteChart.tsx`
- Create: `frontend/components/analytics/FollowUpList.tsx`
- Create: `frontend/components/analytics/ExportButton.tsx`

- [ ] **Step 1: Install Recharts**

```bash
cd frontend && npm install recharts
```

- [ ] **Step 2: Write SummaryStats component**

```tsx
// frontend/components/analytics/SummaryStats.tsx

interface SummaryStatsProps {
  totalSessions: number;
  totalAnswers: number;
}

export default function SummaryStats({ totalSessions, totalAnswers }: SummaryStatsProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalSessions}</p>
        <p className="text-sm text-gray-500">Respondents</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
        <p className="text-3xl font-bold text-gray-900">{totalAnswers}</p>
        <p className="text-sm text-gray-500">Total Answers</p>
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
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
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
              formatter={(value: number, name: string) => {
                const item = data.find((d) => d.votes === value);
                return [`${value} votes (${item?.percentage || 0}%)`, "Votes"];
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
                  "{f.text}"
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
    window.open(getExportUrl(testId), "_blank");
  }

  return (
    <Button variant="secondary" onClick={handleExport}>
      Export CSV
    </Button>
  );
}
```

- [ ] **Step 6: Write analytics page**

```tsx
// frontend/app/tests/[testId]/analytics/page.tsx
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

- [ ] **Step 7: Commit**

```bash
git add frontend/app/tests/ frontend/components/analytics/ frontend/package.json frontend/package-lock.json
git commit -m "feat: add analytics dashboard with Recharts bar/pie charts, follow-ups, and CSV export"
```

---

### Phase 4: Polish and Integration

---

### Task 18: Respondent flow -- hide Navbar

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/app/respond/[slug]/layout.tsx`

- [ ] **Step 1: Create respondent layout without Navbar**

The respondent flow should be clean, without the designer navigation. Create a separate layout.

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

Update the root layout to conditionally show the Navbar. Since App Router layouts are nested, the simplest approach is to keep the Navbar in root layout and override in the respond layout. However, the respond layout is nested inside root, so the Navbar would still show. The correct approach is to restructure:

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

Create a route group for designer pages that includes the Navbar:

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

Move designer pages into the route group:
- `frontend/app/(designer)/page.tsx` -- dashboard
- `frontend/app/(designer)/tests/new/page.tsx` -- new test
- `frontend/app/(designer)/tests/[testId]/page.tsx` -- test detail
- `frontend/app/(designer)/tests/[testId]/analytics/page.tsx` -- analytics

The respondent pages stay at `frontend/app/respond/[slug]/page.tsx` (outside the route group, no Navbar).

- [ ] **Step 2: Move files**

```bash
cd frontend && mkdir -p "app/(designer)/tests/new" "app/(designer)/tests/[testId]/analytics"
mv app/page.tsx "app/(designer)/page.tsx"
mv app/tests/new/page.tsx "app/(designer)/tests/new/page.tsx"
mv "app/tests/[testId]/page.tsx" "app/(designer)/tests/[testId]/page.tsx"
mv "app/tests/[testId]/analytics/page.tsx" "app/(designer)/tests/[testId]/analytics/page.tsx"
rm -rf app/tests
```

- [ ] **Step 3: Create designer layout**

Write `frontend/app/(designer)/layout.tsx` with the Navbar as shown above.

- [ ] **Step 4: Verify both layouts work**

- `http://localhost:3000` -- shows Navbar + dashboard
- `http://localhost:3000/respond/some-slug` -- no Navbar, clean respondent view

- [ ] **Step 5: Commit**

```bash
git add frontend/app/
git commit -m "refactor: use route groups to hide Navbar on respondent pages"
```

---

### Task 19: Backend .gitignore and final main.py

**Files:**
- Create: `backend/.gitignore`
- Modify: `backend/main.py` (final version with all routers)
- Create: `.gitignore` (root)

- [ ] **Step 1: Write backend .gitignore**

```
venv/
__pycache__/
*.pyc
data/
media/
.pytest_cache/
```

- [ ] **Step 2: Write root .gitignore**

```
# Backend
backend/venv/
backend/__pycache__/
backend/**/__pycache__/
backend/*.pyc
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

- [ ] **Step 3: Write final main.py**

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import CORS_ORIGINS, MEDIA_DIR
from app.database import create_db_and_tables
from app.models import Test, ScreenQuestion, Option, Response  # noqa: F401
from app.routes.tests import router as tests_router
from app.routes.questions import router as questions_router
from app.routes.options import router as options_router
from app.routes.respond import router as respond_router
from app.routes.analytics import router as analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    from app.database import engine
    from sqlmodel import text
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()
    yield


app = FastAPI(title="DesignPoll API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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

- [ ] **Step 4: Commit**

```bash
git add .gitignore backend/.gitignore backend/main.py
git commit -m "chore: add gitignore files and finalize main.py with all routers"
```

---

### Task 20: End-to-end smoke test

This task is manual verification to confirm everything works together.

- [ ] **Step 1: Start backend**

```bash
cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Verify full flow**

1. Visit `http://localhost:3000` -- see empty dashboard.
2. Click "New Test" -- create a test named "Homepage Test" with description.
3. On the test detail page, click "Add Question" -- edit the title to "Which homepage?".
4. Add two options with labels "Design A" and "Design B" (optionally with images).
5. Click "Activate" -- status changes to active, share link appears.
6. Open the share link in a new tab -- see intro screen, click Start.
7. Select an option -- it locks in with "Locked in" indicator.
8. Type follow-up text, click Next/Finish.
9. See "Thank you" screen.
10. Go back to test detail, click "Analytics" -- see 1 respondent, vote chart, follow-up text.
11. Click "Export CSV" -- download opens with response data.
12. Close the test -- status changes to "Closed", share link returns error.

- [ ] **Step 4: Commit any fixes discovered during smoke test**

```bash
git add -A && git commit -m "fix: address issues found during end-to-end smoke test"
```

---

## Phase Ordering Summary

| Phase | Tasks | What it produces |
|---|---|---|
| **Phase 1: Backend Foundation** | Tasks 1-9 | Complete REST API with all endpoints, database, image handling, tests |
| **Phase 2: Frontend Foundation** | Tasks 11-12 | Next.js project, API client, shared components |
| **Phase 3: Frontend Pages** | Tasks 13-17 | Dashboard, test builder, respondent flow, analytics |
| **Phase 4: Polish** | Tasks 18-20 | Route groups, gitignore, end-to-end verification |

Each phase produces working, testable software. Phase 1 can be tested entirely via Swagger UI and pytest. Phase 2+3 require both servers running. Phase 4 is cleanup and verification.
