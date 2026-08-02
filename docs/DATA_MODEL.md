# Data Model

The public site separates source discovery, crawl status, content extraction proof, and future reviewed policy facts. This keeps the current public release useful without publishing full policy text.

## SourceUrl

```json
{
  "id": "url_000001",
  "url": "https://example.com/policy.pdf",
  "domain": "example.com",
  "company": "Example Life",
  "source_file_title": "Example Life",
  "source_document_id": "doc_001",
  "kind": "pdf_terms",
  "visibility": "public_web",
  "should_crawl": true,
  "risk_flags": [],
  "first_seen_at": "2026-06-02T00:00:00+08:00"
}
```

## CrawlStatus

```json
{
  "id": "url_000001",
  "url": "https://example.com/policy.pdf",
  "domain": "example.com",
  "status": "ok",
  "robots_allowed": true,
  "http_status": 200,
  "content_type": "application/pdf",
  "checked_at": "2026-06-04T09:07:54+08:00",
  "error": null
}
```

Status meanings:

- `ok`: the source was reachable and may be used for extraction.
- `robots_blocked`: `robots.txt` did not allow crawling; the URL stays visible as source evidence but is not fetched further.
- `error`: the source timed out, returned an error, or needs manual review.

## PolicyContentExtract

`data/policy-content-extracts.json` stores proof that insurance content was actually parsed from reachable policy sources.

```json
{
  "id": "policy-content-000001",
  "company": "Example Life",
  "product_name": "Example Whole Life Insurance",
  "document_kind": "pdf",
  "policy_url": "https://example.com/policy.pdf",
  "content_type": "application/pdf",
  "status": "extracted",
  "page_count": 24,
  "pages_parsed": 12,
  "text_char_count": 18234,
  "field_hits": [
    {
      "key": "claims",
      "label": "理賠/給付",
      "matched_terms": ["給付", "保險金"]
    }
  ],
  "reader_focus": [
    {
      "key": "coverage",
      "label": "保障項目",
      "reader_question": "這張保單主要賠什麼、保障哪些事故或狀態？",
      "status": "detected",
      "summary": "已命中 5 個重點詞：給付、保險金、住院。",
      "terms": ["給付", "保險金", "住院"],
      "pages": [2, 3]
    }
  ],
  "focus_score": 4,
  "extracted_at": "2026-06-04T09:07:54+08:00"
}
```

The public extract does not include full PDF text. It includes enough derived evidence to confirm that the crawler parsed policy content and found reader-important categories. `reader_focus` powers the public quick-read cards for `保障項目`, `重要定義`, `特殊項目`, and `理賠申請`.

## ConsumerField

Future reviewed facts should follow this shape:

```json
{
  "label": "等待期",
  "value": "30 日",
  "summary": "疾病醫療給付需留意等待期。",
  "source_url": "https://example.com/policy.pdf",
  "source_document": "Official policy PDF",
  "source_clause_or_page": "p. 3",
  "extraction_method": "rule | model | manual",
  "confidence": "low | medium | high",
  "last_checked_at": "2026-06-04T09:07:54+08:00"
}
```

## ReviewedBenefit

`data/tii/reviewed-benefits/*.json` stores source-matched benefit facts that can be shown in `Verified Benefits`. Product versions stay separated by TII `product_id`; same-name products are not merged.

Browser-facing TII benefit summaries must preserve the reviewed evidence chain:

- `review_status`: currently only `verified_reference` may expose benefit numbers.
- `source_document_sha256`: hash of the exact official terms file used for review.
- `schedule_sha256`: hash of the reviewed structured benefit schedule.
- `parser_id`, `source_file`, and `reviewed_at`: parser and review trace fields.

The frontend loads TII benefit numbers only when `review_status` and the source hash are present. Saved collections are rehydrated from the current summary; stale LocalStorage `coverage_entries` are not reused when the exact reviewed source cannot be verified.

