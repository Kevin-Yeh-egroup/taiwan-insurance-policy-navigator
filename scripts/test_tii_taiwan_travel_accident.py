from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    TAIWAN_TRAVEL_ACCIDENT_DISABILITY_RATES,
    TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_travel_accident_face_amount,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-007"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-007-taiwan-travel-accident-v221.json"
)
PARSER_ID = "taiwan-travel-accident-face-amount-v1"


def source_document(product_id: str) -> dict:
    version = TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert source_sha256 == version["source_document_sha256"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-007",
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
    TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.items(),
    key=lambda item: item[1]["revision"],
):
    revision = int(version["revision"])
    document = source_document(product_id)
    assert document["page_count"] == version["page_count"]
    assert document["pages_parsed"] == version["page_count"]
    assert document["source_text_extractor"] == version[
        "source_text_extractor"
    ]

    schedule = parse_taiwan_travel_accident_face_amount(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-007/{product_id}")

    version_characteristics = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert version_characteristics["product_family"] == (
        "taiwan-travel-accident-face-amount"
    )
    assert version_characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert version_characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert version_characteristics[
        "disability_rate_options_percent"
    ] == TAIWAN_TRAVEL_ACCIDENT_DISABILITY_RATES
    assert version_characteristics["disability_term"] == (
        "失能" if revision >= 18 else "殘廢"
    )
    assert version_characteristics["accident_claim_days"] == 180
    assert version_characteristics["after_180_causal_exception"] is True
    assert version_characteristics[
        "funeral_benefit_limit_applicable"
    ] is True
    assert version_characteristics["minor_death_benefit_rule"] == (
        "under_14_converts_to_funeral"
        if revision <= 7
        else "under_15_benefit_not_effective"
    )
    assert version_characteristics["funeral_eligibility_rule"] == (
        "under_14_or_mental_incapacity"
        if revision <= 7
        else "mental_capacity_definition"
        if revision <= 17
        else "guardianship_declaration"
    )
    assert version_characteristics["funeral_limit_basis"] == (
        "regulator_funeral_expense_limit"
        if revision <= 7
        else "estate_tax_funeral_deduction_half"
    )
    assert version_characteristics["injury_medical_in_main_terms"] is True

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "accidental-death-or-funeral",
        "accidental-disability",
        "injury-medical-reimbursement",
    }
    death = entries["accidental-death-or-funeral"]
    assert death["calculation_basis"] == "death_or_funeral_face_amount"
    assert death["cumulative_paid_state_key"] == (
        "same_accident_prior_disability_benefit_paid_amount"
    )
    if revision >= 8:
        assert death["exclusion_state_key"] == (
            "minor_death_benefit_status"
        )
        assert death["exclusion_values"] == ["not_effective"]
    else:
        assert "exclusion_state_key" not in death
        assert "exclusion_values" not in death

    disability = entries["accidental-disability"]
    assert disability["calculation_basis"] == "percentage_of_base"
    assert disability["rate_state_key"] == (
        "disability_benefit_rate_percent"
    )
    assert disability["cumulative_paid_state_key"] == (
        "prior_disability_benefit_paid_amount"
    )
    assert disability["rate_min_percent"] == 5
    assert disability["rate_max_percent"] == 100

    medical = entries["injury-medical-reimbursement"]
    assert medical["calculation_basis"] == "reimbursement_with_cap"
    assert medical["basis"] == "policy_recorded_limit"
    assert medical["expense_state_key"] == "injury_medical_expense"
    assert "exclusion_state_key" not in medical
    assert medical["cumulative_paid_state_key"] == (
        "prior_same_injury_medical_benefit_paid_amount"
    )
    schedules[product_id] = schedule


reference_document = source_document("202221M11A58000")
assert parse_taiwan_travel_accident_face_amount(
    {**reference_document, "batch_id": "tii-life-008"}
) is None
assert parse_taiwan_travel_accident_face_amount(
    {**reference_document, "product_id": "202221M11A58001"}
) is None
assert parse_taiwan_travel_accident_face_amount(
    {**reference_document, "file_name": "202221M11A58000-F.pdf"}
) is None
assert parse_taiwan_travel_accident_face_amount(
    {**reference_document, "source_document_sha256": "0" * 64}
) is None
assert parse_taiwan_travel_accident_face_amount(
    {**reference_document, "page_count": 12}
) is None
corrupted_text = copy.deepcopy(reference_document)
corrupted_text["text"] = corrupted_text["text"].replace(
    "台灣人壽旅行平安保險",
    "台灣人壽旅行平安保險異動",
    1,
)
assert parse_taiwan_travel_accident_face_amount(corrupted_text) is None

recovered_document = source_document("202221M11A58014")
assert recovered_document["source_text_extractor"] == "pymupdf"
assert "台灣人壽旅行平安保險" in recovered_document["text"]
assert "傷害醫療保險金" in recovered_document["text"]

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == "tii-plan-benefits-v221"
assert proposal["batch_id"] == "tii-life-007"
assert proposal["proposal_count"] == 22
assert proposal["proposed_count"] == 22
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS[product_id][
            "source_document_sha256"
        ]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-007",
        "product_count": len(schedules),
        "coverage_entry_count": len(schedules) * 3,
        "exact_source_hash_count": len(
            {
                version["source_document_sha256"]
                for version in TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.values()
            }
        ),
        "pymupdf_recovery_count": sum(
            version["source_text_extractor"] == "pymupdf"
            for version in TAIWAN_TRAVEL_ACCIDENT_PRODUCT_VERSIONS.values()
        ),
    }
)
