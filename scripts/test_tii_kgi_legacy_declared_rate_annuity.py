#!/usr/bin/env python3
"""Verify exact-source KGI/China legacy declared-rate annuities."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    KGI_CHINA_LEGACY_DECLARED_RATE_ANNUITY_CHARACTERISTICS,
    parse_kgi_china_legacy_declared_rate_annuity,
)


EXPECTED_SHA256 = {
    "205491M21A02700": "eb4fd662b3b666880cfdbe2b643e78694274a092b00f3935ee8e53c051f7a749",
    "205491M21A02702": "081fe0863e56020dd88410f9e5ce2e848458fc8236b19644b0ffdfa8c438f09f",
    "205491M21A02703": "62c9aafb515a787f2b4352237e9eecb1222c1e603fe7d5bd3a2ab3f08f0b6cfb",
    "205491M21A02704": "af594989c774731f2dcfe3f522294a05aeb046a1da95866ab6166eba5517d35a",
    "205491M21A02705": "82c1c161ac1f6ed3e31282a2e279ceb83b9e3b9952b54b77660d6f901d591114",
    "205491M21A02800": "572dd9ebaf3c391113117d7472c94e8a06c641a26d9180bb1b0dc4fc3675a2a5",
    "205491M21A02801": "324d5f8ff15959663d1b77a3702f3b117e66b88c75525929d085afbeff7e9192",
    "205491M21A02802": "6c842ddeffe8d84a016cd1253c779cb7ee4fef9afa6a9bc3b68b5c1240972e1b",
    "205491M21A02803": "cea344dcdf29238d0f7d1b21c7fac892e7e04e1bcb6c5367acf5f1597915f62c",
    "205491M21A02804": "09e5b5c9f4dfb26302b259b06e26a996bad62a71e8383c5eccbd527fb6abde79",
    "205491M21A02805": "d44f23db9d49e72af46eb1c6d1d9041d853eca245cd6cc87f19ae65ae3d80fae",
    "205491M21A02806": "5971fc53fceb0e6ea373ef198e9cffe47c5494d9bf7697fa406c3ec44f503fe5",
}
SUMMARY_ONLY_PRODUCT_ID = "205491M21A02701"
SUMMARY_ONLY_SHA256 = (
    "6ab00d35057b6e1148cba0ddb6d29e5418a899867b5c13d85b0af4ff19f5a965"
)


payload = json.loads(
    (
        ROOT
        / "work"
        / "tii-document-text"
        / "tii-life-028-text.json"
    ).read_text(encoding="utf-8")
)
documents = {
    str(document.get("product_id") or ""): document
    for document in payload["documents"]
    if document.get("document_type") == "policy_terms"
    and (
        str(document.get("product_id") or "")
        in KGI_CHINA_LEGACY_DECLARED_RATE_ANNUITY_CHARACTERISTICS
        or str(document.get("product_id") or "")
        == SUMMARY_ONLY_PRODUCT_ID
    )
}
parsed = {}
for product_id in KGI_CHINA_LEGACY_DECLARED_RATE_ANNUITY_CHARACTERISTICS:
    schedule = parse_kgi_china_legacy_declared_rate_annuity(
        {**documents[product_id], "batch_id": "tii-life-028"}
    )
    assert schedule is not None, product_id
    parsed[product_id] = schedule

assert EXTRACTOR_VERSION == "tii-plan-benefits-v217"
assert set(parsed) == set(EXPECTED_SHA256)
assert len(parsed) == 12

for product_id, schedule in parsed.items():
    characteristics = (
        KGI_CHINA_LEGACY_DECLARED_RATE_ANNUITY_CHARACTERISTICS[
            product_id
        ]
    )
    source_path = (
        ROOT
        / "work"
        / "tii-documents"
        / "tii-life-028"
        / product_id
        / characteristics["file_name"]
    )
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        EXPECTED_SHA256[product_id]
    )
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert schedule["selection_source"] == "terms"
    assert [option["value"] for option in schedule["plan_options"]] == [
        "guarantee-10",
        "guarantee-15",
    ]
    version = schedule["version_characteristics"]
    assert version["payment_frequency_options"] == ["annual"]
    assert version["guarantee_period_options_years"] == [10, 15]
    assert version["pre_annuity_death_formula"] == (
        "policy_reserve_value_minus_policy_loan_and_interest"
    )
    assert version["annual_annuity_minimum_amount"] == 10_000
    assert version["annual_annuity_maximum_amount"] == 1_200_000

    for option in schedule["plan_options"]:
        entries = {
            entry["id"]: entry
            for entry in option["coverage_entries"]
        }
        assert set(entries) == {
            "pre-annuity-death-reserve-return",
            "annual-annuity-payment",
            "low-annuity-lump-sum-reserve-payment",
            "unpaid-guaranteed-annuity-balance",
            "excess-annuity-reserve-return",
        }
        for entry_id in (
            "pre-annuity-death-reserve-return",
            "low-annuity-lump-sum-reserve-payment",
        ):
            entry = entries[entry_id]
            assert entry["calculation_basis"] == (
                "reserve_minus_policy_loan_and_interest"
            )
            assert entry["policy_state_keys"] == [
                "policy_reserve_value",
                "policy_loan_and_interest_amount",
            ]
        assert entries["annual-annuity-payment"][
            "policy_state_keys"
        ] == ["annuity_payment_amount"]
        assert entries["annual-annuity-payment"]["amount_stage"] == (
            "insurer_quoted_amount"
        )
        assert entries["unpaid-guaranteed-annuity-balance"][
            "policy_state_keys"
        ] == ["unpaid_annuity_balance"]
        assert entries["excess-annuity-reserve-return"][
            "policy_state_keys"
        ] == ["excess_annuity_reserve_return_amount"]

summary_only_path = (
    ROOT
    / "work"
    / "tii-documents"
    / "tii-life-028"
    / SUMMARY_ONLY_PRODUCT_ID
    / f"{SUMMARY_ONLY_PRODUCT_ID}-A.pdf"
)
assert hashlib.sha256(summary_only_path.read_bytes()).hexdigest() == (
    SUMMARY_ONLY_SHA256
)
assert (
    parse_kgi_china_legacy_declared_rate_annuity(
        {
            **documents[SUMMARY_ONLY_PRODUCT_ID],
            "batch_id": "tii-life-028",
        }
    )
    is None
), "the one-page content summary must not be treated as policy terms"

wrong_version = {
    **documents["205491M21A02800"],
    "batch_id": "tii-life-028",
    "product_id": "205491M21A02700",
    "file_name": "205491M21A02700-A.pdf",
}
assert (
    parse_kgi_china_legacy_declared_rate_annuity(wrong_version)
    is None
), "same-category text from a different exact product must not cross-match"

print(
    json.dumps(
        {
            "status": "ok",
            "extractor_version": EXTRACTOR_VERSION,
            "verified_product_count": len(parsed),
            "plan_options_per_product": 2,
            "source_gap_product_ids": [SUMMARY_ONLY_PRODUCT_ID],
            "exact_source_sha_count": len(EXPECTED_SHA256) + 1,
        },
        ensure_ascii=False,
        indent=2,
    )
)
