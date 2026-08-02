from __future__ import annotations

from build_tii_parser_family_queue import (
    build_queue,
    normalize_family_name,
    work_type_for_name,
)


assert (
    normalize_family_name("甲人壽住院醫療附約(第12次部分變更)")
    == "甲人壽住院醫療附約"
)
assert (
    normalize_family_name("甲人壽住院醫療附約（第十三次部份變更）")
    == "甲人壽住院醫療附約"
)
assert work_type_for_name("投資標的異動批註條款") == "endorsement_review"
assert work_type_for_name("海外醫療附加條款") == "additional_terms_review"
assert work_type_for_name("住院醫療附約") == "benefit_parser"

records = [
    {
        "calculation_status": "needs_parser_or_proposal",
        "batch_id": "tii-life-001",
        "product_id": "product-001",
        "company": "甲人壽",
        "insurance_category": "健康保險",
        "product_name": "甲人壽住院醫療附約",
        "coverage_terms": ["保險金", "住院"],
    },
    {
        "calculation_status": "needs_parser_or_proposal",
        "batch_id": "tii-life-001",
        "product_id": "product-002",
        "company": "甲人壽",
        "insurance_category": "健康保險",
        "product_name": "甲人壽住院醫療附約(第1次部分變更)",
        "coverage_terms": ["保險金", "住院"],
    },
    {
        "calculation_status": "needs_parser_or_proposal",
        "batch_id": "tii-life-001",
        "product_id": "product-003",
        "company": "甲人壽",
        "insurance_category": "健康保險",
        "product_name": "甲人壽海外醫療附加條款",
        "coverage_terms": ["醫療費用"],
    },
]
payload = build_queue(records)
assert payload["record_count"] == 3
assert payload["group_count"] == 2
assert payload["multi_version_group_count"] == 1
assert payload["records_in_multi_version_groups"] == 2
benefit_group = next(
    group for group in payload["groups"] if group["work_type"] == "benefit_parser"
)
assert benefit_group["product_ids"] == ["product-001", "product-002"]
assert benefit_group["coverage_term_counts"] == {"保險金": 2, "住院": 2}
assert "source_batch_id + product_id" in benefit_group["version_boundary"]

source_gap_payload = build_queue(
    records,
    {
        ("tii-life-001", "product-002"): {
            "reason_code": "image_only_policy_terms",
            "reason": "No usable text.",
            "next_action": "Run OCR and verify visually.",
            "source_gap_path": "work/source-gaps.json",
        }
    },
)
source_recovery_group = next(
    group
    for group in source_gap_payload["groups"]
    if group["work_type"] == "source_text_recovery"
)
assert source_recovery_group["product_ids"] == ["product-002"]
assert source_recovery_group["source_gaps"][0]["reason_code"] == (
    "image_only_policy_terms"
)
assert "do not infer" in source_recovery_group["next_action"]

priority_payload = build_queue(
    [
        {
            "calculation_status": "needs_parser_or_proposal",
            "batch_id": "tii-life-002",
            "product_id": f"investment-{index:03d}",
            "company": "乙人壽",
            "insurance_category": "投資型壽險",
            "product_name": "乙人壽大型投資型壽險",
            "coverage_terms": ["身故保險金"],
        }
        for index in range(10)
    ]
    + [
        {
            "calculation_status": "needs_parser_or_proposal",
            "batch_id": "tii-life-003",
            "product_id": "health-priority-001",
            "company": "丙人壽",
            "insurance_category": "健康保險",
            "product_name": "丙人壽小型住院醫療",
            "coverage_terms": ["住院醫療保險金"],
        }
    ]
)
assert priority_payload["groups"][0]["insurance_category"] == "健康保險"

print("TII parser-family queue tests passed.")
