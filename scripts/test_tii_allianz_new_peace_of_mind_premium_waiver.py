from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_PRODUCT_IDS,
    ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_VERSIONS,
    complete_strict_source_document,
    parse_allianz_new_peace_of_mind_premium_waiver_policy_state,
    parse_allianz_one_year_inpatient_medical_expense_rider_unit,
    parse_farglory_jinanxin_premium_waiver_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-092"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-092-allianz-new-peace-of-mind-premium-waiver-health-rider.json"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-092-allianz-new-peace-of-mind-premium-waiver-v285.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-092-allianz-new-peace-of-mind-premium-waiver-v285-review-packet"
    / "tii-life-092-allianz-new-peace-of-mind-premium-waiver-v285-review-packet.json"
)
PARSER_ID = (
    "allianz-new-peace-of-mind-premium-waiver-policy-state-v1"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_DIR / product_id / str(version["file_name"])
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
    schedule: dict, expected_error: str
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-092/allianz-new-peace-of-mind-waiver",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Allianz waiver schedule"
        )


assert len(
    ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_PRODUCT_IDS
) == 14
matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["family_fingerprint"] == "0b78b44efcf2e434e23825ed"
assert matrix["product_count"] == 14
assert matrix["status_counts"] == {"readable": 14}
assert matrix["duplicate_source_sha_groups"] == {
    "318ddeb1815726fc99deadf92d3b8b015a47285d4646428f16949e798e888063": [
        "218341R11A00300",
        "218341R11A00301",
        "218341R11A00302",
    ]
}

schedules: dict[str, dict] = {}
for product_id in sorted(
    ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_PRODUCT_IDS
):
    source_version = (
        ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_VERSIONS[
            product_id
        ]
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

    schedule = (
        parse_allianz_new_peace_of_mind_premium_waiver_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    assert parse_allianz_one_year_inpatient_medical_expense_rider_unit(
        document
    ) is None
    assert parse_farglory_jinanxin_premium_waiver_policy_state(
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
        "0b78b44efcf2e434e23825ed"
    )
    assert version["source_document_sha256"] == (
        source_version["source_document_sha256"]
    )
    assert version["source_text_sha256"] == (
        source_version["source_text_sha256"]
    )
    assert version["disability_term"] == (
        "殘廢" if revision <= 9 else "失能"
    )
    assert version[
        "insured_consent_required_for_termination"
    ] is (revision >= 4)
    assert version["critical_illness_definition_phase"] == (
        "legacy_seven_major_diseases"
        if revision <= 8
        else "standardized_severe_major_diseases"
    )
    assert version["cash_payout_available"] is False
    assert version[
        "current_unexpired_premium_refund_available"
    ] is False
    assert version["required_policy_inputs"] == [
        "remaining_premium_amount"
    ]
    assert version["ocr_evidence_path"] == (
        "work/tii-benefit-source-matrices/"
        "tii-life-092-allianz-new-peace-of-mind-premium-waiver-health-rider.json"
        if revision in {7, 8, 9}
        else None
    )
    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {"future-premium-waiver"}
    assert entries["future-premium-waiver"][
        "policy_state_keys"
    ] == ["remaining_premium_amount"]
    assert entries["future-premium-waiver"][
        "result_kind"
    ] == "non_cash_effect"
    schedules[product_id] = schedule


wrong_phase = copy.deepcopy(schedules["218341R11A00304"])
wrong_phase["version_characteristics"]["semantic_phase"] = (
    "legacy_disability_definition"
)
assert_invalid_schedule(wrong_phase, "version contract is invalid")

wrong_cash_flag = copy.deepcopy(
    schedules["218341RZ1A00321A11Z10000013"]
)
wrong_cash_flag["version_characteristics"][
    "cash_payout_available"
] = True
assert_invalid_schedule(wrong_cash_flag, "version contract is invalid")

base_document, _ = source_document("218341R11A00300")
assert parse_allianz_new_peace_of_mind_premium_waiver_policy_state(
    {**base_document, "batch_id": "tii-life-080"}
) is None
assert parse_allianz_new_peace_of_mind_premium_waiver_policy_state(
    {**base_document, "product_id": "216311R12G02700"}
) is None
assert parse_allianz_new_peace_of_mind_premium_waiver_policy_state(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_allianz_new_peace_of_mind_premium_waiver_policy_state(
    {**base_document, "text": f"{base_document['text']}錯置來源"}
) is None

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v285"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]

review_packet = json.loads(
    REVIEW_PACKET_PATH.read_text(encoding="utf-8")
)
assert review_packet["proposal_count"] == 14
assert review_packet["status_counts"] == {
    "ready_for_human_source_review": 14
}
assert review_packet["error_counts"] == {}
assert {
    item["product_id"] for item in review_packet["items"]
} == ALLIANZ_NEW_PEACE_OF_MIND_PREMIUM_WAIVER_PRODUCT_IDS
assert all(
    item["review_packet_status"]
    == "ready_for_human_source_review"
    for item in review_packet["items"]
)

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": 4,
        "ocr_product_count": 3,
        "cash_payout_product_count": 0,
    }
)
