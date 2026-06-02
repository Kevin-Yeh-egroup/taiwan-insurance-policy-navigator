from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pypdf import PdfReader


URL_RE = re.compile(r"https?://[^\s<>\]\)\"'，。；、]+", re.I)

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def clean_url(url: str) -> str:
    return url.rstrip(".,;:!?)]}>\"'，。；、")


def paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        if node.tag == f"{{{NS['w']}}}t" and node.text:
            parts.append(node.text)
        elif node.tag == f"{{{NS['w']}}}tab":
            parts.append("\t")
        elif node.tag == f"{{{NS['w']}}}br":
            parts.append("\n")
    return "".join(parts).strip()


def docx_relationships(zf: zipfile.ZipFile) -> dict[str, str]:
    rels_path = "word/_rels/document.xml.rels"
    if rels_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rels_path))
    rels: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        rel_type = rel.attrib.get("Type", "")
        if rid and target and "hyperlink" in rel_type:
            rels[rid] = target
    return rels


def extract_docx(path: Path, include_full_text: bool) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        rels = docx_relationships(zf)
        root = ET.fromstring(zf.read("word/document.xml"))

    paragraphs: list[str] = []
    links: list[dict[str, str]] = []
    seen_links: set[tuple[str, str]] = set()

    for paragraph in root.findall(".//w:p", NS):
        text = paragraph_text(paragraph)
        if text:
            paragraphs.append(text)

        for hyperlink in paragraph.findall(".//w:hyperlink", NS):
            rid = hyperlink.attrib.get(f"{{{NS['r']}}}id")
            target = rels.get(rid or "")
            link_text = paragraph_text(hyperlink)
            if target:
                key = (link_text, clean_url(target))
                if key not in seen_links:
                    seen_links.add(key)
                    links.append({"text": link_text, "url": clean_url(target)})

        for match in URL_RE.findall(text):
            url = clean_url(match)
            key = ("", url)
            if key not in seen_links:
                seen_links.add(key)
                links.append({"text": "", "url": url})

    record: dict[str, Any] = {
        "file": str(path),
        "kind": "docx",
        "title": path.stem,
        "paragraph_count": len(paragraphs),
        "link_count": len(links),
        "links": links,
        "text_preview": "\n".join(paragraphs[:20]),
    }
    if include_full_text:
        record["text"] = "\n".join(paragraphs)
    return record


def extract_pdf(path: Path, include_full_text: bool) -> dict[str, Any]:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages)
    links = [{"text": "", "url": clean_url(url)} for url in sorted(set(URL_RE.findall(full_text)))]
    record: dict[str, Any] = {
        "file": str(path),
        "kind": "pdf",
        "title": path.stem,
        "page_count": len(reader.pages),
        "link_count": len(links),
        "links": links,
        "text_preview": "\n".join(full_text.splitlines()[:40]),
    }
    if include_full_text:
        record["text"] = full_text
    return record


def load_input_paths(args: argparse.Namespace) -> list[Path]:
    paths: list[str] = []
    if args.input_list:
        data = json.loads(args.input_list.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            paths.extend(data.get("files", []))
        else:
            paths.extend(data)
    paths.extend(args.inputs or [])
    return [Path(path) for path in paths]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract URLs from local PDF/DOCX source files.")
    parser.add_argument("--input-list", type=Path, help="JSON file with a files array.")
    parser.add_argument("--inputs", nargs="*", help="One or more local PDF/DOCX paths.")
    parser.add_argument("--output", type=Path, default=Path("work/source-extraction/source-manifest.json"))
    parser.add_argument("--include-full-text", action="store_true")
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    for path in load_input_paths(args):
        if not path.exists():
            continue
        suffix = path.suffix.lower()
        if suffix == ".docx":
            records.append(extract_docx(path, args.include_full_text))
        elif suffix == ".pdf":
            records.append(extract_pdf(path, args.include_full_text))

    all_urls = sorted({link["url"] for record in records for link in record["links"]})
    output = {
        "generated_by": "scripts/extract_sources.py",
        "source_file_count": len(records),
        "total_unique_url_count": len(all_urls),
        "unique_urls": all_urls,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_file_count": len(records),
                "total_unique_url_count": len(all_urls),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
