from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from claim_tii_parser_family import claim_next_group, update_claim
from tii_workflow_guard import (
    INTEGRATION_LOCK_TOKEN_ENV,
    ExclusiveFileLock,
    IntegrationLock,
    WorkflowLockError,
    atomic_write_json,
    atomic_write_jsonl,
    atomic_write_text,
)


with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)

    text_path = root / "state" / "value.txt"
    atomic_write_text(text_path, "first\n")
    assert text_path.read_text(encoding="utf-8") == "first\n"
    atomic_write_text(text_path, "second\n")
    assert text_path.read_text(encoding="utf-8") == "second\n"
    assert not list(text_path.parent.glob("*.pending"))

    json_path = root / "state" / "value.json"
    atomic_write_json(json_path, {"value": 2})
    assert json.loads(json_path.read_text(encoding="utf-8")) == {"value": 2}

    jsonl_path = root / "state" / "rows.jsonl"
    assert atomic_write_jsonl(jsonl_path, [{"id": 1}, {"id": 2}]) == 2
    assert [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
    ] == [{"id": 1}, {"id": 2}]

    simple_lock_path = root / "locks" / "simple.lock"
    with ExclusiveFileLock(
        simple_lock_path,
        purpose="first",
        owner="worker-a",
    ):
        try:
            ExclusiveFileLock(
                simple_lock_path,
                purpose="second",
                owner="worker-b",
            ).acquire()
        except WorkflowLockError as error:
            assert "worker-a" in str(error)
        else:
            raise AssertionError("second worker must not acquire an active lock")
    assert not simple_lock_path.exists()

    integration_lock_path = root / "locks" / "integration.lock"
    assert INTEGRATION_LOCK_TOKEN_ENV not in os.environ
    with IntegrationLock(
        integration_lock_path,
        purpose="outer",
        owner="worker-a",
    ) as outer:
        assert os.environ[INTEGRATION_LOCK_TOKEN_ENV] == outer.token
        with IntegrationLock(
            integration_lock_path,
            purpose="child",
            owner="worker-a",
        ) as child:
            assert child.inherited is True
            assert child.token == outer.token
    assert INTEGRATION_LOCK_TOKEN_ENV not in os.environ
    assert not integration_lock_path.exists()

    queue_path = root / "parser-family-queue.json"
    queue_payload = {
        "schema_version": 1,
        "generated_at": "2026-07-30T12:00:00+08:00",
        "groups": [
            {
                "queue_id": "parser-family:health-a",
                "family_fingerprint": "health-a",
                "work_type": "benefit_parser",
                "batch_id": "tii-life-001",
                "insurance_category": "健康保險",
                "company": "甲人壽",
                "family_name": "甲住院醫療",
                "record_count": 2,
                "product_ids": ["health-001", "health-002"],
                "version_boundary": "exact versions",
            },
            {
                "queue_id": "parser-family:injury-b",
                "family_fingerprint": "injury-b",
                "work_type": "benefit_parser",
                "batch_id": "tii-life-002",
                "insurance_category": "傷害保險",
                "company": "乙人壽",
                "family_name": "乙傷害醫療",
                "record_count": 1,
                "product_ids": ["injury-001"],
                "version_boundary": "exact versions",
            },
        ],
    }
    atomic_write_json(queue_path, queue_payload)
    claims_dir = root / "claims"
    fixed_now = datetime(2026, 7, 30, 4, 0, tzinfo=timezone.utc)

    first = claim_next_group(
        queue_path=queue_path,
        claims_dir=claims_dir,
        owner="Kevin",
        task_id="task-a",
        lease_minutes=60,
        work_types={"benefit_parser"},
        now=fixed_now,
    )
    assert first["status"] == "claimed"
    assert first["claim"]["queue_id"] == "parser-family:health-a"
    assert first["claim"]["product_ids"] == ["health-001", "health-002"]
    assert first["claim"]["queue_sha256"]

    bounded = claim_next_group(
        queue_path=queue_path,
        claims_dir=root / "bounded-claims",
        owner="Kevin",
        task_id="task-small",
        lease_minutes=60,
        work_types={"benefit_parser"},
        max_records=1,
        now=fixed_now,
    )
    assert bounded["status"] == "claimed"
    assert bounded["claim"]["queue_id"] == "parser-family:injury-b"

    no_size_match = claim_next_group(
        queue_path=queue_path,
        claims_dir=root / "empty-claims",
        owner="Kevin",
        task_id="task-empty",
        lease_minutes=60,
        work_types={"benefit_parser"},
        min_records=3,
        max_records=5,
        now=fixed_now,
    )
    assert no_size_match["status"] == "no-op"
    assert no_size_match["reason"] == "no_matching_queue_group"

    second = claim_next_group(
        queue_path=queue_path,
        claims_dir=claims_dir,
        owner="Kevin",
        task_id="task-b",
        lease_minutes=60,
        work_types={"benefit_parser"},
        now=fixed_now,
    )
    assert second["status"] == "claimed"
    assert second["claim"]["queue_id"] == "parser-family:injury-b"

    busy = claim_next_group(
        queue_path=queue_path,
        claims_dir=claims_dir,
        owner="Kevin",
        task_id="task-c",
        lease_minutes=60,
        queue_id="parser-family:health-a",
        work_types={"benefit_parser"},
        now=fixed_now,
    )
    assert busy["status"] == "no-op"
    assert busy["reason"] == "matching_groups_are_already_claimed"

    first_claim_path = Path(first["claim_path"])
    released = update_claim(
        claim_path=first_claim_path,
        claim_id=first["claim"]["claim_id"],
        task_id="task-a",
        action="release",
        now=fixed_now,
    )
    assert released["status"] == "released"

    reclaimed = claim_next_group(
        queue_path=queue_path,
        claims_dir=claims_dir,
        owner="Kevin",
        task_id="task-c",
        lease_minutes=30,
        queue_id="parser-family:health-a",
        work_types={"benefit_parser"},
        now=fixed_now,
    )
    assert reclaimed["status"] == "claimed"
    assert reclaimed["claim"]["task_id"] == "task-c"
    assert reclaimed["claim"]["supersedes_claim_id"] == (
        first["claim"]["claim_id"]
    )
    history_path = (
        claims_dir
        / "history"
        / "health-a"
        / f"{first['claim']['claim_id']}.json"
    )
    assert history_path.is_file()

print("TII workflow guard tests passed.")
