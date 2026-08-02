# TII Benefit Batch Automation

This project uses a local, bounded batch task for TII benefit structuring. The task is designed to reduce manual repetition while keeping source review in the loop.

## What It Automates

- Rebuild the remaining benefit-structure queue.
- Pick the next queue groups by category, batch, company, and limit.
- Generate proposal files for parsers that already exist.
- Audit selected queue products that still have no proposal, so parser gaps are explicit.
- Promote schedules only when an approval file already exists.
- Rebuild public document summaries for touched batches.
- Run validation and frontend coverage-model tests.
- Write a run report under `work/tii-benefit-automation/runs/`.

## What It Does Not Automate

- It does not solve or bypass TII captcha.
- It does not approve newly extracted policy benefits.
- It does not infer benefits from product names alone.
- It does not publish full terms text.
- It does not commit, push, or deploy.

## Common Commands

Build the exhaustive local completion queues for both unfinished states:

```powershell
python -X utf8 scripts\build_tii_completion_queues.py
```

Build the parser-family work queue from the current exact-version readiness
records:

```powershell
python -X utf8 scripts\build_tii_parser_family_queue.py
```

This planning queue groups only for parser-development efficiency. It keeps
every exact `batch_id + product_id` in each group and never authorizes merging,
approval, or promotion. It separates:

- `benefit_parser`: a policy or rider that needs a deterministic benefit parser;
- `additional_terms_review`: terms that may modify a base contract;
- `endorsement_review`: endorsements that may change benefits or only
  administrative/investment mechanics.

The current snapshot has 57,192 parser gaps in 16,349 work families. The
batch-task runner reads this parser-family queue by default; the legacy
`structure-queue.json` remains supported only when passed explicitly.
Within `benefit_parser`, the default queue order is health, injury, traditional
life, investment life, traditional annuity, then investment annuity. Larger
families come first only inside the same category. Use a bounded claim for the
actual development slice.

Claim one small parser family before implementation:

```powershell
python -X utf8 scripts\claim_tii_parser_family.py claim `
  --owner Kevin `
  --task-id <current-task-id> `
  --max-records 30
```

The claim records the exact queue SHA-256, `queue_id`, version set, owner, task,
and lease expiry. A different task skips an active claim; an expired or released
claim is archived before replacement. Use `renew` or `release` with the current
claim file and claim id.

Run one bounded local completion pass:

```powershell
python -X utf8 scripts\run_tii_completion_batch.py --max-groups 3 --source-groups 8
```

Plan the next five queue groups:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action plan --max-groups 5
```

Plan only accident insurance groups:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action plan --category 傷害保險 --max-groups 15
```

Generate proposal output after a parser has been added:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action prepare-proposals --batch-id tii-life-007 --write-proposals
```

For an exact reviewed parser slice, use a prior proposal or a slice manifest as
the source of the batch, parser, product IDs, and source hashes. Bind the run to
the active claim when it comes from the parser-family queue:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py `
  --action prepare-proposals `
  --claim-file work\tii-parser-family-claims\<family-fingerprint>.json `
  --task-id <current-task-id> `
  --exact-slice work\tii-benefit-proposals\tii-life-050-fubon-cancer-claim-inputs-v220.json `
  --proposal-output work\tii-benefit-proposals\tii-life-050-fubon-cancer-claim-inputs-v220.json `
  --review-packet-output work\tii-benefit-review-packets\tii-life-050-fubon-cancer-claim-inputs-v220 `
  --write-proposals
```

The exact-slice path is the preferred proposal-generation route once the parser
family and target versions are known. It:

- runs only the requested `product_id` values;
- requires every requested product to produce one exact parser match;
- checks batch, parser, product set, source file, source SHA-256, and schedule hash;
- writes to a `.pending` proposal first and atomically replaces the final file
  only after validation;
- builds the human review packet after the exact proposal passes.

`structure-queue.json` can be empty while the exhaustive completion queue still
has unresolved records. The default planning source is therefore
`work/tii-life-calculation-readiness/parser-family-queue.json`. An explicit
exact slice also runs independently of either queue. Do not treat
`queue_groups: 0` as completion without checking readiness and source-pending
queues.

Audit selected products that still need parser work:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action audit-gaps --category 傷害保險 --max-groups 15
```

Promote already reviewed approvals and rebuild summaries:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action promote-approved --batch-id tii-life-007
```

