from __future__ import annotations

import argparse
import json
import math
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from http.cookiejar import MozillaCookieJar
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))
DEFAULT_BATCH_PLAN = Path("data/batch-plan.json")
DEFAULT_PROGRESS = Path("data/tii-execution-progress.json")
DEFAULT_WORK_DIR = Path("work/tii-execution")
DEFAULT_RESULTS_DIR = Path("work/tii-results")
DEFAULT_DETAILS_DIR = Path("work/tii-details")
TOTAL_PATTERN = re.compile(r"總共找到.*?([\d,]+).*?筆", re.DOTALL)
INVALID_DETAIL_MARKERS = ["識別碼錯誤", "錯誤"]


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict] = []
        self.current_form: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "form":
            self.current_form = {
                "attrs": attr,
                "inputs": {},
                "selects": {},
            }
            return
        if not self.current_form:
            return
        if tag == "input":
            name = attr.get("name") or attr.get("id")
            if name:
                self.current_form["inputs"][name] = attr.get("value", "")
        elif tag == "select":
            name = attr.get("name") or attr.get("id")
            if name:
                self.current_form["selects"][name] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self.current_form:
            self.forms.append(self.current_form)
            self.current_form = None


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attr = {key: value or "" for key, value in attrs}
        src = attr.get("src", "")
        if "bmp" in src.lower() or "captcha" in src.lower():
            self.sources.append(src)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if "DetailList.aspx?productId=" in href:
            self.links.append(href)


def now() -> str:
    return datetime.now(TAIPEI).isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_batch(plan: dict, batch_id: str) -> dict:
    for batch in plan.get("tii_manual_matrix_batches", []) + plan.get("tii_priority_batches", []):
        if batch.get("id") == batch_id:
            return batch
    raise SystemExit(f"Unknown TII batch id: {batch_id}")


def opener(cookie_path: Path | None = None) -> tuple[urllib.request.OpenerDirector, MozillaCookieJar]:
    cookie_jar = MozillaCookieJar(str(cookie_path)) if cookie_path else MozillaCookieJar()
    if cookie_path and cookie_path.exists():
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar)), cookie_jar


def read_url(client: urllib.request.OpenerDirector, url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 policy-navigator-manual-runner"})
    with client.open(request, timeout=30) as response:
        return response.read(), response.geturl()


def post_url(client: urllib.request.OpenerDirector, url: str, payload: dict) -> tuple[bytes, str]:
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 policy-navigator-manual-runner",
        },
    )
    with client.open(request, timeout=30) as response:
        return response.read(), response.geturl()


def save_cookies(cookie_jar: MozillaCookieJar, cookie_path: Path) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookie_jar.save(ignore_discard=True, ignore_expires=True)


def image_suffix(content: bytes, fallback: str) -> str:
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"BM"):
        return ".bmp"
    if content.startswith(b"\x89PNG"):
        return ".png"
    return fallback or ".img"


def parse_forms(html: str) -> list[dict]:
    parser = FormParser()
    parser.feed(html)
    return parser.forms


def parse_captcha_sources(html: str, base_url: str) -> list[str]:
    parser = ImageParser()
    parser.feed(html)
    return [urllib.parse.urljoin(base_url, src) for src in parser.sources]


def parse_detail_links(html: str, base_url: str = "https://insprod.tii.org.tw/") -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for product_id, url in parse_detail_link_rows(html, base_url):
        if product_id in seen:
            continue
        seen.add(product_id)
        links.append((product_id, url))
    return links


def parse_detail_link_rows(html: str, base_url: str = "https://insprod.tii.org.tw/") -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(html)
    links: list[tuple[str, str]] = []
    for href in parser.links:
        match = re.search(r"productId=([^&\"'>]+)", href)
        if not match:
            continue
        product_id = match.group(1)
        links.append((product_id, urllib.parse.urljoin(base_url, href)))
    return links


def build_payload(form: dict, batch: dict, captcha: str | None) -> dict:
    payload = dict(form.get("inputs", {}))
    payload.update(batch.get("query_hint", {}))
    payload.setdefault("qry_beginDate_SD1", "")
    payload.setdefault("qry_beginDate_SD2", "")
    payload.setdefault("qry_endDate_ED1", "")
    payload.setdefault("qry_endDate_ED2", "")
    payload.setdefault("endDate2", "")
    payload.setdefault("fQueryAll", "")
    if captcha is not None:
        payload["bmpC"] = captcha
    return payload


