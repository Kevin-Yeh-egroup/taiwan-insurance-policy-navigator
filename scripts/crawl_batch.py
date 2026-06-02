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
    request = urllib.request.Request(url, headers=headers, method="GET")
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
            "final_url": url,
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
            "final_url": url,
            "title": "",
            "elapsed_ms": round((time.time() - started) * 1000),
            "error": str(exc),
        }


def select_urls(source_index: dict[str, Any], limit: int, max_per_domain: int, company: str | None) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    domain_counts = Counter()
    for item in source_index["urls"]:
        if not item["should_crawl"]:
            continue
        if company and item["company"] != company:
            continue
        if domain_counts[item["domain"]] >= max_per_domain:
            continue
        selected.append(item)
        domain_counts[item["domain"]] += 1
        if len(selected) >= limit:
            break
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Polite batch probe for policy source URLs.")
    parser.add_argument("--input", type=Path, default=Path("data/source-index.json"))
    parser.add_argument("--output", type=Path, default=Path("data/crawl-status.json"))
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--max-per-domain", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--delay", type=float, default=0.45)
    parser.add_argument("--company", default=None)
    args = parser.parse_args()

    source_index = json.loads(args.input.read_text(encoding="utf-8"))
    selected = select_urls(source_index, args.limit, args.max_per_domain, args.company)
    robot_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
    results: list[dict[str, Any]] = []

    for item in selected:
        robots = get_robot_parser(item["url"], robot_cache)
        allowed = robots.can_fetch(USER_AGENT, item["url"])
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
        results.append(result)

    domain_summary = defaultdict(lambda: {"checked": 0, "ok": 0, "blocked": 0})
    for item in results:
        row = domain_summary[item["domain"]]
        row["checked"] += 1
        if item["ok"]:
            row["ok"] += 1
        if not item["robots_allowed"]:
            row["blocked"] += 1

    output = {
        "generated_at": now_iso(),
        "user_agent": USER_AGENT,
        "batch": {
            "limit": args.limit,
            "max_per_domain": args.max_per_domain,
            "timeout": args.timeout,
            "delay": args.delay,
            "company": args.company,
        },
        "summary": {
            "checked": len(results),
            "ok": sum(1 for item in results if item["ok"]),
            "robots_blocked": sum(1 for item in results if not item["robots_allowed"]),
            "errors": sum(1 for item in results if item["error"]),
        },
        "domain_summary": [
            {"domain": domain, **values}
            for domain, values in sorted(domain_summary.items(), key=lambda row: row[0])
        ],
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
