from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    HONGTAI_XIANGHAOKANG_WHOLE_LIFE_MEDICAL_VERSIONS,
    complete_strict_source_document,
    hongtai_xianghaokang_semantic_phase,
    parse_hongtai_xianghaokang_whole_life_medical_face_amount,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-086"
PARSER_ID = (
    "hongtai-xianghaokang-whole-life-medical-face-amount-v1"
)


def source_document(product_id: str) -> dict:
    version = HONGTAI_XIANGHAOKANG_WHOLE_LIFE_MEDICAL_VERSIONS[
        product_id
    ]
    source_path = (
        DOCUMENTS_ROOT / product_id / version["file_name"]
    )
    document = {
        "batch_id": "tii-life-086",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert (
    len(HONGTAI_XIANGHAOKANG_WHOLE_LIFE_MEDICAL_VERSIONS)
    == 17
)
for product_id, version in (
    HONGTAI_XIANGHAOKANG_WHOLE_LIFE_MEDICAL_VERSIONS.items()
):
    document = source_document(product_id)
    assert (
        document["source_text_extractor"]
        == version["source_text_extractor"]
    )
    schedule = (
        parse_hongtai_xianghaokang_whole_life_medical_face_amount(
            document
        )
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-086:{product_id}")

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-086"
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
        hongtai_xianghaokang_semantic_phase(revision)
    )
    assert characteristics[
        "emergency_observation_benefit_present"
    ] is (revision <= 7)
    assert characteristics[
        "newborn_screening_waiting_exception"
    ] is (revision >= 6)
    assert characteristics[
        "post_expiry_continuing_hospitalization"
    ] is (revision >= 7)
    assert characteristics["contract_expiry_age"] == (
        111 if revision >= 14 else 110
    )
    assert characteristics["death_cash_benefit_present"] is False
    assert characteristics["maturity_cash_benefit_present"] is False
    assert characteristics["premium_waiver_benefit_present"] is False
    assert characteristics["no_claim_bonus_present"] is False
    assert characteristics["value_add_benefit_present"] is False

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert len(entries) == (7 if revision <= 7 else 6)
    assert ("emergency-observation-benefit" in entries) is (
        revision <= 7
    )
    assert entries["hospital-daily-benefit"][
        "quantity_state_key"
    ] == "hospitalization_days"
    assert entries["outpatient-surgery-benefit"]["multiplier"] == 3
    assert entries["inpatient-surgery-benefit"]["multiplier"] == 10
    assert entries["major-surgery-benefit"]["multiplier"] == 40
    assert entries["trauma-treatment-benefit"][
        "rate_percent"
    ] == 50
    assert entries["remaining-lifetime-medical-benefit-cap"][
        "cumulative_paid_multiplier_state_key"
    ] == "cumulative_medical_benefit_paid_multiplier"


base_document = source_document("217311M11A00400")
assert (
    parse_hongtai_xianghaokang_whole_life_medical_face_amount(
        {**base_document, "batch_id": "tii-life-087"}
    )
    is None
)
assert (
    parse_hongtai_xianghaokang_whole_life_medical_face_amount(
        {**base_document, "file_name": "217311M11A00400-F.pdf"}
    )
    is None
)
assert (
    parse_hongtai_xianghaokang_whole_life_medical_face_amount(
        {**base_document, "source_document_sha256": "0" * 64}
    )
    is None
)
assert (
    parse_hongtai_xianghaokang_whole_life_medical_face_amount(
        {
            **base_document,
            "text": f"{base_document['text']}\nTAMPER",
        }
    )
    is None
)


print(
    "TII Hongtai Xianghaokang whole-life medical parser tests passed."
)
