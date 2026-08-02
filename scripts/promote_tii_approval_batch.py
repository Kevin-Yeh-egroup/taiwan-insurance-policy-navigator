#!/usr/bin/env python3
"""Promote existing TII approval ledgers while skipping stale ledgers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))
DEFAULT_APPROVAL_DIR = ROOT / "work" / "tii-benefit-approvals"
DEFAULT_RUN_DIR = ROOT / "work" / "tii-benefit-approval-promotion"


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_command(args: list[str], *, timeout_seconds: int = 1800) -> dict[str, Any]:
    started_at = now_iso()
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "command": args,
        "started_at": started_at,
        "finished_at": now_iso(),
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def approval_batch_id(path: Path) -> str:
    payload = read_json(path)
    batch_id = str(payload.get("batch_id") or "")
    if not batch_id:
        raise SystemExit(f"approval file has no batch_id: {path}")
    return batch_id


def classify_failure(stderr: str, stdout: str) -> str:
    text = f"{stdout}\n{stderr}"
    if "stale or mismatched approval" in text:
        return "stale_or_mismatched_approval"
    if "approved product has no promotable proposal" in text:
        return "approved_product_has_no_promotable_proposal"
    if "approved schedules have no public content record" in text:
        return "approved_schedule_missing_public_content_record"
    if "approval batch_id does not match" in text:
        return "approval_batch_mismatch"
    return "command_failed"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approval-dir", type=Path, default=DEFAULT_APPROVAL_DIR)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--batch-id", action="append", default=[])
    parser.add_argument("--start-after", default="")
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--skip-summary-rebuild", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.max_files < 0:
        raise SystemExit("--max-files must be zero or positive")

    batch_filter = {item.strip() for item in args.batch_id if item.strip()}
    approval_files = sorted(args.approval_dir.glob("*.json"))
    selected: list[Path] = []
    for path in approval_files:
        if args.start_after and path.name <= args.start_after:
            continue
        batch_id = approval_batch_id(path)
        if batch_filter and batch_id not in batch_filter:
            continue
        selected.append(path)
        if args.max_files and len(selected) >= args.max_files:
            break

    run_id = datetime.now(TAIPEI_TZ).strftime("%Y%m%d-%H%M%S")
    run_path = args.run_dir / "runs" / run_id
    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    commands: list[dict[str, Any]] = []
    touched_batches: set[str] = set()

    for approval_file in selected:
        batch_id = approval_batch_id(approval_file)
        command = [
            sys.executable,
            "-X",
            "utf8",
            "scripts\\extract_tii_plan_benefits.py",
            "--batch-id",
            batch_id,
            "--approval-file",
            str(approval_file),
        ]
        if args.dry_run:
            record = {
                "command": command,
                "returncode": None,
                "stdout": "",
                "stderr": "",
                "started_at": now_iso(),
                "finished_at": now_iso(),
                "dry_run": True,
            }
        else:
            record = run_command(command, timeout_seconds=1800)
        commands.append(record)
        if record["returncode"] not in (0, None):
            skipped.append(
                {
                    "approval_file": str(approval_file.relative_to(ROOT)),
                    "batch_id": batch_id,
                    "reason": classify_failure(record["stderr"], record["stdout"]),
                    "message": (record["stderr"] or record["stdout"])[-1200:],
                }
            )
            continue
        promoted_count = 0
        if record["stdout"]:
            try:
                output = json.loads(record["stdout"])
                promoted_count = int(output.get("promoted_count") or 0)
            except Exception:
                promoted_count = 0
        promoted.append(
            {
                "approval_file": str(approval_file.relative_to(ROOT)),
                "batch_id": batch_id,
                "promoted_count": promoted_count,
            }
        )
        touched_batches.add(batch_id)

    summary_commands: list[dict[str, Any]] = []
    if touched_batches and not args.skip_summary_rebuild and not args.dry_run:
        for batch_id in sorted(touched_batches):
            record = run_command(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\build_tii_document_summaries.py",
                    "--batch-id",
                    batch_id,
                ],
                timeout_seconds=1800,
            )
            summary_commands.append(record)
            if record["returncode"] != 0:
                skipped.append(
                    {
                        "approval_file": "",
                        "batch_id": batch_id,
                        "reason": "summary_rebuild_failed",
                        "message": (record["stderr"] or record["stdout"])[-1200:],
                    }
                )

    payload = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "selected_count": len(selected),
        "promoted_file_count": len(promoted),
        "skipped_file_count": len(skipped),
        "touched_batches": sorted(touched_batches),
        "promoted": promoted,
        "skipped": skipped,
        "commands": commands,
        "summary_commands": summary_commands,
    }
    write_json(run_path / "run.json", payload)
    write_json(args.run_dir / "latest.json", payload)
    print(
        json.dumps(
            {
                "status": "ok",
                "selected_count": payload["selected_count"],
                "promoted_file_count": payload["promoted_file_count"],
                "skipped_file_count": payload["skipped_file_count"],
                "touched_batches": payload["touched_batches"],
                "run": str(run_path / "run.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
