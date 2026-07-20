#!/usr/bin/env python3
"""Scan TII life-policy text for reviewable benefit-table candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCANNER_VERSION = "tii-benefit-candidates-v2"
SIGNAL_PATTERNS = {
    "benefit_heading": re.compile(r"【[^】]{0,80}(?:保險金|給付)[^】]{0,80}】\s*第"),
    "currency_amount": re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:萬元|元)"),
    "article_or_appendix": re.compile(r"(?:第\s*[一二三四五六七八九十百零〇\d]+\s*條|附表)"),
    "plan": re.compile(r"(?:計[劃畫]別|計[劃畫]\s*[A-D一二三四五六七八九十])"),
    "policy_unit": re.compile(r"(?:每\s*單位|投保\s*單位|單位\s*保險金額)"),
    "daily": re.compile(r"(?:住院日額|每日給付|每一日|/\s*日)"),
    "reimbursement": re.compile(r"(?:實支實付|醫療費用保險金限額|實際支付之醫療費用)"),
    "face_amount_formula": re.compile(
        r"(?:保險金額.{0,50}(?:倍|%|百分之)|按.{0,30}保險金額.{0,30}(?:給付|計算))"
    ),
}
STRUCTURE_SIGNALS = {
    "plan",
    "policy_unit",
    "daily",
    "reimbursement",
    "face_amount_formula",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_candidate_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def normalized_headings(text: str) -> list[str]:
    headings = []
    for heading in re.findall(r"【([^】]{1,100})】", text):
        compact = " ".join(heading.split())
        if "保險金" not in compact and "給付" not in compact:
            continue
        normalized = re.sub(r"\d[\d,]*(?:\.\d+)?", "#", compact)
        if normalized not in headings:
            headings.append(normalized)
        if len(headings) >= 16:
            break
    return headings


def candidate_from_document(
    batch_id: str,
    document: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    raw_text = str(document.get("text") or "")
    if not raw_text:
        return None
    text = normalize_candidate_text(raw_text)
    signals = [name for name, pattern in SIGNAL_PATTERNS.items() if pattern.search(text)]
    required = {"benefit_heading", "currency_amount", "article_or_appendix"}
    if not required.issubset(signals) or not STRUCTURE_SIGNALS.intersection(signals):
        return None

    text_hash = sha256_text(raw_text)
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    headings = normalized_headings(text)
    fingerprint_source = json.dumps(
        {
            "signals": sorted(STRUCTURE_SIGNALS.intersection(signals)),
            "headings": headings,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    first_heading = SIGNAL_PATTERNS["benefit_heading"].search(text)
    snippet_start = max(0, (first_heading.start() if first_heading else 0) - 120)
    snippet = " ".join(text[snippet_start : snippet_start + 720].split())
    candidate_id = sha256_text(
        "|".join([SCANNER_VERSION, batch_id, product_id, file_name, text_hash])
    )[:24]
    return {
        "candidate_id": candidate_id,
        "batch_id": batch_id,
        "product_id": product_id,
        "company": metadata.get("company") or metadata.get("company_name") or "",
        "product_name": metadata.get("product_name") or "",
        "insurance_category": metadata.get("insurance_category") or "",
        "source_file": file_name,
        "source_text_sha256": text_hash,
        "text_char_count": len(raw_text),
        "signals": signals,
        "benefit_headings": headings,
        "template_fingerprint": sha256_text(fingerprint_source)[:24],
        "evidence_preview": snippet,
        "status": "candidate",
    }


def scan_batch(
    batch_id: str,
    *,
    raw_dir: Path,
    content_dir: Path,
) -> list[dict[str, Any]]:
    raw_path = raw_dir / f"{batch_id}-text.json"
    content_path = content_dir / f"{batch_id}.json"
    if not raw_path.is_file() or not content_path.is_file():
        raise FileNotFoundError(f"missing input for {batch_id}")
    raw = read_json(raw_path)
    content = read_json(content_path)
    metadata = {
        str(record.get("product_id") or ""): record
        for record in content.get("records", [])
        if record.get("product_id")
    }
    structured_ids = {
        product_id
        for product_id, record in metadata.items()
        if record.get("coverage_entries")
        or any(plan.get("coverage_entries") for plan in record.get("plan_options") or [])
    }
    candidates = []
    for document in raw.get("documents", []):
        product_id = str(document.get("product_id") or "")
        if not product_id or product_id in structured_ids:
            continue
        candidate = candidate_from_document(
            batch_id,
            document,
            metadata.get(product_id, {}),
        )
        if candidate:
            candidates.append(candidate)
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", action="append", dest="batch_ids")
    parser.add_argument(
        "--raw-dir", type=Path, default=ROOT / "work" / "tii-document-text"
    )
    parser.add_argument(
        "--content-dir", type=Path, default=ROOT / "data" / "tii" / "document-content"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "work" / "tii-benefit-candidates" / "candidates.json",
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    batch_ids = args.batch_ids or sorted(
        path.stem.removesuffix("-text")
        for path in args.raw_dir.glob("tii-life-*-text.json")
    )
    candidates = []
    for batch_id in batch_ids:
        candidates.extend(
            scan_batch(batch_id, raw_dir=args.raw_dir, content_dir=args.content_dir)
        )
    candidates.sort(
        key=lambda item: (
            -len(STRUCTURE_SIGNALS.intersection(item["signals"])),
            item["batch_id"],
            item["product_id"],
            item["source_file"],
        )
    )
    if args.limit is not None:
        candidates = candidates[: max(0, args.limit)]

    payload = {
        "schema_version": 1,
        "scanner_version": SCANNER_VERSION,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "batch_ids": batch_ids,
        "candidate_count": len(candidates),
        "template_count": len({item["template_fingerprint"] for item in candidates}),
        "candidates": candidates,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_count": len(batch_ids),
                "candidate_count": payload["candidate_count"],
                "template_count": payload["template_count"],
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
