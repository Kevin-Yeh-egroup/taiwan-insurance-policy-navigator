from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from tii_workflow_guard import (
    IntegrationLock,
    atomic_write_json,
    atomic_write_text,
    canonical_integration_lock,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = (
    ROOT
    / "work"
    / "tii-life-calculation-readiness"
    / "parser-family-queue.json"
)
DEFAULT_LEGACY_QUEUE = (
    ROOT / "work" / "tii-benefit-candidates" / "structure-queue.json"
)
DEFAULT_CANDIDATES = ROOT / "work" / "tii-benefit-candidates" / "all-life-v3.json"
DEFAULT_RUN_DIR = ROOT / "work" / "tii-benefit-automation"
DEFAULT_APPROVAL_DIR = ROOT / "work" / "tii-benefit-approvals"
DEFAULT_PROPOSAL_DIR = ROOT / "work" / "tii-benefit-proposals"
DEFAULT_DOCUMENT_CONTENT_DIR = ROOT / "data" / "tii" / "document-content"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")


def normalize_list(values: list[str] | None) -> set[str]:
    return {value.strip() for value in values or [] if value.strip()}


def command_record(args: list[str], *, dry_run: bool = False) -> dict[str, Any]:
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    started_perf = perf_counter()
    record: dict[str, Any] = {
        "command": args,
        "started_at": started_at,
        "dry_run": dry_run,
    }
    if dry_run:
        record.update({"status": "skipped", "returncode": None})
        return record
    completed = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    record.update(
        {
            "status": "ok" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "duration_seconds": round(perf_counter() - started_perf, 3),
        }
    )
    if completed.returncode != 0:
        raise SystemExit(
            "command failed: "
            + " ".join(args)
            + "\n"
            + (completed.stdout or "")
            + (completed.stderr or "")
        )
    return record


def load_exact_slice(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    batch_id = str(payload.get("batch_id") or "").strip()
    parser_ids = {
        str(payload.get("parser_id") or "").strip()
    } - {""}
    product_rows: list[Any] = []
    for key in ("product_ids", "products", "records", "proposals"):
        value = payload.get(key)
        if isinstance(value, list):
            product_rows = value
            break

    product_ids: list[str] = []
    expected_sources: dict[str, dict[str, str]] = {}
    for row in product_rows:
        if isinstance(row, str):
            product_id = row.strip()
            candidates: list[dict[str, Any]] = []
        elif isinstance(row, dict):
            product_id = str(row.get("product_id") or "").strip()
            candidates = [
                item for item in row.get("candidates") or [] if isinstance(item, dict)
            ]
            if row.get("parser_id"):
                parser_ids.add(str(row["parser_id"]).strip())
            for candidate in candidates:
                if candidate.get("parser_id"):
                    parser_ids.add(str(candidate["parser_id"]).strip())
        else:
            continue
        if not product_id:
            continue
        product_ids.append(product_id)
        if len(candidates) == 1:
            candidate = candidates[0]
            expected_sources[product_id] = {
                "source_file": str(candidate.get("source_file") or ""),
                "source_document_sha256": str(
                    candidate.get("source_document_sha256") or ""
                ),
            }

    explicit_sources = payload.get("sources")
    if isinstance(explicit_sources, list):
        for row in explicit_sources:
            if not isinstance(row, dict):
                continue
            product_id = str(row.get("product_id") or "").strip()
            if not product_id:
                continue
            expected_sources[product_id] = {
                "source_file": str(row.get("source_file") or ""),
                "source_document_sha256": str(
                    row.get("source_document_sha256") or ""
                ),
            }

    unique_product_ids = sorted(set(product_ids))
    if not batch_id:
        raise SystemExit(f"exact slice has no batch_id: {path}")
    if len(parser_ids) != 1:
        raise SystemExit(
            f"exact slice must resolve to one parser_id, found {sorted(parser_ids)}: {path}"
        )
    if not unique_product_ids:
        raise SystemExit(f"exact slice has no product_id values: {path}")
    if len(unique_product_ids) != len(product_ids):
        raise SystemExit(f"exact slice contains duplicate product_id values: {path}")
    missing_source_expectations = [
        product_id
        for product_id in unique_product_ids
        if not expected_sources.get(product_id, {}).get("source_file")
        or not expected_sources.get(product_id, {}).get(
            "source_document_sha256"
        )
    ]
    if missing_source_expectations:
        raise SystemExit(
            "exact slice requires source_file and source_document_sha256 for "
            "every product_id; missing: "
            + ", ".join(missing_source_expectations)
        )

    return {
        "path": str(path),
        "batch_id": batch_id,
        "parser_id": next(iter(parser_ids)),
        "product_ids": unique_product_ids,
        "expected_sources": expected_sources,
        "proposal_output": str(payload.get("proposal_output") or ""),
        "review_packet_output": str(payload.get("review_packet_output") or ""),
    }


def validate_exact_slice_proposal(
    proposal_path: Path,
    exact_slice: dict[str, Any],
) -> dict[str, Any]:
    payload = read_json(proposal_path)
    expected_batch_id = exact_slice["batch_id"]
    expected_parser_id = exact_slice["parser_id"]
    expected_product_ids = set(exact_slice["product_ids"])
    proposals = [
        item for item in payload.get("proposals") or [] if isinstance(item, dict)
    ]
    proposal_product_ids = [
        str(item.get("product_id") or "") for item in proposals
    ]
    actual_product_ids = {
        product_id for product_id in proposal_product_ids if product_id
    }
    errors: list[str] = []
    if str(payload.get("batch_id") or "") != expected_batch_id:
        errors.append("batch_id_mismatch")
    if actual_product_ids != expected_product_ids:
        missing = sorted(expected_product_ids - actual_product_ids)
        unexpected = sorted(actual_product_ids - expected_product_ids)
        if missing:
            errors.append("missing_product_ids=" + ",".join(missing))
        if unexpected:
            errors.append("unexpected_product_ids=" + ",".join(unexpected))
    duplicate_product_ids = sorted(
        product_id
        for product_id, count in Counter(proposal_product_ids).items()
        if product_id and count > 1
    )
    if duplicate_product_ids:
        errors.append(
            "duplicate_product_ids=" + ",".join(duplicate_product_ids)
        )
    if any(not product_id for product_id in proposal_product_ids):
        errors.append("proposal_row_missing_product_id")

    expected_sources = exact_slice.get("expected_sources") or {}
    verified_source_count = 0
    for proposal in proposals:
        product_id = str(proposal.get("product_id") or "")
        candidates = [
            item for item in proposal.get("candidates") or [] if isinstance(item, dict)
        ]
        if proposal.get("status") != "proposed":
            errors.append(f"{product_id}:status={proposal.get('status')}")
        if proposal.get("candidate_count") != 1 or len(candidates) != 1:
            errors.append(f"{product_id}:candidate_count_not_one")
            continue
        candidate = candidates[0]
        if str(candidate.get("parser_id") or "") != expected_parser_id:
            errors.append(f"{product_id}:parser_id_mismatch")
        if not candidate.get("source_document_sha256"):
            errors.append(f"{product_id}:missing_source_document_sha256")
        if not candidate.get("schedule_sha256"):
            errors.append(f"{product_id}:missing_schedule_sha256")
        expected_source = expected_sources.get(product_id)
        if expected_source:
            for field in ("source_file", "source_document_sha256"):
                expected_value = str(expected_source.get(field) or "")
                if expected_value and str(candidate.get(field) or "") != expected_value:
                    errors.append(f"{product_id}:{field}_mismatch")
            verified_source_count += 1

    if errors:
        raise SystemExit(
            f"exact slice proposal validation failed for {proposal_path}: "
            + "; ".join(errors)
        )
    return {
        "status": "ok",
        "batch_id": expected_batch_id,
        "parser_id": expected_parser_id,
        "product_count": len(expected_product_ids),
        "source_expectation_count": len(expected_sources),
        "verified_source_count": verified_source_count,
    }


def load_queue(queue_path: Path) -> list[dict[str, Any]]:
    payload = read_json(queue_path)
    queue = payload.get("groups")
    queue_kind = "parser_family"
    if queue is None:
        queue = payload.get("queue") or []
        queue_kind = "legacy_structure"
    if not isinstance(queue, list):
        raise SystemExit(f"queue/groups field is not a list: {queue_path}")
    normalized: list[dict[str, Any]] = []
    for item in queue:
        if not isinstance(item, dict):
            continue
        if queue_kind == "legacy_structure":
            normalized.append({**item, "queue_kind": queue_kind})
            continue
        batch_id = str(item.get("batch_id") or "")
        company = str(item.get("company") or "")
        sample_versions = [
            row
            for row in item.get("sample_versions") or []
            if isinstance(row, dict)
        ]
        sample_products = list(
            dict.fromkeys(
                str(row.get("product_name") or "")
                for row in sample_versions
                if row.get("product_name")
            )
        )
        record_count = int(item.get("record_count") or 0)
        normalized.append(
            {
                **item,
                "queue_kind": queue_kind,
                "candidate_product_count": record_count,
                "candidate_document_count": record_count,
                "batch_ids": [batch_id] if batch_id else [],
                "companies": [company] if company else [],
                "sample_products": sample_products,
            }
        )
    return normalized


def validate_work_claim(
    claim_path: Path,
    *,
    queue_path: Path,
    queue: list[dict[str, Any]],
    task_id: str,
) -> dict[str, Any]:
    if not task_id.strip():
        raise SystemExit("--task-id is required with --claim-file")
    claim = read_json(claim_path)
    if claim.get("status") != "claimed":
        raise SystemExit(f"claim is not active: {claim_path}")
    try:
        expires_at = datetime.fromisoformat(str(claim.get("expires_at") or ""))
    except ValueError as error:
        raise SystemExit(f"claim has invalid expires_at: {claim_path}") from error
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise SystemExit(f"claim has expired: {claim_path}")
    if str(claim.get("task_id") or "") != task_id.strip():
        raise SystemExit("claim belongs to a different task_id")

    expected_queue_hash = str(claim.get("queue_sha256") or "")
    actual_queue_hash = sha256_file(queue_path)
    if not expected_queue_hash or expected_queue_hash != actual_queue_hash:
        raise SystemExit(
            "claim queue hash no longer matches the current queue; "
            "release or renew the work from a rebuilt queue"
        )

    queue_id = str(claim.get("queue_id") or "")
    matching_groups = [
        group for group in queue if str(group.get("queue_id") or "") == queue_id
    ]
    if len(matching_groups) != 1:
        raise SystemExit(
            f"claim queue_id must resolve to exactly one current group: {queue_id}"
        )
    group = matching_groups[0]
    claim_product_ids = {
        str(value) for value in claim.get("product_ids") or [] if str(value)
    }
    group_product_ids = {
        str(value) for value in group.get("product_ids") or [] if str(value)
    }
    if not claim_product_ids or claim_product_ids != group_product_ids:
        raise SystemExit("claim product_ids no longer match the current queue group")
    if str(claim.get("batch_id") or "") != str(group.get("batch_id") or ""):
        raise SystemExit("claim batch_id no longer matches the current queue group")

    return {
        "claim_path": str(claim_path),
        "claim_id": str(claim.get("claim_id") or ""),
        "task_id": str(claim.get("task_id") or ""),
        "owner": str(claim.get("owner") or ""),
        "expires_at": claim.get("expires_at"),
        "queue_sha256": actual_queue_hash,
        "queue_id": queue_id,
        "batch_id": str(claim.get("batch_id") or ""),
        "product_ids": sorted(claim_product_ids),
        "group": group,
    }


def summarize_queue(queue: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"groups": 0, "products": 0, "documents": 0}
    )
    batch_counts: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"groups": 0, "products": 0, "documents": 0, "categories": Counter()}
    )
    company_counts: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"groups": 0, "products": 0, "documents": 0, "categories": Counter()}
    )
    batch_ids: set[str] = set()
    companies: set[str] = set()
    for group in queue:
        category = str(group.get("insurance_category") or "")
        products = int(group.get("candidate_product_count") or 0)
        documents = int(group.get("candidate_document_count") or 0)
        category_counts[category]["groups"] += 1
        category_counts[category]["products"] += products
        category_counts[category]["documents"] += documents
        for batch_id in group.get("batch_ids") or []:
            batch_ids.add(str(batch_id))
            item = batch_counts[str(batch_id)]
            item["groups"] += 1
            item["products"] += products
            item["documents"] += documents
            item["categories"][category] += 1
        for company in group.get("companies") or []:
            companies.add(str(company))
            item = company_counts[str(company)]
            item["groups"] += 1
            item["products"] += products
            item["documents"] += documents
            item["categories"][category] += 1

    def flatten_counter_map(value: dict[str, Any]) -> dict[str, Any]:
        return {
            key: {
                field: dict(counts) if isinstance(counts, Counter) else counts
                for field, counts in item.items()
            }
            for key, item in sorted(value.items(), key=lambda pair: (-pair[1]["groups"], pair[0]))
        }

    return {
        "queue_kind": (
            next(iter({str(group.get("queue_kind") or "") for group in queue}))
            if len({str(group.get("queue_kind") or "") for group in queue}) == 1
            else "mixed"
        ),
        "groups": len(queue),
        "products": sum(int(group.get("candidate_product_count") or 0) for group in queue),
        "documents": sum(int(group.get("candidate_document_count") or 0) for group in queue),
        "batches": len(batch_ids),
        "companies": len(companies),
        "by_category": dict(sorted(category_counts.items(), key=lambda pair: (-pair[1]["groups"], pair[0]))),
        "top_batches": flatten_counter_map(dict(batch_counts)),
        "top_companies": flatten_counter_map(dict(company_counts)),
    }


