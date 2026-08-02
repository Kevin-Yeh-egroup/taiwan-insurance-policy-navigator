from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    HONGTAI_PREMIUM_WAIVER_RIDER_PRODUCT_IDS,
    HONGTAI_PREMIUM_WAIVER_RIDER_VERSIONS,
    complete_strict_source_document,
    hongtai_premium_waiver_terms_change_number,
    parse_hongtai_premium_waiver_rider_plan_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-086"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-086-hongtai-premium-waiver-rider-v239.json"
)
PARSER_ID = "hongtai-premium-waiver-rider-plan-policy-state-v1"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = HONGTAI_PREMIUM_WAIVER_RIDER_VERSIONS[product_id]
    source_path = (
        DOCUMENTS_DIR / product_id / version["file_name"]
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
            "negative/tii-life-086/hongtai-premium-waiver",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Hongtai waiver schedule"
        )


schedules: dict[str, dict] = {}
ocr_product_count = 0
for product_id in sorted(
    HONGTAI_PREMIUM_WAIVER_RIDER_PRODUCT_IDS
):
    source_version = HONGTAI_PREMIUM_WAIVER_RIDER_VERSIONS[
        product_id
    ]
    revision = int(source_version["revision"])
    change_number = hongtai_premium_waiver_terms_change_number(
        revision
    )
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_version["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        source_version["source_text_extractor"]
    )
    if document["source_text_extractor"] == "windows_ocr":
        ocr_product_count += 1

    schedule = (
        parse_hongtai_premium_waiver_rider_plan_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["source_page_count"] == (
        source_version["page_count"]
    )
    assert version["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{change_number}"
    )
    assert change_number != 8
    assert version["disability_term"] == (
        "殘廢" if revision <= 9 else "失能"
    )
    assert version["disease_waiting_days"] == 30
    assert version["accidental_waiting_exception"] is True
    assert (
        version["critical_illness_definition_source"]
        == "exact_terms_revision"
    )
    assert version["waiver_is_non_cash_effect"] is True
    assert version["no_cash_surrender_value"] is True
    assert version[
        "waived_premium_settlement_discount_rate_percent"
    ] == (
        2
        if revision <= 5
        else 1.5
        if revision <= 7
        else 1.25
        if revision <= 11
        else 1
    )

    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert [
        option["value"] for option in schedule["plan_options"]
    ] == ["A", "B"]
    expected_ids = {
        "future-premium-waiver",
        "current-unexpired-premium-refund",
        "waived-premium-termination-settlement",
    }
    if revision >= 2:
        expected_ids.add(
            "overlapping-waiver-cash-settlement"
        )
    for option in schedule["plan_options"]:
        entries = {
            entry["id"]: entry
            for entry in option["coverage_entries"]
        }
        assert set(entries) == expected_ids
        waiver = entries["future-premium-waiver"]
        assert waiver["calculation_basis"] == "waiver"
        assert waiver["amount_role"] == "premium_waiver"
        assert waiver["result_kind"] == "non_cash_effect"
        assert waiver["policy_state_keys"] == [
            "remaining_premium_amount"
        ]
        for cash_id in expected_ids - {
            "future-premium-waiver"
        }:
            assert entries[cash_id].get("amount") is None
            assert (
                entries[cash_id]["calculation_basis"]
                == "policy_state_amount"
            )
            assert entries[cash_id]["result_kind"] == "cash_payout"
    schedules[product_id] = schedule


assert ocr_product_count == 6

base_document, _ = source_document("217341R11A00100")
assert (
    parse_hongtai_premium_waiver_rider_plan_policy_state(
        {**base_document, "batch_id": "tii-life-085"}
    )
    is None
)
assert (
    parse_hongtai_premium_waiver_rider_plan_policy_state(
        {**base_document, "file_name": "217341R11A00100-F.pdf"}
    )
    is None
)
assert (
    parse_hongtai_premium_waiver_rider_plan_policy_state(
        {
            **base_document,
            "source_document_sha256": "0" * 64,
        }
    )
    is None
)
assert (
    parse_hongtai_premium_waiver_rider_plan_policy_state(
        {**base_document, "text": f"{base_document['text']}變更"}
    )
    is None
)

wrong_revision = copy.deepcopy(
    schedules["217341RZ1A00122A11Z10000009"]
)
wrong_revision["version_characteristics"][
    "terms_revision"
] = "partial_change_8"
assert_invalid_schedule(
    wrong_revision,
    "exact version formula is invalid",
)

wrong_cash_kind = copy.deepcopy(schedules["217341R11A00100"])
wrong_cash_kind["plan_options"][0]["coverage_entries"][0][
    "result_kind"
] = "cash_payout"
assert_invalid_schedule(
    wrong_cash_kind,
    "exact entry contract is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v239"
)
assert proposal_payload["proposal_count"] == 18
assert proposal_payload["proposed_count"] == 18
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == HONGTAI_PREMIUM_WAIVER_RIDER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        HONGTAI_PREMIUM_WAIVER_RIDER_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "ocr_product_count": ocr_product_count,
        "semantic_phase_count": 6,
    }
)
