# Decision Log — DesignPoll

All autonomous decisions made by the Builder during the build pipeline.

---

## [2026-03-31] Decision: Option display randomization
- **Context:** Position bias in A/B tests. First option gets more clicks.
- **Options considered:** Always randomize, never randomize, configurable toggle
- **Chosen:** Default randomized with per-question toggle to disable
- **Reasoning:** Best practice for fair testing; toggle gives designer control when order matters
- **User asked:** No

## [2026-03-31] Decision: Editing active tests
- **Context:** Can designers modify tests that already have responses?
- **Options considered:** Allow all edits, lock everything, lock questions/options only
- **Chosen:** Once active, only allow changing name/description and closing. Questions/options locked.
- **Reasoning:** Editing options after responses exist would corrupt data integrity
- **User asked:** No

## [2026-03-31] Decision: Multiple test retakes
- **Context:** Can the same person retake a test?
- **Options considered:** Block retakes via cookie, allow freely, limit per IP
- **Chosen:** Allow freely — each page load generates a new session_id
- **Reasoning:** Designer wants volume; tracking individuals not needed for MVP
- **User asked:** No

## [2026-03-31] Decision: Image aspect ratio handling
- **Context:** Designers may upload mixed aspect ratio images
- **Options considered:** Enforce uniform size, crop to fit, contain with uniform height
- **Chosen:** Display all options at same height with object-fit: contain, width varies
- **Reasoning:** Fair comparison without cropping important content
- **User asked:** No
