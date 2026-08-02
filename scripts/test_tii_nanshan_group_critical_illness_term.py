from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from extract_tii_plan_benefits import (
    NANSHAN_GROUP_CRITICAL_ILLNESS_TERM_PRODUCT_IDS,
    NANSHAN_GROUP_CRITICAL_ILLNESS_TERM_REVISIONS,
    complete_strict_source_document,
    parse_nanshan_group_critical_illness_term_face_amount,
    parse_plan_table_with_parser,
)
from validate_data import validate_plan_options


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "work" / "tii-documents" / "tii-life-033"
PROPOSAL_PATH = (
    ROOT
    / "work"
    / "tii-benefit-proposals"
    / "tii-life-033-nanshan-group-critical-illness-v213.json"
)
PARSER_ID = "nanshan-group-critical-illness-term-face-amount-v2"
OCR_PRODUCT_IDS = {
    "206137M12B30100",
    "206137M12B30101",
    "206137M12B30102",
    "206137M12B30103",
}
EXPECTED_SOURCE_SHA256 = {
    "206133M15B30110": "0420c28815bad62be1f594027fa6d938976791a3e6c0e53eb3d47b0a66ad92a3",
    "206133M15B30111": "f44bea2ba90ad1189f04eb1f8293307e4952b28d4a12771da0792d449d6561ae",
    "206133MZ5B30121A11Z10000012": "6964909a493bd5749ccfcbed0002e13d2dbd36c0c2325e5200020496826cb197",
    "206133MZ5B30121A11Z10000013": "dc267f8364f3a70ec8c06435d614a4c94029c6b13651bf37d7c8e5f0e1338fa9",
    "206133MZ5B30121A11Z10000014": "765a1e14cbe6d5572d4cd80553a5b46bb825e45f8607db578fdbafba952d7344",
    "206133MZ5B30121A11Z10000015": "7b3d16f0d806e96ceb166d68dd2f062ac1818f04c254e610a34ec1cbf87460da",
    "206133MZ5B30121A11Z10000016": "cc14d133039bf4931c124edea0705e1f782374267d9a8f7e79380ccd76963740",
    "206133MZ5B30121A11Z10000017": "4b4dffde04db4b1d8b8fdd1ef4189a1acb26bac94a825ad2d440fe482aa327bf",
    "206133MZ5B30121A11Z10000018": "c6d100900bcbf8687b8f7a50c202be1c011fe9f14b21c3167c0b76f9dff7f67b",
    "206133MZ5B30121A11Z10000019": "6d548ec6715dc1c65e7297b9b9b068b8b97cad83aa3e1b7cddc7b46ca87bee55",
    "206133MZ5B30121A11Z10000020": "df9622d7e3c52bdba5e4fbcc1399e835c3e8ac9f3e5a2f11fcc16733df22f89e",
    "206137M12B30104": "561d8956d2e69adec1211f91906fda64d92ce9eb560e4548eff3de47cf44b22f",
    "206137M12B30105": "2423090e822f300ad892e055ae4b4bfe36cfff6e32c490e160a681cae40b656f",
    "206137M12B30106": "7d19aa32bbf6e19f0a23b1621069a21c57ec7775a0821cc55dc7847fe915698e",
    "206137M12B30107": "2a109e551fbfd92c7f3e3dfec2f7bfbd549c00fa4881a0df2e3e17b9a871659e",
    "206137M12B30109": "299eee1a579dc88029917d56b545ecb49ea21a6ca5c57b5ddda01f83cb3033b3",
}
EXPECTED_SOURCE_REFS = {
    "206137M12B30104": [6, 6, 7],
    "206133M15B30110": [5, 6, 6],
    "206133MZ5B30121A11Z10000012": [5, 6, 6],
}


def source_document(product_id: str) -> dict:
    source_path = (
        DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    )
    return complete_strict_source_document(
        {
            "batch_id": "tii-life-033",
            "product_id": product_id,
            "file_name": source_path.name,
            "document_type": "policy_terms",
            "text": "",
        },
        source_path,
    )


