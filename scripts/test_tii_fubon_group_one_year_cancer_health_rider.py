from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_PRODUCT_IDS,
    FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_VERSIONS,
    complete_strict_source_document,
    fubon_group_one_year_cancer_health_rider_semantic_phase,
    is_fubon_group_one_year_cancer_health_rider_strict_source,
    normalize_terms_text,
    parse_fubon_group_one_year_cancer_health_rider_policy_state,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
BATCH_ID = "tii-life-050"
FAMILY_FINGERPRINT = "26fabbdc5c324e802bfb1788"
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / BATCH_ID
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-050-fubon-group-one-year-cancer-health-rider-v276.json"
)
PARSER_ID = "fubon-group-one-year-cancer-health-rider-policy-state-v1"
KNOWN_BAD_PRODUCT_ID = "209317R11A00200"


def source_document(product_id: str) -> tuple[dict, Path]:
    version = FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_VERSIONS[
        product_id
    ]
    source_path = DOCUMENTS_DIR / product_id / version["file_name"]
    document = complete_strict_source_document(
        {
            "batch_id": BATCH_ID,
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
            "source_document_sha256": hashlib.sha256(
                source_path.read_bytes()
            ).hexdigest(),
        },
        source_path,
    )
    return document, source_path


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-050/fubon-group-one-year-cancer",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Fubon cancer schedule"
        )


expected_entry_ids = {
    "cancer-death-benefit",
    "cancer-inpatient-daily-benefit",
    "cancer-post-discharge-home-care-benefit",
    "cancer-radiation-daily-benefit",
    "cancer-surgery-treatment-benefit",
    "waiting-period-premium-refund",
}
expected_event_values = {
    "eligible_cancer_death",
    "eligible_cancer_treatment",
    "diagnosed_within_applicable_waiting_period",
    "not_eligible_or_uncertain",
}
schedules: dict[str, dict] = {}

