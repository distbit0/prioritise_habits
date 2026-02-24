import argparse
import json
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from loguru import logger

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"
LAST_RUN_FILE = PROJECT_ROOT / ".last_run"
LAST_NOTES_APPEND_FILE = PROJECT_ROOT / ".last_notes_append"
PENDING_NOTES_HABITS_FILE = PROJECT_ROOT / ".pending_notes_habits"
NOTES_FILE = pathlib.Path("/home/pimania/notes/temp index.md")
NOTES_APPEND_INTERVAL = timedelta(hours=3)

# Log to stdout + file with rotation
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("app.log", rotation="30 KB", retention=5, level="INFO")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Prioritize habits from local JSON")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (skip has_run_today check)",
    )
    return parser.parse_args()


def load_config():
    with open(CONFIG_FILE, "r") as config_file:
        config = json.load(config_file)

    if "lookBackDays" not in config:
        raise KeyError("Missing required config key: lookBackDays")
    if "habitsStoreFile" not in config:
        raise KeyError("Missing required config key: habitsStoreFile")
    return config


def get_habit_store_path(config):
    store_path = pathlib.Path(config["habitsStoreFile"]).expanduser()
    if not store_path.is_absolute():
        store_path = (PROJECT_ROOT / store_path).resolve()
    return store_path


def load_habit_store(store_path):
    with open(store_path, "r") as store_file:
        store = json.load(store_file)

    if not isinstance(store, dict):
        raise ValueError("Habit store must be a JSON object with habits and checkins")

    habits = store.get("habits")
    checkins = store.get("checkins")
    if not isinstance(habits, list):
        raise ValueError("Habit store field 'habits' must be a list")
    if not isinstance(checkins, dict):
        raise ValueError("Habit store field 'checkins' must be an object")

    for habit in habits:
        if not isinstance(habit, dict):
            raise ValueError("Each habit must be a JSON object")
        if "id" not in habit:
            raise ValueError("Each habit must include an 'id'")
        if "name" not in habit:
            raise ValueError("Each habit must include a 'name'")

    for habit_id, habit_checkins in checkins.items():
        if not isinstance(habit_checkins, list):
            raise ValueError(f"Checkins for habit '{habit_id}' must be a list")

    return {"habits": habits, "checkins": checkins}


def save_habit_store(store_path, habits, checkins):
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with open(store_path, "w") as store_file:
        json.dump({"habits": habits, "checkins": checkins}, store_file, indent=2)
    logger.info(f"Habit store saved to {store_path}")


def parse_repeat_rule(rrule_str):
    """
    Parses an RRULE string into a dictionary.

    :param rrule_str: RRULE string (e.g., "RRULE:FREQ=DAILY;INTERVAL=20")
    :return: Dictionary of RRULE components.
    """
    rrule = {}
    if rrule_str.startswith("RRULE:"):
        rrule_str = rrule_str[len("RRULE:") :]
    parts = rrule_str.split(";")
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            rrule[key] = value
    return rrule


def byday_to_weekdays(byday_str):
    """
    Converts BYDAY values to Python weekday numbers.

    :param byday_str: String of BYDAY values (e.g., "SU,MO,TU,WE,TH,FR,SA")
    :return: List of integers representing weekdays (0=Monday, 6=Sunday)
    """
    day_mapping = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
    days = byday_str.split(",")
    weekdays = [day_mapping[day] for day in days if day in day_mapping]
    return weekdays


def parse_date(date_input):
    """
    Parses a date from various formats to a datetime.date object.

    :param date_input: Integer in YYYYMMDD or string in ISO format.
    :return: datetime.date object.
    """
    if isinstance(date_input, int):
        return datetime.strptime(str(date_input), "%Y%m%d").date()
    if isinstance(date_input, str):
        try:
            return datetime.strptime(date_input, "%Y-%m-%dT%H:%M:%S.%f%z").date()
        except ValueError:
            try:
                return datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError as error:
                raise ValueError(f"Unrecognized date format: {date_input}") from error
    raise TypeError(f"Unsupported date input type: {type(date_input)}")


def get_habit_checkins(checkins, habit_id):
    return checkins.get(str(habit_id), [])


