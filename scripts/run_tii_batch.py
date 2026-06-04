from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))
DEFAULT_BATCH_PLAN = Path("data/batch-plan.json")
DEFAULT_PROGRESS = Path("data/tii-execution-progress.json")
DEFAULT_WORK_DIR = Path("work/tii-execution")
DEFAULT_RESULTS_DIR = Path("work/tii-results")


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


def opener() -> urllib.request.OpenerDirector:
    cookie_jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


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


def parse_forms(html: str) -> list[dict]:
    parser = FormParser()
    parser.feed(html)
    return parser.forms


def parse_captcha_sources(html: str, base_url: str) -> list[str]:
    parser = ImageParser()
    parser.feed(html)
    return [urllib.parse.urljoin(base_url, src) for src in parser.sources]


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
    args = parser.parse_args()

    plan = load_json(Path(args.batch_plan))
    batch = find_batch(plan, args.batch_id)
    work_dir = Path(args.work_dir)
    results_dir = Path(args.results_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    client = opener()
    form_bytes, final_url = read_url(client, batch["source_url"])
    form_html = form_bytes.decode("utf-8", errors="replace")
    (work_dir / f"{args.batch_id}-form.html").write_text(form_html, encoding="utf-8")
    forms = parse_forms(form_html)
    if not forms:
        raise SystemExit("Official TII query page did not expose a form.")
    form = forms[0]
    action = urllib.parse.urljoin(final_url, form.get("attrs", {}).get("action", "ResultQueryAll.aspx"))
    captcha_sources = parse_captcha_sources(form_html, final_url)
    captcha_files: list[str] = []
    for index, captcha_url in enumerate(captcha_sources[:2], start=1):
        captcha_bytes, captcha_final_url = read_url(client, captcha_url)
        suffix = Path(urllib.parse.urlparse(captcha_final_url).path).suffix or ".bmp"
        captcha_path = work_dir / f"{args.batch_id}-captcha-{index}{suffix}"
        captcha_path.write_bytes(captcha_bytes)
        captcha_files.append(str(captcha_path))

    result_path = ""
    if args.captcha:
        payload = build_payload(form, batch, args.captcha)
        result_bytes, _ = post_url(client, action, payload)
        result_html = result_bytes.decode("utf-8", errors="replace")
        result_file = results_dir / f"{args.batch_id}.html"
        result_file.write_text(result_html, encoding="utf-8")
        result_path = str(result_file)
        status, note = classify_result(result_html, args.captcha)
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


if __name__ == "__main__":
    main()