for product_id in sorted(
    FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_PRODUCT_IDS
):
    source_contract = (
        FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_VERSIONS[
            product_id
        ]
    )
    revision = int(source_contract["revision"])
    document, source_path = source_document(product_id)
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == source_contract["source_document_sha256"]
    )
    assert document["source_text_extractor"] == source_contract[
        "source_text_extractor"
    ]
    assert hashlib.sha256(
        normalize_terms_text(document["text"]).encode("utf-8")
    ).hexdigest() == source_contract["source_text_sha256"]

    schedule = parse_fubon_group_one_year_cancer_health_rider_policy_state(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(schedule, f"{BATCH_ID}/{product_id}")

    version = schedule["version_characteristics"]
    assert version["source_product_id"] == product_id
    assert version["family_fingerprint"] == FAMILY_FINGERPRINT
    assert version["semantic_phase"] == (
        fubon_group_one_year_cancer_health_rider_semantic_phase(
            revision
        )
    )
    assert version["source_document_sha256"] == source_contract[
        "source_document_sha256"
    ]
    assert version["source_text_sha256"] == source_contract[
        "source_text_sha256"
    ]
    assert version["cancer_reinstatement_waiting_days"] == (
        30 if revision <= 7 else 0
    )
    assert version["carcinoma_in_situ_included"] is (
        revision >= 9
    )
    assert version["insured_grace_period_notice_added"] is (
        revision >= 11
    )
    assert version["forced_execution_continuation_added"] is (
        revision >= 12
    )
    assert version["required_policy_inputs"] == [
        "fubon_group_one_year_cancer_event_status"
    ]
    assert schedule["selection_type"] == "policy_state"
    assert schedule["plan_options"] == []

    entries = {
        entry["id"]: entry for entry in schedule["coverage_entries"]
    }
    assert set(entries) == expected_entry_ids
    assert all(entry.get("amount") is None for entry in entries.values())
    assert all(
        entry["calculation_basis"] == "policy_state_amount"
        for entry in entries.values()
    )
    for entry in entries.values():
        assert entry["exclusion_state_key"] == (
            "fubon_group_one_year_cancer_event_status"
        )
        assert (
            set(entry["exclusion_values"])
            < expected_event_values
        )
    assert entries["cancer-inpatient-daily-benefit"][
        "quantity_state_key"
    ] == "cancer_hospitalization_days"
    assert entries["cancer-post-discharge-home-care-benefit"][
        "quantity_cap_state_key"
    ] == "cancer_hospitalization_days"
    assert entries["cancer-radiation-daily-benefit"][
        "quantity_state_key"
    ] == "cancer_radiation_treatment_days"
    assert entries["cancer-surgery-treatment-benefit"][
        "quantity_state_key"
    ] == "cancer_surgery_count"
    schedules[product_id] = schedule


assert (
    FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_VERSIONS[
        "209327R11A00104"
    ]["source_document_sha256"]
    == FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_VERSIONS[
        "209327R11A00105"
    ]["source_document_sha256"]
)
assert (
    schedules["209327R11A00104"]["version_characteristics"][
        "source_product_id"
    ]
    != schedules["209327R11A00105"]["version_characteristics"][
        "source_product_id"
    ]
)

wrong_source = copy.deepcopy(schedules["209323RZ1A00521A11Z10000013"])
wrong_source["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
assert_invalid_schedule(wrong_source, "version boundary is invalid")

wrong_phase = copy.deepcopy(schedules["209323RZ1A00521A11Z10000009"])
wrong_phase["version_characteristics"][
    "semantic_phase"
] = "medical_act_hospital_issue_only_wait"
assert_invalid_schedule(wrong_phase, "version boundary is invalid")

wrong_formula = copy.deepcopy(schedules["209323R11A00106"])
for entry in wrong_formula["coverage_entries"]:
    if entry["id"] == "cancer-post-discharge-home-care-benefit":
        entry["quantity_cap_state_key"] = "home_care_eligible_days"
assert_invalid_schedule(wrong_formula, "exact entry contract is invalid")

valid_document, _ = source_document("209323R11A00106")
invalid_hash_document = copy.deepcopy(valid_document)
invalid_hash_document["source_document_sha256"] = "0" * 64
assert (
    parse_fubon_group_one_year_cancer_health_rider_policy_state(
        invalid_hash_document
    )
    is None
)
invalid_text_document = copy.deepcopy(valid_document)
invalid_text_document["text"] += "非條款文字"
assert (
    parse_fubon_group_one_year_cancer_health_rider_policy_state(
        invalid_text_document
    )
    is None
)

assert (
    KNOWN_BAD_PRODUCT_ID
    not in FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_PRODUCT_IDS
)
for file_name in (
    "209317R11A00200-A.pdf",
    "209317R11A00200-F.pdf",
):
    bad_path = DOCUMENTS_DIR / KNOWN_BAD_PRODUCT_ID / file_name
    assert bad_path.exists()
    bad_document = {
        "batch_id": BATCH_ID,
        "product_id": KNOWN_BAD_PRODUCT_ID,
        "file_name": file_name,
        "document_type": "policy_terms",
        "text": valid_document["text"],
        "source_document_sha256": hashlib.sha256(
            bad_path.read_bytes()
        ).hexdigest(),
        "source_text_sha256": hashlib.sha256(
            normalize_terms_text(valid_document["text"]).encode(
                "utf-8"
            )
        ).hexdigest(),
        "source_text_extractor": valid_document[
            "source_text_extractor"
        ],
        "page_count": valid_document["page_count"],
        "pages_parsed": valid_document["pages_parsed"],
    }
    assert not is_fubon_group_one_year_cancer_health_rider_strict_source(
        bad_document
    )
    assert (
        parse_fubon_group_one_year_cancer_health_rider_policy_state(
            bad_document
        )
        is None
    )

proposal_payload = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
assert proposal_payload["batch_id"] == BATCH_ID
assert proposal_payload["extractor_version"] == EXTRACTOR_VERSION
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == FUBON_GROUP_ONE_YEAR_CANCER_HEALTH_RIDER_PRODUCT_IDS

print(
    {
        "status": "ok",
        "batch_id": BATCH_ID,
        "product_count": len(schedules),
        "known_bad_source_isolated": KNOWN_BAD_PRODUCT_ID,
    }
)
