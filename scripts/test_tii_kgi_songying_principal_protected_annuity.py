#!/usr/bin/env python3
"""Verify exact-source Songying principal-protected annuity versions."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_FILES,
    KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_PRODUCT_IDS,
    parse_kgi_china_songying_principal_protected_annuity,
)


EXPECTED_SHA256 = {
    "205411M11A02600": "66f0418d630bc2bd3c12af93e6ec620403aa074573b69abdf8e783bd3b554e0a",
    "205411M11A02601": "ce7aedb9aeedf23bc6298551ff90861cd2608340f19f35155c4d616447d9c2af",
    "205411M11A02602": "d3c7069e9ce3b4f9c0afad2d0959820cf8caa3c299a355de126300f8c98880ba",
    "205411M11A02603": "887e343c01ec84053e01ef5591180ed80d5d9c2c3e00df500ffbb6a25a5ed1a4",
    "205411M11A02604": "c1a6082b434b711f7c743b06227ce7f8d6968e84e0b08bfb1dab381830b852d0",
    "205411M11A02605": "28596bcc7ff59329fa4d245341f2315158db4a50c42aa06b56a5b229d5c7ee81",
    "205411M11A02606": "0973139a1ed09b21a184bc5926106939b735193dd0a7bb1fc03b168fca27c0c2",
}
EXPECTED_RATES = {
    "205411M11A02600": {
        "annual": 100.0,
        "semiannual": 49.5562,
        "quarterly": 24.6686,
        "monthly": 8.1987,
    },
    "205411M11A02601": {
        "annual": 100.0,
        "semiannual": 49.4523,
        "quarterly": 24.592,
        "monthly": 8.1679,
    },
    **{
        f"205411M11A0260{revision}": {
            "annual": 100.0,
            "semiannual": 49.4836,
            "quarterly": 24.6147,
            "monthly": 8.1769,
        }
        for revision in range(2, 7)
    },
}


payload = json.loads(
    (
        ROOT
        / "work"
        / "tii-document-text"
        / "tii-life-028-text.json"
    ).read_text(encoding="utf-8")
)
source_documents = {}
parsed = {}
for document in payload["documents"]:
    product_id = str(document.get("product_id") or "")
    if (
        product_id
        not in KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
    ):
        continue
    source_documents[product_id] = document
    schedule = parse_kgi_china_songying_principal_protected_annuity(
        {**document, "batch_id": "tii-life-028"}
    )
    assert schedule is not None, product_id
    parsed[product_id] = schedule

assert EXTRACTOR_VERSION == "tii-plan-benefits-v217"
assert set(source_documents) == (
    KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_PRODUCT_IDS
)
assert set(parsed) == (
    KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_PRODUCT_IDS
)

for product_id, schedule in parsed.items():
    source_path = (
        ROOT
        / "work"
        / "tii-documents"
        / "tii-life-028"
        / product_id
        / KGI_CHINA_SONGYING_PRINCIPAL_PROTECTED_ANNUITY_FILES[
            product_id
        ]
    )
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        EXPECTED_SHA256[product_id]
    )
    assert schedule["selection_type"] == "face_amount_plan"
    assert schedule["input_mode"] == "face_amount_plan"
    assert schedule["selection_source"] == "terms"
    assert schedule["face_amount_label"] == "年領年金金額"
    assert len(schedule["plan_options"]) == 4

    characteristics = schedule["version_characteristics"]
    assert characteristics["payment_frequency_rates_percent"] == (
        EXPECTED_RATES[product_id]
    )
    expected_settlement = (
        "lump_sum_unpaid_balance"
        if product_id in {"205411M11A02600", "205411M11A02601"}
        else "continue_annuity_until_balance_exhausted"
    )
    assert characteristics["death_settlement_mode"] == expected_settlement
    assert characteristics["required_policy_inputs"] == [
        "face_amount",
        "plan",
        "single_premium_amount",
        "annuity_paid_total_amount",
    ]

    for option in schedule["plan_options"]:
        expected_entry_count = (
            3
            if expected_settlement == "lump_sum_unpaid_balance"
            else 4
        )
        assert len(option["coverage_entries"]) == expected_entry_count
        annuity, unpaid, dividend, *conditional_entries = (
            option["coverage_entries"]
        )
        assert annuity["calculation_basis"] == (
            "annuity_face_amount_schedule"
        )
        assert annuity["annuity_payment_pattern"] == "level"
        assert "annuity_guarantee_years" not in annuity
        assert unpaid["calculation_basis"] == (
            "single_premium_minus_paid_annuity_total"
        )
        assert unpaid["policy_state_keys"] == [
            "single_premium_amount",
            "annuity_paid_total_amount",
        ]
        if expected_settlement == "lump_sum_unpaid_balance":
            assert unpaid["amount_role"] == "payout"
            assert unpaid["result_kind"] == "cash_payout"
        else:
            assert unpaid["amount_role"] == "reference"
            assert unpaid["result_kind"] == "payment_method"
        assert dividend["calculation_basis"] == "policy_state_amount"
        assert dividend["policy_state_keys"] == [
            "policy_dividend_amount"
        ]
        assert dividend["amount_stage"] == "insurer_quoted_amount"
        if expected_settlement != "lump_sum_unpaid_balance":
            assert len(conditional_entries) == 1
            successor = conditional_entries[0]
            assert successor["calculation_basis"] == (
                "policy_state_amount"
            )
            assert successor["policy_state_keys"] == [
                "successor_discounted_annuity_amount"
            ]
            assert successor["amount_stage"] == (
                "insurer_quoted_amount"
            )

wrong_version = {
    **source_documents["205411M11A02601"],
    "batch_id": "tii-life-028",
    "product_id": "205411M11A02600",
    "file_name": "205411M11A026-A.pdf",
}
assert (
    parse_kgi_china_songying_principal_protected_annuity(
        wrong_version
    )
    is None
), "a different version's coefficients must not cross-match"

print(
    json.dumps(
        {
            "status": "ok",
            "extractor_version": EXTRACTOR_VERSION,
            "verified_product_count": len(parsed),
            "plan_options_per_product": 4,
            "exact_source_sha_count": len(EXPECTED_SHA256),
        },
        ensure_ascii=False,
        indent=2,
    )
)
