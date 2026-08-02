from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    FUBON_ANXIN_100_CRITICAL_ILLNESS_PLAN_PRODUCT_IDS,
    FUBON_ANXIN_100_CRITICAL_ILLNESS_PLAN_REVISIONS,
    complete_strict_source_document,
    parse_fubon_anxin_100_critical_illness_plan,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-050"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-anxin-100-critical-plan-v214.json"
)
PARSER_ID = "fubon-anxin-100-critical-illness-plan-v1"
EXPECTED_SOURCE_SHA256 = {
    "209391R12B00100": "2e664c5bc65e289864ef9e7eaf9571b4a62b60f54021dc21c7902c784bf263a2",
    "209391R15B00101": "3295abb49131ea9312b5dd14f21d782d160d07932b34e73b059c840b7d8b5126",
    "209351RZ5B00121A11Z10000002": "9276c8538723733fe5b5602443b55d6fa043b0849db24e1e3848eb7c33990a66",
    "209351RZ5B00121A11Z10000003": "435fc86bc6aef68e146fac86e4f963de978df236ccd8415ab2bd59285224f118",
    "209351RZ5B00121A11Z10000004": "a50e99720dd74a26b347495df2b47010e6ed27b2e2b5f4c8354d49c72b07f788",
    "209351RZ5B00121A11Z10000005": "193c55a15c374a2234041c5adf26f0fe241d18bd074e1d5b7d9aa0181111c4c9",
    "209351RZ5B00121A11Z10000006": "0a4e84d51451a9448fa4856cd43b9cdce8d033f0be6f966b6ad8255ad783f354",
    "209351RZ5B00121A11Z10000007": "8a0b5365453195428f30bb18376ccb32eceedd8da19b24885a8bd7e33ab81986",
    "209351RZ5B00121A11Z10000008": "360caab902bfdd3501177a649bb2094437153e11ea5181d049775d2645848ba2",
    "209351RZ5B00121A11Z10000009": "345836a7fd110ca9e18d4dd70d30a0d458c61e8fa489814b98e360630c15cb03",
    "209351RZ5B00121A11Z10000010": "f52b34be872c73821b0bde54aa5d4494c532556fa8dce675024ae5144d7a2c2f",
    "209351RZ5B00121A11Z10000011": "415bae88dc2735d4156fbd5e1a522d9d4a2f17d8d32d5a9e04865366ab189b87",
}
EXPECTED_PLAN_AMOUNTS = {
    "plan-1": 300_000,
    "plan-2": 500_000,
    "plan-3": 1_000_000,
}


def source_document(product_id: str) -> dict:
    source_path = DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-050",
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
        },
        source_path,
    )