```json
{
  "product_id": "202421M31AZI000",
  "selection_type": "account_value",
  "selection_label": "保單帳戶價值",
  "selection_guidance": "請輸入或確認年金給付開始日時的保單帳戶價值。",
  "coverage_entries": [
    {
      "id": "account-value-return-before-annuity-start",
      "name": "返還保單帳戶價值",
      "amount": null,
      "basis": "policy_account_value",
      "calculation_basis": "account_value",
      "amount_role": "payout",
      "limit_scope": "per_policy",
      "source": "terms",
      "source_ref": "條款第十六條"
    }
  ]
}
```

Supported `selection_type` values are `face_amount`, `face_amount_plan`, `account_value`, `paid_premium_factor_plan`, `plan`, `unit`, `multi_unit`, `plan_unit`, `policy_state`, and `fixed`. If a benefit depends on changing policy state, the site prompts for the matching input instead of inventing an amount. Current policy-state inputs include `policy_account_value`, `benefit_valuation_policy_account_value`, `maturity_policy_account_value`, `maturity_interest_amount`, `annuity_payment_amount`, `annuity_payment_year`, `current_policy_amount`, `basic_face_amount`, `current_threshold_face_amount`, `death_benefit_status`, `remaining_funeral_benefit_limit`, `policy_effect_status_at_event`, `unexpired_premium_refund_amount`, `post_event_insurance_cost_refund_amount`, `policy_reserve_value`, `policy_loan_and_interest_amount`, `unpaid_policy_charge_amount`, `remittance_fee_amount`, `previous_policy_reserve_value`, `premium_total_amount`, `single_premium_amount`, `annuity_paid_total_amount`, `successor_discounted_annuity_amount`, `excess_annuity_reserve_return_amount`, `policy_year`, `standard_annual_premium_amount`, `premium_payment_period_years`, `prior_long_term_care_benefit_amount`, `long_term_care_qualification_type`, `adl_impairment_count`, `cdr_score`, `impairment_duration_months`, `long_term_care_permanence_status`, `long_term_care_medical_confirmation_status`, `cognitive_icd_diagnosis_status`, `long_term_care_previous_claim_status`, `premium_payment_period_status`, `paid_premium_total`, `cumulative_paid_target_premium_total`, `target_premium_cumulative_count`, `target_premium_new_count`, `installment_premium_frequency`, `previous_installment_premium_cumulative_count`, `current_installment_premium_cumulative_count`, `previous_installment_premium_average_amount`, `value_addition_qualification_status`, `partial_termination_amount_total`, `specified_percent_or_multiplier`, `remaining_premium_amount`, `hospital_daily_amount`, `reimbursement_limit`, `hospitalization_days`, `intensive_care_days`, `cancer_hospitalization_days`, `cancer_benefit_category`, `prior_cancer_diagnosis_benefit_paid_amount`, `cancer_surgery_count`, `cancer_outpatient_treatment_days`, `cancer_radiation_treatment_days`, `cancer_chemotherapy_treatment_days`, `cancer_hospice_anniversary_count`, `home_care_eligible_days`, `inpatient_medical_expense_days`, `outpatient_visit_count`, `inpatient_medical_expense`, `outpatient_surgery_expense`, `special_procedure_expense`, `surgery_benefit_rate_percent`, `national_health_insurance_payment_status`, `annual_medical_benefit_paid_amount`, `cash_surrender_value`, `installment_periodic_amount`, `unpaid_annuity_balance`, `policy_dividend_amount`, `declared_interest_rate_percent`, `scheduled_interest_rate_percent`, `contract_currency`, and `insured_age_at_event`.

