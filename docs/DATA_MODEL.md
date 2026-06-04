# Data Model

The public site separates source discovery, crawl status, content extraction proof, and future reviewed policy facts. This keeps the current public release useful without publishing full policy text.

## SourceUrl

```json
{
  "id": "url_000001",
  "url": "https://example.com/policy.pdf",
  "domain": "example.com",
  "company": "Example Life",
  "source_file_title": "Example Life",
  "source_document_id": "doc_001",
  "kind": "pdf_terms",
  "visibility": "public_web",
  "should_crawl": true,
  "risk_flags": [],
  "first_seen_at": "2026-06-02T00:00:00+08:00"
}
```

## CrawlStatus

```json
{
  "id": "url_000001",
  "url": "https://example.com/policy.pdf",
  "domain": "example.com",
  "status": "ok",
  "robots_allowed": true,
  "http_status": 200,
  "content_type": "application/pdf",
  "checked_at": "2026-06-04T09:07:54+08:00",
  "error": null
}
```

Status meanings:

- `ok`: the source was reachable and may be used for extraction.
- `robots_blocked`: `robots.txt` did not allow crawling; the URL stays visible as source evidence but is not fetched further.
- `error`: the source timed out, returned an error, or needs manual review.

## PolicyContentExtract

`data/policy-content-extracts.json` stores proof that insurance content was actually parsed from reachable policy sources.

```json
{
  "id": "policy-content-000001",
  "company": "Example Life",
  "product_name": "Example Whole Life Insurance",
  "document_kind": "pdf",
  "policy_url": "https://example.com/policy.pdf",
  "content_type": "application/pdf",
  "status": "extracted",
  "page_count": 24,
  "pages_parsed": 12,
  "text_char_count": 18234,
  "field_hits": [
    {
      "key": "claims",
      "label": "理賠/給付",
      "matched_terms": ["給付", "保險金"]
    }
  ],
  "reader_focus": [
    {
      "key": "coverage",
      "label": "保障項目",
      "reader_question": "這張保單主要賠什麼、保障哪些事故或狀態？",
      "status": "detected",
      "summary": "已命中 5 個重點詞：給付、保險金、住院。",
      "terms": ["給付", "保險金", "住院"],
      "pages": [2, 3]
    }
  ],
  "focus_score": 4,
  "extracted_at": "2026-06-04T09:07:54+08:00"
}
```

The public extract does not include full PDF text. It includes enough derived evidence to confirm that the crawler parsed policy content and found reader-important categories. `reader_focus` powers the public quick-read cards for `保障項目`, `重要定義`, `特殊項目`, and `理賠申請`.

## ConsumerField

Future reviewed facts should follow this shape:

```json
{
  "label": "等待期",
  "value": "30 日",
  "summary": "疾病醫療給付需留意等待期。",
  "source_url": "https://example.com/policy.pdf",
  "source_document": "Official policy PDF",
  "source_clause_or_page": "p. 3",
  "extraction_method": "rule | model | manual",
  "confidence": "low | medium | high",
  "last_checked_at": "2026-06-04T09:07:54+08:00"
}
```

## TIIManualMatrixBatch

The Insurance Institute discontinued-policy query page requires captcha completion. The public site therefore stores manual click-through batches instead of bypassing the captcha.

```json
{
  "id": "tii-life-001",
  "group": "life_personal",
  "company": "Example Life",
  "insurance_category": "健康險",
  "source_url": "https://insprod.tii.org.tw/Query.aspx",
  "status": "manual_captcha_required"
}
```

## TIIImportedResults

`data/tii-policy-results.json` is the execution/import status for captcha-protected TII batches. A planned batch is not counted as complete until a human finishes the captcha query and the runner imports all expected product IDs.

```json
{
  "record_count": 1570,
  "detail_saved_count": 1569,
  "indexed_batch_count": 2,
  "indexed_batches": ["tii-property-001", "tii-property-002"],
  "completed_batch_count": 2,
  "completed_batches": ["tii-property-001", "tii-property-002"],
  "partial_batch_count": 0,
  "pending_manual_batch_count": 304,
  "batch_summaries": [
    {
      "batch_id": "tii-property-001",
      "status": "complete",
      "expected_total_count": 952,
      "expected_total_pages": 96,
      "saved_page_count": 96,
      "imported_record_count": 952,
      "unique_product_id_count": 952,
      "detail_saved_count": 952,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-002",
      "status": "complete",
      "expected_total_count": 618,
      "expected_total_pages": 62,
      "saved_page_count": 62,
      "imported_record_count": 618,
      "unique_product_id_count": 618,
      "detail_saved_count": 617,
      "requires_fresh_captcha_session": false
    }
  ],
  "records": [
    {
      "source_batch_id": "tii-property-001",
      "company": "臺灣產物保險股份有限公司",
      "insurance_category": "汽車保險",
      "product_id": "101111114057010000",
      "detail_url": "https://insprod.tii.org.tw/DetailList.aspx?productId=101111114057010000",
      "detail_saved": true,
      "detail_source_file": "work\\tii-details\\tii-property-001\\101111114057010000.html",
      "product_name": "臺灣產物強制汽車責任保險",
      "sale_status": "已停售",
      "sale_date": "086/12/05",
      "discontinued_date": "094/11/06"
    }
  ],
  "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha."
}
```

Completion rule:

- `indexed_batch_count`: at least one valid product row was imported for that batch.
- `completed_batch_count`: `unique_product_id_count == expected_total_count == imported_record_count`.
- `partial_index`: the batch has usable rows, but the saved pages do not yet match the official total count.
