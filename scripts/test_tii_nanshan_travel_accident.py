from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_TRAVEL_ACCIDENT_LEGACY_DISABILITY_RATES,
    NANSHAN_TRAVEL_ACCIDENT_MODERN_DISABILITY_RATES,
    NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS,
    complete_strict_source_document,
    parse_nanshan_travel_accident_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-031"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-031-nanshan-travel-accident-v226.json"
)
PARSER_ID = "nanshan-travel-accident-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert source_sha256 == version["source_document_sha256"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-031",
            "product_id": product_id,
            "file_name": version["file_name"],
            "document_type": "policy_terms",
            "source_document_sha256": source_sha256,
            "text": "",
        },
        source_path,
    )


schedules: dict[str, dict] = {}
for product_id, version in (
    NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.items()
):
    revision = int(version["revision"])
    document = source_document(product_id)
    assert document["page_count"] == version["page_count"]
    assert document["pages_parsed"] == version["page_count"]
    assert document["source_text_extractor"] == version[
        "source_text_extractor"
    ]

    schedule = parse_nanshan_travel_accident_face_amount(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-031/{product_id}")

    expected_rates = (
        NANSHAN_TRAVEL_ACCIDENT_LEGACY_DISABILITY_RATES
        if revision <= 3
        else NANSHAN_TRAVEL_ACCIDENT_MODERN_DISABILITY_RATES
    )
    has_death_care = revision >= 15
    version_characteristics = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert version_characteristics["product_family"] == (
        "nanshan-travel-accident-face-amount"
    )
    assert version_characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert version_characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert version_characteristics[
        "disability_rate_options_percent"
    ] == expected_rates
    assert version_characteristics["disability_term"] == (
        "失能" if revision >= 18 else "殘廢"
    )
    assert version_characteristics[
        "after_180_causal_exception"
    ] is (revision >= 4)
    assert version_characteristics[
        "death_care_benefit_present"
    ] is has_death_care
    assert version_characteristics["death_care_rate_percent"] == (
        5 if has_death_care else 0
    )
    assert version_characteristics["major_burn_rate_percent"] == 25
    assert version_characteristics[
        "major_burn_same_insurer_aggregate_cap_amount"
    ] == 2_500_000
    assert version_characteristics["major_burn_once_only"] is True
    assert version_characteristics[
        "injury_medical_addendum_requires_policy_confirmation"
    ] is True
    assert version_characteristics["minor_death_benefit_rule"] == (
        "under_14_converts_to_funeral"
        if revision <= 9
        else "under_15_benefit_not_effective"
    )
    assert version_characteristics["funeral_eligibility_rule"] == (
        "under_14_or_mental_incapacity"
        if revision <= 9
        else "mental_capacity_definition"
        if revision <= 17
        else "guardianship_declaration"
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    death_entry_id = (
        "accidental-death-and-care-or-funeral"
        if has_death_care
        else "accidental-death-or-funeral"
    )
    assert set(entries) == {
        death_entry_id,
        "accidental-disability",
        "major-burn-benefit",
        "major-burn-same-insurer-aggregate-cap",
        "injury-medical-reimbursement",
    }
    death = entries[death_entry_id]
    assert death["calculation_basis"] == (
        "death_or_funeral_percentage_of_face_amount"
        if has_death_care
        else "death_or_funeral_face_amount"
    )
    assert death.get("rate_percent") == (
        105 if has_death_care else None
    )
    assert death["cumulative_paid_state_key"] == (
        "same_accident_prior_disability_benefit_paid_amount"
    )
    assert death.get("exclusion_state_key") == (
        "minor_death_benefit_status" if revision >= 10 else None
    )

    disability = entries["accidental-disability"]
    assert disability["calculation_basis"] == "percentage_of_base"
    assert disability["rate_state_key"] == (
        "disability_benefit_rate_percent"
    )
    assert disability["rate_min_percent"] == min(expected_rates)
    assert disability["rate_max_percent"] == max(expected_rates)

    major_burn = entries["major-burn-benefit"]
    assert major_burn["rate_percent"] == 25
    assert major_burn["exclusion_state_key"] == (
        "prior_same_insurer_major_burn_claim_status"
    )
    assert major_burn["cumulative_paid_state_key"] == (
        "same_insurer_other_major_burn_benefit_amount"
    )
    assert major_burn["aggregate_limit_entry_id"] == (
        "major-burn-same-insurer-aggregate-cap"
    )
    assert entries[
        "major-burn-same-insurer-aggregate-cap"
    ]["amount"] == 2_500_000

    medical = entries["injury-medical-reimbursement"]
    assert medical["calculation_basis"] == "reimbursement_with_cap"
    assert medical["exclusion_state_key"] == (
        "injury_medical_rider_status"
    )
    assert medical["cumulative_paid_state_key"] == (
        "prior_same_injury_medical_benefit_paid_amount"
    )
    schedules[product_id] = schedule


assert len(schedules) == 22
duplicate_source_groups: dict[str, list[str]] = {}
for product_id, version in (
    NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.items()
):
    duplicate_source_groups.setdefault(
        version["source_document_sha256"],
        [],
    ).append(product_id)
assert sorted(
    sorted(product_ids)
    for product_ids in duplicate_source_groups.values()
    if len(product_ids) > 1
) == sorted(
    [
        ["206221M11A30100", "206221M11A30101"],
        ["206221M11A30102", "206221M11A30103"],
        ["206221M11A30108", "206221M11A30109"],
        ["206221M11A30110", "206221M11A30111"],
    ]
)

reference_document = source_document("206221M11A30100")
assert (
    parse_nanshan_travel_accident_face_amount(
        {**reference_document, "batch_id": "tii-life-030"}
    )
    is None
)
assert (
    parse_nanshan_travel_accident_face_amount(
        {**reference_document, "product_id": "206221M11A30101"}
    )
    is None
)
assert (
    parse_nanshan_travel_accident_face_amount(
        {**reference_document, "source_document_sha256": "0" * 64}
    )
    is None
)
assert (
    parse_nanshan_travel_accident_face_amount(
        {**reference_document, "page_count": 8}
    )
    is None
)
corrupted_text = copy.deepcopy(reference_document)
corrupted_text["text"] = corrupted_text["text"].replace(
    "旅行平安保險",
    "旅行平安保險異動",
    1,
)
assert (
    parse_nanshan_travel_accident_face_amount(corrupted_text)
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == "tii-plan-benefits-v226"
assert proposal["batch_id"] == "tii-life-031"
assert proposal["proposal_count"] == 22
assert proposal["proposed_count"] == 22
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        NANSHAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-031",
        "product_count": len(schedules),
        "coverage_entry_count": len(schedules) * 5,
        "exact_source_hash_count": len(duplicate_source_groups),
        "duplicate_source_hash_group_count": 4,
    }
)