Claim-scenario fields are entry-specific and source-gated. `quantity_state_key` multiplies a verified daily, per-visit, or per-event amount by the matching count; when each `amount_tiers` item includes contiguous `min_quantity` and `max_quantity` boundaries, the model progressively totals each verified quantity bracket. `tier_selection_state_key` instead selects one verified bracket from a policy-state value such as `policy_year`. `expense_state_key` applies the verified reimbursement cap to the matching actual expense; `rate_state_key` lets the user enter an exact source-table percentage such as a surgery grade; `rate_condition_state_key` and `rate_condition_value` apply a source-backed conditional rate to per-unit, tiered, or reimbursement formulas. `cumulative_paid_state_key` either deducts an exact prior paid amount from a direct benefit or, with `aggregate_limit_entry_id`, prevents a reimbursement estimate from exceeding the remaining verified annual or lifetime cap. `exclusion_state_key` and `exclusion_values` return an explicit ineligible result when the selected policy state is excluded by the exact terms. Parsers must emit these fields only when the exact source document supports them.

For a `face_amount_plan` schedule whose terms use a changed or current insurance amount rather than the original basic face amount, set top-level `face_amount_label` to the exact consumer-facing field name, such as `事故時有效保險金額`. The calculator keeps the same numeric input contract while showing the source-accurate label in both the form and formula explanation.

`face_amount_plan` options may contain their own `coverage_entries` when the selected policy type, payment frequency, or guarantee period changes the official formula. For example, `annuity_face_amount_schedule` combines the terms-owned payment-frequency coefficient with a face amount and, for increasing annuities, the user-entered `annuity_payment_year`.

Calculation bases distinguish payout semantics:

- `fixed_amount`, `per_day`, `per_unit`, `per_unit_per_day`, `percentage_of_base`, `table_multiplier`, and `tiered_or_stepped` are terms-owned amounts or formulas.
- `account_value`, `account_value_annuity_factor`, `policy_state_amount`, `sum_policy_state_amounts`, `death_or_funeral_greater_of`, `death_or_funeral_face_amount`, `target_premium_count_value_addition`, `installment_premium_value_addition`, `net_amount_at_risk_plus_policy_account_value`, `paid_premium_factor_account_value_formula`, `greater_of`, `waiver`, and policy-recorded caps require policy state or insurer-calculated values.
- `policy_state_keys` is an ordered, terms-reviewed list of the exact amount fields used by `greater_of`, `death_or_funeral_greater_of`, `policy_state_amount`, or `sum_policy_state_amounts`. It replaces keyword guessing for version-specific formulas and drives both the user inputs and calculation.
- `benefit_valuation_policy_account_value` must match the valuation timing stated in the exact product-version terms. A current statement value may be shown only as an estimate and must not be presented as the final claim amount.
- `death_or_funeral_greater_of` first calculates the source-backed gross formula. When `death_benefit_status=funeral_limited`, it caps only the non-investment protection portion by `remaining_funeral_benefit_limit`, then adds the policy-account-value return.
- `death_or_funeral_face_amount` uses the selected face amount for ordinary death. When `death_benefit_status=funeral_limited`, it returns the lower of the selected face amount and `remaining_funeral_benefit_limit`.
- `target_premium_count_value_addition` sums the source-backed rate for each newly added target-premium payment count and multiplies it by the cumulative paid target-premium average. It requires the cumulative count, new count, cumulative paid total, and current qualification status. When terms credit the result into the policy account, the result is informational and must not be added again to death, disability, or maturity totals after the account value already includes it. If the terms do not specify fractional-currency handling, the site rounds the estimate to a whole currency unit and labels the insurer amount as authoritative.
- `installment_premium_value_addition` uses the reviewed payment frequency, previous and current cumulative installment-premium counts, previous average installment premium, and qualification status. Annual formulas preserve the 61- and 121-count threshold segments; monthly formulas use the current count band. A credited amount enters the policy account and must not be added a second time to a later death, disability, or maturity result.
- Versioned investment-life formulas deduct only source-backed offsets. `policy_effect_status_at_event` must confirm that the contract was effective; `policy_loan_and_interest_amount`, `unpaid_policy_charge_amount`, and, for foreign-currency products, `remittance_fee_amount` are entered from the latest policy or insurer settlement. If offsets exceed the calculated gross benefit, the site requests insurer confirmation instead of returning a negative payout.
- `currency_state_key=contract_currency` keeps foreign-currency face amounts, account values, and results in the contract currency instead of relabelling them as TWD.
- `minor_account_value_return_age` switches only the exact coverage entry whose terms prescribe an under-age account-value return; it must not be inferred from unrelated age text.
- `aggregate_cap` is a cumulative limit, not an extra payout.
- `waiver` / `premium_waiver` is a premium obligation relief, not cash received.
- `result_kind` distinguishes `cash_payout`, `non_cash_effect`, `payment_method`, and reference-only information. A payment method must not be summed as an additional benefit.
- `amount_stage` distinguishes a source-backed gross contract benefit from a non-cash estimate or an insurer-quoted amount. Gross contract benefits may still be reduced by unpaid premiums, policy loans, interest, statutory funeral limits, or other terms-owned settlements.
- `conditional_event_key` creates an explicit event variant for a `conditional_additive` entry. For example, general death excludes an accidental-death addition, while the accidental-death scenario combines the general death amount and the source-backed accidental addition.
- A long-term-care eligibility rule requires the exact ADL or cognitive route, duration or permanence, medical confirmation, prior-claim status, and the ICD diagnosis confirmation for the cognitive route. These inputs determine eligibility; they are not user-editable coverage terms.
- When a periodic installment amount depends on the insurer's rate announced at the payment start date, the calculator accepts `installment_periodic_amount` from the insurer's quote. It must not infer the amount from surrender value, reserve, or another generic policy field.

