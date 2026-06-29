from __future__ import annotations

import html
import json
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PLAN_PATH = ROOT / "data" / "batch-plan.json"
PROGRESS_PATH = ROOT / "data" / "tii-execution-progress.json"
RESULTS_PATH = ROOT / "data" / "tii-policy-results.json"
WORK_DIR = ROOT / "work" / "tii-execution"
JOB_PATH = ROOT / "work" / "tii-operator-job.json"
DOCUMENT_DOWNLOAD_SCOPE = "life"
DOCUMENT_DOWNLOAD_BATCH_SIZE = 800
DOCUMENT_DOWNLOAD_PROGRESS_PATH = ROOT / "work" / "tii-documents" / "document-download-progress.json"
JOB_LOCK = threading.Lock()
READ_RETRY_ATTEMPTS = 30
READ_RETRY_DELAY_SECONDS = 0.25


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    last_error = ""
    for _ in range(READ_RETRY_ATTEMPTS):
        try:
            text = path.read_text(encoding="utf-8-sig")
            if not text.strip():
                raise json.JSONDecodeError("Empty JSON file", text, 0)
            return json.loads(text)
        except json.JSONDecodeError as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(READ_RETRY_DELAY_SECONDS)
    payload = dict(fallback)
    payload["_load_error"] = last_error or "Unable to read JSON file."
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def job_status() -> dict:
    return load_json(JOB_PATH, {"status": "idle"})


def set_job_status(payload: dict) -> None:
    with JOB_LOCK:
        write_json(JOB_PATH, payload)


