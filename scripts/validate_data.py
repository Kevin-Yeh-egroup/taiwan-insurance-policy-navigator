from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


def fail(message: str) -> None:
    raise SystemExit(f"VALIDATION_FAILED: {message}")


def load_json(path: str) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        fail(f"missing {path}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def main() -> None:
    source_index = load_json("data/source-index.json")
    taxonomy = load_json("data/consumer-taxonomy.json")
    crawl_status = load_json("data/crawl-status.json")
    policy_insights = load_json("data/policy-insights.json")
    tii_metadata = load_json("data/tii-query-metadata.json")
    tii_results = load_json("data/tii-policy-results.json")
    tii_execution_progress = load_json("data/tii-execution-progress.json")
    batch_plan = load_json("data/batch-plan.json")
    batch_progress = load_json("data/batch-progress.json")
    policy_batch_results = load_json("data/policy-batch-results.json")
    policy_content_extracts = load_json("data/policy-content-extracts.json")

    if not source_index.get("urls"):
        fail("source-index has no urls")
    if not taxonomy.get("sections"):
        fail("consumer taxonomy has no sections")

    ids = set()
    for item in source_index["urls"]:
        for field in ["id", "url", "domain", "company", "kind", "visibility", "should_crawl"]:
            if field not in item:
                fail(f"url record missing {field}")
        if item["id"] in ids:
            fail(f"duplicate url id {item['id']}")
        ids.add(item["id"])
        parsed = urlparse(item["url"])
        if item["should_crawl"] and parsed.scheme != "https":
            fail(f"crawl candidate is not https: {item['url']}")
        if item["should_crawl"] and item["domain"] == "docs.google.com":
            fail("private Google Docs URL marked crawlable")

    public_urls = [item for item in source_index["urls"] if item["should_crawl"]]
    if not public_urls:
        fail("no public crawl candidates")

    if not crawl_status.get("results"):
        fail("crawl-status has no results")
    if not policy_insights.get("policies"):
        fail("policy-insights has no policies")
    if not tii_metadata.get("companies"):
        fail("tii metadata has no companies")
    if tii_metadata.get("captcha_required") is not True:
        fail("tii metadata should record captcha boundary")
    if not batch_plan.get("policy_url_batches"):
        fail("batch plan has no policy URL batches")
    if not batch_plan.get("tii_priority_batches"):
        fail("batch plan has no TII priority batches")
    if not batch_plan.get("tii_company_type_groups"):
        fail("batch plan has no TII company type groups")
    if not batch_plan.get("tii_manual_matrix_batches"):
        fail("batch plan has no TII manual matrix batches")
    matrix_count = batch_plan["summary"].get("tii_manual_matrix_batch_count")
    if matrix_count != len(batch_plan["tii_manual_matrix_batches"]):
        fail("TII manual matrix batch count does not match summary")
    matrix_types = {batch.get("company_type") for batch in batch_plan["tii_manual_matrix_batches"]}
    if not {"property", "life"}.issubset(matrix_types):
        fail("TII manual matrix should include both property and life batches")
    if tii_results.get("record_count") != len(tii_results.get("records", [])):
        fail("TII result record_count does not match records length")
    tii_completed_batches = tii_results.get("completed_batch_count", len(tii_results.get("completed_batches", [])))
    if tii_completed_batches != len(tii_results.get("completed_batches", [])):
        fail("TII completed_batch_count does not match completed_batches length")
    tii_indexed_batches = tii_results.get("indexed_batch_count", len(tii_results.get("indexed_batches", [])))
    if tii_indexed_batches != len(tii_results.get("indexed_batches", [])):
        fail("TII indexed_batch_count does not match indexed_batches length")
    if tii_completed_batches > tii_indexed_batches:
        fail("TII completed batches cannot exceed indexed batches")
    if tii_completed_batches > matrix_count:
        fail("TII completed batches cannot exceed manual matrix batch count")
    for record in tii_results.get("records", []):
        for field in [
            "source_batch_id",
            "company",
            "insurance_category",
            "product_id",
            "detail_url",
            "product_name",
            "sale_status",
            "sale_date",
            "record_identity_key",
            "identity_basis",
            "edition_label",
        ]:
            if not record.get(field):
                fail(f"TII imported record missing {field}: {record.get('id')}")
        if record.get("identity_basis") == "tii_product_id" and record.get("record_identity_key") != f"tii-product-id:{record.get('product_id')}":
            fail(f"TII record identity key should preserve productId: {record.get('id')}")
        if record.get("sale_status") == "已停售" and not record.get("discontinued_date"):
            fail(f"TII discontinued record missing discontinued_date: {record.get('id')}")
        if not str(record["detail_url"]).startswith("https://insprod.tii.org.tw/DetailList.aspx?productId="):
            fail(f"TII detail_url is not an official detail URL: {record.get('id')}")
        if "raw_text" in record:
            fail(f"TII imported record should not publish raw_text: {record.get('id')}")
    same_name_groups: dict[tuple[str, str], set[str]] = {}
    for record in tii_results.get("records", []):
        same_name_groups.setdefault((record.get("company", ""), record.get("product_name", "")), set()).add(record.get("product_id", ""))
    multi_product_name_groups = {key: ids for key, ids in same_name_groups.items() if len({item for item in ids if item}) > 1}
    for record in tii_results.get("records", []):
        if (record.get("company", ""), record.get("product_name", "")) in multi_product_name_groups:
            if int(record.get("same_name_product_id_count") or 0) <= 1:
                fail(f"TII same-name different-product record missing version marker: {record.get('id')}")
    tii_batch_ids_from_records = sorted({record.get("source_batch_id") for record in tii_results.get("records", [])})
    if tii_batch_ids_from_records != sorted(tii_results.get("indexed_batches", [])):
        fail("TII indexed_batches should be unique source_batch_id values, not page filenames")
    if not isinstance(tii_results.get("batch_summaries", []), list):
        fail("TII batch_summaries should be a list")
    for summary in tii_results.get("batch_summaries", []):
        for field in [
            "batch_id",
            "status",
            "expected_total_count",
            "saved_page_count",
            "imported_record_count",
            "unique_product_id_count",
            "official_row_count",
            "duplicate_product_id_count",
        ]:
            if field not in summary:
                fail(f"TII batch summary missing {field}")
        if summary["status"] == "complete" and summary["unique_product_id_count"] != summary["expected_total_count"]:
            official_row_count = int(summary.get("official_row_count") or 0)
            duplicate_product_id_count = int(summary.get("duplicate_product_id_count") or 0)
            expected_pages = int(summary.get("expected_total_pages") or 0)
            saved_page_count = int(summary.get("saved_page_count") or 0)
            if (
                official_row_count != summary["expected_total_count"]
                or duplicate_product_id_count <= 0
                or (expected_pages and saved_page_count < expected_pages)
            ):
                fail(f"TII complete batch does not match expected count: {summary['batch_id']}")
        if summary["imported_record_count"] != summary["unique_product_id_count"]:
            fail(f"TII imported count should match unique product ids: {summary['batch_id']}")
    tii_runs = tii_execution_progress.get("runs", [])
    tii_execution_summary = tii_execution_progress.get("summary", {})
    for run in tii_runs:
        fetched_pages = run.get("fetched_pages") or {}
        for page in fetched_pages.get("saved_pages") or []:
            if not Path(page).exists():
                fail(f"TII progress references missing saved page: {page}")
    if tii_execution_summary.get("attempted_batches", len(tii_runs)) != len(tii_runs):
        fail("TII attempted batch count does not match runs length")
    if tii_execution_summary.get("completed_batches", 0) > len(tii_runs):
        fail("TII completed execution count cannot exceed attempted runs")
    if tii_execution_summary.get("attempted_batches", 0) > matrix_count:
        fail("TII attempted batches cannot exceed manual matrix batch count")
    if not batch_progress.get("batches"):
        fail("batch progress has no executed batches")
    if not policy_batch_results.get("batches"):
        fail("policy batch results has no batches")
    if not policy_content_extracts.get("records"):
        fail("policy content extracts has no records")
    content_records = policy_content_extracts["records"]
    content_summary = policy_content_extracts.get("summary", {})
    if content_summary.get("record_count") != len(content_records):
        fail("policy content record count does not match records length")
    if content_summary.get("record_count") != batch_progress["summary"]["policy_url_ok"]:
        fail("policy content extract count should match successful policy URL fetches")
    if content_summary.get("extracted_text_count") != len(content_records):
        fail("every policy content record should have parsed text")
    if content_summary.get("pdf_record_count", 0) + content_summary.get("html_record_count", 0) != len(content_records):
        fail("policy content PDF/HTML counts do not match records length")
    if content_summary.get("records_with_field_hits", 0) <= 0:
        fail("policy content extracts have no field hits")
    if content_summary.get("total_text_characters", 0) <= 0:
        fail("policy content extracts have no text characters")
    if not content_summary.get("focus_counts"):
        fail("policy content extracts have no reader focus counts")

    content_hits = 0
    focus_counts = {}
    total_text_characters = 0
    allowed_content_kinds = {"pdf", "html"}
    required_focus_keys = {"coverage", "definitions", "special", "claims"}
    forbidden_text_fields = {"text", "raw_text", "full_text", "content_text", "extracted_text"}
    for record in content_records:
        for field in ["policy_url", "final_url", "company", "product_name", "document_kind", "extraction_status"]:
            if not record.get(field):
                fail(f"policy content record missing {field}")
        if record["document_kind"] not in allowed_content_kinds:
            fail(f"unsupported policy content document kind: {record['document_kind']}")
        if record["extraction_status"] != "extracted":
            fail(f"policy content record was not extracted: {record.get('policy_id')}")
        if not isinstance(record.get("text_char_count"), int) or record["text_char_count"] <= 0:
            fail(f"policy content record has no parsed text characters: {record.get('policy_id')}")
        if record["document_kind"] == "pdf" and record.get("pages_parsed", 0) <= 0:
            fail(f"PDF policy content record has no parsed pages: {record.get('policy_id')}")
        if not isinstance(record.get("field_hits"), list):
            fail(f"policy content record field_hits must be a list: {record.get('policy_id')}")
        if forbidden_text_fields.intersection(record):
            fail(f"policy content record should not publish full text: {record.get('policy_id')}")
        reader_focus = record.get("reader_focus")
        if not isinstance(reader_focus, list) or len(reader_focus) != 4:
            fail(f"policy content record should have four reader focus cards: {record.get('policy_id')}")
        focus_keys = {card.get("key") for card in reader_focus}
        if focus_keys != required_focus_keys:
            fail(f"policy content reader focus keys are incomplete: {record.get('policy_id')}")
        detected_focus = 0
        for card in reader_focus:
            for field in ["key", "label", "reader_question", "status", "summary", "terms", "pages"]:
                if field not in card:
                    fail(f"reader focus card missing {field}: {record.get('policy_id')}")
            if card["status"] == "detected":
                detected_focus += 1
                focus_counts[card["label"]] = focus_counts.get(card["label"], 0) + 1
                if not card["terms"]:
                    fail(f"detected reader focus card has no terms: {record.get('policy_id')}")
        if record.get("focus_score") != detected_focus:
            fail(f"policy content focus score does not match detected cards: {record.get('policy_id')}")
        if record["field_hits"]:
            content_hits += 1
        total_text_characters += record["text_char_count"]
    if content_hits != content_summary.get("records_with_field_hits"):
        fail("policy content field-hit count does not match records")
    if total_text_characters != content_summary.get("total_text_characters"):
        fail("policy content text-character total does not match records")
    summary_focus_counts = {item["label"]: item["count"] for item in content_summary["focus_counts"]}
    if focus_counts != summary_focus_counts:
        fail("policy content reader focus counts do not match records")
    known_ids = {item["id"] for item in source_index["urls"]}
    for result in crawl_status["results"]:
        if result["url_id"] not in known_ids:
            fail(f"crawl result references unknown url_id {result['url_id']}")

    print(
        json.dumps(
            {
                "status": "ok",
                "source_files": source_index["source_file_count"],
                "total_urls": source_index["total_unique_url_count"],
                "public_crawl_candidates": source_index["public_crawl_candidate_count"],
                "crawl_checked": crawl_status["summary"]["checked"],
                "crawl_ok": crawl_status["summary"]["ok"],
                "policy_count": policy_insights["summary"]["policy_count"],
                "policy_discontinued": policy_insights["summary"]["discontinued_count"],
                "tii_companies": len(tii_metadata["companies"]),
                "policy_url_batches": batch_plan["summary"]["policy_url_batch_count"],
                "tii_priority_batches": batch_plan["summary"]["tii_priority_batch_count"],
                "tii_manual_matrix_batches": batch_plan["summary"]["tii_manual_matrix_batch_count"],
                "tii_attempted_manual_batches": tii_execution_summary.get("attempted_batches", 0),
                "tii_captcha_required_batches": tii_execution_summary.get("captcha_required_batches", 0),
                "tii_completed_manual_batches": tii_completed_batches,
                "tii_indexed_manual_batches": tii_indexed_batches,
                "tii_imported_records": tii_results["record_count"],
                "completed_policy_url_batches": batch_progress["summary"]["completed_policy_url_batches"],
                "policy_url_items_processed": batch_progress["summary"]["policy_url_items_processed"],
                "policy_content_extracted": content_summary["extracted_text_count"],
                "policy_content_field_hits": content_summary["records_with_field_hits"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
