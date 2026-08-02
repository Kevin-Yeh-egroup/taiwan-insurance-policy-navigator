from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    TAIWAN_OVERSEAS_SUDDEN_ILLNESS_MEDICAL_VERSIONS,
    complete_strict_source_document,
    parse_plan_table_with_parser,
    parse_taiwan_overseas_sudden_illness_medical_policy_state,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-008"
PARSER_ID = (
    "taiwan-overseas-sudden-illness-medical-policy-state-v1"
)


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_ROOT / product_id / f"{product_id}-A.pdf"
    )
    document = {
        "batch_id": "tii-life-008",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(TAIWAN_OVERSEAS_SUDDEN_ILLNESS_MEDICAL_VERSIONS) == 18
for (
    product_id,
    version,
) in TAIWAN_OVERSEAS_SUDDEN_ILLNESS_MEDICAL_VERSIONS.items():
    document = source_document(product_id)
    schedule = (
        parse_taiwan_overseas_sudden_illness_medical_policy_state(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_batch_id"] == "tii-life-008"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    assert characteristics["source_page_count"] == version[
        "page_count"
    ]
    assert characteristics["terms_revision"] == (
        "original"
        if revision == 0
        else f"partial_change_{revision}"
    )
    assert characteristics["post_expiry_readmission_excluded"] is (
        revision >= 9
    )
    assert characteristics["return_to_taiwan_medical_coverage"] is False
    assert characteristics["required_policy_inputs"] == [
        "reimbursement_limit",
        "overseas_medical_region_factor_percent",
    ]
    assert characteristics["region_adjustment_percent"] == {
        "north_america": 300,
        "europe_australia_new_zealand_japan": 150,
        "other_overseas_regions": 100,
    }

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "overseas-sudden-illness-inpatient-reimbursement",
        "overseas-sudden-illness-emergency-reimbursement",
        "overseas-sudden-illness-outpatient-reimbursement",
    }
    assert entries[
        "overseas-sudden-illness-inpatient-reimbursement"
    ]["limit_rate_percent"] == 100
    assert entries[
        "overseas-sudden-illness-emergency-reimbursement"
    ]["limit_rate_percent"] == 20
    outpatient = entries[
        "overseas-sudden-illness-outpatient-reimbursement"
    ]
    assert outpatient["limit_rate_percent"] == 0.5
    assert outpatient["limit_scope"] == "per_day"
    assert "不是住院日額" in outpatient["note"]
    for entry in entries.values():
        assert entry["calculation_basis"] == "reimbursement_with_cap"
        assert entry["basis"] == "policy_recorded_limit"
        assert entry["limit_rate_state_key"] == (
            "overseas_medical_region_factor_percent"
        )
        assert entry["policy_state_keys"] == [
            "reimbursement_limit",
            "overseas_medical_region_factor_percent",
        ]
        assert any("實際" in condition for condition in entry["conditions"])
        assert any("返國" in condition for condition in entry["conditions"])

    if revision in {6, 7}:
        assert document["source_text_extractor"] == "windows_ocr"
        assert characteristics["source_text_quality"] == (
            "font_encoded_visual_verified"
        )
        assert characteristics["ocr_evidence_path"].endswith(
            f"{product_id}-ocr-evidence.json"
        )
    else:
        assert characteristics["ocr_evidence_path"] is None


assert (
    TAIWAN_OVERSEAS_SUDDEN_ILLNESS_MEDICAL_VERSIONS[
        "202311RZ1A58G21A11Z10000015"
    ]["source_document_sha256"]
    == TAIWAN_OVERSEAS_SUDDEN_ILLNESS_MEDICAL_VERSIONS[
        "202311RZ1A58G21A11Z10000016"
    ]["source_document_sha256"]
)
assert (
    "202311RZ1A58G21A11Z10000015"
    != "202311RZ1A58G21A11Z10000016"
)

base_document = source_document("202311R11A58G00")
assert parse_taiwan_overseas_sudden_illness_medical_policy_state(
    {**base_document, "batch_id": "tii-life-009"}
) is None
assert parse_taiwan_overseas_sudden_illness_medical_policy_state(
    {**base_document, "file_name": "202311R11A58G00-F.pdf"}
) is None
assert parse_taiwan_overseas_sudden_illness_medical_policy_state(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_taiwan_overseas_sudden_illness_medical_policy_state(
    {**base_document, "text": f"{base_document['text']}變更"}
) is None


print(
    "TII Taiwan overseas sudden illness medical parser tests passed."
)
