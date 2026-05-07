# Local JSON Habit Store Migration

- Goal: remove the hard dependency on TickTick API and keep habit prioritization functional with local state only.
- Design choice: archived habit definitions and completion history stay in `habits_store.json`; editable active/non-archived habit definitions live in `active_habits.json`.
- Active habits are written as full JSON habit records with commonly edited fields ordered first. This preserves metadata while making normal habit edits less buried in TickTick-derived fields.
- Trade-off: this removes remote sync behavior entirely; all updates are now local file mutations by design.
- Validation behavior: the script now raises explicit errors for malformed store/config schema instead of silently fabricating missing fields.
- Priority updates: habit name and `sortOrder` updates are now merged back into the local `habits` list by id, preserving non-prioritized habits unchanged.
- Migration finding: active habit id `7048cbd2aceb8119e1cf1001` was duplicated with identical JSON records, which made id-based updates ambiguous. The redundant copy was removed.

# Due Habit Outputs

- `dueOutputs` controls delivery channels independently from recurrence: `writeToMd` appends to `~/notes/temp index.md`, while `desktopNotification` sends a persistent `notify-send` notification.
- The daily trigger schedule is shared across output channels and stored in `.habit_trigger_schedule`; completion/check-in is still based on all daily triggers firing, not on a specific output channel.