def run_command(args: list[str], timeout: int = 14400) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            [PYTHON, *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return 124, output + f"\nTimed out after {timeout} seconds."
    return completed.returncode, completed.stdout


def has_complete_saved_pages(batch_id: str) -> bool:
    results = load_json(RESULTS_PATH, {"batch_summaries": []})
    summary = next(
        (item for item in results.get("batch_summaries", []) if item.get("batch_id") == batch_id),
        None,
    )
    if summary and summary.get("status") != "complete":
        return False
    saved_pages = list((ROOT / "work" / "tii-results").glob(f"{batch_id}-page-*.html"))
    marker = ROOT / "work" / "tii-results" / f"{batch_id}-pages-complete.json"
    if marker.exists():
        payload = load_json(marker, {})
        total_pages = int(payload.get("total_pages") or 0)
        return total_pages > 0 and len(saved_pages) >= total_pages

    progress = load_json(PROGRESS_PATH, {"runs": []})
    run = next((item for item in progress.get("runs", []) if item.get("batch_id") == batch_id), {})
    fetched_pages = run.get("fetched_pages") or {}
    total_pages = int(fetched_pages.get("total_pages") or 0)
    if not fetched_pages.get("is_complete") or total_pages <= 0:
        return False
    return len(saved_pages) >= total_pages


def run_batch_job(batch_id: str, captcha: str) -> None:
    pages_complete = has_complete_saved_pages(batch_id)
    started_at = now_iso()
    set_job_status(
        {
            "status": "running",
            "batch_id": batch_id,
            "message": "Submitting captcha and fetching missing detail pages."
            if pages_complete
            else "Submitting captcha and fetching pages.",
            "started_at": started_at,
        }
    )
    args = ["scripts/run_tii_batch.py", "--batch-id", batch_id, "--captcha", captcha, "--fetch-details"]
    if not pages_complete:
        args.append("--fetch-all-pages")
    code, output = run_command(args)
    if code == 0:
        import_code, import_output = run_command(
            ["scripts/import_tii_results.py", "--input-dir", "work/tii-results", "--output", "data/tii-policy-results.json"]
        )
        set_job_status(
            {
                "status": "completed" if import_code == 0 else "import_failed",
                "batch_id": batch_id,
                "message": output + "\n\nIMPORT\n" + import_output,
                "started_at": started_at,
                "finished_at": now_iso(),
            }
        )
    else:
        set_job_status(
            {
                "status": "failed",
                "batch_id": batch_id,
                "message": output,
                "started_at": started_at,
                "finished_at": now_iso(),
            }
        )


def run_document_job(batch_id: str, captcha: str, document_offset: int = 0) -> None:
    started_at = now_iso()
    set_job_status(
        {
            "status": "running",
            "mode": "document_download",
            "batch_id": batch_id,
            "document_offset": document_offset,
            "message": f"Submitting captcha and downloading up to {DOCUMENT_DOWNLOAD_BATCH_SIZE} core documents.",
            "started_at": started_at,
        }
    )
    args = [
        "scripts/run_tii_batch.py",
        "--batch-id",
        batch_id,
        "--captcha",
        captcha,
        "--fetch-details",
        "--fetch-documents",
        "--document-priority",
        "core",
        "--document-limit",
        str(DOCUMENT_DOWNLOAD_BATCH_SIZE),
        "--document-offset",
        str(document_offset),
        "--progress",
        str(DOCUMENT_DOWNLOAD_PROGRESS_PATH),
    ]
    code, output = run_command(args)
    extract_output = ""
    extract_code = 0
    if code == 0:
        batch = batch_map().get(batch_id, {})
        company_type = str(batch.get("company_type") or DOCUMENT_DOWNLOAD_SCOPE)
        record_paths = sorted((ROOT / "data" / "tii" / "records" / company_type).glob("*.json"))
        extract_args = [
            "scripts/extract_tii_document_content.py",
            "--batch-id",
            batch_id,
            "--output",
            f"data/tii/document-content/{batch_id}.json",
            "--raw-output",
            f"work/tii-document-text/{batch_id}-text.json",
            "--max-pages",
            "20",
        ]
        if record_paths:
            extract_args.append("--records")
            extract_args.extend(str(path.relative_to(ROOT)) for path in record_paths)
        extract_code, extract_output = run_command(extract_args)
    set_job_status(
        {
            "status": "completed" if code == 0 and extract_code == 0 else "failed",
            "mode": "document_download",
            "batch_id": batch_id,
            "document_offset": document_offset,
            "message": output + ("\n\nEXTRACT\n" + extract_output if extract_output else ""),
            "started_at": started_at,
            "finished_at": now_iso(),
        }
    )


def start_batch_job(batch_id: str, captcha: str, mode: str = "batch", document_offset: int = 0) -> tuple[bool, str]:
    current = job_status()
    if current.get("status") == "running":
        return False, f"Batch {current.get('batch_id')} is already running."
    set_job_status(
        {
            "status": "running",
            "mode": mode,
            "batch_id": batch_id,
            "document_offset": document_offset,
            "message": "Received captcha. Starting crawler worker.",
            "started_at": now_iso(),
        }
    )
    if mode in {"document_pilot", "document_download"}:
        worker = threading.Thread(target=run_document_job, args=(batch_id, captcha, document_offset), daemon=True)
    else:
        worker = threading.Thread(target=run_batch_job, args=(batch_id, captcha), daemon=True)
    worker.start()
    return True, f"Batch {batch_id} started. This page will refresh while the crawler runs."


def batch_map() -> dict[str, dict]:
    plan = load_json(PLAN_PATH, {})
    return {batch["id"]: batch for batch in plan.get("tii_manual_matrix_batches", [])}


def batch_order() -> list[str]:
    plan = load_json(PLAN_PATH, {})
    return [batch["id"] for batch in plan.get("tii_manual_matrix_batches", [])]


def next_batch_id() -> str:
    batches = batch_map()
    ordered_batch_ids = batch_order()
    progress = load_json(PROGRESS_PATH, {"runs": []})
    results = load_json(RESULTS_PATH, {"completed_batches": [], "batch_summaries": []})
    if results.get("_load_error"):
        return ""
    completed = set(results.get("completed_batches", []))
    partial = [
        summary["batch_id"]
        for summary in results.get("batch_summaries", [])
        if summary.get("batch_id") in batches and summary.get("status") != "complete"
    ]
    waiting = [
        run["batch_id"]
        for run in progress.get("runs", [])
        if run.get("batch_id") in batches
        and run.get("batch_id") not in completed
        and "captcha" in run.get("status", "")
    ]
    if waiting:
        waiting_set = set(waiting)
        return next((batch_id for batch_id in ordered_batch_ids if batch_id in waiting_set), sorted(waiting)[0])
    partial_set = set(partial)
    for batch_id in ordered_batch_ids:
        if batch_id in partial_set:
            return batch_id
    for batch_id in ordered_batch_ids:
        if batch_id not in completed:
            return batch_id
    return ""


def captcha_image(batch_id: str) -> Path | None:
    matches = sorted(WORK_DIR.glob(f"{batch_id}-captcha-*"))
    return matches[-1] if matches else None


def clear_captcha_session(batch_id: str) -> None:
    for path in WORK_DIR.glob(f"{batch_id}-captcha-*"):
        path.unlink(missing_ok=True)
    for suffix in ["cookies.txt", "form.html"]:
        (WORK_DIR / f"{batch_id}-{suffix}").unlink(missing_ok=True)


def saved_counts(batch_id: str) -> dict[str, int | bool]:
    if not batch_id:
        return {"saved_pages": 0, "expected_pages": 0, "saved_details": 0, "pages_complete": False}
    results_dir = ROOT / "work" / "tii-results"
    details_dir = ROOT / "work" / "tii-details" / batch_id
    saved_pages = len(list(results_dir.glob(f"{batch_id}-page-*.html")))
    marker = results_dir / f"{batch_id}-pages-complete.json"
    expected_pages = 0
    if marker.exists():
        payload = load_json(marker, {})
        expected_pages = int(payload.get("total_pages") or 0)
    saved_details = len(list(details_dir.glob("*.html"))) if details_dir.exists() else 0
    return {
        "saved_pages": saved_pages,
        "expected_pages": expected_pages,
        "saved_details": saved_details,
        "pages_complete": bool(expected_pages and saved_pages >= expected_pages),
    }


def document_status(batch_id: str) -> dict:
    status_path = ROOT / "work" / "tii-documents" / batch_id / "_document-download-status.json"
    return load_json(status_path, {}) if status_path.exists() else {}


def document_content_path(batch_id: str) -> Path:
    return ROOT / "data" / "tii" / "document-content" / f"{batch_id}.json"


def next_document_work_item() -> dict:
    batches = batch_map()
    ordered_batch_ids = [
        batch_id
        for batch_id in batch_order()
        if batches.get(batch_id, {}).get("company_type") == DOCUMENT_DOWNLOAD_SCOPE
    ]
    for batch_id in ordered_batch_ids:
        status = document_status(batch_id)
        if not status:
            return {"batch_id": batch_id, "document_offset": 0, "reason": "not_started"}
        total = int(status.get("total_document_link_count") or 0)
        offset = int(status.get("document_offset") or 0)
        window = int(status.get("document_link_count") or 0)
        limit = int(status.get("document_limit") or 0)
        if not status.get("total_scanned_all_details") and limit and window >= limit:
            return {
                "batch_id": batch_id,
                "document_offset": offset + window,
                "reason": "limit_boundary_recheck",
                "total_document_link_count": total,
            }
        if total and offset + window < total:
            return {
                "batch_id": batch_id,
                "document_offset": offset + window,
                "reason": "partial",
                "total_document_link_count": total,
            }
        if total and not document_content_path(batch_id).exists():
            return {
                "batch_id": batch_id,
                "document_offset": 0,
                "reason": "needs_extract_refresh",
                "total_document_link_count": total,
            }
    return {"batch_id": "", "document_offset": 0, "reason": "complete"}


def ensure_captcha(batch_id: str, force_refresh: bool = False, progress_path: Path = PROGRESS_PATH) -> tuple[bool, str]:
    if not batch_id:
        return False, "All TII batches are completed."
    if force_refresh:
        clear_captcha_session(batch_id)
    image = captcha_image(batch_id)
    progress = load_json(progress_path, {"runs": []})
    run = next((item for item in progress.get("runs", []) if item.get("batch_id") == batch_id), None)
    if image and run and run.get("status") == "captcha_required":
        return True, "Captcha already prepared."
    code, output = run_command(["scripts/run_tii_batch.py", "--batch-id", batch_id, "--progress", str(progress_path)])
    return code == 0, output


def html_page(message: str = "") -> bytes:
    batches = batch_map()
    progress = load_json(PROGRESS_PATH, {"summary": {}, "runs": []})
    results = load_json(RESULTS_PATH, {"record_count": 0, "pending_manual_batch_count": len(batches)})
    job = job_status()
    completed_result_batches = set(results.get("completed_batches", []))
    active_captcha_count = sum(
        1
        for run in progress.get("runs", [])
        if run.get("batch_id") not in completed_result_batches and "captcha" in run.get("status", "")
    )
    normal_batch_id = next_batch_id()
    document_item = next_document_work_item() if not normal_batch_id else {"batch_id": "", "document_offset": 0}
    mode = "batch" if normal_batch_id else "document_download" if document_item.get("batch_id") else "idle"
    batch_id = normal_batch_id or str(document_item.get("batch_id") or "")
    document_offset = int(document_item.get("document_offset") or 0)
    batch = batches.get(batch_id, {})
    job_running = job.get("status") == "running"
    pilot_mode = mode == "document_download"
    captcha_progress_path = DOCUMENT_DOWNLOAD_PROGRESS_PATH if pilot_mode else PROGRESS_PATH
    ok, prepare_message = (
        (False, "A batch is running.")
        if job_running
        else ensure_captcha(batch_id, progress_path=captcha_progress_path)
        if batch_id and mode != "idle"
        else (False, "No pending batch.")
    )
    if ok and job.get("status") == "failed" and job.get("batch_id") == batch_id:
        prepare_message = "上一輪驗證碼被官方判定錯誤。這張會固定到你送出或手動換圖為止。"
    image = captcha_image(batch_id) if ok else None
    counts = saved_counts(batch_id)
    docs = document_status(batch_id)
    progress_hint = (
        f"已保存清單頁 {counts['saved_pages']}/{counts['expected_pages']}，已保存明細 {counts['saved_details']}。"
        if counts["expected_pages"]
        else f"已保存清單頁 {counts['saved_pages']}，已保存明細 {counts['saved_details']}。"
    )
    mode_hint = (
        f"文件下載模式：送出後會重開 {batch_id} 的明細頁，從第 {document_offset + 1} 份核心文件開始，最多下載 {DOCUMENT_DOWNLOAD_BATCH_SIZE} 份並自動抽文字。"
        if pilot_mode
        else "此批清單頁已完整保存；送出後會只補抓缺少的明細頁。"
        if counts["pages_complete"]
        else "送出後會抓完整清單頁，再補抓可用明細頁。"
    )
    document_hint = (
        f"文件下載：視窗 {docs.get('document_offset', 0)} + {docs.get('document_link_count', 0)} / {docs.get('total_document_link_count', docs.get('document_link_count', 0))}；新增 {docs.get('saved_document_count', 0)}，已存在 {docs.get('already_saved_document_count', 0)}，失敗 {docs.get('failed_document_count', 0)}。"
        if docs
        else "這個文件批次尚未開始。"
    )
    image_tag = ""
    if image:
        image_version = f"{int(image.stat().st_mtime)}-{image.stat().st_size}"
        image_tag = (
            f'<img src="/captcha?batch_id={html.escape(batch_id)}&v={html.escape(image_version)}" '
            'alt="TII captcha" class="captcha">'
        )
    refresh_link = (
        f'<p><a href="/refresh?batch_id={html.escape(batch_id)}">換一張新的驗證碼</a></p>'
        if batch_id and not job_running
        else ""
    )
    rows = "\n".join(
        f"<tr><td>{html.escape(run.get('batch_id', ''))}</td><td>{html.escape(run.get('status', ''))}</td><td>{html.escape(run.get('ran_at', ''))}</td></tr>"
        for run in progress.get("runs", [])[-10:]
    )
    page_title = "TII 人身保險文件下載" if pilot_mode else "TII 人工驗證碼批次執行台"
    submit_label = "送出並下載/抽取文件" if pilot_mode else "送出並抓完整批次"
    body = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {('<meta http-equiv="refresh" content="8">' if job_running else '')}
  <title>{html.escape(page_title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.6; color: #162033; }}
    main {{ max-width: 900px; margin: 0 auto; }}
    .panel {{ border: 1px solid #d7deea; border-radius: 8px; padding: 16px; margin: 16px 0; }}
    .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }}
    .stats span {{ background: #f4f7fb; border-radius: 8px; padding: 10px; display: grid; }}
    .stats strong {{ font-size: 1.4rem; }}
    .captcha {{ display: block; margin: 12px 0; max-width: 220px; image-rendering: auto; }}
    input, button {{ font: inherit; padding: 9px 12px; }}
    input[name="captcha"] {{ width: min(220px, 100%); margin-left: 8px; font-size: 1.25rem; font-weight: 900; letter-spacing: 0.08em; }}
    button {{ background: #155eef; color: white; border: 0; border-radius: 8px; font-weight: 800; cursor: pointer; min-height: 48px; }}
    button:disabled {{ background: #9aa6bb; cursor: wait; }}
    form {{ display: grid; gap: 12px; align-items: start; max-width: 420px; }}
    label {{ display: grid; gap: 6px; font-weight: 700; }}
    input[name="captcha"] {{ margin-left: 0; }}
    .hint {{ background: #f4f7fb; border: 1px solid #d7deea; border-radius: 8px; padding: 10px 12px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border-top: 1px solid #e4e9f2; padding: 8px; text-align: left; }}
    code {{ background: #f4f7fb; padding: 2px 5px; border-radius: 5px; }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(page_title)}</h1>
  <p>這個頁面只在本機使用。它不破解驗證碼；人工輸入一個驗證碼後，系統會在同一個 TII session 內執行。</p>
  <div class="stats">
    <span><strong>{progress.get('summary', {}).get('attempted_batches', 0)}</strong>已啟動</span>
    <span><strong>{results.get('indexed_batch_count', 0)}</strong>已索引</span>
    <span><strong>{results.get('completed_batch_count', 0)}</strong>完整批次</span>
    <span><strong>{active_captcha_count}</strong>等待驗證碼</span>
    <span><strong>{results.get('record_count', 0)}</strong>已匯入保單</span>
    <span><strong>{results.get('detail_saved_count', 0)}</strong>已保存明細</span>
  </div>
  <div class="panel">
    <h2>背景工作</h2>
    <p><strong>{html.escape(job.get('status', 'idle'))}</strong> {html.escape(job.get('batch_id', ''))}</p>
    <pre>{html.escape(str(job.get('message', ''))[:1600])}</pre>
  </div>
  <div class="panel">
    <h2>{'文件下載 pilot' if pilot_mode else '下一批'}</h2>
    <p><strong>{html.escape(batch_id or '全部完成')}</strong></p>
    <p>{html.escape(batch.get('company_label', ''))} / {html.escape(batch.get('category_label', ''))}</p>
    <p class="hint">{html.escape(progress_hint)}<br>{html.escape(mode_hint)}</p>
    <p class="hint">{html.escape(document_hint)}</p>
    <p>{html.escape(prepare_message[:600])}</p>
    {image_tag}
    {refresh_link}
    <form method="post" action="/submit">
      <input type="hidden" name="batch_id" value="{html.escape(batch_id)}">
      <input type="hidden" name="mode" value="{html.escape(mode)}">
      <input type="hidden" name="document_offset" value="{document_offset}">
      <label>人工輸入驗證碼 <input name="captcha" autocomplete="off" inputmode="numeric" required autofocus></label>
      <button type="submit" {('disabled' if job_running else '')}>{html.escape(submit_label)}</button>
    </form>
  </div>
  <div class="panel">
    <h2>訊息</h2>
    <pre>{html.escape(message)}</pre>
  </div>
  <div class="panel">
    <h2>最近執行</h2>
    <table><thead><tr><th>批次</th><th>狀態</th><th>時間</th></tr></thead><tbody>{rows}</tbody></table>
  </div>
</main>
</body>
</html>"""
    return body.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send_no_cache_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/refresh":
            params = urllib.parse.parse_qs(parsed.query)
            batch_id = params.get("batch_id", [""])[0]
            if batch_id:
                clear_captcha_session(batch_id)
            self.send_response(303)
            self.send_no_cache_headers()
            self.send_header("Location", "/submit")
            self.end_headers()
            return
        if parsed.path == "/captcha":
            params = urllib.parse.parse_qs(parsed.query)
            batch_id = params.get("batch_id", [""])[0]
            image = captcha_image(batch_id)
            if not image or not image.exists():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_no_cache_headers()
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(image.read_bytes())
            return
        self.send_response(200)
        self.send_no_cache_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_page())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        batch_id = data.get("batch_id", [""])[0]
        mode = data.get("mode", ["batch"])[0]
        try:
            document_offset = int(data.get("document_offset", ["0"])[0] or 0)
        except ValueError:
            document_offset = 0
        captcha = data.get("captcha", [""])[0].strip()
        if not batch_id or not captcha:
            message = "Missing batch_id or captcha."
        else:
            _, message = start_batch_job(batch_id, captcha, mode, document_offset)
        self.send_response(200)
        self.send_no_cache_headers()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_page(message))


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("TII operator server: http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
