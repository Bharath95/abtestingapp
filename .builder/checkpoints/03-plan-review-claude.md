# Plan Review -- DesignPoll A/B Testing App

**Reviewer:** Claude Opus 4.6 (1M context)
**Date:** 2026-03-31
**Plan reviewed:** `.builder/checkpoints/02-plan.md`
**Requirement reviewed:** `.builder/requirement.md`

---

## Critical

- **No rate limiting on the respondent answer endpoint** -- `POST /api/v1/respond/{slug}/answers` has no rate limiting. A malicious actor (or script kiddie on the local network) could flood the test with thousands of fake sessions since `session_id` is client-generated and retakes are unlimited. This would render analytics meaningless. --> Add a simple in-memory rate limiter (e.g., per-IP limit of N answers per minute via `slowapi` or a lightweight middleware). Even for a local-first app, the designer might share the link on a local network or eventually expose it publicly.

- **`session_id` is entirely client-controlled with no server-side validation** -- The `session_id` is a plain UUID string generated client-side with no verification. Anyone can forge arbitrary session IDs via direct API calls, submitting unlimited responses per "session." The unique constraint `(session_id, screen_question_id)` only prevents re-answering with the *same* session_id, but fabricating new ones is trivial. --> For MVP this is an acceptable tradeoff given the local-first scope, but the plan should explicitly document this as a known limitation. Consider adding an optional server-generated session token in a future iteration (e.g., `GET /api/v1/respond/{slug}/session` returns a signed token).

- **Image upload reads entire file into memory before checking size** -- In `save_image()`, the code does `content = await file.read()` and only then checks `len(content) > MAX_IMAGE_SIZE_BYTES`. A 500MB upload would consume 500MB of server memory before being rejected. --> Read the file in chunks. Use `file.read(MAX_IMAGE_SIZE_BYTES + 1)` and check immediately, or stream to disk with a size counter. Alternatively, check `request.headers['content-length']` first as a fast pre-check (though it can be spoofed, it catches honest mistakes).

## Major

- **N+1 query pattern in `list_tests` endpoint** -- The `list_tests` route fetches all tests, then runs two additional COUNT queries per test (question_count and response_count) inside a loop. With 50 tests, that is 100+ database queries per page load. --> Rewrite as a single query using `outerjoin` and `group_by`, or use subqueries in the SELECT. Example: `select(Test, func.count(distinct(ScreenQuestion.id)), func.count(distinct(Response.session_id))).outerjoin(...).group_by(Test.id)`.

- **N+1 query pattern repeated in analytics** -- `compute_analytics` does per-option queries for vote counts and follow-up texts inside nested loops (questions x options). For a test with 10 questions and 5 options each, that is 100+ queries. --> Batch-load all responses for the test in one query, then aggregate in Python. Or use SQL `GROUP BY` with `option_id` to get vote counts in a single query per question.

- **`get_test` and `get_test_for_respondent` have nearly identical nested query logic** -- Both endpoints manually load questions and options with the same nested loop pattern. This is duplicated business logic that will diverge over time. --> Extract a shared helper function like `_build_test_with_questions(test, session)` used by both endpoints.

- **No input sanitization on `followup_text` for XSS** -- Follow-up text from respondents is stored raw and rendered in the analytics dashboard. If a respondent submits `<script>alert('xss')</script>` as follow-up text, it could execute in the designer's browser when viewing analytics. React does escape by default, but the plan renders follow-up text inside curly quotes (`"{f.text}"`) which relies on React's implicit escaping. --> This is likely safe because React auto-escapes JSX expressions, but the plan should explicitly note this reliance. Consider adding server-side sanitization as defense-in-depth (e.g., strip HTML tags on input).

- **The `PATCH /api/v1/options/{option_id}` endpoint treats `multipart/form-data` with all-optional fields ambiguously** -- When `label` is `None` (not sent), the endpoint skips updating it. But with multipart forms, an empty string `""` and absence of the field can be hard to distinguish. FastAPI's `Form(default=None)` may receive an empty string from some clients instead of `None`, which could blank out the label. --> Add explicit validation: `if label is not None and label.strip() == "": raise HTTPException(400, "Label cannot be empty")`.

