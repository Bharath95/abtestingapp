# Codex Plan Review — DesignPoll A/B Testing App

**Reviewer:** OpenAI Codex (gpt-5.3-codex)
**Reviewed Plan:** `.builder/checkpoints/02-plan.md`
**Requirement:** `.builder/requirement.md`
**Date:** 2026-03-31
**Session ID:** `019d40bb-7da4-7ce3-8282-aa3622eafc25`

---

## VERDICT: APPROVED (after 5 rounds)

---

## Round 1 — REVISE

Codex identified 10 issues across correctness, data loss risk, security, and UX:

### Findings

1. **Critical: URL options dropped from scope.** Requirement says each option supports "image upload OR URL", but plan was upload-only. Action: add `source_type` + `source_url` support end-to-end.

2. **Critical: Completion rate not implemented.** Requirement asks for "Total responses, completion rate" in the summary bar. Plan analytics only exposed `total_sessions` and `total_answers`. Action: define completion metric and add to backend + frontend.

3. **High: 2-5 options rule not enforced.** Requirement says 2-5 options per question. Plan only enforced minimum 2 at activation; no max=5 check. Action: enforce `2 <= options <= 5` in backend and disable "Add Option" in UI at 5.

4. **High: Image replacement deletes old file before new save succeeds.** Data loss risk if new save fails. Action: save new image first, update DB, delete old image post-commit.

5. **High: Test media deleted before DB commit.** Filesystem/DB consistency risk. Action: commit DB delete first, then remove media folder.

6. **High: File validation can accept spoofed non-images.** Validation relied only on MIME header; Pillow failure silently copied invalid file. Action: add `Image.verify()`, reject invalid files.

7. **Medium: Mobile responsiveness broken.** Forced 3-column grid on 3 options and fixed 400px image height not mobile-friendly. Action: use responsive columns and adaptive image heights.

8. **Medium: Chart tooltip percentage wrong on ties.** Tooltip matched by vote value, not option identity. Action: use Recharts payload index.

9. **Medium: CSV injection not handled.** User text exported raw to CSV. Action: sanitize cells starting with `=`, `+`, `-`, `@`.

10. **Medium: Duplicate-answer race condition.** Check-then-insert without IntegrityError handling. Action: catch `IntegrityError` on commit and return 409.

### Revisions Applied

- Added `source_type` and `source_url` fields to Option model, schema, TypeScript types
- Added `completed_sessions`, `completion_rate` to AnalyticsResponse and SummaryStats
- Added max 5 options backend check
- Fixed image replacement order (save new first, delete old post-commit)
- Fixed test media deletion order (DB commit first, then filesystem)
- Added `Image.verify()` validation, reject invalid files
- Fixed grid to responsive columns (`grid-cols-1 sm:grid-cols-2`)
- Fixed chart tooltip to use `props.payload.percentage`
- Added `sanitize_csv_cell()` for CSV export
- Added `IntegrityError` catch for duplicate submissions

---

## Round 2 — REVISE

Codex found 4 remaining issues after Round 1 revisions:

### Findings

1. **Critical: URL support still incomplete end-to-end.** API contracts, routes, serializers, and builder UI not wired for `source_type`/`source_url`. Requirement expected iframe/screenshot preview, not just clickable links.

2. **Critical: OptionCard props type-level break.** `OptionCard` required `sourceType` and `sourceUrl` props but `QuestionView` did not pass them.

3. **High: Frontend max 5 options not enforced in UI.** Add-option editor always rendered regardless of count.

4. **Medium: CSV injection partial.** `session_id` column not sanitized.

### Revisions Applied

- Wired `source_type` + `source_url` through all serializers (tests.py, questions.py, respond.py, options.py)
- Added radio toggle in OptionEditor between "Image Upload" and "URL" modes
- Added sandboxed iframe preview for URL options in OptionCard
- Fixed QuestionView to pass `sourceType` and `sourceUrl` to OptionCard
- Conditionally render add-option editor only when `options.length < 5`
- Applied `sanitize_csv_cell()` to `session_id` column

---

## Round 3 — REVISE

Codex found 3 remaining issues:

### Findings

1. **Critical: Upload mode does not require an image file.** Options could be created in upload mode without any image, violating the "image upload OR URL" invariant.

2. **High: Source-type transitions leave stale data.** Switching from upload to URL didn't clear/delete old image; switching from URL to upload didn't clear `source_url`.

3. **Medium: Iframe absorbs clicks.** In unlocked state, `pointer-events: auto` on iframe intercepted clicks meant for option selection.

### Revisions Applied

- Backend returns 400 if `source_type=upload` but no image file provided
- Frontend disables "Add Option" when upload mode with no file selected
- Full source-type transition logic: switching to URL deletes old image post-commit; switching to upload requires image and clears `source_url`
- Iframe `pointer-events: none` unconditionally; "Open in new tab" link available separately

---

## Round 4 — REVISE

Codex found 2 remaining issues:

### Findings

1. **High: Integration test inconsistent with updated API.** Test created options "without images" but API now requires image for upload mode.

2. **Medium: Documentation section stale.** Image Handling Strategy section still referenced old FormData fields without `source_type`.

### Revisions Applied

- Integration test updated to use `source_type=url` with `source_url` for option creation
- Added assertions on `source_type` and `source_url` in test response
- Image Handling Strategy documentation updated to cover both upload and URL modes

---

## Round 5 — APPROVED

No blocking findings. The plan is now aligned and internally consistent across all layers:

- Integration test matches the API contract
- Image Handling Strategy documents both upload and URL modes
- All serializers wire `source_type`/`source_url` correctly
- All invariants enforced (image required for upload, URL required for URL mode)
- Source-type transitions clean up stale data
- Mobile responsiveness addressed
- Security concerns (CSV injection, image validation, race conditions) addressed

### Residual Non-Blocking Risk

Some external sites may refuse iframe embedding due to `X-Frame-Options` or CSP headers. The "Open in new tab" fallback link mitigates this. Consider adding user-facing messaging when iframe load fails in a future iteration.

---

## Summary of All Changes Made During Review

| # | Category | Issue | Resolution |
|---|----------|-------|------------|
| 1 | Correctness | URL options missing | Added `source_type`/`source_url` end-to-end |
| 2 | Correctness | Completion rate missing | Added `completed_sessions`/`completion_rate` |
| 3 | Correctness | Max 5 options not enforced | Backend check + frontend conditional render |
| 4 | Data Loss | Image replacement order | Save new first, delete old post-commit |
| 5 | Data Loss | Media deleted before DB commit | DB commit first, then filesystem |
| 6 | Security | Spoofed image files accepted | Added `Image.verify()` validation |
| 7 | UX | Mobile responsiveness broken | Responsive grid + adaptive image heights |
| 8 | Correctness | Chart tooltip wrong on ties | Use payload index for percentage |
| 9 | Security | CSV injection | Sanitize all string columns |
| 10 | Integrity | Duplicate-answer race | Catch `IntegrityError`, return 409 |
| 11 | Correctness | OptionCard props break | QuestionView passes all required props |
| 12 | Correctness | Upload mode allows no image | Backend 400 + frontend disable |
| 13 | Data Integrity | Source-type transitions stale data | Clear/delete opposite source on switch |
| 14 | UX | Iframe absorbs clicks | `pointer-events: none` unconditionally |
| 15 | Testing | Integration test inconsistent | Updated to use URL options |
| 16 | Documentation | Stale image handling docs | Updated for both source types |

---

*Reviewed by OpenAI Codex (gpt-5.3-codex) via codex-review skill. 5 rounds, 513,810 tokens consumed.*
