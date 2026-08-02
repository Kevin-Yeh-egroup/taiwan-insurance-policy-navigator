from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    complete_strict_source_document,
    parse_cathay_group_foreign_student_health_fixed_schedule,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
TEXT_FIXTURE = json.loads(
    (ROOT / "work" / "tii-document-text" / "tii-life-020-text.json").read_text(
        encoding="utf-8"
    )
)["documents"]
DOCUMENT_ROOT = ROOT / "work" / "tii-documents" / "tii-life-020"


PRODUCT_IDS = [
    "204313M11AK0000",
    "204313M11AK0001",
    "204313M11AK0002",
    "204313M11AK0003",
    "204313MZ1AK0021A11Z10000004",
]

EXPECTED_VERSION_CHARACTERISTICS = {
    "204313M11AK0000": {
        "terms_revision": "100-original",
        "designated_physician_expense_included": True,
        "post_expiry_readmission_excluded": False,
        "hospital_definition_revision": "public-private-and-foundation-hospitals",
        "day_hospital_excluded": False,
    },
    "204313M11AK0001": {
        "terms_revision": "101-approved",
        "designated_physician_expense_included": False,
        "post_expiry_readmission_excluded": False,
        "hospital_definition_revision": "public-private-and-foundation-hospitals",
        "day_hospital_excluded": False,
    },
    "204313M11AK0002": {
        "terms_revision": "102-revised",
        "designated_physician_expense_included": False,
        "post_expiry_readmission_excluded": True,
        "hospital_definition_revision": "public-private-and-foundation-hospitals",
        "day_hospital_excluded": False,
    },
    "204313M11AK0003": {
        "terms_revision": "103-revised",
        "designated_physician_expense_included": False,
        "post_expiry_readmission_excluded": True,
        "hospital_definition_revision": "public-private-and-medical-corporation-hospitals",
        "day_hospital_excluded": True,
    },
    "204313MZ1AK0021A11Z10000004": {
        "terms_revision": "104-revised",
        "designated_physician_expense_included": False,
        "post_expiry_readmission_excluded": True,
        "hospital_definition_revision": "public-private-and-medical-corporation-hospitals",
        "day_hospital_excluded": True,
    },
}


def document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    fixture = next(
        item
        for item in TEXT_FIXTURE
        if item.get("product_id") == product_id and item.get("file_name") == file_name
    )
    return {**fixture, "batch_id": "tii-life-020"}


for product_id in PRODUCT_IDS:
    source_document = document(product_id)
    schedule = parse_cathay_group_foreign_student_health_fixed_schedule(
        source_document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(source_document)
    assert integrated is not None
    assert integrated[0] == "cathay-group-foreign-student-health-fixed-schedule-v1"
    assert integrated[1] == schedule

    assert schedule["selection_type"] == "fixed"
    assert schedule["input_mode"] == "fixed"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "cathay-group-foreign-student-health"
    assert characteristics["company_group"] == "cathay_life"
    assert characteristics["fixed_schedule"] is True
    assert characteristics["outpatient_emergency_per_visit_limit"] == 1_000
    assert characteristics["daily_room_expense_limit"] == 1_000
    assert characteristics["inpatient_medical_per_hospitalization_limit"] == 120_000
    assert characteristics["non_nhi_payment_rate_percent"] == 100
    assert characteristics["same_hospital_readmission_days"] == 14
    for key, value in EXPECTED_VERSION_CHARACTERISTICS[product_id].items():
        assert characteristics[key] == value

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "outpatient-emergency-medical-limit",
        "daily-room-expense-limit",
        "inpatient-medical-expense-limit",
    }
    assert entries["outpatient-emergency-medical-limit"]["amount"] == 1_000
    assert (
        entries["outpatient-emergency-medical-limit"]["basis"]
        == "per_visit_limit"
    )
    assert entries["outpatient-emergency-medical-limit"]["limit_scope"] == "per_visit"
    assert entries["daily-room-expense-limit"]["amount"] == 1_000
    assert entries["daily-room-expense-limit"]["basis"] == "daily_limit"
    assert entries["daily-room-expense-limit"]["limit_scope"] == "per_day"
    assert entries["inpatient-medical-expense-limit"]["amount"] == 120_000
    assert (
        entries["inpatient-medical-expense-limit"]["basis"]
        == "per_hospitalization_limit"
    )
    assert (
        entries["inpatient-medical-expense-limit"]["limit_scope"]
        == "per_hospitalization"
    )
    assert all(
        entry["calculation_basis"] == "reimbursement_with_cap"
        for entry in entries.values()
    )
    assert all(entry["amount_role"] == "limit" for entry in entries.values())
    room_conditions = entries["daily-room-expense-limit"]["conditions"]
    if characteristics["post_expiry_readmission_excluded"]:
        assert any("契約有效期間屆滿後出院" in item for item in room_conditions)
    else:
        assert not any("契約有效期間屆滿後出院" in item for item in room_conditions)
    if characteristics["day_hospital_excluded"]:
        assert any("日間住院" in item and "日間留院" in item for item in room_conditions)
    else:
        assert not any("日間住院" in item for item in room_conditions)
    validate_plan_options(schedule, f"tii-life-020/{product_id}")

    source_path = DOCUMENT_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in source_document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = indexed_document["text"][:1600]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_cathay_group_foreign_student_health_fixed_schedule(completed_document)
        == schedule
    )


assert (
    parse_cathay_group_foreign_student_health_fixed_schedule(
        document("204313M11AK0000", "F")
    )
    is None
)
assert (
    parse_cathay_group_foreign_student_health_fixed_schedule(
        {**document("204313M11AK0000"), "product_id": "204357M11AQD000"}
    )
    is None
)
assert (
    parse_cathay_group_foreign_student_health_fixed_schedule(
        {**document("204313M11AK0000"), "batch_id": "tii-life-021"}
    )
    is None
)

valid_schedule = parse_cathay_group_foreign_student_health_fixed_schedule(
    document("204313M11AK0000")
)
assert valid_schedule is not None


def assert_invalid_schedule(schedule: dict, expected_error: str) -> None:
    try:
        validate_plan_options(schedule, "negative/cathay-contract")
    except SystemExit as error:
        assert expected_error in str(error)
    else:
        raise AssertionError("formal validator accepted invalid Cathay schedule")


invalid_schedule = copy.deepcopy(valid_schedule)
invalid_schedule["version_characteristics"][
    "designated_physician_expense_included"
] = False
assert_invalid_schedule(invalid_schedule, "revision characteristics are invalid")

invalid_schedule = copy.deepcopy(valid_schedule)
invalid_schedule["coverage_entries"][0]["amount"] = 999
assert_invalid_schedule(invalid_schedule, "entry is invalid")

invalid_schedule = copy.deepcopy(valid_schedule)
invalid_schedule["coverage_entries"].pop(1)
assert_invalid_schedule(invalid_schedule, "entry set is invalid")

invalid_schedule = copy.deepcopy(valid_schedule)
invalid_schedule["coverage_entries"][2]["limit_scope"] = "per_day"
assert_invalid_schedule(invalid_schedule, "entry is invalid")

print({"status": "ok", "product_count": len(PRODUCT_IDS)})
