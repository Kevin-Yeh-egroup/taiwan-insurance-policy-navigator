#!/usr/bin/env python3
"""Verify the exact-source Songying immediate-annuity parser family."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    KGI_CHINA_SONGYING_IMMEDIATE_ANNUITY_PRODUCT_IDS,
    parse_kgi_china_songying_immediate_annuity_face_amount,
)


payload = json.loads(
    (
        ROOT
        / "work"
        / "tii-document-text"
        / "tii-life-028-text.json"
    ).read_text(encoding="utf-8")
)
parsed: dict[str, dict] = {}
for document in payload["documents"]:
    product_id = str(document.get("product_id") or "")
    if (
        product_id not in KGI_CHINA_SONGYING_IMMEDIATE_ANNUITY_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
    ):
        continue
    schedule = parse_kgi_china_songying_immediate_annuity_face_amount(
        {**document, "batch_id": "tii-life-028"}
    )
    assert schedule is not None, product_id
    assert product_id not in parsed, product_id
    parsed[product_id] = schedule

assert EXTRACTOR_VERSION == "tii-plan-benefits-v217"
assert set(parsed) == KGI_CHINA_SONGYING_IMMEDIATE_ANNUITY_PRODUCT_IDS

expected_rates = {
    "annual": 100.0,
    "semiannual": 49.5562,
    "quarterly": 24.6686,
    "monthly": 8.1987,
}
for product_id, schedule in parsed.items():
    assert schedule["selection_type"] == "face_amount_plan", product_id
    assert schedule["input_mode"] == "face_amount_plan", product_id
    assert schedule["selection_source"] == "terms", product_id
    assert schedule["face_amount_label"] == "年金保險投保金額", product_id
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "kgi-china-songying-immediate-annuity-face-amount"
    ), product_id
    assert (
        characteristics["payment_frequency_rates_percent"] == expected_rates
    ), product_id
    assert characteristics["guarantee_period_options_years"] == [
        10,
        15,
        20,
    ], product_id
    assert (
        characteristics["increasing_annuity_simple_growth_rate_percent"] == 3
    ), product_id
    assert len(schedule["plan_options"]) == 24, product_id

    values = {option["value"] for option in schedule["plan_options"]}
    assert len(values) == 24, product_id
    for option in schedule["plan_options"]:
        assert len(option["coverage_entries"]) == 2, (
            product_id,
            option["value"],
        )
        annuity, unpaid = option["coverage_entries"]
        assert (
            annuity["calculation_basis"]
            == "annuity_face_amount_schedule"
        ), (product_id, option["value"])
        assert annuity["basis"] == "face_amount", (
            product_id,
            option["value"],
        )
        assert annuity["rate_percent"] in expected_rates.values(), (
            product_id,
            option["value"],
        )
        if annuity["annuity_payment_pattern"] == "increasing":
            assert annuity["annuity_growth_rate_percent"] == 3
            assert annuity["policy_state_keys"] == [
                "annuity_payment_year"
            ]
        else:
            assert "annuity_growth_rate_percent" not in annuity
            assert "policy_state_keys" not in annuity
        assert unpaid["calculation_basis"] == "policy_state_amount"
        assert unpaid["policy_state_keys"] == ["unpaid_annuity_balance"]

print(
    json.dumps(
        {
            "status": "ok",
            "extractor_version": EXTRACTOR_VERSION,
            "verified_product_count": len(parsed),
            "plan_options_per_product": 24,
            "payment_frequency_count": len(expected_rates),
        },
        ensure_ascii=False,
        indent=2,
    )
)
