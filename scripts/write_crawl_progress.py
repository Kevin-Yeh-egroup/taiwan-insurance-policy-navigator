from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def main() -> None:
    status = json.loads(Path("data/crawl-status.json").read_text(encoding="utf-8"))
    summary = status["summary"]
    domains = status["domain_summary"][:20]
    lines = [
        "# Crawl Progress",
        "",
        f"Updated at: `{now_iso()}`",
        "",
        "## Overall",
        "",
        f"- Total public candidates: `{summary['total_candidates']}`",
        f"- Checked: `{summary['checked']}`",
        f"- Unchecked: `{summary['unchecked']}`",
        f"- Completion rate: `{summary['completion_rate'] * 100:.1f}%`",
        f"- OK: `{summary['ok']}`",
        f"- Robots blocked: `{summary['robots_blocked']}`",
        f"- Errors / needs review: `{summary['errors']}`",
        "",
        "## Top Checked Domains",
        "",
        "| Domain | Checked | OK | Robots blocked | Errors |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in domains:
        lines.append(
            f"| `{row['domain']}` | {row['checked']} | {row['ok']} | {row['blocked']} | {row['errors']} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- The crawler is resumable. It skips URL IDs already present in `data/crawl-status.json`.",
            "- `robots.txt` blocked sources are treated as completed checks, not crawl failures.",
            "- HTTP 404, connection refused, timeout, and encoding/network errors are marked as review items.",
            "- Deeper policy-field extraction should only use sources with stable source URLs and source evidence.",
        ]
    )
    Path("docs/CRAWL_PROGRESS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    main()