`structure_status` is derived for user-facing cards and audit reports:

- `calculated`: coverage entries contain terms-owned amounts or formulas that can be shown or calculated with current inputs.
- `needs_user_input`: terms-owned coverage entries exist, but the user must enter 保額、單位、計畫別或保單現況 before the amount can be calculated.
- `pending_structure`: official terms or document summaries exist, but the benefit table has not yet been converted into structured coverage entries. This does not mean the policy has no benefits.
- `source_pending`: only the product index/list is available; source terms still need to be fetched or parsed.
- `confirmed_no_amount`: manual/reviewed marker for terms that do not provide a fixed or deterministic amount.

The UI must not show internal product-id warnings as a consumer risk message. Product identity is still preserved internally by `product_id` plus version fields, and same-name products must remain separate when the official IDs or version evidence differ.

## TIIManualMatrixBatch

The Insurance Institute discontinued-policy query page requires captcha completion. The public site therefore stores manual click-through batches instead of bypassing the captcha.

```json
{
  "id": "tii-life-001",
  "group": "life_personal",
  "company": "Example Life",
  "insurance_category": "健康險",
  "source_url": "https://insprod.tii.org.tw/Query.aspx",
  "status": "manual_captcha_required"
}
```

## TIIImportedResults

`data/tii-policy-results.json` is the execution/import status for captcha-protected TII batches. A planned batch is not counted as complete until a human finishes the captcha query and the runner imports complete official result-page coverage. Public cards are deduplicated only by TII `productId`, because the official result rows can repeat the same product ID across pages. They are not deduplicated by product name: the same company can reuse a name across different years, sale periods, or product IDs, and those records may have different terms.

