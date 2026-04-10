# Decision Log

## 2026-02-18
- Enforced a global notes-append throttle for `temp index.md`: append at most one new habit line every 3 hours, tracked via `.last_notes_append`.
- Stopped rewriting/removing existing note lines during append; now only appends genuinely new habit lines to avoid batch inserts.
- Added persistent queueing in `.pending_notes_habits` so all eligible habits are eventually appended one-by-one every 3 hours instead of dropping extras.

## 2026-04-10
- Replaced the notes append throttle/queue with a persisted daily trigger schedule. Each due habit trigger gets a random local time from 06:00 through 12:00, and notes are appended only after that trigger time passes.
- Added `dailyTriggerCount` for habits that need multiple note triggers per due day without changing the meaning of existing numeric `goal` habits.
