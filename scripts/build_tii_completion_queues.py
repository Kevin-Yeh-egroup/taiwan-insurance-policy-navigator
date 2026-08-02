#!/usr/bin/env python3
"""Build exhaustive local queues for unfinished TII coverage completion work."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from tii_workflow_guard import (
    IntegrationLock,
    atomic_write_json,
    atomic_write_jsonl,
    canonical_integration_lock,
)


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))

DEFAULT_RECORDS_ROOT = ROOT / "data" / "tii" / "records"
DEFAULT_SUMMARY_DIR = ROOT / "data" / "tii" / "document-summaries"
DEFAULT_REVIEWED_DIR = ROOT / "data" / "tii" / "reviewed-benefits"
DEFAULT_DOCUMENTS_ROOT = ROOT / "work" / "tii-documents"
DEFAULT_CANDIDATES_DIR = ROOT / "work" / "tii-benefit-candidates"
DEFAULT_PROPOSALS_DIR = ROOT / "work" / "tii-benefit-proposals"
DEFAULT_AUDIT_PATH = ROOT / "docs" / "TII_COVERAGE_DATA_AUDIT.json"
DEFAULT_OUTPUT_DIR = ROOT / "work" / "tii-completion-queues"
DEFAULT_TII_PROGRESS_PATH = ROOT / "data" / "tii-execution-progress.json"
DEFAULT_DETAIL_RETRY_FAILURES_PATH = ROOT / "work" / "tii-execution" / "detail-retry-failures.json"

TARGET_TERMS = ("給付項目", "保險範圍", "保險金", "住院", "手術", "醫療費用")


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    return atomic_write_jsonl(path, rows)


def batch_sort_key(batch_id: str) -> tuple[str, int, str]:
    prefix, _, suffix = batch_id.rpartition("-")
    try:
        number = int(suffix)
    except ValueError:
        number = 999999
    return prefix, number, batch_id


def record_shard_paths(records_root: Path) -> list[Path]:
    return sorted(records_root.glob("*/*.json"))


def load_all_records(records_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in record_shard_paths(records_root):
        payload = read_json(path)
        bucket = str(payload.get("bucket") or path.parent.name)
        shard_id = str(payload.get("shard_id") or path.stem)
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            batch_id = str(record.get("source_batch_id") or "")
            product_id = str(record.get("product_id") or "")
            if not batch_id or not product_id:
                continue
            records.append(
                {
                    **record,
                    "_bucket": bucket,
                    "_record_shard": str(path.relative_to(ROOT)),
                    "_record_shard_id": shard_id,
                }
            )
    return records


def load_summary_meta(summary_dir: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], int]:
    meta: dict[tuple[str, str], dict[str, Any]] = {}
    raw_count = 0
    for path in sorted(summary_dir.glob("tii-*.json")):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id") or path.stem)
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            product_id = str(record.get("product_id") or "")
            if not product_id:
                continue
            raw_count += 1
            coverage_terms: list[str] = []
            focus_keys: list[str] = []
            for card in record.get("reader_focus") or []:
                if not isinstance(card, dict):
                    continue
                key = str(card.get("key") or "")
                if key:
                    focus_keys.append(key)
                if key == "coverage":
                    coverage_terms = [
                        str(term)
                        for term in card.get("terms") or []
                        if isinstance(term, str) and term
                    ]
            meta[(batch_id, product_id)] = {
                "batch_id": batch_id,
                "product_id": product_id,
                "coverage_tags": record.get("coverage_tags") or [],
                "coverage_terms": coverage_terms,
                "focus_keys": sorted(set(focus_keys)),
                "summary_path": str(path.relative_to(ROOT)),
            }
    return meta, raw_count


def load_reviewed_keys(reviewed_dir: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path in sorted(reviewed_dir.glob("tii-*.json")):
        payload = read_json(path)
        batch_id = str(payload.get("batch_id") or path.stem)
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            product_id = str(record.get("product_id") or "")
            if product_id:
                keys.add((batch_id, product_id))
    return keys


def load_candidate_keys(candidates_dir: Path) -> tuple[set[tuple[str, str]], Counter[str]]:
    keys: set[tuple[str, str]] = set()
    by_batch: Counter[str] = Counter()
    for path in sorted(candidates_dir.glob("*.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            batch_id = str(candidate.get("batch_id") or "")
            product_id = str(candidate.get("product_id") or "")
            if not batch_id or not product_id:
                continue
            key = (batch_id, product_id)
            if key not in keys:
                by_batch[batch_id] += 1
            keys.add(key)
    return keys, by_batch


def load_reviewable_proposal_keys(proposals_dir: Path) -> tuple[set[tuple[str, str]], Counter[str]]:
    keys: set[tuple[str, str]] = set()
    by_batch: Counter[str] = Counter()
    required_candidate_fields = {
        "parser_id",
        "source_file",
        "source_document_sha256",
        "schedule_sha256",
    }
    for path in sorted(proposals_dir.glob("tii-*.json")):
        try:
            payload = read_json(path)
        except Exception:
            continue
        batch_id = str(payload.get("batch_id") or path.stem)
        proposals = payload.get("proposals")
        if not isinstance(proposals, list):
            continue
        for proposal in proposals:
            if not isinstance(proposal, dict) or proposal.get("status") != "proposed":
                continue
            product_id = str(proposal.get("product_id") or "")
            candidates = proposal.get("candidates")
            if not batch_id or not product_id or not isinstance(candidates, list):
                continue
            if len(candidates) != 1 or not isinstance(candidates[0], dict):
                continue
            candidate = candidates[0]
            if any(not candidate.get(field) for field in required_candidate_fields):
                continue
            key = (batch_id, product_id)
            if key not in keys:
                by_batch[batch_id] += 1
            keys.add(key)
    return keys, by_batch


def scan_downloaded_document_products(documents_root: Path) -> set[tuple[str, str]]:
    products: set[tuple[str, str]] = set()
    if not documents_root.exists():
        return products
    for batch_dir in documents_root.glob("tii-*"):
        if not batch_dir.is_dir():
            continue
        for product_dir in batch_dir.iterdir():
            if product_dir.is_dir() and any(path.is_file() for path in product_dir.iterdir()):
                products.add((batch_dir.name, product_dir.name))
    return products


def load_document_download_statuses(documents_root: Path) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    if not documents_root.exists():
        return statuses
    for batch_dir in sorted(documents_root.glob("tii-*")):
        if not batch_dir.is_dir():
            continue
        status_path = batch_dir / "_document-download-status.json"
        if not status_path.exists():
            continue
        try:
            status = read_json(status_path)
        except Exception:
            continue
        failed_reasons_by_product: dict[str, Counter[str]] = defaultdict(Counter)
        for item in status.get("failed_documents") or []:
            if not isinstance(item, dict):
                continue
            product_id = str(item.get("product_id") or "")
            reason = str(item.get("reason") or "unknown")
            if product_id:
                failed_reasons_by_product[product_id][reason] += 1
        status["_failed_reasons_by_product"] = {
            product_id: dict(counter)
            for product_id, counter in failed_reasons_by_product.items()
        }
        statuses[batch_dir.name] = status
    return statuses


def load_detail_retry_failures(progress_path: Path, failure_ledger_path: Path) -> dict[tuple[str, str], set[str]]:
    failures: dict[tuple[str, str], set[str]] = defaultdict(set)
    if progress_path.exists():
        try:
            payload = read_json(progress_path)
        except Exception:
            payload = {}
        for run in payload.get("runs") or []:
            if not isinstance(run, dict):
                continue
            batch_id = str(run.get("batch_id") or "")
            fetched_details = run.get("fetched_details")
            if not batch_id or not isinstance(fetched_details, dict):
                continue
            for item in fetched_details.get("failed_details") or []:
                if not isinstance(item, dict):
                    continue
                product_id = str(item.get("product_id") or "")
                reason = str(item.get("reason") or "")
                if product_id and reason:
                    failures[(batch_id, product_id)].add(reason)
    if failure_ledger_path.exists():
        try:
            ledger = read_json(failure_ledger_path)
        except Exception:
            ledger = {}
        for item in ledger.get("failures") or []:
            if not isinstance(item, dict):
                continue
            batch_id = str(item.get("batch_id") or "")
            product_id = str(item.get("product_id") or "")
            reason = str(item.get("reason") or "")
            if batch_id and product_id and reason:
                failures[(batch_id, product_id)].add(reason)
    return failures


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    detail_source_file = str(record.get("detail_source_file") or "")
    detail_path = ROOT / detail_source_file if detail_source_file else None
    return {
        "batch_id": str(record.get("source_batch_id") or ""),
        "bucket": str(record.get("_bucket") or ""),
        "record_shard": str(record.get("_record_shard") or ""),
        "record_id": str(record.get("id") or ""),
        "product_id": str(record.get("product_id") or ""),
        "company": str(record.get("company") or ""),
        "insurance_category": str(record.get("insurance_category") or ""),
        "product_name": str(record.get("product_name") or ""),
        "sale_status": str(record.get("sale_status") or ""),
        "sale_date": str(record.get("sale_date") or ""),
        "discontinued_date": str(record.get("discontinued_date") or ""),
        "edition_label": str(record.get("edition_label") or ""),
        "detail_url": str(record.get("detail_url") or ""),
        "detail_saved": bool(record.get("detail_saved")),
        "detail_source_file": detail_source_file,
        "detail_file_exists": bool(detail_path and detail_path.exists()),
        "same_name_product_id_count": int(record.get("same_name_product_id_count") or 1),
    }


def pending_priority(summary: dict[str, Any], has_candidate: bool) -> str:
    terms = set(summary.get("coverage_terms") or [])
    if has_candidate:
        return "candidate_ready"
    if any(term in terms for term in TARGET_TERMS) or any("保險金" in term for term in terms):
        return "needs_candidate_rule"
    return "needs_manual_source_review"


def source_pending_reason(
    record: dict[str, Any],
    downloaded_products: set[tuple[str, str]],
    download_statuses: dict[str, dict[str, Any]],
    detail_retry_failures: dict[tuple[str, str], set[str]],
) -> tuple[str, str]:
    batch_id = str(record.get("source_batch_id") or "")
    product_id = str(record.get("product_id") or "")
    detail_source_file = str(record.get("detail_source_file") or "")
    detail_path = ROOT / detail_source_file if detail_source_file else None
    key = (batch_id, product_id)
    if not record.get("detail_saved") or not detail_source_file or not detail_path or not detail_path.exists():
        retry_failures = detail_retry_failures.get(key) or set()
        if "invalid_detail_session" in retry_failures:
            return "detail_invalid_session_after_retry", "needs_alternate_source_or_manual_document_review"
        return "detail_missing_or_unusable", "needs_tii_result_or_detail_backfill_captcha"
    if key in downloaded_products:
        return "documents_downloaded_needs_extraction", "can_extract_locally"
    download_status = download_statuses.get(batch_id) or {}
    failed_reasons_by_product = download_status.get("_failed_reasons_by_product") or {}
    failed_reasons = set((failed_reasons_by_product.get(product_id) or {}).keys())
    if download_status.get("total_scanned_all_details"):
        if failed_reasons and failed_reasons != {"not_a_document"}:
            return "document_download_failed_after_scan", "needs_tii_document_download_captcha_retry"
        if failed_reasons == {"not_a_document"}:
            return "document_link_not_accessible_after_scan", "needs_alternate_source_or_manual_document_review"
        return "documents_unavailable_after_full_scan", "needs_alternate_source_or_manual_document_review"
    return "documents_not_downloaded", "needs_tii_document_download_captcha"


def source_gate_priority(gate: str) -> int:
    return {
        "can_extract_locally": 0,
        "needs_tii_document_download_captcha": 1,
        "needs_tii_document_download_captcha_retry": 2,
        "needs_tii_result_or_detail_backfill_captcha": 3,
        "needs_alternate_source_or_manual_document_review": 4,
    }.get(gate, 9)


def add_sample(group: dict[str, Any], row: dict[str, Any]) -> None:
    samples = group.setdefault("sample_products", [])
    if len(samples) >= 5:
        return
    samples.append(
        {
            "batch_id": row["batch_id"],
            "product_id": row["product_id"],
            "company": row["company"],
            "product_name": row["product_name"],
            "edition_label": row.get("edition_label", ""),
        }
    )


def build_queues(
    *,
    records_root: Path,
    summary_dir: Path,
    reviewed_dir: Path,
    documents_root: Path,
    candidates_dir: Path,
    proposals_dir: Path,
    audit_path: Path,
    output_dir: Path,
    progress_path: Path,
    failure_ledger_path: Path,
) -> dict[str, Any]:
    generated_at = now_iso()
    all_records = load_all_records(records_root)
    record_keys = {
        (str(record.get("source_batch_id") or ""), str(record.get("product_id") or ""))
        for record in all_records
    }
    summary_meta, summary_raw_count = load_summary_meta(summary_dir)
    reviewed_keys = load_reviewed_keys(reviewed_dir)
    candidate_keys, candidate_by_batch = load_candidate_keys(candidates_dir)
    proposal_keys, proposal_by_batch = load_reviewable_proposal_keys(proposals_dir)
    reviewable_keys = candidate_keys.union(proposal_keys)
    downloaded_products = scan_downloaded_document_products(documents_root)
    download_statuses = load_document_download_statuses(documents_root)
    detail_retry_failures = load_detail_retry_failures(progress_path, failure_ledger_path)

    pending_rows: list[dict[str, Any]] = []
    summary_only_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    pending_groups: dict[tuple[str, str], dict[str, Any]] = {}
    source_groups: dict[tuple[str, str, str], dict[str, Any]] = {}

    status_counter: Counter[str] = Counter()
    pending_priority_counter: Counter[str] = Counter()
    source_reason_counter: Counter[str] = Counter()
    source_gate_counter: Counter[str] = Counter()

    for record in all_records:
        key = (str(record.get("source_batch_id") or ""), str(record.get("product_id") or ""))
        row_base = compact_record(record)
        if key in reviewed_keys:
            status_counter["structured_or_needs_user_input"] += 1
            continue
        summary = summary_meta.get(key)
        if summary:
            has_candidate = key in reviewable_keys
            priority = pending_priority(summary, has_candidate)
            row = {
                **row_base,
                "status": "pending_structure",
                "priority": priority,
                "has_candidate": has_candidate,
                "coverage_tags": summary.get("coverage_tags") or [],
                "coverage_terms": summary.get("coverage_terms") or [],
                "focus_keys": summary.get("focus_keys") or [],
                "summary_path": summary.get("summary_path") or "",
            }
            pending_rows.append(row)
            pending_priority_counter[priority] += 1
            status_counter["pending_structure"] += 1

            group_key = (row["insurance_category"], row["batch_id"])
            group = pending_groups.setdefault(
                group_key,
                {
                    "queue_id": f"pending_structure:{row['insurance_category']}:{row['batch_id']}",
                    "status": "pending_structure",
                    "batch_id": row["batch_id"],
                    "bucket": row["bucket"],
                    "insurance_category": row["insurance_category"],
                    "record_count": 0,
                    "candidate_ready_count": 0,
                    "priority_counts": Counter(),
                    "coverage_term_counts": Counter(),
                    "companies": Counter(),
                    "next_recommended_action": "",
                },
            )
            group["record_count"] += 1
            if has_candidate:
                group["candidate_ready_count"] += 1
            group["priority_counts"][priority] += 1
            group["companies"][row["company"]] += 1
            for term in row["coverage_terms"]:
                if term in TARGET_TERMS or "保險金" in term:
                    group["coverage_term_counts"][term] += 1
            add_sample(group, row)
            continue

        reason, gate = source_pending_reason(record, downloaded_products, download_statuses, detail_retry_failures)
        row = {
            **row_base,
            "status": "source_pending",
            "source_pending_reason": reason,
            "processing_gate": gate,
            "document_product_folder_exists": key in downloaded_products,
        }
        source_rows.append(row)
        source_reason_counter[reason] += 1
        source_gate_counter[gate] += 1
        status_counter["source_pending"] += 1

        group_key = (reason, row["insurance_category"], row["batch_id"])
        group = source_groups.setdefault(
            group_key,
            {
                "queue_id": f"source_pending:{reason}:{row['insurance_category']}:{row['batch_id']}",
                "status": "source_pending",
                "source_pending_reason": reason,
                "processing_gate": gate,
                "batch_id": row["batch_id"],
                "bucket": row["bucket"],
                "insurance_category": row["insurance_category"],
                "record_count": 0,
                "detail_saved_count": 0,
                "document_product_folder_count": 0,
                "companies": Counter(),
                "next_recommended_action": "",
            },
        )
        group["record_count"] += 1
        if row["detail_file_exists"]:
            group["detail_saved_count"] += 1
        if row["document_product_folder_exists"]:
            group["document_product_folder_count"] += 1
        group["companies"][row["company"]] += 1
        add_sample(group, row)

    summary_only_keys = sorted(
        set(summary_meta) - record_keys - reviewed_keys,
        key=lambda item: (batch_sort_key(item[0]), item[1]),
    )
    for batch_id, product_id in summary_only_keys:
        summary = summary_meta[(batch_id, product_id)]
        row = {
            "batch_id": batch_id,
            "bucket": "summary_only",
            "record_shard": "",
            "record_id": "",
            "product_id": product_id,
            "company": "",
            "insurance_category": "",
            "product_name": "",
            "sale_status": "",
            "sale_date": "",
            "discontinued_date": "",
            "edition_label": "",
            "detail_url": "",
            "detail_saved": False,
            "detail_source_file": "",
            "detail_file_exists": False,
            "same_name_product_id_count": 0,
            "status": "pending_structure_summary_only",
            "priority": "needs_index_reconciliation",
            "has_candidate": (batch_id, product_id) in candidate_keys,
            "coverage_tags": summary.get("coverage_tags") or [],
            "coverage_terms": summary.get("coverage_terms") or [],
            "focus_keys": summary.get("focus_keys") or [],
            "summary_path": summary.get("summary_path") or "",
            "note": "Document summary exists, but this exact batch_id + product_id is not present in the current TII record shards.",
        }
        summary_only_rows.append(row)

    for group in pending_groups.values():
        if group["candidate_ready_count"]:
            group["next_recommended_action"] = "Run the benefit proposal/parser workflow for this batch and promote only approved candidates."
        else:
            group["next_recommended_action"] = "Add deterministic parser coverage from official terms before proposing benefits."
        group["priority_counts"] = dict(sorted(group["priority_counts"].items()))
        group["coverage_term_counts"] = dict(
            sorted(group["coverage_term_counts"].items(), key=lambda item: (-item[1], item[0]))
        )
        group["companies"] = dict(group["companies"].most_common(8))

    for group in source_groups.values():
        gate = group["processing_gate"]
        if gate == "can_extract_locally":
            group["next_recommended_action"] = "Run extract_tii_document_content.py for this batch, then rebuild summaries."
        elif gate == "needs_tii_document_download_captcha":
            group["next_recommended_action"] = "Use the TII operator document-download mode with a human CAPTCHA, then extract content."
        elif gate == "needs_tii_document_download_captcha_retry":
            group["next_recommended_action"] = "Retry this scanned batch with a fresh TII CAPTCHA because at least one document download failed with a retryable error."
        elif gate == "needs_alternate_source_or_manual_document_review":
            group["next_recommended_action"] = "Do not re-run CAPTCHA for this fully scanned batch; inspect product detail pages or alternate official sources for missing documents."
        else:
            group["next_recommended_action"] = "Backfill result/detail pages through the TII operator with a human CAPTCHA."
        group["companies"] = dict(group["companies"].most_common(8))

    pending_group_list = sorted(
        pending_groups.values(),
        key=lambda item: (
            -int(item["candidate_ready_count"]),
            -int(item["record_count"]),
            batch_sort_key(str(item["batch_id"])),
        ),
    )
    source_group_list = sorted(
        source_groups.values(),
        key=lambda item: (
            source_gate_priority(str(item["processing_gate"])),
            -int(item["record_count"]),
            batch_sort_key(str(item["batch_id"])),
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    pending_records_path = output_dir / "pending-structure-records.jsonl"
    summary_only_records_path = output_dir / "pending-structure-summary-only-records.jsonl"
    source_records_path = output_dir / "source-pending-records.jsonl"
    pending_count = write_jsonl(pending_records_path, pending_rows)
    summary_only_count = write_jsonl(summary_only_records_path, summary_only_rows)
    source_count = write_jsonl(source_records_path, source_rows)
    write_json(output_dir / "pending-structure-groups.json", {"generated_at": generated_at, "groups": pending_group_list})
    write_json(output_dir / "source-pending-groups.json", {"generated_at": generated_at, "groups": source_group_list})

    audit_payload: dict[str, Any] = {}
    if audit_path.exists():
        audit_payload = read_json(audit_path)
    audit_counts = audit_payload.get("structure_status_counts") or {}
    audit_formula_source_pending = max(len(all_records) - len(summary_meta), 0)
    status_matches_audit = {
        "pending_structure": int(audit_counts.get("pending_structure") or -1)
        == pending_count + summary_only_count,
        "source_pending_formula": int(audit_counts.get("source_pending") or -1)
        == audit_formula_source_pending,
        "source_pending_exact_records_without_summary": int(audit_counts.get("source_pending") or -1)
        == source_count,
    }

    summary = {
        "schema_version": 1,
        "generated_at": generated_at,
        "source": "local TII records, document summaries, reviewed benefits, and downloaded document folders",
        "rules": {
            "version_key": "source_batch_id + product_id",
            "pending_structure": "A document summary exists, but no reviewed benefit schedule exists for the exact version key.",
            "source_pending": "A public TII record exists, but no document summary exists for the exact version key.",
            "captcha_boundary": "Official TII query and document sessions require human CAPTCHA; this queue does not solve or bypass CAPTCHA.",
        },
        "counts": {
            "total_records": len(all_records),
            "coverage_work_universe_keys": len(record_keys.union(set(summary_meta))),
            "document_summary_records_raw": summary_raw_count,
            "document_summary_keys": len(summary_meta),
            "document_summary_keys_in_tii_index": len(set(summary_meta).intersection(record_keys)),
            "document_summary_keys_not_in_tii_index": summary_only_count,
            "reviewed_benefit_keys": len(reviewed_keys),
            "candidate_keys": len(candidate_keys),
            "reviewable_proposal_keys": len(proposal_keys),
            "reviewable_candidate_or_proposal_keys": len(reviewable_keys),
            "downloaded_document_product_folders": len(downloaded_products),
            "pending_structure": pending_count + summary_only_count,
            "pending_structure_in_tii_index": pending_count,
            "pending_structure_summary_only": summary_only_count,
            "source_pending": source_count,
            "source_pending_audit_formula": audit_formula_source_pending,
            "structured_or_needs_user_input": status_counter["structured_or_needs_user_input"],
        },
        "pending_structure": {
            "group_count": len(pending_group_list),
            "priority_counts": dict(sorted(pending_priority_counter.items())),
            "candidate_ready_count": pending_priority_counter["candidate_ready"],
            "records_path": str(pending_records_path.relative_to(ROOT)),
            "summary_only_records_path": str(summary_only_records_path.relative_to(ROOT)),
            "summary_only_count": summary_only_count,
            "groups_path": str((output_dir / "pending-structure-groups.json").relative_to(ROOT)),
            "next_groups": pending_group_list[:10],
        },
        "source_pending": {
            "group_count": len(source_group_list),
            "reason_counts": dict(sorted(source_reason_counter.items())),
            "processing_gate_counts": dict(sorted(source_gate_counter.items())),
            "records_path": str(source_records_path.relative_to(ROOT)),
            "groups_path": str((output_dir / "source-pending-groups.json").relative_to(ROOT)),
            "next_groups": source_group_list[:10],
        },
        "audit_alignment": {
            "audit_path": str(audit_path.relative_to(ROOT)) if audit_path.exists() else "",
            "audit_counts": audit_counts,
            "audit_formula_source_pending": audit_formula_source_pending,
            "exact_source_pending_records_without_summary": source_count,
            "status_matches_audit": status_matches_audit,
            "note": (
                "The public audit originally computed source_pending as total record count minus "
                "summary record count. The exact queue also reports records_without_summary by "
                "batch_id + product_id, which is higher when summary-only reconciliation rows exist."
            ),
        },
        "automation_recommendation": {
            "benefit_structuring": "Run a bounded parser/proposal/review slice first; do not infer benefits from names or keyword hits.",
            "source_backfill": "Prioritize can_extract_locally, then needs_tii_document_download_captcha, then detail_missing_or_unusable.",
        },
    }
    write_json(output_dir / "status-summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-root", type=Path, default=DEFAULT_RECORDS_ROOT)
    parser.add_argument("--summary-dir", type=Path, default=DEFAULT_SUMMARY_DIR)
    parser.add_argument("--reviewed-dir", type=Path, default=DEFAULT_REVIEWED_DIR)
    parser.add_argument("--documents-root", type=Path, default=DEFAULT_DOCUMENTS_ROOT)
    parser.add_argument("--candidates-dir", type=Path, default=DEFAULT_CANDIDATES_DIR)
    parser.add_argument("--proposals-dir", type=Path, default=DEFAULT_PROPOSALS_DIR)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--progress", type=Path, default=DEFAULT_TII_PROGRESS_PATH)
    parser.add_argument("--failure-ledger", type=Path, default=DEFAULT_DETAIL_RETRY_FAILURES_PATH)
    args = parser.parse_args()

    with IntegrationLock(
        canonical_integration_lock(ROOT),
        purpose="build_tii_completion_queues",
        owner="build_tii_completion_queues.py",
    ):
        summary = build_queues(
            records_root=args.records_root,
            summary_dir=args.summary_dir,
            reviewed_dir=args.reviewed_dir,
            documents_root=args.documents_root,
            candidates_dir=args.candidates_dir,
            proposals_dir=args.proposals_dir,
            audit_path=args.audit,
            output_dir=args.output_dir,
            progress_path=args.progress,
            failure_ledger_path=args.failure_ledger,
        )
    print(
        json.dumps(
            {
                "status": "ok",
                "counts": summary["counts"],
                "pending_structure_groups": summary["pending_structure"]["group_count"],
                "source_pending_groups": summary["source_pending"]["group_count"],
                "audit_alignment": summary["audit_alignment"]["status_matches_audit"],
                "output": str(args.output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
