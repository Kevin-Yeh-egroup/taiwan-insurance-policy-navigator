from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - dependency boundary
    raise SystemExit("Missing pypdf. Use the Codex Python runtime that includes pypdf.") from exc

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - optional fallback for legacy PDF encodings
    pdfium = None

try:
    import pymupdf
except ImportError:  # pragma: no cover - optional OCR renderer
    pymupdf = None


TAIPEI = timezone(timedelta(hours=8))
logging.getLogger("pypdf").setLevel(logging.ERROR)

DOCUMENT_TYPES = {
    "A": "policy_terms",
    "F": "product_summary",
    "B": "premium_rate",
    "C": "application_form",
    "E": "attachment",
    "K": "attachment",
}

COVERAGE_RULES = [
    {
        "label": "年金險",
        "name_terms": ["年金", "利率變動型年金"],
        "text_terms": ["年金給付", "年金金額", "年金保單價值準備金"],
        "category_terms": ["年金"],
    },
    {
        "label": "壽險",
        "name_terms": ["壽險", "終身壽險", "定期壽險", "生存保險", "死亡保險"],
        "text_terms": [],
        "category_terms": ["人壽"],
    },
    {
        "label": "醫療險",
        "name_terms": ["醫療", "住院", "手術", "日額", "實支", "健康"],
        "text_terms": ["住院醫療", "手術醫療", "醫療費用", "病房費用", "門診醫療"],
        "category_terms": ["健康"],
    },
    {
        "label": "意外險",
        "name_terms": ["傷害", "意外", "平安", "燒燙傷", "骨折"],
        "text_terms": ["傷害保險金", "燒燙傷保險金", "骨折保險金"],
        "category_terms": ["傷害"],
    },
    {
        "label": "癌症險",
        "name_terms": ["癌症", "防癌", "腫瘤"],
        "text_terms": ["癌症保險金", "惡性腫瘤", "原位癌"],
        "category_terms": [],
    },
    {
        "label": "重大疾病險",
        "name_terms": ["重大疾病", "重大傷病", "特定疾病", "特定傷病"],
        "text_terms": ["重大疾病保險金", "重大傷病保險金", "特定疾病保險金", "特定傷病保險金"],
        "category_terms": [],
    },
    {
        "label": "長照險",
        "name_terms": ["長期照顧", "長照", "失智", "認知功能障礙"],
        "text_terms": ["長期照顧保險金", "長照保險金", "認知功能障礙"],
        "category_terms": [],
    },
    {
        "label": "失能/殘扶",
        "name_terms": ["失能", "殘廢", "生活扶助"],
        "text_terms": ["失能扶助保險金", "殘廢生活扶助", "殘廢保險金"],
        "category_terms": [],
    },
    {
        "label": "豁免/附加條款",
        "name_terms": ["豁免", "附加條款", "附約", "批註條款"],
        "text_terms": ["豁免保險費"],
        "category_terms": [],
    },
]

