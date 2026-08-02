from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    FARGLORY_NEW_CANCER_WHOLE_LIFE_HEALTH_99_VERSIONS,
    complete_strict_source_document,
    farglory_new_cancer_whole_life_health_99_semantic_phase,
    parse_farglory_new_cancer_whole_life_health_99_unit,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-080"
PARSER_ID = "farglory-new-cancer-whole-life-health-99-unit-v1"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-080-farglory-new-cancer-whole-life-health-99-v264.json"
)


def source_document(product_id: str) -> dict:
    version = (
        FARGLORY_NEW_CANCER_WHOLE_LIFE_HEALTH_99_VERSIONS[
            product_id
        ]
    )
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / str(version["file_name"])
    )
    document = {
        "batch_id": "tii-life-080",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


schedules: dict[str, dict] = {}
for product_id, version in (
    FARGLORY_NEW_CANCER_WHOLE_LIFE_HEALTH_99_VERSIONS.items()
):
    document = source_document(product_id)
    schedule = (
        parse_farglory_new_cancer_whole_life_health_99_unit(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID, product_id
    assert integrated[1] == schedule, product_id
    validate_plan_options(
        schedule,
        f"tii-life-080/{product_id}",
    )

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["source_text_extractor"] == "pypdf"
    assert characteristics["semantic_phase"] == (
        farglory_new_cancer_whole_life_health_99_semantic_phase(
            revision
        )
    )
    assert characteristics["cancer_reinstatement_waiting_days"] == (
        90 if revision <= 6 else 0
    )
    assert characteristics["cancer_classification"] == (
        "legacy-in-situ-stage-one-prostate-other"
        if revision <= 8
        else "standardized-initial-mild-severe"
    )
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["no_death_benefit"] is True
    assert characteristics["maturity_benefit_present"] is False
    assert characteristics["per_unit_total_cap"] == 1_800_000

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    assert len(entries) == 13
    assert entries["cancer-diagnosis-reduced"]["amount"] == 15_000
    assert entries["cancer-diagnosis-full"]["amount"] == 100_000
    assert entries["cancer-hospital-daily"]["amount"] == 1_200
    assert entries["cancer-hospital-auxiliary"]["amount"] == 600
    assert entries["cancer-inpatient-surgery"]["amount"] == 30_000
    assert entries["cancer-outpatient-surgery"]["amount"] == 4_500
    assert (
        entries["cancer-bone-marrow-transplant"]["amount"]
        == 60_000
    )
    assert entries["cancer-outpatient-medical"]["amount"] == 600
    assert entries["cancer-radiochemotherapy"]["amount"] == 1_000
    assert (
        entries["cancer-breast-reconstruction"]["amount"]
        == 60_000
    )
    assert entries["cancer-prosthetic-limb"]["amount"] == 100_000
    assert (
        entries["cancer-lifetime-benefit-cap"]["amount"]
        == 1_800_000
    )
    assert "premium-waiver" not in entries
    schedules[product_id] = schedule


wrong_hash = copy.deepcopy(schedules["216321R11A11600"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
try:
    validate_plan_options(
        wrong_hash,
        "negative/tii-life-080/farglory-new-cancer-99",
    )
except SystemExit as error:
    assert "version formula is invalid" in str(error), str(error)
else:
    raise AssertionError(
        "formal validator accepted a wrong source hash"
    )


base_document = source_document("216321R11A11600")
assert parse_farglory_new_cancer_whole_life_health_99_unit(
    {**base_document, "batch_id": "tii-life-079"}
) is None
assert parse_farglory_new_cancer_whole_life_health_99_unit(
    {**base_document, "file_name": "216321R11A11600-F.pdf"}
) is None
assert parse_farglory_new_cancer_whole_life_health_99_unit(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_farglory_new_cancer_whole_life_health_99_unit(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "新台幣拾萬元",
            "新台幣玖萬元",
            1,
        ),
    }
) is None

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == "tii-life-080"
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v264"
)
assert proposal_payload["proposal_count"] == 15
assert proposal_payload["proposed_count"] == 15
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == set(FARGLORY_NEW_CANCER_WHOLE_LIFE_HEALTH_99_VERSIONS)
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        FARGLORY_NEW_CANCER_WHOLE_LIFE_HEALTH_99_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]


print(
    "TII Farglory new cancer whole-life health 99 "
    "parser tests passed."
)
