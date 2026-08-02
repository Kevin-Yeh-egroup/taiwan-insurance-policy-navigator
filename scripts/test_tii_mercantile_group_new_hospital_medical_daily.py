from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
    sha256_file,
)
from tii_mercantile_group_new_hospital_medical_daily import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    SOURCE_GAP_PRODUCT_IDS,
    VERSIONS,
    has_day_hospital_exclusion,
    has_post_expiry_exclusion,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-062"
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
PARSER_ID = "mercantile-group-new-hospital-medical-daily-face-amount-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-062-mercantile-group-new-hospital-medical-daily.json"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-062-mercantile-group-new-hospital-medical-daily-v306.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-062-mercantile-group-new-hospital-medical-daily-v306-review-packet"
    / "tii-life-062-mercantile-group-new-hospital-medical-daily-v306-review-packet.json"
)


def source_document(product_id: str) -> tuple[dict, Path]:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_ROOT / product_id / version["file_name"]
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "source_document_sha256": sha256_file(source_path),
        },
        source_path,
    )
    return document, source_path


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/mercantile-group-daily")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert matrix["product_count"] == 13
assert matrix["status_counts"] == {"readable": 12, "source_pending": 1}
assert matrix["duplicate_source_sha_groups"] == {}
assert {row["product_id"] for row in matrix["rows"]} == (
    PRODUCT_IDS | SOURCE_GAP_PRODUCT_IDS
)
gap_row = next(
    row for row in matrix["rows"] if row["product_id"] == "211317M11A00802"
)
assert gap_row == {
    "product_id": "211317M11A00802",
    "file_name": "",
    "status": "source_pending",
    "gap_reason": "missing_policy_terms_document",
}
gap_dir = DOCUMENTS_ROOT / "211317M11A00802"
assert not (gap_dir / "211317M11A00802-A.pdf").exists()
assert (gap_dir / "211317M11A00802-F.pdf").is_file()

schedules: dict[str, dict] = {}
for product_id, expected in VERSIONS.items():
    document, source_path = source_document(product_id)
    assert sha256_file(source_path) == expected["source_document_sha256"]
    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")
    schedules[product_id] = schedule

    revision = int(expected["revision"])
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["source_document_sha256"] == expected["source_document_sha256"]
    assert version["source_text_sha256"] == expected["source_text_sha256"]
    assert version["source_text_extractor"] == expected["source_text_extractor"]
    assert version["source_page_count"] == expected["page_count"]
    assert version["post_expiry_readmission_excluded"] is has_post_expiry_exclusion(revision)
    assert version["day_hospital_excluded"] is has_day_hospital_exclusion(revision)
    assert version["reimbursement_benefit"] is False
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "hospital-daily-benefit",
        "intensive-care-additional-benefit",
        "surgery-benefit",
        "discharge-recuperation-benefit",
    }
    assert entries["hospital-daily-benefit"]["quantity_cap_state_key"] == (
        "mercantile_group_daily_max_hospital_days"
    )
    assert entries["intensive-care-additional-benefit"]["amount_tiers"][-1] == {
        "label": "第 31 至 120 日",
        "multiplier": 1,
        "min_quantity": 31,
        "max_quantity": 120,
    }
    assert entries["surgery-benefit"]["multiplier_state_key"] == (
        "surgery_benefit_multiplier_decimal"
    )
    assert entries["discharge-recuperation-benefit"]["quantity_cap"] == 120

assert sum(
    version["source_text_extractor"] == "windows_ocr"
    for version in VERSIONS.values()
) == 1

base_document, _ = source_document("211313M11A00808")
assert parse_policy({**base_document, "batch_id": "tii-life-050"}) is None
assert parse_policy({**base_document, "file_name": "211313M11A00808-F.pdf"}) is None
assert parse_policy({**base_document, "source_document_sha256": "0" * 64}) is None
assert parse_policy({**base_document, "text": base_document["text"] + "錯置來源"}) is None
assert parse_policy({**base_document, "product_id": "211313M11A00908"}) is None

neighbor_path = (
    DOCUMENTS_ROOT / "211313M11A00908" / "211313M11A00908-A.pdf"
)
neighbor_document = complete_strict_source_document(
    {
        "batch_id": BATCH_ID,
        "product_id": "211313M11A00908",
        "file_name": neighbor_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(neighbor_path),
    },
    neighbor_path,
)
assert parse_policy(neighbor_document) is None

wrong_phase = copy.deepcopy(schedules["211313M11A00808"])
wrong_phase["version_characteristics"]["day_hospital_excluded"] = False
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_cap = copy.deepcopy(schedules["211317M11A00800"])
wrong_cap["coverage_entries"][0]["quantity_cap_state_key"] = (
    "hospitalization_day_limit_per_stay"
)
assert_invalid_schedule(wrong_cap, "exact entry contract is invalid")

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == "tii-plan-benefits-v306"
assert proposal["proposal_count"] == 12
assert proposal["proposed_count"] == 12
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == PRODUCT_IDS
assert all(item["status"] == "proposed" for item in proposal["proposals"])

review = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review["proposal_count"] == 12
assert review["status_counts"] == {"ready_for_human_source_review": 12}
assert len(review["items"]) == 12
assert all(
    item["review_packet_status"] == "ready_for_human_source_review"
    and item["errors"] == []
    for item in review["items"]
)

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_count": 13,
        "proposal_count": 12,
        "source_gap_count": 1,
        "windows_ocr_count": 1,
    }
)
