from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from build_tii_proposal_review_packet import (
    build_packet,
    schedule_sha256,
    semantic_schedule_sha256,
    write_json,
)


with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    documents_root = root / "documents"
    proposal_path = root / "proposal.json"
    schedule = {
        "selection_type": "unit",
        "input_mode": "unit",
        "coverage_entries": [
            {
                "id": "benefit",
                "name": "Benefit",
                "basis": "per_unit",
                "amount": 1000,
            }
        ],
    }
    versioned_schedule = {
        **schedule,
        "version_characteristics": {
            "source_product_id": "product-001",
            "terms_revision": "partial-change-1",
            "source_document_sha256": "a" * 64,
            "source_text_quality": "machine_readable_exact_hash",
            "source_text_extractor": "pypdf",
            "benefit_rule": "same",
        },
    }
    other_identity_schedule = {
        **schedule,
        "version_characteristics": {
            "source_product_id": "product-002",
            "terms_revision": "partial-change-2",
            "source_document_sha256": "b" * 64,
            "source_text_quality": "font_encoded_visual_verified",
            "source_text_extractor": "pymupdf",
            "benefit_rule": "same",
        },
    }
    assert schedule_sha256(versioned_schedule) != schedule_sha256(
        other_identity_schedule
    )
    assert semantic_schedule_sha256(
        versioned_schedule
    ) == semantic_schedule_sha256(other_identity_schedule)
    proposals = []
    for product_id, source_bytes, product_schedule in (
        ("product-001", b"source-one", versioned_schedule),
        ("product-002", b"source-two", other_identity_schedule),
    ):
        source_file = f"{product_id}-A.pdf"
        source_path = documents_root / "tii-life-test" / product_id / source_file
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(source_bytes)
        proposals.append(
            {
                "product_id": product_id,
                "status": "proposed",
                "candidate_count": 1,
                "candidates": [
                    {
                        "parser_id": "test-parser-v1",
                        "source_file": source_file,
                        "source_document_sha256": hashlib.sha256(
                            source_bytes
                        ).hexdigest(),
                        "schedule_sha256": schedule_sha256(
                            product_schedule
                        ),
                        "schedule": product_schedule,
                    }
                ],
            }
        )

    write_json(
        proposal_path,
        {
            "batch_id": "tii-life-test",
            "proposals": proposals,
        },
    )
    packet = build_packet(proposal_path, documents_root)
    assert packet["status_counts"] == {"ready_for_human_source_review": 2}
    assert packet["schedule_group_count"] == 2
    assert packet["semantic_schedule_group_count"] == 1
    semantic_group = packet["semantic_schedule_groups"][0]
    assert semantic_group["product_count"] == 2
    assert semantic_group["exact_schedule_count"] == 2
    assert semantic_group["source_document_count"] == 2
    assert semantic_group["product_ids"] == [
        "product-001",
        "product-002",
    ]
    assert semantic_group["parser_ids"] == ["test-parser-v1"]

print("TII proposal review-packet tests passed.")