FOCUS_GROUPS = [
    {
        "key": "coverage",
        "label": "保障項目",
        "terms": [
            "給付項目",
            "保險範圍",
            "保險金",
            "住院",
            "手術",
            "門診",
            "醫療費用",
            "癌症",
            "重大疾病",
            "重大傷病",
            "長期照顧",
            "身故",
            "失能",
            "殘廢",
            "傷害",
            "海外突發疾病",
            "豁免保險費",
            "年金給付",
            "年金金額",
            "未支領之年金餘額",
        ],
    },
    {
        "key": "definitions",
        "label": "重要定義",
        "terms": [
            "名詞定義",
            "定義",
            "疾病",
            "傷害",
            "醫院",
            "醫師",
            "住院",
            "手術",
            "癌症",
            "重大疾病",
            "重大傷病",
            "等待期間",
            "意外傷害事故",
            "保證期間",
            "年金給付期間",
            "宣告利率",
            "預定利率",
        ],
    },
    {
        "key": "special",
        "label": "特殊項目",
        "terms": [
            "除外責任",
            "不保事項",
            "等待期間",
            "免責",
            "限制",
            "投保年齡",
            "續保",
            "保險期間",
            "給付限制",
            "同一次住院",
            "自負額",
            "既往症",
            "契約撤銷權",
            "年金給付開始日",
            "年金保單價值準備金",
            "變更年金給付開始日",
        ],
    },
    {
        "key": "claims",
        "label": "理賠申請",
        "terms": [
            "理賠",
            "申請",
            "保險金的申領",
            "申領",
            "檢具",
            "診斷證明書",
            "醫療費用收據",
            "病歷",
            "受益人",
            "通知",
        ],
    },
]


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def write_json(path: Path, data: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def write_progress(path: Path | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    write_json(path, payload)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def text_garble_ratio(text: str) -> float:
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return 0.0

    def is_readable(char: str) -> bool:
        codepoint = ord(char)
        if 0x3400 <= codepoint <= 0x4DBF or 0x4E00 <= codepoint <= 0x9FFF:
            return True
        if char.isascii() and char.isprintable():
            return True
        return char in "，。、；：！？「」『』（）《》〈〉【】—…．％・"

    suspicious = sum(not is_readable(char) for char in visible)
    return suspicious / len(visible)


def extract_pdfium_pages(path: Path, pages_to_parse: int) -> tuple[str, list[dict[str, Any]]]:
    if pdfium is None:
        return "", []
    parts: list[str] = []
    page_texts: list[dict[str, Any]] = []
    try:
        document = pdfium.PdfDocument(str(path))
        for index in range(min(len(document), pages_to_parse)):
            page = document[index]
            text_page = page.get_textpage()
            page_text = text_page.get_text_range()
            text_page.close()
            page.close()
            normalized = normalize_text(page_text)
            if normalized:
                parts.append(normalized)
                page_texts.append({"page": index + 1, "text": normalized})
        document.close()
    except Exception:
        return "", []
    return normalize_text(" ".join(parts)), page_texts


def normalize_ocr_text(text: str) -> str:
    normalized = normalize_text(text)
    return re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)


def extract_windows_ocr_pages(
    path: Path,
    pages_to_parse: int,
    *,
    evidence_output: Path | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    if os.name != "nt" or (pdfium is None and pymupdf is None):
        return "", []

    helper = Path(__file__).with_name("ocr_pdf_windows.ps1")
    if not helper.exists():
        return "", []

    try:
        with tempfile.TemporaryDirectory(prefix="tii-ocr-") as temp_dir:
            temp_root = Path(temp_dir)
            output_path = temp_root / "ocr.json"
            render_evidence: list[dict[str, Any]] = []
            renderer = "pymupdf" if pymupdf is not None else "pypdfium2"
            if pymupdf is not None:
                document = pymupdf.open(path)
                try:
                    for index in range(min(len(document), pages_to_parse)):
                        page = document[index]
                        width, height = page.rect.width, page.rect.height
                        max_dimension = max(width, height)
                        scale = min(2.0, 2200 / max_dimension) if max_dimension else 2.0
                        pixmap = page.get_pixmap(
                            matrix=pymupdf.Matrix(scale, scale),
                            alpha=False,
                        )
                        image_path = temp_root / f"page-{index + 1:04d}.png"
                        pixmap.save(image_path)
                        render_evidence.append(
                            {
                                "page": index + 1,
                                "render_scale": scale,
                                "pixel_width": pixmap.width,
                                "pixel_height": pixmap.height,
                                "png_sha256": hashlib.sha256(
                                    image_path.read_bytes()
                                ).hexdigest(),
                            }
                        )
                finally:
                    document.close()
            else:
                document = pdfium.PdfDocument(str(path))
                try:
                    for index in range(min(len(document), pages_to_parse)):
                        page = document[index]
                        width, height = page.get_size()
                        max_dimension = max(width, height)
                        scale = min(2.0, 2200 / max_dimension) if max_dimension else 2.0
                        bitmap = page.render(scale=scale)
                        image = bitmap.to_pil()
                        image_path = temp_root / f"page-{index + 1:04d}.png"
                        image.save(image_path)
                        render_evidence.append(
                            {
                                "page": index + 1,
                                "render_scale": scale,
                                "pixel_width": image.width,
                                "pixel_height": image.height,
                                "png_sha256": hashlib.sha256(
                                    image_path.read_bytes()
                                ).hexdigest(),
                            }
                        )
                        image.close()
                        bitmap.close()
                        page.close()
                finally:
                    document.close()

            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(helper),
                    "-ImageDirectory",
                    str(temp_root),
                    "-OutputPath",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(90, pages_to_parse * 20),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            if completed.returncode != 0 or not output_path.exists():
                return "", []

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            page_texts = []
            parts = []
            text_evidence: dict[int, dict[str, Any]] = {}
            for item in payload.get("pages", []):
                page_text = normalize_ocr_text(str(item.get("text") or ""))
                if not page_text:
                    continue
                page_number = int(item.get("page") or len(page_texts) + 1)
                page_texts.append({"page": page_number, "text": page_text})
                parts.append(page_text)
                text_evidence[page_number] = {
                    "ocr_text_char_count": len(page_text),
                    "ocr_text_sha256": hashlib.sha256(
                        page_text.encode("utf-8")
                    ).hexdigest(),
                    "text": page_text,
                }
            normalized_text = normalize_ocr_text(" ".join(parts))
            if evidence_output is not None:
                evidence_pages = []
                for item in render_evidence:
                    page_number = int(item["page"])
                    evidence_pages.append(
                        {
                            **item,
                            **text_evidence.get(
                                page_number,
                                {
                                    "ocr_text_char_count": 0,
                                    "ocr_text_sha256": "",
                                    "text": "",
                                },
                            ),
                        }
                    )
                evidence = {
                    "schema_version": 1,
                    "source_file": path.name,
                    "source_document_sha256": hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest(),
                    "renderer": renderer,
                    "ocr_language": payload.get("language") or "",
                    "page_count": len(evidence_pages),
                    "page_numbers": [
                        item["page"] for item in evidence_pages
                    ],
                    "normalized_text_char_count": len(normalized_text),
                    "normalized_text_sha256": hashlib.sha256(
                        normalized_text.encode("utf-8")
                    ).hexdigest(),
                    "pages": evidence_pages,
                }
                evidence_output.parent.mkdir(parents=True, exist_ok=True)
                evidence_output.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2)
                    + "\n",
                    encoding="utf-8",
                )
            return normalized_text, page_texts
    except Exception:
        return "", []


