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

Audit selected products that still need parser work:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action audit-gaps --category ?瑕拿靽 --max-groups 15
```

Promote already reviewed approvals and rebuild summaries:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action promote-approved --batch-id tii-life-007
```

Run the normal release checks:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action verify
```

Run a bounded end-to-end cycle without auto-approving new benefits:

```powershell
python -X utf8 scripts\run_tii_benefit_batch_task.py --action all --max-groups 5
```

## Approval Boundary

The approval source of truth remains `work/tii-benefit-approvals/*.json`. A benefit schedule becomes public only after:

1. A parser extracts one exact candidate for a `batch_id + product_id`.
2. The source document hash and schedule hash are captured.
3. A review entry approves that exact candidate.
4. `extract_tii_plan_benefits.py --approval-file ...` promotes it.
5. Validation passes.

## Suggested Operating Loop

1. Run `plan` and select the next group.
2. Run `audit-gaps` to separate products with existing proposals from products needing parser work.
3. Implement or reuse a parser for the missing products.
4. Run parser tests.
5. Run `prepare-proposals --write-proposals`.
6. Create approval entries only after source review.
7. Run `promote-approved`.
8. Run `verify`.
9. Commit, push, or deploy only when Kevin asks.

This keeps the process fast while avoiding false certainty in high-stakes insurance terms.
