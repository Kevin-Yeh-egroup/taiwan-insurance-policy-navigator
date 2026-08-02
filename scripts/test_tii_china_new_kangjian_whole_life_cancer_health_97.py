from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    CHINA_NEW_KANGJIAN_WHOLE_LIFE_CANCER_HEALTH_97_VERSIONS,
    china_new_kangjian_whole_life_cancer_health_97_semantic_phase,
    complete_strict_source_document,
    parse_china_new_kangjian_whole_life_cancer_health_97_unit,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-026"
PARSER_ID = (
    "china-new-kangjian-whole-life-cancer-health-97-unit-v1"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-026-china-new-kangjian-whole-life-cancer-health-97-v273.json"
)


def source_document(product_id: str) -> dict:
    version = (
        CHINA_NEW_KANGJIAN_WHOLE_LIFE_CANCER_HEALTH_97_VERSIONS[
            product_id
        ]
    )
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / str(version["file_name"])
    )
    document = {
        "batch_id": "tii-life-026",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


schedules: dict[str, dict] = {}
for product_id, version in (
    CHINA_NEW_KANGJIAN_WHOLE_LIFE_CANCER_HEALTH_97_VERSIONS.items()
):
    document = source_document(product_id)
    schedule = (
        parse_china_new_kangjian_whole_life_cancer_health_97_unit(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID, product_id
    assert integrated[1] == schedule, product_id
    validate_plan_options(schedule, f"tii-life-026/{product_id}")

    revision = int(version["revision"])
    old_schedule = revision <= 3
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["source_text_extractor"] == (
        version["source_text_extractor"]
    )
    assert characteristics["source_text_quality"] == (
        "ocr_exact_hash"
        if version["source_text_extractor"] == "windows_ocr"
        else "machine_readable_exact_hash"
    )
    assert characteristics["semantic_phase"] == (
        china_new_kangjian_whole_life_cancer_health_97_semantic_phase(
            revision
        )
    )
    assert characteristics["maximum_unit_count"] == (
        6 if old_schedule else 12
    )
    assert characteristics["cancer_reinstatement_waiting_days"] == (
        90 if revision <= 7 else 0
    )
    assert characteristics["day_hospital_excluded"] is (
        revision >= 5
    )
    assert characteristics["medical_review_opinion_revision"] is (
        revision >= 10
    )
    assert characteristics["premium_waiver_available"] is True
    assert (
        characteristics["targeted_therapy_benefit_present"]
        is False
    )
    assert (
        characteristics["bone_marrow_lifetime_once_cap_present"]
        is False
    )
    assert characteristics["per_unit_total_cap"] == (
        2_500_000 if old_schedule else 1_250_000
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert len(entries) == 20
    assert entries["cancer-death"]["amount"] == (
        300_000 if old_schedule else 150_000
    )
    assert entries["cancer-diagnosis-in-situ"]["amount"] == (
        5_000 if old_schedule else 2_500
    )
    assert entries["cancer-diagnosis-full"]["amount"] == (
        100_000 if old_schedule else 50_000
    )
    assert (
        entries["cancer-diagnosis-specified-combined"]["amount"]
        == (130_000 if old_schedule else 65_000)
    )
    assert (
        entries["cancer-diagnosis-full"][
            "cumulative_paid_state_key"
        ]
        == "prior_cancer_diagnosis_benefit_paid_amount"
    )
    assert (
        "aggregate_limit_entry_id"
        not in entries["cancer-diagnosis-full"]
    )
    assert (
        entries["cancer-bone-marrow-transplant"][
            "quantity_state_key"
        ]
        == "china_new_kangjian_97_bone_marrow_transplant_count"
    )
    assert (
        "quantity_cap"
        not in entries["cancer-bone-marrow-transplant"]
    )
    assert entries["cancer-prosthetic-limb"]["quantity_cap"] == 4
    assert entries["cancer-denture"]["quantity_cap"] == 1
    assert (
        entries["cancer-breast-reconstruction"]["quantity_cap"]
        == 2
    )
    assert (
        entries["future-premium-waiver"]["calculation_basis"]
        == "waiver"
    )
    assert (
        entries["future-premium-waiver"]["result_kind"]
        == "non_cash_effect"
    )
    schedules[product_id] = schedule


wrong_hash = copy.deepcopy(schedules["205321M11A00200"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
try:
    validate_plan_options(
        wrong_hash,
        "negative/tii-life-026/china-new-kangjian-97",
    )
except SystemExit as error:
    assert "version formula is invalid" in str(error), str(error)
else:
    raise AssertionError(
        "formal validator accepted a wrong source hash"
    )


base_document = source_document("205321M11A00200")
assert parse_china_new_kangjian_whole_life_cancer_health_97_unit(
    {**base_document, "batch_id": "tii-life-025"}
) is None
assert parse_china_new_kangjian_whole_life_cancer_health_97_unit(
    {**base_document, "file_name": "205321M11A00200-F.pdf"}
) is None
assert parse_china_new_kangjian_whole_life_cancer_health_97_unit(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_china_new_kangjian_whole_life_cancer_health_97_unit(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "新康健終身防癌健康保險",
            "新康健終身健康保險",
            1,
        ),
    }
) is None


proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == "tii-life-026"
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v273"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == set(
    CHINA_NEW_KANGJIAN_WHOLE_LIFE_CANCER_HEALTH_97_VERSIONS
)
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        CHINA_NEW_KANGJIAN_WHOLE_LIFE_CANCER_HEALTH_97_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]


print(
    "TII China new Kangjian whole-life cancer health 97 "
    "parser tests passed."
)
