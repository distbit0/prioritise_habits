import json
from datetime import datetime, timezone

import pytest

from src.main import (
    apply_checkin_payload,
    create_persistent_desktop_notifications,
    get_habit_due_outputs,
    get_completed_habits_after_ready_triggers,
    get_ready_habit_triggers,
    get_ready_triggers_for_due_output,
    load_habit_store,
    merge_habit_updates,
    sample_habit_trigger_time,
)


def write_store(tmp_path, payload):
    store_path = tmp_path / "store.json"
    store_path.write_text(json.dumps(payload))
    return store_path


def test_load_habit_store_accepts_valid_schema(tmp_path):
    store_path = write_store(
        tmp_path,
        {
            "habits": [{"id": "habit-1", "name": "Read", "goal": 1}],
            "checkins": {"habit-1": []},
        },
    )

    store = load_habit_store(store_path)

    assert len(store["habits"]) == 1
    assert store["habits"][0]["id"] == "habit-1"
    assert store["checkins"]["habit-1"] == []


def test_load_habit_store_rejects_habit_without_id(tmp_path):
    store_path = write_store(
        tmp_path,
        {
            "habits": [{"name": "Read"}],
            "checkins": {},
        },
    )

    with pytest.raises(ValueError, match="must include an 'id'"):
        load_habit_store(store_path)


def test_load_habit_store_rejects_invalid_due_output(tmp_path):
    store_path = write_store(
        tmp_path,
        {
            "habits": [
                {
                    "id": "habit-1",
                    "name": "Read",
                    "dueOutputs": {"writeToMd": "yes"},
                }
            ],
            "checkins": {},
        },
    )

    with pytest.raises(ValueError, match="dueOutputs.writeToMd must be a boolean"):
        load_habit_store(store_path)


def test_habit_due_outputs_default_to_md_only():
    habit = {"id": "habit-1", "name": "Read"}

    assert get_habit_due_outputs(habit) == {
        "writeToMd": True,
        "desktopNotification": False,
    }


def test_ready_triggers_are_filtered_by_due_output():
    ready_triggers = [
        {
            "habit": {
                "id": "habit-1",
                "name": "Read",
                "dueOutputs": {"writeToMd": True, "desktopNotification": False},
            },
            "trigger": {},
        },
        {
            "habit": {
                "id": "habit-2",
                "name": "Reply",
                "dueOutputs": {"writeToMd": False, "desktopNotification": True},
            },
            "trigger": {},
        },
    ]

    md_triggers = get_ready_triggers_for_due_output(ready_triggers, "writeToMd")
    notification_triggers = get_ready_triggers_for_due_output(
        ready_triggers, "desktopNotification"
    )

    assert [item["habit"]["id"] for item in md_triggers] == ["habit-1"]
    assert [item["habit"]["id"] for item in notification_triggers] == ["habit-2"]


def test_apply_checkin_payload_add_and_update():
    checkins = {}
    add_payload = {
        "add": [
            {
                "habitId": "habit-1",
                "checkinStamp": 20260224,
                "goal": 1.0,
                "value": 1.0,
                "status": 2,
                "checkinTime": "2026-02-24T10:00:00.000+0000",
                "opTime": "2026-02-24T10:00:00.000+0000",
            }
        ],
        "update": [],
        "delete": [],
    }

    applied_add_count = apply_checkin_payload(checkins, add_payload)

    assert applied_add_count == 1
    assert "habit-1" in checkins
    assert len(checkins["habit-1"]) == 1
    assert checkins["habit-1"][0]["id"] == "habit-1-20260224"
    assert checkins["habit-1"][0]["status"] == 2

    update_payload = {
        "add": [],
        "update": [
            {
                "habitId": "habit-1",
                "checkinStamp": 20260224,
                "id": "habit-1-20260224",
                "goal": 1.0,
                "value": 1.0,
                "status": 1,
                "checkinTime": "2026-02-24T12:00:00.000+0000",
                "opTime": "2026-02-24T12:00:00.000+0000",
            }
        ],
        "delete": [],
    }

    applied_update_count = apply_checkin_payload(checkins, update_payload)

    assert applied_update_count == 1
    assert len(checkins["habit-1"]) == 1
    assert checkins["habit-1"][0]["status"] == 1


