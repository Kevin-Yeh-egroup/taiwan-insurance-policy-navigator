from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    CHUBB_DISABILITY_SUPPORT_ADDENDUM_VERSIONS,
    complete_strict_source_document,
    parse_chubb_disability_support_addendum,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-182"
PARSER_ID = "chubb-disability-support-addendum-v1"
LEGACY_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-182-chubb-disability-support-addendum-"
        "legacy-exact-source-matrix.json"
    )
)
MODERN_MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-candidates"
    / (
        "tii-life-182-chubb-disability-support-addendum-"
        "modern-exact-source-matrix.json"
    )
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / (
        "tii-life-182-chubb-disability-support-addendum-"
        "v225.json"
    )
)


def source_document(product_id: str) -> dict:
    version = CHUBB_DISABILITY_SUPPORT_ADDENDUM_VERSIONS[product_id]
    source_path = DOCUMENT_ROOT / product_id / version["file_name"]
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-182",
            "product_id": product_id,
            "document_type": "policy_terms",
            "file_name": version["file_name"],
            "source_document_sha256": version[
                "source_document_sha256"
            ],
        },
        source_path,
    )


versions = CHUBB_DISABILITY_SUPPORT_ADDENDUM_VERSIONS
assert len(versions) == 38
assert {
    version["revision"] for version in versions.values()
} == set(range(38))
assert len(
    {
        version["source_document_sha256"]
        for version in versions.values()
    }
) == 38

legacy_matrix = json.loads(
    LEGACY_MATRIX_PATH.read_text(encoding="utf-8")
)
modern_matrix = json.loads(
    MODERN_MATRIX_PATH.read_text(encoding="utf-8")
)
assert legacy_matrix["batch_id"] == "tii-life-182"
assert legacy_matrix["product_count"] == 29
assert legacy_matrix["status_counts"] == {"readable": 29}
assert legacy_matrix["duplicate_source_sha_groups"] == {}
assert modern_matrix["batch_id"] == "tii-life-182"
assert modern_matrix["product_count"] == 9
assert modern_matrix["status_counts"] == {"readable": 9}
assert modern_matrix["duplicate_source_sha_groups"] == {}

schedules = {}
semantic_phase_counts = {
    "legacy_main_contract_insurance_amount": 0,
    "main_contract_type_specific_amount": 0,
}
brand_phase_counts = {
    "china_life_brand": 0,
    "chubb_life_brand": 0,
}
for product_id, source_version in sorted(
    versions.items(),
    key=lambda item: item[1]["revision"],
):
    revision = source_version["revision"]
    document = source_document(product_id)
    schedule = parse_chubb_disability_support_addendum(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-182/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_batch_id"] == "tii-life-182"
    assert version["source_product_id"] == product_id
    assert version["source_document_sha256"] == source_version[
        "source_document_sha256"
    ]
    assert version["terms_revision"] == f"partial-change-{revision}"
    assert version["grade_payment_months"] == {
        "1": 100,
        "2": 75,
        "3": 75,
        "4": 75,
        "5": 50,
        "6": 50,
    }
    assert version["eligibility_waiting_days"] == 180
    assert version["maximum_eligible_age"] == 75
    assert version["death_balance_discount_rate_percent"] == 2
    semantic_phase_counts[version["semantic_phase"]] += 1
    brand_phase_counts[version["company_brand_phase"]] += 1

    if revision <= 18:
        assert schedule["selection_type"] == "face_amount"
        assert schedule["input_mode"] == "face_amount"
        assert schedule.get("plan_options", []) == []
        assert version["main_contract_amount_basis"] == (
            "main_contract_insurance_amount"
        )
    else:
        assert schedule["selection_type"] == "face_amount_plan"
        assert schedule["input_mode"] == "face_amount_plan"
        assert schedule["plan_options"] == [
            {"value": "investment", "label": "投資型主約"},
            {
                "value": "non_investment",
                "label": "非投資型主約",
            },
        ]
        assert version["main_contract_amount_basis"] == (
            "main_contract_type_specific"
        )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "chubb-disability-support-monthly",
        "chubb-disability-support-death-balance",
    }
    assert entries[
        "chubb-disability-support-monthly"
    ]["rate_percent"] == 1
    assert entries[
        "chubb-disability-support-monthly"
    ]["limit_scope"] == "per_month"
    assert entries[
        "chubb-disability-support-death-balance"
    ]["calculation_basis"] == "policy_state_amount"
    schedules[product_id] = schedule

assert semantic_phase_counts == {
    "legacy_main_contract_insurance_amount": 19,
    "main_contract_type_specific_amount": 19,
}
assert brand_phase_counts == {
    "china_life_brand": 29,
    "chubb_life_brand": 9,
}

reference = source_document("270391A11A00119")
for corrupted in (
    {**reference, "batch_id": "tii-life-181"},
    {**reference, "product_id": "270391A11A00118"},
    {**reference, "file_name": "270391A11A00118-A.pdf"},
    {**reference, "source_document_sha256": "0" * 64},
    {**reference, "page_count": 999},
):
    assert parse_chubb_disability_support_addendum(corrupted) is None
corrupted_text = copy.deepcopy(reference)
corrupted_text["text"] = corrupted_text["text"].replace(
    "主契約基本保額的百分之一",
    "主契約基本保額",
    1,
)
assert parse_chubb_disability_support_addendum(corrupted_text) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == "tii-life-182"
assert proposal["proposal_count"] == 38
assert proposal["proposed_count"] == 38
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == set(versions)
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    product_id = item["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == versions[
        product_id
    ]["source_document_sha256"]
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "products": len(schedules),
        "semantic_phase_counts": semantic_phase_counts,
        "brand_phase_counts": brand_phase_counts,
    }
)