def select_groups(
    queue: list[dict[str, Any]],
    *,
    categories: set[str],
    batch_ids: set[str],
    company_terms: set[str],
    max_groups: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for group in queue:
        category = str(group.get("insurance_category") or "")
        batches = {str(batch_id) for batch_id in group.get("batch_ids") or []}
        companies = [str(company) for company in group.get("companies") or []]
        if categories and category not in categories:
            continue
        if batch_ids and not batches.intersection(batch_ids):
            continue
        if company_terms and not any(
            any(term in company for term in company_terms) for company in companies
        ):
            continue
        selected.append(group)
        if len(selected) >= max_groups:
            break
    return selected


def selected_batch_ids(groups: list[dict[str, Any]]) -> list[str]:
    return sorted({str(batch_id) for group in groups for batch_id in group.get("batch_ids") or []})


def load_policy_records(
    batch_ids: list[str],
    *,
    document_content_dir: Path = DEFAULT_DOCUMENT_CONTENT_DIR,
) -> dict[str, list[dict[str, Any]]]:
    records_by_batch: dict[str, list[dict[str, Any]]] = {}
    for batch_id in batch_ids:
        path = document_content_dir / f"{batch_id}.json"
        if not path.is_file():
            records_by_batch[batch_id] = []
            continue
        payload = read_json(path)
        records: list[dict[str, Any]] = []
        for record in payload.get("records") or []:
            if not isinstance(record, dict):
                continue
            policy_terms = [
                document
                for document in record.get("documents") or []
                if isinstance(document, dict)
                and document.get("document_type") == "policy_terms"
            ]
            records.append(
                {
                    "batch_id": batch_id,
                    "product_id": str(record.get("product_id") or ""),
                    "product_name": str(record.get("product_name") or ""),
                    "policy_terms_count": len(policy_terms),
                    "policy_term_files": [
                        str(document.get("file_name") or "")
                        for document in policy_terms
                        if document.get("file_name")
                    ],
                }
            )
        records_by_batch[batch_id] = records
    return records_by_batch


def load_proposal_index(
    batch_ids: list[str],
    *,
    proposal_dir: Path = DEFAULT_PROPOSAL_DIR,
) -> dict[tuple[str, str], dict[str, Any]]:
    proposal_index: dict[tuple[str, str], dict[str, Any]] = {}
    for batch_id in batch_ids:
        path = proposal_dir / f"{batch_id}.json"
        if not path.is_file():
            continue
        payload = read_json(path)
        for proposal in payload.get("proposals") or []:
            if not isinstance(proposal, dict):
                continue
            product_id = str(proposal.get("product_id") or "")
            candidates = [
                candidate
                for candidate in proposal.get("candidates") or []
                if isinstance(candidate, dict)
            ]
            proposal_index[(batch_id, product_id)] = {
                "batch_id": batch_id,
                "product_id": product_id,
                "status": proposal.get("status"),
                "candidate_count": proposal.get("candidate_count"),
                "parser_ids": sorted(
                    {
                        str(candidate.get("parser_id") or "")
                        for candidate in candidates
                        if candidate.get("parser_id")
                    }
                ),
            }
    return proposal_index


def audit_proposal_gaps(
    groups: list[dict[str, Any]],
    *,
    document_content_dir: Path = DEFAULT_DOCUMENT_CONTENT_DIR,
    proposal_dir: Path = DEFAULT_PROPOSAL_DIR,
) -> dict[str, Any]:
    batches = selected_batch_ids(groups)
    records_by_batch = load_policy_records(
        batches,
        document_content_dir=document_content_dir,
    )
    proposal_index = load_proposal_index(batches, proposal_dir=proposal_dir)
    with_proposal: list[dict[str, Any]] = []
    missing_proposal: list[dict[str, Any]] = []
    ambiguous_name_matches: list[dict[str, Any]] = []
    missing_name_matches: list[dict[str, Any]] = []

    for group in groups:
        group_batches = [str(batch_id) for batch_id in group.get("batch_ids") or []]
        group_records = [
            record
            for batch_id in group_batches
            for record in records_by_batch.get(batch_id, [])
        ]
        for product_name in group.get("sample_products") or []:
            name = str(product_name or "")
            matches = [
                record
                for record in group_records
                if record.get("product_name") == name
            ]
            if not matches:
                missing_name_matches.append(
                    {
                        "queue_id": group.get("queue_id"),
                        "insurance_category": group.get("insurance_category"),
                        "product_name": name,
                        "batch_ids": group_batches,
                    }
                )
                continue
            if len(matches) > 1:
                ambiguous_name_matches.append(
                    {
                        "queue_id": group.get("queue_id"),
                        "insurance_category": group.get("insurance_category"),
                        "product_name": name,
                        "matches": matches,
                    }
                )
                continue
            record = matches[0]
            key = (str(record["batch_id"]), str(record["product_id"]))
            proposal = proposal_index.get(key)
            item = {
                "queue_id": group.get("queue_id"),
                "insurance_category": group.get("insurance_category"),
                "batch_id": record["batch_id"],
                "product_id": record["product_id"],
                "product_name": record["product_name"],
                "policy_terms_count": record["policy_terms_count"],
                "policy_term_files": record["policy_term_files"],
            }
            if proposal:
                with_proposal.append({**item, "proposal": proposal})
            else:
                missing_proposal.append(item)

    def count_by(items: list[dict[str, Any]], field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(item.get(field) or "") for item in items).items()))

    return {
        "target_products": len(with_proposal)
        + len(missing_proposal)
        + len(ambiguous_name_matches)
        + len(missing_name_matches),
        "with_proposal_count": len(with_proposal),
        "missing_proposal_count": len(missing_proposal),
        "ambiguous_name_match_count": len(ambiguous_name_matches),
        "missing_name_match_count": len(missing_name_matches),
        "with_proposal": with_proposal,
        "missing_proposal": missing_proposal,
        "ambiguous_name_matches": ambiguous_name_matches,
        "missing_name_matches": missing_name_matches,
        "missing_by_batch": count_by(missing_proposal, "batch_id"),
        "missing_by_category": count_by(missing_proposal, "insurance_category"),
        "proposal_by_batch": count_by(with_proposal, "batch_id"),
        "proposal_by_category": count_by(with_proposal, "insurance_category"),
    }


