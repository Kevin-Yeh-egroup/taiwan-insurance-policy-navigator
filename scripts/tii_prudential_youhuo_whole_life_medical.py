from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "8d2f0ffd993fdd1fc6c4766a"
SOURCE_ROWS = (
    ("203311M11A00200", 0, "203311M11A00200-A.pdf", 16, "pypdf", "91a4ea995a3fbfdab934e17725ec840cf958f59565c2546be01b546a0a39801f", "7a794b15bd8adecfd912e07c518dafb89571152d7839fb2702fdb90daa6b2e3d"),
    ("203311M11A00201", 1, "203311M11A00201-A.pdf", 15, "pypdf", "e9a75dcbab0fd3384e96a07e64d65dfc4a82c35891e2ceeb8bad80474c4a3fe8", "cf7f0ba381c5a79064163695991c5e49484786bec7cbc8636be79f8df852a655"),
    ("203311M11A00202", 2, "203311M11A00202-A.pdf", 15, "pypdf", "5adf42f6ab9196ee97dae6b3d3e1bdf5e15f25adcefbd074f6d97085452b5147", "516cbaff6a9254c30db69f27a6321bb9f7bf98a396b5520a4da53e220ab7a370"),
    ("203311M11A00203", 3, "203311M11A00203-A.pdf", 15, "pypdf", "3ce1c539b784966ecc8fe389e43b97dfa0b9b8005982434e1ddf80c936041be2", "ff04e8cc92382be877ec35a8b0ad31ef5eee0010e0fb992472f4736c016b6849"),
    ("203311M11A00204", 4, "203311M11A00204-A.pdf", 15, "pypdf", "3164f825d05309861cfd50fb6b1d79abfc4566d1e720eb2cfb56d8008df54163", "1913d807fdd34e417d03901a0b6242d068209c9afc632b364689082b97d0b929"),
    ("203311M11A00205", 5, "203311M11A00205-A.pdf", 15, "pypdf", "6433e5cefaa6ccfa4d42443ec9b5758c871cf8337c27c034c859b85e8bec937b", "c941b98d11564bc1f5e12ffe83c07549fffc7a0c1eef39836d7ae24f650acc40"),
    ("203311M11A00206", 6, "203311M11A00206-A.pdf", 11, "pypdf", "ef16c3dc13385bd581d71e2ac500ad5482dfabb5d8afbdbe5048b321bfd0c65f", "a64f5aa0098c591534ea33d5e44703815467cdace5eb33ddd6d359b365eb778f"),
    ("203311MZ1A00123A11Z10000007", 7, "203311MZ1A00123A11Z10000007-A.pdf", 16, "pymupdf", "c190ddd29600662cae02f807a3ca8e49b8534d1812e5e42f4419c0f1091951aa", "ab5eb271d7399631a007138f59ab3cbdad21a61f57bbf14dcae7fff1a5366fd3"),
    ("203311MZ1A00123A11Z10000008", 8, "203311MZ1A00123A11Z10000008-A.pdf", 48, "pymupdf", "68b5ec1c70859119f41c7fcbfa09429041ea6ec5586c8c93b9d1059250e27ace", "f136e32cec30afdc3018483cb5c8a4c1501287360148c769eba8de391c1f10b3"),
    ("203311MZ1A00123A11Z10000009", 9, "203311MZ1A00123A11Z10000009-A.pdf", 43, "pymupdf", "eca22b0a6b2c6826aefe688b0b364108f1b3c753d837a52ec60a7f438225ec8f", "a9e14d8f911acc62283fdffe5239dcd6d000593fb2338661662488cb91929eaa"),
    ("203311MZ1A00123A11Z10000010", 10, "203311MZ1A00123A11Z10000010-A.pdf", 48, "pymupdf", "3b408371314c147d3d60c279a828faff32ae2b2a9d558db739810d7a9b13410b", "390153ccdb251abcc4b09817f2d245c2b3c04694f4953c18ed233687f5e8f2bf"),
    ("203311MZ1A00123A11Z10000011", 11, "203311MZ1A00123A11Z10000011-A.pdf", 48, "pymupdf", "4dfc457175e4c50f69bef3585b57af27a11ae284bc550f7b400a73948c8a81c4", "5ed0b7cf5b675fc8e6ea4365b920cabc3d45bfcac263e0a3e59658a6ea5094ad"),
    ("203311MZ1A00123A11Z10000012", 12, "203311MZ1A00123A11Z10000012-A.pdf", 48, "pymupdf", "dbe0e31f5bd66879eafd2895f52599e320a2ed2d8c3766046db5e1138a372e2f", "5a7c32a008726a81eb7e77495e7560bd06b781567101e7464a21379984e9a7a5"),
)
VERSIONS = {
    product_id: {
        "revision": revision,
        "file_name": file_name,
        "page_count": page_count,
        "source_text_extractor": extractor,
        "source_document_sha256": document_sha,
        "source_text_sha256": text_sha,
    }
    for product_id, revision, file_name, page_count, extractor, document_sha, text_sha
    in SOURCE_ROWS
}
PRODUCT_IDS = frozenset(VERSIONS)

