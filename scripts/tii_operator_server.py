from __future__ import annotations

import html
import json
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PLAN_PATH = ROOT / "data" / "batch-plan.json"
PROGRESS_PATH = ROOT / "data" / "tii-execution-progress.json"
RESULTS_PATH = ROOT / "data" / "tii-policy-results.json"
WORK_DIR = ROOT / "work" / "tii-execution"
JOB_PATH = ROOT / "work" / "tii-operator-job.json"
JOB_LOCK = threading.Lock()


def load_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def job_status() -> dict:
    return load_json(JOB_PATH, {"status": "idle"})


def set_job_status(payload: dict) -> None:
    with JOB_LOCK:
        write_json(JOB_PATH, payload)


def run_command(args: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        [PYTHON, *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=900,
    )
    return completed.returncode, completed.stdout


def run_batch_job(batch_id: str, captcha: str) -> None:
    set_job_status({"status": "running", "batch_id": batch_id, "message": "Submitting captcha and fetching pages."})
    code, output = run_command(
        [
            "scripts/run_tii_batch.py",
            "--batch-id",
            batch_id,
            "--captcha",
            captcha,
            "--fetch-all-pages",
            "--fetch-details",
        ]
    )
    if code == 0:
        import_code, import_output = run_command(
            ["scripts/import_tii_results.py", "--input-dir", "work/tii-results", "--output", "data/tii-policy-results.json"]
        )
        set_job_status(
            {
                "status": "completed" if import_code == 0 else "import_failed",
                "batch_id": batch_id,
                "message": output + "\n\nIMPORT\n" + import_output,
            }
        )
    else:
        set_job_status({"status": "failed", "batch_id": batch_id, "message": output})


def start_batch_job(batch_id: str, captcha: str) -> tuple[bool, str]:
    current = job_status()
    if current.get("status") == "running":
        return False, f"Batch {current.get('batch_id')} is already running."
    worker = threading.Thread(target=run_batch_job, args=(batch_id, captcha), daemon=True)
    worker.start()
    return True, f"Batch {batch_id} started. This page will refresh while the crawler runs."


def batch_map() -> dict[str, dict]:
    plan = load_json(PLAN_PATH, {})
    return {batch["id"]: batch for batch in plan.get("tii_manual_matrix_batches", [])}


def next_batch_id() -> str:
    batches = batch_map()
    progress = load_json(PROGRESS_PATH, {"runs": []})
    results = load_json(RESULTS_PATH, {"completed_batches": [], "batch_summaries": []})
    completed = set(results.get("completed_batches", []))
    partial = [
        summary["batch_id"]
        for summary in results.get("batch_summaries", [])
        if summary.get("batch_id") in batches and summary.get("status") != "complete"
    ]
    waiting = [run["batch_id"] for run in progress.get("runs", []) if "captcha" in run.get("status", "")]
    if waiting:
        return sorted(waiting)[0]
    if partial:
        return sorted(partial)[0]
    for batch_id in sorted(batches):
        if batch_id not in completed:
            return batch_id
    return ""


def captcha_image(batch_id: str) -> Path | None:
    matches = sorted(WORK_DIR.glob(f"{batch_id}-captcha-*"))
    return matches[-1] if matches else None


def ensure_captcha(batch_id: str) -> tuple[bool, str]:
    if not batch_id:
        return False, "All TII batches are completed."
    image = captcha_image(batch_id)
    progress = load_json(PROGRESS_PATH, {"runs": []})
    run = next((item for item in progress.get("runs", []) if item.get("batch_id") == batch_id), None)
    if image and run and run.get("status") == "captcha_required":
        return True, "Captcha already prepared."
    code, output = run_command(["scripts/run_tii_batch.py", "--batch-id", batch_id])
    return code == 0, output


def html_page(message: str = "") -> bytes:
    batches = batch_map()
    progress = load_json(PROGRESS_PATH, {"summary": {}, "runs": []})
    results = load_json(RESULTS_PATH, {"record_count": 0, "pending_manual_batch_count": len(batches)})
    job = job_status()
    batch_id = next_batch_id()
    batch = batches.get(batch_id, {})
    job_running = job.get("status") == "running"
    ok, prepare_message = (False, "A batch is running.") if job_running else ensure_captcha(batch_id) if batch_id else (False, "No pending batch.")
    image = captcha_image(batch_id) if ok else None
    image_tag = ""
    if image:
        image_tag = f'<img src="/captcha?batch_id={html.escape(batch_id)}" alt="TII captcha" class="captcha">'
    rows = "\n".join(
        f"<tr><td>{html.escape(run.get('batch_id', ''))}</td><td>{html.escape(run.get('status', ''))}</td><td>{html.escape(run.get('ran_at', ''))}</td></tr>"
        for run in progress.get("runs", [])[-10:]
    )
    body = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {('<meta http-equiv="refresh" content="8">' if job_running else '')}
  <title>TII Operator</title>
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
    button {{ background: #155eef; color: white; border: 0; border-radius: 8px; font-weight: 800; cursor: pointer; }}
    button:disabled {{ background: #9aa6bb; cursor: wait; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border-top: 1px solid #e4e9f2; padding: 8px; text-align: left; }}
    code {{ background: #f4f7fb; padding: 2px 5px; border-radius: 5px; }}
  </style>
</head>
<body>
<main>
  <h1>TII 人工驗證碼批次執行台</h1>
  <p>這個頁面只在本機使用。它不破解驗證碼；人工輸入一個驗證碼後，系統會自動抓該批所有結果分頁、可用明細頁並匯入。</p>
  <div class="stats">
    <span><strong>{progress.get('summary', {}).get('attempted_batches', 0)}</strong>已啟動</span>
    <span><strong>{results.get('indexed_batch_count', 0)}</strong>已索引</span>
    <span><strong>{results.get('completed_batch_count', 0)}</strong>完整批次</span>
    <span><strong>{progress.get('summary', {}).get('captcha_required_batches', 0)}</strong>等待驗證碼</span>
    <span><strong>{results.get('record_count', 0)}</strong>已匯入保單</span>
    <span><strong>{results.get('detail_saved_count', 0)}</strong>已保存明細</span>
  </div>
  <div class="panel">
    <h2>背景工作</h2>
    <p><strong>{html.escape(job.get('status', 'idle'))}</strong> {html.escape(job.get('batch_id', ''))}</p>
    <pre>{html.escape(str(job.get('message', ''))[:1600])}</pre>
  </div>
  <div class="panel">
    <h2>下一批</h2>
    <p><strong>{html.escape(batch_id or '全部完成')}</strong></p>
    <p>{html.escape(batch.get('company_label', ''))} / {html.escape(batch.get('category_label', ''))}</p>
    <p>{html.escape(prepare_message[:600])}</p>
    {image_tag}
    <form method="post" action="/submit">
      <input type="hidden" name="batch_id" value="{html.escape(batch_id)}">
      <label>人工輸入驗證碼 <input name="captcha" autocomplete="off" inputmode="numeric" required autofocus></label>
      <button type="submit" {('disabled' if job_running else '')}>送出並抓完整批次</button>
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
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/captcha":
            params = urllib.parse.parse_qs(parsed.query)
            batch_id = params.get("batch_id", [""])[0]
            image = captcha_image(batch_id)
            if not image or not image.exists():
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()
            self.wfile.write(image.read_bytes())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_page())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        batch_id = data.get("batch_id", [""])[0]
        captcha = data.get("captcha", [""])[0].strip()
        if not batch_id or not captcha:
            message = "Missing batch_id or captcha."
        else:
            _, message = start_batch_job(batch_id, captcha)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_page(message))


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("TII operator server: http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
