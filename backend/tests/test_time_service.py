from datetime import datetime, timezone

from app.services.time_service import is_open_now


def test_is_open_now_true_for_valid_window():
    hours = {
        "sat": [["00:00", "23:59"]],
    }
    now = datetime(2026, 2, 14, 15, 0, 0, tzinfo=timezone.utc)  # Saturday
    assert is_open_now(hours, "America/Chicago", now_utc=now)


def test_is_open_now_false_when_closed_all_day():
    hours = {
        "sat": [],
    }
    now = datetime(2026, 2, 14, 15, 0, 0, tzinfo=timezone.utc)
    assert not is_open_now(hours, "America/Chicago", now_utc=now)