```json
{
  "record_count": 46013,
  "detail_expected_count": 46013,
  "detail_saved_count": 45846,
  "detail_missing_count": 167,
  "detail_coverage_rate": 0.9964,
  "indexed_batch_count": 31,
  "indexed_batches": ["tii-property-001", "tii-property-002", "...", "tii-property-031"],
  "completed_batch_count": 31,
  "completed_batches": ["tii-property-001", "tii-property-002", "...", "tii-property-031"],
  "partial_batch_count": 0,
  "pending_manual_batch_count": 275,
  "batch_summaries": [
    {
      "batch_id": "tii-property-001",
      "status": "complete",
      "expected_total_count": 952,
      "expected_total_pages": 96,
      "official_row_count": 952,
      "saved_page_count": 96,
      "imported_record_count": 952,
      "unique_product_id_count": 952,
      "expected_unique_product_id_count": 952,
      "duplicate_product_id_count": 0,
      "detail_expected_count": 952,
      "detail_saved_count": 952,
      "detail_missing_count": 0,
      "detail_coverage_rate": 1.0,
      "detail_status": "complete",
      "requires_fresh_captcha_session": false,
      "requires_detail_backfill_session": false
    },
    {
      "batch_id": "tii-property-002",
      "status": "complete",
      "expected_total_count": 618,
      "expected_total_pages": 62,
      "official_row_count": 618,
      "saved_page_count": 62,
      "imported_record_count": 618,
      "unique_product_id_count": 618,
      "expected_unique_product_id_count": 618,
      "duplicate_product_id_count": 0,
      "detail_expected_count": 618,
      "detail_saved_count": 617,
      "detail_missing_count": 1,
      "detail_coverage_rate": 0.9984,
      "detail_status": "partial_detail",
      "requires_fresh_captcha_session": false,
      "requires_detail_backfill_session": true
    },
    {
      "batch_id": "tii-property-003",
      "status": "complete",
      "expected_total_count": 525,
      "expected_total_pages": 53,
      "official_row_count": 525,
      "saved_page_count": 53,
      "imported_record_count": 525,
      "unique_product_id_count": 525,
      "expected_unique_product_id_count": 525,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 525,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-004",
      "status": "complete",
      "expected_total_count": 2667,
      "expected_total_pages": 267,
      "official_row_count": 2667,
      "saved_page_count": 267,
      "imported_record_count": 2091,
      "unique_product_id_count": 2091,
      "expected_unique_product_id_count": 2091,
      "duplicate_product_id_count": 576,
      "detail_saved_count": 2087,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-005",
      "status": "complete",
      "expected_total_count": 1391,
      "expected_total_pages": 140,
      "official_row_count": 1391,
      "saved_page_count": 140,
      "imported_record_count": 1391,
      "unique_product_id_count": 1391,
      "expected_unique_product_id_count": 1391,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1391,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-006",
      "status": "complete",
      "expected_total_count": 1190,
      "expected_total_pages": 119,
      "official_row_count": 1190,
      "saved_page_count": 119,
      "imported_record_count": 1190,
      "unique_product_id_count": 1190,
      "expected_unique_product_id_count": 1190,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1186,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-007",
      "status": "complete",
      "expected_total_count": 683,
      "expected_total_pages": 69,
      "official_row_count": 683,
      "saved_page_count": 69,
      "imported_record_count": 683,
      "unique_product_id_count": 683,
      "expected_unique_product_id_count": 683,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 683,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-008",
      "status": "complete",
      "expected_total_count": 2525,
      "expected_total_pages": 253,
      "official_row_count": 2525,
      "saved_page_count": 253,
      "imported_record_count": 2165,
      "unique_product_id_count": 2165,
      "expected_unique_product_id_count": 2165,
      "duplicate_product_id_count": 360,
      "detail_saved_count": 2161,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-009",
      "status": "complete",
      "expected_total_count": 73,
      "expected_total_pages": 8,
      "official_row_count": 73,
      "saved_page_count": 8,
      "imported_record_count": 73,
      "unique_product_id_count": 73,
      "expected_unique_product_id_count": 73,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 73,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-010",
      "status": "complete",
      "expected_total_count": 30,
      "expected_total_pages": 3,
      "official_row_count": 30,
      "saved_page_count": 3,
      "imported_record_count": 30,
      "unique_product_id_count": 30,
      "expected_unique_product_id_count": 30,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 30,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-011",
      "status": "complete",
      "expected_total_count": 7,
      "expected_total_pages": 1,
      "official_row_count": 7,
      "saved_page_count": 1,
      "imported_record_count": 7,
      "unique_product_id_count": 7,
      "expected_unique_product_id_count": 7,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 7,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-012",
      "status": "complete",
      "expected_total_count": 106,
      "expected_total_pages": 11,
      "official_row_count": 106,
      "saved_page_count": 11,
      "imported_record_count": 106,
      "unique_product_id_count": 106,
      "expected_unique_product_id_count": 106,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 106,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-013",
      "status": "complete",
      "expected_total_count": 1599,
      "expected_total_pages": 160,
      "official_row_count": 1599,
      "saved_page_count": 160,
      "imported_record_count": 1599,
      "unique_product_id_count": 1599,
      "expected_unique_product_id_count": 1599,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1599,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-014",
      "status": "complete",
      "expected_total_count": 943,
      "expected_total_pages": 95,
      "official_row_count": 943,
      "saved_page_count": 95,
      "imported_record_count": 943,
      "unique_product_id_count": 943,
      "expected_unique_product_id_count": 943,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 940,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-015",
      "status": "complete",
      "expected_total_count": 3112,
      "expected_total_pages": 312,
      "official_row_count": 3112,
      "saved_page_count": 312,
      "imported_record_count": 3112,
      "unique_product_id_count": 3112,
      "expected_unique_product_id_count": 3112,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 3103,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-016",
      "status": "complete",
      "expected_total_count": 10537,
      "expected_total_pages": 1054,
      "official_row_count": 10537,
      "saved_page_count": 1054,
      "imported_record_count": 8056,
      "unique_product_id_count": 8056,
      "expected_unique_product_id_count": 8056,
      "duplicate_product_id_count": 2481,
      "detail_saved_count": 8011,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-017",
      "status": "complete",
      "expected_total_count": 1233,
      "expected_total_pages": 124,
      "official_row_count": 1233,
      "saved_page_count": 124,
      "imported_record_count": 1233,
      "unique_product_id_count": 1233,
      "expected_unique_product_id_count": 1233,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1233,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-018",
      "status": "complete",
      "expected_total_count": 940,
      "expected_total_pages": 94,
      "official_row_count": 940,
      "saved_page_count": 94,
      "imported_record_count": 940,
      "unique_product_id_count": 940,
      "expected_unique_product_id_count": 940,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 938,
      "requires_fresh_captcha_session": false
    },
    {
      "batch_id": "tii-property-019",
      "status": "complete",
      "expected_total_count": 1576,
      "expected_total_pages": 158,
      "official_row_count": 1576,
      "saved_page_count": 158,
      "imported_record_count": 1576,
      "unique_product_id_count": 1576,
      "expected_unique_product_id_count": 1576,
      "duplicate_product_id_count": 0,
      "detail_saved_count": 1569,
      "requires_fresh_captcha_session": false
    }
  ],
  "records": [
    {
      "source_batch_id": "tii-property-001",
      "company": "臺灣產物保險股份有限公司",
      "insurance_category": "汽車保險",
      "product_id": "101111114057010000",
      "record_identity_key": "tii-product-id:101111114057010000",
      "identity_basis": "tii_product_id",
      "detail_url": "https://insprod.tii.org.tw/DetailList.aspx?productId=101111114057010000",
      "detail_saved": true,
      "detail_source_file": "work\\tii-details\\tii-property-001\\101111114057010000.html",
      "product_name": "臺灣產物強制汽車責任保險",
      "sale_status": "已停售",
      "sale_date": "086/12/05",
      "discontinued_date": "094/11/06",
      "edition_label": "銷售日 086/12/05｜停售日 094/11/06｜productId 101111114057010000",
      "same_name_product_id_count": 1,
      "same_name_version_note": ""
    }
  ],
  "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha."
}
```

