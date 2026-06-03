# Taiwan Policy Navigator

公開保單資訊整理與爬蟲專案草案。目標不是把條款 PDF 全部堆在一起，而是把民眾查保單時最常需要確認的資訊整理成可搜尋、可比較、可回溯來源的欄位。

## Current Status

- Local git repo initialized.
- 17 user-provided source files were scanned locally.
- 1,670 unique URLs were extracted.
- Public-safe source index and crawler status are generated with scripts.
- Crawl status now covers all 1,666 public crawl candidates (100.0% checked).
- 919 checked sources are currently reachable, 387 are blocked by robots rules, and 360 need review.
- Segmented policy URL batches are fully executed: 17/17 batches, 1,343 policy URLs processed, 559 pages reachable, 532 blocked by robots rules, and 252 errors or timeouts.
- TII captcha-protected batches remain manual; this project does not bypass captcha.
- Public GitHub repository is live.
- Vercel Production is live with review-stage noindex controls.

Production URL:

<https://taiwan-insurance-policy-navigator.vercel.app/>

操作手冊:

<https://taiwan-insurance-policy-navigator.vercel.app/manual.html>

## Scope

This site is an information guide. It is not insurance advice, legal advice, claim approval guidance, or a promise that a claim will be paid. Every product page must link back to the original insurer or official source.

## Consumer Information Architecture

The first public version uses these sections:

1. 理賠內容
2. 名詞定義
3. 等待期/免責期
4. 除外責任
5. 保費與續保
6. 投保限制
7. 官方文件

Each field should carry `source_url`, `source_document`, `source_clause_or_page`, `scraped_at`, `verified_at`, and `confidence`.

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

Do not push to GitHub or deploy to Vercel until Kevin approves:

- repository visibility,
- public/production target,
- noindex status,
- whether the data is ready for public readers,
- whether any raw extraction files should remain local only.

`noindex` is included for review-stage publishing, but it is not access control.

## TII Discontinued Policy Import

The Insurance Institute query page uses an image captcha. This project does not bypass it. Use `scripts\extract_tii_metadata.py` for public form metadata, then manually save query result HTML/CSV after completing captcha and import it with:

```powershell
python scripts\import_tii_results.py --input-dir work\tii-results --output data\tii-policy-results.json
```

For a large policy universe, use segmented batches instead of one full crawl:

```powershell
python scripts\plan_segmented_batches.py --policy-batch-size 80
```

This creates `data\batch-plan.json`, including automated policy URL batches and manual TII captcha batches.

Execute one automated URL/content batch:

```powershell
python scripts\run_policy_batch.py --batch-id policy-url-001
```

Execution writes `data\policy-batch-results.json` and `data\batch-progress.json`.

Current execution snapshot: `policy-url-001` through `policy-url-017` are complete. The site reports the distinction between executed batches, pages that were actually reachable, robots-blocked URLs, and errors/timeouts.