def is_habit_due_on_date(habit, date, checkins, strict=False):
    """
    Determines if a habit is due on a specific date.

    :param habit: Habit dictionary.
    :param date: datetime.date object to check.
    :param checkins: Dictionary mapping habit IDs to lists of checkin dictionaries.
    :param strict: Boolean, if True, only return True for DAILY habits on the exact due date.
    :return: Boolean indicating if the habit is due on the given date.
    """
    if habit.get("archivedTime"):
        return False

    repeat_rule = habit.get("repeatRule", "")
    if not repeat_rule:
        return False

    rrule = parse_repeat_rule(repeat_rule)
    freq = rrule.get("FREQ", "").upper()

    if freq == "WEEKLY":
        byday = rrule.get("BYDAY", "")
        if not byday:
            return False
        weekdays = byday_to_weekdays(byday)
        return date.weekday() in weekdays

    if freq == "DAILY":
        interval = int(rrule.get("INTERVAL", "1"))
        habit_checkins = get_habit_checkins(checkins, habit.get("id"))
        latest_checkin_date = None
        for checkin in habit_checkins:
            checkin_stamp = checkin.get("checkinStamp")
            if checkin_stamp is None:
                continue
            try:
                checkin_date = parse_date(checkin_stamp)
            except (ValueError, TypeError):
                continue

            if latest_checkin_date is None or checkin_date > latest_checkin_date:
                latest_checkin_date = checkin_date

        if latest_checkin_date:
            days_since_last_checkin = (date - latest_checkin_date).days
            if strict:
                return (
                    days_since_last_checkin % interval == 0
                    and days_since_last_checkin >= interval
                )
            return days_since_last_checkin >= interval

        target_start = habit.get("targetStartDate")
        if target_start:
            try:
                target_start_date = parse_date(target_start)
            except (ValueError, TypeError):
                return False

            if strict:
                return (
                    (target_start_date - date).days % interval == 0
                    and target_start_date <= date
                )
            return target_start_date <= date
        return True

    return False


def get_habits_due_today(list_of_habits, checkins):
    """
    Returns a list of habits due today based on the provided habits and checkins.

    :param list_of_habits: List of habit dictionaries.
    :param checkins: Dictionary mapping habit IDs to lists of checkin dictionaries.
    :return: List of habit dictionaries that are due today.
    """
    today = datetime.now().astimezone().date()
    return [
        habit
        for habit in list_of_habits
        if is_habit_due_on_date(habit, today, checkins)
    ]


def calculate_completion_rate(habit, checkins, look_back_days):
    """
    Calculates the completion rate for a habit.

    :param habit: Habit dictionary.
    :param checkins: Dictionary mapping habit IDs to lists of checkin dictionaries.
    :param look_back_days: Number of days to look back for completion history.
    :return: Float representing the completion rate (0 to 1).
    """
    habit_checkins = get_habit_checkins(checkins, habit.get("id"))
    if not habit_checkins:
        return 0

    today = datetime.now().astimezone().date()
    start_date = today - timedelta(days=look_back_days)
    recent_checkins = [
        checkin
        for checkin in habit_checkins
        if parse_date(checkin["checkinStamp"]) >= start_date
    ]

    total_days = (today - start_date).days + 1
    scheduled_count = sum(
        1
        for day in range(total_days)
        if is_habit_due_on_date(
            habit, start_date + timedelta(days=day), checkins, strict=False
        )
    )
    completed_count = len(recent_checkins) + 0.1

    completion_rate = completed_count / scheduled_count if scheduled_count > 0 else 0
    logger.info(
        f"Habit: {habit['name'][:10]}, Rate: {completion_rate}, "
        f"Scheduled: {scheduled_count}, Completed: {completed_count}"
    )
    return completion_rate


def sort_habits_by_completion_rate(habits, checkins, look_back_days):
    """
    Sorts habits based on their completion rate.

    :param habits: List of habit dictionaries.
    :param checkins: Dictionary mapping habit IDs to lists of checkin dictionaries.
    :param look_back_days: Number of days to look back for completion history.
    :return: List of habits sorted by completion rate (ascending).
    """

    def get_sort_key(habit):
        name = habit["name"]
        if "@" in name:
            return (-1, 0)
        match = re.search(r"\^(\d*)", name)
        if match:
            number = match.group(1)
            if number == "":
                return (0, 1)
            return (0, int(number))
        return (1, 0)

    sorted_by_completion = sorted(
        habits, key=lambda habit: calculate_completion_rate(habit, checkins, look_back_days)
    )
    return sorted(sorted_by_completion, key=get_sort_key)


def update_habit_text(habits):
    always_top_habits = [habit.copy() for habit in habits if "@" in habit["name"]]
    habits_to_number = [habit for habit in habits if "@" not in habit["name"]]

    numbered_habits = []
    for priority, habit in enumerate(habits_to_number, start=1):
        old_name = habit["name"]
        new_name = f"{priority}. {remove_existing_prefix(old_name)}"
        logger.info(f"Updated: {old_name} -> {new_name}")
        habit_update = habit.copy()
        habit_update["name"] = new_name
        numbered_habits.append(habit_update)

    return always_top_habits + numbered_habits


