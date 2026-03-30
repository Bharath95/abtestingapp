# Project: DesignPoll — A/B Testing App for UI/UX Designers

## What This Is
A web application that lets UI/UX designers create A/B (or A/B/C/...) design tests, present them to respondents, collect locked-in choices with optional reasoning, and view results through a simple analytics dashboard.

## Tech Stack
- **Frontend:** Next.js with Tailwind CSS (TypeScript)
- **Backend:** FastAPI (Python) — lightweight, async, easy to extend
- **Database:** SQLite (zero-cost, local-first, no hosting needed)
- **Charts:** Recharts or Chart.js (via react-chartjs-2)
- **Image storage:** Local filesystem (uploaded images stored in a `media/` directory)

## User Roles
1. **Designer** — creates and configures tests, views analytics
2. **Respondent** — takes the test (no account needed)

## Core Features (MVP)

### 1. Test Builder (Designer Side)
The designer creates a **test** which contains one or more **screen questions** in sequence.

**Hierarchy:**
```
Test
 └── Screen Question 1
      ├── Option A (image upload OR URL)
      ├── Option B (image upload OR URL)
      └── Option C (optional, image upload OR URL)
      └── Follow-up config:
           ├── "Why did you choose this?" (text input)
           └── Required or optional (configurable per screen question)
 └── Screen Question 2
      ├── Option A
      ├── Option B
      └── Follow-up config...
 └── ... more screen questions
```

**Designer configures per screen question:**
- A title/prompt (e.g., "Which homepage layout do you prefer?")
- 2-5 options, each with: a label, an image (upload) OR a URL (renders as iframe or screenshot)
- Whether follow-up reasoning is required or optional
- Custom follow-up prompt text (default: "Why did you choose this?")

**Designer configures per test:**
- Test name
- Optional description/intro text shown to respondents before starting

### 2. Respondent Flow
1. Respondent opens the test (locally on designer's laptop, or via shareable link later)
2. Sees intro screen with test name + description → clicks "Start"
3. For each screen question:
   a. Sees all options side-by-side (images or URL previews)
   b. Clicks to select one option → **choice locks in** (visually confirmed, cannot change)
   c. If follow-up is configured: sees a text input for reasoning
   d. Clicks "Next" to proceed to next screen question
4. After all screen questions: sees a "Thank you" completion screen

**Important UX details:**
- Once an option is selected, it is visually highlighted and locked. Show a subtle "Locked in" indicator. No undo.
- The follow-up text input appears inline after selection, not as a separate page
- Progress indicator showing "Question 2 of 5" etc.
- Mobile-responsive — designer may hand their phone/tablet to respondents

### 3. Analytics Dashboard (Designer Side)
For each test, the designer sees:
- **Summary bar:** Total responses, completion rate
- **Per screen question:**
  - Bar chart or pie chart showing vote distribution across options (counts + percentages)
  - List of follow-up reasons grouped by chosen option
  - Highlight the "winning" option
- **Export:** Download all responses as CSV

Keep charts simple — bar charts for vote counts, with percentages labeled. Use a clean, minimal design.

### 4. Shareable Link (Nice-to-Have for MVP)
- Each test gets a unique URL slug (e.g., `/test/abc123`)
- Works when the app is running locally — designer shares their local URL on the same network
- Future iteration: deploy to a cloud host for public links

### 5. Authentication (Nice-to-Have)
- Not required for MVP — single designer using locally
- Structure the code so auth can be added later (e.g., designer_id foreign key on tests, but default to a single user)
- If simple to include: basic email/password login with JWT

## API Design Guidelines
- RESTful endpoints under `/api/v1/`
- Key resources: tests, screen-questions, options, responses
- Use Pydantic models for request/response validation
- CORS configured for Next.js frontend (localhost:3000 ↔ localhost:8000)

## Project Structure
```
abtestingapp/
├── frontend/          # Next.js app
│   ├── app/           # App router pages
│   ├── components/    # Reusable UI components
│   └── lib/           # API client, utilities
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── models/    # SQLAlchemy/SQLModel models
│   │   ├── routes/    # API route handlers
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   ├── media/         # Uploaded images
│   └── main.py        # FastAPI entry point
├── CLAUDE.md
└── README.md
```

## Non-Functional Requirements
- Runs entirely locally — no external services, no cloud dependencies
- SQLite database file stored in `backend/data/`
- Fast startup — designer should be able to `npm run dev` + `uvicorn` and be ready
- Clean, modern UI — use Tailwind defaults, no custom design system needed
- Error handling on both frontend and backend — show user-friendly messages

## What NOT to Build
- No real-time collaboration
- No version history for tests
- No respondent accounts or tracking
- No payment/billing
- No complex statistical analysis (just counts and percentages)
