import json

import pytest

from src.main import apply_checkin_payload, load_habit_store, merge_habit_updates


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