def refresh_queue(candidates_path: Path, output_path: Path) -> list[dict[str, Any]]:
    if (
        output_path.name == "parser-family-queue.json"
        or output_path.resolve() == DEFAULT_QUEUE.resolve()
    ):
        return [
            command_record(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\audit_tii_life_calculation_readiness.py",
                ]
            ),
            command_record(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\build_tii_parser_family_queue.py",
                    "--output",
                    str(output_path),
                ]
            ),
        ]
    commands = [
        command_record(
            [
                sys.executable,
                "-X",
                "utf8",
                "scripts\\build_tii_benefit_queue.py",
                "--candidates",
                str(candidates_path),
                "--output",
                str(output_path),
            ]
        )
    ]
    return commands


def prepare_proposals(
    batch_ids: list[str],
    *,
    write_proposals: bool,
    product_ids: list[str] | None = None,
    parser_id: str | None = None,
    proposal_output: Path | None = None,
) -> list[dict[str, Any]]:
    if proposal_output and len(batch_ids) != 1:
        raise SystemExit("--proposal-output requires exactly one selected batch")
    commands = []
    for batch_id in batch_ids:
        args = [
            sys.executable,
            "-X",
            "utf8",
            "scripts\\extract_tii_plan_benefits.py",
            "--batch-id",
            batch_id,
        ]
        if parser_id:
            args.extend(["--parser-id", parser_id])
        for product_id in product_ids or []:
            args.extend(["--product-id", product_id])
        if product_ids:
            args.append("--require-all-product-ids")
        if proposal_output:
            args.extend(["--proposal-output", str(proposal_output)])
        if not write_proposals:
            args.append("--dry-run")
        commands.append(command_record(args))
    return commands


