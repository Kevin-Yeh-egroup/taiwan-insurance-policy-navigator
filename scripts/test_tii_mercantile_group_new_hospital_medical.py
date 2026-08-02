from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
    sha256_file,
)
from tii_mercantile_group_new_hospital_medical import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    has_day_hospital_exclusion,
    has_post_expiry_exclusion,
    parse_policy,
    semantic_phase,
    uses_policy_recorded_limits,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-062"
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / BATCH_ID
PARSER_ID = "mercantile-group-new-hospital-medical-exact-v1"
MATRIX_PATH = (
    ROOT
    / "work"
    / "tii-benefit-source-matrices"
    / "tii-life-062-mercantile-group-new-hospital-medical.json"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-062-mercantile-group-new-hospital-medical-v305.json"
)
REVIEW_PACKET_PATH = (
    ROOT
    / "work"
    / "tii-benefit-review-packets"
    / "tii-life-062-mercantile-group-new-hospital-medical-v305-review-packet"
    / "tii-life-062-mercantile-group-new-hospital-medical-v305-review-packet.json"
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
        validate_plan_options(schedule, "negative/mercantile-group-new-hospital")
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError("strict validator accepted an invalid schedule")


matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
assert matrix["family_fingerprint"] == FAMILY_FINGERPRINT
assert matrix["product_count"] == 13
assert matrix["status_counts"] == {"readable": 13}
assert {row["product_id"] for row in matrix["rows"]} == PRODUCT_IDS
assert matrix["duplicate_source_sha_groups"] == {
    "642e5eb6edbe88aa1821fec5ee73e0b073489f668fc4b21be7495586057f00c3": [
        "211313MZ1A00921A11Z10000010",
        "211313MZ1A00921A11Z10000011",
    ]
}

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
    assert version["post_discharge_radiotherapy_expense_days"] == (90 if revision <= 1 else 0)
    assert version["non_nhi_payment_rate_percent"] == 66
    assert version["hospital_day_limit_per_stay"] == 120

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "daily-room-expense-reimbursement",
        "inpatient-medical-expense-reimbursement",
        "inpatient-surgery-expense-reimbursement",
        "hospital-daily-cash-alternative",
    }
    assert entries["inpatient-medical-expense-reimbursement"]["limit_proration_threshold"] == 30
    assert entries["inpatient-surgery-expense-reimbursement"]["rate_max_percent"] == 500
    if uses_policy_recorded_limits(revision):
        assert schedule["selection_type"] == "policy_state"
        assert schedule["plan_options"] == []
        assert version["policy_recorded_limits_required"] is True
    else:
        assert schedule["selection_type"] == "unit"
        assert "plan_options" not in schedule
        assert version["insured_amount_unit_twd"] == 100
        assert entries["daily-room-expense-reimbursement"]["amount"] == 100
        assert entries["inpatient-medical-expense-reimbursement"]["amount"] == 3_000
        assert entries["inpatient-surgery-expense-reimbursement"]["amount"] == 4_000

assert sum(
    version["source_text_extractor"] == "windows_ocr"
    for version in VERSIONS.values()
) == 1

base_document, _ = source_document("211313M11A00908")
assert parse_policy({**base_document, "batch_id": "tii-life-050"}) is None
assert parse_policy({**base_document, "file_name": "211313M11A00908-F.pdf"}) is None
assert parse_policy({**base_document, "source_document_sha256": "0" * 64}) is None
assert parse_policy({**base_document, "text": base_document["text"] + "跨商品補值"}) is None
assert parse_policy({**base_document, "product_id": "211311R11A00709"}) is None

neighbor_path = (
    ROOT
    / "work"
    / "tii-documents"
    / BATCH_ID
    / "211311R11A00709"
    / "211311R11A00709-A.pdf"
)
neighbor_document = complete_strict_source_document(
    {
        "batch_id": BATCH_ID,
        "product_id": "211311R11A00709",
        "file_name": neighbor_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(neighbor_path),
    },
    neighbor_path,
)
assert parse_policy(neighbor_document) is None

wrong_phase = copy.deepcopy(schedules["211313M11A00908"])
wrong_phase["version_characteristics"]["post_expiry_readmission_excluded"] = False
assert_invalid_schedule(wrong_phase, "source or version boundary is invalid")

wrong_source = copy.deepcopy(schedules["211313M11A00907"])
wrong_source["version_characteristics"]["family_fingerprint"] = "8bc99ce40a87d65117a5a397"
assert_invalid_schedule(wrong_source, "source or version boundary is invalid")

wrong_amount = copy.deepcopy(schedules["211317M11A00902"])
for entry in wrong_amount["coverage_entries"]:
    if entry["id"] == "inpatient-surgery-expense-reimbursement":
        entry["amount"] = 5_000
assert_invalid_schedule(wrong_amount, "exact entry contract is invalid")

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["proposal_count"] == 13
assert proposal["proposed_count"] == 13
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == PRODUCT_IDS
assert all(item["status"] == "proposed" for item in proposal["proposals"])

review = json.loads(REVIEW_PACKET_PATH.read_text(encoding="utf-8"))
assert review["proposal_count"] == 13
assert review["status_counts"] == {"ready_for_human_source_review": 13}
assert len(review["items"]) == 13
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
        "product_count": len(schedules),
        "source_gap_count": 0,
        "windows_ocr_count": 1,
    }
)
