from __future__ import annotations

import json
import tempfile
from pathlib import Path

from build_tii_benefit_queue import build_queue


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    plan_path = root / "batch-plan.json"
    content_dir = root / "content"
    raw_dir = root / "raw"
    reviewed_dir = root / "reviewed"
    candidates_path = root / "candidates.json"

    write_json(
        plan_path,
        {
            "tii_manual_matrix_batches": [
                {
                    "id": "tii-life-001",
                    "company_type": "life",
                    "company_type_label": "人身保險",
                    "company_label": "001-測試人壽",
                    "category_label": "健康保險",
                },
                {
                    "id": "tii-property-001",
                    "company_type": "property",
                    "company_type_label": "財產保險",
                    "company_label": "001-測試產險",
                    "category_label": "汽車保險",
                },
            ]
        },
    )
    write_json(
        content_dir / "tii-life-001.json",
        {
            "records": [
                {
                    "product_id": "same-id",
                    "insurance_category": "健康保險",
                    "extracted_document_count": 1,
                },
                {
                    "product_id": "verified-id",
                    "insurance_category": "健康保險",
                    "extracted_document_count": 1,
                    "coverage_entries": [
                        {
                            "amount": 1000,
                            "source": "terms",
                            "source_ref": "第十條",
                        }
                    ],
                },
                {
                    "product_id": "verified-formula-id",
                    "insurance_category": "健康保險",
                    "extracted_document_count": 1,
                    "coverage_entries": [
                        {
                            "calculation_basis": "percentage_of_base",
                            "rate_percent": 100,
                            "source": "terms",
                            "source_ref": "第十一條",
                        }
                    ],
                },
            ]
        },
    )
    write_json(raw_dir / "tii-life-001-text.json", {"documents": []})
    write_json(
        candidates_path,
        {
            "candidates": [
                {
                    "batch_id": "tii-life-001",
                    "product_id": "same-id",
                    "insurance_category": "健康保險",
                    "template_fingerprint": "template-a",
                    "company": "測試人壽",
                    "product_name": "測試醫療險",
                }
            ]
        },
    )

    payload = build_queue(
        plan_path=plan_path,
        content_dir=content_dir,
        raw_dir=raw_dir,
        candidates_path=candidates_path,
        reviewed_dir=reviewed_dir,
    )
    categories = {item["insurance_category"]: item for item in payload["categories"]}
    assert payload["scope"]["official_batch_count"] == 2
    assert categories["健康保險"]["candidate_product_count"] == 1
    assert categories["健康保險"]["records_with_verified_benefits"] == 2
    assert categories["健康保險"]["status"] == "ready_for_structuring"
    assert categories["汽車保險"]["status"] == "blocked_missing_documents"
    assert payload["queue"][0]["dedupe_key"] == "batch_id + product_id"

print("tii benefit queue tests: ok")
