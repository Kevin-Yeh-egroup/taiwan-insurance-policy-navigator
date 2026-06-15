from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CATEGORY_SLUGS = {
    "傷害保險": "injury",
    "健康保險": "health",
    "傳統型壽險": "traditional-life",
    "傳統型年金": "traditional-annuity",
    "投資型壽險": "investment-life",
    "投資型年金": "investment-annuity",
    "火災保險": "fire",
    "汽車保險": "auto",
    "海上保險": "marine",
    "意外保險": "accident",
}

BUCKET_LABELS = {
    "life": "壽險/人身保險",
    "property": "產險/財產保險",
    "other": "其他",
}

INDEX_SCHEMA = {
    "i": "id",
    "b": "source_batch_id",
    "c": "company",
    "k": "insurance_category",
    "p": "product_id",
    "n": "product_name",
    "s": "sale_status",
    "sd": "sale_date",
    "dd": "discontinued_date",
    "e": "edition_label",
    "v": "same_name_product_id_count",
    "d": "detail_saved",
}


def write_json(path: Path, data: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def bucket_for_record(record: dict[str, Any]) -> str:
    batch_id = str(record.get("source_batch_id") or "")
    if batch_id.startswith("tii-life-"):
        return "life"
    if batch_id.startswith("tii-property-"):
        return "property"
    return "other"


def slug_for_category(category: str) -> str:
    if category in CATEGORY_SLUGS:
        return CATEGORY_SLUGS[category]
    value = re.sub(r"\s+", "-", category.strip().lower())
    value = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff-]+", "", value).strip("-")
    return value or "uncategorized"


def compact_index_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "i": record.get("id", ""),
        "b": record.get("source_batch_id", ""),
        "c": record.get("company", ""),
        "k": record.get("insurance_category", ""),
        "p": record.get("product_id", ""),
        "n": record.get("product_name", ""),
        "s": record.get("sale_status", ""),
        "sd": record.get("sale_date", ""),
        "dd": record.get("discontinued_date", ""),
        "e": record.get("edition_label", ""),
        "v": int(record.get("same_name_product_id_count") or 1),
        "d": bool(record.get("detail_saved")),
    }


def same_name_counts(records: list[dict[str, Any]]) -> tuple[int, int]:
    groups: dict[tuple[str, str], set[str]] = {}
    for record in records:
        key = (str(record.get("company") or ""), str(record.get("product_name") or ""))
        product_id = str(record.get("product_id") or "")
        if key[0] and key[1] and product_id:
            groups.setdefault(key, set()).add(product_id)
    version_groups = {key: ids for key, ids in groups.items() if len(ids) > 1}
    version_cards = sum(1 for record in records if int(record.get("same_name_product_id_count") or 0) > 1)
    return len(version_groups), version_cards


