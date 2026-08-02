from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS,
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_VERSIONS,
    complete_strict_source_document,
    parse_bnp_paribas_legacy_recorded_variable_life,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_PATH = ROOT / "work" / "tii-document-text" / "tii-life-173-text.json"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-173"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-173-bnp-legacy-recorded-variable-life-v212.json"
)
PARSER_ID = "bnp-paribas-legacy-recorded-variable-life-v1"


payload = json.loads(TEXT_PATH.read_text(encoding="utf-8"))
source_documents = {
    document["product_id"]: document
    for document in payload["documents"]
    if document["product_id"]
    in BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS
    and document["file_name"].lower()
    == f"{document['product_id'].lower()}-a.pdf"
}
assert set(source_documents) == (
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS
)


def completed_document(product_id: str) -> dict:
    source = source_documents[product_id]
    source_path = DOCUMENTS_DIR / product_id / source["file_name"]
    document = {
        **source,
        "batch_id": "tii-life-173",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


schedules: dict[str, dict] = {}
for product_id in sorted(
    BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_PRODUCT_IDS
):
    document = completed_document(product_id)
    version_contract = (
        BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_VERSIONS[product_id]
    )
    schedule = parse_bnp_paribas_legacy_recorded_variable_life(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(
        document,
        parser_id_filter=PARSER_ID,
    )
    assert integrated == (PARSER_ID, schedule)
    validate_plan_options(schedule, f"tii-life-173/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert (
        version["source_document_sha256"]
        == version_contract["source_document_sha256"]
    )
    assert (
        version["source_text_sha256"]
        == version_contract["normalized_text_sha256"]
    )
    assert version["source_page_count"] == version_contract["page_count"]
    assert (
        version["source_text_extractor"]
        == version_contract["source_text_extractor"]
    )
    assert version["terms_revision"] == version_contract["terms_revision"]

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    if version_contract["formula_variant"] == "paid_premium_factor":
        assert schedule["selection_type"] == "paid_premium_factor_plan"
        assert [option["value"] for option in schedule["plan_options"]] == [
            "甲型",
            "乙型",
        ]
        assert set(entries) == {
            "maturity-benefit",
            "death-or-funeral-benefit",
            "total-disability-benefit",
        }
        assert {
            entries["death-or-funeral-benefit"]["calculation_basis"],
            entries["total-disability-benefit"]["calculation_basis"],
        } == {"paid_premium_factor_account_value_formula"}
    else:
        assert schedule["selection_type"] == "policy_state"
        assert schedule.get("plan_options") in (None, [])
        assert set(entries) == {
            "maturity-benefit",
            "death-or-funeral-benefit",
            "total-disability-benefit",
            "value-added-benefit",
        }
        assert (
            entries["value-added-benefit"]["calculation_basis"]
            == "installment_premium_value_addition"
        )
    schedules[product_id] = schedule


base_id = "267191M31A00900"
base_document = completed_document(base_id)
negative_mutations = [
    {"batch_id": "tii-life-172"},
    {"product_id": "267191M31A00999"},
    {"file_name": "wrong.pdf"},
    {"document_type": "product_summary"},
    {"source_document_sha256": "0" * 64},
    {"source_text_extractor": "pymupdf"},
    {"page_count": base_document["page_count"] + 1},
    {"text": f"{base_document['text']}不屬於本版本"},
]
for mutation in negative_mutations:
    invalid = {**base_document, **mutation}
    assert (
        parse_bnp_paribas_legacy_recorded_variable_life(invalid) is None
    ), mutation

shared_ids = [
    "267191M31A01900",
    "267191M31A01901",
    "267191M31A01902",
]
assert len(
    {
        BNP_PARIBAS_LEGACY_RECORDED_VARIABLE_LIFE_VERSIONS[product_id][
            "source_document_sha256"
        ]
        for product_id in shared_ids
    }
) == 1
assert {
    schedules[product_id]["version_characteristics"]["source_product_id"]
    for product_id in shared_ids
} == set(shared_ids)

wrong_source_identity = copy.deepcopy(schedules[base_id])
wrong_source_identity["version_characteristics"]["source_product_id"] = (
    "267191M31A00901"
)
try:
    validate_plan_options(
        wrong_source_identity,
        "negative/tii-life-173/source-product-id",
    )
except SystemExit as error:
    assert "version contract is invalid" in str(error)
else:
    raise AssertionError("validator accepted a mismatched source product")

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == "tii-life-173"
assert proposal_payload["proposal_count"] == 24
assert proposal_payload["proposed_count"] == 24
assert proposal_payload["manual_review_count"] == 0
for proposal in proposal_payload["proposals"]:
    product_id = proposal["product_id"]
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_file"].lower() == f"{product_id.lower()}-a.pdf"
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-173",
        "product_count": len(schedules),
        "promoted_count": 0,
    }
)
