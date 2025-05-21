# Habit Prioritization Script for TickTick

This Python script interacts with the TickTick API to help prioritize daily and weekly habits.

## Features

- **Fetches Data**: Retrieves all habits and their check-in history from your TickTick account.
- **Local Backup**: Saves a JSON copy of all fetched habits to `src/habits.json` (configurable, defaults to `/home/pimania/miscSyncs/habits/habits.json`).
- **Identifies Due Habits**: Determines which habits are scheduled for the current day based on their recurrence rules (daily, weekly) and check-in status.
- **Calculates Completion Rate**: For habits due today, it computes their completion rate based on historical check-ins.
- **Prioritizes Habits**: Sorts the due habits, placing those with lower completion rates first.
- **Updates TickTick**: 
    - Modifies the names of the prioritized habits in TickTick by prepending a numerical priority (e.g., "1. Habit A", "2. Habit B").
    - Updates the `sortOrder` attribute of these habits in TickTick to reflect the new priority.
- **Daily Execution**: The script is intended to run once per day. It creates a `.last_run` file in the `src` directory to track its last execution and avoid re-running on the same day.
- **Test Mode**: Includes a `--test` command-line argument to bypass the daily run check for testing purposes.

## How it Works

The script performs the following steps:

1.  **Initialization**: 
    *   Loads environment variables (specifically the TickTick cookie).
    *   Parses command-line arguments (e.g., `--test`).
2.  **Daily Run Check**: Verifies if the script has already run today by checking the timestamp of `src/.last_run`. If it has and `--test` is not active, it exits.
3.  **API Interaction**:
    *   Fetches all habits from the TickTick API (`/api/v2/habits`).
    *   Saves these habits to a local JSON file.
    *   Fetches check-in data for all habits (`/api/v2/habitCheckins/query`).
4.  **Habit Processing**:
    *   Filters habits to identify those due today using `is_habit_due_on_date` which considers:
        *   Archived status.
        *   `repeatRule` (FREQ=DAILY, FREQ=WEEKLY, BYDAY).
        *   `INTERVAL` for daily habits.
        *   Latest check-in date to determine if a daily habit with an interval is due (e.g., if interval is 2, and last check-in was yesterday, it's not due today).
    *   Calculates the completion rate for each due habit (`calculate_completion_rate`). This involves checking how many times the habit was due versus how many times it was checked in within a defined period (e.g., last 30 occurrences for daily habits, or since creation for weekly).
5.  **Sorting and Updating**:
    *   Sorts the due habits by their completion rate in ascending order (`sort_habits_by_completion_rate`).
    *   Updates the names of these habits by prefixing them with a priority number (e.g., "1. Exercise", "2. Read"). Existing numerical prefixes are removed first.
    *   Sends a batch update request to TickTick (`/api/v2/habits/batch`) to change habit names and their `sortOrder`.
6.  **Finalization**: Updates the `src/.last_run` file timestamp.

## Setup

1.  **Clone the repository (if applicable) or save the script.**
2.  **Install dependencies**:
    ```bash
    uv pip install requests python-dotenv
    ```
3.  **Create a `.env` file** in the `src` directory (or the same directory as `main.py`) with your TickTick cookie:
    ```
    tiktikCookie="your_ticktick_cookie_here"
    ```
    To get your cookie:
    *   Open your browser and log in to TickTick (web version).
    *   Open the developer tools (usually F12).
    *   Go to the "Network" tab.
    *   Find a request to the TickTick API (e.g., refresh the habits page).
    *   Look for the `cookie` header in the request headers and copy its value.
4.  **(Optional) Configure `HABITS_JSON_FILE`**: By default, habits are saved to `/home/pimania/miscSyncs/habits/habits.json`. You can change this path in `src/main.py` if needed.

## Usage

Navigate to the `src` directory (or where `main.py` is located) and run the script:

```bash
uv run python main.py
```

To run in test mode (ignores the daily run check):

```bash
uv run python main.py --test
```

## Key Functions in `src/main.py`

-   `main()`: Orchestrates the entire process.
-   `parse_repeat_rule(rrule_str)`: Parses RRULE strings (e.g., "RRULE:FREQ=DAILY;INTERVAL=2").
-   `byday_to_weekdays(byday_str)`: Converts BYDAY strings (e.g., "MO,TU,WE") to weekday numbers.
-   `parse_date(date_input)`: Parses date strings/integers into `datetime.date` objects.
-   `is_habit_due_on_date(habit, date, checkins, strict=False)`: Core logic to determine if a habit is due on a given date.
-   `get_habits_due_today(list_of_habits, checkins)`: Filters habits to find those due today.
-   `calculate_completion_rate(habit, checkins)`: Computes the completion percentage.
-   `sort_habits_by_completion_rate(habits, checkins)`: Sorts habits based on completion rate.
-   `update_habit_text(habits)`: Prepares updated habit names with priority numbers.
-   `update_habit_sort_order(habits)`: Prepares updates for habit `sortOrder`.
-   `has_run_today()`: Checks if the script has already run today.
-   `update_last_run()`: Updates the timestamp of the last run.
-   `save_habits_json(habits)`: Saves fetched habits to a JSON file.

## Dependencies

-   `requests`: For making HTTP requests to the TickTick API.
-   `python-dotenv`: For loading environment variables from a `.env` file.

## Note on TickTick API

This script uses unofficial TickTick API endpoints. These endpoints could change or break without notice. Use at your own risk. Always back up important data.