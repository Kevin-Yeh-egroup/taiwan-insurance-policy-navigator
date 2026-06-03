from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse


TAIPEI = timezone(timedelta(hours=8))
MANIFEST_PATH = Path("work/source-extraction/source-manifest.json")
OUTPUT_PATH = Path("data/policy-insights.json")


TYPE_ALIASES = {
    "健康醫療險": "健康險",
    "健康保險": "健康險",
    "醫療險": "健康險",
    "年金保險": "年金險",
    "終身壽險": "壽險",
    "投資型壽險": "壽險",
    "傳統型壽險": "壽險",
    "傷害保險": "傷害險",
}


def clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip(" -：:*")


def grab(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.S)
    return clean(match.group(1)) if match else ""


def status_from_block(block: str) -> str:
    match = re.search(r"是否停售：(?P<sale>.*)", block, re.S)
    if not match:
        return "不確定"
    sale_text = match.group("sale")
    marker = r"\[\s*(?:✅|x|X|v|V|✓)\s*\]"
    if re.search(marker + r"\s*是", sale_text):
        return "已停售"
    if re.search(marker + r"\s*否", sale_text):
        return "仍可投保"
    if re.search(marker + r"\s*不確定", sale_text):
        return "不確定"
    return "不確定"


def normalize_type(policy_type: str) -> str:
    value = clean(policy_type)
    return TYPE_ALIASES.get(value, value or "未分類")


def infer_content_flags(text: str) -> list[str]:
    candidates = {
        "理賠/給付": ["理賠", "給付", "保險金", "申請文件"],
        "名詞定義": ["名詞定義", "定義", "醫院", "住院", "手術"],
        "等待期/免責期": ["等待期", "免責期", "等待期間"],
        "除外責任": ["除外責任", "不保事項", "不予給付"],
        "保費/續保": ["保費", "費率", "續保", "復效", "停效"],
        "投保限制": ["投保年齡", "職業類別", "健康告知", "最高保額"],
    }
    flags: list[str] = []
    for label, keywords in candidates.items():
        if any(keyword in text for keyword in keywords):
            flags.append(label)
    return flags


def parse_policy_blocks(manifest: dict) -> list[dict]:
    policies: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for record in manifest.get("records", []):
        text = str(record.get("text", "")).replace("\u00a0", " ")
        blocks = re.split(r"(?=保險公司名稱：)", text)
        for block in blocks:
            if "商品名稱" not in block:
                continue
            company = (
                grab(r"保險公司名稱：\s*(.*?)(?:\s*-\s*\*\*商品名稱|\s*商品名稱)", block)
                or clean(record.get("title"))
            )
            product_name = grab(r"商品名稱：\s*(.*?)(?:\s*-\s*\*\*商品類型|\s*商品類型|\n|---)", block)
            raw_type = (
                grab(r"商品類型：\*\*\s*(.*?)(?:（例|---|\n)", block)
                or grab(r"商品類型：\s*(.*?)(?:（例|---|\n)", block)
            )
            policy_url = (
                grab(r"條款下載頁 URL：\*\*\s*(https?://\S+)", block)
                or grab(r"條款下載頁 URL：\s*(https?://\S+)", block)
            )
            version_text = grab(
                r"條款版本或公告日期：\*\*\s*(.*?)(?:（如：|-\s*\*\*是否停售|是否停售)",
                block,
            )
            if not product_name:
                continue

            key = (company, product_name, policy_url)
            if key in seen:
                continue
            seen.add(key)
            policies.append(
                {
                    "id": f"policy_{len(policies) + 1:06d}",
                    "company": company,
                    "product_name": product_name,
                    "product_type": normalize_type(raw_type),
                    "raw_product_type": clean(raw_type),
                    "sale_status": status_from_block(block),
                    "policy_url": policy_url,
                    "source_domain": urlparse(policy_url).netloc if policy_url else "",
                    "version_text": version_text,
                    "source_document_title": clean(record.get("title")),
                    "content_flags": infer_content_flags(block),
                }
            )
    return policies


def count_rows(counter: Counter, limit: int | None = None) -> list[dict]:
    rows = [{"label": label, "count": count} for label, count in counter.most_common(limit)]
    return rows


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"missing {MANIFEST_PATH}; run scripts/extract_sources.py first")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    policies = parse_policy_blocks(manifest)
    status_counts = Counter(policy["sale_status"] for policy in policies)
    type_counts = Counter(policy["product_type"] for policy in policies)
    company_counts = Counter(policy["company"] for policy in policies)
    content_flag_counts = Counter(flag for policy in policies for flag in policy["content_flags"])

    discontinued = [policy for policy in policies if policy["sale_status"] == "已停售"]
    unknown = [policy for policy in policies if policy["sale_status"] == "不確定"]

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source": {
            "kind": "local_extracted_documents",
            "manifest": "work/source-extraction/source-manifest.json",
            "public_note": "Derived from user-provided source documents; local raw text is not published.",
        },
        "summary": {
            "policy_count": len(policies),
            "company_count": len(company_counts),
            "type_count": len(type_counts),
            "discontinued_count": status_counts.get("已停售", 0),
            "current_count": status_counts.get("仍可投保", 0),
            "unknown_count": status_counts.get("不確定", 0),
        },
        "status_counts": count_rows(status_counts),
        "type_counts": count_rows(type_counts, 14),
        "company_counts": count_rows(company_counts, 16),
        "content_flag_counts": count_rows(content_flag_counts),
        "discontinued_policies": discontinued[:80],
        "unknown_status_policies": unknown[:80],
        "policies": policies,
        "limitations": [
            "此資料來自現有文件欄位整理，尚未代表保發中心停售查詢全量資料。",
            "可開啟或停售狀態仍需回官方條款、保險公司或保發中心查詢結果確認。",
            "理賠、定義、等待期、除外責任等內容旗標為文字線索，尚未完成逐條專業審閱。",
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
