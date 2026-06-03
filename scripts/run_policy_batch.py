from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from plan_segmented_batches import chunked, policy_url_items


TAIPEI = timezone(timedelta(hours=8))
USER_AGENT = "TaiwanPolicyNavigatorBot/0.2 (segmented-policy-content-review)"
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

CONTENT_KEYWORDS = {
    "理賠/給付": ["理賠", "給付", "保險金", "申請文件"],
    "名詞定義": ["名詞定義", "定義", "醫院", "住院", "手術"],
    "等待期/免責期": ["等待期", "免責期", "等待期間"],
    "除外責任": ["除外責任", "不保事項", "不予給付"],
    "保費/續保": ["保費", "費率", "續保", "復效", "停效"],
    "投保限制": ["投保年齡", "職業類別", "健康告知", "最高保額"],
}


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def origin(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def iri_to_uri(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/%:@")
    query = urllib.parse.quote(urllib.parse.unquote(parsed.query), safe="=&?/:;+,%@")
    fragment = urllib.parse.quote(urllib.parse.unquote(parsed.fragment), safe="=&?/:;+,%@")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, fragment))


def get_robot_parser(url: str, cache: dict[str, urllib.robotparser.RobotFileParser]) -> urllib.robotparser.RobotFileParser:
    site = origin(url)
    if site not in cache:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{site}/robots.txt")
        try:
            parser.read()
        except Exception:
            pass
        cache[site] = parser
    return cache[site]


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "big5", "cp950"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_title(data: bytes) -> str:
    match = TITLE_RE.search(data)
    if not match:
        return ""
    return re.sub(r"\s+", " ", decode_bytes(match.group(1))).strip()


def text_from_response(data: bytes, content_type: str) -> str:
    lowered = content_type.lower()
    if "pdf" in lowered:
        return ""
    text = decode_bytes(data)
    if "html" in lowered or "<html" in text[:500].lower():
        text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_flags(text: str, fallback_flags: list[str]) -> list[str]:
    flags = set(fallback_flags)
    for label, keywords in CONTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            flags.add(label)
    return sorted(flags)


