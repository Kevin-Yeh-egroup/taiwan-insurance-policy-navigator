#!/usr/bin/env python3
"""Verify the exact-source Fubon NHSD fixed-benefit inpatient family."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    FUBON_NHSD_FIXED_INPATIENT_PRODUCT_VERSIONS,
    FUBON_NHSD_SURGERY_GRADE_AMOUNTS,
    complete_strict_source_document,
    parse_fubon_nhsd_fixed_inpatient_surgery_unit,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options  # noqa: E402


documents = json.loads(
    (
        ROOT
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    ).read_text(encoding="utf-8")
)["documents"]

parsed: dict[str, dict] = {}
for product_id, version in FUBON_NHSD_FIXED_INPATIENT_PRODUCT_VERSIONS.items():
    file_name = f"{product_id}-A.pdf"
    document = {
        **next(
            item
            for item in documents
            if item.get("product_id") == product_id
            and item.get("file_name") == file_name
        ),
        "batch_id": "tii-life-050",
    }
    document = complete_strict_source_document(
        document,
        ROOT
        / "work"
        / "tii-documents"
        / "tii-life-050"
        / product_id
        / file_name,
    )
    assert document["page_count"] == version["page_count"], product_id
    schedule = parse_fubon_nhsd_fixed_inpatient_surgery_unit(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == "fubon-nhsd-fixed-inpatient-surgery-unit-v1"
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"Fubon NHSD {product_id}")
    parsed[product_id] = schedule

assert EXTRACTOR_VERSION == "tii-plan-benefits-v217"
assert set(parsed) == set(FUBON_NHSD_FIXED_INPATIENT_PRODUCT_VERSIONS)

for product_id, schedule in parsed.items():
    version = FUBON_NHSD_FIXED_INPATIENT_PRODUCT_VERSIONS[product_id]
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"
    assert schedule["selection_source"] == "terms"
    assert "單位數只換算手術給付" in schedule["selection_guidance"]

    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == version["terms_revision"]
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["hospital_daily_annual_days_limit"] == 365
    assert characteristics["icu_or_burn_daily_multiplier"] == 1.25
    assert characteristics["icu_or_burn_annual_days_limit"] == 365
    assert characteristics["icu_and_burn_same_day_choose_one"] is True
    assert characteristics["surgery_grade_count"] == 8
    assert characteristics["surgery_total_cap_daily_multiplier"] == 75
    assert characteristics["home_recovery_min_hospital_days"] == 7
    assert characteristics["home_recovery_days_limit"] == 90
    assert characteristics["long_hospital_min_days"] == 31
    assert characteristics["long_hospital_days_limit"] == 150
    assert characteristics["same_hospital_readmission_days"] == 14
    assert (
        characteristics["post_expiry_readmission_excluded"]
        == version["post_expiry_readmission_excluded"]
    )
    assert characteristics["unlisted_surgery_requires_agreement"] is True

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == 13
    assert entries["hospital-daily-benefit"]["basis"] == "hospital_daily_amount"
    assert entries["hospital-daily-benefit"]["multiplier"] == 1
    assert (
        entries["icu-or-burn-center-daily-benefit"]["multiplier"]
        == 1.25
    )
    assert (
        entries["icu-or-burn-center-daily-benefit"]["aggregation_rule"]
        == "choose_one"
    )
    assert entries["inpatient-surgery-aggregate-cap"]["multiplier"] == 75
    assert (
        entries["inpatient-surgery-aggregate-cap"]["amount_role"]
        == "limit"
    )
    assert entries["home-recovery-daily-benefit"]["multiplier"] == 0.25
    assert entries["long-hospital-daily-subsidy"]["multiplier"] == 0.25
    assert [
        entries[f"inpatient-surgery-grade-{grade}"]["amount"]
        for grade in range(1, 9)
    ] == list(FUBON_NHSD_SURGERY_GRADE_AMOUNTS)

first_id = next(iter(FUBON_NHSD_FIXED_INPATIENT_PRODUCT_VERSIONS))
first = next(
    item
    for item in documents
    if item.get("product_id") == first_id
    and item.get("file_name") == f"{first_id}-A.pdf"
)
assert (
    parse_fubon_nhsd_fixed_inpatient_surgery_unit(
        {**first, "batch_id": "tii-life-049"}
    )
    is None
)
assert (
    parse_fubon_nhsd_fixed_inpatient_surgery_unit(
        {
            **first,
            "batch_id": "tii-life-050",
            "file_name": f"{first_id}-F.pdf",
        }
    )
    is None
)

print(
    json.dumps(
        {
            "status": "ok",
            "extractor_version": EXTRACTOR_VERSION,
            "verified_product_count": len(parsed),
            "coverage_entries_per_product": 13,
            "surgery_grade_count": len(
                FUBON_NHSD_SURGERY_GRADE_AMOUNTS
            ),
        },
        ensure_ascii=False,
        indent=2,
    )
)
