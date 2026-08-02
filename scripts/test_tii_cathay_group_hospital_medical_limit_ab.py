from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_plan_table_with_parser,
)
from tii_cathay_group_hospital_medical_limit_ab import (
    FAMILY_FINGERPRINT,
    PRODUCT_IDS,
    VERSIONS,
    parse_policy,
    semantic_phase,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-020"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-020-cathay-group-hospital-medical-limit-ab-v294.json"
)
PARSER_ID = "cathay-group-hospital-medical-limit-ab-v1"
ENTRY_IDS = [
    "daily-room-expense-benefit",
    "inpatient-medical-expense-benefit",
]


def source_document(product_id: str) -> tuple[dict, Path]:
    version = VERSIONS[product_id]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest(),
        },
        source_path,
    )
    return document, source_path


schedules: dict[str, dict] = {}
for product_id in sorted(PRODUCT_IDS):
    expected = VERSIONS[product_id]
    document, source_path = source_document(product_id)
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == (
        expected["source_document_sha256"]
    )
    assert document["source_text_extractor"] == (
        expected["source_text_extractor"]
    )
    schedule = parse_policy(document)
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    revision = int(expected["revision"])
    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["source_document_sha256"] == (
        expected["source_document_sha256"]
    )
    assert version["source_text_sha256"] == expected["source_text_sha256"]
    assert version["semantic_phase"] == semantic_phase(revision)
    assert version["newborn_screening_exception_count"] == (
        0 if revision < 4 else 11 if revision < 8 else 21
    )
    assert version["designated_physician_expense_included"] is (
        revision <= 2
    )
    assert version["post_expiry_readmission_excluded"] is (
        revision >= 5
    )
    assert version["day_hospital_excluded"] is (revision >= 6)
    assert version["premium_notice_multichannel"] is (revision >= 11)
    assert version["day_stay_day_care_wording"] is (revision >= 12)
    assert schedule["selection_type"] == "plan"
    assert [x["value"] for x in schedule["plan_options"]] == ["A", "B"]
    for option in schedule["plan_options"]:
        assert [
            entry["id"] for entry in option["coverage_entries"]
        ] == ENTRY_IDS
    schedules[product_id] = schedule


assert VERSIONS["204317R11AMAA02"]["source_text_extractor"] == "windows_ocr"

revision0 = schedules["204317R11AMAA00"]
wrong_schedule = copy.deepcopy(revision0)
wrong_schedule["plan_options"][0]["coverage_entries"][0][
    "rate_percent"
] = 70
try:
    validate_plan_options(wrong_schedule, "negative/cathay-group-limit")
except SystemExit as error:
    assert "exact entry contract is invalid" in str(error), str(error)
else:
    raise AssertionError("formal validator accepted an altered rate")

wrong_source, _ = source_document("204317R11AMAA00")
wrong_source["source_document_sha256"] = "0" * 64
assert parse_policy(wrong_source) is None

quanyi_id = "204317R11AWAA00"
quanyi_path = DOCUMENTS_DIR / quanyi_id / f"{quanyi_id}-A.pdf"
assert parse_policy(
    {
        "batch_id": BATCH_ID,
        "product_id": quanyi_id,
        "file_name": quanyi_path.name,
        "document_type": "policy_terms",
        "text": "國泰人壽團體全意住院醫療限額給付健康保險附約",
        "source_document_sha256": hashlib.sha256(
            quanyi_path.read_bytes()
        ).hexdigest(),
    }
) is None

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["batch_id"] == BATCH_ID
assert proposal["extractor_version"] == "tii-plan-benefits-v294"
assert proposal["proposal_count"] == 13
assert proposal["proposed_count"] == 13
assert proposal["manual_review_count"] == 0
assert {item["product_id"] for item in proposal["proposals"]} == PRODUCT_IDS
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    expected = VERSIONS[item["product_id"]]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        expected["source_document_sha256"]
    )

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "semantic_phase_count": len(
            {x["version_characteristics"]["semantic_phase"] for x in schedules.values()}
        ),
        "parser_id": PARSER_ID,
    }
)
