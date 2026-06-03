# Taiwan Policy Navigator

公開保單資訊整理與爬蟲專案草案。目標不是把條款 PDF 全部堆在一起，而是把民眾查保單時最常需要確認的資訊整理成可搜尋、可比較、可回溯來源的欄位。

## Current Status

- Local git repo initialized.
- 17 user-provided source files were scanned locally.
- 1,670 unique URLs were extracted.
- Public-safe source index and crawler status can be generated with scripts.
- Public GitHub repository is live.
- Vercel Production is live with review-stage noindex controls.

Production URL:

<https://taiwan-insurance-policy-navigator.vercel.app/>

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
python scripts\crawl_batch.py --limit 60 --max-per-domain 4
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
