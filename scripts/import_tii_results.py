from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))
DATE_PATTERN = re.compile(r"^\d{3}/\d{2}/\d{2}$")


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


def compact_cells(cells: list[str]) -> list[str]:
    return [cell.strip() for cell in cells if cell and cell.strip()]


def load_batch_meta(progress_path: Path) -> dict:
    if not progress_path.exists():
        return {}
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    return {run.get("batch_id"): run for run in progress.get("runs", [])}


def load_manual_batch_count(batch_plan_path: Path) -> int:
    if not batch_plan_path.exists():
        return 0
    plan = json.loads(batch_plan_path.read_text(encoding="utf-8"))
    return int(plan.get("summary", {}).get("tii_manual_matrix_batch_count", 0) or 0)


def normalize_company_label(label: str) -> str:
    return re.sub(r"^\d+-", "", label or "").strip()


def normalize_records(raw_records: list[dict], batch_meta: dict) -> list[dict]:
    normalized: list[dict] = []
    for raw in raw_records:
        cells = raw.get("cells")
        source_file = raw.get("source_file", "")
        batch_id = Path(source_file).stem
        run_meta = batch_meta.get(batch_id, {})
        if isinstance(cells, list):
            compact = compact_cells(cells)
            if len(compact) < 3 or compact[0] == "保險商品名稱":
                continue
            sale_date = next((cell for cell in compact if DATE_PATTERN.match(cell)), "")
            discontinued_date = ""
            for cell in reversed(compact):
                if DATE_PATTERN.match(cell):
                    if cell != sale_date:
                        discontinued_date = cell
                    break
            if not sale_date:
                continue
            product_name = compact[0]
            company = normalize_company_label(run_meta.get("company_label", ""))
            category = run_meta.get("category_label", "")
            sale_status = "已停售" if discontinued_date else "仍可投保或未標示停售"
        else:
            text = " | ".join(str(value) for value in raw.values())
            company = raw.get("公司名稱") or raw.get("公司") or ""
            product_name = raw.get("商品名稱") or raw.get("商品") or ""
            category = raw.get("保險類別") or run_meta.get("category_label", "")
            sale_date = raw.get("銷售日") or ""
            discontinued_date = raw.get("停售日") or ""
            sale_status = raw.get("停售狀態") or raw.get("狀態") or ("已停售" if "停售" in text else "不確定")

        if not product_name or product_name == "保險商品名稱":
            continue

        normalized.append(
            {
                "id": f"tii_policy_{len(normalized) + 1:06d}",
                "source_file": source_file,
                "source_batch_id": batch_id,
                "company": company,
                "insurance_category": category,
                "product_name": product_name,
                "sale_status": sale_status,
                "sale_date": sale_date,
                "discontinued_date": discontinued_date,
            }
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import manually saved TII result HTML/CSV after a human completes the captcha."
    )
    parser.add_argument("--input-dir", default="work/tii-results", help="Directory with saved .html/.csv result files")
    parser.add_argument("--output", default="data/tii-policy-results.json", help="Output JSON path")
    parser.add_argument("--progress", default="data/tii-execution-progress.json", help="TII execution progress JSON")
    parser.add_argument("--batch-plan", default="data/batch-plan.json", help="Batch plan JSON")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    raw_records: list[dict] = []
    for path in sorted(input_dir.glob("*")):
        if path.suffix.lower() in {".html", ".htm"}:
            raw_records.extend(parse_saved_html(path))
        elif path.suffix.lower() == ".csv":
            raw_records.extend(load_csv(path))

    batch_meta = load_batch_meta(Path(args.progress))
    manual_batch_count = load_manual_batch_count(Path(args.batch_plan))
    normalized_records = normalize_records(raw_records, batch_meta)
    completed_batches = sorted(
        {
            Path(record.get("source_file", "")).stem
            for record in normalized_records
            if record.get("source_file")
        }
    )

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source": "manually_saved_tii_query_results",
        "input_dir": str(input_dir),
        "record_count": len(normalized_records),
        "completed_batch_count": len(completed_batches),
        "completed_batches": completed_batches,
        "pending_manual_batch_count": max(manual_batch_count - len(completed_batches), 0),
        "records": normalized_records,
        "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha.",
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"record_count": output["record_count"], "output": args.output}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