def classify_result(html: str, captcha: str | None) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", html)
    if captcha is None:
        return "captcha_required", "Fetched official form and captcha image; no captcha was provided, so the batch is not completed."
    if any(marker in text for marker in ["識別碼錯誤", "驗證碼", "captcha", "Captcha"]):
        return "captcha_failed_or_required", "Official site did not return usable result data; captcha may be missing or incorrect."
    if any(marker in text for marker in ["商品", "保險", "停售", "查詢結果"]):
        return "submitted_result_saved", "Official site returned a result-like page and it was saved for import."
    return "submitted_unknown_response", "Official site returned a page, but the result format needs manual review."


def result_total_count(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = TOTAL_PATTERN.search(text)
    return int(match.group(1).replace(",", "")) if match else 0


def ensure_result_page(html: str, batch_id: str) -> None:
    if "DetailList.aspx?productId=" not in html:
        raise SystemExit(f"{batch_id} result page does not contain policy detail links; refusing to mark it completed.")


def fetch_result_pages(
    client: urllib.request.OpenerDirector,
    batch_id: str,
    results_dir: Path,
    page_size: int = 10,
    max_pages: int = 500,
) -> dict:
    result_file = results_dir / f"{batch_id}.html"
    if result_file.exists():
        page_one_html = result_file.read_text(encoding="utf-8", errors="replace")
    else:
        page_one_bytes, _ = read_url(client, "https://insprod.tii.org.tw/ResultQueryAll.aspx?page=1")
        page_one_html = page_one_bytes.decode("utf-8", errors="replace")
    ensure_result_page(page_one_html, batch_id)
    page_one_path = results_dir / f"{batch_id}-page-001.html"
    page_one_path.write_text(page_one_html, encoding="utf-8")
    total_count = result_total_count(page_one_html)
    detected_page_size = page_one_html.count("DetailList.aspx?productId=") or page_size
    page_size = detected_page_size
    total_pages = max(math.ceil(total_count / page_size), 1)
    if total_pages > max_pages:
        raise SystemExit(
            f"{batch_id} result set needs {total_pages} pages, over max_pages={max_pages}. "
            "The TII session may have lost the intended query filters."
        )
    saved_pages = [str(page_one_path)]
    for page in range(2, total_pages + 1):
        page_bytes, _ = read_url(
            client,
            f"https://insprod.tii.org.tw/ResultQueryAll.aspx?page={page}",
        )
        page_html = page_bytes.decode("utf-8", errors="replace")
        ensure_result_page(page_html, batch_id)
        page_path = results_dir / f"{batch_id}-page-{page:03d}.html"
        page_path.write_text(page_html, encoding="utf-8")
        saved_pages.append(str(page_path))
    product_id_rows = [
        product_id
        for path in saved_pages
        for product_id, _ in parse_detail_link_rows(Path(path).read_text(encoding="utf-8", errors="replace"))
    ]
    unique_product_ids = set(product_id_rows)
    official_row_count = len(product_id_rows)
    duplicate_product_id_count = max(official_row_count - len(unique_product_ids), 0)
    pages_complete = bool(total_pages and len(saved_pages) == total_pages)
    complete_by_unique_count = bool(total_count and len(unique_product_ids) == total_count)
    complete_by_official_rows = bool(total_count and official_row_count == total_count and pages_complete)
    if total_count and not (complete_by_unique_count or complete_by_official_rows):
        raise SystemExit(
            f"{batch_id} saved {official_row_count} official rows / {len(unique_product_ids)} unique product ids, expected {total_count}. "
            "Refusing to mark the batch complete."
        )
    return {
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "official_row_count": official_row_count,
        "unique_product_id_count": len(unique_product_ids),
        "duplicate_product_id_count": duplicate_product_id_count,
        "saved_page_count": len(saved_pages),
        "saved_page_sample": saved_pages[:20],
        "is_complete": bool(total_count and (complete_by_unique_count or complete_by_official_rows)),
    }


def fetch_detail_pages(
    client: urllib.request.OpenerDirector,
    batch_id: str,
    results_dir: Path,
    details_dir: Path,
    limit: int = 0,
    delay_seconds: float = 0.2,
) -> dict:
    detail_root = details_dir / batch_id
    detail_root.mkdir(parents=True, exist_ok=True)
    result_paths = sorted(results_dir.glob(f"{batch_id}-page-*.html"))
    if not result_paths:
        result_paths = [results_dir / f"{batch_id}.html"]
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in result_paths:
        if not path.exists():
            continue
        for product_id, url in parse_detail_links(path.read_text(encoding="utf-8", errors="replace")):
            if product_id in seen:
                continue
            seen.add(product_id)
            links.append((product_id, url))
    if limit > 0:
        links = links[:limit]

    saved: list[str] = []
    already_saved: list[str] = []
    failed: list[dict] = []
    for index, (product_id, url) in enumerate(links, start=1):
        detail_path = detail_root / f"{product_id}.html"
        if detail_path.exists():
            already_saved.append(str(detail_path))
            continue
        try:
            detail_bytes, _ = read_url(client, url)
            detail_html = detail_bytes.decode("utf-8", errors="replace")
            if any(marker in detail_html for marker in INVALID_DETAIL_MARKERS):
                failed.append({"product_id": product_id, "url": url, "reason": "invalid_detail_session"})
                continue
            detail_path.write_text(detail_html, encoding="utf-8")
            saved.append(str(detail_path))
        except Exception as exc:  # pragma: no cover - network failures are recorded for manual review.
            failed.append({"product_id": product_id, "url": url, "reason": str(exc)})
        if delay_seconds and index < len(links):
            time.sleep(delay_seconds)
    return {
        "detail_link_count": len(links),
        "saved_detail_count": len(saved),
        "already_saved_detail_count": len(already_saved),
        "total_saved_detail_count": len(saved) + len(already_saved),
        "failed_detail_count": len(failed),
        "saved_detail_sample": saved[:20],
        "failed_details": failed[:20],
    }


def update_progress(progress_path: Path, record: dict) -> dict:
    if progress_path.exists():
        progress = load_json(progress_path)
    else:
        progress = {"generated_at": now(), "runs": []}
    runs = [item for item in progress.get("runs", []) if item.get("batch_id") != record["batch_id"]]
    runs.append(record)
    progress["generated_at"] = now()
    progress["runs"] = sorted(runs, key=lambda item: item["batch_id"])
    progress["summary"] = {
        "attempted_batches": len(progress["runs"]),
        "completed_batches": sum(1 for item in progress["runs"] if item.get("status") == "submitted_result_saved"),
        "captcha_required_batches": sum(1 for item in progress["runs"] if "captcha" in item.get("status", "")),
    }
    write_json(progress_path, progress)
    return progress


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one TII captcha-protected batch as far as compliance allows.")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--captcha", default=None, help="Captcha typed by a human. Omit to fetch and save the captcha only.")
    parser.add_argument("--batch-plan", default=str(DEFAULT_BATCH_PLAN))
    parser.add_argument("--progress", default=str(DEFAULT_PROGRESS))
    parser.add_argument("--work-dir", default=str(DEFAULT_WORK_DIR))
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--details-dir", default=str(DEFAULT_DETAILS_DIR))
    parser.add_argument("--fetch-all-pages", action="store_true", help="After a successful captcha, fetch all result pages.")
    parser.add_argument("--fetch-details", action="store_true", help="After result pages are saved, fetch product detail pages in the same TII session.")
    parser.add_argument("--detail-limit", type=int, default=0, help="Optional detail-page limit for testing. 0 means no limit.")
    parser.add_argument("--page-size", type=int, default=10, choices=[10, 20, 30, 40, 50])
    parser.add_argument("--max-pages", type=int, default=1500, help="Safety ceiling for paginated TII result pages.")
    args = parser.parse_args()

    plan = load_json(Path(args.batch_plan))
    batch = find_batch(plan, args.batch_id)
    work_dir = Path(args.work_dir)
    results_dir = Path(args.results_dir)
    details_dir = Path(args.details_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    details_dir.mkdir(parents=True, exist_ok=True)

    cookie_path = work_dir / f"{args.batch_id}-cookies.txt"
    form_path = work_dir / f"{args.batch_id}-form.html"
    client, cookie_jar = opener(cookie_path)

    if args.fetch_all_pages and not args.captcha and cookie_path.exists():
        fetched_pages = fetch_result_pages(client, args.batch_id, results_dir, args.page_size, args.max_pages)
        fetched_details = (
            fetch_detail_pages(client, args.batch_id, results_dir, details_dir, args.detail_limit)
            if args.fetch_details
            else {}
        )
        save_cookies(cookie_jar, cookie_path)
        record = {
            "batch_id": args.batch_id,
            "ran_at": now(),
            "status": "submitted_result_saved",
            "note": "Fetched all result pages from an existing completed TII session.",
            "company_label": batch.get("company_label"),
            "category_label": batch.get("category_label"),
            "query_hint": batch.get("query_hint"),
            "form_action": "https://insprod.tii.org.tw/ResultQueryAll.aspx",
            "captcha_files": [str(path) for path in sorted(work_dir.glob(f"{args.batch_id}-captcha-*"))],
            "result_file": str(results_dir / f"{args.batch_id}-page-001.html"),
            "fetched_pages": fetched_pages,
            "fetched_details": fetched_details,
        }
        progress = update_progress(Path(args.progress), record)
        print(
            json.dumps(
                {
                    "run": record,
                    "summary": progress["summary"],
                    "next_step": "Run import_tii_results.py to import all saved result pages.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.captcha and form_path.exists() and cookie_path.exists():
        final_url = batch["source_url"]
        form_html = form_path.read_text(encoding="utf-8", errors="replace")
    else:
        form_bytes, final_url = read_url(client, batch["source_url"])
        form_html = form_bytes.decode("utf-8", errors="replace")
        form_path.write_text(form_html, encoding="utf-8")
        save_cookies(cookie_jar, cookie_path)

    forms = parse_forms(form_html)
    if not forms:
        raise SystemExit("Official TII query page did not expose a form.")
    form = forms[0]
    action = urllib.parse.urljoin(final_url, form.get("attrs", {}).get("action", "ResultQueryAll.aspx"))
    captcha_files: list[str] = []
    if not args.captcha:
        captcha_sources = parse_captcha_sources(form_html, final_url)
        for index, captcha_url in enumerate(captcha_sources[:2], start=1):
            captcha_bytes, captcha_final_url = read_url(client, captcha_url)
            fallback_suffix = Path(urllib.parse.urlparse(captcha_final_url).path).suffix
            suffix = image_suffix(captcha_bytes, fallback_suffix)
            captcha_path = work_dir / f"{args.batch_id}-captcha-{index}{suffix}"
            captcha_path.write_bytes(captcha_bytes)
            captcha_files.append(str(captcha_path))
        save_cookies(cookie_jar, cookie_path)
    else:
        captcha_files = [str(path) for path in sorted(work_dir.glob(f"{args.batch_id}-captcha-*"))]

    result_path = ""
    fetched_pages: dict = {}
    fetched_details: dict = {}
    if args.captcha:
        payload = build_payload(form, batch, args.captcha)
        result_bytes, _ = post_url(client, action, payload)
        save_cookies(cookie_jar, cookie_path)
        result_html = result_bytes.decode("utf-8", errors="replace")
        result_file = results_dir / f"{args.batch_id}.html"
        result_file.write_text(result_html, encoding="utf-8")
        result_path = str(result_file)
        status, note = classify_result(result_html, args.captcha)
        if args.fetch_all_pages and status == "submitted_result_saved":
            fetched_pages = fetch_result_pages(client, args.batch_id, results_dir, args.page_size, args.max_pages)
        if args.fetch_details and status == "submitted_result_saved":
            fetched_details = fetch_detail_pages(client, args.batch_id, results_dir, details_dir, args.detail_limit)
    else:
        status, note = classify_result(form_html, None)

    record = {
        "batch_id": args.batch_id,
        "ran_at": now(),
        "status": status,
        "note": note,
        "company_label": batch.get("company_label"),
        "category_label": batch.get("category_label"),
        "query_hint": batch.get("query_hint"),
        "form_action": action,
        "captcha_files": captcha_files,
        "result_file": result_path,
        "fetched_pages": fetched_pages,
        "fetched_details": fetched_details,
    }
    progress = update_progress(Path(args.progress), record)
    print(
        json.dumps(
            {
                "run": record,
                "summary": progress["summary"],
                "next_step": "Open the captcha image and rerun with --captcha <code> if you want to complete this batch.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.captcha and status != "submitted_result_saved":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
