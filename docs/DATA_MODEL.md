# Data Model

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

## PolicyRecord

Future structured extraction should produce:

```json
{
  "id": "policy_000001",
  "company": "保險公司",
  "product_name": "商品名稱",
  "status": "現售 | 停售 | 未知",
  "insurance_type": "醫療 | 意外 | 壽險 | 年金 | 產險 | 社會保險 | 其他",
  "coverage_summary": [],
  "claim_items": [],
  "definitions": [],
  "waiting_periods": [],
  "exclusions": [],
  "premium_and_renewal": [],
  "underwriting_limits": [],
  "official_documents": [],
  "source_updated_at": null,
  "scraped_at": null,
  "verified_at": null,
  "stale_after": null,
  "confidence": "unreviewed | parsed | sampled | expert_reviewed"
}
```

## ExtractedField

Every consumer-facing extracted fact should preserve evidence:

```json
{
  "label": "等待期",
  "value": "30 日",
  "summary": "疾病住院醫療可能有等待期限制。",
  "source_url": "https://example.com/policy.pdf",
  "source_document": "條款 PDF",
  "source_clause_or_page": "第 2 條或 p. 3",
  "extraction_method": "rule | model | manual",
  "confidence": "low | medium | high",
  "last_checked_at": "2026-06-02T00:00:00+08:00"
}
```
