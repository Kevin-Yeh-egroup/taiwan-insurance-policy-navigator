from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


TAIPEI_TZ = timezone(timedelta(hours=8))


def revision_for_product_id(product_id: str) -> int | None:
    match = re.search(r"(\d{2})$", product_id)
    return int(match.group(1)) if match else None


def page_count_for_row(row: dict) -> int | None:
    extractors = row.get("extractors") or {}
    for extractor in ("pypdf", "pymupdf"):
        page_count = (extractors.get(extractor) or {}).get("page_count")
        if isinstance(page_count, int) and page_count > 0:
            return page_count
    return None


def build_gap_report(matrix: dict) -> dict:
    duplicate_hashes = {
        source_hash: product_ids
        for source_hash, product_ids in (
            matrix.get("duplicate_source_sha_groups") or {}
        ).items()
        if len(product_ids) > 1
    }
    gaps = []
    for row in matrix.get("rows") or []:
        if row.get("status") != "source_pending":
            continue
        product_id = str(row.get("product_id") or "")
        revision = revision_for_product_id(product_id)
        source_hash = str(row.get("source_document_sha256") or "")
        shared_product_ids = duplicate_hashes.get(source_hash, [])
        if row.get("gap_reason") == "missing_policy_terms_document":
            reason_code = "missing_policy_terms_document"
            reason = (
                "The exact product_id has no official A-type policy-terms "
                "document in the current TII detail capture."
            )
            next_action = (
                "Return to the exact TII product detail, download the official "
                "A-type policy terms, then rebuild the source matrix."
            )
        else:
            reason_code = "broken_font_mapping_policy_terms"
            reason = (
                "The official policy-terms PDF yields no reliable CJK policy "
                "text with either pypdf or PyMuPDF because its embedded font "
                "mapping is broken."
            )
            next_action = (
                "Obtain an official machine-readable copy or run page-level "
                "OCR followed by visual verification of every formula and "
                "eligibility page and create a new exact normalized-text hash."
            )
        if shared_product_ids:
            reason += (
                " This source hash is shared by "
                + ", ".join(shared_product_ids)
                + "; each product_id remains an independent version boundary."
            )
        gaps.append(
            {
                "product_id": product_id,
                "terms_revision": (
                    f"partial-change-{revision}"
                    if revision is not None
                    else "unknown"
                ),
                "file_name": row.get("file_name"),
                "source_document_sha256": source_hash or None,
                "page_count": page_count_for_row(row),
                "status": "source_pending",
                "reason_code": reason_code,
                "reason": reason,
                "next_action": next_action,
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(TAIPEI_TZ).isoformat(
            timespec="seconds"
        ),
        "batch_id": matrix.get("batch_id"),
        "family_fingerprint": matrix.get("family_fingerprint"),
        "family_name": matrix.get("family_name"),
        "version_boundary": (
            "Each item remains isolated by exact batch_id + product_id + "
            "source document SHA-256. Adjacent revisions must not be used to "
            "infer a benefit schedule."
        ),
        "gap_count": len(gaps),
        "gaps": gaps,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic source-gap report from an exact family "
            "source matrix."
        )
    )
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    report = build_gap_report(matrix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": report["batch_id"],
                "gap_count": report["gap_count"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