Completion rule:

- `indexed_batch_count`: at least one valid product row was imported for that batch.
- `completed_batch_count`: either `unique_product_id_count == expected_total_count == imported_record_count`, or `official_row_count == expected_total_count` with full saved-page coverage and a positive `duplicate_product_id_count`.
- `partial_index`: the batch has usable rows, but the saved pages do not yet match the official total count.
- `record_count`: public product cards after deduplicating repeated official `productId` rows.
- `official_row_count`: row coverage reported by saved TII result pages before deduplication.
- `detail_expected_count`: expected detail-page count after productId deduplication.
- `detail_saved_count`: official detail pages saved locally during human-captcha sessions.
- `detail_missing_count`: detail pages that still need a later backfill session. A batch can have complete official result-page coverage while `detail_status` is `partial_detail`.
- `requires_detail_backfill_session`: true when the batch has preserved result rows but some official detail pages were unavailable or session-invalid during the run.
- `record_identity_key`: stable public identity. Prefer `tii-product-id:<productId>`; use the company/category/name/date fallback only when an official product ID is absent.
- `edition_label`: user-facing version cue combining sale date, discontinued date, and `productId`.
- `same_name_product_id_count` / `same_name_version_note`: marker for same-company same-name records that represent different product IDs. These records must remain separate cards.

