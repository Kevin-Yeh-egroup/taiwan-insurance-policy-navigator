#!/usr/bin/env python3
"""Focused regression tests for the life calculation-readiness audit."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import audit_tii_life_calculation_readiness as audit


def write_proposal(
    path: Path,
    *,
    generated_at: str,
    extractor_version: str,
    schedule_sha256: str,
) -> None:
    payload = {
        "batch_id": "tii-life-999",
        "generated_at": generated_at,
        "extractor_version": extractor_version,
        "proposals": [
            {
                "product_id": "PRODUCT-1",
                "status": "proposed",
                "candidate_count": 1,
                "candidates": [
                    {
                        "parser_id": "parser-1",
                        "source_file": "terms/PRODUCT-1.pdf",
                        "source_document_sha256": "source-sha",
                        "schedule_sha256": schedule_sha256,
                    }
                ],
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_latest_exact_source_proposal_wins() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        proposals_dir = Path(temp_dir)
        write_proposal(
            proposals_dir / "tii-life-999-new.json",
            generated_at="2026-07-29T02:00:00+08:00",
            extractor_version="tii-plan-benefits-v207",
            schedule_sha256="new-schedule",
        )
        write_proposal(
            proposals_dir / "tii-life-999.json",
            generated_at="2026-07-28T02:00:00+08:00",
            extractor_version="tii-plan-benefits-v197",
            schedule_sha256="old-schedule",
        )

        proposal = audit.load_proposal_index(proposals_dir)[
            ("tii-life-999", "PRODUCT-1")
        ]
        assert proposal["extractor_version"] == "tii-plan-benefits-v207"
        assert proposal["candidates"][0]["schedule_sha256"] == "new-schedule"


def test_upgrade_requires_same_exact_source_and_changed_schedule() -> None:
    reviewed = {
        "parser_id": "parser-1",
        "source_file": "terms/PRODUCT-1.pdf",
        "source_document_sha256": "source-sha",
        "schedule_sha256": "old-schedule",
    }
    proposal = {
        "status": "proposed",
        "candidates": [
            {
                "parser_id": "parser-1",
                "source_file": "terms/PRODUCT-1.pdf",
                "source_document_sha256": "source-sha",
                "schedule_sha256": "new-schedule",
            }
        ],
    }
    assert audit.proposal_supersedes_reviewed(reviewed, proposal)

    proposal["candidates"][0]["parser_id"] = "parser-2"
    assert audit.proposal_supersedes_reviewed(reviewed, proposal)

    proposal["candidates"][0]["schedule_sha256"] = "old-schedule"
    assert not audit.proposal_supersedes_reviewed(reviewed, proposal)

    proposal["candidates"][0]["schedule_sha256"] = "new-schedule"
    proposal["candidates"][0]["source_document_sha256"] = "other-source"
    assert not audit.proposal_supersedes_reviewed(reviewed, proposal)


def test_face_amount_plan_inputs_and_policy_state_formula() -> None:
    record = {
        "selection_type": "face_amount_plan",
        "version_characteristics": {
            "required_policy_inputs": [
                "policy_account_value",
                "insured_age_at_event",
            ]
        },
    }
    entries = [
        {
            "calculation_basis": "net_amount_at_risk_plus_policy_account_value",
            "basis": "policy_recorded_limit",
        }
    ]
    inputs = audit.required_inputs_from_reviewed(record, entries)
    assert inputs == {
        "basic_face_amount",
        "plan",
        "policy_account_value",
        "insured_age_at_event",
        "policy_recorded_limit",
    }
    assert audit.entry_bucket(entries[0]) == "requires_policy_state"


def test_source_gap_overrides_keyword_summary() -> None:
    key = ("tii-life-053", "PRODUCT-GAP")
    classified = audit.classify_unreviewed(
        key,
        {
            key: {
                "coverage_terms": ["保險金"],
                "summary_path": "summary.json",
            }
        },
        {},
        {},
        {
            key: {
                "source_pending_reason": "image_only_policy_terms",
                "next_action": "Run verified OCR.",
                "processing_gate": (
                    "needs_exact_readable_source_or_verified_ocr"
                ),
                "source_gap_path": "source-gaps.json",
            }
        },
    )
    assert classified["calculation_status"] == "source_pending"
    assert classified["source_pending_reason"] == (
        "image_only_policy_terms"
    )
    assert classified["coverage_terms"] == ["保險金"]


def test_claim_scenario_readiness_distinguishes_rates_from_totals() -> None:
    fixed = audit.classify_reviewed(
        {
            "selection_type": "plan",
            "coverage_entries": [
                {
                    "name": "診斷保險金",
                    "calculation_basis": "fixed_amount",
                    "amount": 100_000,
                }
            ],
        }
    )
    assert fixed["coverage_schedule_ready"]
    assert fixed["claim_scenario_ready"]

    daily = audit.classify_reviewed(
        {
            "selection_type": "plan",
            "coverage_entries": [
                {
                    "name": "住院日額",
                    "calculation_basis": "per_day",
                    "amount": 1_000,
                }
            ],
        }
    )
    assert daily["coverage_schedule_ready"]
    assert not daily["claim_scenario_ready"]
    assert daily["claim_scenario_gap_reasons"] == [
        "days_not_applied_to_claim_total"
    ]

    reimbursement = audit.classify_reviewed(
        {
            "selection_type": "plan",
            "coverage_entries": [
                {
                    "name": "住院醫療費用限額",
                    "calculation_basis": "reimbursement_with_cap",
                    "amount_role": "limit",
                    "amount": 50_000,
                }
            ],
        }
    )
    assert reimbursement["coverage_schedule_ready"]
    assert not reimbursement["claim_scenario_ready"]
    assert set(reimbursement["claim_scenario_gap_reasons"]) == {
        "actual_expense_not_applied_to_claim_total",
        "no_cash_payout_formula",
    }

    typed = audit.classify_reviewed(
        {
            "selection_type": "plan",
            "coverage_entries": [
                {
                    "name": "住院日額",
                    "calculation_basis": "per_day",
                    "amount": 1_000,
                    "quantity_state_key": "hospitalization_days",
                },
                {
                    "name": "住院醫療費用保險金",
                    "basis": "per_event",
                    "calculation_basis": "reimbursement_with_cap",
                    "amount_role": "limit",
                    "result_kind": "cash_payout",
                    "amount": 50_000,
                    "expense_state_key": "inpatient_medical_expense",
                },
                {
                    "name": "年度總限額",
                    "basis": "annual_limit",
                    "calculation_basis": "reimbursement_with_cap",
                    "amount_role": "limit",
                    "aggregation_rule": "cumulative_cap",
                    "amount": 500_000,
                },
            ],
        }
    )
    assert typed["coverage_schedule_ready"]
    assert typed["claim_scenario_ready"]
    assert typed["claim_scenario_gap_reasons"] == []


def test_claim_scenario_accepts_tiered_days_and_user_selected_rate() -> None:
    typed = audit.classify_reviewed(
        {
            "selection_type": "unit",
            "coverage_entries": [
                {
                    "name": "住院醫療保險金",
                    "calculation_basis": "tiered_or_stepped",
                    "quantity_state_key": "hospitalization_days",
                    "amount_tiers": [
                        {
                            "min_quantity": 1,
                            "max_quantity": 30,
                            "amount": 1_000,
                        },
                        {
                            "min_quantity": 31,
                            "max_quantity": 90,
                            "amount": 1_500,
                        },
                        {
                            "min_quantity": 91,
                            "max_quantity": None,
                            "amount": 2_000,
                        },
                    ],
                },
                {
                    "name": "住院手術保險金",
                    "calculation_basis": "percentage_of_base",
                    "basis": "per_event",
                    "base_amount": 1_000,
                    "rate_state_key": "surgery_benefit_rate_percent",
                    "result_kind": "cash_payout",
                },
            ],
        }
    )
    assert typed["coverage_schedule_ready"]
    assert typed["claim_scenario_ready"]
    assert typed["claim_scenario_gap_reasons"] == []
    assert typed["required_user_inputs"] == [
        "base_amount",
        "hospitalization_days",
        "surgery_benefit_rate_percent",
        "units",
    ]
    assert typed["entry_buckets"] == {"terms_formula": 2}


def test_claim_scenario_accepts_cancer_tier_condition_and_prior_paid() -> None:
    typed = audit.classify_reviewed(
        {
            "selection_type": "unit",
            "coverage_entries": [
                {
                    "name": "罹患癌症保險金",
                    "calculation_basis": "tiered_or_stepped",
                    "basis": "per_unit",
                    "amount": 50_000,
                    "amount_tiers": [
                        {
                            "label": "第 1 至 20 保單年度",
                            "amount": 50_000,
                            "min_quantity": 1,
                            "max_quantity": 20,
                        },
                        {
                            "label": "第 21 保單年度起",
                            "amount": 75_000,
                            "min_quantity": 21,
                        },
                    ],
                    "tier_selection_state_key": "policy_year",
                    "rate_condition_state_key": "cancer_benefit_category",
                    "rate_condition_value": "reduced_benefit_cancer",
                    "rate_percent": 15,
                    "cumulative_paid_state_key":
                        "prior_cancer_diagnosis_benefit_paid_amount",
                },
                {
                    "name": "癌症安寧照護保險金",
                    "calculation_basis": "per_unit",
                    "basis": "per_unit",
                    "amount": 20_000,
                    "quantity_state_key":
                        "cancer_hospice_anniversary_count",
                    "exclusion_state_key": "cancer_benefit_category",
                    "exclusion_values": ["reduced_benefit_cancer"],
                },
            ],
        }
    )
    assert typed["coverage_schedule_ready"]
    assert typed["claim_scenario_ready"]
    assert typed["claim_scenario_gap_reasons"] == []
    assert typed["required_user_inputs"] == [
        "cancer_benefit_category",
        "cancer_hospice_anniversary_count",
        "policy_year",
        "prior_cancer_diagnosis_benefit_paid_amount",
        "units",
    ]


if __name__ == "__main__":
    test_latest_exact_source_proposal_wins()
    test_upgrade_requires_same_exact_source_and_changed_schedule()
    test_face_amount_plan_inputs_and_policy_state_formula()
    test_source_gap_overrides_keyword_summary()
    test_claim_scenario_readiness_distinguishes_rates_from_totals()
    test_claim_scenario_accepts_tiered_days_and_user_selected_rate()
    test_claim_scenario_accepts_cancer_tier_condition_and_prior_paid()
    print("TII life calculation-readiness tests passed.")
