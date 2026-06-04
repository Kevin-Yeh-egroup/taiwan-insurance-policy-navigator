from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any


try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - dependency boundary
    raise SystemExit(
        "Missing pypdf. Run with the bundled Codex Python runtime or install pypdf in the active Python environment."
    ) from exc


TAIPEI = timezone(timedelta(hours=8))
USER_AGENT = "TaiwanPolicyNavigatorBot/0.3 (policy-content-extraction)"

FIELD_KEYWORDS = {
    "理賠/給付": ["理賠", "給付", "保險金", "給付項目", "申請文件", "受益人"],
    "名詞定義": ["名詞定義", "定義", "醫院", "住院", "手術", "疾病", "傷害"],
    "等待期/免責期": ["等待期", "免責期", "等待期間"],
    "除外責任": ["除外責任", "不保事項", "不予給付", "除外"],
    "保費/續保": ["保費", "費率", "續保", "保證續保", "復效", "停效"],
    "投保限制": ["投保年齡", "職業類別", "健康告知", "給付上限", "最高保額"],
}

FOCUS_GROUPS = [
    {
        "key": "coverage",
        "label": "保障項目",
        "reader_question": "這張保單主要賠什麼、保障哪些事故或狀態？",
        "empty_note": "未在已解析頁面命中明確保障詞，請回官方條款確認給付項目。",
        "terms": [
            "給付項目",
            "給付",
            "保險金",
            "住院",
            "手術",
            "醫療",
            "身故",
            "失能",
            "重大疾病",
            "重大傷病",
            "癌症",
            "長期照顧",
            "燒燙傷",
            "傷害",
            "意外",
            "年金",
        ],
    },
    {
        "key": "definitions",
        "label": "重要定義",
        "reader_question": "條款怎麼定義住院、手術、疾病、傷害等關鍵字？",
        "empty_note": "未在已解析頁面命中明確定義詞，仍需查看官方條款的名詞定義章節。",
        "terms": [
            "名詞定義",
            "定義",
            "醫院",
            "住院",
            "手術",
            "疾病",
            "傷害",
            "癌症",
            "重大疾病",
            "重大傷病",
            "長期照顧",
            "失能",
        ],
    },
    {
        "key": "special",
        "label": "特殊項目",
        "reader_question": "有哪些等待期、除外責任、續保、投保限制或給付上限？",
        "empty_note": "未在已解析頁面命中特殊限制詞，請仍以官方條款為準。",
        "terms": [
            "除外責任",
            "不保事項",
            "不予給付",
            "等待期",
            "等待期間",
            "免責期",
            "給付上限",
            "最高保額",
            "投保年齡",
            "職業類別",
            "健康告知",
            "保證續保",
            "續保",
            "停效",
            "復效",
            "保費",
        ],
    },
    {
        "key": "claims",
        "label": "理賠申請",
        "reader_question": "出事時可能需要哪些申請、證明或受益人資訊？",
        "empty_note": "未在已解析頁面命中理賠申請詞，請回官方條款確認申請文件。",
        "terms": [
            "理賠",
            "申請文件",
            "保險金申請",
            "診斷證明",
            "醫療費用收據",
            "收據",
            "事故通知",
            "受益人",
        ],
    },
]


class HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def iri_to_uri(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/%:@")
    query = urllib.parse.quote(urllib.parse.unquote(parsed.query), safe="=&?/:;+,%@")
    fragment = urllib.parse.quote(urllib.parse.unquote(parsed.fragment), safe="=&?/:;+,%@")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, fragment))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "big5", "cp950"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def flatten_policy_results(policy_batch_results: dict[str, Any]) -> list[dict[str, Any]]:
    return [result for batch in policy_batch_results.get("batches", []) for result in batch.get("results", [])]


def is_pdf_record(result: dict[str, Any]) -> bool:
    content_type = str(result.get("content_type") or "").lower()
    url = str(result.get("final_url") or result.get("policy_url") or "").lower()
    return "pdf" in content_type or url.endswith(".pdf")