def assert_invalid_schedule(
    schedule: dict,
    expected_error: str,
) -> None:
    try:
        validate_plan_options(
            schedule,
            "negative/tii-life-033/nanshan-group-critical-illness",
        )
    except SystemExit as error:
        assert expected_error in str(error), str(error)
    else:
        raise AssertionError(
            "formal validator accepted an invalid Nanshan schedule"
        )


schedules: dict[str, dict] = {}
for product_id in sorted(
    NANSHAN_GROUP_CRITICAL_ILLNESS_TERM_PRODUCT_IDS
):
    revision = NANSHAN_GROUP_CRITICAL_ILLNESS_TERM_REVISIONS[
        product_id
    ]
    document = source_document(product_id)
    source_path = (
        DOCUMENTS_DIR / product_id / f"{product_id}-A.pdf"
    )
    assert (
        hashlib.sha256(source_path.read_bytes()).hexdigest()
        == EXPECTED_SOURCE_SHA256[product_id]
    )
    schedule = parse_nanshan_group_critical_illness_term_face_amount(
        document
    )
    assert schedule is not None, product_id
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == PARSER_ID
    assert integrated[1] == schedule
    validate_plan_options(
        schedule,
        f"tii-life-033/{product_id}",
    )

    critical_term = (
        "重度重大疾病" if revision >= 13 else "重大疾病"
    )
    disability_term = (
        "完全失能" if revision >= 14 else "殘廢"
    )
    has_refund = revision >= 7
    expected_funeral_rule = (
        "legacy_under_14_or_mental_capacity"
        if revision <= 7
        else (
            "mental_capacity_definition"
            if revision <= 13
            else "guardianship_declaration"
        )
    )
    expected_exception_scope = (
        "all_defined_critical_disease"
        if revision >= 7
        else "paralysis_or_major_organ_transplant_only"
    )
    expected_funeral_cap_reference = (
        "legacy_legal_status_cap"
        if revision <= 7
        else (
            "mental_capacity_cap"
            if revision <= 13
            else (
                "inheritance_deduction_half_at_insurance_application"
                if revision <= 16
                else "statutory_inheritance_deduction_half"
            )
        )
    )

    version = schedule["version_characteristics"]
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_source"] == "terms"
    assert schedule["face_amount_label"] == "被保險人保險金額"
    assert version["source_product_id"] == product_id
    assert version["terms_revision"] == f"partial_change_{revision}"
    assert version["critical_disease_term"] == critical_term
    assert version["disability_term"] == disability_term
    assert version["critical_disease_item_count"] == 7
    assert version["complete_disability_table_item_count"] == 7
    assert version["critical_disease_waiting_days"] == 60
    assert (
        version["accidental_waiting_exception_scope"]
        == expected_exception_scope
    )
    assert (
        version["funeral_status_rule_revision"]
        == expected_funeral_rule
    )
    assert (
        version["funeral_cap_reference_revision"]
        == expected_funeral_cap_reference
    )
    assert (
        version["amount_presentation"]
        == "contract_gross_benefit_before_premium_adjustments"
    )
    assert "non_participating_policy" not in version
    assert (
        version["benefit_event_unexpired_premium_refund"]
        is has_refund
    )
    assert (
        version["unexpired_premium_refund_requires_policy_state"]
        is has_refund
    )

    entries = {
        entry["id"]: entry
        for entry in schedule["coverage_entries"]
    }
    expected_entry_ids = {
        "critical-disease-benefit",
        "death-or-funeral-benefit",
        "disability-benefit",
    }
    if has_refund:
        expected_entry_ids.add("unexpired-premium-refund")
    assert set(entries) == expected_entry_ids
    assert (
        entries["critical-disease-benefit"]["name"]
        == f"{critical_term}保險金"
    )
    assert (
        entries["critical-disease-benefit"]["rate_percent"]
        == 100
    )
    assert (
        entries["death-or-funeral-benefit"][
            "calculation_basis"
        ]
        == "death_or_funeral_face_amount"
    )
    assert (
        entries["disability-benefit"]["name"]
        == f"{disability_term}保險金"
    )
    assert entries["disability-benefit"]["rate_percent"] == 100
    assert {
        entries[entry_id]["benefit_group_id"]
        for entry_id in {
            "critical-disease-benefit",
            "death-or-funeral-benefit",
            "disability-benefit",
        }
    } == {"nanshan-group-critical-illness-terminal-benefit"}
    assert [
        entries["critical-disease-benefit"]["event_key"],
        entries["death-or-funeral-benefit"]["event_key"],
        entries["disability-benefit"]["event_key"],
    ] == ["critical_disease", "death_or_funeral", "disability"]
    if has_refund:
        assert (
            entries["unexpired-premium-refund"][
                "policy_state_keys"
            ]
            == ["unexpired_premium_refund_amount"]
        )
        assert entries["unexpired-premium-refund"][
            "applies_to_entry_ids"
        ] == [
            "critical-disease-benefit",
            "death-or-funeral-benefit",
            "disability-benefit",
        ]
    if product_id in EXPECTED_SOURCE_REFS:
        assert [
            int(entry["source_ref"].split("第 ")[1].split(" 頁")[0])
            for entry in schedule["coverage_entries"][:3]
        ] == EXPECTED_SOURCE_REFS[product_id]
    schedules[product_id] = schedule