PLAN_ROWS = (
    ("HCL-5", "計劃 5", 500),
    ("HCL-10", "計劃 10", 1_000),
    ("HCL-15", "計劃 15", 1_500),
    ("HCL-20", "計劃 20", 2_000),
    ("HCL-25", "計劃 25", 2_500),
    ("HCL-30", "計劃 30", 3_000),
)
EVENT_STATE_KEY = "prudential_youhuo_event_status"
EVENT_VALUES = {
    "eligible_medical_benefit",
    "eligible_newborn_screening_exception",
    "eligible_initial_critical_or_specific_illness",
    "initial_30_day_sickness_death_refund",
    "death_unexpired_premium_refund",
    "disease_waiting_not_met",
    "major_disease_waiting_not_met",
    "not_eligible_or_uncertain",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def is_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-014"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    phases = {
        0: "ahcl-original-six-hour-emergency",
        1: "legacy-partial-change-six-hour-emergency",
        2: "bhcl-six-hour-emergency",
        3: "bhcl-newborn-screening-exception",
        4: "bhcl-post-expiry-readmission-exclusion",
        5: "bhcl-post-expiry-readmission-exclusion",
        6: "chcl-inpatient-only",
        7: "chcl-inpatient-only-post-expiry-wording",
        8: "dhcl-plan-number-modern-surgery-table",
        9: "dhcl-reinstatement-major-disease-waiting-removed",
        10: "dhcl-functional-impairment-wording",
        11: "dhcl-major-and-specific-disease-definition-update",
        12: "dhcl-specific-disease-diagnosis-medical-review-update",
    }
    return phases[revision]


def document_code(revision: int) -> str:
    if revision == 0:
        return "AHCL"
    if revision == 1:
        return "partial-change-1-no-code"
    if revision <= 5:
        return "BHCL"
    if revision <= 7:
        return "CHCL"
    return "DHCL"


def entry(
    entry_id: str,
    name: str,
    amount: int | None,
    basis: str,
    note: str,
    source_ref: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "name": name,
        "amount": amount,
        "basis": basis,
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        **fields,
    }


def eligibility(revision: int, *eligible_values: str) -> dict[str, Any]:
    eligible = set(eligible_values)
    if revision >= 3 and "eligible_medical_benefit" in eligible:
        eligible.add("eligible_newborn_screening_exception")
    return {
        "eligibility_state_key": EVENT_STATE_KEY,
        "ineligible_values": sorted(
            EVENT_VALUES - eligible - {"not_eligible_or_uncertain"}
        ),
        "uncertain_values": ["not_eligible_or_uncertain"],
    }


def expected_entry_contracts(
    revision: int,
    daily_amount: int,
    unit_based: bool,
) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in coverage_entries(revision, daily_amount, unit_based)
    }


