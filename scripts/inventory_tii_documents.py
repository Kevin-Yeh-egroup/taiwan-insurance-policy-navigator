from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse


TII_BASE_URL = "https://insprod.tii.org.tw/"
TAIPEI_TZ = timezone(timedelta(hours=8))
OPEN2_LINK_RE = re.compile(
    r"<a\b[^>]*href\s*=\s*['\"]?(?P<href>Open2\.ashx\?id=[^'\"\s>]+)['\"]?[^>]*>(?P<label>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")
    return path.stat().st_size


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = TAG_RE.sub(" ", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def open2_id_from_href(href: str) -> str:
    parsed = urlparse(urljoin(TII_BASE_URL, href))
    return parse_qs(parsed.query).get("id", [""])[0]


def document_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or "unknown"


def filename_suffix_code(filename: str) -> str:
    stem = Path(filename).stem.upper()
    match = re.search(r"-([A-Z])(?:\d+)?$", stem)
    return match.group(1) if match else ""


def classify_document(filename: str, context_hint: str) -> dict[str, str]:
    lower_context = context_hint.lower()
    suffix_code = filename_suffix_code(filename)
    basis = "filename_suffix" if suffix_code else "context"
    confidence = "medium" if suffix_code else "low"

    if suffix_code == "A" or "保單條款" in context_hint:
        return {
            "document_type": "policy_terms",
            "document_label": "policy terms",
            "priority": "core",
            "basis": basis,
            "confidence": "high",
        }
    if suffix_code == "F" or "商品內容" in context_hint or "內容說明" in context_hint:
        return {
            "document_type": "product_summary",
            "document_label": "product content summary",
            "priority": "core",
            "basis": basis,
            "confidence": "high",
        }
    if "費率" in context_hint or "rate" in lower_context:
        return {
            "document_type": "premium_rate",
            "document_label": "premium or rate document",
            "priority": "supplemental",
            "basis": "context",
            "confidence": "medium",
        }
    if "要保" in context_hint or "申請" in context_hint or "application" in lower_context:
        return {
            "document_type": "application_form",
            "document_label": "application form",
            "priority": "supplemental",
            "basis": "context",
            "confidence": "medium",
        }
    if "核准" in context_hint or "備查" in context_hint or "approval" in lower_context:
        return {
            "document_type": "regulatory_filing",
            "document_label": "regulatory filing",
            "priority": "supplemental",
            "basis": "context",
            "confidence": "medium",
        }
    if suffix_code:
        return {
            "document_type": f"attachment_{suffix_code.lower()}",
            "document_label": f"attachment {suffix_code}",
            "priority": "supplemental",
            "basis": "filename_suffix",
            "confidence": confidence,
        }
    return {
        "document_type": "attachment",
        "document_label": "attachment",
        "priority": "supplemental",
        "basis": "fallback",
        "confidence": "low",
    }


def extract_open2_links(detail_html: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for match in OPEN2_LINK_RE.finditer(detail_html):
        href = html.unescape(match.group("href"))
        filename = clean_text(match.group("label"))
        context_start = max(0, match.start() - 900)
        context_hint = clean_text(detail_html[context_start : match.start()])[-240:]
        download_url = urljoin(TII_BASE_URL, href)
        open2_id = open2_id_from_href(href)
        if not open2_id:
            continue
        classification = classify_document(filename, context_hint)
        links.append(
            {
                "open2_id": open2_id,
                "download_url": download_url,
                "filename": filename or f"{open2_id}.bin",
                "extension": document_extension(filename),
                "suffix_code": filename_suffix_code(filename),
                "context_hint": context_hint,
                **classification,
            }
        )
    return links


def load_records(records_root: Path, bucket: str, category: str = "", limit: int = 0) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((records_root / bucket).glob("*.json")):
        if category and path.stem != category:
            continue
        payload = read_json(path)
        for record in payload.get("records") or []:
            records.append({**record, "_record_shard": str(path)})
            if limit and len(records) >= limit:
                return records
    return records


def stable_document_key(open2_id: str, filename: str) -> str:
    base = open2_id or filename
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def inventory_documents(
    bucket: str,
    records_root: Path,
    output_root: Path,
    category: str = "",
    limit: int = 0,
    include_policy_map: bool = True,
) -> dict[str, Any]:
    records = load_records(records_root, bucket, category=category, limit=limit)
    generated_at = datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    documents_by_id: dict[str, dict[str, Any]] = {}
    policy_documents: list[dict[str, Any]] = []
    counters = Counter()
    by_category: dict[str, Counter] = defaultdict(Counter)
    by_batch: dict[str, Counter] = defaultdict(Counter)

    for index, record in enumerate(records, start=1):
        counters["records_total"] += 1
        detail_source_file = str(record.get("detail_source_file") or "")
        source_batch_id = str(record.get("source_batch_id") or "")
        category = str(record.get("insurance_category") or "")
        product_id = str(record.get("product_id") or "")
        if not detail_source_file:
            counters["records_without_detail_path"] += 1
            continue

        detail_path = Path(detail_source_file)
        if not detail_path.exists():
            counters["records_missing_detail_file"] += 1
            by_category[category]["missing_detail_file"] += 1
            by_batch[source_batch_id]["missing_detail_file"] += 1
            continue

        counters["records_with_detail_file"] += 1
        detail_html = detail_path.read_text(encoding="utf-8", errors="replace")
        links = extract_open2_links(detail_html)
        if not links:
            counters["records_with_detail_no_documents"] += 1
            by_category[category]["no_documents"] += 1
            by_batch[source_batch_id]["no_documents"] += 1
            continue

        counters["records_with_documents"] += 1
        by_category[category]["records_with_documents"] += 1
        by_batch[source_batch_id]["records_with_documents"] += 1

        for link in links:
            counters["document_links_total"] += 1
            counters[f"type:{link['document_type']}"] += 1
            counters[f"extension:{link['extension']}"] += 1
            by_category[category][f"type:{link['document_type']}"] += 1
            by_batch[source_batch_id][f"type:{link['document_type']}"] += 1

            document_key = stable_document_key(link["open2_id"], link["filename"])
            doc = documents_by_id.setdefault(
                document_key,
                {
                    "document_key": document_key,
                    "open2_id": link["open2_id"],
                    "download_url": link["download_url"],
                    "filename": link["filename"],
                    "extension": link["extension"],
                    "suffix_code": link["suffix_code"],
                    "document_type": link["document_type"],
                    "document_label": link["document_label"],
                    "priority": link["priority"],
                    "classification_basis": link["basis"],
                    "classification_confidence": link["confidence"],
                    "first_context_hint": link["context_hint"],
                    "linked_policy_count": 0,
                    "linked_batches": [],
                    "linked_categories": [],
                },
            )
            doc["linked_policy_count"] += 1
            if source_batch_id and source_batch_id not in doc["linked_batches"]:
                doc["linked_batches"].append(source_batch_id)
            if category and category not in doc["linked_categories"]:
                doc["linked_categories"].append(category)

            if include_policy_map:
                policy_documents.append(
                    {
                        "record_id": record.get("id") or "",
                        "product_id": product_id,
                        "source_batch_id": source_batch_id,
                        "company": record.get("company") or "",
                        "insurance_category": category,
                        "product_name": record.get("product_name") or "",
                        "sale_date": record.get("sale_date") or "",
                        "discontinued_date": record.get("discontinued_date") or "",
                        "detail_source_file": detail_source_file,
                        "document_key": document_key,
                        "document_type": link["document_type"],
                        "filename": link["filename"],
                        "download_url": link["download_url"],
                    }
                )

        if index % 5000 == 0:
            print(f"scanned {index:,}/{len(records):,} {bucket} records")

    documents = sorted(
        documents_by_id.values(),
        key=lambda item: (
            0 if item["priority"] == "core" else 1,
            item["document_type"],
            item["filename"],
            item["document_key"],
        ),
    )
    download_queue = [
        {
            "document_key": doc["document_key"],
            "download_url": doc["download_url"],
            "filename": doc["filename"],
            "extension": doc["extension"],
            "document_type": doc["document_type"],
            "priority": doc["priority"],
            "linked_policy_count": doc["linked_policy_count"],
            "status": "pending",
            "attempt_count": 0,
            "saved_path": "",
            "last_error": "",
        }
        for doc in documents
    ]

    summary = {
        "generated_at": generated_at,
        "bucket": bucket,
        "category_filter": category,
        "record_limit": limit,
        "policy_map_included": include_policy_map,
        "source": "local_saved_tii_detail_html",
        "records_total": counters["records_total"],
        "records_with_detail_file": counters["records_with_detail_file"],
        "records_missing_detail_file": counters["records_missing_detail_file"],
        "records_without_detail_path": counters["records_without_detail_path"],
        "records_with_documents": counters["records_with_documents"],
        "records_with_detail_no_documents": counters["records_with_detail_no_documents"],
        "document_links_total": counters["document_links_total"],
        "unique_documents": len(documents),
        "core_documents": sum(1 for doc in documents if doc["priority"] == "core"),
        "policy_terms_documents": sum(1 for doc in documents if doc["document_type"] == "policy_terms"),
        "product_summary_documents": sum(1 for doc in documents if doc["document_type"] == "product_summary"),
        "document_type_counts": {
            key.removeprefix("type:"): value for key, value in sorted(counters.items()) if key.startswith("type:")
        },
        "extension_counts": {
            key.removeprefix("extension:"): value
            for key, value in sorted(counters.items())
            if key.startswith("extension:")
        },
        "category_counts": {
            category: dict(counts) for category, counts in sorted(by_category.items(), key=lambda item: item[0])
        },
        "batch_counts": {batch: dict(counts) for batch, counts in sorted(by_batch.items(), key=lambda item: item[0])},
        "outputs": {
            "inventory": str(output_root / f"{bucket}-document-inventory.json"),
            "download_queue": str(output_root / f"{bucket}-download-queue.json"),
            "summary": str(output_root / f"{bucket}-document-summary.json"),
        },
        "notes": [
            "This phase reads saved local TII detail HTML and does not download official documents.",
            "Download URLs are TII Open2.ashx links extracted from saved detail pages.",
            "Classification is a planning hint and will be confirmed again from downloaded document content.",
        ],
    }

    return {
        "summary": summary,
        "documents": documents,
        "policy_documents": policy_documents if include_policy_map else [],
        "download_queue": download_queue,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory official TII document links from saved detail HTML.")
    parser.add_argument("--bucket", choices=["life", "property"], default="life")
    parser.add_argument("--category", default="", help="Optional record shard slug, for example health or injury.")
    parser.add_argument("--limit", type=int, default=0, help="Optional record limit for pilot runs.")
    parser.add_argument("--no-policy-map", action="store_true", help="Skip per-policy document mapping in inventory output.")
    parser.add_argument("--records-root", default="data/tii/records")
    parser.add_argument("--output-root", default="work/tii-document-inventory")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    result = inventory_documents(
        args.bucket,
        Path(args.records_root),
        output_root,
        category=args.category,
        limit=args.limit,
        include_policy_map=not args.no_policy_map,
    )
    run_slug = args.bucket
    if args.category:
        run_slug += f"-{args.category}"
    if args.limit:
        run_slug += f"-limit-{args.limit}"
    inventory_path = output_root / f"{run_slug}-document-inventory.json"
    queue_path = output_root / f"{run_slug}-download-queue.json"
    summary_path = output_root / f"{run_slug}-document-summary.json"
    result["summary"]["outputs"] = {
        "inventory": str(inventory_path),
        "download_queue": str(queue_path),
        "summary": str(summary_path),
    }

    inventory_size = write_json(
        inventory_path,
        {
            "summary": result["summary"],
            "documents": result["documents"],
            "policy_documents": result["policy_documents"],
        },
    )
    queue_size = write_json(
        queue_path,
        {"summary": result["summary"], "download_queue": result["download_queue"]},
    )
    summary_size = write_json(summary_path, result["summary"])
    print(
        json.dumps(
            {
                "bucket": args.bucket,
                "records_total": result["summary"]["records_total"],
                "document_links_total": result["summary"]["document_links_total"],
                "unique_documents": result["summary"]["unique_documents"],
                "core_documents": result["summary"]["core_documents"],
                "outputs": {
                    str(inventory_path): inventory_size,
                    str(queue_path): queue_size,
                    str(summary_path): summary_size,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
