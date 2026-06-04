# Crawl Progress

Updated at: `2026-06-04T09:07:54+08:00`

## Overall

- Total public candidates: `1666`
- Checked: `1666`
- Unchecked: `0`
- Completion rate: `100.0%`
- OK: `919`
- Robots blocked: `387`
- Errors / needs review: `360`

## Policy URL Content Batches

- Completed URL batches: `17 / 17`
- Policy URLs processed: `1343`
- Reachable page reads: `559`
- Robots blocked: `532`
- Errors / timeouts: `252`
- Note: completed batch means the URL was checked. Reachable records then move into policy content extraction.

## Policy Content Extraction

- Reachable policy sources parsed: `559`
- PDF records parsed: `551`
- HTML records parsed: `8`
- Records with parsed text: `559`
- Records with consumer-important field hits: `555`
- Parsed text characters: `6,373,892`
- Field-hit categories:
  - `理賠/給付`: `554`
  - `名詞定義`: `552`
  - `保費/續保`: `482`
  - `除外責任`: `457`
  - `投保限制`: `358`
  - `等待期/免責期`: `104`
- Reader-first focus cards:
  - `保障項目`: `553`
  - `重要定義`: `552`
  - `理賠申請`: `539`
  - `特殊項目`: `529`
- Public output: `data/policy-content-extracts.json`
- Public output policy: derived evidence only; full policy text is not published.

## TII Manual Matrix

- Property-insurance manual batches: `108`
- Life / personal-insurance manual batches: `198`
- Total TII manual matrix batches: `306`
- Captcha boundary: TII result pages require human captcha completion; this project prepares click-through batches and imports saved results, but does not bypass captcha.

## Top Checked Domains

| Domain | Checked | OK | Robots blocked | Errors |
| --- | ---: | ---: | ---: | ---: |
| `www.taiwanlife.com` | 294 | 1 | 293 | 0 |
| `www.nanshanlife.com.tw` | 291 | 284 | 0 | 7 |
| `www.cki.com.tw` | 269 | 269 | 0 | 0 |
| `www.skl.com.tw` | 235 | 1 | 0 | 234 |
| `www.kgilife.com.tw` | 128 | 128 | 0 | 0 |
| `www.hontai.com.tw` | 84 | 0 | 84 | 0 |
| `www.pcalife.com.tw` | 83 | 5 | 0 | 78 |
| `www.twfhclife.com.tw` | 66 | 65 | 0 | 1 |
| `www.fubon.com` | 41 | 40 | 0 | 1 |
| `www.cathaylife.com.tw` | 40 | 40 | 0 | 0 |
| `www.nanshangeneral.com.tw` | 28 | 0 | 0 | 28 |
| `www.bli.gov.tw` | 25 | 25 | 0 | 0 |
| `vulweb.mli.com.tw` | 24 | 18 | 0 | 6 |
| `www.post.gov.tw` | 21 | 19 | 0 | 2 |
| `www.cathay-ins.com.tw` | 9 | 8 | 0 | 1 |
| `law.moj.gov.tw` | 7 | 0 | 7 | 0 |
| `www.ecover.com.tw` | 7 | 7 | 0 | 0 |
| `www.sk858.com.tw` | 4 | 4 | 0 | 0 |
| `www.msig-mingtai.com.tw` | 3 | 1 | 0 | 2 |
| `www.nhi.gov.tw` | 3 | 0 | 3 | 0 |

## Notes

- The crawler is resumable. It skips URL IDs already present in `data/crawl-status.json`.
- `robots.txt` blocked sources are treated as completed checks, not crawl failures.
- HTTP 404, connection refused, timeout, and encoding/network errors are marked as review items.
- Deeper reviewed policy-field extraction should only use sources with stable source URLs and source evidence.
