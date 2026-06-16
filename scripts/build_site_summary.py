from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_optional_json(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def latest_run_for_batch(progress: dict, batch_id: str) -> dict:
    if not batch_id:
        return {}
    for run in reversed(progress.get("runs", [])):
        if run.get("batch_id") == batch_id:
            return run
    return {}


def active_captcha_runs(progress: dict, completed_batch_ids: set[str]) -> list[dict]:
    return [
        run
        for run in progress.get("runs", [])
        if run.get("batch_id") not in completed_batch_ids and run.get("status") == "captcha_required"
    ]


def latest_captcha_run(progress: dict, completed_batch_ids: set[str]) -> dict:
    return max(
        active_captcha_runs(progress, completed_batch_ids),
        key=lambda run: run.get("ran_at", ""),
        default={},
    )


def find_latest_completed_run(progress: dict, completed_batch_ids: set[str]) -> dict:
    return max(
        (
            run
            for run in progress.get("runs", [])
            if run.get("status") == "submitted_result_saved" and run.get("batch_id") in completed_batch_ids
        ),
        key=lambda run: run.get("ran_at", ""),
        default={},
    )


def main() -> None:
    tii_results = load_json("data/tii-policy-results.json")
    tii_manifest = load_optional_json(tii_results.get("tii_manifest_path") or "data/tii/manifest.json")
    tii_progress = load_json("data/tii-execution-progress.json")
    batch_plan = load_json("data/batch-plan.json")
    crawl_status = load_json("data/crawl-status.json")
    policy_content = load_json("data/policy-content-extracts.json")

    batch_summaries = tii_results.get("batch_summaries", [])
    completed_batch_ids = set(tii_results.get("completed_batches") or [])
    batch_plan_by_id = {batch.get("id"): batch for batch in batch_plan.get("tii_manual_matrix_batches", [])}
    batch_order_index = {batch.get("id"): index for index, batch in enumerate(batch_plan.get("tii_manual_matrix_batches", []))}
    latest_completed_run = find_latest_completed_run(tii_progress, completed_batch_ids)
    latest_completed_id = latest_completed_run.get("batch_id") or max(
        completed_batch_ids,
        key=lambda batch_id: batch_order_index.get(batch_id, -1),
        default="",
    )
    latest_completed_summary = next(
        (batch for batch in reversed(batch_summaries) if batch.get("batch_id") == latest_completed_id),
        {},
    )
    waiting_run = latest_captcha_run(tii_progress, completed_batch_ids)
    latest_completed_plan = batch_plan_by_id.get(latest_completed_id, {})

    same_name_cards = [
        record for record in tii_results.get("records", []) if int(record.get("same_name_product_id_count") or 0) > 1
    ]
    same_name_groups = {
        (record.get("company", ""), record.get("product_name", ""))
        for record in same_name_cards
        if record.get("company") and record.get("product_name")
    }
    same_name_group_count = len(same_name_groups) or int(
        tii_results.get("same_name_version_group_count")
        or tii_manifest.get("same_name_version_group_count")
        or 0
    )
    same_name_card_count = len(same_name_cards) or int(
        tii_results.get("same_name_version_card_count")
        or tii_manifest.get("same_name_version_card_count")
        or 0
    )

    total_manual_batches = int(batch_plan.get("summary", {}).get("tii_manual_matrix_batch_count") or 0)
    progress_summary = tii_progress.get("summary", {})
    content_summary = policy_content.get("summary", {})
    crawl_summary = crawl_status.get("summary", {})

    output = {
        "generated_at": datetime.now(TAIPEI).replace(microsecond=0).isoformat(),
        "public_url": "https://taiwan-insurance-policy-navigator.vercel.app/",
        "tii": {
            "total_manual_batches": total_manual_batches,
            "attempted_batches": int(progress_summary.get("attempted_batches") or 0),
            "waiting_captcha_batches": len(active_captcha_runs(tii_progress, completed_batch_ids)),
            "indexed_batches": int(tii_results.get("indexed_batch_count") or 0),
            "completed_batches": int(tii_results.get("completed_batch_count") or 0),
            "pending_manual_batches": int(tii_results.get("pending_manual_batch_count") or 0),
            "imported_policy_records": int(tii_results.get("record_count") or 0),
            "detail_expected_count": int(tii_results.get("detail_expected_count") or 0),
            "detail_saved_count": int(tii_results.get("detail_saved_count") or 0),
            "detail_missing_count": int(tii_results.get("detail_missing_count") or 0),
            "detail_coverage_rate": float(tii_results.get("detail_coverage_rate") or 0),
            "official_result_rows": sum(int(batch.get("official_row_count") or 0) for batch in batch_summaries),
            "official_duplicate_product_rows": sum(
                int(batch.get("duplicate_product_id_count") or 0) for batch in batch_summaries
            ),
            "same_name_version_group_count": same_name_group_count,
            "same_name_version_card_count": same_name_card_count,
            "latest_completed_batch": {
                "batch_id": latest_completed_id,
                "company_label": latest_completed_run.get("company_label") or latest_completed_plan.get("company_label", ""),
                "category_label": latest_completed_run.get("category_label") or latest_completed_plan.get("category_label", ""),
                "expected_total_count": int(latest_completed_summary.get("expected_total_count") or 0),
                "official_row_count": int(latest_completed_summary.get("official_row_count") or 0),
                "imported_record_count": int(latest_completed_summary.get("imported_record_count") or 0),
                "detail_expected_count": int(latest_completed_summary.get("detail_expected_count") or 0),
                "detail_saved_count": int(latest_completed_summary.get("detail_saved_count") or 0),
                "detail_missing_count": int(latest_completed_summary.get("detail_missing_count") or 0),
                "detail_status": latest_completed_summary.get("detail_status", ""),
            },
            "current_waiting_batch": {
                "batch_id": waiting_run.get("batch_id", ""),
                "company_label": waiting_run.get("company_label", ""),
                "category_label": waiting_run.get("category_label", ""),
            },
        },
        "policy_content": {
            "reachable_policy_sources": int(content_summary.get("record_count") or 0),
            "records_with_field_hits": int(content_summary.get("records_with_field_hits") or 0),
            "pdf_records": int(content_summary.get("pdf_record_count") or 0),
            "html_records": int(content_summary.get("html_record_count") or 0),
        },
        "source_crawl": {
            "checked": int(crawl_summary.get("checked") or 0),
            "ok": int(crawl_summary.get("ok") or 0),
            "robots_blocked": int(crawl_summary.get("robots_blocked") or 0),
            "errors": int(crawl_summary.get("errors") or 0),
        },
    }
    Path("data/site-summary.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": "data/site-summary.json",
                "imported_policy_records": output["tii"]["imported_policy_records"],
                "completed_batches": output["tii"]["completed_batches"],
                "latest_completed_batch": latest_completed_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
