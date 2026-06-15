from __future__ import annotations

import argparse
import csv
import json
import math
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

from build_tii_shards import build_shards, slim_results


TAIPEI = timezone(timedelta(hours=8))
DATE_PATTERN = re.compile(r"^\d{3}/\d{2}/\d{2}$")
TOTAL_PATTERN = re.compile(r"總共找到.*?([\d,]+).*?筆", re.DOTALL)


class TextTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_td = False
        self.in_tr = False
        self.current_cell: list[str] = []
        self.current_cell_links: list[str] = []
        self.current_row: list[str] = []
        self.current_row_links: list[str] = []
        self.rows: list[list[str]] = []
        self.records: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_tr = True
            self.current_row = []
            self.current_row_links = []
        elif tag in {"td", "th"} and self.in_tr:
            self.in_td = True
            self.current_cell = []
            self.current_cell_links = []
        elif tag == "a" and self.in_td:
            href = dict(attrs).get("href")
            if href:
                self.current_cell_links.append(href)

    def handle_data(self, data: str) -> None:
        if self.in_td:
            text = " ".join(data.split())
            if text:
                self.current_cell.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_td:
            self.current_row.append(" ".join(self.current_cell).strip())
            self.current_row_links.extend(self.current_cell_links)
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            if any(self.current_row):
                self.rows.append(self.current_row)
                self.records.append({"cells": self.current_row, "links": self.current_row_links})
            self.in_tr = False


