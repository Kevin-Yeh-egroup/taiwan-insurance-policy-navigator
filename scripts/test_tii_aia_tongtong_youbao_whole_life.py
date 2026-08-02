from __future__ import annotations

from pathlib import Path

from extract_tii_plan_benefits import (
    AIA_TONGTONG_YOUBAO_VERSIONS,
    EXTRACTOR_VERSION,
    aia_tongtong_youbao_semantic_phase,
    complete_strict_source_document,
    parse_aia_tongtong_youbao_unit,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-140"
PARSER_ID = "aia-tongtong-youbao-whole-life-unit-v1"


def source_document(product_id: str) -> dict:
    version = AIA_TONGTONG_YOUBAO_VERSIONS[product_id]
    source_path = DOCUMENTS_ROOT / product_id / version["file_name"]
    document = {
        "batch_id": "tii-life-140",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert EXTRACTOR_VERSION == "tii-plan-benefits-v255"
assert len(AIA_TONGTONG_YOUBAO_VERSIONS) == 16

for product_id, version in AIA_TONGTONG_YOUBAO_VERSIONS.items():
    document = source_document(product_id)
    assert document["source_text_extractor"] == version[
        "source_text_extractor"
    ]
    schedule = parse_aia_tongtong_youbao_unit(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(
        document, parser_id_filter=PARSER_ID
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-140:{product_id}")

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert schedule["selection_type"] == "unit"
    assert schedule["input_mode"] == "unit"
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == version[
        "source_document_sha256"
    ]
    assert characteristics["source_text_sha256"] == version[
        "source_text_sha256"
    ]
    assert characteristics["source_page_count"] == version["page_count"]
    assert characteristics["semantic_phase"] == (
        aia_tongtong_youbao_semantic_phase(revision)
    )
    assert characteristics["care_term"] == (
        "長期看護" if revision <= 6 else "長期照顧"
    )
    assert characteristics["disability_term"] == (
        "殘廢" if revision <= 11 else "失能"
    )
    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert len(entries) == 14
    assert entries["hospital-medical-benefit"]["amount"] == 1000
    assert entries["hospital-medical-benefit"]["quantity_cap"] == 90
    assert entries["surgery-medical-benefit"][
        "multiplier_state_key"
    ] == "surgery_benefit_multiplier_decimal"
    assert entries["disease-death-benefit"]["calculation_basis"] == (
        "death_or_funeral_greater_of_per_unit_floor_and_paid_premium_net"
    )
    assert entries["future-premium-waiver"]["result_kind"] == (
        "non_cash_effect"
    )

duplicate_a = AIA_TONGTONG_YOUBAO_VERSIONS["257391M12G00105"]
duplicate_b = AIA_TONGTONG_YOUBAO_VERSIONS["257391M11G00106"]
assert (
    duplicate_a["source_document_sha256"]
    == duplicate_b["source_document_sha256"]
)

base_document = source_document("257391M12G00100")
assert (
    parse_aia_tongtong_youbao_unit(
        {**base_document, "batch_id": "tii-life-141"}
    )
    is None
)
assert (
    parse_aia_tongtong_youbao_unit(
        {**base_document, "source_document_sha256": "0" * 64}
    )
    is None
)
assert (
    parse_aia_tongtong_youbao_unit(
        {**base_document, "text": f"{base_document['text']}\nTAMPER"}
    )
    is None
)

print("TII AIA Tongtong Youbao whole-life parser tests passed.")
