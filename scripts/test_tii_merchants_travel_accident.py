from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    MERCHANTS_TRAVEL_ACCIDENT_LEGACY_DISABILITY_RATES,
    MERCHANTS_TRAVEL_ACCIDENT_MODERN_DISABILITY_RATES,
    MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS,
    complete_strict_source_document,
    parse_merchants_travel_accident_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-061"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-061-merchants-travel-accident-v221.json"
)
PARSER_ID = "merchants-travel-accident-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert source_sha256 == version["source_document_sha256"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-061",
            "product_id": product_id,
            "file_name": version["file_name"],
            "document_type": "policy_terms",
            "source_document_sha256": source_sha256,
            "text": "",
        },
        source_path,
    )


schedules: dict[str, dict] = {}
for product_id, version in sorted(
    MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.items()
):
    revision = int(version["revision"])
    document = source_document(product_id)
    assert document["page_count"] == version["page_count"]
    assert document["pages_parsed"] == version["page_count"]

    schedule = parse_merchants_travel_accident_face_amount(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-061/{product_id}")

    expected_rates = (
        MERCHANTS_TRAVEL_ACCIDENT_LEGACY_DISABILITY_RATES
        if revision <= 1
        else MERCHANTS_TRAVEL_ACCIDENT_MODERN_DISABILITY_RATES
    )
    version_characteristics = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert version_characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert version_characteristics["source_text_extractor"] == (
        "pymupdf"
        if version.get("pymupdf_normalized_text_sha256")
        else "pypdf"
    )
    assert version_characteristics["disability_rate_options_percent"] == expected_rates
    assert version_characteristics["disability_term"] == (
        "失能" if revision >= 16 else "殘廢"
    )
    assert version_characteristics["after_180_causal_exception"] is (
        revision >= 5
    )
    assert version_characteristics["funeral_benefit_limit_applicable"] is (
        revision >= 1
    )
    assert version_characteristics[
        "injury_medical_addendum_present_in_terms"
    ] is True
    assert version_characteristics[
        "injury_medical_addendum_requires_policy_confirmation"
    ] is True
    expected_required_inputs = [
        "disability_benefit_rate_percent",
        "injury_medical_rider_status",
    ]
    if revision >= 1:
        expected_required_inputs.append("death_benefit_status")
    assert version_characteristics["required_policy_inputs"] == (
        expected_required_inputs
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        (
            "accidental-death-or-funeral"
            if revision >= 1
            else "accidental-death"
        ),
        "accidental-disability",
        "injury-medical-reimbursement",
    }
    disability = entries["accidental-disability"]
    assert disability["calculation_basis"] == "percentage_of_base"
    assert disability["rate_state_key"] == (
        "disability_benefit_rate_percent"
    )
    assert disability["cumulative_paid_state_key"] == (
        "prior_disability_benefit_paid_amount"
    )
    assert disability["rate_min_percent"] == min(expected_rates)
    assert disability["rate_max_percent"] == max(expected_rates)
    medical = entries["injury-medical-reimbursement"]
    assert medical["calculation_basis"] == "reimbursement_with_cap"
    assert medical["basis"] == "policy_recorded_limit"
    assert medical["expense_state_key"] == "injury_medical_expense"
    assert medical["exclusion_state_key"] == (
        "injury_medical_rider_status"
    )
    assert medical["exclusion_values"] == ["not_included"]
    assert medical["cumulative_paid_state_key"] == (
        "prior_same_injury_medical_benefit_paid_amount"
    )

    death = entries[
        (
            "accidental-death-or-funeral"
            if revision >= 1
            else "accidental-death"
        )
    ]
    assert death["calculation_basis"] == (
        "death_or_funeral_face_amount"
        if revision >= 1
        else "percentage_of_base"
    )
    assert death["cumulative_paid_state_key"] == (
        "same_accident_prior_disability_benefit_paid_amount"
    )
    schedules[product_id] = schedule


reference_document = source_document("211221M11A00100")
wrong_batch = {**reference_document, "batch_id": "tii-life-060"}
assert parse_merchants_travel_accident_face_amount(wrong_batch) is None
wrong_product = {**reference_document, "product_id": "211221M11A00101"}
assert parse_merchants_travel_accident_face_amount(wrong_product) is None
wrong_file = {**reference_document, "file_name": "211221M11A0010-B.pdf"}
assert parse_merchants_travel_accident_face_amount(wrong_file) is None
wrong_source_hash = {
    **reference_document,
    "source_document_sha256": "0" * 64,
}
assert (
    parse_merchants_travel_accident_face_amount(wrong_source_hash)
    is None
)
wrong_page_count = {**reference_document, "page_count": 5}
assert (
    parse_merchants_travel_accident_face_amount(wrong_page_count)
    is None
)
corrupted_text = copy.deepcopy(reference_document)
corrupted_text["text"] = corrupted_text["text"].replace(
    "旅行平安保險",
    "旅行平安保險異動",
    1,
)
assert (
    parse_merchants_travel_accident_face_amount(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == "tii-plan-benefits-v221"
assert proposal["batch_id"] == "tii-life-061"
assert proposal["proposal_count"] == 25
assert proposal["proposed_count"] == 25
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-061",
        "product_count": len(schedules),
        "coverage_entry_count": len(schedules) * 3,
        "exact_source_hash_count": len(
            {
                version["source_document_sha256"]
                for version in MERCHANTS_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.values()
            }
        ),
    }
)