def classify_document(path: Path) -> str:
    match = re.search(r"-([A-Z])(?:\d+)?\.[^.]+$", path.name, flags=re.IGNORECASE)
    if not match:
        return "unknown"
    return DOCUMENT_TYPES.get(match.group(1).upper(), "attachment")


def detect_file_kind(path: Path, data: bytes) -> str:
    if data.startswith(b"%PDF-") or path.suffix.lower() == ".pdf":
        return "pdf"
    if data.startswith(b"\xd0\xcf\x11\xe0") or path.suffix.lower() == ".doc":
        return "doc"
    if data.startswith(b"PK\x03\x04") or path.suffix.lower() == ".docx":
        return "docx"
    return "unknown"


def extract_pdf_text(path: Path, max_pages: int) -> tuple[str, int, int, list[dict[str, Any]], str]:
    parts: list[str] = []
    page_texts: list[dict[str, Any]] = []
    pypdf_error: Exception | None = None
    try:
        reader = PdfReader(BytesIO(path.read_bytes()), strict=False)
        page_count = len(reader.pages)
        pages_to_parse = page_count if max_pages <= 0 else min(page_count, max_pages)
        for index in range(pages_to_parse):
            try:
                page_text = reader.pages[index].extract_text() or ""
            except Exception:
                page_text = ""
            normalized = normalize_text(page_text)
            if normalized:
                parts.append(normalized)
                page_texts.append({"page": index + 1, "text": normalized})
    except Exception as exc:
        pypdf_error = exc
        if pdfium is None:
            raise
        try:
            document = pdfium.PdfDocument(str(path))
            try:
                page_count = len(document)
            finally:
                document.close()
        except Exception:
            raise pypdf_error
        pages_to_parse = page_count if max_pages <= 0 else min(page_count, max_pages)

    text = normalize_text(" ".join(parts))
    extraction_method = "pypdf"
    if pypdf_error is not None or not text or text_garble_ratio(text) >= 0.2:
        fallback_text, fallback_pages = extract_pdfium_pages(path, pages_to_parse)
        if (
            len(fallback_text) >= 50
            and (
                not text
                or text_garble_ratio(fallback_text) + 0.1 < text_garble_ratio(text)
            )
        ):
            text = fallback_text
            page_texts = fallback_pages
            extraction_method = "pdfium"

    if not text or text_garble_ratio(text) >= 0.2:
        ocr_text, ocr_pages = extract_windows_ocr_pages(path, pages_to_parse)
        if len(ocr_text) >= 50 and text_garble_ratio(ocr_text) < 0.2:
            return ocr_text, page_count, pages_to_parse, ocr_pages, "windows_ocr"

    return text, page_count, pages_to_parse, page_texts, extraction_method if text else "none"


