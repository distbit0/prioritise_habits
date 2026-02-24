# Habit Prioritization Script (Local JSON Store)

This script prioritizes your due habits from a local JSON file. It does not call TickTick.

## What it does

- Reads active habits and check-in history from a local JSON store.
- Finds habits due today from each habit's `repeatRule`.
- Calculates completion rate over `lookBackDays`.
- Reorders due habits so lower completion rates are prioritized first.
- Updates habit names with numeric prefixes (for ordered display).
- Records today's completion in the local `checkins` store.
- Appends completed habit names to `~/notes/temp index.md` with the existing 3-hour append throttle.

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

A starter store is included at [`habits_store.json`](habits_store.json).

## Usage

```bash
uv run --env-file .env python src/main.py
```

Run in test mode (skip daily run guard):

```bash
uv run --env-file .env python src/main.py --test
```
