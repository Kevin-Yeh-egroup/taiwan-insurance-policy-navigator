from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_tii_plan_benefits import (  # noqa: E402
    EXTRACTOR_VERSION,
    parse_allianz_age111_variable_universal_life_face_amount,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


reviewed = load_json(
    ROOT / "data" / "tii" / "reviewed-benefits" / "tii-life-095.json"
)
reviewed_product_ids = {
    record["product_id"]
    for record in reviewed["records"]
    if record.get("parser_id")
    == "allianz-age111-variable-universal-life-face-amount-v1"
}
documents = load_json(
    ROOT / "work" / "tii-document-text" / "tii-life-095-text.json"
)["documents"]

parsed: dict[str, dict] = {}
for source in documents:
    product_id = source.get("product_id")
    if (
        product_id not in reviewed_product_ids
        or source.get("document_type") != "policy_terms"
        or str(source.get("file_name") or "").lower()
        != f"{str(product_id).lower()}-a.pdf"
    ):
        continue
    schedule = parse_allianz_age111_variable_universal_life_face_amount(
        {**source, "batch_id": "tii-life-095"}
    )
    assert schedule is not None, product_id
    assert product_id not in parsed, product_id
    parsed[product_id] = schedule

assert EXTRACTOR_VERSION == "tii-plan-benefits-v230"
assert len(reviewed_product_ids) == 804
assert set(parsed) == reviewed_product_ids

policy_type_groups = Counter()
threshold_schedule_groups = Counter()
type_e_product_count = 0
threshold_schedule_product_count = 0
for product_id, schedule in parsed.items():
    assert schedule["selection_type"] == "face_amount_plan", product_id
    assert schedule["input_mode"] == "face_amount_plan", product_id
    characteristics = schedule["version_characteristics"]
    policy_types = characteristics["policy_type_options"]
    assert schedule["plan_options"] == [
        {"value": policy_type, "label": policy_type}
        for policy_type in policy_types
    ], product_id
    assert set(characteristics["net_amount_at_risk_formula_by_type"]) == set(
        policy_types
    ), product_id
    assert "threshold_factor" not in characteristics["required_policy_inputs"]
    assert all(
        entry["calculation_basis"]
        == "net_amount_at_risk_plus_policy_account_value"
        for entry in schedule["coverage_entries"]
    ), product_id

    threshold_schedule = characteristics["threshold_factor_schedule"]
    assert characteristics["threshold_factor_required"] == bool(
        threshold_schedule
    ), product_id
    if threshold_schedule:
        threshold_schedule_product_count += 1
        assert "insured_age_at_event" in characteristics["required_policy_inputs"]
    else:
        assert "insured_age_at_event" not in characteristics["required_policy_inputs"]

    if "戊型" in policy_types:
        type_e_product_count += 1
        assert {
            "paid_premium_total",
            "partial_termination_amount_total",
        }.issubset(characteristics["required_policy_inputs"])

    policy_type_groups[tuple(policy_types)] += 1
    threshold_schedule_groups[
        tuple(
            (item["min_age"], item["max_age"], item["factor"])
            for item in threshold_schedule
        )
    ] += 1

assert type_e_product_count == 207
assert threshold_schedule_product_count == 591
assert len(policy_type_groups) == 8
assert len(threshold_schedule_groups) == 6

print(
    json.dumps(
        {
            "status": "ok",
            "extractor_version": EXTRACTOR_VERSION,
            "verified_product_count": len(parsed),
            "policy_type_group_count": len(policy_type_groups),
            "type_e_product_count": type_e_product_count,
            "threshold_schedule_product_count": threshold_schedule_product_count,
            "threshold_schedule_group_count": len(threshold_schedule_groups),
        },
        ensure_ascii=False,
        indent=2,
    )
)
