from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TAIPEI_TZ = timezone(timedelta(hours=8))
PROTECTED_FIELDS = (
    "parser_id",
    "source_file",
    "source_document_sha256",
    "schedule_sha256",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append source-reviewed TII benefit proposals to an approval ledger."
    )
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--parser-id", required=True)
    parser.add_argument("--reviewed-by", default="codex-assisted-source-review")
    parser.add_argument("--review-note", required=True)
    parser.add_argument(
        "--product-id",
        action="append",
        default=[],
        help="Approve only the selected product id; repeat for multiple products.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace an existing approval only after the source has been re-reviewed.",
    )
    args = parser.parse_args()

    proposal_payload = load_json(args.proposal)
    batch_id = str(proposal_payload.get("batch_id") or "")
    if not batch_id:
        raise SystemExit("proposal has no batch_id")

    if args.approval.exists():
        approval_payload = load_json(args.approval)
        if approval_payload.get("batch_id") != batch_id:
            raise SystemExit("approval batch_id does not match proposal batch_id")
    else:
        approval_payload = {"batch_id": batch_id, "reviews": []}

    reviews_by_product = {
        str(review.get("product_id") or ""): review
        for review in approval_payload.get("reviews", [])
    }
    reviewed_at = datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
    selected_product_ids = set(args.product_id)
    matched_product_ids = set()
    added = []
    replaced = []
    unchanged = []
    for proposal in proposal_payload.get("proposals", []):
        candidates = proposal.get("candidates") or []
        if (
            proposal.get("status") != "proposed"
            or len(candidates) != 1
            or candidates[0].get("parser_id") != args.parser_id
        ):
            continue
        product_id = str(proposal.get("product_id") or "")
        if selected_product_ids and product_id not in selected_product_ids:
            continue
        matched_product_ids.add(product_id)
        candidate = candidates[0]
        if not product_id or any(not candidate.get(field) for field in PROTECTED_FIELDS):
            raise SystemExit(f"proposal lacks protected source fields: {product_id}")
        review = {
            "product_id": product_id,
            "decision": "approved",
            **{field: candidate[field] for field in PROTECTED_FIELDS},
            "reviewed_by": args.reviewed_by,
            "reviewed_at": reviewed_at,
            "review_note": args.review_note,
        }
        existing = reviews_by_product.get(product_id)
        if existing:
            protected_fields_changed = any(
                existing.get(field) != review.get(field) for field in PROTECTED_FIELDS
            )
            if protected_fields_changed:
                if not args.replace_existing:
                    raise SystemExit(
                        f"existing approval no longer matches proposal: {product_id}"
                    )
                reviews_by_product[product_id] = review
                replaced.append(product_id)
            else:
                unchanged.append(product_id)
            continue
        reviews_by_product[product_id] = review
        added.append(product_id)

    missing_product_ids = selected_product_ids - matched_product_ids
    if missing_product_ids:
        raise SystemExit(
            "selected product has no promotable proposal: "
            + ", ".join(sorted(missing_product_ids))
        )

    if not added and not replaced and not unchanged:
        raise SystemExit(f"no promotable proposal matched parser: {args.parser_id}")

    approval_payload["reviews"] = sorted(
        reviews_by_product.values(), key=lambda review: str(review.get("product_id") or "")
    )
    args.approval.parent.mkdir(parents=True, exist_ok=True)
    args.approval.write_text(
        json.dumps(approval_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": batch_id,
                "parser_id": args.parser_id,
                "added_count": len(added),
                "replaced_count": len(replaced),
                "unchanged_count": len(unchanged),
                "approval_count": len(approval_payload["reviews"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
