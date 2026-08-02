# TII Life Calculation Readiness

- Generated at: `2026-08-01T07:33:50+08:00`
- Version boundary: `source_batch_id + product_id + source document`

## Goal

All life-insurance product versions should produce benefit numbers after collecting the inputs required by official terms, or have a clear unresolved reason.

## Completion

- Ready for user number flow: `3078`
- Coverage schedule ready: `3078`
- Claim scenario total ready: `2726`
- Coverage schedule only: `352`
- Unresolved: `60266`
- Ready rate: `0.0486`

## Status Counts

- `needs_parser_or_proposal`: `55635`
- `reviewable_proposal_pending`: `2676`
- `reviewable_upgrade_pending`: `1118`
- `source_pending`: `837`
- `structured_needs_policy_state`: `2679`
- `structured_user_input_calculable`: `399`

## Category Summary

| Category | Total | Ready | Unresolved | Ready rate |
| --- | ---: | ---: | ---: | ---: |
| 健康保險 | 14908 | 219 | 14689 | 0.0147 |
| 傳統型壽險 | 16839 | 220 | 16619 | 0.0131 |
| 傳統型年金 | 1029 | 0 | 1029 | 0.0 |
| 傷害保險 | 9390 | 187 | 9203 | 0.0199 |
| 投資型壽險 | 14565 | 645 | 13920 | 0.0443 |
| 投資型年金 | 6613 | 1807 | 4806 | 0.2732 |

## Most Common Required Inputs

- `policy_recorded_limit`: `3715`
- `policy_account_value`: `2611`
- `basic_face_amount`: `1977`
- `annuity_factor`: `1807`
- `base_amount`: `1324`
- `current_insured_amount`: `1065`
- `paid_premium_total`: `1065`
- `policy_value_reserve`: `1065`
- `policy_type`: `804`
- `insurance_deduction_amount`: `792`
- `threshold_factor`: `580`
- `premium_or_paid_premium`: `239`
- `plan`: `237`
- `days`: `180`
- `actual_medical_expense`: `172`
- `units`: `144`
- `unexpired_premium`: `114`
- `hospital_daily_amount`: `27`

## Next Groups

- `reviewable_upgrade_pending:投資型壽險:tii-life-095`: `804` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:投資型壽險:tii-life-029`: `94` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:傳統型壽險:tii-life-009`: `65` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:投資型壽險:tii-life-017`: `41` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:投資型壽險:tii-life-011`: `38` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:健康保險:tii-life-050`: `38` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:傳統型壽險:tii-life-051`: `15` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:健康保險:tii-life-026`: `9` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:健康保險:tii-life-014`: `6` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:傷害保險:tii-life-013`: `4` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:傳統型壽險:tii-life-117`: `2` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:健康保險:tii-life-008`: `1` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_upgrade_pending:健康保險:tii-life-116`: `1` records. Source-review the newer exact-source schedule before replacing the currently reviewed calculation contract.
- `reviewable_proposal_pending:投資型壽險:tii-life-173`: `803` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:健康保險:tii-life-050`: `222` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:健康保險:tii-life-080`: `156` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:健康保險:tii-life-032`: `107` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:健康保險:tii-life-014`: `105` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:健康保險:tii-life-008`: `100` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
- `reviewable_proposal_pending:投資型壽險:tii-life-053`: `100` records. Source-review the proposal against exact source_batch_id + product_id + source document before promotion.
