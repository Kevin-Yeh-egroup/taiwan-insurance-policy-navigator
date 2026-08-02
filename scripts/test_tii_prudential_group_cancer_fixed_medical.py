from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    PRUDENTIAL_GROUP_CANCER_FIXED_MEDICAL_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_prudential_group_cancer_fixed_medical_unit,
    prudential_group_cancer_fixed_medical_semantic_phase,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-014"
PARSER_ID = "prudential-group-cancer-fixed-medical-unit-v1"


def source_document(product_id: str) -> dict:
    version = PRUDENTIAL_GROUP_CANCER_FIXED_MEDICAL_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT / product_id / version["file_name"]
    )
    document = {
        "batch_id": "tii-life-014",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(PRUDENTIAL_GROUP_CANCER_FIXED_MEDICAL_VERSIONS) == 16
for product_id, version in (
    PRUDENTIAL_GROUP_CANCER_FIXED_MEDICAL_VERSIONS.items()
):
    document = source_document(product_id)
    assert (
        document["source_text_extractor"]
        == version["source_text_extractor"]
    )
    schedule = parse_prudential_group_cancer_fixed_medical_unit(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-014:{product_id}")

    revision = int(version["revision"])
    early_schedule = revision <= 5
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-014"
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_page_count"] == version[
        "page_count"
    ]
    assert characteristics["semantic_phase"] == (
        prudential_group_cancer_fixed_medical_semantic_phase(
            revision
        )
    )
    assert characteristics["maximum_unit_count"] == (
        10 if early_schedule else 20
    )
    assert characteristics["cancer_definition_revision"] == (
        "standardized_severe_cancer_13_exclusions"
        if revision >= 12
        else "legacy_malignant_tumor_definition"
    )
    assert characteristics["cancer_waiting_days"] == 30
    assert characteristics["cancer_coverage_starts_day"] == 31
    assert characteristics[
        "renewal_waiting_period_reapplies"
    ] is False
    assert characteristics["outpatient_annual_visit_limit"] == 70
    assert characteristics["minor_death_benefit_excluded"] is (
        early_schedule
    )
    assert characteristics["radiation_benefit_present"] is False
    assert characteristics["chemotherapy_benefit_present"] is False
    assert characteristics[
        "bone_marrow_transplant_benefit_present"
    ] is False

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "cancer-death-benefit",
        "cancer-inpatient-daily-benefit",
        "cancer-post-discharge-outpatient-benefit",
        "cancer-inpatient-surgery-benefit",
    }
    assert entries["cancer-death-benefit"]["amount"] == (
        500_000 if early_schedule else 250_000
    )
    assert entries["cancer-inpatient-daily-benefit"][
        "amount"
    ] == (2_000 if early_schedule else 1_000)
    assert entries["cancer-post-discharge-outpatient-benefit"][
        "amount_tiers"
    ] == [
        {
            "label": "同一保單年度第 1 至 70 次",
            "amount": 1_000 if early_schedule else 500,
            "min_quantity": 1,
            "max_quantity": 70,
        }
    ]
    assert entries["cancer-inpatient-surgery-benefit"][
        "amount"
    ] == (30_000 if early_schedule else 15_000)
    assert entries["cancer-death-benefit"].get(
        "exclusion_state_key"
    ) == ("minor_death_benefit_status" if early_schedule else None)
    assert entries["cancer-death-benefit"].get(
        "exclusion_values"
    ) == (["not_effective"] if early_schedule else None)


base_document = source_document("203327M11A00200")
assert (
    parse_prudential_group_cancer_fixed_medical_unit(
        {**base_document, "batch_id": "tii-life-015"}
    )
    is None
)
assert (
    parse_prudential_group_cancer_fixed_medical_unit(
        {**base_document, "file_name": "203327M11A00200-F.pdf"}
    )
    is None
)
assert (
    parse_prudential_group_cancer_fixed_medical_unit(
        {**base_document, "source_document_sha256": "0" * 64}
    )
    is None
)
assert (
    parse_prudential_group_cancer_fixed_medical_unit(
        {**base_document, "text": f"{base_document['text']}\nTAMPER"}
    )
    is None
)


print(
    "TII Prudential group cancer fixed medical parser tests passed."
)
