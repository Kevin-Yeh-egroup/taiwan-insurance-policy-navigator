from __future__ import annotations

import copy
from pathlib import Path

from extract_tii_plan_benefits import (
    FARGLORY_XIONG_HEALTH_SURGERY_MEDICAL_VERSIONS,
    complete_strict_source_document,
    parse_farglory_xiong_health_surgery_medical_unit,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-080"
PARSER_ID = "farglory-xiong-health-surgery-medical-unit-v1"


def source_document(product_id: str) -> dict:
    source_path = DOCUMENTS_ROOT / product_id / f"{product_id}-A.pdf"
    document = {
        "batch_id": "tii-life-080",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


assert len(FARGLORY_XIONG_HEALTH_SURGERY_MEDICAL_VERSIONS) == 14
verified_schedules: dict[str, dict] = {}
for product_id, version in (
    FARGLORY_XIONG_HEALTH_SURGERY_MEDICAL_VERSIONS.items()
):
    document = source_document(product_id)
    schedule = parse_farglory_xiong_health_surgery_medical_unit(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(
        schedule,
        f"test/tii-life-080/{product_id}",
    )
    verified_schedules[product_id] = schedule

    revision = version["revision"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_batch_id"] == "tii-life-080"
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
        "original" if revision == 0 else f"partial_change_{revision}"
    )
    assert characteristics["inpatient_unit_factor"] == 25
    assert characteristics["outpatient_unit_factor"] == 100
    assert characteristics["lifetime_cap_per_unit"] == 50000
    assert characteristics["surgery_table_multiplier_min"] == 1
    assert characteristics["surgery_table_multiplier_max"] == 100
    assert characteristics["death_benefit_available"] is False
    assert characteristics["maturity_benefit_available"] is False
    assert (
        characteristics["premium_waiver_cash_benefit_available"]
        is False
    )

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == {
        "inpatient-surgery-medical-benefit",
        "outpatient-surgery-medical-benefit",
        "remaining-lifetime-surgery-medical-cap",
    }
    assert entries["inpatient-surgery-medical-benefit"]["amount"] == 25
    assert entries["outpatient-surgery-medical-benefit"]["amount"] == 100
    for entry_id in (
        "inpatient-surgery-medical-benefit",
        "outpatient-surgery-medical-benefit",
    ):
        assert entries[entry_id]["calculation_basis"] == "table_multiplier"
        assert entries[entry_id]["multiplier_state_key"] == (
            "surgery_benefit_multiplier"
        )
        assert entries[entry_id]["aggregate_limit_entry_id"] == (
            "remaining-lifetime-surgery-medical-cap"
        )
        assert entries[entry_id]["cumulative_paid_state_key"] == (
            "cumulative_surgery_benefit_paid_amount"
        )


invalid_schedule = copy.deepcopy(verified_schedules["216311R11A07200"])
invalid_schedule["coverage_entries"][0]["amount"] = 26
try:
    validate_plan_options(
        invalid_schedule,
        "negative/tii-life-080/216311R11A07200",
    )
except SystemExit as error:
    assert "coverage exact entry contract is invalid" in str(error), str(error)
else:
    raise AssertionError("strict validator accepted a changed inpatient factor")


base_document = source_document("216311R11A07200")
assert parse_farglory_xiong_health_surgery_medical_unit(
    {**base_document, "batch_id": "tii-life-081"}
) is None
assert parse_farglory_xiong_health_surgery_medical_unit(
    {**base_document, "file_name": "216311R11A07200-F.pdf"}
) is None
assert parse_farglory_xiong_health_surgery_medical_unit(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_xiong_health_surgery_medical_unit(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "再乘以二十五",
            "再乘以二十六",
            1,
        ),
    }
) is None

cross_family_path = (
    DOCUMENTS_ROOT
    / "216351R11A09700"
    / "216351R11A09700-A.pdf"
)
cross_family_document = complete_strict_source_document(
    {
        "batch_id": "tii-life-080",
        "product_id": "216351R11A09700",
        "file_name": cross_family_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(cross_family_path),
    },
    cross_family_path,
)
assert parse_farglory_xiong_health_surgery_medical_unit(
    cross_family_document
) is None


print(
    {
        "status": "ok",
        "batch_id": "tii-life-080",
        "product_count": len(
            FARGLORY_XIONG_HEALTH_SURGERY_MEDICAL_VERSIONS
        ),
        "semantic_phases": [
            "constant_unit_multiplier_benefit_model"
        ],
        "cross_family_isolated": "216351R11A09700",
    }
)
