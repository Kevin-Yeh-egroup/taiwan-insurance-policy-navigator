from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


GLOBAL_HEALTH_RIDER_FINGERPRINT = "d76e180a26130fedc3560678"
GLOBAL_HEALTH_RIDER_SOURCE_ROWS = (
    ("264391R11AHIR00", 0, "264391R11AHIR-A.pdf", 10, "pypdf", "82b908602963080a9eb3489300a339fe23c879b9d1eaea7818d47baf8a85f626", "445c7cadfb96dba5ae4727202a3f0e48e7f774424136d4d6960b5183cd93f76a"),
    ("264391R11AHIR01", 1, "264391R11AHIR01-A.pdf", 10, "pypdf", "c6018228db362234c9ada743a21095dce9452d02b01a73b0e97e48f19c299cfe", "ffdf6bef7120003ff5e9190158d9c7c2fd82b600ffd074d247a05e3ae6108912"),
    ("264391R11AHIR02", 2, "264391R11AHIR02-A.pdf", 11, "pypdf", "229afc415273691cbd75e5cd25711fdb463f9467d480862f9f4daa7595d06727", "a3aa8cf704719e8e3b10c863d0c2f034a22bddf8e29b4e9c5f390ab4e9bf2c84"),
    ("264391R11AHIR03", 3, "264391R11AHIR03-A.pdf", 10, "pypdf", "0555c3c0a08cba4bddff83790f0533a32dcccbecbaf0845565d180f700559be4", "ef31d98b81f8d0a7a52d1deb84aeb6bc8f400154bae2731daf8c66a56f1e67f5"),
    ("264391R11AHIR04", 4, "264391R11AHIR04-A.pdf", 10, "pypdf", "1feacf4e1c1510ffbb1b25f6778ef6ab094416fcea9dd1232eef1608b43d30e8", "b1077b06b919e70586d269ea89d40d8466653182e1d6343cd79d75dacd9c67c6"),
    ("264391R11AHIR05", 5, "264391R11AHIR05-A.pdf", 11, "pypdf", "b0704c983973f4eed7b4b0686e83009480919477efb48d158df12c8ab4bc1419", "7e07c2efe08b667954d6d50010adcd5223bf67da41ceabd376148b318309c2af"),
    ("264391R11AHIR06", 6, "264391R11AHIR06-A.pdf", 12, "pypdf", "83e7b2553f874d87240a771e3998f771656aba588544b81525df19cd6a38bfb2", "6401a502bf56f734acba08dd5af8f21c26cb49ab139a5ebef8231ea19a23964e"),
    ("264391R11AHIR07", 7, "264391R11AHIR07-A.pdf", 12, "pypdf", "53476f576552164d285bc1a9f757f5f87bd6d7eed72da071fe41a19533904f59", "1c28dff0039bb67cc8203ce5b2260e31ca49f60779ddaf9051fb57329a67d0f1"),
    ("264311R11AHIR08", 8, "264311R11AHIR08-A.pdf", 11, "pypdf", "6480e9e205942a6740bacb30fe6f384d53f248497dbff3013ba752931865c500", "ff11928869d0171bcc1226172d9777f19f4612221e25e33392c564683abaebc2"),
    ("264311RZ1ANIR21A11Z10000009", 9, "264311RZ1ANIR21A11Z10000009-A.pdf", 11, "pypdf", "e6272876391705757ec7d21d95d5b354b0f6c529d491fdc498903a0d0ecdda16", "5d825432775a447365f6697ec44239baca8cd8e9be7dd09442cb5a549a3215c8"),
    ("264311RZ1ANIR21A11Z10000010", 10, "264311RZ1ANIR21A11Z10000010-A.pdf", 12, "pypdf", "7cc67b91bbb4cb0549bceb0fe2cfda4c304115b638062124ebc2c104f52a2bec", "e6e9a2caf05fbe6dd91aa7c12b5d11aba243830c38e1f70157edad90f1607886"),
    ("264311RZ1ANIR21A11Z10000011", 11, "264311RZ1ANIR21A11Z10000011-A.pdf", 12, "pymupdf", "6e03435210c845ce9a6ecf06d0dbb0cb7c360f7a6098e1ab3ff12216b771363f", "38a21f6d0fdddf3d104645ccfe4266588971439a8ccd38a394845d214b873728"),
    ("264311RZ1ANIR21A11Z10000012", 12, "264311RZ1ANIR21A11Z10000012-A.pdf", 12, "pymupdf", "63ac592d291572e092ed4c42dad1fcc97c1db63c6debaadbb22e91dc61b25da6", "b80ecbc35168dcad468ef89574959734e19d72378a3a5e6e8fc7dd91eeafef40"),
    ("264311RZ1ANIR21A11Z10000013", 13, "264311RZ1ANIR21A11Z10000013-A.pdf", 12, "pypdf", "31aee1c4cb3eb3723d73f61b5b2c9f27bddd6e5515c41d7d0f4d179939277168", "e5fb0a0b431b6412dd487b33b623ed1e06f6d460e6f6c5a888a142be09685e5b"),
)
GLOBAL_HEALTH_RIDER_VERSIONS = {
    product_id: {
        "revision": revision,
        "file_name": file_name,
        "page_count": page_count,
        "source_text_extractor": extractor,
        "source_document_sha256": document_sha,
        "source_text_sha256": text_sha,
    }
    for product_id, revision, file_name, page_count, extractor, document_sha, text_sha
    in GLOBAL_HEALTH_RIDER_SOURCE_ROWS
}
GLOBAL_HEALTH_RIDER_PRODUCT_IDS = frozenset(GLOBAL_HEALTH_RIDER_VERSIONS)