- **Analytics endpoint accessible for any test status including draft** -- `GET /api/v1/tests/{test_id}/analytics` does not check test status. While not harmful, showing analytics for a draft test with zero responses adds no value and could confuse the designer. --> Consider returning early with an appropriate message for draft tests, or document that this is intentional.

- **No `allow_credentials=True` in CORS config** -- The CORS middleware does not set `allow_credentials`. If the frontend ever needs to send cookies (for future auth), this will break silently. --> Add `allow_credentials=True` to the CORS middleware now to future-proof, or add a comment explaining why it is omitted.

- **`TestDetail` extends `TestPublic` which includes `question_count` and `response_count`, but these are not populated in the `get_test` endpoint** -- The schema `TestDetail` extends `TestPublic` via `Omit<Test, "question_count" | "response_count">` on the TypeScript side, but the Python `TestDetail` extends `TestPublic` directly. `TestPublic` does not include those fields (they are on `TestListItem`), so this actually works in Python. However, the TypeScript `TestDetail` interface does not extend `Test` at all -- it re-declares all fields. This inconsistency between the Python schemas and TypeScript types could cause confusion during implementation. --> Ensure the Python `TestDetail` schema and TypeScript `TestDetail` interface are kept in sync. The current plan has them correctly separated, but a comment explaining the intentional divergence would help.

## Minor

- **`utcnow()` helper function is duplicated across four model files** -- Each model file (`test.py`, `screen_question.py`, `option.py`, `response.py`) defines its own `utcnow()` function. --> Extract to a shared utility, e.g., `app/utils.py`, and import from there.

- **`generate_slug()` uses `secrets.token_urlsafe(8)` which produces 11 characters, but the column is `String(16)`** -- This works fine but the column size implies slugs could be longer. If slug generation logic changes, the mismatch could be confusing. --> Add a comment noting the expected slug length, or use `max_length=12` to match the actual output.

- **`delete_question` does not clean up image files for the question's options** -- When a question is deleted, its options are cascade-deleted in the database, but the plan does not call `delete_image()` for each option's image. The files remain on disk as orphans. --> Before deleting the question, iterate over its options and call `delete_image()` for each one that has an `image_filename`.

- **`delete_test` calls `delete_test_media(test_id)` which uses `shutil.rmtree` -- but the file deletion happens before `session.delete(test)` and `session.commit()`** -- If the database commit fails after files are already deleted, the data becomes inconsistent (DB references files that no longer exist). --> Reorder: delete from database first, commit, then delete files. Or wrap in a try/except that handles partial failures.

- **`ConfirmDialog` does not trap focus or handle keyboard events** -- The modal overlay renders without focus trapping or Escape key support. Screen readers and keyboard users cannot properly interact with it. --> Add `onKeyDown` for Escape, `autoFocus` on the cancel button, and `aria-modal="true"`. For a more robust solution, consider using `<dialog>` element or a headless UI library.

- **The integration test (`test_workflow.py`) uses the production database** -- `setup_module()` calls `drop_all` and `create_all` on the production engine. If the developer runs tests while the app is running, it destroys their data. --> Use a separate test database. Override `DATABASE_URL` in tests to use `:memory:` or a temporary file. This is a common pitfall with SQLModel/SQLAlchemy test setups.

- **`VoteChart` tooltip formatter has a bug** -- The formatter `data.find((d) => d.votes === value)` will match the wrong item if two options have the same vote count. --> Use the `name` parameter or the chart's payload index instead: `formatter={(value, name, props) => [... props.payload.percentage ...]}`.

- **No loading/error states shown to the user when individual API calls fail in the test builder** -- `QuestionEditor` and `OptionEditor` call API functions but only `try/finally` around the saving flag, with no `catch` to display errors. If `createOption` fails, the user sees no feedback. --> Add error state and display error messages in each editor component.

- **The `QuestionView` `useMemo` dependency array uses `question.id` but accesses `question.options`** -- If the options change without the question ID changing (e.g., after adding an option and re-rendering), the memoized shuffle will not update. --> Include `question.options` (or `question.options.length`) in the dependency array.

- **Dashboard page uses Server Component with `fetchTests()` calling `localhost:8000`** -- When running `next build` for production or during SSR, the server-side fetch to `localhost:8000` may fail if the backend is not running on the same machine, or if running inside a container. --> For a local-first MVP this is acceptable, but add a comment noting this limitation. Consider making the dashboard a Client Component or using `try/catch` (which the plan does include).