def extract_legacy_doc_text(data: bytes) -> tuple[str, list[dict[str, Any]]]:
    # Old binary .doc files often keep Traditional Chinese text in UTF-16LE streams.
    decoded = data.decode("utf-16le", errors="ignore")
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9，。、；：：「」『』（）()《》%％、／/\\\-\s]{8,}", decoded)
    cleaned: list[str] = []
    for chunk in chunks:
        normalized = normalize_text(chunk)
        cjk_count = sum(1 for char in normalized if "\u4e00" <= char <= "\u9fff")
        if cjk_count >= 4 and len(normalized) >= 10:
            cleaned.append(normalized)
    text = normalize_text(" ".join(cleaned))
    return text, [{"page": 1, "text": text}] if text else []


def compact_terms(terms: list[str], limit: int = 10) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        output.append(term)
        if len(output) >= limit:
            break
    return output


def snippet_for_term(text: str, term: str, radius: int = 42) -> str:
    index = text.find(term)
    if index < 0:
        return ""
    start = max(0, index - radius)
    end = min(len(text), index + len(term) + radius)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet += "..."
    return snippet


def detect_focus(page_texts: list[dict[str, Any]], document_label: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for group in FOCUS_GROUPS:
        term_pages: dict[str, set[int]] = defaultdict(set)
        snippets: list[dict[str, Any]] = []
        for page in page_texts:
            text = page["text"]
            for term in group["terms"]:
                if term in text:
                    term_pages[term].add(int(page["page"]))
                    if len(snippets) < 3:
                        snippet = snippet_for_term(text, term)
                        if snippet:
                            snippets.append(
                                {
                                    "document": document_label,
                                    "page": int(page["page"]),
                                    "term": term,
                                    "snippet": snippet,
                                }
                            )
        matched_terms = compact_terms([term for term in group["terms"] if term in term_pages])
        pages = sorted({page for term in matched_terms for page in term_pages.get(term, set())})[:8]
        cards.append(
            {
                "key": group["key"],
                "label": group["label"],
                "status": "detected" if matched_terms else "not_detected",
                "terms": matched_terms,
                "pages": pages,
                "evidence": snippets,
            }
        )
    return cards


def merge_focus(document_cards: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for group in FOCUS_GROUPS:
        terms: list[str] = []
        pages: set[int] = set()
        evidence: list[dict[str, Any]] = []
        for cards in document_cards:
            card = next((item for item in cards if item["key"] == group["key"]), None)
            if not card:
                continue
            terms.extend(card.get("terms") or [])
            pages.update(int(page) for page in card.get("pages") or [])
            evidence.extend(card.get("evidence") or [])
        compacted_terms = compact_terms(terms, 12)
        status = "detected" if compacted_terms else "not_detected"
        summary = (
            f"已從文件文字命中 {len(compacted_terms)} 個重點詞：{'、'.join(compacted_terms[:6])}。"
            if compacted_terms
            else "這批已下載文件未抽到明確文字命中，仍需回官方文件確認。"
        )
        merged.append(
            {
                "key": group["key"],
                "label": group["label"],
                "status": status,
                "summary": summary,
                "terms": compacted_terms,
                "pages": sorted(pages)[:8],
                "evidence": evidence[:5],
            }
        )
    return merged


def infer_coverage_tags(text: str, product_name: str, insurance_category: str) -> list[str]:
    tags = []
    for rule in COVERAGE_RULES:
        label = rule["label"]
        if any(term in product_name for term in rule["name_terms"]):
            tags.append(label)
            continue
        if any(term in insurance_category for term in rule["category_terms"]):
            tags.append(label)
            continue
        if any(term in text for term in rule["text_terms"]):
            tags.append(label)
    return tags


def infer_structured_coverage_tags(record: dict[str, Any]) -> list[str] | None:
    entries = list(record.get("coverage_entries") or [])
    for option in record.get("plan_options") or []:
        if isinstance(option, dict):
            entries.extend(option.get("coverage_entries") or [])
    if not entries:
        return None

    benefit_names = " ".join(
        str(entry.get("name") or "")
        for entry in entries
        if isinstance(entry, dict)
    )
    return infer_coverage_tags(
        benefit_names,
        str(record.get("product_name") or ""),
        str(record.get("insurance_category") or ""),
    )


def load_records(paths: list[Path]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records", []):
            product_id = str(record.get("product_id") or record.get("p") or "")
            if product_id:
                records[product_id] = record
    return records


def extract_document(path: Path, product_id: str, max_pages: int) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    file_kind = detect_file_kind(path, data)
    document_type = classify_document(path)
    base = {
        "file_name": path.name,
        "product_id": product_id,
        "document_type": document_type,
        "document_kind": file_kind,
        "file_size": path.stat().st_size,
        "page_count": None,
        "pages_parsed": 0,
        "text_char_count": 0,
        "extraction_status": "not_started",
        "extraction_method": None,
        "reader_focus": [],
        "error": None,
    }
    text = ""
    page_texts: list[dict[str, Any]] = []
    try:
        if file_kind == "pdf":
            text, page_count, pages_parsed, page_texts, extraction_method = extract_pdf_text(path, max_pages)
            base.update(
                {
                    "page_count": page_count,
                    "pages_parsed": pages_parsed,
                    "extraction_method": extraction_method,
                }
            )
        elif file_kind == "doc":
            text, page_texts = extract_legacy_doc_text(data)
            base.update({"pages_parsed": 1 if text else 0, "extraction_method": "legacy_doc"})
        elif file_kind == "docx":
            base.update({"extraction_status": "unsupported_docx"})
            return base, ""
        else:
            base.update({"extraction_status": "unsupported_file"})
            return base, ""

        extraction_status = "extracted" if text else "no_text"
        if file_kind == "pdf" and text and text_garble_ratio(text) >= 0.2:
            extraction_status = "garbled"
        focus = detect_focus(page_texts, path.name) if extraction_status == "extracted" else []
        base.update(
            {
                "text_char_count": len(text),
                "extraction_status": extraction_status,
                "reader_focus": focus,
            }
        )
        return base, text
    except Exception as exc:
        base.update({"extraction_status": "error", "error": str(exc)[:300]})
        return base, ""


def skipped_document(path: Path, product_id: str, reason: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "file_name": path.name,
        "product_id": product_id,
        "document_type": classify_document(path),
        "document_kind": detect_file_kind(path, data),
        "file_size": path.stat().st_size,
        "page_count": None,
        "pages_parsed": 0,
        "text_char_count": 0,
        "extraction_status": "skipped",
        "reader_focus": [],
        "error": reason,
    }


def build_product_record(
    product_id: str,
    documents: list[dict[str, Any]],
    texts: list[str],
    record_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_record = record_lookup.get(product_id, {})
    full_text = normalize_text(" ".join(texts))
    focus = merge_focus([doc.get("reader_focus") or [] for doc in documents])
    coverage_tags = infer_coverage_tags(
        full_text,
        str(source_record.get("product_name") or ""),
        str(source_record.get("insurance_category") or ""),
    )
    extracted_docs = [doc for doc in documents if doc["extraction_status"] == "extracted"]
    return {
        "product_id": product_id,
        "company": source_record.get("company", ""),
        "insurance_category": source_record.get("insurance_category", ""),
        "product_name": source_record.get("product_name", ""),
        "sale_status": source_record.get("sale_status", ""),
        "sale_date": source_record.get("sale_date", ""),
        "discontinued_date": source_record.get("discontinued_date", ""),
        "source_batch_id": source_record.get("source_batch_id", ""),
        "coverage_tags": coverage_tags,
        "document_count": len(documents),
        "extracted_document_count": len(extracted_docs),
        "text_char_count": sum(
            doc.get("text_char_count", 0)
            for doc in documents
            if doc["extraction_status"] == "extracted"
        ),
        "reader_focus": focus,
        "focus_score": sum(1 for card in focus if card["status"] == "detected"),
        "confidence": "parsed" if extracted_docs else "unreviewed",
        "documents": [
            {
                key: doc[key]
                for key in [
                    "file_name",
                    "document_type",
                    "document_kind",
                    "file_size",
                    "page_count",
                    "pages_parsed",
                    "text_char_count",
                    "extraction_status",
                    "extraction_method",
                    "error",
                ]
            }
            for doc in documents
        ],
    }


def summarize(records: list[dict[str, Any]], documents: list[dict[str, Any]], generated_at: str, batch_id: str) -> dict[str, Any]:
    extracted_documents = [doc for doc in documents if doc["extraction_status"] == "extracted"]
    focus_counts = Counter(
        card["label"]
        for record in records
        for card in record.get("reader_focus", [])
        if card.get("status") == "detected"
    )
    return {
        "generated_at": generated_at,
        "source": "local TII files downloaded through captcha session",
        "batch_id": batch_id,
        "scope_note": "Public output keeps summaries, terms, pages, and short evidence snippets only. Full extracted text stays in ignored work/ output.",
        "product_count": len(records),
        "document_count": len(documents),
        "extracted_document_count": len(extracted_documents),
        "no_text_document_count": sum(doc["extraction_status"] == "no_text" for doc in documents),
        "garbled_document_count": sum(doc["extraction_status"] == "garbled" for doc in documents),
        "ocr_document_count": sum(doc.get("extraction_method") == "windows_ocr" for doc in documents),
        "error_document_count": sum(doc["extraction_status"] == "error" for doc in documents),
        "pdf_document_count": sum(doc["document_kind"] == "pdf" for doc in documents),
        "legacy_doc_document_count": sum(doc["document_kind"] == "doc" for doc in documents),
        "policy_terms_document_count": sum(doc["document_type"] == "policy_terms" for doc in documents),
        "product_summary_document_count": sum(doc["document_type"] == "product_summary" for doc in documents),
        "total_text_characters": sum(doc.get("text_char_count", 0) for doc in extracted_documents),
        "focus_counts": [{"label": label, "count": count} for label, count in focus_counts.most_common()],
        "coverage_tag_counts": [
            {"label": label, "count": count}
            for label, count in Counter(tag for record in records for tag in record.get("coverage_tags", [])).most_common()
        ],
        "status_counts": [
            {"label": label, "count": count}
            for label, count in Counter(doc["extraction_status"] for doc in documents).most_common()
        ],
    }


REVIEWED_SCHEDULE_FIELDS = (
    "selection_type",
    "input_mode",
    "selection_source",
    "selection_label",
    "face_amount_label",
    "selection_guidance",
    "unit_fields",
    "version_characteristics",
    "plan_options",
    "coverage_entries",
)

REVIEWED_SOURCE_FIELDS = (
    "parser_id",
    "source_file",
    "source_document_sha256",
    "schedule_sha256",
    "reviewed_at",
)


def compact_document_summary(
    public_output: dict[str, Any],
    batch_id: str,
    reviewed_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reviewed_by_product_id = {
        str(record.get("product_id") or ""): record
        for record in (reviewed_records or [])
        if record.get("product_id")
    }
    records = []
    for record in public_output.get("records", []):
        product_id = str(record.get("product_id") or "")
        reviewed = reviewed_by_product_id.get(product_id)
        structured_tags = infer_structured_coverage_tags(record)
        summary = {
            "product_id": product_id,
            "coverage_tags": (
                structured_tags
                if structured_tags is not None
                else record.get("coverage_tags") or []
            ),
            "reader_focus": [
                {
                    key: card.get(key)
                    for key in ["key", "label", "summary", "terms"]
                }
                for card in record.get("reader_focus", [])
                if card.get("status") == "detected"
            ],
        }
        schedule_source = reviewed or record
        for field in REVIEWED_SCHEDULE_FIELDS:
            if schedule_source.get(field):
                summary[field] = schedule_source[field]
        if reviewed:
            for field in REVIEWED_SOURCE_FIELDS:
                if reviewed.get(field):
                    summary[field] = reviewed[field]
            summary["review_status"] = "verified_reference"
        records.append(summary)
    return {
        "generated_at": public_output.get("generated_at"),
        "batch_id": batch_id,
        "record_count": len(records),
        "records": records,
    }


def find_document_files(documents_root: Path, batch_id: str, limit: int | None) -> list[Path]:
    batch_root = documents_root / batch_id
    if not batch_root.exists():
        raise SystemExit(f"missing batch documents folder: {batch_root}")
    files = [
        path
        for path in sorted(batch_root.rglob("*"))
        if path.is_file() and path.name != "_document-download-status.json"
    ]
    return files[:limit] if limit else files


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract public-safe summaries from downloaded TII documents.")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--documents-root", type=Path, default=Path("work/tii-documents"))
    parser.add_argument("--records", type=Path, nargs="+", default=[Path("data/tii/records/life/health.json")])
    parser.add_argument("--output", type=Path, default=Path("data/tii/document-content-pilot.json"))
    parser.add_argument("--summary-output", type=Path, default=None)
    parser.add_argument("--raw-output", type=Path, default=Path("work/tii-document-text/document-text.json"))
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--progress-output", type=Path, default=None)
    parser.add_argument("--skip-file", action="append", default=[])
    args = parser.parse_args()

    generated_at = now_iso()
    record_lookup = load_records(args.records)
    files = find_document_files(args.documents_root, args.batch_id, args.limit)
    skip_files = {str(item) for item in args.skip_file}
    documents_by_product: dict[str, list[dict[str, Any]]] = defaultdict(list)
    texts_by_product: dict[str, list[str]] = defaultdict(list)
    raw_documents: list[dict[str, Any]] = []

    for index, path in enumerate(files, start=1):
        product_id = path.parent.name
        write_progress(
            args.progress_output,
            {
                "status": "running",
                "batch_id": args.batch_id,
                "current_index": index,
                "total_files": len(files),
                "current_file": str(path),
                "current_product_id": product_id,
                "updated_at": now_iso(),
            },
        )
        if str(path) in skip_files or path.name in skip_files:
            document = skipped_document(path, product_id, "manual_skip")
            text = ""
        else:
            document, text = extract_document(path, product_id, args.max_pages)
        documents_by_product[product_id].append(document)
        if text and document["extraction_status"] == "extracted":
            texts_by_product[product_id].append(text)
        raw_documents.append(
            {
                "product_id": product_id,
                "file_name": path.name,
                "document_type": document["document_type"],
                "document_kind": document["document_kind"],
                "extraction_status": document["extraction_status"],
                "text": text,
            }
        )
        write_progress(
            args.progress_output,
            {
                "status": "running",
                "batch_id": args.batch_id,
                "current_index": index,
                "total_files": len(files),
                "current_file": str(path),
                "current_product_id": product_id,
                "last_extraction_status": document["extraction_status"],
                "updated_at": now_iso(),
            },
        )

    records = [
        build_product_record(product_id, documents, texts_by_product.get(product_id, []), record_lookup)
        for product_id, documents in sorted(documents_by_product.items())
    ]
    all_documents = [doc for documents in documents_by_product.values() for doc in documents]
    public_output = {
        "generated_at": generated_at,
        "summary": summarize(records, all_documents, generated_at, args.batch_id),
        "records": records,
    }
    raw_output = {
        "generated_at": generated_at,
        "batch_id": args.batch_id,
        "scope_note": "Ignored local full text for extraction QA; do not publish.",
        "documents": raw_documents,
    }
    write_json(args.output, public_output)
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(
            json.dumps(compact_document_summary(public_output, args.batch_id), ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    write_json(args.raw_output, raw_output)
    write_progress(
        args.progress_output,
        {
            "status": "completed",
            "batch_id": args.batch_id,
            "total_files": len(files),
            "summary": public_output["summary"],
            "updated_at": now_iso(),
        },
    )
    print(json.dumps(public_output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