def update_habit_sort_order(habits):
    updated_habits = []
    for habit in habits:
        habit_update = habit.copy()
        priority_match = re.match(r"^(\d+)\.\s", habit["name"])
        if priority_match:
            priority = int(priority_match.group(1))
        else:
            priority = (len(updated_habits) + 1) * 1000000000
        habit_update["sortOrder"] = priority
        updated_habits.append(habit_update)
    return updated_habits


def merge_habit_updates(all_habits, updated_habits):
    updates_by_id = {str(habit["id"]): habit for habit in updated_habits}
    existing_ids = {str(habit["id"]) for habit in all_habits}
    unknown_ids = set(updates_by_id).difference(existing_ids)
    if unknown_ids:
        raise ValueError(f"Cannot update missing habits: {sorted(unknown_ids)}")

    merged_habits = []
    for habit in all_habits:
        habit_id = str(habit["id"])
        if habit_id not in updates_by_id:
            merged_habits.append(habit)
            continue
        merged_habit = habit.copy()
        merged_habit.update(updates_by_id[habit_id])
        merged_habits.append(merged_habit)
    return merged_habits


def remove_existing_prefix(name):
    return re.sub(r"^\d+\.\s*", "", name)


def has_run_today():
    if not LAST_RUN_FILE.exists():
        return False
    current_date = datetime.now().date()
    last_run = datetime.fromtimestamp(LAST_RUN_FILE.stat().st_mtime)
    return current_date == last_run.date()


def update_last_run():
    LAST_RUN_FILE.touch()


def get_checkin_entry_for_date(habit_id, checkins, checkin_stamp):
    habit_checkins = get_habit_checkins(checkins, habit_id)
    for checkin in habit_checkins:
        if checkin.get("checkinStamp") == checkin_stamp:
            return checkin
    return None


def build_checkin_payload(due_habits, checkins, checkin_stamp, checkin_time):
    payload = {"add": [], "update": [], "delete": []}
    for habit in due_habits:
        habit_id = habit.get("id")
        habit_goal = habit.get("goal")
        if habit_goal is None:
            logger.error(f"Missing goal for habit: {habit.get('name')} ({habit_id})")
            continue

        try:
            habit_goal_value = float(habit_goal)
        except (TypeError, ValueError):
            logger.error(
                f"Invalid goal for habit: {habit.get('name')} ({habit_id}) -> {habit_goal}"
            )
            continue

        existing_checkin = get_checkin_entry_for_date(habit_id, checkins, checkin_stamp)
        if existing_checkin and existing_checkin.get("status") == 2:
            continue

        entry = {
            "habitId": habit_id,
            "checkinStamp": checkin_stamp,
            "goal": habit_goal_value,
            "value": habit_goal_value,
            "status": 2,
            "checkinTime": checkin_time,
            "opTime": checkin_time,
        }

        if existing_checkin and existing_checkin.get("id"):
            entry["id"] = existing_checkin["id"]
            payload["update"].append(entry)
        else:
            payload["add"].append(entry)

    return payload


def upsert_checkin_entry(habit_checkins, checkin_entry):
    entry_id = checkin_entry.get("id")
    if entry_id:
        for index, existing in enumerate(habit_checkins):
            if existing.get("id") == entry_id:
                merged_entry = existing.copy()
                merged_entry.update(checkin_entry)
                habit_checkins[index] = merged_entry
                return

    entry_stamp = checkin_entry.get("checkinStamp")
    for index, existing in enumerate(habit_checkins):
        if existing.get("checkinStamp") == entry_stamp:
            merged_entry = existing.copy()
            merged_entry.update(checkin_entry)
            habit_checkins[index] = merged_entry
            return

    new_entry = checkin_entry.copy()
    if "id" not in new_entry:
        new_entry["id"] = f"{new_entry['habitId']}-{new_entry['checkinStamp']}"
    habit_checkins.append(new_entry)


def apply_checkin_payload(checkins, payload):
    if not payload["add"] and not payload["update"]:
        return 0

    applied_count = 0
    for checkin_entry in payload["add"] + payload["update"]:
        habit_id = checkin_entry.get("habitId")
        if habit_id is None:
            logger.error(f"Skipping checkin entry without habitId: {checkin_entry}")
            continue

        habit_key = str(habit_id)
        habit_checkins = checkins.setdefault(habit_key, [])
        if not isinstance(habit_checkins, list):
            raise ValueError(f"Checkins bucket for habit '{habit_key}' is not a list")

        upsert_checkin_entry(habit_checkins, checkin_entry)
        applied_count += 1
    return applied_count


