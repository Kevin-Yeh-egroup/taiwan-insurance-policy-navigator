#!/usr/bin/env python3
"""Run one bounded local pass of the TII coverage completion workflow."""

from __future__ import annotations

import argparse
import atexit
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tii_workflow_guard import (
    IntegrationLock,
    atomic_write_json,
    atomic_write_text,
    canonical_integration_lock,
)


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))
DEFAULT_RUN_DIR = ROOT / "work" / "tii-completion-automation"
DEFAULT_QUEUE_DIR = ROOT / "work" / "tii-completion-queues"


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def run_id() -> str:
    return datetime.now(TAIPEI_TZ).strftime("%Y%m%d-%H%M%S-%f")


def command_record(args: list[str], *, timeout_seconds: int = 1800) -> dict[str, Any]:
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
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip()[-6000:],
        "stderr": completed.stderr.strip()[-6000:],
    }


def run_or_stop(args: list[str], *, timeout_seconds: int = 1800) -> dict[str, Any]:
    record = command_record(args, timeout_seconds=timeout_seconds)
    if record["returncode"] != 0:
        raise SystemExit(
            "command failed: "
            + " ".join(args)
            + "\n"
            + str(record.get("stdout") or "")
            + str(record.get("stderr") or "")
        )
    return record


def load_next_source_groups(queue_dir: Path, limit: int) -> list[dict[str, Any]]:
    path = queue_dir / "source-pending-groups.json"
    if not path.exists() or limit <= 0:
        return []
    payload = read_json(path)
    groups = [item for item in payload.get("groups") or [] if isinstance(item, dict)]
    return groups[:limit]


def build_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("completion_summary") or {}
    counts = summary.get("counts") or {}
    pending = summary.get("pending_structure") or {}
    source = summary.get("source_pending") or {}
    lines = [
        "# TII Completion Batch Run",
        "",
        f"- Run id: `{payload['run_id']}`",
        f"- Generated at: `{payload['generated_at']}`",
        "",
        "## Queue Snapshot",
        "",
        f"- Pending structure: `{counts.get('pending_structure', 0)}` records / `{pending.get('group_count', 0)}` groups",
        f"- Source pending: `{counts.get('source_pending', 0)}` records / `{source.get('group_count', 0)}` groups",
        f"- Candidate-ready pending records: `{pending.get('candidate_ready_count', 0)}`",
        "",
        "## Source Pending Gates",
        "",
    ]
    for gate, count in (source.get("processing_gate_counts") or {}).items():
        lines.append(f"- `{gate}`: `{count}`")
    lines.extend(["", "## Next Source Groups", ""])
    for group in payload.get("next_source_groups") or []:
        lines.append(
            "- "
            f"`{group.get('batch_id')}` / {group.get('insurance_category')} / "
            f"{group.get('source_pending_reason')}: `{group.get('record_count')}` records"
        )
    if not payload.get("next_source_groups"):
        lines.append("- No source groups selected.")
    lines.extend(["", "## Commands", ""])
    for command in payload.get("commands") or []:
        lines.append(
            f"- `{command.get('status')}` rc=`{command.get('returncode')}`: "
            f"`{' '.join(command.get('command') or [])}`"
        )
    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This run does not approve newly generated benefit schedules.",
            "- This run does not solve or bypass TII CAPTCHA.",
            "- Source records needing `needs_tii_document_download_captcha` still require the operator page and human CAPTCHA input.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-groups", type=int, default=3)
    parser.add_argument("--source-groups", type=int, default=8)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--queue-dir", type=Path, default=DEFAULT_QUEUE_DIR)
    parser.add_argument("--skip-benefit-run", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()

    if args.max_groups < 0:
        raise SystemExit("--max-groups must be zero or positive")
    if args.source_groups < 0:
        raise SystemExit("--source-groups must be zero or positive")

    integration_lock = IntegrationLock(
        canonical_integration_lock(ROOT),
        purpose="run_tii_completion_batch",
        owner="run_tii_completion_batch.py",
    ).acquire()
    atexit.register(integration_lock.release)

    run_path = args.run_dir / "runs" / run_id()
    commands: list[dict[str, Any]] = []
    commands.append(
        run_or_stop(
            [
                sys.executable,
                "-X",
                "utf8",
                "scripts\\build_tii_completion_queues.py",
                "--output-dir",
                str(args.queue_dir),
            ],
            timeout_seconds=1800,
        )
    )

    if not args.skip_benefit_run and args.max_groups:
        commands.append(
            run_or_stop(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\run_tii_benefit_batch_task.py",
                    "--action",
                    "audit-gaps",
                    "--max-groups",
                    str(args.max_groups),
                ],
                timeout_seconds=3600,
            )
        )
        if not args.skip_verify:
            commands.append(
                run_or_stop(
                    [
                        sys.executable,
                        "-X",
                        "utf8",
                        "scripts\\run_tii_benefit_batch_task.py",
                        "--action",
                        "verify",
                        "--max-groups",
                        str(args.max_groups),
                    ],
                    timeout_seconds=3600,
                )
            )

    completion_summary = read_json(args.queue_dir / "status-summary.json")
    next_source_groups = load_next_source_groups(args.queue_dir, args.source_groups)
    payload = {
        "schema_version": 1,
        "run_id": run_path.name,
        "generated_at": now_iso(),
        "filters": {
            "max_groups": args.max_groups,
            "source_groups": args.source_groups,
            "skip_benefit_run": args.skip_benefit_run,
            "skip_verify": args.skip_verify,
        },
        "completion_summary": completion_summary,
        "next_source_groups": next_source_groups,
        "commands": commands,
    }
    write_json(run_path / "run.json", payload)
    atomic_write_text(run_path / "report.md", build_markdown(payload))
    write_json(args.run_dir / "latest.json", payload)
    atomic_write_text(args.run_dir / "latest.md", build_markdown(payload))

    integration_lock.release()
    atexit.unregister(integration_lock.release)

    print(
        json.dumps(
            {
                "status": "ok",
                "run_id": run_path.name,
                "pending_structure": completion_summary["counts"]["pending_structure"],
                "source_pending": completion_summary["counts"]["source_pending"],
                "next_source_groups": len(next_source_groups),
                "commands": [
                    {
                        "status": item["status"],
                        "returncode": item["returncode"],
                        "command": item["command"],
                    }
                    for item in commands
                ],
                "report": str(run_path / "report.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    integration_lock.release()


if __name__ == "__main__":
    main()
