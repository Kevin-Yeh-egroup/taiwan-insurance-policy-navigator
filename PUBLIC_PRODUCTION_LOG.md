# Public Production Log

## 2026-06-05 Sixteenth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `da1d521`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed sixteenth TII batch data: `dpl_4PMTsyqW9ZRwenSCCzrxZUW9aDd4`
- Deployment URL: <https://taiwan-insurance-policy-navigator-h1v7ss7tq.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=23541`, `detail_saved_count=23471`, `indexed_batch_count=16`, `completed_batch_count=16`, `partial_batch_count=0`, and pending manual batches `290`.
- TII execution progress shows `attempted_batches=17`, `completed_batches=16`, `captcha_required_batches=1`; `tii-property-017` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-016` is complete by official row coverage: `10537 / 10537` official result rows, `8056` imported product cards, `2481` official duplicate product-id rows, `1054` saved result pages, and `8011` saved detail pages; `45` official detail pages returned invalid detail sessions.
- The local operator now detects completed saved result pages and uses the next captcha only to fetch missing detail pages, which avoids refetching very large batches.
- Production data preserves `987` same-company same-name multi-product groups as `2438` separate cards.
- Production UI/data renders `23,541` imported TII policies, `23,471` saved detail pages, `26,958` official result rows, and `3,417` official duplicate rows.

## 2026-06-05 Fifteenth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `cc3e63c`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed fifteenth TII batch data: `dpl_E5SDgQFqsu996RGaoYB4QFxJuRAf`
- Deployment URL: <https://taiwan-insurance-policy-navigator-pj5qywm1i.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=15485`, `detail_saved_count=15460`, `indexed_batch_count=15`, `completed_batch_count=15`, `partial_batch_count=0`, and pending manual batches `291`.
- TII execution progress shows `attempted_batches=16`, `completed_batches=15`, `captcha_required_batches=1`; `tii-property-016` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-015` is complete by official row coverage: `3112 / 3112` official result rows, `3112` imported product cards, `0` official duplicate product-id rows, `312` saved result pages, and `3103` saved detail pages; `9` official detail pages returned invalid detail sessions.
- The local operator now skips already saved detail pages on rerun and reports timeout as a failed job instead of leaving the UI in a running state.
- Production data preserves `479` same-company same-name multi-product groups as `1085` separate cards.
- Production UI/data renders `15,485` imported TII policies, `15,460` saved detail pages, `16,421` official result rows, and `936` official duplicate rows.

## 2026-06-05 Fourteenth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `ecbc767`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed fourteenth TII batch data: `dpl_8HFwiBuUsWwe9z32vGYn4mo9jsVL`
- Deployment URL: <https://taiwan-insurance-policy-navigator-1bfzledea.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=12373`, `detail_saved_count=12357`, `indexed_batch_count=14`, `completed_batch_count=14`, `partial_batch_count=0`, and pending manual batches `292`.
- TII execution progress shows `attempted_batches=15`, `completed_batches=14`, `captcha_required_batches=1`; `tii-property-015` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-013` is complete by official row coverage: `1599 / 1599` official result rows, `1599` imported product cards, `0` official duplicate product-id rows, `160` saved result pages, and `1599` saved detail pages.
- `tii-property-014` is complete by official row coverage: `943 / 943` official result rows, `943` imported product cards, `0` official duplicate product-id rows, `95` saved result pages, and `940` saved detail pages; `3` official detail pages returned invalid detail sessions.
- Production data preserves `265` same-company same-name multi-product groups as `562` separate cards.
- Production UI/data renders `12,373` imported TII policies, `12,357` saved detail pages, `13,309` official result rows, and `936` official duplicate rows.

## 2026-06-05 Twelfth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `5f7e245`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twelfth TII batch data: `dpl_EfcuuDvK8Ei2q6UMvnM2BpSn3aPg`
- Deployment URL: <https://taiwan-insurance-policy-navigator-pk8blsdlm.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=9831`, `detail_saved_count=9818`, `indexed_batch_count=12`, `completed_batch_count=12`, `partial_batch_count=0`, and pending manual batches `294`.
- TII execution progress shows `attempted_batches=13`, `completed_batches=12`, `captcha_required_batches=1`; `tii-property-013` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-009` is complete by official row coverage: `73 / 73` official result rows, `73` imported product cards, `0` official duplicate product-id rows, `8` saved result pages, and `73` saved detail pages.
- `tii-property-010` is complete by official row coverage: `30 / 30` official result rows, `30` imported product cards, `0` official duplicate product-id rows, `3` saved result pages, and `30` saved detail pages.
- `tii-property-011` is complete by official row coverage: `7 / 7` official result rows, `7` imported product cards, `0` official duplicate product-id rows, `1` saved result page, and `7` saved detail pages.
- `tii-property-012` is complete by official row coverage: `106 / 106` official result rows, `106` imported product cards, `0` official duplicate product-id rows, `11` saved result pages, and `106` saved detail pages.
- Production data preserves `194` same-company same-name multi-product groups as `420` separate cards.
- Production UI/data renders `9,831` imported TII policies, `9,818` saved detail pages, `10,767` official result rows, and `936` official duplicate rows.

## 2026-06-05 Eighth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `0e211d3`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed eighth TII batch data: `dpl_A7Yib7dwWWtpsuhnKGFUy9Nre87G`
- Deployment URL: <https://taiwan-insurance-policy-navigator-9d1mwv1p6.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=9615`, `detail_saved_count=9602`, `indexed_batch_count=8`, `completed_batch_count=8`, `partial_batch_count=0`, and pending manual batches `298`.
- TII execution progress shows `attempted_batches=9`, `completed_batches=8`, `captcha_required_batches=1`; `tii-property-009` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-007` is complete by official row coverage: `683 / 683` official result rows, `683` imported product cards, `0` official duplicate product-id rows, `69` saved result pages, and `683` saved detail pages.
- `tii-property-008` is complete by official row coverage: `2525 / 2525` official result rows, `2165` imported product cards, `360` official duplicate product-id rows, `253` saved result pages, and `2161` saved detail pages; `4` official detail pages returned invalid detail sessions.
- Production data preserves `146` same-company same-name multi-product groups as `321` separate cards.
- Production UI/data renders `9,615` imported TII policies, `9,602` saved detail pages, `10,551` official result rows, and `936` official duplicate rows.

## 2026-06-05 Sixth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `075a32d`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed sixth TII batch data: `dpl_C9PEWgvoze9nQiHaixzZjaDsorgi`
- Deployment URL: <https://taiwan-insurance-policy-navigator-1fnigllvp.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=6767`, `detail_saved_count=6758`, `indexed_batch_count=6`, `completed_batch_count=6`, `partial_batch_count=0`, and pending manual batches `300`.
- TII execution progress shows `attempted_batches=7`, `completed_batches=6`, `captcha_required_batches=1`; `tii-property-007` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-006` is complete by official row coverage: `1190 / 1190` official result rows, `1190` imported product cards, `0` official duplicate product-id rows, `119` saved result pages, and `1186` saved detail pages; `4` official detail pages returned invalid detail sessions.
- Production data preserves `79` same-company same-name multi-product groups as `168` separate cards.
- Production UI/data renders `6,767` imported TII policies, `6,758` saved detail pages, `7,343` official result rows, and `576` official duplicate rows.

## 2026-06-04 Fifth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `94a2ec1`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed fifth TII batch data: `dpl_69rgymrp4VD2iCaXd71BhXbHfSkM`
- Deployment URL: <https://taiwan-insurance-policy-navigator-f1b5p2zge.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=5577`, `detail_saved_count=5572`, `indexed_batch_count=5`, `completed_batch_count=5`, `partial_batch_count=0`, and pending manual batches `301`.
- TII execution progress shows `attempted_batches=6`, `completed_batches=5`, `captcha_required_batches=1`; `tii-property-006` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-005` is complete by official row coverage: `1391 / 1391` official result rows, `1391` imported product cards, `0` official duplicate product-id rows, `140` saved result pages, and `1391` saved detail pages.
- Production data preserves `69` same-company same-name multi-product groups as `146` separate cards.
- Production UI renders query controls, `5,577` imported TII policies, `5,572` saved detail pages, `6,153` official result rows, and `576` official duplicate rows.

## 2026-06-04 TII Same-Name Version Preservation

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Release commit: `a58e8ac`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for same-name version preservation: `dpl_Bodvod5DVsc2xoQn8F4T7Sd4K9ii`
- Deployment URL: <https://taiwan-insurance-policy-navigator-6x2ra3n7r.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=4186`, `detail_saved_count=4181`, `indexed_batch_count=4`, and `completed_batch_count=4`.
- Production data includes `record_identity_key`, `identity_basis`, and `edition_label` for TII records.
- Production data preserves `66` same-company same-name multi-product groups as `140` separate cards.
- Production UI renders `140` same-name version chips and `140` version-note blocks; the TII status area states that cards are not merged by name.