for product_id in OCR_PRODUCT_IDS:
    assert (
        parse_nanshan_group_critical_illness_term_face_amount(
            source_document(product_id)
        )
        is None
    )

wrong_version = copy.deepcopy(schedules["206137M12B30107"])
wrong_version["version_characteristics"][
    "benefit_event_unexpired_premium_refund"
] = False
assert_invalid_schedule(
    wrong_version,
    "version flag is invalid",
)

wrong_entry = copy.deepcopy(schedules["206133MZ5B30121A11Z10000020"])
next(
    entry
    for entry in wrong_entry["coverage_entries"]
    if entry["id"] == "death-or-funeral-benefit"
)["calculation_basis"] = "percentage_of_base"
assert_invalid_schedule(
    wrong_entry,
    "amount or calculable formula is invalid",
)

wrong_additive_target = copy.deepcopy(
    schedules["206137M12B30107"]
)
next(
    entry
    for entry in wrong_additive_target["coverage_entries"]
    if entry["id"] == "unexpired-premium-refund"
)["applies_to_entry_ids"] = ["missing-benefit"]
assert_invalid_schedule(
    wrong_additive_target,
    "additive event target is invalid",
)

proposal_payload = json.loads(
    PROPOSAL_PATH.read_text(encoding="utf-8")
)
assert proposal_payload["batch_id"] == "tii-life-033"
assert proposal_payload["proposal_count"] == len(schedules)
assert {
    proposal["product_id"]
    for proposal in proposal_payload["proposals"]
} == set(schedules)
for proposal in proposal_payload["proposals"]:
    product_id = proposal["product_id"]
    assert proposal["status"] == "proposed"
    assert proposal["candidate_count"] == 1
    candidate = proposal["candidates"][0]
    assert candidate["parser_id"] == PARSER_ID
    assert (
        candidate["source_file"].lower()
        == f"{product_id.lower()}-a.pdf"
    )
    assert (
        candidate["source_document_sha256"]
        == EXPECTED_SOURCE_SHA256[product_id]
    )
    assert candidate["schedule"] == schedules[product_id]

print(
    {
        "status": "ok",
        "batch_id": "tii-life-033",
        "product_count": len(schedules),
        "ocr_gap_count": len(OCR_PRODUCT_IDS),
        "version_range": [4, 20],
    }
)
