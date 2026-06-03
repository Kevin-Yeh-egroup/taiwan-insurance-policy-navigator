from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))


class TextTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_td = False
        self.in_tr = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
        elif tag in {"td", "th"} and self.in_tr:
            self.in_td = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_td:
            text = " ".join(data.split())
            if text:
                self.current_cell.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_td:
            self.current_row.append(" ".join(self.current_cell).strip())
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            if any(self.current_row):
                self.rows.append(self.current_row)
            self.in_tr = False


def parse_saved_html(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "識別碼錯誤" in html:
        raise ValueError(f"{path} contains captcha error, not usable result data")

    parser = TextTableParser()
    parser.feed(html)
    rows = parser.rows
    records: list[dict] = []
    for row in rows:
        joined = " | ".join(row)
        if not any(keyword in joined for keyword in ["商品", "保險", "停售", "銷售", "公司"]):
            continue
        if len(row) < 3:
            continue
        records.append({"source_file": path.name, "cells": row})
    return records


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row, source_file=path.name) for row in csv.DictReader(handle)]


def normalize_records(raw_records: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for index, raw in enumerate(raw_records, start=1):
        cells = raw.get("cells")
        if isinstance(cells, list):
            text = " | ".join(cells)
            company = next((cell for cell in cells if "保險" in cell and "商品" not in cell), "")
            product_name = next((cell for cell in cells if "商品" in cell), "") or (cells[1] if len(cells) > 1 else "")
            sale_status = "已停售" if "停售" in text else "不確定"
        else:
            text = " | ".join(str(value) for value in raw.values())
            company = raw.get("公司名稱") or raw.get("公司") or ""
            product_name = raw.get("商品名稱") or raw.get("商品") or ""
            sale_status = raw.get("停售狀態") or raw.get("狀態") or ("已停售" if "停售" in text else "不確定")

        normalized.append(
            {
                "id": f"tii_policy_{index:06d}",
                "source_file": raw.get("source_file", ""),
                "company": company,
                "product_name": product_name,
                "sale_status": sale_status,
                "raw_text": re.sub(r"\s+", " ", text).strip(),
            }
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import manually saved TII result HTML/CSV after a human completes the captcha."
    )
    parser.add_argument("--input-dir", default="work/tii-results", help="Directory with saved .html/.csv result files")
    parser.add_argument("--output", default="data/tii-policy-results.json", help="Output JSON path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    raw_records: list[dict] = []
    for path in sorted(input_dir.glob("*")):
        if path.suffix.lower() in {".html", ".htm"}:
            raw_records.extend(parse_saved_html(path))
        elif path.suffix.lower() == ".csv":
            raw_records.extend(load_csv(path))

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source": "manually_saved_tii_query_results",
        "input_dir": str(input_dir),
        "record_count": len(raw_records),
        "records": normalize_records(raw_records),
        "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha.",
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"record_count": output["record_count"], "output": args.output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