def append_completed_habits(notes_path, habits):
    notes_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_habit_lines = [
        remove_existing_prefix(habit.get("name", "")).strip().lower()
        for habit in habits
    ]
    candidate_habit_lines = []
    for line in normalized_habit_lines:
        if line and line not in candidate_habit_lines:
            candidate_habit_lines.append(line)

    existing_lines = []
    if notes_path.exists():
        with open(notes_path, "r") as notes_file:
            existing_lines = notes_file.readlines()

    existing_line_set = {line.strip() for line in existing_lines if line.strip()}
    pending_habit_lines = []
    if PENDING_NOTES_HABITS_FILE.exists():
        with open(PENDING_NOTES_HABITS_FILE, "r") as pending_file:
            pending_habit_lines = json.load(pending_file)

    merged_habit_lines = []
    for line in pending_habit_lines + candidate_habit_lines:
        if line not in merged_habit_lines and line not in existing_line_set:
            merged_habit_lines.append(line)

    if not merged_habit_lines:
        if PENDING_NOTES_HABITS_FILE.exists():
            PENDING_NOTES_HABITS_FILE.unlink()
        logger.info(f"No pending habit lines to append to {notes_path}")
        return

    now = datetime.now(timezone.utc)
    if LAST_NOTES_APPEND_FILE.exists():
        last_append = datetime.fromtimestamp(
            LAST_NOTES_APPEND_FILE.stat().st_mtime, timezone.utc
        )
        next_append_time = last_append + NOTES_APPEND_INTERVAL
        if now < next_append_time:
            logger.info(
                f"Skipping notes append until {next_append_time.isoformat()} (UTC)"
            )
            with open(PENDING_NOTES_HABITS_FILE, "w") as pending_file:
                json.dump(merged_habit_lines, pending_file)
            return

    next_habit_line = merged_habit_lines[0]
    with open(notes_path, "a") as notes_file:
        notes_file.write(f"\n\n{next_habit_line}")
        notes_file.write("\n")
    LAST_NOTES_APPEND_FILE.touch()
    remaining_habit_lines = merged_habit_lines[1:]
    if remaining_habit_lines:
        with open(PENDING_NOTES_HABITS_FILE, "w") as pending_file:
            json.dump(remaining_habit_lines, pending_file)
    elif PENDING_NOTES_HABITS_FILE.exists():
        PENDING_NOTES_HABITS_FILE.unlink()
    logger.info(f"Appended one new habit line to {notes_path}: {next_habit_line}")


def main(test_mode=None):
    args = parse_arguments() if test_mode is None else None
    run_in_test_mode = args.test if args else test_mode
    if not run_in_test_mode and has_run_today():
        logger.info("Script has already run today. Exiting.")
        return

    try:
        config = load_config()
        store_path = get_habit_store_path(config)
        store = load_habit_store(store_path)
        all_habits = store["habits"]
        checkins = store["checkins"]
        due_habits_today = get_habits_due_today(all_habits, checkins)

        if due_habits_today:
            logger.info(f"Found {len(due_habits_today)} long-term habits due today.")

            today = datetime.now().astimezone().date()
            checkin_stamp = int(today.strftime("%Y%m%d"))
            checkin_time = (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ".000+0000"
            )
            payload = build_checkin_payload(
                due_habits_today, checkins, checkin_stamp, checkin_time
            )
            completed_habit_ids = {
                entry["habitId"] for entry in payload["add"] + payload["update"]
            }
            completed_habits = [
                habit
                for habit in due_habits_today
                if habit.get("id") in completed_habit_ids
            ]

            applied_checkins = apply_checkin_payload(checkins, payload)
            append_completed_habits(NOTES_FILE, completed_habits)
            logger.info(
                f"Marked {len(completed_habits)} habits as completed, "
                f"applied {applied_checkins} checkins, and appended notes."
            )

            sorted_habits = sort_habits_by_completion_rate(
                due_habits_today, checkins, config["lookBackDays"]
            )
            sorted_habits = update_habit_text(sorted_habits)
            sorted_habits = update_habit_sort_order(sorted_habits)
            all_habits = merge_habit_updates(all_habits, sorted_habits)
            save_habit_store(store_path, all_habits, checkins)

            update_last_run()
            logger.info("Script execution completed and last run time updated.")
        else:
            logger.info("No long-term habits due today.")
            append_completed_habits(NOTES_FILE, [])
    except FileNotFoundError as error:
        logger.error(f"Missing required file: {error}")
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as error:
        logger.error(f"Failed to process local habit store/config: {error}")


if __name__ == "__main__":
    main()
