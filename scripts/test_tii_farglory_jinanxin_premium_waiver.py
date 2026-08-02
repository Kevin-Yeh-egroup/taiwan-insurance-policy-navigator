from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FARGLORY_JINANXIN_PREMIUM_WAIVER_PRODUCT_IDS,
    FARGLORY_JINANXIN_PREMIUM_WAIVER_VERSIONS,
    complete_strict_source_document,
    farglory_jinanxin_premium_waiver_file_name,
    parse_farglory_jinanxin_premium_waiver_policy_state,
    parse_farglory_premium_waiver_rider_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-080"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-080-farglory-jinanxin-premium-waiver-v249.json"
)
PARSER_ID = "farglory-jinanxin-premium-waiver-policy-state-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    source_path = (
        DOCUMENTS_DIR
        / product_id
        / farglory_jinanxin_premium_waiver_file_name(product_id)
    )
    source_sha256 = hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": source_sha256,
        },
        source_path,
    )
    return document, source_path


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-080/farglory-jinanxin-waiver",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Jinanxin schedule"
        )


assert len(FARGLORY_JINANXIN_PREMIUM_WAIVER_PRODUCT_IDS) == 16
schedules: dict[str, dict] = {}
for product_id in sorted(
    FARGLORY_JINANXIN_PREMIUM_WAIVER_PRODUCT_IDS
):
    source_version = (
        FARGLORY_JINANXIN_PREMIUM_WAIVER_VERSIONS[product_id]
    )
    revision = int(source_version["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )

    schedule = parse_farglory_jinanxin_premium_waiver_policy_state(
        document
    )
    assert schedule is not None, product_id
    assert parse_farglory_premium_waiver_rider_policy_state(
        document
    ) is None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == (
        "8b1ce911a76877355b950bc1"
    )
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["source_page_count"] == (
        source_version["page_count"]
    )
    assert version["ocr_evidence_path"] is None
    assert version["premium_waiver_disability_levels"] == (
        "2-3" if revision <= 1 else "2-6"
    )
    assert version["disability_term"] == (
        "殘廢" if revision <= 10 else "失能"
    )
    assert version[
        "insured_consent_required_for_termination"
    ] is (revision >= 7)
    assert version["post_rider_expiry_premiums_resume"] is (
        revision == 15
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert entries["future-premium-waiver"][
        "policy_state_keys"
    ] == ["remaining_premium_amount"]
    assert entries["future-premium-waiver"][
        "result_kind"
    ] == "non_cash_effect"
    if revision == 15:
        assert set(entries) == {
            "future-premium-waiver",
            "current-unexpired-premium-refund",
            "overlapping-waiver-cash-settlement",
        }
        assert version["required_policy_inputs"] == [
            "remaining_premium_amount",
            "unexpired_premium_refund_amount",
            "overlapping_waiver_settlement_amount",
        ]
        assert version[
            "current_unexpired_premium_refund_scope"
        ] == "main_contract_and_other_riders_excluding_this_rider"
    else:
        assert set(entries) == {"future-premium-waiver"}
        assert version["required_policy_inputs"] == [
            "remaining_premium_amount"
        ]
    schedules[product_id] = schedule


wrong_consent = copy.deepcopy(schedules["216311R12G02707"])
wrong_consent["version_characteristics"][
    "insured_consent_required_for_termination"
] = False
assert_invalid_schedule(
    wrong_consent,
    "version contract is invalid",
)

wrong_refund_scope = copy.deepcopy(
    schedules["216341RZ1A02722A11Z10000015"]
)
wrong_refund_scope["version_characteristics"][
    "current_unexpired_premium_refund_scope"
] = "all_attached_contracts"
assert_invalid_schedule(
    wrong_refund_scope,
    "version contract is invalid",
)

base_document, _ = source_document("216311R12G02700")
assert parse_farglory_jinanxin_premium_waiver_policy_state(
    {**base_document, "batch_id": "tii-life-081"}
) is None
assert parse_farglory_jinanxin_premium_waiver_policy_state(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_jinanxin_premium_waiver_policy_state(
    {**base_document, "text": f"{base_document['text']}變更"}
) is None

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v249"
)
assert proposal_payload["proposal_count"] == 16
assert proposal_payload["proposed_count"] == 16
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FARGLORY_JINANXIN_PREMIUM_WAIVER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FARGLORY_JINANXIN_PREMIUM_WAIVER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": 5,
        "ocr_product_count": 0,
    }
)