## 2026-06-04 Fourth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `19266db`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed fourth TII batch data: `dpl_BaNarjme7Rpv6DUXsFgjW8479x4U`
- Deployment URL: <https://taiwan-insurance-policy-navigator-8rxd7q708.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=4186`, `detail_saved_count=4181`, `indexed_batch_count=4`, `completed_batch_count=4`, `partial_batch_count=0`, and pending manual batches `302`.
- TII execution progress shows `attempted_batches=5`, `completed_batches=4`, `captcha_required_batches=1`; `tii-property-005` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-004` is complete by official row coverage: `2667 / 2667` official result rows, `2091` deduplicated product cards, `576` official duplicate product-id rows, `267` saved result pages, and `2087` saved detail pages; `4` official detail pages returned invalid detail sessions on retry.
- Production UI renders query controls, `4,186` imported TII policies, `4,181` saved detail pages, `4,762` official result rows, and `576` official duplicate rows.

## 2026-06-04 Third TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `78574bb`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed third TII batch data: `dpl_TKLRPt5Kj87qUsogpAnsoKhTyeAs`
- Deployment URL: <https://taiwan-insurance-policy-navigator-914rvs865.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=2095`, `indexed_batch_count=3`, `completed_batch_count=3`, `partial_batch_count=0`, and pending manual batches `303`.
- `tii-property-001` is `952 / 952` with `96` saved result pages and `952` saved detail pages.
- `tii-property-002` is `618 / 618` with `62` saved result pages and `617` saved detail pages; `1` official detail page returned an invalid detail session.
- `tii-property-003` is `525 / 525` with `53` saved result pages and `525` saved detail pages.
- Production UI renders query controls, `2,095` imported TII policies, `2,094` saved detail pages, and the third batch data.

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
