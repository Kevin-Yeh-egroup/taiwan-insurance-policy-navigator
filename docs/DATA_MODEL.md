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

`data/tii-policy-results.json` is the execution/import status for captcha-protected TII batches. A planned batch is not counted as complete until a human finishes the captcha query and the runner imports complete official result-page coverage. Public cards are deduplicated only by TII `productId`, because the official result rows can repeat the same product ID across pages. They are not deduplicated by product name: the same company can reuse a name across different years, sale periods, or product IDs, and those records may have different terms.

```json
{
  "record_count": 43008,
  "detail_expected_count": 43008,
  "detail_saved_count": 42874,
  "detail_missing_count": 134,
  "detail_coverage_rate": 0.9969,
  "indexed_batch_count": 29,
  "indexed_batches": ["tii-property-001", "tii-property-002", "...", "tii-property-029"],
  "completed_batch_count": 29,
  "completed_batches": ["tii-property-001", "tii-property-002", "...", "tii-property-029"],
  "partial_batch_count": 0,
  "pending_manual_batch_count": 277,
  "batch_summaries": [
    {
      "batch_id": "tii-property-001",
      "status": "complete",
      "expected_total_count": 952,
      "expected_total_pages": 96,
      "official_row_count": 952,
      "saved_page_count": 96,
      "imported_record_count": 952,
      "unique_product_id_count": 952,
      "expected_unique_product_id_count": 952,
      "duplicate_product_id_count": 0,
      "detail_expected_count": 952,
      "detail_saved_count": 952,
      "detail_missing_count": 0,
      "detail_coverage_rate": 1.0,
      "detail_status": "complete",
      "requires_fresh_captcha_session": false,
      "requires_detail_backfill_session": false
    },
    {
      "batch_id": "tii-property-002",
      "status": "complete",
      "expected_total_count": 618,
      "expected_total_pages": 62,
      "official_row_count": 618,
      "saved_page_count": 62,
      "imported_record_count": 618,
      "unique_product_id_count": 618,
      "expected_unique_product_id_count": 618,
      "duplicate_product_id_count": 0,
      "detail_expected_count": 618,
      "detail_saved_count": 617,
      "detail_missing_count": 1,
      "detail_coverage_rate": 0.9984,
      "detail_status": "partial_detail",
      "requires_fresh_captcha_session": false,
      "requires_detail_backfill_session": true
    },
    {
      "batch_id": "tii-property-003",
      "status": "complete",
      "expected_total_count": 525,
      "expected_total_pages": 53,
      "official_row_count": 525,
      "saved_page_count": 53,
      "imported_record_count": 525,
      "unique_product_id_count": 525,
      "expected_unique_product_id_count": 525,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 525,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-004",
      "status": "complete",
      "expected_total_count": 2667,
      "expected_total_pages": 267,
      "official_row_count": 2667,
      "saved_page_count": 267,
      "imported_record_count": 2091,
      "unique_product_id_count": 2091,
      "expected_unique_product_id_count": 2091,
      "duplicate_product_id_count": 576,
      "detail_saved_count": 2087,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-005",
      "status": "complete",
      "expected_total_count": 1391,
      "expected_total_pages": 140,
      "official_row_count": 1391,
      "saved_page_count": 140,
      "imported_record_count": 1391,
      "unique_product_id_count": 1391,
      "expected_unique_product_id_count": 1391,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1391,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-006",
      "status": "complete",
      "expected_total_count": 1190,
      "expected_total_pages": 119,
      "official_row_count": 1190,
      "saved_page_count": 119,
      "imported_record_count": 1190,
      "unique_product_id_count": 1190,
      "expected_unique_product_id_count": 1190,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1186,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-007",
      "status": "complete",
      "expected_total_count": 683,
      "expected_total_pages": 69,
      "official_row_count": 683,
      "saved_page_count": 69,
      "imported_record_count": 683,
      "unique_product_id_count": 683,
      "expected_unique_product_id_count": 683,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 683,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-008",
      "status": "complete",
      "expected_total_count": 2525,
      "expected_total_pages": 253,
      "official_row_count": 2525,
      "saved_page_count": 253,
      "imported_record_count": 2165,
      "unique_product_id_count": 2165,
      "expected_unique_product_id_count": 2165,
      "duplicate_product_id_count": 360,
      "detail_saved_count": 2161,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-009",
      "status": "complete",
      "expected_total_count": 73,
      "expected_total_pages": 8,
      "official_row_count": 73,
      "saved_page_count": 8,
      "imported_record_count": 73,
      "unique_product_id_count": 73,
      "expected_unique_product_id_count": 73,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 73,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-010",
      "status": "complete",
      "expected_total_count": 30,
      "expected_total_pages": 3,
      "official_row_count": 30,
      "saved_page_count": 3,
      "imported_record_count": 30,
      "unique_product_id_count": 30,
      "expected_unique_product_id_count": 30,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 30,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-011",
      "status": "complete",
      "expected_total_count": 7,
      "expected_total_pages": 1,
      "official_row_count": 7,
      "saved_page_count": 1,
      "imported_record_count": 7,
      "unique_product_id_count": 7,
      "expected_unique_product_id_count": 7,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 7,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-012",
      "status": "complete",
      "expected_total_count": 106,
      "expected_total_pages": 11,
      "official_row_count": 106,
      "saved_page_count": 11,
      "imported_record_count": 106,
      "unique_product_id_count": 106,
      "expected_unique_product_id_count": 106,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 106,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-013",
      "status": "complete",
      "expected_total_count": 1599,
      "expected_total_pages": 160,
      "official_row_count": 1599,
      "saved_page_count": 160,
      "imported_record_count": 1599,
      "unique_product_id_count": 1599,
      "expected_unique_product_id_count": 1599,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1599,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-014",
      "status": "complete",
      "expected_total_count": 943,
      "expected_total_pages": 95,
      "official_row_count": 943,
      "saved_page_count": 95,
      "imported_record_count": 943,
      "unique_product_id_count": 943,
      "expected_unique_product_id_count": 943,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 940,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-015",
      "status": "complete",
      "expected_total_count": 3112,
      "expected_total_pages": 312,
      "official_row_count": 3112,
      "saved_page_count": 312,
      "imported_record_count": 3112,
      "unique_product_id_count": 3112,
      "expected_unique_product_id_count": 3112,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 3103,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-016",
      "status": "complete",
      "expected_total_count": 10537,
      "expected_total_pages": 1054,
      "official_row_count": 10537,
      "saved_page_count": 1054,
      "imported_record_count": 8056,
      "unique_product_id_count": 8056,
      "expected_unique_product_id_count": 8056,
      "duplicate_product_id_count": 2481,
      "detail_saved_count": 8011,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-017",
      "status": "complete",
      "expected_total_count": 1233,
      "expected_total_pages": 124,
      "official_row_count": 1233,
      "saved_page_count": 124,
      "imported_record_count": 1233,
      "unique_product_id_count": 1233,
      "expected_unique_product_id_count": 1233,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1233,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-018",
      "status": "complete",
      "expected_total_count": 940,
      "expected_total_pages": 94,
      "official_row_count": 940,
      "saved_page_count": 94,
      "imported_record_count": 940,
      "unique_product_id_count": 940,
      "expected_unique_product_id_count": 940,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 938,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-019",
      "status": "complete",
      "expected_total_count": 1576,
      "expected_total_pages": 158,
      "official_row_count": 1576,
      "saved_page_count": 158,
      "imported_record_count": 1576,
      "unique_product_id_count": 1576,
      "expected_unique_product_id_count": 1576,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1569,
      "requires_fresh_captcha_session": false
    }
  ],
  "records": [
    {
      "source_batch_id": "tii-property-001",
      "company": "臺灣產物保險股份有限公司",
      "insurance_category": "汽車保險",
      "product_id": "101111114057010000",
      "record_identity_key": "tii-product-id:101111114057010000",
      "identity_basis": "tii_product_id",
      "detail_url": "https://insprod.tii.org.tw/DetailList.aspx?productId=101111114057010000",
      "detail_saved": true,
      "detail_source_file": "work\\tii-details\\tii-property-001\\101111114057010000.html",
      "product_name": "臺灣產物強制汽車責任保險",
      "sale_status": "已停售",
      "sale_date": "086/12/05",
      "discontinued_date": "094/11/06",
      "edition_label": "銷售日 086/12/05｜停售日 094/11/06｜productId 101111114057010000",
      "same_name_product_id_count": 1,
      "same_name_version_note": ""
    }
  ],
  "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha."
}
```

