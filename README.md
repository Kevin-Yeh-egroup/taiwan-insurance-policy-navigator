# Taiwan Insurance Policy Navigator

Public, noindex insurance-policy navigator for Taiwan insurance source documents. The site turns insurer PDF/HTML sources into searchable source cards, crawl status, and reader-first summaries for claim/benefit terms, definitions, exclusions, renewal/premium notes, waiting periods, and underwriting limits.

## Current Status

- Local git repo initialized and connected to a public GitHub repository.
- Vercel Production is live with review-stage noindex controls.
- 17 user-provided source files were scanned locally.
- 1,670 unique URLs were extracted.
- Crawl status covers all 1,666 public crawl candidates.
- 919 checked sources are reachable, 387 are blocked by robots rules, and 360 need review.
- Segmented policy URL batches are fully executed: 17/17 automated URL batches, 1,343 policy URLs processed, 559 reachable, 532 blocked by robots rules, and 252 errors/timeouts.
- Policy content extraction is complete for all 559 reachable policy sources: 551 PDF records and 8 HTML records produced parsed text, with 555 records hitting at least one consumer-important field.
- Reader-first focus cards are generated per policy: coverage items, important definitions, special conditions, and claim application cues.
- TII captcha-protected discontinued-policy batches remain manual; this project does not bypass captcha.
- TII manual batches follow the site split: 108 property-insurance batches and 198 life/personal-insurance batches, 306 total. Current TII execution/import status is 9 attempted manual batches, 1 waiting on captcha, 8 indexed manual batches, 8 complete manual batches, 9,615 imported TII policy records, and 9,602 saved detail pages.

Production URL:

<https://taiwan-insurance-policy-navigator.vercel.app/>

User manual:

<https://taiwan-insurance-policy-navigator.vercel.app/manual.html>

## Scope

This site is an information guide. It is not insurance advice, legal advice, claim approval guidance, or a promise that a claim will be paid. Every product card links back to the original insurer or official source.

The public data intentionally stores derived evidence only: source URL, crawl status, parsed-text counts, field-hit categories, and short metadata. Full policy text is not published.

## Consumer Information Architecture

The consumer-facing structure is based on the questions ordinary readers usually ask first:

1. What claim or benefit items are mentioned?
2. How does the policy define key terms?
3. Are there waiting periods or exemption periods?
4. What exclusions or non-payment conditions appear?
5. What renewal, premium, or cancellation language appears?
6. Are there underwriting or eligibility limits?
7. Where is the official source document?

Each extracted fact should preserve `source_url`, `source_document`, `source_clause_or_page`, `scraped_at`, `verified_at`, and `confidence` when it becomes a reviewed structured field.

## Local Commands

```powershell
python scripts\extract_sources.py --input-list work\input-files.json
python scripts\prepare_public_sources.py
python scripts\crawl_batch.py --limit 60 --max-per-domain 8
python scripts\write_crawl_progress.py
python scripts\build_policy_insights.py
python scripts\extract_tii_metadata.py
python scripts\plan_segmented_batches.py --policy-batch-size 80
python scripts\run_policy_batch.py --batch-id policy-url-001
1..17 | ForEach-Object { python scripts\run_policy_batch.py --batch-id ('policy-url-{0:D3}' -f $_) }
& 'C:\Users\Kevin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts\build_policy_content_extracts.py --delay 0 --timeout 30 --max-pdf-pages 12
python scripts\validate_data.py
python -m http.server 4173
```

Then open `http://localhost:4173/`.

`work\input-files.json` is local-only and should contain:

```json
{
  "files": [
    "C:\\path\\to\\source.docx",
    "C:\\path\\to\\source.pdf"
  ]
}
```

## Publishing Gate

Kevin has approved this repo as public, Vercel as Production, and noindex as retained. Future changes still need separate approval before:

- changing repository visibility,
- removing noindex or allowing indexing,
- adding private/raw extraction files to public data,
- changing deployment protection, account settings, domains, or billing.

`noindex` is included for review-stage publishing, but it is not access control.

## TII Discontinued Policy Import

The Insurance Institute query page uses an image captcha. This project does not bypass it. Use `scripts\extract_tii_metadata.py` for public form metadata. For batch execution, run the local-only operator:

```powershell
python scripts\tii_operator_server.py
```

Open `http://127.0.0.1:8765/`, type the official captcha yourself, and the operator submits the batch, fetches all result pages, fetches available detail pages, imports the results, and prepares the next captcha. The same can be run from CLI:

```powershell
python scripts\run_tii_batch.py --batch-id tii-property-001 --captcha <human-typed-code> --fetch-all-pages --fetch-details
python scripts\import_tii_results.py --input-dir work\tii-results --output data\tii-policy-results.json
```

For a large policy universe, use segmented batches instead of one full crawl:

```powershell
python scripts\plan_segmented_batches.py --policy-batch-size 80
```

This creates `data\batch-plan.json`, including automated policy URL batches, priority TII captcha batches, and the full TII property/life manual matrix.

Execute one automated URL/content batch:

```powershell
python scripts\run_policy_batch.py --batch-id policy-url-001
```

Execution writes `data\policy-batch-results.json` and `data\batch-progress.json`.

Current execution snapshot: `policy-url-001` through `policy-url-017` are complete. These 17 are only the automated policy URL/content batches. The separate TII discontinued-policy matrix contains 306 captcha-protected manual batches.

Current content extraction snapshot: `559` reachable policy sources were parsed, including `551` PDF records and `8` HTML records. The extraction produced `6,373,892` parsed text characters and field hits for `555` records. Reader-first focus cards detected `保障項目` in `553` records, `重要定義` in `552`, `特殊項目` in `529`, and `理賠申請` in `539`. The public data stores derived counts, field hits, page hints, and source links, not full policy text.

Current TII manual matrix: `27` property insurers x `4` property categories = `108` batches; `33` life/personal insurers x `6` personal-insurance categories = `198` batches; total `306` manual batches. These batches are shown on the site as clickable property/life groups, but captcha still requires human input. Current status is `9` attempted manual batches, `1` waiting on captcha, `8 / 306` indexed manual batches, `8 / 306` complete manual batches, and `9,615` imported TII policy records. `tii-property-001` is complete with `952 / 952` records; `tii-property-002` is complete with `618 / 618` records and `617` saved detail pages; `tii-property-003` is complete with `525 / 525` records and `525` saved detail pages; `tii-property-004` is complete by official row coverage with `2,667 / 2,667` official rows, `2,091` deduplicated product cards, `576` official duplicate product-id rows, and `2,087` saved detail pages; `tii-property-005` is complete with `1,391 / 1,391` records and `1,391` saved detail pages; `tii-property-006` is complete with `1,190 / 1,190` records and `1,186` saved detail pages; `tii-property-007` is complete with `683 / 683` records and `683` saved detail pages; `tii-property-008` is complete by official row coverage with `2,525 / 2,525` official rows, `2,165` deduplicated product cards, `360` official duplicate product-id rows, and `2,161` saved detail pages. `tii-property-009` is prepared and waiting for a fresh human-entered captcha. The remaining `298` TII batches still require fresh operator captcha sessions.

TII identity rule: public cards are deduplicated only when the official result repeats the same `productId`. Do not deduplicate by policy name. The same company can reuse the same product name across different years, sale periods, or product IDs, and those records can have different terms. Imported records therefore preserve `record_identity_key`, `identity_basis`, `edition_label`, and same-name version markers so users can compare sale date, discontinued date, `productId`, and official detail pages separately.
