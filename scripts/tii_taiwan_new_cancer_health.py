from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "522347467635c4e200d9aad0"
SOURCE_ROWS = (
    ("202321M11A68100", 0, "202321M11A68100-A.pdf", 7, "pymupdf", "8bb8433a867c35e62d3d37ca098fa8765a4187524d1adb2f99f499cf228a5095", "c2f69939c1390593646c8711bed729029246115316369568089ed3c18cd511e0"),
    ("202321M11A68101", 1, "202321M11A68101-A.pdf", 7, "pymupdf", "4a651a514914907da1dde3f9f59f63f19c28244d7a4b0b209c932e60f203a500", "fd4bf7455a130aeab03430595dcd3f83fe4cb088b987b8a2d0222764535586ac"),
    ("202321M11A68102", 2, "202321M11A68102-A.pdf", 7, "pymupdf", "889362822ee150da93686c13fb2f24416418ddc8b9f2b6c42a15a21c26e44fb1", "0c6c062ebc482476d3d46be8a5dd97f13d16207f2b0bb1ffd45edf0bf5368d85"),
    ("202321M11A68103", 3, "202321M11A68103-A.pdf", 7, "pypdf", "d73480f68c41d76a1711249062e403fba67f5ec02bb930760e9a674d46db7fec", "26119e064c1f815449db501709a9e72845ad789dbd3c6557ae9686ae42f82037"),
    ("202321M11A68104", 4, "202321M11A68104-A.pdf", 7, "pypdf", "76c884de841383aaca7a5ad31133270bbed8203abc3469848ac64dd2dbc5d019", "f1848150423506b66242b2a0c9f3b68c2a33eee2a5b5297e475118983bd53cfe"),
    ("202321M11A68105", 5, "202321M11A68105-A.pdf", 7, "pypdf", "3dc1465cb6828f2c8a20e6df97b2ea9c4c54c3f8db9e8d169671503dd7d30328", "97d49bd42dbf4757270e7878917a8d525f123b9d6264969098b8a16f8093c0fe"),
    ("202321MZ1A68121A11Z10000006", 6, "202321MZ1A68121A11Z10000006-A.pdf", 7, "pypdf", "4c31f4a14005c13891405ba80cb65d0104d9642ad986747da62a7eebd25d4304", "478b0ebcd610324a92fb45d06d583807102524acb920a24ea70e17c9935598c8"),
    ("202321MZ1A68121A11Z10000007", 7, "202321MZ1A68121A11Z10000007-A.pdf", 7, "pypdf", "f2fb380976d3c3b8531ed37fd5d1998c8185e8a4e347d15489fe405ed9ab9b81", "ab996f4f6a8a904bf639494656a836ac1867dd88f86703e1f25682fefe8b8f58"),
    ("202321MZ1A68121A11Z10000008", 8, "202321MZ1A68121A11Z10000008-A.pdf", 7, "pypdf", "37844f04fed5e2d05eff8ae9f6dcddba2c4cd9c1e7eb76c8b5ca67c1d2574d2d", "e00c4437955accb547c973aa58dfd5a2ece52acba543a83d3d94f2f4a52e3fc3"),
    ("202321MZ1A68121A11Z10000009", 9, "202321MZ1A68121A11Z10000009-A.pdf", 7, "pypdf", "9b51444c3c7299f6ae78c1c4cd0e38d63c1d1a6e35d81237d3f45cab92ac2fea", "9b636abd130cfdd40256fe21f02c99111c3995724e3f3296b04420ad16a4fcc0"),
    ("202321MZ1A68121A11Z10000010", 10, "202321MZ1A68121A11Z10000010-A.pdf", 6, "pypdf", "4a457109d282d8e6cd05071f580408f68ca9c34e98aaf957421060c3e0168a7e", "7b59c696f1817a4643fa962a57bb704c2e47f8eb4a1e92c22ba931e4449e7c1b"),
    ("202321MZ1A68121A11Z10000011", 11, "202321MZ1A68121A11Z10000011-A.pdf", 6, "pypdf", "3368d2427dea3c21e2794d3392016b101a6ca3137a559eef1382bdbeeb9c41fc", "30e303c3d1a4f44f4f400905e3abbe020931dd2b15436c8cd1e0b90194832242"),
    ("202321MZ1A68121A11Z10000012", 12, "202321MZ1A68121A11Z10000012-A.pdf", 7, "pypdf", "09afb9f3ffd9cc6330823dc89831f703660c61489864dd8afb81515723d771a4", "5bf8e200382b538ef53f289b941f23a69a554285919d36dc1a462055cb258f9a"),
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
        and str(document.get("batch_id") or "") == "tii-life-008"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "legacy-inception-waiting-original"
    if revision <= 2:
        return "reinstatement-ten-day-waiting"
    if revision == 3:
        return "post-expiry-readmission-exclusion"
    if revision <= 7:
        return "medical-corporation-and-claim-document-update"
    if revision == 8:
        return "inception-waiting-only"
    if revision == 9:
        return "inclusive-disability-wording-update"
    if revision == 10:
        return "modern-cancer-definition"
    return "modern-cancer-definition-medical-review"


EVENT_STATE_KEY = "taiwan_new_cancer_health_event_status"
EVENT_VALUES = {
    "eligible_cancer_hospitalization",
    "eligible_home_recovery",
    "eligible_cancer_death",
    "diagnosed_within_initial_waiting_period",
    "eligible_non_cancer_death_refund",
    "not_eligible_or_uncertain",
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


def event_exclusions(*eligible_values: str) -> list[str]:
    return sorted(EVENT_VALUES - set(eligible_values))


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    waiting_condition = (
        "生效日起九十日內為癌症等待期間；復效日含起另有十日等待期間。"
        if 1 <= revision <= 7
        else "生效日起九十日內為癌症等待期間；本版條款未另列復效等待日數。"
    )
    common = {
        "amount_role": "payout",
        "aggregation_rule": "separate",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        "exclusion_state_key": EVENT_STATE_KEY,
    }
    return [
        entry(
            "cancer-hospital-daily",
            "癌症住院醫療保險金",
            2_500,
            "daily_per_unit",
            "每投保單位每日 2,500 元，最多二單位；條款明列住院日數不受限制，至保單失效為止。",
            "保單條款第八條",
            calculation_basis="per_unit_per_day",
            limit_scope="per_day",
            quantity_state_key="cancer_hospitalization_days",
            exclusion_values=event_exclusions(
                "eligible_cancer_hospitalization"
            ),
            conditions=[waiting_condition, "限因癌症直接治療而住院。"],
            **common,
        ),
        entry(
            "cancer-home-recovery",
            "在家療養保險金",
            15_000,
            "per_unit",
            "連續住院六日以上後出院在家療養，每投保單位每次 15,000 元；最多二單位，每保險年度最多三次。",
            "保單條款第九條",
            calculation_basis="per_unit",
            limit_scope="annual",
            quantity_state_key=(
                "taiwan_new_cancer_home_recovery_claim_count"
            ),
            quantity_cap=3,
            multiplier_state_key="cancer_hospitalization_days",
            minimum_multiplier=6,
            exclusion_values=event_exclusions("eligible_home_recovery"),
            conditions=[waiting_condition, "本次連續住院須達六日。"],
            **common,
        ),
        entry(
            "cancer-death",
            "因癌身故保險金",
            180_000,
            "per_unit",
            "每投保單位 180,000 元，最多二單位。",
            "保單條款第十條",
            calculation_basis="per_unit",
            limit_scope="per_policy",
            exclusion_values=event_exclusions("eligible_cancer_death"),
            conditions=[waiting_condition, "須為首次罹患癌症而直接致身故。"],
            **common,
        ),
        entry(
            "waiting-period-premium-refund",
            "等待期間內確診退還保險費",
            None,
            "policy_recorded_limit",
            "生效日起九十日內首次確診癌症時，無息返還已收保險費並終止契約；請輸入保單或保險公司核算金額。",
            "保單條款第二條",
            calculation_basis="policy_state_amount",
            limit_scope="per_policy",
            unit_key="taiwan_new_cancer_waiting_refund_amount",
            policy_state_keys=[
                "taiwan_new_cancer_waiting_refund_amount"
            ],
            exclusion_values=event_exclusions(
                "diagnosed_within_initial_waiting_period"
            ),
            amount_stage="insurer_quoted_amount",
            **{
                key: value
                for key, value in common.items()
                if key != "amount_stage"
            },
        ),
        entry(
            "non-cancer-death-current-year-premium-refund",
            "非癌身故退還金",
            None,
            "policy_recorded_limit",
            "個人保險單退還當年度已繳保險費總額；家庭保險單退還其半數，其他家庭成員當年度保障仍有效。",
            "保單條款第十一條",
            calculation_basis="policy_state_amount",
            limit_scope="per_policy",
            unit_key="current_policy_year_paid_premium_amount",
            policy_state_keys=["current_policy_year_paid_premium_amount"],
            rate_percent=50,
            rate_condition_state_key="taiwan_new_cancer_policy_form",
            rate_condition_value="family",
            exclusion_values=event_exclusions(
                "eligible_non_cancer_death_refund"
            ),
            amount_stage="gross_contract_benefit",
            **{
                key: value
                for key, value in common.items()
                if key != "amount_stage"
            },
        ),
    ]


def expected_entry_contracts(revision: int) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in coverage_entries(revision)
    }


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
        "台灣人壽新防癌健康保險",
        "住院醫療保險金的給付",
        "每單位新台幣貳仟伍佰元正",
        "其住院日數不受限制",
        "每天最高給付額為二單位",
        "連續住院六(含)日以上",
        "壹萬伍仟元正",
        "最高給付次數為三次",
        "每單位新台幣壹拾捌萬元",
        "非癌身故退還金的給付",
        "當年度所繳保險費總額之半數",
    )
    if any(signal not in dense for signal in required_signals):
        return None

    revision = int(version["revision"])
    phase_checks = (
        ("復效日(含)起十日" in dense, 1 <= revision <= 7),
        (
            "本公司就再次住院部分不予給付保險金" in dense,
            revision >= 3,
        ),
        ("醫療法人" in dense, revision >= 4),
        ("受益人的身分證明" in dense, revision >= 4),
        ("子女機能障礙" in dense, revision >= 9),
        ("國際疾病傷害及死因分類標準" in dense, revision >= 10),
        ("基於審核保險金之需要" in dense, revision >= 11),
        ("並解除本契約" in dense, revision == 0),
        ("本契約效力即行終止" in dense, revision >= 1),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    claim_inputs_by_event = {
        "eligible_cancer_hospitalization": [
            EVENT_STATE_KEY,
            "cancer_hospitalization_days",
        ],
        "eligible_home_recovery": [
            EVENT_STATE_KEY,
            "cancer_hospitalization_days",
            "taiwan_new_cancer_home_recovery_claim_count",
        ],
        "eligible_cancer_death": [EVENT_STATE_KEY],
        "diagnosed_within_initial_waiting_period": [
            EVENT_STATE_KEY,
            "taiwan_new_cancer_waiting_refund_amount",
        ],
        "eligible_non_cancer_death_refund": [
            EVENT_STATE_KEY,
            "taiwan_new_cancer_policy_form",
            "current_policy_year_paid_premium_amount",
        ],
        "not_eligible_or_uncertain": [EVENT_STATE_KEY],
    }
    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "selection_label": "投保單位數",
        "selection_guidance": (
            "請輸入保單記載的一或二單位，再選擇本次要查看的癌症住院、在家療養、身故或退費情境。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "taiwan-new-cancer-health",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "company_group": "taiwan_life",
            "source_batch_id": "tii-life-008",
            "terms_revision": f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": (
                "machine_readable_exact_hash_pymupdf_recovery"
                if version["source_text_extractor"] == "pymupdf"
                else "machine_readable_exact_hash"
            ),
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "unit_count_required": True,
            "unit_count_positive_integer": True,
            "maximum_units_per_insured": 2,
            "cancer_initial_waiting_days": 90,
            "cancer_reinstatement_waiting_days": (
                10 if 1 <= revision <= 7 else 0
            ),
            "post_expiry_readmission_excluded": revision >= 3,
            "medical_corporation_hospital_wording": revision >= 4,
            "inclusive_disability_wording": revision >= 9,
            "modern_cancer_definition": revision >= 10,
            "medical_review_wording": revision >= 11,
            "hospital_daily_amount_per_unit": 2_500,
            "hospital_daily_day_limit": None,
            "home_recovery_amount_per_unit": 15_000,
            "home_recovery_minimum_hospital_days": 6,
            "home_recovery_annual_claim_limit": 3,
            "cancer_death_amount_per_unit": 180_000,
            "waiting_period_premium_refund_available": True,
            "non_cancer_death_current_year_premium_refund": True,
            "required_policy_inputs": ["unit_count"],
            "claim_event_inputs_by_event": claim_inputs_by_event,
            "amount_presentation": (
                "unit_count_with_cancer_event_and_policy_state"
            ),
        },
        "coverage_entries": coverage_entries(revision),
    }
