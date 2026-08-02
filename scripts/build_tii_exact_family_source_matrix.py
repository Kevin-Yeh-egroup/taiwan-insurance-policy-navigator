#!/usr/bin/env python3
"""Build an exact-version PDF readability matrix for one parser family."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TAIPEI_TZ = timezone(timedelta(hours=8))
DEFAULT_QUEUE = (
    ROOT
    / "work"
    / "tii-life-calculation-readiness"
    / "parser-family-queue.json"
)
DEFAULT_DOCUMENTS_ROOT = ROOT / "work" / "tii-documents"
DEFAULT_CONTENT_ROOT = ROOT / "data" / "tii" / "document-content"


def now_iso() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_metrics(
    text: str,
    *,
    anchors: list[str],
    page_count: int,
    error: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)
    compact = re.sub(r"\s+", "", normalized)
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", normalized))
    matched_anchors = [
        anchor
        for anchor in anchors
        if re.sub(r"\s+", "", normalize_text(anchor)) in compact
    ]
    minimum_anchor_count = min(2, len(anchors))
    usable = (
        not error
        and cjk_count >= 100
        and len(matched_anchors) >= minimum_anchor_count
    )
    return {
        "page_count": page_count,
        "normalized_char_count": len(normalized),
        "cjk_count": cjk_count,
        "cjk_density": (
            round(cjk_count / len(normalized), 6)
            if normalized
            else 0
        ),
        "anchor_count": len(matched_anchors),
        "matched_anchors": matched_anchors,
        "normalized_text_sha256": (
            hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if normalized
            else ""
        ),
        "usable": usable,
        "error": error,
    }


def extract_with_pypdf(path: Path, anchors: list[str]) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path, strict=False)
        pages = [page.extract_text() or "" for page in reader.pages]
        return text_metrics(
            "\n".join(pages),
            anchors=anchors,
            page_count=len(pages),
        )
    except Exception as error:
        return text_metrics(
            "",
            anchors=anchors,
            page_count=0,
            error=f"{type(error).__name__}: {error}",
        )


def extract_with_pymupdf(
    path: Path,
    anchors: list[str],
) -> dict[str, Any]:
    try:
        import pymupdf

        with pymupdf.open(path) as reader:
            pages = [page.get_text("text") or "" for page in reader]
        return text_metrics(
            "\n".join(pages),
            anchors=anchors,
            page_count=len(pages),
        )
    except Exception as error:
        return text_metrics(
            "",
            anchors=anchors,
            page_count=0,
            error=f"{type(error).__name__}: {error}",
        )


def extract_with_windows_ocr(
    path: Path,
    anchors: list[str],
    page_count: int,
) -> dict[str, Any]:
    try:
        from extract_tii_document_content import (
            extract_windows_ocr_pages,
        )

        text, pages = extract_windows_ocr_pages(path, page_count)
        return text_metrics(
            text,
            anchors=anchors,
            page_count=len(pages),
        )
    except Exception as error:
        return text_metrics(
            "",
            anchors=anchors,
            page_count=0,
            error=f"{type(error).__name__}: {error}",
        )


def choose_extractor(
    extractors: dict[str, dict[str, Any]],
    forced_extractor: str | None = None,
) -> str | None:
    if (
        forced_extractor
        and extractors.get(forced_extractor, {}).get("usable")
    ):
        return forced_extractor
    candidates = [
        (name, metrics)
        for name, metrics in extractors.items()
        if metrics.get("usable")
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            int(item[1].get("anchor_count") or 0),
            int(item[1].get("cjk_count") or 0),
            item[0] == "pypdf",
        ),
        reverse=True,
    )
    return candidates[0][0]


def policy_terms_file_names(
    *,
    batch_id: str,
    content_root: Path,
) -> dict[str, str]:
    path = content_root / f"{batch_id}.json"
    if not path.is_file():
        return {}
    payload = read_json(path)
    result: dict[str, str] = {}
    for record in payload.get("records") or []:
        if not isinstance(record, dict):
            continue
        product_id = str(record.get("product_id") or "")
        for document in record.get("documents") or []:
            if (
                isinstance(document, dict)
                and document.get("document_type") == "policy_terms"
                and document.get("file_name")
            ):
                result[product_id] = str(document["file_name"])
                break
    return result


def build_matrix(
    *,
    queue_path: Path,
    family_fingerprint: str,
    documents_root: Path,
    content_root: Path,
    anchors: list[str],
    included_product_ids: list[str] | None = None,
    proposal_path: Path | None = None,
    batch_id_override: str = "",
    family_name_override: str = "",
    force_windows_ocr_product_ids: list[str] | None = None,
    force_pymupdf_product_ids: list[str] | None = None,
) -> dict[str, Any]:
    queue = read_json(queue_path)
    groups = [
        group
        for group in queue.get("groups") or []
        if isinstance(group, dict)
    ]
    group = next(
        (
            item
            for item in groups
            if item.get("family_fingerprint") == family_fingerprint
        ),
        None,
    )
    proposal = (
        read_json(proposal_path)
        if proposal_path and proposal_path.is_file()
        else {}
    )
    proposal_product_ids = [
        str(item.get("product_id") or "")
        for item in proposal.get("proposals") or []
        if isinstance(item, dict) and item.get("product_id")
    ]
    if group is None and not (
        (batch_id_override or proposal.get("batch_id"))
        and proposal_product_ids
    ):
        raise SystemExit(
            f"family fingerprint not found: {family_fingerprint}"
        )
    batch_id = str(
        (group or {}).get("batch_id")
        or batch_id_override
        or proposal.get("batch_id")
        or ""
    )
    exact_product_ids = [
        str(product_id)
        for product_id in (group or {}).get("product_ids") or []
        if product_id
    ]
    for product_id in proposal_product_ids:
        if product_id and product_id not in exact_product_ids:
            exact_product_ids.append(product_id)
    for product_id in included_product_ids or []:
        if product_id and product_id not in exact_product_ids:
            exact_product_ids.append(product_id)
    terms_by_product = policy_terms_file_names(
        batch_id=batch_id,
        content_root=content_root,
    )
    batch_root = documents_root / batch_id
    rows: list[dict[str, Any]] = []
    for product_id in exact_product_ids:
        file_name = terms_by_product.get(product_id, "")
        source_path = batch_root / product_id / file_name
        if not file_name or not source_path.is_file():
            rows.append(
                {
                    "product_id": product_id,
                    "file_name": file_name,
                    "status": "source_pending",
                    "gap_reason": "missing_policy_terms_document",
                }
            )
            continue
        extractors = {
            "pypdf": extract_with_pypdf(source_path, anchors),
            "pymupdf": extract_with_pymupdf(source_path, anchors),
        }
        force_windows_ocr = product_id in set(
            force_windows_ocr_product_ids or []
        )
        forced_extractor = (
            "pymupdf"
            if product_id in set(force_pymupdf_product_ids or [])
            else None
        )
        preferred_extractor = choose_extractor(
            extractors,
            forced_extractor=forced_extractor,
        )
        if force_windows_ocr or not preferred_extractor:
            page_count = max(
                int(metrics.get("page_count") or 0)
                for metrics in extractors.values()
            )
            extractors["windows_ocr"] = extract_with_windows_ocr(
                source_path,
                anchors,
                page_count,
            )
            preferred_extractor = (
                "windows_ocr"
                if (
                    force_windows_ocr
                    and extractors["windows_ocr"].get("usable")
                )
                else choose_extractor(extractors)
            )
        row: dict[str, Any] = {
            "product_id": product_id,
            "file_name": file_name,
            "source_document_sha256": sha256_file(source_path),
            "file_size": source_path.stat().st_size,
            "status": (
                "readable"
                if preferred_extractor
                else "source_pending"
            ),
            "preferred_extractor": preferred_extractor,
            "extractors": extractors,
        }
        if not preferred_extractor:
            row["gap_reason"] = (
                "no_usable_cjk_or_policy_anchors"
            )
        rows.append(row)

    duplicate_sources: dict[str, list[str]] = {}
    for row in rows:
        source_sha = str(row.get("source_document_sha256") or "")
        if source_sha:
            duplicate_sources.setdefault(source_sha, []).append(
                row["product_id"]
            )
    duplicate_sources = {
        source_sha: product_ids
        for source_sha, product_ids in duplicate_sources.items()
        if len(product_ids) > 1
    }
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "queue_path": str(queue_path),
        "family_fingerprint": family_fingerprint,
        "family_name": (
            (group or {}).get("family_name")
            or family_name_override
            or ""
        ),
        "batch_id": batch_id,
        "version_boundary": (
            "This matrix is source-readability evidence only. Every parser, "
            "proposal, review, and promotion must preserve exact "
            "source_batch_id + product_id + source document SHA-256."
        ),
        "anchors": anchors,
        "product_count": len(exact_product_ids),
        "status_counts": status_counts,
        "duplicate_source_sha_groups": duplicate_sources,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-fingerprint", required=True)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument(
        "--documents-root",
        type=Path,
        default=DEFAULT_DOCUMENTS_ROOT,
    )
    parser.add_argument(
        "--content-root",
        type=Path,
        default=DEFAULT_CONTENT_ROOT,
    )
    parser.add_argument("--anchor", action="append", default=[])
    parser.add_argument(
        "--include-product-id",
        action="append",
        default=[],
        help="Add an exact product_id even if it is no longer pending in the queue.",
    )
    parser.add_argument(
        "--proposal",
        type=Path,
        help="Read exact product_ids and batch_id from a generated proposal.",
    )
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--family-name", default="")
    parser.add_argument(
        "--force-pymupdf-product-id",
        action="append",
        default=[],
        help=(
            "Prefer PyMuPDF for one exact product_id when source review "
            "shows that another usable text layer duplicates columns."
        ),
    )
    parser.add_argument(
        "--force-windows-ocr-product-id",
        action="append",
        default=[],
        help=(
            "Force one exact product_id through Windows OCR even when a "
            "partial machine-readable layer passes the anchor threshold."
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_matrix(
        queue_path=args.queue,
        family_fingerprint=args.family_fingerprint,
        documents_root=args.documents_root,
        content_root=args.content_root,
        anchors=[anchor.strip() for anchor in args.anchor if anchor.strip()],
        included_product_ids=[
            product_id.strip()
            for product_id in args.include_product_id
            if product_id.strip()
        ],
        proposal_path=args.proposal,
        batch_id_override=args.batch_id.strip(),
        family_name_override=args.family_name.strip(),
        force_windows_ocr_product_ids=[
            product_id.strip()
            for product_id in args.force_windows_ocr_product_id
            if product_id.strip()
        ],
        force_pymupdf_product_ids=[
            product_id.strip()
            for product_id in args.force_pymupdf_product_id
            if product_id.strip()
        ],
    )
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": payload["batch_id"],
                "family_fingerprint": payload["family_fingerprint"],
                "product_count": payload["product_count"],
                "status_counts": payload["status_counts"],
                "duplicate_source_sha_group_count": len(
                    payload["duplicate_source_sha_groups"]
                ),
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