def build_shards(tii_results: dict[str, Any], output_root: Path = Path("data/tii")) -> dict[str, Any]:
    records = list(tii_results.get("records") or [])
    generated_at = str(tii_results.get("generated_at") or "")
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        bucket = bucket_for_record(record)
        category = str(record.get("insurance_category") or "未分類")
        groups.setdefault((bucket, category), []).append(record)

    index_shards: list[dict[str, Any]] = []
    record_shards: list[dict[str, Any]] = []
    category_counts: list[dict[str, Any]] = []
    bucket_counts: dict[str, int] = {}
    company_counts: dict[str, int] = {}
    total_index_bytes = 0
    total_record_bytes = 0

    for (bucket, category), items in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1])):
        slug = slug_for_category(category)
        shard_id = f"{bucket}-{slug}"
        index_path = Path("data") / "tii" / "index" / bucket / f"{slug}.json"
        record_path = Path("data") / "tii" / "records" / bucket / f"{slug}.json"
        index_payload = {
            "generated_at": generated_at,
            "shard_id": shard_id,
            "bucket": bucket,
            "bucket_label": BUCKET_LABELS.get(bucket, bucket),
            "category": category,
            "record_count": len(items),
            "schema": INDEX_SCHEMA,
            "records": [compact_index_record(record) for record in items],
        }
        record_payload = {
            "generated_at": generated_at,
            "shard_id": shard_id,
            "bucket": bucket,
            "bucket_label": BUCKET_LABELS.get(bucket, bucket),
            "category": category,
            "record_count": len(items),
            "records": items,
        }
        index_bytes = write_json(index_path, index_payload)
        record_bytes = write_json(record_path, record_payload)
        total_index_bytes += index_bytes
        total_record_bytes += record_bytes
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + len(items)
        for record in items:
            company = str(record.get("company") or "")
            if company:
                company_counts[company] = company_counts.get(company, 0) + 1
        index_shards.append(
            {
                "id": shard_id,
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS.get(bucket, bucket),
                "category": category,
                "path": index_path.as_posix(),
                "record_count": len(items),
                "bytes": index_bytes,
            }
        )
        record_shards.append(
            {
                "id": shard_id,
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS.get(bucket, bucket),
                "category": category,
                "path": record_path.as_posix(),
                "record_count": len(items),
                "bytes": record_bytes,
            }
        )
        category_counts.append(
            {
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS.get(bucket, bucket),
                "category": category,
                "record_count": len(items),
                "index_shard_id": shard_id,
                "record_shard_id": shard_id,
            }
        )

    same_name_group_count, same_name_card_count = same_name_counts(records)
    manifest = {
        "generated_at": generated_at,
        "source": tii_results.get("source", "manually_saved_tii_query_results"),
        "record_count": len(records),
        "detail_expected_count": int(tii_results.get("detail_expected_count") or 0),
        "detail_saved_count": int(tii_results.get("detail_saved_count") or 0),
        "detail_missing_count": int(tii_results.get("detail_missing_count") or 0),
        "detail_coverage_rate": float(tii_results.get("detail_coverage_rate") or 0),
        "indexed_batch_count": int(tii_results.get("indexed_batch_count") or 0),
        "completed_batch_count": int(tii_results.get("completed_batch_count") or 0),
        "pending_manual_batch_count": int(tii_results.get("pending_manual_batch_count") or 0),
        "same_name_version_group_count": same_name_group_count,
        "same_name_version_card_count": same_name_card_count,
        "bucket_counts": [
            {
                "bucket": bucket,
                "bucket_label": BUCKET_LABELS.get(bucket, bucket),
                "record_count": count,
            }
            for bucket, count in sorted(bucket_counts.items())
        ],
        "category_counts": category_counts,
        "company_counts": [
            {"company": company, "record_count": count}
            for company, count in sorted(company_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "index_schema": INDEX_SCHEMA,
        "index_shards": index_shards,
        "record_shards": record_shards,
        "total_index_bytes": total_index_bytes,
        "total_record_bytes": total_record_bytes,
    }
    write_json(output_root / "manifest.json", manifest)
    return manifest


def slim_results(tii_results: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    output = {key: value for key, value in tii_results.items() if key != "records"}
    output.update(
        {
            "record_count": int(manifest.get("record_count") or 0),
            "records_are_sharded": True,
            "tii_manifest_path": "data/tii/manifest.json",
            "tii_index_shard_count": len(manifest.get("index_shards", [])),
            "tii_record_shard_count": len(manifest.get("record_shards", [])),
            "tii_total_index_bytes": int(manifest.get("total_index_bytes") or 0),
            "tii_total_record_bytes": int(manifest.get("total_record_bytes") or 0),
            "same_name_version_group_count": int(manifest.get("same_name_version_group_count") or 0),
            "same_name_version_card_count": int(manifest.get("same_name_version_card_count") or 0),
            "records": [],
            "record_storage_note": "Full TII records are split into data/tii/records shards; compact search records are split into data/tii/index shards.",
        }
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Split TII policy records into category shards.")
    parser.add_argument("--input", default="data/tii-policy-results.json")
    parser.add_argument("--output", default="data/tii-policy-results.json")
    parser.add_argument("--output-root", default="data/tii")
    args = parser.parse_args()

    source = Path(args.input)
    tii_results = json.loads(source.read_text(encoding="utf-8"))
    if not tii_results.get("records"):
        raise SystemExit(f"{args.input} has no records to shard")
    manifest = build_shards(tii_results, Path(args.output_root))
    slim = slim_results(tii_results, manifest)
    write_json(Path(args.output), slim)
    print(
        json.dumps(
            {
                "record_count": slim["record_count"],
                "manifest": "data/tii/manifest.json",
                "index_shards": slim["tii_index_shard_count"],
                "record_shards": slim["tii_record_shard_count"],
                "slim_output": args.output,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
