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

    content_hits = 0
    total_text_characters = 0
    allowed_content_kinds = {"pdf", "html"}
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
        if record["field_hits"]:
            content_hits += 1
        total_text_characters += record["text_char_count"]
    if content_hits != content_summary.get("records_with_field_hits"):
        fail("policy content field-hit count does not match records")
    if total_text_characters != content_summary.get("total_text_characters"):
        fail("policy content text-character total does not match records")
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
