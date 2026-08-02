#!/usr/bin/env python3
"""Build a source-review packet for proposed TII benefit schedules."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))
DEFAULT_DOCUMENTS_ROOT = ROOT / "work" / "tii-documents"
DEFAULT_OUTPUT_DIR = ROOT / "work" / "tii-benefit-review-packets"

SCHEDULE_FIELDS = (
    "selection_type",
    "input_mode",
    "selection_source",
    "selection_label",
    "face_amount_label",
    "selection_guidance",
    "unit_fields",
    "version_characteristics",
    "plan_options",
    "coverage_entries",
)
SEMANTIC_VERSION_IDENTITY_FIELDS = {
    "source_product_id",
    "terms_revision",
    "source_document_sha256",
    "source_text_quality",
    "source_text_extractor",
}


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def schedule_sha256(schedule: dict[str, Any]) -> str:
    canonical_schedule = {
        field: schedule[field]
        for field in SCHEDULE_FIELDS
        if field in schedule
    }
    canonical = json.dumps(
        canonical_schedule,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(canonical.encode("utf-8"))


def semantic_schedule_sha256(schedule: dict[str, Any]) -> str:
    canonical_schedule = {
        field: schedule[field]
        for field in SCHEDULE_FIELDS
        if field in schedule
    }
    version = canonical_schedule.get("version_characteristics")
    if isinstance(version, dict):
        canonical_schedule["version_characteristics"] = {
            key: value
            for key, value in version.items()
            if key not in SEMANTIC_VERSION_IDENTITY_FIELDS
        }
    canonical = json.dumps(
        canonical_schedule,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(canonical.encode("utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def all_entries(schedule: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [
        entry
        for entry in schedule.get("coverage_entries") or []
        if isinstance(entry, dict)
    ]
    for plan in schedule.get("plan_options") or []:
        if not isinstance(plan, dict):
            continue
        entries.extend(
            entry
            for entry in plan.get("coverage_entries") or []
            if isinstance(entry, dict)
        )
    return entries


def candidate_status(
    *,
    batch_id: str,
    product_id: str,
    candidate: dict[str, Any],
    documents_root: Path,
) -> dict[str, Any]:
    source_file = str(candidate.get("source_file") or "")
    source_path = documents_root / batch_id / product_id / source_file
    expected_source_hash = str(candidate.get("source_document_sha256") or "")
    actual_source_hash = sha256_bytes(source_path.read_bytes()) if source_path.is_file() else ""
    schedule = candidate.get("schedule") if isinstance(candidate.get("schedule"), dict) else {}
    expected_schedule_hash = str(candidate.get("schedule_sha256") or "")
    actual_schedule_hash = schedule_sha256(schedule) if schedule else ""
    semantic_schedule_hash = (
        semantic_schedule_sha256(schedule) if schedule else ""
    )
    errors: list[str] = []
    if not source_file:
        errors.append("missing_source_file")
    if not source_path.is_file():
        errors.append("source_pdf_missing")
    if expected_source_hash and actual_source_hash and expected_source_hash != actual_source_hash:
        errors.append("source_pdf_hash_mismatch")
    if not expected_source_hash:
        errors.append("missing_source_document_sha256")
    if not schedule:
        errors.append("missing_schedule")
    if expected_schedule_hash and actual_schedule_hash and expected_schedule_hash != actual_schedule_hash:
        errors.append("schedule_hash_mismatch")
    if not expected_schedule_hash:
        errors.append("missing_schedule_sha256")
    entry_count = len(all_entries(schedule))
    if not entry_count:
        errors.append("no_coverage_entries")
    return {
        "parser_id": candidate.get("parser_id") or "",
        "source_file": source_file,
        "source_path": display_path(source_path),
        "source_file_exists": source_path.is_file(),
        "expected_source_document_sha256": expected_source_hash,
        "actual_source_document_sha256": actual_source_hash,
        "source_hash_matches": bool(expected_source_hash and expected_source_hash == actual_source_hash),
        "expected_schedule_sha256": expected_schedule_hash,
        "actual_schedule_sha256": actual_schedule_hash,
        "semantic_schedule_sha256": semantic_schedule_hash,
        "schedule_hash_matches": bool(expected_schedule_hash and expected_schedule_hash == actual_schedule_hash),
        "selection_type": schedule.get("selection_type") or "",
        "input_mode": schedule.get("input_mode") or "",
        "selection_label": schedule.get("selection_label") or "",
        "face_amount_label": schedule.get("face_amount_label") or "",
        "coverage_entry_count": entry_count,
        "plan_option_count": len(schedule.get("plan_options") or []),
        "version_characteristics": schedule.get("version_characteristics") or {},
        "review_packet_status": "ready_for_human_source_review" if not errors else "blocked",
        "errors": errors,
    }


def build_packet(proposal_path: Path, documents_root: Path) -> dict[str, Any]:
    proposal = read_json(proposal_path)
    batch_id = str(proposal.get("batch_id") or "")
    if not batch_id:
        raise SystemExit(f"proposal has no batch_id: {proposal_path}")
    items: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    parser_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    schedule_hash_counts: Counter[str] = Counter()
    schedule_groups: dict[str, dict[str, Any]] = {}
    semantic_schedule_hash_counts: Counter[str] = Counter()
    semantic_schedule_groups: dict[str, dict[str, Any]] = {}

    for proposal_item in proposal.get("proposals") or []:
        if not isinstance(proposal_item, dict):
            continue
        product_id = str(proposal_item.get("product_id") or "")
        candidates = [
            candidate
            for candidate in proposal_item.get("candidates") or []
            if isinstance(candidate, dict)
        ]
        candidate_reports = [
            candidate_status(
                batch_id=batch_id,
                product_id=product_id,
                candidate=candidate,
                documents_root=documents_root,
            )
            for candidate in candidates
        ]
        errors = [
            error
            for report in candidate_reports
            for error in report.get("errors") or []
        ]
        ready = (
            proposal_item.get("status") == "proposed"
            and len(candidate_reports) == 1
            and not errors
        )
        status = "ready_for_human_source_review" if ready else "blocked"
        status_counts[status] += 1
        for report in candidate_reports:
            if report.get("parser_id"):
                parser_counts[str(report["parser_id"])] += 1
            if report.get("expected_schedule_sha256"):
                schedule_hash = str(report["expected_schedule_sha256"])
                schedule_hash_counts[schedule_hash] += 1
                group = schedule_groups.setdefault(
                    schedule_hash,
                    {
                        "schedule_sha256": schedule_hash,
                        "parser_ids": set(),
                        "product_ids": [],
                        "source_document_sha256_values": set(),
                        "representative_product_id": product_id,
                        "representative_source_file": report.get("source_file") or "",
                        "coverage_entry_count": report.get("coverage_entry_count") or 0,
                        "plan_option_count": report.get("plan_option_count") or 0,
                    },
                )
                if report.get("parser_id"):
                    group["parser_ids"].add(str(report["parser_id"]))
                group["product_ids"].append(product_id)
                if report.get("expected_source_document_sha256"):
                    group["source_document_sha256_values"].add(
                        str(report["expected_source_document_sha256"])
                    )
            if report.get("semantic_schedule_sha256"):
                semantic_hash = str(report["semantic_schedule_sha256"])
                semantic_schedule_hash_counts[semantic_hash] += 1
                semantic_group = semantic_schedule_groups.setdefault(
                    semantic_hash,
                    {
                        "semantic_schedule_sha256": semantic_hash,
                        "parser_ids": set(),
                        "product_ids": [],
                        "exact_schedule_sha256_values": set(),
                        "source_document_sha256_values": set(),
                        "representative_product_id": product_id,
                        "representative_source_file": report.get(
                            "source_file"
                        )
                        or "",
                        "coverage_entry_count": report.get(
                            "coverage_entry_count"
                        )
                        or 0,
                        "plan_option_count": report.get(
                            "plan_option_count"
                        )
                        or 0,
                    },
                )
                if report.get("parser_id"):
                    semantic_group["parser_ids"].add(
                        str(report["parser_id"])
                    )
                semantic_group["product_ids"].append(product_id)
                if report.get("expected_schedule_sha256"):
                    semantic_group[
                        "exact_schedule_sha256_values"
                    ].add(str(report["expected_schedule_sha256"]))
                if report.get("expected_source_document_sha256"):
                    semantic_group[
                        "source_document_sha256_values"
                    ].add(str(report["expected_source_document_sha256"]))
        for error in errors:
            error_counts[error] += 1
        items.append(
            {
                "product_id": product_id,
                "proposal_status": proposal_item.get("status") or "",
                "review_packet_status": status,
                "candidate_count": len(candidate_reports),
                "candidate_reports": candidate_reports,
                "errors": sorted(set(errors)),
            }
        )

    schedule_group_rows = []
    for group in schedule_groups.values():
        schedule_group_rows.append(
            {
                **group,
                "parser_ids": sorted(group["parser_ids"]),
                "product_ids": sorted(group["product_ids"]),
                "product_count": len(group["product_ids"]),
                "source_document_count": len(
                    group["source_document_sha256_values"]
                ),
                "source_document_sha256_values": sorted(
                    group["source_document_sha256_values"]
                ),
            }
        )
    schedule_group_rows.sort(
        key=lambda item: (-item["product_count"], item["schedule_sha256"])
    )
    semantic_schedule_group_rows = []
    for group in semantic_schedule_groups.values():
        semantic_schedule_group_rows.append(
            {
                **group,
                "parser_ids": sorted(group["parser_ids"]),
                "product_ids": sorted(group["product_ids"]),
                "product_count": len(group["product_ids"]),
                "exact_schedule_count": len(
                    group["exact_schedule_sha256_values"]
                ),
                "exact_schedule_sha256_values": sorted(
                    group["exact_schedule_sha256_values"]
                ),
                "source_document_count": len(
                    group["source_document_sha256_values"]
                ),
                "source_document_sha256_values": sorted(
                    group["source_document_sha256_values"]
                ),
            }
        )
    semantic_schedule_group_rows.sort(
        key=lambda item: (
            -item["product_count"],
            item["semantic_schedule_sha256"],
        )
    )

    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "proposal_path": display_path(proposal_path),
        "batch_id": batch_id,
        "proposal_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "parser_counts": dict(parser_counts.most_common()),
        "schedule_hash_counts": dict(schedule_hash_counts.most_common()),
        "schedule_group_count": len(schedule_group_rows),
        "schedule_groups": schedule_group_rows,
        "semantic_schedule_hash_counts": dict(
            semantic_schedule_hash_counts.most_common()
        ),
        "semantic_schedule_group_count": len(
            semantic_schedule_group_rows
        ),
        "semantic_schedule_groups": semantic_schedule_group_rows,
        "error_counts": dict(error_counts.most_common()),
        "safety_notes": [
            "This packet verifies local source-file and schedule integrity only.",
            "Schedule-hash grouping reduces repeated structural review but never merges product versions or replaces exact source-file confirmation.",
            "Semantic schedule grouping excludes only source/version identity fields; every product_id, exact schedule hash, and source hash remains independently reviewable.",
            "It does not approve or promote proposed schedules.",
            "Human or explicitly approved source review is still required before writing an approval ledger.",
        ],
        "items": items,
    }


def build_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# TII Benefit Proposal Review Packet",
        "",
        f"- Batch: `{packet['batch_id']}`",
        f"- Proposal: `{packet['proposal_path']}`",
        f"- Generated at: `{packet['generated_at']}`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in packet["status_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Parser Counts", ""])
    for parser_id, count in packet["parser_counts"].items():
        lines.append(f"- `{parser_id}`: `{count}`")
    lines.extend(["", "## Schedule Hash Counts", ""])
    for schedule_hash, count in packet["schedule_hash_counts"].items():
        lines.append(f"- `{schedule_hash}`: `{count}`")
    lines.extend(
        [
            "",
            "## Schedule Review Groups",
            "",
            f"- Distinct schedules: `{packet['schedule_group_count']}`",
            "",
        ]
    )
    for group in packet["schedule_groups"][:80]:
        lines.append(
            "- "
            f"`{group['schedule_sha256']}` / "
            f"{group['product_count']} products / "
            f"{group['source_document_count']} exact source documents / "
            f"parser `{', '.join(group['parser_ids'])}` / "
            f"representative `{group['representative_product_id']}`"
        )
    if len(packet["schedule_groups"]) > 80:
        lines.append(f"- ...and `{len(packet['schedule_groups']) - 80}` more groups.")
    lines.extend(
        [
            "",
            "## Semantic Review Groups",
            "",
            (
                "- Distinct semantic schedules: "
                f"`{packet['semantic_schedule_group_count']}`"
            ),
            "",
        ]
    )
    for group in packet["semantic_schedule_groups"][:80]:
        lines.append(
            "- "
            f"`{group['semantic_schedule_sha256']}` / "
            f"{group['product_count']} products / "
            f"{group['exact_schedule_count']} exact schedules / "
            f"{group['source_document_count']} exact source documents / "
            f"representative `{group['representative_product_id']}`"
        )
    if len(packet["semantic_schedule_groups"]) > 80:
        lines.append(
            "- ...and "
            f"`{len(packet['semantic_schedule_groups']) - 80}` "
            "more semantic groups."
        )
    if packet["error_counts"]:
        lines.extend(["", "## Errors", ""])
        for error, count in packet["error_counts"].items():
            lines.append(f"- `{error}`: `{count}`")
    lines.extend(["", "## Ready Items", ""])
    ready_items = [
        item
        for item in packet["items"]
        if item.get("review_packet_status") == "ready_for_human_source_review"
    ]
    for item in ready_items[:80]:
        report = (item.get("candidate_reports") or [{}])[0]
        lines.append(
            "- "
            f"`{item['product_id']}` / `{report.get('source_file')}` / "
            f"`{report.get('expected_schedule_sha256')}` / "
            f"{report.get('coverage_entry_count')} entries / "
            f"face amount label: `{report.get('face_amount_label') or 'n/a'}`"
        )
    if len(ready_items) > 80:
        lines.append(f"- ...and `{len(ready_items) - 80}` more.")
    lines.extend(["", "## Safety Notes", ""])
    for note in packet["safety_notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--documents-root", type=Path, default=DEFAULT_DOCUMENTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    proposal_path = args.proposal if args.proposal.is_absolute() else ROOT / args.proposal
    packet = build_packet(proposal_path, args.documents_root)
    stem = proposal_path.stem
    json_output = args.output_dir / f"{stem}-review-packet.json"
    markdown_output = args.output_dir / f"{stem}-review-packet.md"
    write_json(json_output, packet)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(build_markdown(packet), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": packet["batch_id"],
                "proposal_count": packet["proposal_count"],
                "status_counts": packet["status_counts"],
                "error_counts": packet["error_counts"],
                "output": str(json_output),
                "markdown": str(markdown_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