def parse_saved_html(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    if "識別碼錯誤" in html:
        raise ValueError(f"{path} contains captcha error, not usable result data")

    parser = TextTableParser()
    parser.feed(html)
    records: list[dict] = []
    for parsed in parser.records:
        row = parsed["cells"]
        joined = " | ".join(row)
        has_product_link = any("DetailList.aspx?productId=" in link for link in parsed.get("links", []))
        if not has_product_link and not any(keyword in joined for keyword in ["商品", "保險", "停售", "銷售", "公司"]):
            continue
        if len(row) < 3:
            continue
        records.append({"source_file": path.name, "cells": row, "links": parsed.get("links", [])})
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


def company_markers(label: str) -> list[str]:
    normalized = normalize_company_label(label)
    if not normalized:
        return []
    markers = {normalized}
    short = normalized
    for suffix in [
        "人壽保險股份有限公司",
        "產物保險股份有限公司",
        "保險股份有限公司",
        "股份有限公司",
    ]:
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            if short:
                markers.add(short)
    return sorted((marker for marker in markers if len(marker) >= 2), key=len, reverse=True)


def load_batch_plan(batch_plan_path: Path) -> dict:
    if not batch_plan_path.exists():
        return {}
    plan = json.loads(batch_plan_path.read_text(encoding="utf-8"))
    return {batch.get("id"): batch for batch in plan.get("tii_manual_matrix_batches", [])}


def expected_company_label(batch_id: str, batch_meta: dict, batch_plan: dict) -> str:
    run = batch_meta.get(batch_id, {})
    planned = batch_plan.get(batch_id, {})
    return run.get("company_label") or planned.get("company_label") or ""


def expected_company_code(batch_id: str, batch_meta: dict, batch_plan: dict) -> str:
    run = batch_meta.get(batch_id, {})
    planned = batch_plan.get(batch_id, {})
    query_hint = run.get("query_hint") or planned.get("query_hint") or {}
    return str(query_hint.get("CompanyID") or planned.get("company_code") or "").strip()


def source_batch_id(source_file: str) -> str:
    stem = Path(source_file).stem
    return re.sub(r"-page-\d+$", "", stem)


def html_matches_batch_company(path: Path, batch_meta: dict, batch_plan: dict) -> bool:
    batch_id = source_batch_id(path.name)
    html = path.read_text(encoding="utf-8", errors="replace")
    if "DetailList.aspx?productId=" not in html:
        return True
    markers = company_markers(expected_company_label(batch_id, batch_meta, batch_plan))
    if markers and any(marker in html for marker in markers):
        return True
    expected_code = expected_company_code(batch_id, batch_meta, batch_plan)
    product_ids = re.findall(r"productId=([^&\"'>]+)", html)
    if expected_code and product_ids:
        matching = sum(1 for product_id in product_ids if product_id.startswith(expected_code))
        return matching / len(product_ids) >= 0.6
    if not markers:
        return True
    return any(marker in html for marker in markers)


def invalid_page_sources(input_dir: Path, batch_meta: dict, batch_plan: dict) -> dict[str, list[str]]:
    invalid: dict[str, list[str]] = {}
    for path in sorted(input_dir.glob("tii-*-page-*.html")):
        if html_matches_batch_company(path, batch_meta, batch_plan):
            continue
        invalid.setdefault(source_batch_id(path.name), []).append(path.name)
    return invalid


def product_id_from_links(links: list[str]) -> tuple[str, str]:
    for link in links:
        match = re.search(r"productId=([^&\"'>]+)", link)
        if match:
            product_id = match.group(1)
            return product_id, urllib.parse.urljoin("https://insprod.tii.org.tw/", link)
    return "", ""


def product_ids_from_result_page(path: Path) -> list[str]:
    product_ids: list[str] = []
    for record in parse_saved_html(path):
        product_id, _ = product_id_from_links(record.get("links", []))
        if product_id:
            product_ids.append(product_id)
    return product_ids


def result_total_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = TOTAL_PATTERN.search(text)
    return int(match.group(1).replace(",", "")) if match else 0


def result_expected_counts(input_dir: Path, batch_meta: dict, batch_plan: dict) -> dict[str, dict]:
    counts: dict[str, dict] = {}
    for path in sorted(input_dir.glob("tii-*.html")):
        if re.search(r"-page-\d+\.html$", path.name) and not html_matches_batch_company(path, batch_meta, batch_plan):
            continue
        batch_id = source_batch_id(path.name)
        html = path.read_text(encoding="utf-8", errors="replace")
        total_count = result_total_count(html)
        if total_count:
            counts.setdefault(batch_id, {})["expected_total_count"] = total_count
        if re.search(r"-page-\d+\.html$", path.name):
            batch_counts = counts.setdefault(batch_id, {})
            batch_counts.setdefault("saved_pages", set()).add(path.name)
            page_product_ids = product_ids_from_result_page(path)
            batch_counts.setdefault("page_record_counts", []).append(len(page_product_ids))
            batch_counts["official_row_count"] = int(batch_counts.get("official_row_count") or 0) + len(page_product_ids)
            batch_counts.setdefault("unique_product_ids", set()).update(page_product_ids)
    normalized: dict[str, dict] = {}
    for batch_id, value in counts.items():
        saved_pages = value.get("saved_pages", set())
        expected_total_count = int(value.get("expected_total_count") or 0)
        official_row_count = int(value.get("official_row_count") or 0)
        unique_product_ids = value.get("unique_product_ids", set())
        unique_product_id_count = len(unique_product_ids)
        page_size = max(value.get("page_record_counts") or [0])
        normalized[batch_id] = {
            "expected_total_count": expected_total_count,
            "expected_total_pages": math.ceil(expected_total_count / page_size) if expected_total_count and page_size else 0,
            "official_row_count": official_row_count,
            "expected_unique_product_id_count": unique_product_id_count,
            "duplicate_product_id_count": max(official_row_count - unique_product_id_count, 0),
            "saved_page_count": len(saved_pages),
        }
    return normalized


def load_detail_files(details_dir: Path) -> dict[str, str]:
    if not details_dir.exists():
        return {}
    detail_files: dict[str, str] = {}
    for path in sorted(details_dir.glob("tii-*/*.html")):
        detail_files.setdefault(path.stem, str(path))
        detail_files[f"{path.parent.name}:{path.stem}"] = str(path)
    return detail_files


def record_identity_key(
    product_id: str,
    company: str,
    category: str,
    product_name: str,
    sale_date: str,
    discontinued_date: str,
) -> str:
    if product_id:
        return f"tii-product-id:{product_id}"
    fallback = "|".join([company, category, product_name, sale_date, discontinued_date])
    return f"tii-fallback:{fallback}"


def add_same_name_metadata(records: list[dict]) -> None:
    groups: dict[tuple[str, str], set[str]] = {}
    for record in records:
        key = (record.get("company", ""), record.get("product_name", ""))
        product_id = record.get("product_id", "")
        if key[0] and key[1] and product_id:
            groups.setdefault(key, set()).add(product_id)
    same_name_counts = {key: len(product_ids) for key, product_ids in groups.items() if len(product_ids) > 1}
    for record in records:
        count = same_name_counts.get((record.get("company", ""), record.get("product_name", "")), 1)
        record["same_name_product_id_count"] = count
        record["same_name_version_note"] = (
            f"同公司同名商品有 {count} 個不同 productId；請依銷售日、停售日、productId 與官方明細分別判讀。"
            if count > 1
            else ""
        )


def normalize_records(raw_records: list[dict], batch_meta: dict, detail_files: dict[str, str]) -> list[dict]:
    normalized: list[dict] = []
    seen_product_ids_by_batch: dict[str, set[str]] = {}
    for raw in raw_records:
        cells = raw.get("cells")
        source_file = raw.get("source_file", "")
        batch_id = source_batch_id(source_file)
        run_meta = batch_meta.get(batch_id, {})
        product_id, detail_url = product_id_from_links(raw.get("links", []))
        if isinstance(cells, list):
            compact = compact_cells(cells)
            if len(compact) < 3 or compact[0] == "保險商品名稱":
                continue
            date_cells = [cell for cell in compact if DATE_PATTERN.match(cell)]
            sale_date = date_cells[0] if date_cells else ""
            discontinued_date = date_cells[-1] if len(date_cells) > 1 else ""
            status_cell = next((cell for cell in reversed(compact) if "銷售" in cell or "停售" in cell), "")
            if not sale_date and not product_id:
                continue
            product_name = compact[0]
            company = normalize_company_label(run_meta.get("company_label", ""))
            category = run_meta.get("category_label", "")
            sale_status = status_cell or ("已停售" if discontinued_date else "仍可投保或未標示停售")
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
        if product_id:
            seen_product_ids = seen_product_ids_by_batch.setdefault(batch_id, set())
            if product_id in seen_product_ids:
                continue
            seen_product_ids.add(product_id)
        detail_source_file = detail_files.get(f"{batch_id}:{product_id}") or detail_files.get(product_id, "")

        normalized.append(
            {
                "id": f"tii_policy_{len(normalized) + 1:06d}",
                "source_file": source_file,
                "source_batch_id": batch_id,
                "company": company,
                "insurance_category": category,
                "product_id": product_id,
                "record_identity_key": record_identity_key(
                    product_id,
                    company,
                    category,
                    product_name,
                    sale_date,
                    discontinued_date,
                ),
                "identity_basis": "tii_product_id" if product_id else "company_category_name_dates",
                "detail_url": detail_url,
                "detail_saved": bool(detail_source_file),
                "detail_source_file": detail_source_file,
                "product_name": product_name,
                "sale_status": sale_status,
                "sale_date": sale_date,
                "discontinued_date": discontinued_date,
                "edition_label": (
                    f"銷售日 {sale_date or '未標示'}｜停售日 {discontinued_date or '未標示'}"
                    f"｜productId {product_id or '未標示'}"
                ),
            }
        )
    add_same_name_metadata(normalized)
    return normalized


def batch_summaries(
    records: list[dict],
    batch_meta: dict,
    expected_counts: dict[str, dict],
    invalid_sources: dict[str, list[str]],
) -> list[dict]:
    by_batch: dict[str, list[dict]] = {}
    for record in records:
        by_batch.setdefault(record["source_batch_id"], []).append(record)
    summaries: list[dict] = []
    zero_result_batches = {
        batch_id
        for batch_id, run in batch_meta.items()
        if run.get("status") == "submitted_result_saved"
        and int((run.get("fetched_pages") or {}).get("total_count") or 0) == 0
        and (run.get("fetched_pages") or {}).get("is_complete")
    }
    for batch_id in sorted(set(by_batch) | zero_result_batches | set(invalid_sources)):
        batch_records = by_batch.get(batch_id, [])
        run = batch_meta.get(batch_id, {})
        fetched_pages = run.get("fetched_pages") or {}
        fallback = expected_counts.get(batch_id, {})
        expected_count = int(fetched_pages.get("total_count") or fallback.get("expected_total_count") or 0)
        official_row_count = int(fetched_pages.get("official_row_count") or fallback.get("official_row_count") or 0)
        saved_pages = fetched_pages.get("saved_pages") or []
        saved_page_count = int(fetched_pages.get("saved_page_count") or 0) or len(saved_pages) or int(
            fallback.get("saved_page_count") or 0
        )
        imported_count = len(batch_records)
        unique_count = len({record.get("product_id") for record in batch_records if record.get("product_id")})
        expected_unique_count = int(
            fetched_pages.get("unique_product_id_count")
            or fallback.get("expected_unique_product_id_count")
            or unique_count
            or 0
        )
        duplicate_product_id_count = int(
            fetched_pages.get("duplicate_product_id_count")
            or fallback.get("duplicate_product_id_count")
            or max(official_row_count - unique_count, 0)
        )
        detail_saved_count = sum(1 for record in batch_records if record.get("detail_saved"))
        detail_expected_count = expected_unique_count or unique_count
        detail_missing_count = max(detail_expected_count - detail_saved_count, 0)
        detail_coverage_rate = round(detail_saved_count / detail_expected_count, 4) if detail_expected_count else 0
        expected_pages = int(fetched_pages.get("total_pages") or fallback.get("expected_total_pages") or 0)
        page_content_mismatch_count = len(invalid_sources.get(batch_id, []))
        complete_by_unique_count = bool(expected_count and unique_count == expected_count and imported_count == expected_count)
        complete_by_official_rows = bool(
            expected_count
            and official_row_count == expected_count
            and unique_count == imported_count
            and unique_count == expected_unique_count
            and (not expected_pages or saved_page_count >= expected_pages)
            and page_content_mismatch_count == 0
        )
        complete_by_no_results = bool(
            run.get("status") == "submitted_result_saved"
            and fetched_pages.get("is_complete")
            and expected_count == 0
            and official_row_count == 0
            and imported_count == 0
        )
        if page_content_mismatch_count:
            status = "partial_index"
        elif complete_by_no_results:
            status = "complete"
        elif expected_count and (complete_by_unique_count or complete_by_official_rows):
            status = "complete"
            if not expected_pages:
                expected_pages = saved_page_count
        elif expected_count and imported_count < expected_count:
            status = "partial_index"
        else:
            status = "indexed_no_expected_total"
        summaries.append(
            {
                "batch_id": batch_id,
                "status": status,
                "expected_total_count": expected_count,
                "expected_total_pages": expected_pages,
                "official_row_count": official_row_count,
                "saved_page_count": saved_page_count,
                "imported_record_count": imported_count,
                "unique_product_id_count": unique_count,
                "expected_unique_product_id_count": expected_unique_count,
                "duplicate_product_id_count": duplicate_product_id_count,
                "detail_expected_count": detail_expected_count,
                "detail_saved_count": detail_saved_count,
                "detail_missing_count": detail_missing_count,
                "detail_coverage_rate": detail_coverage_rate,
                "page_content_mismatch_count": page_content_mismatch_count,
                "page_content_mismatch_sample": invalid_sources.get(batch_id, [])[:10],
                "detail_status": "complete" if detail_missing_count == 0 else "partial_detail",
                "requires_fresh_captcha_session": status != "complete",
                "requires_detail_backfill_session": detail_missing_count > 0,
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import manually saved TII result HTML/CSV after a human completes the captcha."
    )
    parser.add_argument("--input-dir", default="work/tii-results", help="Directory with saved .html/.csv result files")
    parser.add_argument("--output", default="data/tii-policy-results.json", help="Output JSON path")
    parser.add_argument("--progress", default="data/tii-execution-progress.json", help="TII execution progress JSON")
    parser.add_argument("--batch-plan", default="data/batch-plan.json", help="Batch plan JSON")
    parser.add_argument("--details-dir", default="work/tii-details", help="Directory with saved TII detail HTML files")
    parser.add_argument("--shard-root", default="data/tii", help="Directory for sharded TII public data")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    batch_meta = load_batch_meta(Path(args.progress))
    batch_plan = load_batch_plan(Path(args.batch_plan))
    invalid_sources = invalid_page_sources(input_dir, batch_meta, batch_plan)
    raw_records: list[dict] = []
    for path in sorted(input_dir.glob("*")):
        if not path.name.startswith("tii-"):
            continue
        if path.suffix.lower() in {".html", ".htm"}:
            if re.search(r"-page-\d+\.html$", path.name) and not html_matches_batch_company(
                path, batch_meta, batch_plan
            ):
                continue
            raw_records.extend(parse_saved_html(path))
        elif path.suffix.lower() == ".csv":
            raw_records.extend(load_csv(path))

    manual_batch_count = load_manual_batch_count(Path(args.batch_plan))
    detail_files = load_detail_files(Path(args.details_dir))
    normalized_records = normalize_records(raw_records, batch_meta, detail_files)
    expected_counts = result_expected_counts(input_dir, batch_meta, batch_plan)
    summaries = batch_summaries(normalized_records, batch_meta, expected_counts, invalid_sources)
    indexed_batches = [summary["batch_id"] for summary in summaries]
    completed_batches = [summary["batch_id"] for summary in summaries if summary["status"] == "complete"]
    detail_expected_count = sum(summary.get("detail_expected_count", 0) for summary in summaries)
    detail_saved_count = sum(1 for record in normalized_records if record.get("detail_saved"))
    detail_missing_count = sum(summary.get("detail_missing_count", 0) for summary in summaries)

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source": "manually_saved_tii_query_results",
        "input_dir": str(input_dir),
        "record_count": len(normalized_records),
        "detail_expected_count": detail_expected_count,
        "detail_saved_count": detail_saved_count,
        "detail_missing_count": detail_missing_count,
        "detail_coverage_rate": round(detail_saved_count / detail_expected_count, 4) if detail_expected_count else 0,
        "indexed_batch_count": len(indexed_batches),
        "indexed_batches": indexed_batches,
        "completed_batch_count": len(completed_batches),
        "completed_batches": completed_batches,
        "partial_batch_count": sum(1 for summary in summaries if summary["status"] != "complete"),
        "page_content_mismatch_batch_count": len(invalid_sources),
        "page_content_mismatch_sources": invalid_sources,
        "batch_summaries": summaries,
        "pending_manual_batch_count": max(manual_batch_count - len(completed_batches), 0),
        "records": normalized_records,
        "compliance_note": "This importer parses files saved after a human completes TII captcha. It does not automate or bypass captcha.",
    }
    manifest = build_shards(output, Path(args.shard_root))
    slim_output = slim_results(output, manifest)
    Path(args.output).write_text(json.dumps(slim_output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        json.dumps(
            {
                "record_count": output["record_count"],
                "output": args.output,
                "manifest": str(Path(args.shard_root) / "manifest.json"),
                "index_shards": len(manifest.get("index_shards", [])),
                "record_shards": len(manifest.get("record_shards", [])),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
