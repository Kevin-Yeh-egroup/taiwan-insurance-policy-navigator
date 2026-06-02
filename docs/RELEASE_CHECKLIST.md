# Release Checklist

## Public Readiness

- [ ] Site wording says this is an information guide, not insurance advice or claim approval guidance.
- [ ] Every policy detail has source URL, source document, scraped date, and verification status.
- [ ] No claim language says `一定理賠`, `保證給付`, or `符合即可領`.
- [ ] Stale or unverified data is visibly marked.
- [ ] Private/local URLs are excluded from public pages.
- [ ] Raw extraction files with full user-provided text are not committed to public repo.

## Crawler Safety

- [ ] Each domain's `robots.txt` is checked before crawling.
- [ ] The crawler has a clear user agent.
- [ ] Batch limits, per-domain limits, timeouts, and retry ceilings are configured.
- [ ] No login, CAPTCHA, paid, private, or session-bound pages are crawled.
- [ ] Crawl logs do not expose cookies, auth headers, or private file paths.

## Engineering

- [ ] `python scripts/prepare_public_sources.py` passes.
- [ ] `python scripts/crawl_batch.py --limit 60 --max-per-domain 4` completes.
- [ ] `python scripts/validate_data.py` passes.
- [ ] Static app loads on desktop and mobile.
- [ ] Search, filters, source list, and taxonomy sections render correctly.

## GitHub And Vercel

- [ ] Kevin approves public/private repo visibility.
- [ ] Kevin approves Vercel Preview or Production.
- [ ] `.env`, `.vercel`, `work/source-extraction/source-manifest.json`, crawl cache, and raw logs are excluded.
- [ ] Production uses a dedicated project/alias.
- [ ] `robots.txt` returns `Disallow: /` during review.
- [ ] HTML meta robots and `X-Robots-Tag` are present.
- [ ] Final URL returns `200 OK`.
