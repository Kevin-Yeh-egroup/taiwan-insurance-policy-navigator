#!/usr/bin/env python3
"""Claim, renew, or release one exact TII parser-family work package."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from tii_workflow_guard import (
    ExclusiveFileLock,
    WorkflowLockError,
    atomic_write_json,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = (
    ROOT
    / "work"
    / "tii-life-calculation-readiness"
    / "parser-family-queue.json"
)
DEFAULT_CLAIMS_DIR = ROOT / "work" / "tii-parser-family-claims"
DEFAULT_LEASE_MINUTES = 180


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_at(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return value


def claim_key(group: dict[str, Any]) -> str:
    fingerprint = str(group.get("family_fingerprint") or "").strip()
    if fingerprint:
        return fingerprint
    queue_id = str(group.get("queue_id") or "").strip()
    if not queue_id:
        raise SystemExit("queue group has no family_fingerprint or queue_id")
    return hashlib.sha256(queue_id.encode("utf-8")).hexdigest()[:24]


def claim_path_for_group(
    group: dict[str, Any],
    claims_dir: Path,
) -> Path:
    return claims_dir / f"{claim_key(group)}.json"


def claim_is_active(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
) -> bool:
    if payload.get("status") != "claimed":
        return False
    expires_at = parse_time(payload.get("expires_at"))
    return bool(expires_at and expires_at > (now or utc_now()))


def archive_prior_claim(
    payload: dict[str, Any],
    *,
    claims_dir: Path,
    key: str,
) -> None:
    claim_id = str(payload.get("claim_id") or "").strip()
    if not claim_id:
        return
    archive_path = claims_dir / "history" / key / f"{claim_id}.json"
    if not archive_path.exists():
        atomic_write_json(archive_path, payload)


def select_groups(
    queue_payload: dict[str, Any],
    *,
    queue_id: str = "",
    work_types: set[str] | None = None,
    categories: set[str] | None = None,
    batch_ids: set[str] | None = None,
    min_records: int = 1,
    max_records: int | None = None,
) -> list[dict[str, Any]]:
    groups = [
        group
        for group in queue_payload.get("groups") or []
        if isinstance(group, dict)
    ]
    selected = []
    for group in groups:
        if queue_id and str(group.get("queue_id") or "") != queue_id:
            continue
        if work_types and str(group.get("work_type") or "") not in work_types:
            continue
        if (
            categories
            and str(group.get("insurance_category") or "") not in categories
        ):
            continue
        if batch_ids and str(group.get("batch_id") or "") not in batch_ids:
            continue
        record_count = int(group.get("record_count") or 0)
        if record_count < min_records:
            continue
        if max_records is not None and record_count > max_records:
            continue
        selected.append(group)
    return selected


def claim_next_group(
    *,
    queue_path: Path,
    claims_dir: Path,
    owner: str,
    task_id: str,
    lease_minutes: int,
    queue_id: str = "",
    work_types: set[str] | None = None,
    categories: set[str] | None = None,
    batch_ids: set[str] | None = None,
    min_records: int = 1,
    max_records: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if lease_minutes <= 0:
        raise SystemExit("lease_minutes must be positive")
    if not owner.strip() or not task_id.strip():
        raise SystemExit("owner and task_id are required")
    if min_records <= 0:
        raise SystemExit("min_records must be positive")
    if max_records is not None and max_records < min_records:
        raise SystemExit("max_records must be greater than or equal to min_records")
    queue_payload = read_json(queue_path)
    queue_sha256 = sha256_file(queue_path)
    selected = select_groups(
        queue_payload,
        queue_id=queue_id,
        work_types=work_types,
        categories=categories,
        batch_ids=batch_ids,
        min_records=min_records,
        max_records=max_records,
    )
    current_time = now or utc_now()
    busy: list[dict[str, Any]] = []
    for group in selected:
        product_ids = [
            str(value)
            for value in group.get("product_ids") or []
            if str(value)
        ]
        if not product_ids:
            continue
        key = claim_key(group)
        claim_path = claim_path_for_group(group, claims_dir)
        lock_path = claims_dir / ".locks" / f"{key}.lock"
        try:
            with ExclusiveFileLock(
                lock_path,
                purpose="claim_tii_parser_family",
                owner=owner,
                extra={"queue_id": str(group.get("queue_id") or "")},
            ):
                prior: dict[str, Any] = {}
                if claim_path.exists():
                    prior = read_json(claim_path)
                if claim_is_active(prior, now=current_time):
                    busy.append(
                        {
                            "queue_id": group.get("queue_id"),
                            "claim_id": prior.get("claim_id"),
                            "owner": prior.get("owner"),
                            "task_id": prior.get("task_id"),
                            "expires_at": prior.get("expires_at"),
                        }
                    )
                    continue
                if prior:
                    archive_prior_claim(
                        prior,
                        claims_dir=claims_dir,
                        key=key,
                    )
                expires_at = current_time + timedelta(minutes=lease_minutes)
                claim = {
                    "schema_version": 1,
                    "status": "claimed",
                    "claim_id": uuid4().hex,
                    "owner": owner.strip(),
                    "task_id": task_id.strip(),
                    "claimed_at": iso_at(current_time),
                    "expires_at": iso_at(expires_at),
                    "lease_minutes": lease_minutes,
                    "queue_path": str(queue_path),
                    "queue_generated_at": str(
                        queue_payload.get("generated_at") or ""
                    ),
                    "queue_sha256": queue_sha256,
                    "queue_id": str(group.get("queue_id") or ""),
                    "family_fingerprint": str(
                        group.get("family_fingerprint") or ""
                    ),
                    "work_type": str(group.get("work_type") or ""),
                    "batch_id": str(group.get("batch_id") or ""),
                    "insurance_category": str(
                        group.get("insurance_category") or ""
                    ),
                    "company": str(group.get("company") or ""),
                    "family_name": str(group.get("family_name") or ""),
                    "record_count": len(product_ids),
                    "product_ids": product_ids,
                    "version_boundary": str(
                        group.get("version_boundary") or ""
                    ),
                    **(
                        {"supersedes_claim_id": prior.get("claim_id")}
                        if prior.get("claim_id")
                        else {}
                    ),
                }
                atomic_write_json(claim_path, claim)
                return {
                    "status": "claimed",
                    "claim_path": str(claim_path),
                    "claim": claim,
                }
        except WorkflowLockError as error:
            busy.append(
                {
                    "queue_id": group.get("queue_id"),
                    "reason": "claim_lock_busy",
                    "detail": str(error),
                }
            )

    return {
        "status": "no-op",
        "reason": (
            "matching_groups_are_already_claimed"
            if selected and busy
            else "no_matching_queue_group"
        ),
        "matching_group_count": len(selected),
        "busy": busy,
    }


def update_claim(
    *,
    claim_path: Path,
    claim_id: str,
    task_id: str,
    action: str,
    lease_minutes: int = DEFAULT_LEASE_MINUTES,
    now: datetime | None = None,
) -> dict[str, Any]:
    key = claim_path.stem
    lock_path = claim_path.parent / ".locks" / f"{key}.lock"
    current_time = now or utc_now()
    with ExclusiveFileLock(
        lock_path,
        purpose=f"{action}_tii_parser_family_claim",
        owner=task_id,
    ):
        claim = read_json(claim_path)
        if str(claim.get("claim_id") or "") != claim_id:
            raise SystemExit("claim_id does not match the current claim")
        if str(claim.get("task_id") or "") != task_id:
            raise SystemExit("task_id does not own the current claim")
        if action == "renew":
            if not claim_is_active(claim, now=current_time):
                raise SystemExit("expired or inactive claim cannot be renewed")
            if lease_minutes <= 0:
                raise SystemExit("lease_minutes must be positive")
            claim["lease_minutes"] = lease_minutes
            claim["renewed_at"] = iso_at(current_time)
            claim["expires_at"] = iso_at(
                current_time + timedelta(minutes=lease_minutes)
            )
        elif action == "release":
            claim["status"] = "released"
            claim["released_at"] = iso_at(current_time)
        else:
            raise SystemExit(f"unsupported claim action: {action}")
        atomic_write_json(claim_path, claim)
        return {
            "status": claim["status"],
            "claim_path": str(claim_path),
            "claim": claim,
        }


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    claim_parser = subparsers.add_parser("claim")
    claim_parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    claim_parser.add_argument(
        "--claims-dir",
        type=Path,
        default=DEFAULT_CLAIMS_DIR,
    )
    claim_parser.add_argument("--owner", required=True)
    claim_parser.add_argument("--task-id", required=True)
    claim_parser.add_argument(
        "--lease-minutes",
        type=int,
        default=DEFAULT_LEASE_MINUTES,
    )
    claim_parser.add_argument("--queue-id", default="")
    claim_parser.add_argument(
        "--work-type",
        action="append",
        default=[],
    )
    claim_parser.add_argument("--category", action="append", default=[])
    claim_parser.add_argument("--batch-id", action="append", default=[])
    claim_parser.add_argument("--min-records", type=int, default=1)
    claim_parser.add_argument("--max-records", type=int)

    for action in ("renew", "release"):
        action_parser = subparsers.add_parser(action)
        action_parser.add_argument("--claim-file", type=Path, required=True)
        action_parser.add_argument("--claim-id", required=True)
        action_parser.add_argument("--task-id", required=True)
        if action == "renew":
            action_parser.add_argument(
                "--lease-minutes",
                type=int,
                default=DEFAULT_LEASE_MINUTES,
            )

    args = parser.parse_args()
    if args.action == "claim":
        result = claim_next_group(
            queue_path=resolve_path(args.queue),
            claims_dir=resolve_path(args.claims_dir),
            owner=args.owner,
            task_id=args.task_id,
            lease_minutes=args.lease_minutes,
            queue_id=args.queue_id,
            work_types={
                value for value in (args.work_type or ["benefit_parser"]) if value
            },
            categories={value for value in args.category if value},
            batch_ids={value for value in args.batch_id if value},
            min_records=args.min_records,
            max_records=args.max_records,
        )
    else:
        result = update_claim(
            claim_path=resolve_path(args.claim_file),
            claim_id=args.claim_id,
            task_id=args.task_id,
            action=args.action,
            lease_minutes=getattr(
                args,
                "lease_minutes",
                DEFAULT_LEASE_MINUTES,
            ),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