def fetch_policy(policy: dict[str, Any], timeout: int, max_bytes: int) -> dict[str, Any]:
    url = policy.get("policy_url", "")
    request = urllib.request.Request(
        iri_to_uri(url),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,application/json;q=0.8,*/*;q=0.5",
            "Range": f"bytes=0-{max_bytes - 1}",
        },
        method="GET",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes)
            content_type = response.headers.get("content-type", "")
            text = text_from_response(body, content_type)
            return {
                "status": response.status,
                "ok": 200 <= response.status < 400,
                "content_type": content_type,
                "content_length": response.headers.get("content-length"),
                "final_url": response.geturl(),
                "title": extract_title(body) if "html" in content_type.lower() else "",
                "text_sample": text[:1200],
                "detected_flags": detect_flags(text, policy.get("content_flags", [])),
                "elapsed_ms": round((time.time() - started) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "ok": False,
            "content_type": exc.headers.get("content-type") if exc.headers else "",
            "content_length": exc.headers.get("content-length") if exc.headers else None,
            "final_url": url,
            "title": "",
            "text_sample": "",
            "detected_flags": policy.get("content_flags", []),
            "elapsed_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "status": None,
            "ok": False,
            "content_type": "",
            "content_length": None,
            "final_url": url,
            "title": "",
            "text_sample": "",
            "detected_flags": policy.get("content_flags", []),
            "elapsed_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }


def select_batch(policy_insights: dict, batch_id: str, batch_size: int) -> list[dict]:
    if not batch_id.startswith("policy-url-"):
        raise SystemExit("run_policy_batch.py only executes policy-url-* automated batches")
    try:
        index = int(batch_id.rsplit("-", 1)[1]) - 1
    except ValueError as exc:
        raise SystemExit(f"invalid batch id: {batch_id}") from exc
    batches = chunked(policy_url_items(policy_insights), batch_size)
    if index < 0 or index >= len(batches):
        raise SystemExit(f"batch id out of range: {batch_id}")
    return batches[index]


def load_existing(path: Path) -> dict:
    if not path.exists():
        return {"generated_at": now_iso(), "batches": []}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_batch(batch_id: str, results: list[dict]) -> dict:
    status_counts = Counter(result.get("sale_status", "") for result in results)
    return {
        "id": batch_id,
        "kind": "policy_url_content_batch",
        "status": "completed",
        "ran_at": now_iso(),
        "item_count": len(results),
        "ok": sum(1 for result in results if result.get("ok")),
        "robots_blocked": sum(1 for result in results if result.get("robots_allowed") is False),
        "errors": sum(1 for result in results if result.get("error") and result.get("robots_allowed") is not False),
        "status_mix": dict(status_counts),
    }


def write_results(output_path: Path, progress_path: Path, batch_id: str, results: list[dict]) -> None:
    output = load_existing(output_path)
    batches = [batch for batch in output.get("batches", []) if batch.get("id") != batch_id]
    batches.append(
        {
            "id": batch_id,
            "kind": "policy_url_content_batch",
            "generated_at": now_iso(),
            "results": results,
        }
    )
    output["generated_at"] = now_iso()
    output["batches"] = sorted(batches, key=lambda row: row["id"])
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    progress = load_existing(progress_path)
    progress_batches = [batch for batch in progress.get("batches", []) if batch.get("id") != batch_id]
    progress_batches.append(summarize_batch(batch_id, results))
    progress["generated_at"] = now_iso()
    progress["summary"] = {
        "completed_policy_url_batches": len(progress_batches),
        "policy_url_items_processed": sum(batch.get("item_count", 0) for batch in progress_batches),
        "policy_url_ok": sum(batch.get("ok", 0) for batch in progress_batches),
        "policy_url_robots_blocked": sum(batch.get("robots_blocked", 0) for batch in progress_batches),
        "policy_url_errors": sum(batch.get("errors", 0) for batch in progress_batches),
    }
    progress["batches"] = sorted(progress_batches, key=lambda row: row["id"])
    progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute one automated policy URL content batch.")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--policy-insights", type=Path, default=Path("data/policy-insights.json"))
    parser.add_argument("--batch-plan", type=Path, default=Path("data/batch-plan.json"))
    parser.add_argument("--output", type=Path, default=Path("data/policy-batch-results.json"))
    parser.add_argument("--progress", type=Path, default=Path("data/batch-progress.json"))
    parser.add_argument("--timeout", type=int, default=14)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--max-bytes", type=int, default=131072)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    policy_insights = json.loads(args.policy_insights.read_text(encoding="utf-8"))
    batch_plan = json.loads(args.batch_plan.read_text(encoding="utf-8"))
    batch_size = int(batch_plan.get("strategy", {}).get("policy_url_batch_size", 80))
    selected = select_batch(policy_insights, args.batch_id, batch_size)
    if args.limit:
        selected = selected[: args.limit]

    robot_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
    results: list[dict] = []
    for policy in selected:
        url = policy.get("policy_url", "")
        allowed = False
        if url:
            robots = get_robot_parser(url, robot_cache)
            allowed = robots.can_fetch(USER_AGENT, iri_to_uri(url))
        result = {
            "policy_id": policy.get("id"),
            "company": policy.get("company"),
            "product_name": policy.get("product_name"),
            "product_type": policy.get("product_type"),
            "sale_status": policy.get("sale_status"),
            "policy_url": url,
            "checked_at": now_iso(),
            "robots_allowed": allowed,
        }
        if allowed:
            result.update(fetch_policy(policy, args.timeout, args.max_bytes))
            time.sleep(args.delay)
        else:
            result.update(
                {
                    "status": None,
                    "ok": False,
                    "content_type": "",
                    "content_length": None,
                    "final_url": url,
                    "title": "",
                    "text_sample": "",
                    "detected_flags": policy.get("content_flags", []),
                    "elapsed_ms": 0,
                    "error": "Blocked by robots.txt or missing URL",
                }
            )
        results.append(result)

    write_results(args.output, args.progress, args.batch_id, results)
    summary = summarize_batch(args.batch_id, results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
