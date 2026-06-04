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
  "extracted_at": "2026-06-04T09:07:54+08:00"
}
```

The public extract does not include full PDF text. It includes enough derived evidence to confirm that the crawler parsed policy content and found reader-important categories.

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