def test_merge_habit_updates_replaces_matching_habit():
    all_habits = [
        {"id": "habit-1", "name": "Read", "sortOrder": 10},
        {"id": "habit-2", "name": "Walk", "sortOrder": 20},
    ]
    updated_habits = [{"id": "habit-2", "name": "1. Walk", "sortOrder": 1}]

    merged_habits = merge_habit_updates(all_habits, updated_habits)

    assert merged_habits[0]["name"] == "Read"
    assert merged_habits[1]["name"] == "1. Walk"
    assert merged_habits[1]["sortOrder"] == 1


def test_merge_habit_updates_rejects_unknown_habit_id():
    all_habits = [{"id": "habit-1", "name": "Read"}]
    updated_habits = [{"id": "habit-x", "name": "Invalid"}]

    with pytest.raises(ValueError, match="Cannot update missing habits"):
        merge_habit_updates(all_habits, updated_habits)


def test_ready_habit_triggers_uses_persisted_daily_schedule(tmp_path):
    schedule_path = tmp_path / "schedule.json"
    schedule_path.write_text(
        json.dumps(
            {
                "date": "20260410",
                "triggers": {
                    "habit-1": [
                        {
                            "time": "2026-04-10T06:30:00+00:00",
                            "triggered": False,
                        },
                        {
                            "time": "2026-04-10T11:30:00+00:00",
                            "triggered": False,
                        },
                    ]
                },
            }
        )
    )
    due_habits = [
        {
            "id": "habit-1",
            "name": "Sequence",
            "dailyTriggerCount": 2,
        }
    ]

    ready_triggers, schedule = get_ready_habit_triggers(
        due_habits,
        schedule_path,
        datetime(2026, 4, 10, 9, 0, tzinfo=timezone.utc),
    )

    assert len(ready_triggers) == 1
    assert ready_triggers[0]["habit"]["id"] == "habit-1"
    assert schedule["triggers"]["habit-1"][1]["triggered"] is False


def test_sample_habit_trigger_time_stays_in_morning_window():
    trigger_time = sample_habit_trigger_time(
        datetime(2026, 4, 10, tzinfo=timezone.utc).date(),
        timezone.utc,
    )

    assert trigger_time.hour >= 6
    assert trigger_time.hour <= 12


def test_persistent_desktop_notifications_use_notify_send(monkeypatch):
    calls = []

    def fake_run(command, check):
        calls.append({"command": command, "check": check})

    monkeypatch.setattr("src.main.subprocess.run", fake_run)

    notification_count = create_persistent_desktop_notifications(
        [
            {
                "habit": {"id": "habit-1", "name": "1. Reply to unread msg"},
                "trigger": {},
            }
        ]
    )

    assert notification_count == 1
    assert calls == [
        {
            "command": [
                "notify-send",
                "--app-name=prioritise_habits",
                "--urgency=critical",
                "--expire-time=0",
                "Habit due",
                "Reply to unread msg",
            ],
            "check": True,
        }
    ]


def test_completed_habit_waits_for_all_daily_triggers():
    habit = {"id": "habit-1", "name": "Sequence"}
    schedule = {
        "date": "20260410",
        "triggers": {
            "habit-1": [
                {"time": "2026-04-10T06:30:00+00:00", "triggered": False},
                {"time": "2026-04-10T11:30:00+00:00", "triggered": False},
            ]
        },
    }

    first_completed_habits, first_checkin_times = get_completed_habits_after_ready_triggers(
        [{"habit": habit, "trigger": schedule["triggers"]["habit-1"][0]}],
        schedule,
    )

    assert first_completed_habits == []
    assert first_checkin_times == {}

    second_completed_habits, second_checkin_times = (
        get_completed_habits_after_ready_triggers(
            [{"habit": habit, "trigger": schedule["triggers"]["habit-1"][1]}],
            schedule,
        )
    )

    assert second_completed_habits == [habit]
    assert second_checkin_times["habit-1"] == "2026-04-10T11:30:00.000+0000"
