from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TAIPEI = timezone(timedelta(hours=8))
USER_AGENT = "TaiwanPolicyNavigatorBot/0.1 (policy-catalog-research; production-review-required)"
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)


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


def decode_title(data: bytes) -> str:
    match = TITLE_RE.search(data)
    if not match:
        return ""
    title = re.sub(rb"\s+", b" ", match.group(1)).strip()
    for encoding in ("utf-8", "big5", "cp950"):
        try:
            return title.decode(encoding, errors="replace")
        except Exception:
            continue
    return title.decode("utf-8", errors="replace")


def fetch_probe(url: str, timeout: int) -> dict[str, Any]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/pdf,application/json;q=0.8,*/*;q=0.5",
        "Range": "bytes=0-65535",
    }
    safe_url = iri_to_uri(url)
    request = urllib.request.Request(safe_url, headers=headers, method="GET")
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(65536)
            content_type = response.headers.get("content-type", "")
            title = ""
            if "html" in content_type.lower():
                title = decode_title(body)
            return {
                "status": response.status,
                "ok": 200 <= response.status < 400,
                "content_type": content_type,
                "content_length": response.headers.get("content-length"),
                "final_url": response.geturl(),
                "title": title,
                "elapsed_ms": round((time.time() - started) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": exc.code,
            "ok": False,
            "content_type": exc.headers.get("content-type") if exc.headers else "",
            "content_length": exc.headers.get("content-length") if exc.headers else None,
                "final_url": safe_url,
            "title": "",
            "elapsed_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "status": None,
            "ok": False,
            "content_type": "",
            "content_length": None,
            "final_url": safe_url,
            "title": "",
            "elapsed_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }


def load_existing_results(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["url_id"]: item for item in data.get("results", [])}


def select_urls(
    source_index: dict[str, Any],
    existing_results: dict[str, dict[str, Any]],
    limit: int,
    max_per_domain: int,
    company: str | None,
    domain: str | None,
    kind: str | None,
    retry_errors: bool,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    domain_counts = Counter()
    for item in source_index["urls"]:
        if not item["should_crawl"]:
            continue
        if company and item["company"] != company:
            continue
        if domain and item["domain"] != domain:
            continue
        if kind and item["kind"] != kind:
            continue
        existing = existing_results.get(item["id"])
        if existing and not retry_errors:
            continue
        if existing and retry_errors and not existing.get("error"):
            continue
        if domain_counts[item["domain"]] >= max_per_domain:
            continue
        selected.append(item)
        domain_counts[item["domain"]] += 1
        if len(selected) >= limit:
            break
    return selected


def summarize_results(source_index: dict[str, Any], results: list[dict[str, Any]], batch: dict[str, Any]) -> dict[str, Any]:
    public_ids = {item["id"] for item in source_index["urls"] if item["should_crawl"]}
    checked_ids = {item["url_id"] for item in results}
    domain_summary = defaultdict(lambda: {"checked": 0, "ok": 0, "blocked": 0, "errors": 0})
    for item in results:
        if item["url_id"] not in public_ids:
            continue
        row = domain_summary[item["domain"]]
        row["checked"] += 1
        if item["ok"]:
            row["ok"] += 1
        if not item["robots_allowed"]:
            row["blocked"] += 1
        if item["error"]:
            row["errors"] += 1

    public_count = len(public_ids)
    checked_count = len(public_ids & checked_ids)
    ok_count = sum(1 for item in results if item["url_id"] in public_ids and item["ok"])
    blocked_count = sum(1 for item in results if item["url_id"] in public_ids and not item["robots_allowed"])
    error_count = sum(1 for item in results if item["url_id"] in public_ids and item["error"])
    return {
        "generated_at": now_iso(),
        "user_agent": USER_AGENT,
        "batch": batch,
        "summary": {
            "total_candidates": public_count,
            "checked": checked_count,
            "unchecked": public_count - checked_count,
            "completion_rate": round(checked_count / public_count, 4) if public_count else 0,
            "ok": ok_count,
            "robots_blocked": blocked_count,
            "errors": error_count,
        },
        "domain_summary": [
            {"domain": domain, **values}
            for domain, values in sorted(domain_summary.items(), key=lambda row: (-row[1]["checked"], row[0]))
        ],
        "results": sorted(results, key=lambda row: row["url_id"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Polite batch probe for policy source URLs.")
    parser.add_argument("--input", type=Path, default=Path("data/source-index.json"))
    parser.add_argument("--output", type=Path, default=Path("data/crawl-status.json"))
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--max-per-domain", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--delay", type=float, default=0.45)
    parser.add_argument("--company", default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--fresh", action="store_true", help="Ignore existing output and start a new status file.")
    parser.add_argument("--retry-errors", action="store_true", help="Retry only URLs with prior errors.")
    args = parser.parse_args()

    source_index = json.loads(args.input.read_text(encoding="utf-8"))
    existing_results = {} if args.fresh else load_existing_results(args.output)
    selected = select_urls(
        source_index=source_index,
        existing_results=existing_results,
        limit=args.limit,
        max_per_domain=args.max_per_domain,
        company=args.company,
        domain=args.domain,
        kind=args.kind,
        retry_errors=args.retry_errors,
    )
    robot_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
    new_results: list[dict[str, Any]] = []

    for item in selected:
        robots = get_robot_parser(item["url"], robot_cache)
        allowed = robots.can_fetch(USER_AGENT, iri_to_uri(item["url"]))
        result: dict[str, Any] = {
            "url_id": item["id"],
            "url": item["url"],
            "domain": item["domain"],
            "company": item["company"],
            "kind": item["kind"],
            "checked_at": now_iso(),
            "robots_allowed": allowed,
        }
        if allowed:
            result.update(fetch_probe(item["url"], args.timeout))
            time.sleep(args.delay)
        else:
            result.update(
                {
                    "status": None,
                    "ok": False,
                    "content_type": "",
                    "content_length": None,
                    "final_url": item["url"],
                    "title": "",
                    "elapsed_ms": 0,
                    "error": "Blocked by robots.txt",
                }
            )
        new_results.append(result)

    merged_results = existing_results.copy()
    for item in new_results:
        merged_results[item["url_id"]] = item

    batch = {
        "limit": args.limit,
        "max_per_domain": args.max_per_domain,
        "timeout": args.timeout,
        "delay": args.delay,
        "company": args.company,
        "domain": args.domain,
        "kind": args.kind,
        "fresh": args.fresh,
        "retry_errors": args.retry_errors,
        "selected": len(selected),
        "new_results": len(new_results),
    }
    output = summarize_results(source_index, list(merged_results.values()), batch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                **output["summary"],
                "selected_this_run": len(selected),
                "new_results_this_run": len(new_results),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
