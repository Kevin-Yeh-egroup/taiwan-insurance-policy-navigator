from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from run_tii_benefit_batch_task import (
    approval_files_for_batches,
    audit_proposal_gaps,
    load_exact_slice,
    load_queue,
    prepare_exact_slice,
    read_json,
    select_groups,
    selected_batch_ids,
    summarize_queue,
    validate_exact_slice_proposal,
    validate_work_claim,
    write_json,
)
from tii_workflow_guard import sha256_file


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

    exact_slice_path = root / "exact-slice.json"
    write_json(
        exact_slice_path,
        {
            "batch_id": "tii-life-002",
            "parser_id": "beta-parser",
            "product_ids": ["beta-001"],
            "sources": [
                {
                    "product_id": "beta-001",
                    "source_file": "beta-001-A.pdf",
                    "source_document_sha256": "source-hash",
                }
            ],
        },
    )
    exact_slice = load_exact_slice(exact_slice_path)
    assert exact_slice["batch_id"] == "tii-life-002"
    assert exact_slice["parser_id"] == "beta-parser"
    assert exact_slice["product_ids"] == ["beta-001"]

    missing_source_slice_path = root / "missing-source-slice.json"
    write_json(
        missing_source_slice_path,
        {
            "batch_id": "tii-life-002",
            "parser_id": "beta-parser",
            "product_ids": ["beta-001"],
        },
    )
    try:
        load_exact_slice(missing_source_slice_path)
    except SystemExit as error:
        assert "requires source_file and source_document_sha256" in str(error)
    else:
        raise AssertionError("exact slice without source hashes must be rejected")

    exact_proposal_path = root / "exact-proposal.json"
    write_json(
        exact_proposal_path,
        {
            "batch_id": "tii-life-002",
            "proposals": [
                {
                    "product_id": "beta-001",
                    "status": "proposed",
                    "candidate_count": 1,
                    "candidates": [
                        {
                            "parser_id": "beta-parser",
                            "source_file": "beta-001-A.pdf",
                            "source_document_sha256": "source-hash",
                            "schedule_sha256": "schedule-hash",
                        }
                    ],
                }
            ],
        },
    )
    validation = validate_exact_slice_proposal(exact_proposal_path, exact_slice)
    assert validation["status"] == "ok"
    assert validation["product_count"] == 1
    assert validation["verified_source_count"] == 1
    mismatched_slice = {
        **exact_slice,
        "expected_sources": {
            "beta-001": {
                "source_file": "beta-001-A.pdf",
                "source_document_sha256": "different-source-hash",
            }
        },
    }
    try:
        validate_exact_slice_proposal(exact_proposal_path, mismatched_slice)
    except SystemExit as error:
        assert "source_document_sha256_mismatch" in str(error)
    else:
        raise AssertionError("source hash mismatch must block exact-slice validation")

    duplicate_proposal_path = root / "duplicate-proposal.json"
    duplicate_payload = {
        **{
            "batch_id": "tii-life-002",
            "proposals": [],
        }
    }
    duplicate_payload["proposals"] = (
        read_json(exact_proposal_path)["proposals"] * 2
    )
    write_json(duplicate_proposal_path, duplicate_payload)
    try:
        validate_exact_slice_proposal(duplicate_proposal_path, exact_slice)
    except SystemExit as error:
        assert "duplicate_product_ids=beta-001" in str(error)
    else:
        raise AssertionError("duplicate proposal rows must be rejected")

    approval_dir = root / "approvals"
    write_json(approval_dir / "one.json", {"batch_id": "tii-life-001"})
    write_json(approval_dir / "two.json", {"batch_id": "tii-life-002"})
    assert approval_files_for_batches(
        approval_dir, [], all_files=False
    ) == []
    assert len(
        approval_files_for_batches(approval_dir, [], all_files=True)
    ) == 2

    locked_target = root / "locked-proposal.json"
    lock_path = locked_target.with_name(locked_target.name + ".lock")
    lock_path.write_text("existing worker\n", encoding="utf-8")
    try:
        prepare_exact_slice(
            exact_slice,
            write_proposals=True,
            proposal_output=locked_target,
            review_packet_output=None,
        )
    except SystemExit as error:
        assert "already locked" in str(error)
    else:
        raise AssertionError("concurrent exact proposal target must be blocked")

    parser_family_queue_path = root / "parser-family-queue.json"
    write_json(
        parser_family_queue_path,
        {
            "schema_version": 1,
            "record_count": 2,
            "group_count": 1,
            "groups": [
                {
                    "queue_id": "parser-family:family-hash",
                    "family_fingerprint": "family-hash",
                    "work_type": "benefit_parser",
                    "batch_id": "tii-life-002",
                    "insurance_category": "life",
                    "company": "beta life",
                    "family_name": "beta whole life",
                    "record_count": 2,
                    "product_ids": ["beta-001", "beta-002"],
                    "sample_versions": [
                        {
                            "product_id": "beta-001",
                            "product_name": "beta whole life",
                        }
                    ],
                }
            ],
        },
    )
    parser_family_queue = load_queue(parser_family_queue_path)
    assert len(parser_family_queue) == 1
    assert parser_family_queue[0]["queue_kind"] == "parser_family"
    assert parser_family_queue[0]["batch_ids"] == ["tii-life-002"]
    assert parser_family_queue[0]["companies"] == ["beta life"]
    assert parser_family_queue[0]["sample_products"] == [
        "beta whole life"
    ]
    assert parser_family_queue[0]["candidate_product_count"] == 2
    parser_family_summary = summarize_queue(parser_family_queue)
    assert parser_family_summary["queue_kind"] == "parser_family"
    assert parser_family_summary["groups"] == 1
    assert parser_family_summary["products"] == 2

    claim_path = root / "claim.json"
    write_json(
        claim_path,
        {
            "schema_version": 1,
            "status": "claimed",
            "claim_id": "claim-001",
            "owner": "Kevin",
            "task_id": "task-001",
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=30)
            ).isoformat(timespec="seconds"),
            "queue_sha256": sha256_file(parser_family_queue_path),
            "queue_id": "parser-family:family-hash",
            "batch_id": "tii-life-002",
            "product_ids": ["beta-001", "beta-002"],
        },
    )
    validated_claim = validate_work_claim(
        claim_path,
        queue_path=parser_family_queue_path,
        queue=parser_family_queue,
        task_id="task-001",
    )
    assert validated_claim["queue_id"] == "parser-family:family-hash"
    assert validated_claim["product_ids"] == ["beta-001", "beta-002"]

    try:
        validate_work_claim(
            claim_path,
            queue_path=parser_family_queue_path,
            queue=parser_family_queue,
            task_id="task-002",
        )
    except SystemExit as error:
        assert "different task_id" in str(error)
    else:
        raise AssertionError("a different task must not use the active claim")

print("tii benefit batch task tests: ok")