def prepare_exact_slice(
    exact_slice: dict[str, Any],
    *,
    write_proposals: bool,
    proposal_output: Path | None,
    review_packet_output: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    final_output = proposal_output
    if final_output is None and exact_slice.get("proposal_output"):
        final_output = Path(exact_slice["proposal_output"])
    if write_proposals and final_output is None:
        raise SystemExit(
            "exact slice writes require --proposal-output or proposal_output in the slice"
        )

    command_output = final_output
    pending_output: Path | None = None
    lock_path: Path | None = None
    if write_proposals and final_output:
        final_output.parent.mkdir(parents=True, exist_ok=True)
        lock_path = final_output.with_name(final_output.name + ".lock")
        try:
            with lock_path.open("x", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "pid": os.getpid(),
                            "created_at": datetime.now()
                            .astimezone()
                            .isoformat(timespec="seconds"),
                            "target": str(final_output),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except FileExistsError as error:
            raise SystemExit(
                f"exact proposal target is already locked: {lock_path}"
            ) from error
        pending_output = final_output.with_name(
            f".{final_output.name}.{uuid4().hex}.pending"
        )
        command_output = pending_output

    try:
        commands = prepare_proposals(
            [exact_slice["batch_id"]],
            write_proposals=write_proposals,
            product_ids=exact_slice["product_ids"],
            parser_id=exact_slice["parser_id"],
            proposal_output=command_output,
        )
        validation = None
        if write_proposals and pending_output and final_output:
            validation = validate_exact_slice_proposal(
                pending_output, exact_slice
            )
            pending_output.replace(final_output)
            packet_output = review_packet_output
            if packet_output is None and exact_slice.get(
                "review_packet_output"
            ):
                packet_output = Path(exact_slice["review_packet_output"])
            if packet_output:
                commands.append(
                    command_record(
                        [
                            sys.executable,
                            "-X",
                            "utf8",
                            "scripts\\build_tii_proposal_review_packet.py",
                            "--proposal",
                            str(final_output),
                            "--output-dir",
                            str(packet_output),
                        ]
                    )
                )
        return commands, validation
    finally:
        if pending_output:
            pending_output.unlink(missing_ok=True)
        if lock_path:
            lock_path.unlink(missing_ok=True)


def approval_files_for_batches(approval_dir: Path, batch_ids: list[str], *, all_files: bool) -> list[Path]:
    files = sorted(approval_dir.glob("*.json"))
    if all_files:
        return files
    if not batch_ids:
        return []
    selected = set(batch_ids)
    matched = []
    for path in files:
        try:
            payload = read_json(path)
        except Exception:
            continue
        if str(payload.get("batch_id") or "") in selected:
            matched.append(path)
    return matched


def promote_approved(approval_files: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    commands = []
    touched_batches: set[str] = set()
    for approval_file in approval_files:
        payload = read_json(approval_file)
        batch_id = str(payload.get("batch_id") or "")
        if not batch_id:
            raise SystemExit(f"approval file has no batch_id: {approval_file}")
        touched_batches.add(batch_id)
        commands.append(
            command_record(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\extract_tii_plan_benefits.py",
                    "--batch-id",
                    batch_id,
                    "--approval-file",
                    str(approval_file),
                ]
            )
        )
    for batch_id in sorted(touched_batches):
        commands.append(
            command_record(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "scripts\\build_tii_document_summaries.py",
                    "--batch-id",
                    batch_id,
                ]
            )
        )
    return commands, sorted(touched_batches)


def verify_commands(*, full_parser_tests: bool) -> list[dict[str, Any]]:
    commands = [
        command_record([sys.executable, "-X", "utf8", "scripts\\validate_data.py"]),
        command_record([sys.executable, "-X", "utf8", "scripts\\test_tii_benefit_queue.py"]),
        command_record(
            [sys.executable, "-X", "utf8", "scripts\\test_tii_benefit_batch_task.py"]
        ),
        command_record(
            [sys.executable, "-X", "utf8", "scripts\\test_tii_proposal_review_packet.py"]
        ),
        command_record(
            [sys.executable, "-X", "utf8", "scripts\\test_tii_parser_family_queue.py"]
        ),
        command_record(
            [sys.executable, "-X", "utf8", "scripts\\test_tii_life_calculation_readiness.py"]
        ),
        command_record([sys.executable, "-X", "utf8", "scripts\\test_tii_document_content.py"]),
        command_record(
            [
                sys.executable,
                "-X",
                "utf8",
                "scripts\\test_tii_strict_source_text_cache.py",
            ]
        ),
        command_record(["node", "scripts\\test_coverage_model.js"]),
    ]
    if full_parser_tests:
        commands.append(
            command_record([sys.executable, "-X", "utf8", "scripts\\test_tii_plan_benefits.py"])
        )
    return commands


def build_report_markdown(payload: dict[str, Any]) -> str:
    queue = payload["queue_summary"]
    selected = payload["selected_groups"]
    lines = [
        "# TII Benefit Batch Automation Run",
        "",
        f"- Run id: `{payload['run_id']}`",
        f"- Action: `{payload['action']}`",
        f"- Generated at: `{payload['generated_at']}`",
        "",
        "## Queue Snapshot",
        "",
        f"- Queue type: `{queue['queue_kind']}`",
        f"- Remaining parser/work groups: `{queue['groups']}`",
        f"- Remaining product documents: `{queue['products']}`",
        f"- Remaining source documents: `{queue['documents']}`",
        f"- Remaining batches: `{queue['batches']}`",
        f"- Remaining companies: `{queue['companies']}`",
        "",
        "## By Category",
        "",
        "| Category | Groups | Products | Documents |",
        "| --- | ---: | ---: | ---: |",
    ]
    for category, stats in queue["by_category"].items():
        lines.append(
            f"| {category} | {stats['groups']} | {stats['products']} | {stats['documents']} |"
        )
    lines.extend(["", "## Selected Groups", ""])
    if not selected:
        lines.append("- No groups selected by the current filters.")
    for index, group in enumerate(selected, start=1):
        products = group.get("candidate_product_count")
        documents = group.get("candidate_document_count")
        lines.extend(
            [
                f"### {index}. {group.get('queue_id')}",
                "",
                f"- Category: {group.get('insurance_category')}",
                f"- Products: `{products}`",
                f"- Documents: `{documents}`",
                f"- Batches: `{', '.join(group.get('batch_ids') or [])}`",
                f"- Companies: `{', '.join(group.get('companies') or [])}`",
                f"- Samples: {', '.join(group.get('sample_products') or [])}",
                "",
            ]
        )
    audit = payload.get("proposal_gap_audit")
    if audit:
        lines.extend(
            [
                "## Proposal Gap Audit",
                "",
                f"- Target products checked: `{audit['target_products']}`",
                f"- Products with proposal: `{audit['with_proposal_count']}`",
                f"- Products missing proposal: `{audit['missing_proposal_count']}`",
                f"- Ambiguous name matches: `{audit['ambiguous_name_match_count']}`",
                f"- Missing name matches: `{audit['missing_name_match_count']}`",
                "",
                "### Missing Proposal By Batch",
                "",
            ]
        )
        if audit["missing_by_batch"]:
            for batch_id, count in audit["missing_by_batch"].items():
                lines.append(f"- `{batch_id}`: `{count}`")
        else:
            lines.append("- No missing proposals for selected products.")
        if audit["missing_proposal"]:
            lines.extend(["", "### Missing Proposal Products", ""])
            for item in audit["missing_proposal"][:40]:
                lines.append(
                    "- "
                    f"`{item['batch_id']}` / `{item['product_id']}`: "
                    f"{item['product_name']}"
                )
            if len(audit["missing_proposal"]) > 40:
                lines.append(
                    f"- ...and `{len(audit['missing_proposal']) - 40}` more."
                )
        lines.append("")
    lines.extend(["## Command Results", ""])
    for command in payload.get("commands") or []:
        status = command.get("status")
        returncode = command.get("returncode")
        command_text = " ".join(command.get("command") or [])
        duration = command.get("duration_seconds")
        duration_text = f" ({duration:.3f}s)" if duration is not None else ""
        lines.append(
            f"- `{status}` rc=`{returncode}`: `{command_text}`{duration_text}"
        )
    exact_validation = payload.get("exact_slice_validation")
    if exact_validation:
        lines.extend(
            [
                "",
                "## Exact Slice Validation",
                "",
                f"- Batch: `{exact_validation['batch_id']}`",
                f"- Parser: `{exact_validation['parser_id']}`",
                f"- Products: `{exact_validation['product_count']}`",
                f"- Source expectations verified: `{exact_validation['verified_source_count']}` / `{exact_validation['source_expectation_count']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Safety Gates",
            "",
            "- This task may generate proposals and apply existing approval files.",
            "- It does not approve new benefit schedules by itself.",
            "- It does not commit, push, or deploy.",
            "- Public summaries should be rebuilt only from reviewed schedules.",
            "",
            "## Next Recommended Move",
            "",
            payload.get("next_move") or "- Continue with the first selected group.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a bounded, resumable TII benefit-structuring batch task."
    )
    parser.add_argument(
        "--action",
        choices=[
            "plan",
            "refresh-queue",
            "prepare-proposals",
            "promote-approved",
            "verify",
            "audit-gaps",
            "all",
        ],
        default="plan",
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--approval-dir", type=Path, default=DEFAULT_APPROVAL_DIR)
    parser.add_argument("--proposal-dir", type=Path, default=DEFAULT_PROPOSAL_DIR)
    parser.add_argument(
        "--document-content-dir",
        type=Path,
        default=DEFAULT_DOCUMENT_CONTENT_DIR,
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument(
        "--claim-file",
        type=Path,
        help="Active parser-family claim; binds this run to its queue hash and products.",
    )
    parser.add_argument(
        "--task-id",
        default="",
        help="Owning task id; required with --claim-file.",
    )
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--batch-id", action="append", default=[])
    parser.add_argument(
        "--parser-id",
        help="Run one exact parser family; strongly recommended with product slices.",
    )
    parser.add_argument(
        "--product-id",
        action="append",
        default=[],
        help="Limit proposal generation to exact product_id values for small slices.",
    )
    parser.add_argument(
        "--exact-slice",
        type=Path,
        help="JSON manifest or prior proposal defining one batch, parser, exact products, and optional source hashes.",
    )
    parser.add_argument(
        "--proposal-output",
        type=Path,
        help="Exact proposal output path; required when writing an exact slice unless the manifest defines it.",
    )
    parser.add_argument(
        "--review-packet-output",
        type=Path,
        help="Build a human source-review packet after an exact proposal passes validation.",
    )
    parser.add_argument("--company-term", action="append", default=[])
    parser.add_argument("--max-groups", type=int, default=5)
    parser.add_argument(
        "--write-proposals",
        action="store_true",
        help="Write proposal files instead of only dry-running proposal generation.",
    )
    parser.add_argument(
        "--all-approval-files",
        action="store_true",
        help="Promote every approval file instead of only selected batches.",
    )
    parser.add_argument(
        "--full-parser-tests",
        action="store_true",
        help="Also run the slower full parser regression suite.",
    )
    args = parser.parse_args()

    if args.max_groups <= 0:
        raise SystemExit("--max-groups must be positive")

    integration_lock: IntegrationLock | None = None
    if args.action in {"refresh-queue", "promote-approved", "all"} or (
        args.action == "prepare-proposals" and args.write_proposals
    ):
        integration_lock = IntegrationLock(
            canonical_integration_lock(ROOT),
            purpose=f"run_tii_benefit_batch_task:{args.action}",
            owner="run_tii_benefit_batch_task.py",
        ).acquire()
        atexit.register(integration_lock.release)

    run_path = args.run_dir / "runs" / run_id()
    commands: list[dict[str, Any]] = []
    exact_slice = load_exact_slice(args.exact_slice) if args.exact_slice else None
    if exact_slice:
        if args.action not in {"plan", "prepare-proposals"}:
            raise SystemExit(
                "--exact-slice supports plan or prepare-proposals only; "
                "run promotion and verification as separate explicit gates"
            )
        requested_batches = normalize_list(args.batch_id)
        if requested_batches and requested_batches != {exact_slice["batch_id"]}:
            raise SystemExit("--batch-id conflicts with the exact slice batch_id")
        if args.parser_id and args.parser_id != exact_slice["parser_id"]:
            raise SystemExit("--parser-id conflicts with the exact slice parser_id")
        requested_products = normalize_list(args.product_id)
        if requested_products and requested_products != set(exact_slice["product_ids"]):
            raise SystemExit("--product-id values conflict with the exact slice")

    if args.action in {"refresh-queue", "all"}:
        commands.extend(refresh_queue(args.candidates, args.queue))

    queue = load_queue(args.queue)
    work_claim = (
        validate_work_claim(
            args.claim_file,
            queue_path=args.queue,
            queue=queue,
            task_id=args.task_id,
        )
        if args.claim_file
        else None
    )
    if work_claim:
        claimed_group = work_claim["group"]
        selected = select_groups(
            [claimed_group],
            categories=normalize_list(args.category),
            batch_ids=normalize_list(args.batch_id),
            company_terms=normalize_list(args.company_term),
            max_groups=1,
        )
        if not selected:
            raise SystemExit("requested filters conflict with the active claim")
        requested_products = normalize_list(args.product_id)
        if requested_products and not requested_products.issubset(
            set(work_claim["product_ids"])
        ):
            raise SystemExit("--product-id contains values outside the active claim")
        if exact_slice and not set(exact_slice["product_ids"]).issubset(
            set(work_claim["product_ids"])
        ):
            raise SystemExit("--exact-slice contains values outside the active claim")
    else:
        selected = select_groups(
            queue,
            categories=normalize_list(args.category),
            batch_ids=normalize_list(args.batch_id),
            company_terms=normalize_list(args.company_term),
            max_groups=args.max_groups,
        )
    requested_batches = normalize_list(args.batch_id)
    if exact_slice:
        batches = [exact_slice["batch_id"]]
    elif requested_batches:
        batches = sorted(requested_batches)
    else:
        batches = selected_batch_ids(selected)
    exact_slice_validation: dict[str, Any] | None = None

    if args.action in {"prepare-proposals", "all"} and batches:
        if exact_slice:
            exact_commands, exact_slice_validation = prepare_exact_slice(
                exact_slice,
                write_proposals=args.write_proposals,
                proposal_output=args.proposal_output,
                review_packet_output=args.review_packet_output,
            )
            commands.extend(exact_commands)
        else:
            commands.extend(
                prepare_proposals(
                    batches,
                    write_proposals=args.write_proposals,
                    product_ids=sorted(normalize_list(args.product_id)),
                    parser_id=args.parser_id,
                    proposal_output=args.proposal_output,
                )
            )

    proposal_gap_audit: dict[str, Any] | None = None
    if args.action in {"audit-gaps", "all"}:
        proposal_gap_audit = audit_proposal_gaps(
            selected,
            document_content_dir=args.document_content_dir,
            proposal_dir=args.proposal_dir,
        )

    touched_batches: list[str] = []
    if args.action in {"promote-approved", "all"}:
        if (
            args.action == "promote-approved"
            and not batches
            and not args.all_approval_files
        ):
            raise SystemExit(
                "promote-approved requires --batch-id or explicit "
                "--all-approval-files"
            )
        approval_files = approval_files_for_batches(
            args.approval_dir,
            batches,
            all_files=args.all_approval_files,
        )
        promotion_commands, touched_batches = promote_approved(approval_files)
        commands.extend(promotion_commands)
        if touched_batches:
            commands.extend(refresh_queue(args.candidates, args.queue))
            queue = load_queue(args.queue)

    if args.action in {"verify", "all"}:
        commands.extend(verify_commands(full_parser_tests=args.full_parser_tests))

    queue_summary = summarize_queue(queue)
    if exact_slice and exact_slice_validation:
        next_move = (
            "Review the exact-source packet. Create approval entries only after "
            "human source review, then run promotion and verification as separate gates."
        )
    elif exact_slice:
        next_move = (
            "Run the exact slice with --action prepare-proposals --write-proposals "
            "and an explicit proposal output."
        )
    elif selected:
        next_move = (
            "Review the first selected queue group, implement or reuse a parser, then "
            "run this task again with --action prepare-proposals --write-proposals."
        )
    else:
        next_move = (
            "No selected parser/work groups remain. Check readiness and source-pending "
            "queues before treating queue zero as completion."
        )
    payload = {
        "schema_version": 1,
        "run_id": run_path.name,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "action": args.action,
        "filters": {
            "category": args.category,
            "batch_id": args.batch_id,
            "product_id": args.product_id,
            "parser_id": args.parser_id,
            "exact_slice": str(args.exact_slice) if args.exact_slice else None,
            "claim_file": str(args.claim_file) if args.claim_file else None,
            "task_id": args.task_id or None,
            "company_term": args.company_term,
            "max_groups": args.max_groups,
        },
        "queue_path": str(args.queue),
        "candidate_path": str(args.candidates),
        "proposal_dir": str(args.proposal_dir),
        "document_content_dir": str(args.document_content_dir),
        "queue_summary": queue_summary,
        "selected_batch_ids": batches,
        "selected_groups": selected,
        "proposal_gap_audit": proposal_gap_audit,
        "exact_slice_validation": exact_slice_validation,
        "work_claim": (
            {key: value for key, value in work_claim.items() if key != "group"}
            if work_claim
            else None
        ),
        "touched_batches": touched_batches,
        "commands": commands,
        "next_move": next_move,
    }
    write_json(run_path / "run.json", payload)
    atomic_write_text(run_path / "report.md", build_report_markdown(payload))
    write_json(args.run_dir / "latest.json", payload)
    atomic_write_text(args.run_dir / "latest.md", build_report_markdown(payload))

    if integration_lock:
        integration_lock.release()
        atexit.unregister(integration_lock.release)

    print(
        json.dumps(
            {
                "status": "ok",
                "action": args.action,
                "queue_groups": queue_summary["groups"],
                "queue_products": queue_summary["products"],
                "selected_groups": len(selected),
                "selected_batch_ids": batches,
                "proposal_gap_audit": {
                    "target_products": proposal_gap_audit["target_products"],
                    "with_proposal_count": proposal_gap_audit[
                        "with_proposal_count"
                    ],
                    "missing_proposal_count": proposal_gap_audit[
                        "missing_proposal_count"
                    ],
                }
                if proposal_gap_audit
                else None,
                "touched_batches": touched_batches,
                "exact_slice_validation": exact_slice_validation,
                "command_count": len(commands),
                "report": str(run_path / "report.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
