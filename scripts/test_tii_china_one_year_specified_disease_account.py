from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
)
from tii_china_one_year_specified_disease_account import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-026"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-026-china-one-year-specified-disease-account-v296.json"
)
PARSER_ID = "china-one-year-specified-disease-account-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "source_document_sha256": version["source_document_sha256"],
            "text": "",
        },
        source_path,
    )


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-026/china-specified-disease-account",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("formal validator accepted an invalid schedule")


schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    expected = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / expected["file_name"]
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == expected[
        "source_document_sha256"
    ]
    document = source_document(product_id)
    assert document["source_text_extractor"] == expected[
        "source_text_extractor"
    ]
    assert document["page_count"] == expected["page_count"]
    assert document["pages_parsed"] == expected["page_count"]
    assert hashlib.sha256(document["text"].encode("utf-8")).hexdigest() == (
        expected["source_text_sha256"]
    )

    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated == (PARSER_ID, schedule), product_id
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(expected["revision"])
    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert schedule["selection_label"] == "保險金額"
    assert schedule["face_amount_label"] == "保單所載保險金額"
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == expected[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == expected[
        "source_text_sha256"
    ]
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["specified_disease_item_count"] == 18
    assert version["cancer_waiting_days"] == 90
    assert version["other_disease_waiting_days"] == 30
    assert version["policy_account_value_is_benefit_basis"] is False
    assert version["insurance_cost_deducted_from_main_policy_account"] is True
    assert version["maximum_claim_count"] == 1
    assert version["contract_terminates_after_benefit"] is True
    assert version["beneficiary_identity_document_required"] is (
        revision >= 4
    )
    assert version["legacy_disability_wording_present"] is (revision <= 7)
    assert version["medical_opinion_review_available"] is (revision >= 11)
    assert version["required_policy_inputs"] == [
        "china_account_specific_illness_claim_status",
    ]

    entries = {item["id"]: item for item in schedule["coverage_entries"]}
    assert set(entries) == {
        "specified-disease-account-benefit",
        "unexpired-insurance-cost-refund",
    }
    primary = entries["specified-disease-account-benefit"]
    refund = entries["unexpired-insurance-cost-refund"]
    assert primary["calculation_basis"] == "percentage_of_base"
    assert primary["rate_percent"] == 100
    assert primary["unit_key"] == "face_amount"
    assert primary["aggregation_rule"] == "choose_one"
    assert primary["event_key"] == "specified_disease"
    assert refund["calculation_basis"] == "policy_state_amount"
    assert refund["aggregation_rule"] == "conditional_additive"
    assert refund["applies_to_entry_ids"] == [
        "specified-disease-account-benefit"
    ]
    assert refund["policy_state_keys"] == [
        "unexpired_premium_refund_amount"
    ]
    assert {
        item["exclusion_state_key"] for item in entries.values()
    } == {"china_account_specific_illness_claim_status"}
    assert {
        tuple(item["exclusion_values"]) for item in entries.values()
    } == {("already_paid",)}
    schedules[product_id] = schedule


valid_document = source_document("205351R11A54800")
wrong_sha = copy.deepcopy(valid_document)
wrong_sha["source_document_sha256"] = "0" * 64
assert parse_policy(wrong_sha) is None

wrong_product = copy.deepcopy(valid_document)
wrong_product["product_id"] = "205351R11A00200"
assert parse_policy(wrong_product) is None

wrong_file = copy.deepcopy(valid_document)
wrong_file["file_name"] = "205351R11A00200-A.pdf"
assert parse_policy(wrong_file) is None

altered_text = copy.deepcopy(valid_document)
altered_text["text"] = altered_text["text"].replace(
    "本公司按其保險金額給付",
    "本公司按其保險金額百分之九十給付",
    1,
)
assert parse_policy(altered_text) is None

wrong_account_basis = copy.deepcopy(schedules["205351R11A54800"])
wrong_account_basis["version_characteristics"][
    "policy_account_value_is_benefit_basis"
] = True
assert_invalid_schedule(wrong_account_basis, "identity is invalid")

wrong_rate = copy.deepcopy(schedules["205351R11A54800"])
wrong_rate["coverage_entries"][0]["rate_percent"] = 90
assert_invalid_schedule(wrong_rate, "entry contract is invalid")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == "tii-plan-benefits-v296"
assert proposal_payload["proposal_count"] == 13
assert proposal_payload["proposed_count"] == 13
assert proposal_payload["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal_payload["proposals"]
} == PRODUCT_IDS
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == VERSIONS[product_id][
        "source_document_sha256"
    ]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": len(
            {
                schedule["version_characteristics"]["semantic_phase"]
                for schedule in schedules.values()
            }
        ),
        "parser_id": PARSER_ID,
    }
)
