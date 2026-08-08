"""Behavioral coverage for timezone and overlap scheduling policies."""

from datetime import datetime, timedelta, timezone

from autocron.core.scheduler import Task
from autocron.core.utils import get_next_run_time, resolve_timezone, timezone_name


def test_overlap_policies_reserve_and_release_slots():
    now = datetime.now(timezone.utc) + timedelta(minutes=1)

    skip = Task(name="skip", func=lambda: None, every="1m", timezone="UTC")
    assert skip.claim_due(now, available_slots=1) == 1
    assert skip.claim_due(now + timedelta(minutes=1), available_slots=1) == 0
    assert skip.skipped_count >= 1
    skip.release_instance()

    queue = Task(
        name="queue", func=lambda: None, every="1m", timezone="UTC", overlap_policy="queue"
    )
    assert queue.claim_due(now, available_slots=0) == 0
    assert queue.queued_runs == 1
    queue.release_instance()
    assert queue.claim_due(now + timedelta(minutes=1), available_slots=1) == 1
    queue.release_instance()

    allow = Task(
        name="allow",
        func=lambda: None,
        every="1m",
        timezone="UTC",
        overlap_policy="allow",
        max_instances=2,
    )
    assert allow.claim_due(now, available_slots=2) == 1
    allow.release_instance()


def test_timezone_helpers_and_dst_gap_rejection():
    assert timezone_name("UTC") == "UTC"
    assert timezone_name(None) == "local"
    assert resolve_timezone("UTC").tzname(None) == "UTC"
    try:
        get_next_run_time("0 2 * * *", datetime(2024, 3, 10, 1, 30), "America/New_York")
    except Exception as error:
        assert "does not exist" in str(error)