Run the normal release checks:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action verify
```

Use layered verification during parser development:

1. Run parser-specific tests, the matching frontend-flow test, coverage-model
   tests, and `validate_data.py` after each exact slice.
2. Build several review-only proposal slices without promoting them.
3. Run the full `test_tii_plan_benefits.py` regression once after shared parser
   or calculation-model changes and before commit, push, or deploy.
4. Rebuild readiness, coverage audit, and completion queues once at the end of
   the grouped work session instead of after every unapproved proposal.

This keeps fast feedback under a few seconds for exact slices while retaining
the complete regression and audit gates at the integration boundary.

Strict-source text extraction uses a disposable cache under
`work/tii-source-text-cache/`. A cache entry is reused only after all of these
checks pass:

- the current PDF bytes still match the exact source SHA-256;
- the requested extractor and its installed package version match;
- the cache schema version matches;
- the cached normalized text matches its own SHA-256.

Any mismatch triggers a fresh extraction. The cache never authorizes a parser,
proposal, approval, or promotion, and can be disabled for a run with
`TII_DISABLE_STRICT_SOURCE_CACHE=1`.

Run the bounded orchestration pass:

```powershell
python -X utf8 scripts\run_tii_completion_batch.py --max-groups 5 --source-groups 8
```

This rebuilds the completion queues, audits proposal gaps, and runs verification
as separate explicit commands. It does not call the broad `all` action or
promote approval files.

## Approval Boundary

The approval source of truth remains `work/tii-benefit-approvals/*.json`. A benefit schedule becomes public only after:

1. A parser extracts one exact candidate for a `batch_id + product_id`.
2. The source document hash and schedule hash are captured.
3. A review entry approves that exact candidate.
4. `extract_tii_plan_benefits.py --approval-file ...` promotes it.
5. Validation passes.

## Suggested Operating Loop

1. Rebuild the readiness and parser-family queues.
2. Claim one bounded family and record the exact version set.
3. Run `audit-gaps` with the claim to separate existing proposals from parser work.
4. Implement or reuse a deterministic parser for only the claimed products.
5. Run parser tests.
6. Run claimed `prepare-proposals --write-proposals` with an exact slice.
7. Create approval entries only after source review.
8. Release the claim, then run `promote-approved` only when approval files exist.
9. Run `verify`.
10. Commit, push, or deploy only when Kevin asks.

This keeps the process fast while avoiding false certainty in high-stakes insurance terms.

## Measured Performance

On the 17-version `fubon-cancer-unit-v1` slice:

- unfiltered batch execution exceeded 184 seconds before the safety timeout;
- exact-slice proposal generation completed in 1.925 seconds;
- exact source expectations passed 17 / 17;
- review-packet generation completed in 0.206 seconds.

The speedup comes from eliminating irrelevant batch scans. It does not reduce
the exact-version boundary, source-hash checks, human approval, or full
regression requirement.

On the 59-version `farglory-ginjili-variable-universal-life-v1` slice:

- the first exact-source validation pass completed in 54.276 seconds;
- the second pass completed in 1.238 seconds after cache population;
- all 59 proposal schedules, six semantic groups, and ten source gaps remained
  unchanged;
- every cache hit still re-hashed the current PDF bytes first.

This measured repeat-run speedup is about 44 times. It accelerates revalidation
without allowing stale or cross-version text reuse.

Review packets also group identical `schedule_sha256` values for structural
review efficiency while retaining every exact product and source hash. At the
current readiness snapshot, 1,115 upgrade proposals reduce to 159 distinct
schedule-review groups across 24 batch/parser families; all 1,115 exact product
versions still require source confirmation before approval.

## Completion Queue Boundary

`pending_structure` and `source_pending` are separate work pools:

- `pending_structure` means a source summary exists, but the exact `source_batch_id + product_id` has not yet been promoted into reviewed benefit entries.
- `candidate_ready` inside the completion queue includes both legacy candidate snapshots and reviewable proposal files under `work/tii-benefit-proposals/`. It means "ready for source review/promotion", not "already verified".
- `source_pending` means the TII product record exists, but the local public summary does not yet have usable source terms for that exact version.
- Source backfill can only use official saved TII detail pages and human-completed CAPTCHA sessions. The automation prepares the next batch and continues after a human CAPTCHA; it does not solve or bypass CAPTCHA.
- Queue files live under `work/tii-completion-queues/` and are local-only because they may contain operational source paths.
- Canonical queue and readiness writers use atomic replacement and one
  repository-local integration lock. A concurrent writer fails closed instead
  of partially replacing shared JSON/JSONL files.

## Source Backfill CAPTCHA Runbook

Most remaining `source_pending` records are not missing because the terms are unavailable; they are gated by the official TII CAPTCHA/session flow. Use this process:

1. Rebuild the queue:

```powershell
python -X utf8 scripts\build_tii_completion_queues.py
```

2. Inspect the next source batch in `work\tii-completion-queues\source-pending-groups.json`.

3. Start the local operator page:

```powershell
python -X utf8 scripts\tii_operator_server.py
```

Open `http://127.0.0.1:8765/submit`, enter the CAPTCHA shown there, and let the worker run. The operator downloads at most 800 document links per CAPTCHA window, then continues from the next offset if a batch has more documents.

4. After a successful document download, rebuild extracted content and queues:

```powershell
python -X utf8 scripts\build_tii_document_summaries.py
python -X utf8 scripts\audit_tii_coverage_data.py --output docs\TII_COVERAGE_DATA_AUDIT.json | Set-Content -Path docs\TII_COVERAGE_DATA_AUDIT.md -Encoding utf8
python -X utf8 scripts\build_tii_completion_queues.py
python -X utf8 scripts\validate_data.py
```

This turns downloaded source files into `pending_structure` records. It does not automatically verify benefit amounts; exact benefit schedules still require parser/proposal review and approval promotion.