## Coverage Calculation Schema

Every official TII category can use the same search, detail, collection, edit, and coverage-group flow. Amounts are shown only when reviewed terms provide enough structure to calculate or label them safely.

```json
{
  "selection_type": "plan_unit",
  "selection_source": "terms",
  "plan_options": [
    {
      "value": "B",
      "label": "計畫 B",
      "coverage_entries": [
        {
          "name": "住院醫療保險金",
          "amount": 1000,
          "calculation_basis": "per_unit_per_day",
          "amount_role": "payout",
          "limit_scope": "per_day",
          "aggregation_rule": "separate",
          "source": "terms",
          "source_ref": "給付附表"
        }
      ]
    }
  ]
}
```

`selection_type` controls the only inputs a user may edit:

- `face_amount`: positive-integer `face_amount` only.
- `plan`: one reviewed `plan_name`; no quantity field.
- `unit`: positive-integer `unit_count` only.
- `plan_unit`: both a reviewed plan and a positive-integer unit count.
- `policy_state`: no plan/unit/face-amount field is shown; the editable fields come only from reviewed coverage entries, such as current policy amount or policy reserve value.
- `fixed`: terms define the amount and no user input is needed.
- `unknown`: terms have not established the amount input; the product remains usable but displays `金額尚待整理`.

Any mode other than `unknown` must be backed by `selection_source: terms` or a reviewed plan option table. Existing user values never create a mode by themselves.

Each `coverage_entry` is terms-owned and cannot be edited by the user. Supported `calculation_basis` values include `fixed_amount`, `percentage_of_base`, `plan_schedule_lookup`, `per_unit`, `per_unit_per_day`, `per_day`, `reimbursement_with_cap`, `percentage_of_actual_expense_with_cap`, `table_multiplier`, `tiered_or_stepped`, `additional_benefit`, `account_value`, `account_value_annuity_factor`, `annuity_face_amount_schedule`, `single_premium_minus_paid_annuity_total`, `reserve_minus_policy_loan_and_interest`, `policy_state_amount`, `sum_policy_state_amounts`, `death_or_funeral_greater_of`, `death_or_funeral_face_amount`, `target_premium_count_value_addition`, `installment_premium_value_addition`, `maturity_policy_account_value`, `policy_value_component`, `policy_value_plus_general_insurance_amount`, `policy_value_plus_general_and_accidental_insurance_amount`, `net_amount_at_risk_plus_policy_account_value`, `paid_premium_factor_account_value_formula`, `policy_year_tiered_premium_or_face_amount`, `policy_year_greater_of_face_reserve_premium_with_offset`, `death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset`, `maturity_greater_of_face_and_premium_with_offset`, `aggregate_cap`, `greater_of`, `waiver`, and `unknown`. `amount_role`, `result_kind`, `limit_scope`, and `aggregation_rule` preserve whether a result is a cash payout, non-cash effect, payment method, base, cap, or reference and whether benefits may be combined.

When a terms formula depends on a claimant state, `eligibility_rule` is executable rather than display-only prose. A long-term-care rule records the ADL/CDR route, threshold, minimum duration, permanent-condition override, and optional payment-period requirement. Missing inputs return `needs_policy_state`; a complete state that does not meet the terms returns `not_eligible` with no payout value. This must not be presented as proof that the policy has no coverage.