def fetch_bytes(url: str, timeout: int, max_bytes: int | None = None) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        iri_to_uri(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,text/html,application/xhtml+xml,*/*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(max_bytes) if max_bytes else response.read()
        return body, response.headers.get("content-type", ""), response.geturl()


def extract_pdf_text(data: bytes, max_pages: int) -> tuple[str, int, int, list[dict[str, Any]]]:
    reader = PdfReader(BytesIO(data), strict=False)
    page_count = len(reader.pages)
    pages_to_parse = page_count if max_pages <= 0 else min(page_count, max_pages)
    parts: list[str] = []
    page_texts: list[dict[str, Any]] = []
    for index in range(pages_to_parse):
        try:
            page_text = reader.pages[index].extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            normalized = normalize_text(page_text)
            parts.append(normalized)
            page_texts.append({"page": index + 1, "text": normalized})
    return normalize_text(" ".join(parts)), page_count, pages_to_parse, page_texts


def extract_html_text(data: bytes) -> str:
    parser = HtmlTextParser()
    parser.feed(decode_bytes(data))
    return parser.text()


def detect_fields(text: str, fallback_flags: list[str] | None = None) -> tuple[list[str], list[str]]:
    hits = set(fallback_flags or [])
    matched_terms: set[str] = set()
    for label, terms in FIELD_KEYWORDS.items():
        for term in terms:
            if term in text:
                hits.add(label)
                matched_terms.add(term)
    return sorted(hits), sorted(matched_terms)


def compact_terms(terms: list[str], limit: int = 10) -> list[str]:
    seen = set()
    compacted: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        compacted.append(term)
        if len(compacted) >= limit:
            break
    return compacted


def detect_focus(page_texts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    focus_cards: list[dict[str, Any]] = []
    for group in FOCUS_GROUPS:
        term_pages: dict[str, set[int]] = {}
        for page in page_texts:
            text = page["text"]
            for term in group["terms"]:
                if term in text:
                    term_pages.setdefault(term, set()).add(int(page["page"]))

        matched_terms = compact_terms([term for term in group["terms"] if term in term_pages])
        pages = sorted({page for term in matched_terms for page in term_pages.get(term, set())})[:8]
        status = "detected" if matched_terms else "not_detected"
        if matched_terms:
            summary = f"已命中 {len(matched_terms)} 個重點詞：{'、'.join(matched_terms[:6])}。"
        else:
            summary = group["empty_note"]
        focus_cards.append(
            {
                "key": group["key"],
                "label": group["label"],
                "reader_question": group["reader_question"],
                "status": status,
                "summary": summary,
                "terms": matched_terms,
                "pages": pages,
            }
        )
    return focus_cards


def build_record(result: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    url = result.get("final_url") or result.get("policy_url") or ""
    base = {
        "policy_id": result.get("policy_id"),
        "company": result.get("company"),
        "product_name": result.get("product_name"),
        "product_type": result.get("product_type"),
        "sale_status": result.get("sale_status"),
        "policy_url": result.get("policy_url"),
        "final_url": url,
        "source_content_type": result.get("content_type"),
        "source_status": result.get("status"),
        "extracted_at": now_iso(),
        "document_kind": "pdf" if is_pdf_record(result) else "html",
        "page_count": None,
        "pages_parsed": 0,
        "text_char_count": 0,
        "field_hits": [],
        "matched_terms": [],
        "extraction_status": "not_started",
        "confidence": "unreviewed",
        "error": None,
    }

    try:
        if base["document_kind"] == "pdf":
            data, content_type, final_url = fetch_bytes(url, args.timeout)
            text, page_count, pages_parsed, page_texts = extract_pdf_text(data, args.max_pdf_pages)
            base.update(
                {
                    "final_url": final_url,
                    "source_content_type": content_type or base["source_content_type"],
                    "page_count": page_count,
                    "pages_parsed": pages_parsed,
                }
            )
        else:
            data, content_type, final_url = fetch_bytes(url, args.timeout, args.max_html_bytes)
            text = extract_html_text(data)
            page_texts = [{"page": 1, "text": text}] if text else []
            base.update(
                {
                    "final_url": final_url,
                    "source_content_type": content_type or base["source_content_type"],
                    "pages_parsed": 1,
                }
            )

        field_hits, matched_terms = detect_fields(text, result.get("detected_flags", []))
        reader_focus = detect_focus(page_texts)
        base.update(
            {
                "text_char_count": len(text),
                "field_hits": field_hits,
                "matched_terms": matched_terms[:20],
                "reader_focus": reader_focus,
                "focus_score": sum(1 for card in reader_focus if card["status"] == "detected"),
                "extraction_status": "extracted" if text else "no_text",
                "confidence": "parsed" if text and field_hits else "sampled" if text else "unreviewed",
            }
        )
    except Exception as exc:
        base.update({"extraction_status": "error", "error": str(exc)[:300]})
    return base


def count_rows(counter: Counter, limit: int = 12) -> list[dict[str, Any]]:
    return [{"label": label, "count": count} for label, count in counter.most_common(limit)]


def summarize(records: list[dict[str, Any]], candidates: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    extracted = [record for record in records if record["extraction_status"] == "extracted"]
    with_fields = [record for record in extracted if record["field_hits"]]
    return {
        "generated_at": generated_at,
        "source": "data/policy-batch-results.json",
        "scope_note": "Only URLs that were already ok and robots-allowed are fetched. TII captcha result pages are not bypassed.",
        "candidate_count": len(candidates),
        "record_count": len(records),
        "extracted_text_count": len(extracted),
        "records_with_field_hits": len(with_fields),
        "pdf_record_count": sum(record["document_kind"] == "pdf" for record in records),
        "html_record_count": sum(record["document_kind"] == "html" for record in records),
        "total_text_characters": sum(record["text_char_count"] for record in extracted),
        "field_counts": count_rows(Counter(field for record in extracted for field in record["field_hits"])),
        "focus_counts": count_rows(
            Counter(card["label"] for record in extracted for card in record.get("reader_focus", []) if card["status"] == "detected")
        ),
        "company_counts": count_rows(Counter(record["company"] for record in extracted)),
        "product_type_counts": count_rows(Counter(record["product_type"] for record in extracted)),
        "status_counts": count_rows(Counter(record["sale_status"] for record in records)),
        "error_count": sum(record["extraction_status"] == "error" for record in records),
        "no_text_count": sum(record["extraction_status"] == "no_text" for record in records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured proof from already reachable policy pages and PDFs.")
    parser.add_argument("--input", type=Path, default=Path("data/policy-batch-results.json"))
    parser.add_argument("--output", type=Path, default=Path("data/policy-content-extracts.json"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-pdf-pages", type=int, default=12, help="0 means all pages")
    parser.add_argument("--max-html-bytes", type=int, default=524288)
    args = parser.parse_args()

    policy_batch_results = json.loads(args.input.read_text(encoding="utf-8"))
    all_results = flatten_policy_results(policy_batch_results)
    candidates = [result for result in all_results if result.get("ok") and result.get("robots_allowed") is True]
    if args.limit:
        candidates = candidates[: args.limit]

    generated_at = now_iso()
    records: list[dict[str, Any]] = []
    for index, result in enumerate(candidates, start=1):
        records.append(build_record(result, args))
        if args.delay and index < len(candidates):
            time.sleep(args.delay)

    output = {
        "generated_at": generated_at,
        "summary": summarize(records, candidates, generated_at),
        "records": records,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
