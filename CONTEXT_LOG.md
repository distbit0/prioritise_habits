# Local JSON Habit Store Migration

- Goal: remove the hard dependency on TickTick API and keep habit prioritization functional with local state only.
- Design choice: a single JSON store now holds both active habit definitions (`habits`) and completion history (`checkins`) so scheduling and completion-rate logic can run without network access.
- Trade-off: this removes remote sync behavior entirely; all updates are now local file mutations by design.
- Validation behavior: the script now raises explicit errors for malformed store/config schema instead of silently fabricating missing fields.
- Priority updates: habit name and `sortOrder` updates are now merged back into the local `habits` list by id, preserving non-prioritized habits unchanged.

# Due Habit Outputs

- `dueOutputs` controls delivery channels independently from recurrence: `writeToMd` appends to `~/notes/temp index.md`, while `desktopNotification` sends a persistent `notify-send` notification.
- The daily trigger schedule is shared across output channels and stored in `.habit_trigger_schedule`; completion/check-in is still based on all daily triggers firing, not on a specific output channel.
