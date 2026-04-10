# Habit Prioritization Script (Local JSON Store)

This script prioritizes your due habits from a local JSON file. It does not call TickTick.

## What it does

- Reads active habits and check-in history from a local JSON store.
- Finds habits due today from each habit's `repeatRule`.
- Calculates completion rate over `lookBackDays`.
- Reorders due habits so lower completion rates are prioritized first.
- Updates habit names with numeric prefixes (for ordered display).
- Records today's completion in the local `checkins` store.
- Samples each due habit trigger time between 06:00 and 12:00 local time.
- Writes ready habit names to enabled due outputs once their sampled trigger time has passed.

## Configuration

Edit [`config.json`](config.json):

```json
{
  "lookBackDays": 21,
  "habitsStoreFile": "./habits_store.json"
}
```

- `lookBackDays`: number of days used when calculating completion rate.
- `habitsStoreFile`: path to your local habit store JSON file.

Relative paths are resolved from the repo root.

## Habit Store Format

The habit store must be a JSON object with this structure:

```json
{
  "habits": [
    {
      "id": "habit-1",
      "name": "Read",
      "goal": 1,
      "repeatRule": "RRULE:FREQ=DAILY;INTERVAL=1",
      "dailyTriggerCount": 1,
      "dueOutputs": {
        "writeToMd": true,
        "desktopNotification": false
      },
      "targetStartDate": "2025-01-01",
      "archivedTime": null,
      "sortOrder": 1
    }
  ],
  "checkins": {
    "habit-1": [
      {
        "id": "habit-1-20260224",
        "habitId": "habit-1",
        "checkinStamp": 20260224,
        "goal": 1,
        "value": 1,
        "status": 2,
        "checkinTime": "2026-02-24T12:00:00.000+0000",
        "opTime": "2026-02-24T12:00:00.000+0000"
      }
    ]
  }
}
```

Notes:
- `habits` must be a list of habit objects with at least `id` and `name`.
- `checkins` must be an object keyed by habit id.
- Habits with `archivedTime` are treated as inactive.
- `dailyTriggerCount` is optional and defaults to `1`. Use `2` for a habit that should trigger twice on each due day.
- `dueOutputs` is optional and defaults to writing to `~/notes/temp index.md` only.
- Set `writeToMd` and `desktopNotification` independently; a habit can use either, both, or neither.

A starter store is included at [`habits_store.json`](habits_store.json).

## Trigger Scheduling

Each run creates or reuses a daily trigger schedule at `.habit_trigger_schedule`.
For each due habit trigger, the script samples a local time from 06:00 through 12:00.
Only triggers whose sampled time has passed are written to their enabled outputs.
Desktop notifications are created with `notify-send` using critical urgency and no expiry.

Run the script repeatedly during that window, for example from cron or another scheduler, if you want habits to appear throughout the morning instead of all at once.

## Usage

```bash
uv run --env-file .env python src/main.py
```

Run in test mode:

```bash
uv run --env-file .env python src/main.py --test
```