def coverage_entries(
    revision: int,
    daily_amount: int,
    unit_based: bool,
) -> list[dict[str, Any]]:
    daily_basis = "daily_per_unit" if unit_based else "daily_total"
    unit_basis = "per_unit" if unit_based else "daily_total"
    cap_basis = "per_unit" if unit_based else "percentage_of_base"
    cap_rate_fields = {} if unit_based else {"rate_percent": 100}
    medical_eligibility = eligibility(revision, "eligible_medical_benefit")
    bonus_fields = {
        "rate_state_key": "prudential_youhuo_bonus_factor_percent",
        "rate_min_percent": 100,
        "rate_max_percent": 130,
    }
    common_payout = {
        "amount_role": "payout",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
    }
    lifetime_cap = daily_amount * 3_000
    surgery_cap_multiplier = 60 if revision <= 7 else 98
    surgery_rate_min = 1 if revision <= 7 else 2
    surgery_rate_max = 300 if revision <= 7 else 490
    entries = [
        entry(
            "remaining-lifetime-medical-cap",
            "累積總給付剩餘上限",
            lifetime_cap,
            unit_basis,
            "相關醫療給付與理賠加值合計以住院保險金日額三千倍為上限；已領金額須依理賠紀錄輸入。",
            "累積總給付金額限制與契約的終止",
            calculation_basis=cap_basis,
            amount_role="limit",
            limit_scope="lifetime",
            aggregation_rule="cumulative_cap",
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            result_kind="reference",
            amount_stage="not_applicable",
            **cap_rate_fields,
        ),
        entry(
            "hospital-daily-benefit",
            "住院日額保險金",
            daily_amount,
            daily_basis,
            "按住院保險金日額乘符合條款的實際住院日數，每次住院最多三百六十五日。",
            "住院日額保險金之給付",
            calculation_basis="table_multiplier",
            limit_scope="per_day",
            multiplier=1,
            quantity_state_key="hospitalization_days",
            quantity_cap=365,
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            aggregate_limit_entry_id="remaining-lifetime-medical-cap",
            **bonus_fields,
            **medical_eligibility,
            **common_payout,
        ),
        entry(
            "intensive-care-additional-benefit",
            "加護病房保險金",
            daily_amount,
            daily_basis,
            "住進符合條款的加護病房時，除住院日額外再按日額二倍給付，每次住院最多三百六十五日。",
            "加護病房保險金之給付",
            calculation_basis="table_multiplier",
            limit_scope="per_day",
            multiplier=2,
            quantity_state_key="intensive_care_days",
            quantity_cap=365,
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            aggregate_limit_entry_id="remaining-lifetime-medical-cap",
            **bonus_fields,
            **medical_eligibility,
            **common_payout,
        ),
        entry(
            "inpatient-surgery-benefit",
            "住院手術費用保險金",
            daily_amount * 20,
            unit_basis,
            "按住院日額二十倍乘 exact product ID 手術附表比率；請輸入同一次住院依條款合併後的附表總比率。",
            "住院手術費用保險金之給付及手術附表",
            calculation_basis="table_multiplier",
            limit_scope="per_hospitalization",
            multiplier_state_key="prudential_youhuo_surgery_rate_percent",
            minimum_multiplier=surgery_rate_min / 100,
            maximum_multiplier=surgery_rate_max / 100,
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            aggregate_limit_entry_id="remaining-lifetime-medical-cap",
            conditions=[
                f"同一次住院手術合計最高為住院日額 {surgery_cap_multiplier} 倍。",
                "同一部位或器官的合併方式及未列手術須依 exact product ID 附表與保險公司認定。",
            ],
            **bonus_fields,
            **medical_eligibility,
            **common_payout,
        ),
        entry(
            "inpatient-surgery-aggregate-cap",
            "同一次住院手術給付上限",
            daily_amount * surgery_cap_multiplier,
            unit_basis,
            f"同一次住院手術費用保險金合計最高為住院日額 {surgery_cap_multiplier} 倍。",
            "住院手術費用保險金之給付",
            calculation_basis=cap_basis,
            amount_role="limit",
            limit_scope="per_hospitalization",
            aggregation_rule="cumulative_cap",
            result_kind="reference",
            amount_stage="not_applicable",
            **cap_rate_fields,
        ),
        entry(
            "inpatient-surgery-nursing-benefit",
            "住院手術看護保險金",
            daily_amount,
            daily_basis,
            "同一次住院接受符合條款的住院手術時，按住院日額五倍給付一次。",
            "住院手術看護保險金之給付",
            calculation_basis="table_multiplier",
            limit_scope="per_hospitalization",
            multiplier=5,
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            aggregate_limit_entry_id="remaining-lifetime-medical-cap",
            **bonus_fields,
            **medical_eligibility,
            **common_payout,
        ),
        entry(
            "outpatient-surgery-benefit",
            "門診手術費用保險金",
            daily_amount,
            daily_basis,
            "每次符合條款的門診手術按住院日額三倍給付；同部位或同器官十四日內多次手術只給一次。",
            "門診手術費用保險金之給付",
            calculation_basis="table_multiplier",
            limit_scope="per_surgery",
            multiplier=3,
            quantity_state_key="outpatient_surgery_count",
            cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
            aggregate_limit_entry_id="remaining-lifetime-medical-cap",
            **bonus_fields,
            **medical_eligibility,
            **common_payout,
        ),
    ]
    if revision <= 5:
        entries.append(
            entry(
                "emergency-medical-transport-benefit",
                "緊急醫療轉送保險金",
                daily_amount,
                daily_basis,
                "以救護車緊急轉送後經醫師診斷必須住院時，按住院日額二倍給付一次。",
                "緊急醫療轉送保險金之給付",
                calculation_basis="table_multiplier",
                limit_scope="per_hospitalization",
                multiplier=2,
                cumulative_paid_state_key="cumulative_medical_benefit_paid_amount",
                aggregate_limit_entry_id="remaining-lifetime-medical-cap",
                **bonus_fields,
                **medical_eligibility,
                **common_payout,
            )
        )
    critical_eligibility = eligibility(
        revision,
        "eligible_initial_critical_or_specific_illness",
    )
    entries.extend(
        [
            entry(
                "initial-critical-or-specific-illness-benefit",
                "初次重大疾病或特定傷病保險金",
                daily_amount,
                daily_basis,
                "符合本版重大疾病或特定傷病定義時，按住院日額三百倍給付一次；身故後才診斷不給付。",
                "重大疾病或特定傷病保險金之給付",
                calculation_basis="table_multiplier",
                limit_scope="lifetime",
                multiplier=300,
                **critical_eligibility,
                **common_payout,
            ),
            entry(
                "future-premium-waiver",
                "重大疾病或特定傷病豁免未來保費",
                None,
                "policy_premium",
                "首次符合重大疾病或特定傷病條件後豁免條款所定未來保費；這是非現金效果。",
                "豁免保險費",
                calculation_basis="waiver",
                amount_role="premium_waiver",
                limit_scope="per_policy",
                aggregation_rule="separate",
                unit_key="remaining_premium_amount",
                policy_state_keys=["remaining_premium_amount"],
                result_kind="non_cash_effect",
                amount_stage="non_cash_estimate",
                **critical_eligibility,
            ),
            entry(
                "initial-sickness-death-premium-refund",
                "生效後三十日內疾病身故退還已收保費",
                None,
                "policy_recorded_limit",
                "被保險人於生效日起三十日內因疾病身故時，無息退還已收保費；金額依繳費紀錄或保險公司核算。",
                "保險責任的開始及交付保險費",
                calculation_basis="policy_state_amount",
                amount_role="payout",
                limit_scope="per_policy",
                aggregation_rule="separate",
                unit_key="prudential_youhuo_initial_sickness_death_refund_amount",
                policy_state_keys=[
                    "prudential_youhuo_initial_sickness_death_refund_amount"
                ],
                result_kind="cash_payout",
                amount_stage="insurer_quoted_amount",
                **eligibility(revision, "initial_30_day_sickness_death_refund"),
            ),
            entry(
                "death-unexpired-premium-refund",
                "身故未到期保險費退還",
                None,
                "policy_recorded_limit",
                "身故使契約終止時按日數比例退還未到期保費；金額依保險公司列示。",
                "契約的終止",
                calculation_basis="policy_state_amount",
                amount_role="payout",
                limit_scope="per_policy",
                aggregation_rule="separate",
                unit_key="unexpired_premium_refund_amount",
                policy_state_keys=["unexpired_premium_refund_amount"],
                result_kind="cash_payout",
                amount_stage="insurer_quoted_amount",
                **eligibility(revision, "death_unexpired_premium_refund"),
            ),
        ]
    )
    return entries


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    version = VERSIONS[product_id]
    if (
        document.get("page_count") != version["page_count"]
        or document.get("pages_parsed") != version["page_count"]
        or str(document.get("source_document_sha256") or "")
        != version["source_document_sha256"]
        or str(document.get("source_text_extractor") or "")
        != version["source_text_extractor"]
    ):
        return None

    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version[
        "source_text_sha256"
    ]:
        return None
    dense = re.sub(r"\s+", "", text)
    required_signals = (
        "保誠人壽優活終身醫療健康保險",
        "累積總給付金額限制與契約的終止",
        "住院日額保險金",
        "加護病房",
        "住院手術",
        "住院手術看護保險金",
        "門診手術",
        "重大疾病或特定傷病保險金",
        "豁免保險費",
        "理賠加值保險金",
        "三千倍",
        "百分之三十",
        "無解約金",
    )
    if any(signal not in dense for signal in required_signals):
        return None

    revision = int(version["revision"])
    old_plan_table = "5001,0001,5002,0002,5003,000" in dense
    modern_plan_formula = (
        "保險計劃數乘上新台幣一百元" in dense
    )
    phase_checks = (
        ("持續治療達六小時" in dense, revision <= 5),
        ("緊急醫療轉送保險金" in dense, revision <= 5),
        ("先天性代謝異常疾病" in dense, revision >= 3),
        ("契約有效期間屆滿後" in dense, revision >= 4),
        (old_plan_table, revision <= 7),
        (modern_plan_formula, revision >= 8),
        ("六十倍" in dense, revision <= 7),
        ("九十八倍" in dense, revision >= 8),
        ("徵詢其他醫師之醫學專業意見" in dense, revision >= 12),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    unit_based = revision >= 8
    claim_inputs_by_event = {
        "eligible_medical_benefit": [
            EVENT_STATE_KEY,
            "prudential_youhuo_bonus_factor_percent",
            "cumulative_medical_benefit_paid_amount",
            "hospitalization_days",
            "intensive_care_days",
            "prudential_youhuo_surgery_rate_percent",
            "outpatient_surgery_count",
        ],
        "eligible_newborn_screening_exception": [
            EVENT_STATE_KEY,
            "prudential_youhuo_bonus_factor_percent",
            "cumulative_medical_benefit_paid_amount",
            "hospitalization_days",
        ],
        "eligible_initial_critical_or_specific_illness": [
            EVENT_STATE_KEY,
            "remaining_premium_amount",
        ],
        "initial_30_day_sickness_death_refund": [
            EVENT_STATE_KEY,
            "prudential_youhuo_initial_sickness_death_refund_amount",
        ],
        "death_unexpired_premium_refund": [
            EVENT_STATE_KEY,
            "unexpired_premium_refund_amount",
        ],
        "disease_waiting_not_met": [EVENT_STATE_KEY],
        "major_disease_waiting_not_met": [EVENT_STATE_KEY],
        "not_eligible_or_uncertain": [EVENT_STATE_KEY],
    }
    version_characteristics = {
        "source_product_id": product_id,
        "product_family": "prudential-youhuo-whole-life-medical",
        "family_fingerprint": FAMILY_FINGERPRINT,
        "company_group": "prudential_life",
        "source_batch_id": "tii-life-014",
        "terms_revision": f"partial_change_{revision}",
        "semantic_phase": semantic_phase(revision),
        "document_code": document_code(revision),
        "source_document_sha256": version["source_document_sha256"],
        "source_text_sha256": version["source_text_sha256"],
        "source_text_extractor": version["source_text_extractor"],
        "source_text_quality": (
            "machine_readable_exact_hash_pymupdf_full_document"
            if version["source_text_extractor"] == "pymupdf"
            else "machine_readable_exact_hash"
        ),
        "source_page_count": version["page_count"],
        "currency_basis": "twd",
        "selection_basis": (
            "policy_plan_number_times_100"
            if unit_based
            else "listed_hcl_plan"
        ),
        "plan_options_stated_in_terms": not unit_based,
        "plan_names": (
            [] if unit_based else [row[1] for row in PLAN_ROWS]
        ),
        "plan_daily_amounts": (
            {} if unit_based else {row[0]: row[2] for row in PLAN_ROWS}
        ),
        "daily_amount_per_plan_number": 100 if unit_based else None,
        "unit_count_required": unit_based,
        "unit_count_positive_integer": unit_based,
        "disease_initial_waiting_days": 30,
        "major_disease_initial_waiting_days": 90,
        "major_disease_reinstatement_waiting_days": (
            0 if revision >= 9 else 90
        ),
        "newborn_screening_waiting_exception": revision >= 3,
        "post_expiry_readmission_excluded": revision >= 4,
        "six_hour_treatment_qualifies": revision <= 5,
        "emergency_transport_benefit_available": revision <= 5,
        "hospital_daily_max_days_per_stay": 365,
        "intensive_care_multiplier": 2,
        "intensive_care_max_days_per_stay": 365,
        "inpatient_surgery_base_multiplier": 20,
        "surgery_schedule_rate_min_percent": 1 if revision <= 7 else 2,
        "surgery_schedule_rate_max_percent": 300 if revision <= 7 else 490,
        "same_stay_surgery_cap_multiplier": 60 if revision <= 7 else 98,
        "modern_nhi_surgery_table_gate": revision >= 8,
        "inpatient_surgery_nursing_multiplier": 5,
        "outpatient_surgery_multiplier": 3,
        "outpatient_repeat_window_days": 14,
        "initial_critical_or_specific_illness_multiplier": 300,
        "initial_critical_or_specific_illness_once_only": True,
        "posthumous_critical_or_specific_diagnosis_payable": False,
        "no_claim_bonus_rate_percent": 30,
        "no_claim_bonus_lookback_policy_years": 3,
        "lifetime_medical_cap_multiplier": 3_000,
        "premium_waiver_available": True,
        "no_cash_surrender_value": True,
        "death_lump_sum_available": False,
        "maturity_benefit_available": False,
        "initial_sickness_death_refund_days": 30,
        "medical_review_wording": revision >= 12,
        "required_policy_inputs": [
            "unit_count" if unit_based else "plan_name"
        ],
        "claim_event_inputs_by_event": claim_inputs_by_event,
        "amount_presentation": (
            "plan_number_with_claim_and_policy_state"
            if unit_based
            else "listed_plan_with_claim_and_policy_state"
        ),
    }
    if unit_based:
        return {
            "selection_type": "unit",
            "input_mode": "unit",
            "selection_source": "terms",
            "selection_label": "保險計劃數",
            "selection_guidance": (
                "請輸入保單面頁記載的正整數保險計劃數；本版條款以計劃數乘新臺幣 100 元計算住院日額。"
            ),
            "version_characteristics": version_characteristics,
            "coverage_entries": coverage_entries(revision, 100, True),
        }
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保險計劃",
        "selection_guidance": (
            "請依保單面頁選擇 HCL-5、10、15、20、25 或 30；本版以條款給付表的固定住院日額計算。"
        ),
        "version_characteristics": version_characteristics,
        "plan_options": [
            {
                "value": value,
                "label": label,
                "coverage_entries": coverage_entries(
                    revision,
                    daily_amount,
                    False,
                ),
            }
            for value, label, daily_amount in PLAN_ROWS
        ],
    }
