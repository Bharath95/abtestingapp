# Codex Implementation Plan Review

**Model:** gpt-5.3-codex
**Status:** APPROVED after 4 rounds
**Date:** 2026-03-31
**Plan reviewed:** `/Users/bharath/Documents/abtestingapp/.builder/checkpoints/04-impl-plan.md`
**Requirement:** `/Users/bharath/Documents/abtestingapp/.builder/requirement.md`

---

## Round 1 -- VERDICT: REVISE

Codex identified 8 issues:

### 1. BLOCKER: Plan not self-contained
The plan repeatedly referenced line ranges beyond the file's 2521 lines ("implement exactly as written at lines 3500+", "lines 4266+", "lines 5072+", etc.). Backend routes/services, frontend pages/components, and integration tests could not be reproduced reliably.

**Action taken:** Removed all stale line references. Tasks now describe what to implement via inline specs, endpoint contracts, and acceptance criteria -- no external references.

### 2. HIGH: SQLite foreign key enforcement is fragile
Plan itself stated PRAGMA must run for every new connection, but implementation ran it once in lifespan via one `engine.connect()`. Cascades/constraints could be inconsistent, causing orphan rows/files and incorrect analytics.

**Action taken:** Replaced one-time lifespan PRAGMA execution with a SQLAlchemy `connect` event listener in `database.py` that runs `PRAGMA foreign_keys=ON` and `journal_mode=WAL` on EVERY new connection. Lifespan now only calls `create_db_and_tables()`.

### 3. HIGH: In-memory SQLite test setup is fragile
Test DB used `sqlite://` without `StaticPool`; `create_all()` ran before explicit model import in fixture flow. Could cause flaky/empty schema behavior under TestClient threads.

**Action taken:** Added `poolclass=StaticPool` to test engine. Added explicit model imports (`from app.models import ...`) before `create_all`. Moved FK PRAGMA before `create_all`.

### 4. MEDIUM: Custom follow-up prompt not validated in respondent UX
Requirement specifies custom follow-up prompt per question as core, but respondent acceptance checks only that follow-up input appears -- not that the configured `followup_prompt` text is actually rendered.

**Action taken:** Added explicit acceptance criteria that `FollowUpInput` renders the question-specific `followup_prompt` text (not a hardcoded default). Updated component spec to require `prompt: string` and `required: boolean` props.

### 5. MEDIUM: No automated test coverage for upload mode
Integration test explicitly used URL-mode options only. Upload regressions (validation, replacement, thumbnailing, cleanup) could pass unnoticed.

**Action taken:** Added a new `test_upload.py` file covering: valid upload, invalid MIME type (400), oversized file (400), source-type transitions (upload->url, url->upload), and option delete with file cleanup assertions.

### 6. MEDIUM: URL option lacks server-side validation
Raw `source_url` accepted in form contract; frontend renders URL via iframe/open-link. `javascript:` / `data:` / malformed URL abuse possible. Missing `rel="noopener noreferrer"` on new-tab links.

**Action taken:** Added server-side `validate_source_url()` helper requirement that rejects non-http/https schemes. Added `rel="noopener noreferrer"` requirement on all new-tab links in OptionCard.

### 7. MEDIUM: Image decompression bomb risk
Size check + `Image.verify()` was included but no max-pixel guard. Small compressed payloads could trigger heavy decode/memory pressure when creating thumbnails.

**Action taken:** Added max pixel count check (25 megapixels) after `Image.verify()` passes. File is cleaned up on failure. Updated acceptance criteria.

### 8. LOW: Suggestion to move to contract-first milestones
For each task, include concrete endpoint/schema contracts and minimal acceptance tests in the same file.

**Action taken:** Added a dedicated "Security Considerations" section. All tasks now use self-contained specs with inline contracts.

---

## Round 2 -- VERDICT: REVISE

Codex identified 5 remaining issues:

### 1. BLOCKER: Stale "Section 9" / "approved plan" references still remained
Several tasks still said "as specified in the approved plan (Section 9, Task X)" and `api.ts` still cited `lines 922-3049`.

