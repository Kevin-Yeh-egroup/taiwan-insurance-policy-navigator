from __future__ import annotations

import copy
import json
from pathlib import Path

from extract_tii_plan_benefits import (
    CHINA_NEW_LOHAS_PLAN_DAILY_AMOUNTS,
    CHINA_NEW_LOHAS_SURGERY_RATES,
    CHINA_NEW_LOHAS_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS,
    china_new_lohas_whole_life_medical_health_document_code,
    china_new_lohas_whole_life_medical_health_semantic_phase,
    complete_strict_source_document,
    parse_china_new_lohas_whole_life_medical_health_plan,
    parse_plan_table_with_parser,
    sha256_file,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = ROOT / "work" / "tii-documents" / "tii-life-026"
PARSER_ID = (
    "china-new-lohas-whole-life-medical-health-plan-v1"
)
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-026-china-new-lohas-whole-life-medical-health-v274.json"
)


def source_document(product_id: str) -> dict:
    version = (
        CHINA_NEW_LOHAS_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS[
            product_id
        ]
    )
    source_path = (
        DOCUMENTS_ROOT
        / product_id
        / str(version["file_name"])
    )
    document = {
        "batch_id": "tii-life-026",
        "product_id": product_id,
        "file_name": source_path.name,
        "document_type": "policy_terms",
        "source_document_sha256": sha256_file(source_path),
    }
    return complete_strict_source_document(document, source_path)


schedules: dict[str, dict] = {}
for product_id, version in (
    CHINA_NEW_LOHAS_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS.items()
):
    document = source_document(product_id)
    schedule = (
        parse_china_new_lohas_whole_life_medical_health_plan(
            document
        )
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None, product_id
    assert integrated[0] == PARSER_ID, product_id
    assert integrated[1] == schedule, product_id
    validate_plan_options(schedule, f"tii-life-026/{product_id}")

    revision = int(version["revision"])
    characteristics = schedule["version_characteristics"]
    assert characteristics["source_product_id"] == product_id
    assert characteristics["source_document_sha256"] == (
        version["source_document_sha256"]
    )
    assert characteristics["source_text_sha256"] == (
        version["source_text_sha256"]
    )
    assert characteristics["source_text_extractor"] == (
        version["source_text_extractor"]
    )
    assert characteristics["source_text_quality"] == (
        "ocr_exact_hash"
        if version["source_text_extractor"] == "windows_ocr"
        else "machine_readable_exact_hash"
    )
    assert characteristics["semantic_phase"] == (
        china_new_lohas_whole_life_medical_health_semantic_phase(
            revision
        )
    )
    assert characteristics["document_code"] == (
        china_new_lohas_whole_life_medical_health_document_code(
            revision
        )
    )
    assert characteristics["six_hour_treatment_qualifies"] is (
        revision <= 4
    )
    assert (
        characteristics["emergency_transport_benefit_available"]
        is (revision <= 4)
    )
    assert characteristics["medical_review_opinion_revision"] is (
        revision >= 10
    )
    assert characteristics["surgery_schedule_rates_percent"] == (
        list(CHINA_NEW_LOHAS_SURGERY_RATES)
    )
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["burn_unit_benefit_present"] is False
    assert (
        characteristics["pre_post_outpatient_benefit_present"]
        is False
    )
    assert characteristics["no_cash_surrender_value"] is True

    options = schedule["plan_options"]
    assert [option["value"] for option in options] == [
        f"plan-{plan_number}"
        for plan_number in CHINA_NEW_LOHAS_PLAN_DAILY_AMOUNTS
    ]
    for option, (plan_number, daily_amount) in zip(
        options,
        CHINA_NEW_LOHAS_PLAN_DAILY_AMOUNTS.items(),
        strict=True,
    ):
        assert option["label"] == f"計劃 {plan_number}"
        entries = {
            entry["id"]: entry
            for entry in option["coverage_entries"]
        }
        assert (
            entries["remaining-lifetime-medical-cap"]["amount"]
            == daily_amount * 3000
        )
        assert (
            entries["hospital-daily-benefit"][
                "quantity_state_key"
            ]
            == "china_new_lohas_eligible_hospital_daily_days"
        )
        assert (
            entries["hospital-daily-benefit"]["quantity_cap"]
            == 365
        )
        assert (
            entries["intensive-care-additional-benefit"][
                "multiplier"
            ]
            == 2
        )
        surgery = entries["inpatient-surgery-benefit"]
        assert surgery["amount"] == daily_amount * 10
        assert (
            surgery["calculation_basis"]
            == "percentage_of_base"
        )
        assert (
            surgery["rate_state_key"]
            == "surgery_total_benefit_rate_percent"
        )
        assert surgery["rate_min_percent"] == 11
        assert surgery["rate_max_percent"] == 500
        assert (
            entries["inpatient-surgery-nursing-benefit"][
                "multiplier"
            ]
            == 5
        )
        assert (
            entries["outpatient-surgery-benefit"]["multiplier"]
            == 3
        )
        assert (
            "emergency-medical-transport-benefit" in entries
        ) is (revision <= 4)
        assert (
            entries["terminal-age-return"]["rate_percent"]
            == 106
        )
        assert (
            entries["death-or-funeral-benefit"]["rate_percent"]
            == 106
        )
        assert (
            entries["minor-under-15-premium-refund"][
                "rate_percent"
            ]
            == 100
        )
    schedules[product_id] = schedule


wrong_hash = copy.deepcopy(schedules["205311M11A00800"])
wrong_hash["version_characteristics"][
    "source_document_sha256"
] = "0" * 64
try:
    validate_plan_options(
        wrong_hash,
        "negative/tii-life-026/china-new-lohas-medical",
    )
except SystemExit as error:
    assert "version formula is invalid" in str(error), str(error)
else:
    raise AssertionError(
        "formal validator accepted a wrong source hash"
    )


base_document = source_document("205311M11A00800")
assert parse_china_new_lohas_whole_life_medical_health_plan(
    {**base_document, "batch_id": "tii-life-025"}
) is None
assert parse_china_new_lohas_whole_life_medical_health_plan(
    {**base_document, "file_name": "205311M11A00800-F.pdf"}
) is None
assert parse_china_new_lohas_whole_life_medical_health_plan(
    {**base_document, "source_document_sha256": "0" * 64}
) is None
assert parse_china_new_lohas_whole_life_medical_health_plan(
    {
        **base_document,
        "text": str(base_document["text"]).replace(
            "新樂活終身醫療健康保險",
            "新樂活終身健康保險",
            1,
        ),
    }
) is None


proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == "tii-life-026"
assert proposal_payload["extractor_version"] == (
    "tii-plan-benefits-v274"
)
assert proposal_payload["proposal_count"] == 14
assert proposal_payload["proposed_count"] == 14
assert proposal_payload["manual_review_count"] == 0
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == set(
    CHINA_NEW_LOHAS_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS
)
for proposal in proposal_payload["proposals"]:
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    product_id = proposal["product_id"]
    assert candidate["parser_id"] == PARSER_ID
    assert candidate["source_document_sha256"] == (
        CHINA_NEW_LOHAS_WHOLE_LIFE_MEDICAL_HEALTH_VERSIONS[
            product_id
        ]["source_document_sha256"]
    )
    assert candidate["schedule"] == schedules[product_id]


print(
    "TII China new Lohas whole-life medical health "
    "parser tests passed."
)
