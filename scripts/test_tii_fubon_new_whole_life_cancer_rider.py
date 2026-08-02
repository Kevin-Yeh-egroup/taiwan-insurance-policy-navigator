from __future__ import annotations

import json
from pathlib import Path

from extract_tii_plan_benefits import (
    FUBON_NEW_WHOLE_LIFE_CANCER_RIDER_NO_RESTART_WAIT_PRODUCT_IDS,
    parse_fubon_new_whole_life_cancer_rider_unit_table,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


PRODUCT_IDS = [
    "209321R11A00300",
    "209321R11A00301",
    "209321R11A00302",
    "209321R11A00303",
    "209321R11A00304",
    "209321RZ1A00123A11Z10000005",
    "209321RZ1A00123A11Z10000006",
    "209321RZ1A00123A11Z10000007",
    "209321RZ1A00123A11Z10000008",
    "209321RZ1A00123A11Z10000009",
    "209321RZ1A00123A11Z10000010",
    "209321RZ1A00123A11Z10000011",
    "209321RZ1A00123A11Z10000012",
    "209321RZ1A00123A11Z10000013",
    "209321RZ1A00123A11Z10000014",
]
MODERN_PRODUCT_IDS = set(PRODUCT_IDS[8:])
NO_RESTART_WAIT_PRODUCT_IDS = set(PRODUCT_IDS[6:])


def load_documents() -> list[dict]:
    payload_path = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    )
    return json.loads(payload_path.read_text(encoding="utf-8"))["documents"]


def main() -> None:
    documents = load_documents()
    for product_id in PRODUCT_IDS:
        document = {
            **next(
                item
                for item in documents
                if item.get("product_id") == product_id
                and item.get("file_name") == f"{product_id}-A.pdf"
            ),
            "batch_id": "tii-life-050",
        }
        schedule = parse_fubon_new_whole_life_cancer_rider_unit_table(document)
        assert schedule is not None
        integrated = parse_plan_table_with_parser(document)
        assert integrated is not None
        assert integrated[0] == "fubon-new-whole-life-cancer-rider-unit-v1"
        assert integrated[1] == schedule
        validate_plan_options(schedule, f"Fubon cancer rider {product_id}")
        assert schedule["selection_type"] == schedule["input_mode"] == "unit"
        assert schedule["selection_label"] == "投保單位數"
        expected_classification = (
            "2018-initial-mild-severe"
            if product_id in MODERN_PRODUCT_IDS
            else "legacy-specific-other"
        )
        assert schedule["version_characteristics"]["cancer_classification"] == (
            expected_classification
        )
        assert schedule["version_characteristics"]["cancer_initial_waiting_days"] == 90
        assert schedule["version_characteristics"][
            "cancer_reinstatement_waiting_days"
        ] == (0 if product_id in NO_RESTART_WAIT_PRODUCT_IDS else 90)
        assert schedule["version_characteristics"][
            "premium_waiver_requires_remaining_premium_amount"
        ] is True
        entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
        assert len(entries) == 12
        assert entries["cancer-diagnosis-early-or-specific"]["amount"] == 10_000
        assert entries["cancer-diagnosis-severe-or-other"]["amount"] == 50_000
        assert entries["cancer-inpatient-daily"]["amount"] == 1_200
        assert entries["cancer-discharge-recovery"]["amount"] == 600
        assert entries["cancer-outpatient"]["amount"] == 500
        assert entries["cancer-chemotherapy"]["amount"] == 1_000
        assert entries["cancer-radiation"]["amount"] == 1_000
        assert entries["cancer-inpatient-surgery"]["amount"] == 20_000
        assert entries["cancer-marrow-transplant"]["amount"] == 120_000
        assert entries["cancer-breast-reconstruction"]["amount"] == 20_000
        assert entries["lifetime-total-benefit-cap"]["amount"] == 1_800_000
        assert entries["lifetime-total-benefit-cap"]["amount_role"] == "limit"
        assert entries["lifetime-total-benefit-cap"]["calculation_basis"] == "per_unit"
        assert entries["premium-waiver"]["calculation_basis"] == "waiver"
        assert entries["premium-waiver"]["basis"] == "policy_premium"
        assert entries["premium-waiver"]["amount_role"] == "premium_waiver"
        assert entries["premium-waiver"]["unit_key"] == "remaining_premium_amount"
        assert "amount" not in entries["premium-waiver"]

    assert (
        FUBON_NEW_WHOLE_LIFE_CANCER_RIDER_NO_RESTART_WAIT_PRODUCT_IDS
        == NO_RESTART_WAIT_PRODUCT_IDS
    )
    invalid_waiver_schedule = json.loads(json.dumps(schedule, ensure_ascii=False))
    invalid_waiver_entry = next(
        entry
        for entry in invalid_waiver_schedule["coverage_entries"]
        if entry["id"] == "premium-waiver"
    )
    invalid_waiver_entry["unit_key"] = "wrong_state_key"
    try:
        validate_plan_options(
            invalid_waiver_schedule,
            "Fubon cancer rider invalid waiver input",
        )
    except SystemExit:
        pass
    else:
        raise AssertionError("invalid waiver state key must fail validation")

    first_document = {
        **next(
            item
            for item in documents
            if item.get("product_id") == "209321R11A00300"
            and item.get("file_name") == "209321R11A00300-A.pdf"
        ),
        "batch_id": "tii-life-050",
    }
    assert (
        parse_fubon_new_whole_life_cancer_rider_unit_table(
            {**first_document, "file_name": "209321R11A00300-F.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_new_whole_life_cancer_rider_unit_table(
            {**first_document, "batch_id": "tii-life-051"}
        )
        is None
    )
    assert (
        parse_fubon_new_whole_life_cancer_rider_unit_table(
            {
                **first_document,
                "text": first_document["text"]
                .replace("壹佰捌拾萬元", "")
                .replace("壹佰捌拾萬元", ""),
            }
        )
        is None
    )
    print(json.dumps({"status": "ok", "product_count": len(PRODUCT_IDS)}))


if __name__ == "__main__":
    main()
