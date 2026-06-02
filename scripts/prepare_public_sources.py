from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


TAIPEI = timezone(timedelta(hours=8))
DEFAULT_INPUT = Path("work/source-extraction/source-manifest.json")
DEFAULT_OUTPUT = Path("data/source-index.json")

COMPANY_NAMES = {
    "台灣人壽": "台灣人壽",
    "南山人壽": "南山人壽",
    "南山人壽健康醫療": "南山人壽",
    "新光人壽": "新光人壽",
    "富邦人壽": "富邦人壽",
    "三商美邦人壽": "三商美邦人壽",
    "遠雄人壽": "遠雄人壽",
    "宏泰人壽": "宏泰人壽",
    "中華郵政": "中華郵政",
    "商業保險": "商業保險",
    "兆豐產險": "兆豐產險",
    "明台產險": "明台產險",
    "國泰人壽險(仍可投保)": "國泰人壽",
    "保誠人壽險": "保誠人壽",
    "凱基人壽": "凱基人壽",
    "臺銀人壽": "臺銀人壽",
    "社會保險": "社會保險",
}

PRIVATE_DOMAINS = {"docs.google.com"}


def now_iso() -> str:
    return datetime.now(TAIPEI).replace(microsecond=0).isoformat()


def classify_url(url: str) -> tuple[str, str, bool, list[str]]:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    flags: list[str] = []

    if parsed.scheme == "file":
        return "local_file", parsed.scheme, False, ["local_file"]
    if parsed.scheme not in {"http", "https"}:
        return "unsupported", domain or parsed.scheme, False, ["unsupported_scheme"]
    if domain in PRIVATE_DOMAINS:
        return "private_document", domain, False, ["private_or_session_bound"]

    if "law.moj.gov.tw" in domain or "law.fsc.gov.tw" in domain or "law.lia-roc.org.tw" in domain:
        kind = "law_source"
    elif "bli.gov.tw" in domain or "nhi.gov.tw" in domain or "bot.com.tw" in domain or "afrc.mnd.gov.tw" in domain:
        kind = "social_insurance"
    elif path.endswith(".pdf") or ".pdf" in path or "portal-api/file" in path:
        kind = "pdf_or_file"
    elif "insurancedetail" in path or "product" in path:
        kind = "product_page"
    else:
        kind = "web_page"

    if path.endswith(".ashx"):
        flags.append("download_endpoint")
    if "portal-api/file" in path:
        flags.append("file_api")
    return kind, domain, True, flags


def make_source_index(manifest: dict[str, Any]) -> dict[str, Any]:
    generated_at = now_iso()
    source_documents: list[dict[str, Any]] = []
    urls: list[dict[str, Any]] = []
    seen: set[str] = set()
    domains = Counter()
    by_company = defaultdict(int)
    by_kind = Counter()
    excluded = Counter()

    doc_id_by_title: dict[str, str] = {}
    for idx, record in enumerate(manifest["records"], start=1):
        doc_id = f"doc_{idx:03d}"
        title = record["title"]
        company = COMPANY_NAMES.get(title, record.get("company_hint") or title)
        doc_id_by_title[title] = doc_id
        public_count = 0
        for link in record["links"]:
            kind, domain, should_crawl, flags = classify_url(link["url"])
            if should_crawl:
                public_count += 1
            else:
                excluded[kind] += 1
        source_documents.append(
            {
                "id": doc_id,
                "title": title,
                "company": company,
                "kind": record["kind"],
                "input_file": record["file"],
                "total_links": record["link_count"],
                "public_crawl_candidates": public_count,
            }
        )

    for record in manifest["records"]:
        title = record["title"]
        company = COMPANY_NAMES.get(title, record.get("company_hint") or title)
        doc_id = doc_id_by_title[title]
        for link in record["links"]:
            url = link["url"]
            if url in seen:
                continue
            seen.add(url)
            kind, domain, should_crawl, flags = classify_url(url)
            visibility = "public_web" if should_crawl else "excluded_from_public_crawl"
            if should_crawl:
                domains[domain] += 1
                by_company[company] += 1
                by_kind[kind] += 1
            urls.append(
                {
                    "id": f"url_{len(urls) + 1:06d}",
                    "url": url,
                    "domain": domain,
                    "company": company,
                    "source_file_title": title,
                    "source_document_id": doc_id,
                    "source_label": (link.get("text") or "").strip(),
                    "kind": kind,
                    "visibility": visibility,
                    "should_crawl": should_crawl,
                    "risk_flags": flags,
                    "first_seen_at": generated_at,
                }
            )

    return {
        "generated_at": generated_at,
        "source_file_count": len(source_documents),
        "total_unique_url_count": len(urls),
        "public_crawl_candidate_count": sum(1 for item in urls if item["should_crawl"]),
        "excluded_count": sum(1 for item in urls if not item["should_crawl"]),
        "source_documents": source_documents,
        "top_domains": [{"domain": d, "count": c} for d, c in domains.most_common(40)],
        "company_counts": [{"company": c, "count": n} for c, n in sorted(by_company.items())],
        "kind_counts": [{"kind": k, "count": c} for k, c in by_kind.most_common()],
        "excluded_counts": [{"kind": k, "count": c} for k, c in excluded.most_common()],
        "urls": urls,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a public-safe source index.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    output = make_source_index(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "source_file_count": output["source_file_count"],
                "total_unique_url_count": output["total_unique_url_count"],
                "public_crawl_candidate_count": output["public_crawl_candidate_count"],
                "excluded_count": output["excluded_count"],
                "top_domains": output["top_domains"][:10],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
