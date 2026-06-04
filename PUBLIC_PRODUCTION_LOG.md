# Public Production Log

## 2026-06-04 Second TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `01256e9`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed second TII batch data: `dpl_DEH2WbbpsKMUQA5u1JbcxLBeGwq9`
- Deployment URL: <https://taiwan-insurance-policy-navigator-7cikrvmzu.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=1570`, `indexed_batch_count=2`, `completed_batch_count=2`, `partial_batch_count=0`, and pending manual batches `304`.
- `tii-property-001` is `952 / 952` with `96` saved result pages and `952` saved detail pages.
- `tii-property-002` is `618 / 618` with `62` saved result pages and `617` saved detail pages; `1` official detail page returned an invalid detail session.
- Production UI renders query controls, `1,570` imported TII policies, `1,569` saved detail pages, and the second batch data.

## 2026-06-04 First TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `a469c85`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed first TII batch data: `dpl_FJrqGbDfFA4g7xjAz28DZV2SkaTE`
- Deployment URL: <https://taiwan-insurance-policy-navigator-coql40ibe.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=952`, `indexed_batch_count=1`, `completed_batch_count=1`, `partial_batch_count=0`, and first batch `tii-property-001` as `952 / 952` with `96` saved result pages and `952` saved detail pages.
- Production UI renders query controls, `productId 101111114057010000`, `明細已保存`, `已索引批次`, and `完整批次`.

## 2026-06-04

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Release commit: `b6d06f3`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for the TII operator/data update: `dpl_AVhWCuoR7Tcmz5XyXt9DP7uL3aci`
- Deployment URL: <https://taiwan-insurance-policy-navigator-byo3bnmd0.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=10`, `indexed_batch_count=1`, `completed_batch_count=0`, `partial_batch_count=1`, and first batch `tii-property-001` as `10 / 952`.
- Production UI renders query controls, `productId 101111114057010000`, `明細待抓取`, `已索引批次`, and `完整批次`.

## 2026-06-03

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Latest release commit at deployment time: `0b544ce`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Active production deployment: `dpl_8psg5wkZR9F3srmAzgokcejzWzgg`
- Deployment URL: <https://taiwan-insurance-policy-navigator-3mxwbz8e5.vercel.app>
- Target: production
- Status: READY

Review-stage noindex controls:

- HTML meta robots: `noindex,nofollow,noarchive`
- `robots.txt`: `Disallow: /`
- Vercel header: `X-Robots-Tag: noindex, nofollow, noarchive`

Safety remediation:

- First deployment `dpl_CTEEDgjd7hKrmhN14JqUVBmNHzL4` accidentally included local ignored directories because Vercel did not rely on `.gitignore` alone.
- Added `.vercelignore` to exclude `.git/`, `.env*`, `.vercel/`, `work/`, `outputs/`, `tmp/`, and cache directories.
- Redeployed production safely.
- Removed the first deployment.
- Verified old deployment root and raw manifest paths return `404`.
- Verified active production root returns `200` and raw local paths return `404`.
