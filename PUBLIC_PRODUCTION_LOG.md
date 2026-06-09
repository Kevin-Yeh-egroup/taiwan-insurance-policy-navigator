# Public Production Log

## 2026-06-09 Forty-sixth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `28c2e9d`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed forty-sixth TII batch data: `dpl_AUZ85zBtZQf82coVJicJtiKMDuMf`
- Deployment URL: <https://taiwan-insurance-policy-navigator-kivnt4keq.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=63191`, `detail_saved_count=62982`, `detail_missing_count=209`, `completed_batches=46`, `pending_manual_batches=260`, `latest_completed_batch=tii-property-046`, and `current_waiting_batch=tii-property-047`.
- `data/tii-policy-results.json` range request returned `206 Partial Content` and includes the same `63191` record / `62982` saved-detail production dataset, `detail_missing_count=209`, `completed_batch_count=46`, and `tii-property-046` in the completed batch list. Full object length reported `65409249` bytes.
- Manual page returned `200 OK` and includes the `63,191` record / `46 / 306` completed-batch update plus the `tii-property-047` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=47`, `completed_batches=46`, `captcha_required_batches=1`; `tii-property-047` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-046` is complete by official rows: `677 / 677` official result rows, `677` imported product cards, and `672 / 677` saved detail pages, with `5` detail pages marked for later backfill.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Forty-fifth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `5a374dd`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed forty-fifth TII batch data: `dpl_6AUBGSJKAKEPuiMV7KXa2CkxeUz9`
- Deployment URL: <https://taiwan-insurance-policy-navigator-9vqmtxes5.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=62514`, `detail_saved_count=62310`, `detail_missing_count=204`, `completed_batches=45`, `pending_manual_batches=261`, `latest_completed_batch=tii-property-045`, and `current_waiting_batch=tii-property-046`.
- `data/tii-policy-results.json` range request returned `206 Partial Content` and includes the same `62514` record / `62310` saved-detail production dataset, `detail_missing_count=204`, `completed_batch_count=45`, and `tii-property-045` in the completed batch list. Full object length reported `64698347` bytes.
- Manual page returned `200 OK` and includes the `62,514` record / `45 / 306` completed-batch update plus the `tii-property-046` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=46`, `completed_batches=45`, `captcha_required_batches=1`; `tii-property-046` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-045` is complete by official rows: `1198 / 1198` official result rows, `1198` imported product cards, and `1198 / 1198` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Forty-fourth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `9c9778b`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed forty-fourth TII batch data: `dpl_8Fz12we48m8yaJY1aTs3ptGh6wAw`
- Deployment URL: <https://taiwan-insurance-policy-navigator-83mqy19w7.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=61316`, `detail_saved_count=61112`, `detail_missing_count=204`, `completed_batches=44`, `pending_manual_batches=262`, `latest_completed_batch=tii-property-044`, and `current_waiting_batch=tii-property-045`.
- `data/tii-policy-results.json` range request returned `206 Partial Content` and includes the same `61316` record / `61112` saved-detail production dataset, `detail_missing_count=204`, `completed_batch_count=44`, and `tii-property-044` in the completed batch list. Full object length reported `63469781` bytes.
- Manual page returned `200 OK` and includes the `61,316` record / `44 / 306` completed-batch update plus the `tii-property-045` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=45`, `completed_batches=44`, `captcha_required_batches=1`; `tii-property-045` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-044` is complete by official rows: `3621 / 3621` official result rows, `2801` imported product cards, `820` official duplicate product-id rows, and `2793 / 2801` saved detail pages, with `8` detail pages marked for later backfill.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Forty-second and Forty-third TII Batches Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `733f65e`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed forty-second and forty-third TII batch data: `dpl_4PdtYMoMR8d4j4TdVSuFy8iTAg3K`
- Deployment URL: <https://taiwan-insurance-policy-navigator-h8sa8jpkj.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=58515`, `detail_saved_count=58319`, `detail_missing_count=196`, `completed_batches=43`, `pending_manual_batches=263`, `latest_completed_batch=tii-property-043`, and `current_waiting_batch=tii-property-044`.
- `data/tii-policy-results.json` range request returned `206 Partial Content` and includes the same `58515` record / `58319` saved-detail production dataset, `completed_batch_count=43`, and `tii-property-043` in the completed batch list. Full object length reported `60570223` bytes.
- Manual page returned `200 OK` and includes the `58,515` record / `43 / 306` completed-batch update plus the `tii-property-044` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=44`, `completed_batches=43`, `captcha_required_batches=1`; `tii-property-044` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-042` is complete by official rows: `1610 / 1610` official result rows, `1610` imported product cards, and `1603 / 1610` saved detail pages, with `7` detail pages marked for later backfill.
- `tii-property-043` is complete by official rows: `731 / 731` official result rows, `731` imported product cards, and `731 / 731` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Thirty-eighth through Forty-first TII Batches Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `3449af0`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-eighth through forty-first TII batch data: `dpl_7JFUnbKFrBjoECdMnRFeA3jwrUpx`
- Deployment URL: <https://taiwan-insurance-policy-navigator-dk8sgs32l.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=56174`, `detail_saved_count=55985`, `completed_batches=41`, `pending_manual_batches=265`, `latest_completed_batch=tii-property-041`, and `current_waiting_batch=tii-property-042`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `56174` record / `55985` saved-detail production dataset, `completed_batch_count=41`, and `tii-property-041` in the completed batch list.
- Manual page returned `200 OK` and includes the `56,174` record / `41 / 306` completed-batch update plus the `tii-property-042` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=42`, `completed_batches=41`, `captcha_required_batches=1`; `tii-property-042` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-038` is complete by official rows: `24 / 24` official result rows, `24` imported product cards, and `24 / 24` saved detail pages.
- `tii-property-039` is complete by official rows: `5 / 5` official result rows, `5` imported product cards, and `5 / 5` saved detail pages.
- `tii-property-040` is complete by official rows: `40 / 40` official result rows, `40` imported product cards, and `40 / 40` saved detail pages.
- `tii-property-041` is complete by official rows: `1131 / 1131` official result rows, `1131` imported product cards, and `1131 / 1131` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Thirty-seventh TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `213721a`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-seventh TII batch data: `dpl_39BbpgbwsS9snazFHkFcv7NR88nF`
- Deployment URL: <https://taiwan-insurance-policy-navigator-biee1a8zr.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=54974`, `detail_saved_count=54785`, `completed_batches=37`, `pending_manual_batches=269`, `latest_completed_batch=tii-property-037`, and `current_waiting_batch=tii-property-038`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `54974` record / `54785` saved-detail production dataset, `completed_batch_count=37`, and `tii-property-037` in the completed batch list.
- Manual page returned `200 OK` and includes the `54,974` record / `37 / 306` completed-batch update plus the `tii-property-038` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=38`, `completed_batches=37`, `captcha_required_batches=1`; `tii-property-038` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-037` is complete by official rows: `25 / 25` official result rows, `25` imported product cards, and `25 / 25` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Thirty-sixth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `adcfb25`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-sixth TII batch data: `dpl_C2seGLP1fLYHCBHLmjuFNVJoMfJc`
- Deployment URL: <https://taiwan-insurance-policy-navigator-ewdwmiql7.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=54949`, `detail_saved_count=54760`, `completed_batches=36`, `pending_manual_batches=270`, and `current_waiting_batch=tii-property-037`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `54949` record / `54760` saved-detail production dataset, `completed_batch_count=36`, and `tii-property-036` in the completed batch list.
- Manual page returned `200 OK` and includes the `54,949` record / `36 / 306` completed-batch update plus the `tii-property-037` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=37`, `completed_batches=36`, `captcha_required_batches=1`; `tii-property-037` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-036` is complete by official rows: `2163 / 2163` official result rows, `1837` imported product cards, `326` official duplicate product-id rows, and `1837 / 1837` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Thirty-fifth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `f0374ea`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-fifth TII batch data: `dpl_HAjkLFPbVB3V2HEEcA13RRrvznRL`
- Deployment URL: <https://taiwan-insurance-policy-navigator-7wkemdh2q.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=53112`, `detail_saved_count=52923`, `completed_batch_count=35`, and `pending_manual_batch_count=271`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `53112` record / `52923` saved-detail production dataset.
- Manual page returned `200 OK` and includes the `53,112` record / `35 / 306` completed-batch update plus the `tii-property-036` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=36`, `completed_batches=35`, `captcha_required_batches=1`; `tii-property-036` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-035` is complete by official rows: `488 / 488` official result rows, `488` imported product cards, and `487 / 488` saved detail pages, with `1` detail page marked for later backfill.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-09 Thirty-fourth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `cd8a82f`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-fourth TII batch data: `dpl_9FDvDDd4DBqLTdvWiEbvWCo1DbQG`
- Deployment URL: <https://taiwan-insurance-policy-navigator-89qyf7c5t.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=52624`, `detail_saved_count=52436`, `completed_batch_count=34`, and `pending_manual_batch_count=272`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `52624` record / `52436` saved-detail production dataset.
- Manual page returned `200 OK` and includes the `52,624` record / `34 / 306` completed-batch update plus the `tii-property-035` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=35`, `completed_batches=34`, `captcha_required_batches=1`; `tii-property-035` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-034` is complete by official rows: `888 / 888` official result rows, `888` imported product cards, and `879 / 888` saved detail pages, with `9` detail pages marked for later backfill.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-08 Thirty-third TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `bf9bc46`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-third TII batch data: `dpl_ABVzG3P1YMmziYMq1wxbkzpcX3Xq`
- Deployment URL: <https://taiwan-insurance-policy-navigator-cja0r34wk.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `imported_policy_records=51736`, `detail_saved_count=51557`, `completed_batch_count=33`, and `pending_manual_batch_count=273`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `51736` record / `51557` saved-detail production dataset.
- Manual page returned `200 OK` and includes the `51,736` record / `33 / 306` completed-batch update plus the `tii-property-034` waiting-batch note.
- README returned `200 OK` and includes the same `51,736` record / `33 / 306` progress note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=34`, `completed_batches=33`, `captcha_required_batches=1`; `tii-property-034` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-032` is complete by official rows: `6486 / 6486` official result rows, `4543` imported product cards, `1943` official duplicate product-id rows, `4531 / 4543` saved detail pages, and `12` detail pages marked for later backfill.
- `tii-property-033` is complete: `1180 / 1180` official result rows, `1180` imported product cards, and `1180 / 1180` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-08 Thirty-first TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `c88354d`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed thirty-first TII batch data: `dpl_2PRfnYfswJoCdtumuGYzfj5NjrDX`
- Deployment URL: <https://taiwan-insurance-policy-navigator-4u48qqbqt.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- `data/site-summary.json` returned `200 OK` and includes `record_count=46013`, `detail_saved_count=45846`, `completed_batch_count=31`, and `pending_manual_batch_count=275`.
- `data/tii-policy-results.json` returned `200 OK` and includes the same `46013` record / `45846` saved-detail production dataset.
- Manual page returned `200 OK` and includes the `46,013` record / `31 / 306` completed-batch update.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- TII execution progress shows `attempted_batches=32`, `completed_batches=31`, `captcha_required_batches=1`; `tii-property-032` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-031` is complete: `1746 / 1746` official result rows, `1746` imported product cards, and `1746 / 1746` saved detail pages.
- Production data preserves same-company same-name multi-product groups as separate policy cards and keeps the same-name version timeline with sale date, discontinued date, and policy code.

## 2026-06-08 Twenty-ninth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `cba88d3`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-ninth TII batch data: `dpl_DspQpk5WXC3913PRAR8pccxWCoX1`
- Deployment URL: <https://taiwan-insurance-policy-navigator-ovkbc85zj.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `43,008` record / `29 / 306` completed-batch update plus the `tii-property-030` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=43008`, `detail_expected_count=43008`, `detail_saved_count=42874`, `detail_missing_count=134`, `indexed_batch_count=29`, `completed_batch_count=29`, `partial_batch_count=0`, and pending manual batches `277`.
- TII execution progress shows `attempted_batches=30`, `completed_batches=29`, `captcha_required_batches=1`; `tii-property-030` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-029` is complete: `1040 / 1040` official result rows, `1040` imported product cards, `0` official duplicate product-id rows, `104` saved result pages, and `1040 / 1040` saved detail pages.
- Production data preserves `1283` same-company same-name multi-product groups as `3431` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-eighth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `1aca062`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-eighth TII batch data: `dpl_5ttmNn6eA65Z7Rqb59Hw3mPLzxo5`
- Deployment URL: <https://taiwan-insurance-policy-navigator-ky4klpg7a.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `41,968` record / `28 / 306` completed-batch update plus the `tii-property-029` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=41968`, `detail_expected_count=41968`, `detail_saved_count=41834`, `detail_missing_count=134`, `indexed_batch_count=28`, `completed_batch_count=28`, `partial_batch_count=0`, and pending manual batches `278`.
- TII execution progress shows `attempted_batches=29`, `completed_batches=28`, `captcha_required_batches=1`; `tii-property-029` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-028` is complete by official row coverage: `4285 / 4285` official result rows, `3461` imported product cards, `824` official duplicate product-id rows, `429` saved result pages, and `3460 / 3461` saved detail pages; `1` official detail page returned an invalid detail response and remains marked for later backfill.
- Production data preserves `1283` same-company same-name multi-product groups as `3431` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-seventh TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `518e2ec`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-seventh TII batch data: `dpl_FQdbqNcQVwY37r3NF6pGbUW4tJLW`
- Deployment URL: <https://taiwan-insurance-policy-navigator-cec25vo6a.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `38,507` record / `27 / 306` completed-batch update plus the `tii-property-028` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=38507`, `detail_expected_count=38507`, `detail_saved_count=38374`, `detail_missing_count=133`, `indexed_batch_count=27`, `completed_batch_count=27`, `partial_batch_count=0`, and pending manual batches `279`.
- TII execution progress shows `attempted_batches=28`, `completed_batches=27`, `captcha_required_batches=1`; `tii-property-028` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-027` is complete by official row coverage: `1462 / 1462` official result rows, `1462` imported product cards, `0` official duplicate product-id rows, `147` saved result pages, and `1455 / 1462` saved detail pages; `7` official detail pages returned invalid detail responses and remain marked for later backfill.
- Production data preserves `1253` same-company same-name multi-product groups as `3371` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-sixth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `0ef3543`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-sixth TII batch data: `dpl_G9Zz1Jsq1YhGJqL9m9PYco5r5Zg6`
- Deployment URL: <https://taiwan-insurance-policy-navigator-2puqmxrru.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `37,045` record / `26 / 306` completed-batch update plus the `tii-property-027` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=37045`, `detail_expected_count=37045`, `detail_saved_count=36919`, `detail_missing_count=126`, `indexed_batch_count=26`, `completed_batch_count=26`, `partial_batch_count=0`, and pending manual batches `280`.
- TII execution progress shows `attempted_batches=27`, `completed_batches=26`, `captcha_required_batches=1`; `tii-property-027` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-026` is complete by official row coverage: `610 / 610` official result rows, `610` imported product cards, `0` official duplicate product-id rows, `61` saved result pages, and `605 / 610` saved detail pages; `5` official detail pages returned invalid detail responses and remain marked for later backfill.
- Production data preserves `1231` same-company same-name multi-product groups as `3322` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-fifth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `cb7af05`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-fifth TII batch data: `dpl_2WApSjwmpnNyt58zcWYNG7okMFGh`
- Deployment URL: <https://taiwan-insurance-policy-navigator-1h6mcys4z.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `36,435` record / `25 / 306` completed-batch update plus the `tii-property-026` waiting-batch note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=36435`, `detail_expected_count=36435`, `detail_saved_count=36314`, `detail_missing_count=121`, `indexed_batch_count=25`, `completed_batch_count=25`, `partial_batch_count=0`, and pending manual batches `281`.
- TII execution progress shows `attempted_batches=26`, `completed_batches=25`, `captcha_required_batches=1`; `tii-property-026` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-025` is complete: `1156 / 1156` official result rows, `1156` imported product cards, `0` official duplicate product-id rows, `116` saved result pages, and `1156 / 1156` saved detail pages.
- Production data preserves `1228` same-company same-name multi-product groups as `3316` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-fourth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `ecca610`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-fourth TII batch data: `dpl_4sD1xDDv3LxDa4pJfqKhADB8kUmg`
- Deployment URL: <https://taiwan-insurance-policy-navigator-l743jhm41.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `35,279` record / `24` completed-batch update.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` returned `200 OK` and remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=35279`, `detail_expected_count=35279`, `detail_saved_count=35158`, `detail_missing_count=121`, `indexed_batch_count=24`, `completed_batch_count=24`, `partial_batch_count=0`, and pending manual batches `282`.
- TII execution progress shows `attempted_batches=25`, `completed_batches=24`, `captcha_required_batches=1`; `tii-property-025` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-024` is complete: `1785 / 1785` official result rows, `1400` imported product cards, `385` official duplicate product-id rows, `179` saved result pages, and `1400 / 1400` saved detail pages.
- Production data preserves `1220` same-company same-name multi-product groups as `3299` separate cards.
- Discontinued-policy cards keep the same-name version timeline, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-08 Twenty-third TII Batches And Version Timeline

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `51f0f43`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-third TII batch data: `dpl_7VDM5eEn2dDmZHKVmQgcUMhGJJ4g`
- Deployment URL: <https://taiwan-insurance-policy-navigator-hm7ra6h7r.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `33,879` record / `23` completed-batch update plus the same-name version timeline note.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=33879`, `detail_saved_count=33758`, `detail_missing_count=121`, `indexed_batch_count=23`, `completed_batch_count=23`, `partial_batch_count=0`, and pending manual batches `283`.
- TII execution progress shows `attempted_batches=24`, `completed_batches=23`, `captcha_required_batches=1`; `tii-property-024` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-022` is complete: `706 / 706` official result rows, `706` imported product cards, `71` saved result pages, and `705 / 706` saved detail pages; `1` official detail page remains marked for later backfill.
- `tii-property-023` is complete: `846 / 846` official result rows, `846` imported product cards, `85` saved result pages, and `844 / 846` saved detail pages; `2` official detail pages remain marked for later backfill.
- Production data preserves `1183` same-company same-name multi-product groups as `3219` separate cards.
- Discontinued-policy cards render a same-name version timeline for multi-product groups, showing sale date, discontinued date, and policy code without deduplicating by policy name.

## 2026-06-05 Twenty-first TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `f0c2855`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed twenty-first TII batch data: `dpl_5ajkRXZGpom84aU88ckxCbWKTggb`
- Deployment URL: <https://taiwan-insurance-policy-navigator-l89rgeeus.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Manual page returned `200 OK` and includes the `32,327` record / `21` completed-batch update.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=32327`, `detail_expected_count=32327`, `detail_saved_count=32209`, `detail_missing_count=118`, `indexed_batch_count=21`, `completed_batch_count=21`, `partial_batch_count=0`, and pending manual batches `285`.
- TII execution progress shows `attempted_batches=22`, `completed_batches=21`, `captcha_required_batches=1`; `tii-property-022` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-020` is complete by official row coverage: `5159 / 5159` official result rows, `3874` imported product cards, `1285` official duplicate product-id rows, `516` saved result pages, and `3835 / 3874` saved detail pages; `39` official detail pages remain marked for later backfill.
- `tii-property-021` is complete by official row coverage: `1173 / 1173` official result rows, `1163` imported product cards, `10` official duplicate product-id rows, `118` saved result pages, and `1163 / 1163` saved detail pages.
- Production data preserves `1164` same-company same-name multi-product groups as `3181` separate cards.
- Production UI/data renders `32,327` imported TII policies, `32,209` saved detail pages, `118` detail-page backfill gaps, `37,039` official result rows, and `4,712` official duplicate rows.

## 2026-06-05 Nineteenth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `2c0535e`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed nineteenth TII batch data: `dpl_AESUFWtxsCehRtU53E113ynZYtye`
- Deployment URL: <https://taiwan-insurance-policy-navigator-oyuu2lgxq.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=27290`, `detail_saved_count=27211`, `indexed_batch_count=19`, `completed_batch_count=19`, `partial_batch_count=0`, and pending manual batches `287`.
- TII execution progress shows `attempted_batches=20`, `completed_batches=19`, `captcha_required_batches=1`; `tii-property-020` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-019` is complete: `1576 / 1576` official result rows, `1576` imported product cards, `0` official duplicate product-id rows, `158` saved result pages, and `1569` saved detail pages; `7` official detail pages returned invalid detail sessions.
- Production data preserves `1043` same-company same-name multi-product groups as `2667` separate cards.
- Production UI/data renders `27,290` imported TII policies, `27,211` saved detail pages, `30,707` official result rows, and `3,417` official duplicate rows.

## 2026-06-05 Eighteenth TII Batch Complete

Repository:

- GitHub: <https://github.com/Kevin-Yeh-egroup/taiwan-insurance-policy-navigator>
- Visibility: public
- Branch: `main`
- Completed-data commit: `0a1c7a7`

Vercel:

- Project: `taiwan-insurance-policy-navigator`
- Team: `egroup-task3s-projects`
- Production URL: <https://taiwan-insurance-policy-navigator.vercel.app/>
- Verified deployment for completed eighteenth TII batch data: `dpl_BSBMSbyGhSSLmg959oETKzcZbBGW`
- Deployment URL: <https://taiwan-insurance-policy-navigator-7cqfb8cc6.vercel.app>
- Target: production
- Status: READY

Verification:

- Root returned `200 OK`.
- Vercel header remained `X-Robots-Tag: noindex, nofollow, noarchive`.
- HTML meta robots remained `noindex,nofollow,noarchive`.
- `robots.txt` remained `User-agent: *` / `Disallow: /`.
- Production data shows TII `record_count=25714`, `detail_saved_count=25642`, `indexed_batch_count=18`, `completed_batch_count=18`, `partial_batch_count=0`, and pending manual batches `288`.
- TII execution progress shows `attempted_batches=19`, `completed_batches=18`, `captcha_required_batches=1`; `tii-property-019` is prepared and waiting for a fresh human-entered captcha.
- `tii-property-017` is complete: `1233 / 1233` official result rows, `1233` imported product cards, `0` official duplicate product-id rows, `124` saved result pages, and `1233` saved detail pages.
- `tii-property-018` is complete: `940 / 940` official result rows, `940` imported product cards, `0` official duplicate product-id rows, `94` saved result pages, and `938` saved detail pages; `2` official detail pages returned invalid detail sessions.
- The runner/importer now stores saved result/detail path samples instead of full path lists in progress JSON, while preserving counts for validation and imports.
- Production data preserves `1002` same-company same-name multi-product groups as `2470` separate cards.
- Production UI/data renders `25,714` imported TII policies, `25,642` saved detail pages, `29,131` official result rows, and `3,417` official duplicate rows.

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
