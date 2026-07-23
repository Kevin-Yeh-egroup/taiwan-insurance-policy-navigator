from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "work" / "tii-benefit-candidates" / "structure-queue.json"
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def normalize_list(values: list[str] | None) -> set[str]:
    return {value.strip() for value in values or [] if value.strip()}


def command_record(args: list[str], *, dry_run: bool = False) -> dict[str, Any]:
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
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


def load_queue(queue_path: Path) -> list[dict[str, Any]]:
    payload = read_json(queue_path)
    queue = payload.get("queue") or []
    if not isinstance(queue, list):
        raise SystemExit(f"queue field is not a list: {queue_path}")
    return [item for item in queue if isinstance(item, dict)]


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


def prepare_proposals(batch_ids: list[str], *, write_proposals: bool) -> list[dict[str, Any]]:
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
        if not write_proposals:
            args.append("--dry-run")
        commands.append(command_record(args))
    return commands


def approval_files_for_batches(approval_dir: Path, batch_ids: list[str], *, all_files: bool) -> list[Path]:
    files = sorted(approval_dir.glob("*.json"))
    if all_files or not batch_ids:
        return files
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
        command_record([sys.executable, "-X", "utf8", "scripts\\test_tii_document_content.py"]),
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
        f"- Remaining template groups: `{queue['groups']}`",
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
        lines.append(f"- `{status}` rc=`{returncode}`: `{command_text}`")
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
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--batch-id", action="append", default=[])
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

    run_path = args.run_dir / "runs" / run_id()
    commands: list[dict[str, Any]] = []

    if args.action in {"refresh-queue", "all"}:
        commands.extend(refresh_queue(args.candidates, args.queue))

    queue = load_queue(args.queue)
    selected = select_groups(
        queue,
        categories=normalize_list(args.category),
        batch_ids=normalize_list(args.batch_id),
        company_terms=normalize_list(args.company_term),
        max_groups=args.max_groups,
    )
    batches = selected_batch_ids(selected)

    if args.action in {"prepare-proposals", "all"} and batches:
        commands.extend(prepare_proposals(batches, write_proposals=args.write_proposals))

    proposal_gap_audit: dict[str, Any] | None = None
    if args.action in {"audit-gaps", "all"}:
        proposal_gap_audit = audit_proposal_gaps(
            selected,
            document_content_dir=args.document_content_dir,
            proposal_dir=args.proposal_dir,
        )

    touched_batches: list[str] = []
    if args.action in {"promote-approved", "all"}:
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
    next_move = (
        "Review the first selected queue group, implement or reuse a parser, then "
        "run this task again with --action prepare-proposals --write-proposals."
        if selected
        else "No selected groups remain for the current filters. Relax filters or refresh the queue."
    )
    payload = {
        "schema_version": 1,
        "run_id": run_path.name,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "action": args.action,
        "filters": {
            "category": args.category,
            "batch_id": args.batch_id,
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
        "touched_batches": touched_batches,
        "commands": commands,
        "next_move": next_move,
    }
    write_json(run_path / "run.json", payload)
    (run_path / "report.md").write_text(build_report_markdown(payload), encoding="utf-8")
    write_json(args.run_dir / "latest.json", payload)
    (args.run_dir / "latest.md").write_text(build_report_markdown(payload), encoding="utf-8")

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
                "command_count": len(commands),
                "report": str(run_path / "report.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