**Action taken:** Removed ALL remaining "approved plan" / "Section 9" / "Section 4.3" phrasing. Verified with grep -- zero matches remain.

### 2. HIGH: Task 20 reintroduced the old PRAGMA pattern
Task 2's database.py was correctly fixed, but Task 20's "final main.py" code block still had the lifespan PRAGMA execution from the original plan.

**Action taken:** Updated Task 20's final `main.py` to match Task 2 -- lifespan only calls `create_db_and_tables()`, with comment noting PRAGMAs are handled via event listener.

### 3. MEDIUM: Upload delete cleanup test didn't assert file removal
`test_upload.py` step said "delete option and verify 204" but didn't assert that actual files were removed from disk.

**Action taken:** Step 8 now explicitly asserts both original image file and thumbnail file are removed from `media/{test_id}/` using `pathlib.Path.exists()`.

### 4. MEDIUM: No negative test for URL scheme validation
URL validation requirement existed but no test cases for `javascript:`, `data:`, `file:` rejection.

**Action taken:** Added steps 9-11 to `test_upload.py` that create options with `javascript:alert(1)`, `data:text/html,...`, and `file:///etc/passwd`, expecting 400 for each.

### 5. LOW: Test strategy text inconsistent with added test file
References still said `pytest tests/test_workflow.py -v` instead of `pytest tests/ -v`.

**Action taken:** Updated all references to `pytest tests/ -v` consistently.

---

## Round 3 -- VERDICT: REVISE

Codex identified 1 remaining issue:

### 1. HIGH: Test isolation incomplete for filesystem media
`conftest.py` only overrode the DB session but not `MEDIA_DIR`. Upload tests checking on-disk file deletion could touch/delete real `backend/media/` files.

**Action taken:** Added a `test_media_dir` fixture that:
- Creates a per-test temp directory via pytest's `tmp_path`
- Monkeypatches both `app.config.MEDIA_DIR` and `app.services.image_service.MEDIA_DIR` to the temp directory
- Is `autouse=True` so it applies to all tests automatically
- Updated `client_fixture` to depend on `test_media_dir` for correct ordering
- Updated acceptance criteria to include "media writes are isolated from production `backend/media/`"

---

## Round 4 -- VERDICT: APPROVED

Codex confirmed all prior blockers are resolved:

> "Re-review complete. The prior blockers are addressed: no stale external references remain, Task 20 no longer regresses PRAGMA handling, media isolation is now explicit and ordered correctly in test fixtures, upload cleanup is asserted on disk, invalid URL schemes are tested, and test commands are consistent."

---

## Summary of All Changes Applied to the Implementation Plan

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| 1 | Blocker | Stale line references (3500+, 4266+, etc.) | Removed all; tasks use inline specs |
| 2 | Blocker | "Approved plan (Section 9)" references | Removed all; fully self-contained |
| 3 | High | SQLite PRAGMA runs once, not per-connection | SQLAlchemy `connect` event listener in database.py |
| 4 | High | Task 20 re-introduced old PRAGMA pattern | Updated Task 20 main.py to match fixed version |
| 5 | High | In-memory test DB fragile (no StaticPool) | Added StaticPool + explicit model imports |
| 6 | High | Test media not isolated from production | Added monkeypatched `test_media_dir` fixture |
| 7 | Medium | No upload mode test coverage | Added `test_upload.py` with 11 test steps |
| 8 | Medium | URL scheme not validated server-side | Added `validate_source_url()` for http/https only |
| 9 | Medium | No negative URL scheme tests | Added javascript:/data:/file: rejection tests |
| 10 | Medium | Custom followup_prompt not validated in UX | Added explicit acceptance criteria + component props |
| 11 | Medium | Upload delete didn't assert file removal | Added pathlib.Path.exists() assertions |
| 12 | Medium | Decompression bomb risk (no pixel limit) | Added 25MP max pixel check after verify() |
| 13 | Low | Test command inconsistency | Updated all to `pytest tests/ -v` |
| 14 | Low | Missing security section | Added dedicated Security Considerations section |

**The revised implementation plan has been approved by Codex and is ready for implementation.**
