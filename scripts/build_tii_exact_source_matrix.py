from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = (
    ROOT
    / "work"
    / "tii-life-calculation-readiness"
    / "parser-family-queue.json"
)
DEFAULT_DOCUMENTS_ROOT = ROOT / "work" / "tii-documents"
TAIPEI_TZ = timezone(timedelta(hours=8))
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def normalize_terms_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_with_pypdf(path: Path) -> tuple[list[str], str | None]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(path, strict=False)
        return [page.extract_text() or "" for page in reader.pages], None
    except Exception as error:
        return [], f"{type(error).__name__}: {error}"


def extract_with_pymupdf(path: Path) -> tuple[list[str], str | None]:
    try:
        import pymupdf

        with pymupdf.open(path) as reader:
            return [page.get_text("text") or "" for page in reader], None
    except Exception as error:
        return [], f"{type(error).__name__}: {error}"


def extractor_result(
    *,
    page_texts: list[str],
    error: str | None,
    anchors: list[str],
    minimum_cjk_count: int,
) -> dict[str, Any]:
    normalized_text = normalize_terms_text("\n".join(page_texts))
    cjk_count = len(CJK_PATTERN.findall(normalized_text))
    matched_anchors = [
        anchor
        for anchor in anchors
        if normalize_terms_text(anchor) in normalized_text
    ]
    normalized_char_count = len(normalized_text)
    usable = bool(
        not error
        and page_texts
        and cjk_count >= minimum_cjk_count
        and len(matched_anchors) == len(anchors)
    )
    return {
        "page_count": len(page_texts) or None,
        "normalized_char_count": normalized_char_count,
        "cjk_count": cjk_count,
        "cjk_density": (
            round(cjk_count / normalized_char_count, 6)
            if normalized_char_count
            else 0.0
        ),
        "anchor_count": len(matched_anchors),
        "matched_anchors": matched_anchors,
        "normalized_text_sha256": (
            hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
            if normalized_text
            else None
        ),
        "usable": usable,
        "error": error,
    }


def find_group(queue: dict[str, Any], family_fingerprint: str) -> dict[str, Any]:
    matches = [
        group
        for group in queue.get("groups") or []
        if group.get("family_fingerprint") == family_fingerprint
    ]
    if len(matches) != 1:
        raise ValueError(
            "Expected exactly one parser family for fingerprint "
            f"{family_fingerprint!r}; found {len(matches)}."
        )
    return matches[0]


def policy_terms_path(
    *,
    documents_root: Path,
    batch_id: str,
    product_id: str,
) -> Path | None:
    product_dir = documents_root / batch_id / product_id
    if not product_dir.is_dir():
        return None
    candidates = sorted(
        path
        for path in product_dir.iterdir()
        if path.is_file() and path.name.lower().endswith("-a.pdf")
    )
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple A-type policy terms for {batch_id}/{product_id}: "
            + ", ".join(path.name for path in candidates)
        )
    return candidates[0] if candidates else None


def build_matrix(
    *,
    queue: dict[str, Any],
    queue_path: Path,
    documents_root: Path,
    family_fingerprint: str,
    anchors: list[str],
    minimum_cjk_count: int,
) -> dict[str, Any]:
    group = find_group(queue, family_fingerprint)
    batch_id = str(group.get("batch_id") or "")
    rows = []
    hash_product_ids: dict[str, list[str]] = defaultdict(list)

    for product_id_value in group.get("product_ids") or []:
        product_id = str(product_id_value or "")
        source_path = policy_terms_path(
            documents_root=documents_root,
            batch_id=batch_id,
            product_id=product_id,
        )
        if source_path is None:
            rows.append(
                {
                    "product_id": product_id,
                    "file_name": None,
                    "source_document_sha256": None,
                    "file_size": None,
                    "status": "source_pending",
                    "preferred_extractor": None,
                    "extractors": {},
                    "gap_reason": "missing_policy_terms_document",
                }
            )
            continue

        source_hash = sha256_file(source_path)
        hash_product_ids[source_hash].append(product_id)
        pypdf_pages, pypdf_error = extract_with_pypdf(source_path)
        pymupdf_pages, pymupdf_error = extract_with_pymupdf(source_path)
        extractors = {
            "pypdf": extractor_result(
                page_texts=pypdf_pages,
                error=pypdf_error,
                anchors=anchors,
                minimum_cjk_count=minimum_cjk_count,
            ),
            "pymupdf": extractor_result(
                page_texts=pymupdf_pages,
                error=pymupdf_error,
                anchors=anchors,
                minimum_cjk_count=minimum_cjk_count,
            ),
        }
        preferred_extractor = next(
            (
                extractor_name
                for extractor_name in ("pypdf", "pymupdf")
                if extractors[extractor_name]["usable"]
            ),
            None,
        )
        row = {
            "product_id": product_id,
            "file_name": source_path.name,
            "source_document_sha256": source_hash,
            "file_size": source_path.stat().st_size,
            "status": "readable" if preferred_extractor else "source_pending",
            "preferred_extractor": preferred_extractor,
            "extractors": extractors,
        }
        if not preferred_extractor:
            row["gap_reason"] = "no_usable_cjk_or_policy_anchors"
        rows.append(row)

    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[str(row["status"])] += 1
    duplicate_source_sha_groups = {
        source_hash: product_ids
        for source_hash, product_ids in hash_product_ids.items()
        if len(product_ids) > 1
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(TAIPEI_TZ).isoformat(
            timespec="seconds"
        ),
        "batch_id": batch_id,
        "family_fingerprint": family_fingerprint,
        "family_name": group.get("family_name"),
        "queue_path": str(queue_path.relative_to(ROOT)),
        "version_boundary": (
            "Every row remains isolated by exact batch_id + product_id + "
            "source document SHA-256. A shared hash is evidence of a shared "
            "file only and never merges product versions."
        ),
        "anchors": anchors,
        "product_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "duplicate_source_sha_groups": duplicate_source_sha_groups,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build an exact product-version source matrix for one TII parser "
            "family using both pypdf and PyMuPDF."
        )
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=DEFAULT_QUEUE,
    )
    parser.add_argument(
        "--documents-root",
        type=Path,
        default=DEFAULT_DOCUMENTS_ROOT,
    )
    parser.add_argument("--family-fingerprint", required=True)
    parser.add_argument(
        "--anchor",
        action="append",
        required=True,
        help=(
            "Required normalized policy-text anchor. Repeat for multiple "
            "anchors; all anchors must match."
        ),
    )
    parser.add_argument("--minimum-cjk-count", type=int, default=500)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    matrix = build_matrix(
        queue=queue,
        queue_path=args.queue.resolve(),
        documents_root=args.documents_root.resolve(),
        family_fingerprint=args.family_fingerprint,
        anchors=[str(anchor) for anchor in args.anchor],
        minimum_cjk_count=args.minimum_cjk_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": matrix["batch_id"],
                "family_name": matrix["family_name"],
                "product_count": matrix["product_count"],
                "status_counts": matrix["status_counts"],
                "duplicate_source_sha_group_count": len(
                    matrix["duplicate_source_sha_groups"]
                ),
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
