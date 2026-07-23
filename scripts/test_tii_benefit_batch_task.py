from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from run_tii_benefit_batch_task import (
    audit_proposal_gaps,
    select_groups,
    selected_batch_ids,
    summarize_queue,
    write_json,
)


QUEUE = [
    {
        "queue_id": "injury:a",
        "insurance_category": "injury",
        "candidate_product_count": 3,
        "candidate_document_count": 3,
        "batch_ids": ["tii-life-001"],
        "companies": ["alpha life"],
        "sample_products": ["alpha accident"],
    },
    {
        "queue_id": "life:b",
        "insurance_category": "life",
        "candidate_product_count": 2,
        "candidate_document_count": 4,
        "batch_ids": ["tii-life-002", "tii-life-003"],
        "companies": ["beta life"],
        "sample_products": ["beta whole life"],
    },
]


summary = summarize_queue(QUEUE)
assert summary["groups"] == 2
assert summary["products"] == 5
assert summary["documents"] == 7
assert summary["batches"] == 3
assert summary["companies"] == 2
assert summary["by_category"]["injury"]["groups"] == 1
assert summary["top_batches"]["tii-life-002"]["categories"]["life"] == 1

selected = select_groups(
    QUEUE,
    categories={"life"},
    batch_ids=set(),
    company_terms=set(),
    max_groups=5,
)
assert [group["queue_id"] for group in selected] == ["life:b"]
assert selected_batch_ids(selected) == ["tii-life-002", "tii-life-003"]

selected = select_groups(
    QUEUE,
    categories=set(),
    batch_ids={"tii-life-001"},
    company_terms={"alpha"},
    max_groups=1,
)
assert [group["queue_id"] for group in selected] == ["injury:a"]

with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    document_content_dir = root / "document-content"
    proposal_dir = root / "proposals"
    write_json(
        document_content_dir / "tii-life-001.json",
        {
            "records": [
                {
                    "product_id": "alpha-001",
                    "product_name": "alpha accident",
                    "documents": [
                        {
                            "document_type": "policy_terms",
                            "file_name": "alpha-001-A.pdf",
                        }
                    ],
                }
            ]
        },
    )
    write_json(
        document_content_dir / "tii-life-002.json",
        {
            "records": [
                {
                    "product_id": "beta-001",
                    "product_name": "beta whole life",
                    "documents": [
                        {
                            "document_type": "policy_terms",
                            "file_name": "beta-001-A.pdf",
                        }
                    ],
                }
            ]
        },
    )
    write_json(
        proposal_dir / "tii-life-002.json",
        {
            "proposals": [
                {
                    "product_id": "beta-001",
                    "status": "proposed",
                    "candidate_count": 1,
                    "candidates": [{"parser_id": "beta-parser"}],
                }
            ]
        },
    )
    audit = audit_proposal_gaps(
        QUEUE,
        document_content_dir=document_content_dir,
        proposal_dir=proposal_dir,
    )
    assert audit["target_products"] == 2
    assert audit["with_proposal_count"] == 1
    assert audit["missing_proposal_count"] == 1
    assert audit["missing_by_batch"] == {"tii-life-001": 1}
    assert audit["proposal_by_batch"] == {"tii-life-002": 1}
    assert audit["with_proposal"][0]["proposal"]["parser_ids"] == ["beta-parser"]

print("tii benefit batch task tests: ok")