schedules: dict[str, dict] = {}
for product_id in sorted(
    FUBON_ANXIN_100_CRITICAL_ILLNESS_PLAN_PRODUCT_IDS
):
    revision = FUBON_ANXIN_100_CRITICAL_ILLNESS_PLAN_REVISIONS[
        product_id
    ]
    source_path = DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == EXPECTED_SOURCE_SHA256[product_id]
    )
    document = source_document(product_id)
    assert document["page_count"] == 9
    assert document["pages_parsed"] == 9
    schedule = parse_fubon_anxin_100_critical_illness_plan(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"tii-life-050/{product_id}")

    version = schedule["version_characteristics"]
    disability_term = "完全失能" if revision >= 6 else "完全殘廢"
    assert schedule["selection_type"] == "plan"
    assert schedule["input_mode"] == "plan"
    assert schedule["selection_source"] == "terms"
    assert "unit_fields" not in schedule
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == (
        "original" if revision == 0 else f"partial_change_{revision}"
    )
    assert version["plan_count"] == 3
    assert version["plan_amounts"] == {
        "計畫一": 300_000,
        "計畫二": 500_000,
        "計畫三": 1_000_000,
    }
    assert version["critical_disease_waiting_days"] == (
        30 if revision <= 4 else 0
    )
    assert (
        version["accidental_waiting_exception"]
        is (revision <= 4)
    )
    assert version["critical_disease_definition_revision"] == (
        "standardized_severe_seven_major_diseases"
        if revision >= 3
        else "legacy_seven_major_diseases"
    )
    assert version["disability_term"] == disability_term
    assert version["funeral_status_rule_revision"] == (
        "mental_capacity_definition"
        if revision <= 5
        else "guardianship_declaration"
    )
    assert version["benefits_mutually_exclusive"] is True
    assert version["contract_terminates_after_benefit"] is True

    assert [plan["value"] for plan in schedule["plan_options"]] == [
        "plan-1",
        "plan-2",
        "plan-3",
    ]
    for plan in schedule["plan_options"]:
        entries = {
            entry["id"]: entry
            for entry in plan["coverage_entries"]
        }
        amount = EXPECTED_PLAN_AMOUNTS[plan["value"]]
        assert set(entries) == {
            "death-or-funeral-benefit",
            "complete-disability-benefit",
            "critical-disease-benefit",
        }
        assert {entry["amount"] for entry in entries.values()} == {
            amount
        }
        assert {
            entry["aggregation_rule"]
            for entry in entries.values()
        } == {"choose_one"}
        assert {
            entry["benefit_group_id"]
            for entry in entries.values()
        } == {"fubon-anxin-100-terminal-benefit"}
        assert [
            entries["death-or-funeral-benefit"]["event_key"],
            entries["complete-disability-benefit"]["event_key"],
            entries["critical-disease-benefit"]["event_key"],
        ] == [
            "death_or_funeral",
            "complete_disability",
            "critical_disease",
        ]
        assert (
            entries["death-or-funeral-benefit"][
                "calculation_basis"
            ]
            == "death_or_funeral_fixed_amount"
        )
        assert (
            entries["complete-disability-benefit"]["name"]
            == f"{disability_term}保險金"
        )
        assert all(
            "附表一計畫別保險金額表，第 7 頁"
            in entry["source_ref"]
            for entry in entries.values()
        )
    schedules[product_id] = schedule

reference_document = source_document("209391R12B00100")
wrong_batch = {
    **reference_document,
    "batch_id": "tii-life-049",
}
assert parse_fubon_anxin_100_critical_illness_plan(wrong_batch) is None
wrong_file = {
    **reference_document,
    "file_name": "209391R12B00100-B.pdf",
}
assert parse_fubon_anxin_100_critical_illness_plan(wrong_file) is None
wrong_page_count = {
    **reference_document,
    "page_count": 8,
}
assert (
    parse_fubon_anxin_100_critical_illness_plan(
        wrong_page_count
    )
    is None
)
corrupted_table = copy.deepcopy(reference_document)
corrupted_table["text"] = (
    corrupted_table["text"]
    .replace("100 萬", "99 萬")
    .replace("100萬", "99萬")
)
assert (
    parse_fubon_anxin_100_critical_illness_plan(
        corrupted_table
    )
    is None
)

proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal["extractor_version"] == "tii-plan-benefits-v214"
assert proposal["batch_id"] == "tii-life-050"
assert proposal["proposal_count"] == 12
assert proposal["proposed_count"] == 12
assert proposal["manual_review_count"] == 0
assert {
    item["product_id"] for item in proposal["proposals"]
} == FUBON_ANXIN_100_CRITICAL_ILLNESS_PLAN_PRODUCT_IDS
for item in proposal["proposals"]:
    assert item["status"] == "proposed"
    assert item["candidate_count"] == 1
    candidate = item["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert (
        candidate["source_document_sha256"]
        == EXPECTED_SOURCE_SHA256[item["product_id"]]
    )
    assert candidate["schedule"] == schedules[item["product_id"]]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-050",
        "product_count": len(schedules),
        "plan_count": 3,
        "coverage_entry_count": len(schedules) * 3 * 3,
    }
)