Completion rule:

- `indexed_batch_count`: at least one valid product row was imported for that batch.
- `completed_batch_count`: either `unique_product_id_count == expected_total_count == imported_record_count`, or `official_row_count == expected_total_count` with full saved-page coverage and a positive `duplicate_product_id_count`.
- `partial_index`: the batch has usable rows, but the saved pages do not yet match the official total count.
- `record_count`: public product cards after deduplicating repeated official `productId` rows.
- `official_row_count`: row coverage reported by saved TII result pages before deduplication.
- `detail_expected_count`: expected detail-page count after productId deduplication.
- `detail_saved_count`: official detail pages saved locally during human-captcha sessions.
- `detail_missing_count`: detail pages that still need a later backfill session. A batch can have complete official result-page coverage while `detail_status` is `partial_detail`.
- `requires_detail_backfill_session`: true when the batch has preserved result rows but some official detail pages were unavailable or session-invalid during the run.
- `record_identity_key`: stable public identity. Prefer `tii-product-id:<productId>`; use the company/category/name/date fallback only when an official product ID is absent.
- `edition_label`: user-facing version cue combining sale date, discontinued date, and `productId`.
- `same_name_product_id_count` / `same_name_version_note`: marker for same-company same-name records that represent different product IDs. These records must remain separate cards.
