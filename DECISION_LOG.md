# Decision Log

## 2026-02-18
- Enforced a global notes-append throttle for `temp index.md`: append at most one new habit line every 3 hours, tracked via `.last_notes_append`.
- Stopped rewriting/removing existing note lines during append; now only appends genuinely new habit lines to avoid batch inserts.