For long-term-care whole-life formulas, the policyholder supplies the policy year, standard annual premium, premium payment period, reserve value, and any prior long-term-care payout. The model derives the terms-defined annual premium total as `standard annual premium × min(policy year, payment period)` and applies the exact version's year cutoff, premium multiplier, face-amount rate, prior-benefit offset, and funeral-benefit cap. A premium waiver is a `non_cash_effect`; installment conversion remains a `payment_method` until the insurer's declared conversion rate or quoted periodic amount is available.

For mutually exclusive claim events, `benefit_group_id`, `event_key`, and `event_label` identify each primary `choose_one` payout. A `conditional_additive` entry may declare `applies_to_entry_ids`; the calculation model then produces one event-specific total by adding that entry only to the selected primary event. This prevents mutually exclusive death, disability, and disease amounts from being summed together or a refund from being counted more than once.

For a version-specific policy-state formula, the entry stores only exact source-backed fields:

```json
{
  "name": "身故保險金或喪葬費用保險金",
  "basis": "policy_recorded_limit",
  "calculation_basis": "greater_of",
  "policy_state_keys": [
    "basic_face_amount",
    "current_threshold_face_amount",
    "policy_account_value"
  ],
  "minor_account_value_return_age": 15,
  "source": "terms",
  "source_ref": "身故保險金或喪葬費用保險金的給付與保單帳戶價值之返還"
}
```

The user enters the current values shown on the policy, endorsement, annual statement, or insurer quotation. A threshold amount that was recalculated at an earlier premium or withdrawal event must be entered as the current recorded threshold; the site must not reconstruct it from the user's current age and account value.

For threshold-face-amount products, `version_characteristics.threshold_multiplier_age_bands` preserves the exact age-band wording and multiplier percentages found in that `product_id`'s terms. It is version evidence only. The calculator must still use the user-entered current threshold amount because later premium payments or partial withdrawals may have recalculated it under an earlier age band.

`limit_scope` includes `per_surgery` for surgery schedules and `cross_policy` when a statutory or contractual cap aggregates policies across insurers. Percentage fields may exceed 100 when a reviewed terms table defines a multiplier, such as a surgery schedule ranging from 10% to 500%; the validator permits reviewed values up to 1000% and the UI keeps the full range instead of clipping it to 100%.

For `reimbursement_with_cap`, a legacy `basis` of `per_unit` or `daily_per_unit` means the reviewed table amount is a per-unit limit. The displayed policy limit must multiply that amount by the user's positive-integer `unit_count`; without a unit count, the UI must request it instead of presenting the per-unit amount as the whole-policy cap.

For `percentage_of_actual_expense_with_cap`, the terms define a reimbursement percentage, but the real payout still depends on the user's actual expense and the policy-recorded limit. When `basis` is `policy_recorded_limit`, the user's selected/input limit is treated as the displayed cap; the terms-owned `rate_percent` explains how non-standard reimbursement is calculated.

For a verified benefit whose per-unit amount changes by policy year or another terms-defined tier, `amount_tiers` stores each reviewed label and amount as structured data. The UI may calculate every displayed tier from the user's unit count, but it must not collapse the tiers into one estimated payout or ask the user to edit the terms-owned tier labels.

```json
{
  "name": "罹患癌症保險金",
  "basis": "per_unit",
  "calculation_basis": "tiered_or_stepped",
  "amount_tiers": [
    { "label": "第 1 至 20 保單年度", "amount": 50000 },
    { "label": "第 21 保單年度起", "amount": 75000 }
  ]
}
```

Safety rules:

- Do not infer an input mode or amount from product-name keywords.
- Do not convert an unsupported calculation basis into a fixed payout.
- Do not total entries with different bases, scopes, or aggregation rules by default.
- Show the selected plan, unit count, or face amount together with the derived benefit rows so the user can verify the basis.
- Preserve official product identity and version separately from the coverage calculation schema.