- **No `HEAD` method allowed in CORS** -- The `allow_methods` list is `["GET", "POST", "PATCH", "DELETE"]`, missing `OPTIONS` (handled implicitly by the middleware) and `HEAD`. Some browser preflight checks may need `OPTIONS` support. --> FastAPI's CORS middleware handles `OPTIONS` automatically, so this is fine. But consider adding `PUT` to the allow list for future extensibility, or just use `["*"]` for development simplicity.

- **Image thumbnails are always generated but never explicitly served to the respondent** -- The plan mentions `thumb_` prefixed files and a `get_thumbnail_url()` function, but the respondent `OptionCard` component uses `option.image_url` (the full-size image URL), not the thumbnail. --> Either use thumbnail URLs in the respondent flow for faster loading (which was the stated purpose), or remove thumbnail generation to simplify. Currently the thumbnails are created but wasted.

- **CSV export uses `StreamingResponse` wrapping `io.StringIO` -- but the entire CSV is generated in memory first** -- `generate_csv()` builds the complete CSV string, then `StreamingResponse` wraps it. This is not truly streaming. For large datasets, this could consume significant memory. --> For MVP scale this is fine. For future improvement, refactor `generate_csv` to be a generator that yields rows.

---

## What's Good

- **Clean separation of concerns** -- The plan follows a well-structured layered architecture: models, schemas, routes, services. Each layer has a clear responsibility. The file structure is logical and will be easy to navigate.

- **Thoughtful test lifecycle state machine** -- The `draft -> active -> closed` state transitions with clear rules about what can be modified in each state is well-designed. The validation rules (must have questions with 2+ options to activate) prevent broken tests from going live.

- **Smart decision on option randomization** -- Defaulting to randomized options with a per-question toggle is a genuinely useful feature for reducing position bias. This shows domain awareness of A/B testing best practices.

- **Good use of existing ecosystem** -- The tech stack choices are pragmatic: SQLModel eliminates schema duplication, FastAPI auto-generates API docs, Tailwind avoids CSS complexity for a frontend novice. No unnecessary dependencies.

- **Excellent API design** -- RESTful conventions are followed consistently. The respondent-facing endpoints (`/api/v1/respond/{slug}`) are cleanly separated from the designer CRUD endpoints. Status codes (201, 204, 400, 403, 404, 409) are used correctly and meaningfully.

- **Comprehensive integration test** -- Task 10's `test_workflow.py` covers the complete happy path and key error cases (duplicate submission, modification of active test, closed test rejection). This provides good confidence before moving to the frontend.

- **Lock-in UX is well-specified** -- The respondent flow's state machine (intro -> question -> done) with explicit `isLocked` state prevents accidental changes. The requirement for "no undo" on selection is clearly implemented.

- **Cascade delete rules are well-thought-out** -- The cascade chain from Test -> ScreenQuestion -> Option/Response with corresponding file cleanup shows attention to data consistency.

- **Progressive build order** -- The 20-task, 4-phase implementation plan is ordered so each phase produces testable, working software. Backend-first approach means the API can be verified via Swagger before any frontend work begins.

- **Frontend type safety** -- TypeScript interfaces mirror the API response shapes exactly, and the `apiFetch<T>` generic function provides type-safe API calls throughout.

- **Route groups for respondent/designer separation** -- Using Next.js route groups `(designer)` to conditionally include the Navbar is the idiomatic App Router approach and avoids complex conditional rendering logic.

---

## Summary

The plan is thorough, well-organized, and demonstrates strong architectural judgment for an MVP-scope application. The tech stack is appropriate, the API design is clean, and the implementation sequence is logical.

The most pressing issues are:

1. **The image upload memory consumption** (Critical) -- should be fixed before implementation.
2. **N+1 query patterns** (Major) -- will not matter at MVP scale but should be addressed early to avoid technical debt.
3. **Orphaned image files on question deletion** (Minor) -- straightforward fix, easy to miss during implementation.
4. **Integration test using production database** (Minor) -- should be fixed before Task 10 to avoid data loss.

None of the issues identified require fundamental architectural changes. The plan is ready for implementation with the critical and major items addressed inline during the build.
