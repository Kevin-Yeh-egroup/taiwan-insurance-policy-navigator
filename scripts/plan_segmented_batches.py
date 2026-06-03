from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path


TAIPEI = timezone(timedelta(hours=8))
DEFAULT_LIFE_CATEGORY_VALUES = {"3_1", "3_2", "2_3", "2_4", "2_5", "2_6"}
TII_COMPANY_TYPES = {
    "property": {
        "category_id": "1",
        "label": "財產保險",
        "short_label": "產險",
        "category_prefixes": {"1"},
    },
    "life": {
        "category_id": "2",
        "label": "人身保險",
        "short_label": "壽險",
        "category_prefixes": {"2", "3"},
    },
}


def chunked(items: list[dict], size: int) -> list[list[dict]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compact_labels(counter: Counter, limit: int = 5) -> list[str]:
    return [label for label, _count in counter.most_common(limit)]


def infer_tii_company_type(company: dict) -> str:
    value = str(company.get("value") or "")
    try:
        code = int(value)
    except ValueError:
        return "other"
    if 100 <= code < 200:
        return "property"
    if 200 <= code < 300:
        return "life"
    return "other"


def infer_tii_category_type(category: dict) -> str:
    value = str(category.get("value") or "")
    prefix = value.split("_", 1)[0]
    for key, config in TII_COMPANY_TYPES.items():
        if prefix in config["category_prefixes"]:
            return key
    return "other"


def enriched_tii_companies(tii_metadata: dict) -> list[dict]:
    rows: list[dict] = []
    for company in tii_metadata.get("companies", []):
        value = company.get("value")
        if not value or value == "000":
            continue
        company_type = infer_tii_company_type(company)
        config = TII_COMPANY_TYPES.get(company_type, {})
        rows.append(
            {
                **company,
                "company_type": company_type,
                "company_type_label": config.get("label", "其他"),
                "company_type_short_label": config.get("short_label", "其他"),
            }
        )
    return rows


def enriched_tii_categories(tii_metadata: dict) -> list[dict]:
    rows: list[dict] = []
    for category in tii_metadata.get("insurance_categories", []):
        if not category.get("value"):
            continue
        company_type = infer_tii_category_type(category)
        config = TII_COMPANY_TYPES.get(company_type, {})
        rows.append(
            {
                **category,
                "company_type": company_type,
                "company_type_label": config.get("label", "其他"),
                "company_type_short_label": config.get("short_label", "其他"),
            }
        )
    return rows


def policy_url_items(policy_insights: dict) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    status_priority = {"已停售": 0, "不確定": 1, "仍可投保": 2}
    for policy in policy_insights.get("policies", []):
        url = policy.get("policy_url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(policy)
    return sorted(
        rows,
        key=lambda row: (
            status_priority.get(row.get("sale_status"), 9),
            row.get("company", ""),
            row.get("product_type", ""),
            row.get("id", ""),
        ),
    )


def build_policy_url_batches(policies: list[dict], batch_size: int) -> list[dict]:
    batches: list[dict] = []
    for index, rows in enumerate(chunked(policies, batch_size), start=1):
        companies = Counter(row.get("company", "") for row in rows)
        types = Counter(row.get("product_type", "") for row in rows)
        statuses = Counter(row.get("sale_status", "") for row in rows)
        batches.append(
            {
                "id": f"policy-url-{index:03d}",
                "kind": "policy_url_content_batch",
                "status": "planned",
                "item_count": len(rows),
                "priority": "high" if any(row.get("sale_status") != "仍可投保" for row in rows) else "normal",
                "status_mix": dict(statuses),
                "companies": compact_labels(companies),
                "product_types": compact_labels(types),
                "first_policy_id": rows[0].get("id"),
                "last_policy_id": rows[-1].get("id"),
                "sample_products": [row.get("product_name", "") for row in rows[:3]],
                "recommended_command": (
                    "python scripts\\crawl_batch.py --limit 80 --max-per-domain 8 "
                    "# source availability probe; deep content extraction should use this batch id"
                ),
            }
        )
    return batches


def match_priority_companies(policy_insights: dict, tii_metadata: dict) -> list[dict]:
    current_companies = [row["label"] for row in policy_insights.get("company_counts", [])]
    tii_companies = enriched_tii_companies(tii_metadata)
    matches: list[dict] = []
    used: set[str] = set()
    for company in current_companies:
        for option in tii_companies:
            label = option.get("label", "")
            if option.get("value") in used:
                continue
            if company and company in label:
                used.add(option["value"])
                matches.append(option)
                break
    return matches


def build_tii_manual_matrix(tii_metadata: dict) -> tuple[list[dict], list[dict], dict]:
    companies = enriched_tii_companies(tii_metadata)
    categories = enriched_tii_categories(tii_metadata)
    manual_batches: list[dict] = []
    groups: list[dict] = []

    for company_type, config in TII_COMPANY_TYPES.items():
        group_companies = [row for row in companies if row["company_type"] == company_type]
        group_categories = [row for row in categories if row["company_type"] == company_type]
        group_batches: list[dict] = []
        for company in group_companies:
            for category in group_categories:
                index = len(group_batches) + 1
                batch = {
                    "id": f"tii-{company_type}-{index:03d}",
                    "kind": "tii_manual_captcha_batch",
                    "status": "planned_manual",
                    "company_type": company_type,
                    "company_type_code": config["category_id"],
                    "company_type_label": config["label"],
                    "company_type_short_label": config["short_label"],
                    "company_code": company.get("value"),
                    "company_label": company.get("label"),
                    "category_value": category.get("value"),
                    "category_label": category.get("label"),
                    "source_url": "https://insprod.tii.org.tw/Query.aspx",
                    "query_hint": {
                        "categoryId": config["category_id"],
                        "CompanyID": company.get("value"),
                        "f_CategoryId1": category.get("value"),
                        "endDate2": "",
                        "fQueryAll": "",
                    },
                    "manual_steps": [
                        "Open https://insprod.tii.org.tw/Query.aspx",
                        f"Select company type {config['label']} ({config['category_id']}).",
                        "Select the company and insurance category from this batch.",
                        "Leave not-discontinued unchecked to include discontinued records.",
                        "Human enters captcha and saves result HTML/CSV to work\\tii-results.",
                        "Run python scripts\\import_tii_results.py --input-dir work\\tii-results --output data\\tii-policy-results.json",
                    ],
                }
                group_batches.append(batch)
                manual_batches.append(batch)
        groups.append(
            {
                "key": company_type,
                "company_type_code": config["category_id"],
                "label": config["label"],
                "short_label": config["short_label"],
                "company_count": len(group_companies),
                "category_count": len(group_categories),
                "manual_batch_count": len(group_batches),
                "companies": group_companies,
                "insurance_categories": group_categories,
                "sample_batch_ids": [batch["id"] for batch in group_batches[:6]],
            }
        )

    summary = {
        "manual_matrix_batch_count": len(manual_batches),
        "property_company_count": next((group["company_count"] for group in groups if group["key"] == "property"), 0),
        "life_company_count": next((group["company_count"] for group in groups if group["key"] == "life"), 0),
        "other_company_count": len([row for row in companies if row["company_type"] == "other"]),
        "matching_category_batch_rule": (
            "Property companies are paired with property categories; "
            "life companies are paired with personal-insurance categories."
        ),
    }
    return groups, manual_batches, summary


def build_tii_batches(policy_insights: dict, tii_metadata: dict) -> tuple[list[dict], dict]:
    categories = [
        row
        for row in enriched_tii_categories(tii_metadata)
        if row.get("value") and row.get("value") in DEFAULT_LIFE_CATEGORY_VALUES
    ]
    all_categories = enriched_tii_categories(tii_metadata)
    companies = enriched_tii_companies(tii_metadata)
    priority_companies = match_priority_companies(policy_insights, tii_metadata)

    batches: list[dict] = []
    for company in priority_companies:
        for category in categories:
            batches.append(
                {
                    "id": f"tii-{len(batches) + 1:03d}",
                    "kind": "tii_manual_captcha_batch",
                    "status": "planned_manual",
                    "company_type": company.get("company_type"),
                    "company_type_code": TII_COMPANY_TYPES.get(company.get("company_type"), {}).get("category_id", ""),
                    "company_type_label": company.get("company_type_label"),
                    "company_type_short_label": company.get("company_type_short_label"),
                    "company_code": company.get("value"),
                    "company_label": company.get("label"),
                    "category_value": category.get("value"),
                    "category_label": category.get("label"),
                    "target": "停售保單優先",
                    "query_hint": {
                        "categoryId": TII_COMPANY_TYPES.get(company.get("company_type"), {}).get("category_id", ""),
                        "CompanyID": company.get("value"),
                        "f_CategoryId1": category.get("value"),
                        "endDate2": "",
                        "fQueryAll": "",
                    },
                    "manual_steps": [
                        "Open https://insprod.tii.org.tw/Query.aspx",
                        "Select company and insurance category from this batch.",
                        "Leave 未停售 unchecked to include discontinued records.",
                        "Human enters captcha and saves result HTML/CSV to work\\tii-results.",
                        "Run python scripts\\import_tii_results.py --input-dir work\\tii-results --output data\\tii-policy-results.json",
                    ],
                }
            )

    full_coverage = {
        "company_count": len(companies),
        "category_count": len(all_categories),
        "estimated_batches": len(companies) * len(all_categories),
        "cross_product_estimated_batches": len(companies) * len(all_categories),
        "note": "Full TII coverage is company x category. Because captcha is required, process priority batches first.",
    }
    return batches, full_coverage


def main() -> None:
    parser = argparse.ArgumentParser(description="Create segmented batch plan for many insurance policies.")
    parser.add_argument("--policy-insights", type=Path, default=Path("data/policy-insights.json"))
    parser.add_argument("--tii-metadata", type=Path, default=Path("data/tii-query-metadata.json"))
    parser.add_argument("--output", type=Path, default=Path("data/batch-plan.json"))
    parser.add_argument("--policy-batch-size", type=int, default=80)
    args = parser.parse_args()

    policy_insights = load_json(args.policy_insights)
    tii_metadata = load_json(args.tii_metadata)
    policy_items = policy_url_items(policy_insights)
    policy_batches = build_policy_url_batches(policy_items, args.policy_batch_size)
    tii_batches, tii_full_coverage = build_tii_batches(policy_insights, tii_metadata)
    tii_company_type_groups, tii_manual_matrix_batches, tii_matrix_summary = build_tii_manual_matrix(tii_metadata)
    tii_full_coverage["estimated_batches"] = tii_matrix_summary["manual_matrix_batch_count"]
    tii_full_coverage["note"] = (
        "Full TII coverage follows the site split: property companies x property categories, "
        "and life companies x personal-insurance categories. Captcha remains manual."
    )

    output = {
        "generated_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "strategy": {
            "policy_url_batch_size": args.policy_batch_size,
            "default_daily_target": "1-3 TII manual batches plus 1 automated URL/content batch",
            "priority_order": [
                "已停售",
                "不確定",
                "高量公司",
                "健康險/壽險/傷害險/年金險",
                "其他公司與其他類型",
            ],
            "captcha_boundary": "TII batches require human captcha completion; do not bypass captcha.",
        },
        "summary": {
            "policy_url_total": len(policy_items),
            "policy_url_batch_count": len(policy_batches),
            "tii_priority_batch_count": len(tii_batches),
            "tii_full_estimated_batch_count": tii_full_coverage["estimated_batches"],
            "tii_manual_matrix_batch_count": tii_matrix_summary["manual_matrix_batch_count"],
            "tii_priority_company_count": len({batch["company_code"] for batch in tii_batches}),
            "tii_property_company_count": tii_matrix_summary["property_company_count"],
            "tii_life_company_count": tii_matrix_summary["life_company_count"],
            "tii_other_company_count": tii_matrix_summary["other_company_count"],
        },
        "policy_url_batches": policy_batches,
        "tii_priority_batches": tii_batches,
        "tii_company_type_groups": tii_company_type_groups,
        "tii_manual_matrix_batches": tii_manual_matrix_batches,
        "tii_full_coverage": tii_full_coverage,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