def is_global_health_rider_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = GLOBAL_HEALTH_RIDER_VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-164"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "original_same_insurance_accident_90_day_readmission"
    if revision == 1:
        return "global_life_same_insurance_accident_90_day_readmission"
    if revision == 2:
        return "same_hospitalization_14_day_readmission"
    if revision <= 5:
        return "same_policy_year_same_hospitalization"
    if revision <= 7:
        return "newborn_screening_waiting_exception"
    if revision <= 9:
        return "day_hospital_exclusion_disability_wording"
    return "day_hospital_exclusion_work_inability_wording"


def eligibility(revision: int) -> dict[str, Any]:
    ineligible = ["disease_waiting_not_met", "confirmed_not_eligible"]
    uncertain = ["uncertain"]
    if revision < 6:
        ineligible.append("eligible_newborn_screening_exception")
    if revision < 8:
        uncertain.append("day_hospital_or_day_stay")
    else:
        ineligible.append("day_hospital_or_day_stay")
    return {
        "eligibility_state_key": "global_health_event_status",
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def entry(
    entry_id: str,
    name: str,
    amount: int | None,
    basis: str,
    note: str,
    source_ref: str,
    **fields: Any,
) -> dict[str, Any]:
    result = {
        "id": entry_id,
        "name": name,
        "basis": basis,
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        **fields,
    }
    if amount is not None:
        result["amount"] = amount
    return result


def benefit_entries(revision: int, amounts: dict[str, int]) -> list[dict[str, Any]]:
    event_eligibility = eligibility(revision)
    bonus_fields = {
        "rate_state_key": "global_health_bonus_factor_percent",
        "rate_min_percent": 100,
        "rate_max_percent": 150,
    }
    cash_common = {
        "amount_role": "payout",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **event_eligibility,
    }
    entries = [
        entry(
            "hospital-daily-benefit", "住院日額保險金", amounts["hospital"],
            "daily_total", "每日按計畫日額給付，同一事故或住院最高三百六十五日。",
            "保單條款住院日額保險金的給付及保險計畫表",
            calculation_basis="table_multiplier", limit_scope="per_day",
            multiplier=1, quantity_state_key="hospitalization_days",
            quantity_cap=365, conditions=["健康增值比例適用本項。"],
            **bonus_fields, **cash_common,
        ),
        entry(
            "intensive-care-daily-benefit", "加護病房日額保險金", amounts["icu"],
            "daily_total", "入住加護病房期間每日按計畫金額額外給付，最高三十日。",
            "保單條款加護病房日額保險金的給付及保險計畫表",
            calculation_basis="table_multiplier", limit_scope="per_day",
            multiplier=1, quantity_state_key="intensive_care_days",
            quantity_cap=30, conditions=["健康增值比例適用本項。"],
            **bonus_fields, **cash_common,
        ),
        entry(
            "surgery-fixed-benefit", "外科手術定額保險金", amounts["surgery"],
            "benefit_base", "計畫手術基準額乘附表比例；同一住院或事故累計最高基準額三倍。",
            "保單條款外科手術定額保險金的給付、手術附表及保險計畫表",
            calculation_basis="table_multiplier", limit_scope="per_surgery",
            multiplier_state_key="global_health_surgery_schedule_multiplier",
            minimum_multiplier=0.05,
            cumulative_paid_state_key="global_health_same_stay_surgery_paid_amount",
            aggregate_limit_entry_id="surgery-aggregate-cap",
            conditions=["同一部位多項手術按最高比例；不同部位分別計算。", "健康增值比例適用本項。"],
            **bonus_fields, **cash_common,
        ),
        entry(
            "surgery-aggregate-cap", "同一住院或事故手術給付上限", amounts["surgery"] * 3,
            "per_hospitalization_limit", "同一住院或事故外科手術定額保險金累計上限為手術基準額三倍。",
            "保單條款外科手術定額保險金的給付",
            calculation_basis="aggregate_cap", amount_role="limit",
            limit_scope="per_hospitalization", aggregation_rule="cumulative_cap",
            result_kind="reference", amount_stage="not_applicable",
        ),
        entry(
            "major-surgery-additional-benefit", "重大手術增額保險金", amounts["major"],
            "per_event", "手術附表給付比例超過百分之二百時，另按計畫金額給付一次。",
            "保單條款重大手術增額保險金的給付及保險計畫表",
            calculation_basis="fixed_amount", amount_role="payout",
            limit_scope="per_surgery", aggregation_rule="separate",
            multiplier_state_key="global_health_surgery_schedule_multiplier",
            minimum_multiplier=2.000001, result_kind="cash_payout",
            amount_stage="gross_contract_benefit",
            conditions=["手術附表比例必須嚴格大於百分之二百；健康增值比例不適用本項。"],
            **event_eligibility,
        ),
        entry(
            "misc-medical-daily-benefit", "住院雜項醫療日額保險金", amounts["misc"],
            "daily_total", "每日按計畫金額給付，最高三十日。",
            "保單條款住院雜項醫療日額保險金的給付及保險計畫表",
            calculation_basis="per_day", amount_role="payout",
            limit_scope="per_day", aggregation_rule="separate",
            quantity_state_key="hospitalization_days", quantity_cap=30,
            result_kind="cash_payout", amount_stage="gross_contract_benefit",
            conditions=["健康增值比例不適用本項。"], **event_eligibility,
        ),
    ]
    waiver_eligibility = {
        "eligibility_state_key": "global_health_work_inability_status",
        "ineligible_values": ["not_persisting_180_days"],
        "uncertain_values": ["uncertain"],
    }
    entries.extend(
        [
            entry(
                "first-180-day-premium-refund", "前一百八十日已繳保費退還", None,
                "policy_recorded_limit", "喪失工作能力持續一百八十日時，退還診斷日起前一百八十日內已到期並繳交的本附約保費。",
                "保單條款附約保險費的豁免",
                calculation_basis="policy_state_amount", amount_role="payout",
                limit_scope="per_policy", aggregation_rule="separate",
                unit_key="global_health_premiums_paid_within_180_days",
                policy_state_keys=["global_health_premiums_paid_within_180_days"],
                result_kind="cash_payout", amount_stage="insurer_quoted_amount",
                **waiver_eligibility,
            ),
            entry(
                "future-premium-waiver", "未來附約保險費豁免", None,
                "policy_premium", "喪失工作能力持續一百八十日後，於狀態持續期間豁免本附約未到期保費。",
                "保單條款附約保險費的豁免",
                calculation_basis="waiver", amount_role="premium_waiver",
                limit_scope="per_policy", aggregation_rule="separate",
                unit_key="remaining_premium_amount",
                policy_state_keys=["remaining_premium_amount"],
                result_kind="non_cash_effect", amount_stage="non_cash_estimate",
                conditions=["只及於本被保險人的本附約，不是現金保險金。"],
                **waiver_eligibility,
            ),
        ]
    )
    return entries


PLAN_ROWS = (
    ("HI-05", "基本計畫", 500, 1000, 10000, 10000, 250),
    ("HI-10", "計畫一", 1000, 1500, 15000, 15000, 500),
    ("HI-20", "計畫二", 2000, 2000, 20000, 20000, 1000),
    ("HI-30", "計畫三", 3000, 3000, 25000, 25000, 1500),
    ("HI-40", "計畫四", 4000, 4000, 30000, 30000, 2000),
)


def parse_global_health_rider_plan(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_global_health_rider_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    version = GLOBAL_HEALTH_RIDER_VERSIONS[product_id]
    if (
        document.get("page_count") != version["page_count"]
        or document.get("pages_parsed") != version["page_count"]
        or str(document.get("source_document_sha256") or "") != version["source_document_sha256"]
        or str(document.get("source_text_extractor") or "") != version["source_text_extractor"]
    ):
        return None
    text = " ".join(unicodedata.normalize("NFKC", str(document.get("text") or "")).split())
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version["source_text_sha256"]:
        return None
    dense = re.sub(r"\s+", "", text)
    if any(signal not in dense for signal in ("健康保險", "住院日額保險金", "外科手術定額保險金", "健康增值保險金", "保險計劃表")):
        return None

    revision = int(version["revision"])
    claim_inputs = [
        "global_health_event_status", "hospitalization_days",
        "intensive_care_days", "global_health_surgery_schedule_multiplier",
        "global_health_same_stay_surgery_paid_amount",
        "global_health_bonus_factor_percent",
        "global_health_work_inability_status",
        "global_health_premiums_paid_within_180_days",
        "remaining_premium_amount",
    ]
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保險計畫",
        "selection_guidance": "請依保單首頁或批註選擇 HI 計畫；本商品沒有投保單位數。",
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "global-health-rider",
            "family_fingerprint": GLOBAL_HEALTH_RIDER_FINGERPRINT,
            "company_group": "global_life",
            "source_batch_id": "tii-life-164",
            "terms_revision": "original" if revision == 0 else f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": False,
            "plan_table_in_terms": True,
            "plan_option_count": 5,
            "unit_count_required": False,
            "disease_waiting_days": 30,
            "accident_waiting_period_exempt": True,
            "newborn_screening_waiting_exception": revision >= 6,
            "readmission_rule_days": 90 if revision <= 1 else 14 if revision == 2 else 0,
            "same_insurance_accident_wording": revision <= 1,
            "same_hospitalization_policy_year_wording": revision >= 3,
            "day_hospital_excluded": revision >= 8,
            "disability_terminology": "喪失工作能力" if revision >= 10 else "失能",
            "hospital_daily_day_limit": 365,
            "intensive_care_day_limit": 30,
            "misc_medical_day_limit": 30,
            "surgery_rate_min_percent": 5,
            "surgery_rate_max_percent": 300,
            "surgery_aggregate_limit_multiplier": 3,
            "major_surgery_threshold_percent": 200,
            "no_claim_bonus_schedule_percent": [100, 120, 130, 140, 150],
            "work_inability_waiver_days": 180,
            "death_cash_benefit_available": False,
            "outpatient_medical_benefit_available": False,
            "maturity_benefit_available": False,
            "premium_waiver_available": True,
            "required_policy_inputs": ["plan_name"],
            "claim_event_inputs": claim_inputs,
            "amount_presentation": "selected_plan_amounts_with_claim_and_policy_inputs",
        },
        "plan_options": [
            {
                "value": code,
                "label": f"{code} {label}",
                "coverage_entries": benefit_entries(
                    revision,
                    {"hospital": hospital, "icu": icu, "surgery": surgery, "major": major, "misc": misc},
                ),
            }
            for code, label, hospital, icu, surgery, major, misc in PLAN_ROWS
        ],
    }
