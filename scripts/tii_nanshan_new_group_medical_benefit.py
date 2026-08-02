from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "f497d4c1ed5cd39f4aec740f"
SOURCE_ROWS = (
    ("206317M11A30200", 0, "206317M11A30200-A.pdf", 13, "pypdf", "7e54fec7a2a0a7d11e1ce1b46bd010192efd5a9282fdb8ca9d644be65feed72c", "1aee5030dd6132482ccd31fc762bcdb6216540c74da1384efa04c2ffdcaf83ce"),
    ("206317M11A30201", 1, "206317M11A30201-A.pdf", 14, "pypdf", "e258c1c5fc2a0f9c7239f1990ce0cf86cd884aa900f636dd7023c8553dc7c4e6", "19658ab805d599d5987e76b0531fda603756d632f079e0894304513f36f8b9be"),
    ("206317M11A30202", 2, "206317M11A30202-A.pdf", 14, "pypdf", "2fd874c1805b20602552c05fa11e71da70371aab05998a4b752202871f4097f8", "b50f70eae25f687ccf0c2afb7ebf210ee8e7b71e725022e17291737911795845"),
    ("206317M11A30203", 3, "206317M11A30203-A.pdf", 13, "pypdf", "94eb3cd4f2d249b296bf1a6eff4b6ed46fa6a9e8f45a68e1d6b49f5365e21556", "3b6ce1fc80d1e6cf646108734db86ca6b775921d616d7a1bff896349673a4931"),
    ("206317M11A30204", 4, "206317M11A30204-A.pdf", 13, "pypdf", "1b7aa24a1309bac9ef83ab21622d4ce4d91870b6add83774627e083aeb8759c3", "0e5d95fb9fc93f0ff90a16bd58d9f0e3384beba680fe8dcf73a66c07b88596a9"),
    ("206317M11A30205", 5, "206317M11A30205-A.pdf", 13, "pypdf", "4e2db9a990432fd9c7217779b6c54cae5c301b25b2327ca872fbd459212f7b73", "3054d930abe8bb65e293cb5c6e3393b437dea99f3e63577a190aea9fed92d3b2"),
    ("206313M11A30306", 6, "206313M11A30306-A.pdf", 14, "pypdf", "1c44c7c1d52e7ae45c36c29d352c002ca2b7071633e56a070030558095fa0cec", "060ebbbdc91da1b57df71aaa0b87c60f123395d83d7a2c8991acf5ed89c453d7"),
    ("206313M11A30307", 7, "206313M11A30307-A.pdf", 13, "pypdf", "a985d7a8ad3ac1d7e892db3d187d7f78d4a01f7631c8ef74a3cd73b040ac75b5", "53d28142ebab579d04bb3f4bb2b53702a9f51e5f240f7d7dace0711843f0c426"),
    ("206313MZ1A30221A11Z10000008", 8, "206313MZ1A30221A11Z10000008-A.pdf", 13, "pypdf", "c262aefb14d47fced836d3c053d79912f28803aac5ff610e9d38937d4bcf2216", "84fe5ce1fec902ca062fc0a124ed79a353ef23a66df21e3a2b1d34caa3e0f332"),
    ("206313MZ1A30221A11Z10000009", 9, "206313MZ1A30221A11Z10000009-A.pdf", 13, "pypdf", "58b659450ea283e63e784cb35bd7e87558b6d6fe0e0687f22c565001c1096090", "3a0823e8863087325f2daf9710b40aba173bb716d2bd538e651e162dacfc0f0e"),
    ("206313MZ1A30221A11Z10000010", 10, "206313MZ1A30221A11Z10000010-A.pdf", 13, "pypdf", "0572a7c9d2fe8e7c5ce86d936ba2c14f50dd756eee21175349281266d4456b50", "5d3fecffdb2a76845d5ca1d148813c519cfe45923fca280e1f2f1c3b554090b4"),
    ("206313MZ1A30221A11Z10000011", 11, "206313MZ1A30221A11Z10000011-A.pdf", 13, "pypdf", "4be7cc93641b0385fae4d6d562df12a92b91ef11ef95f1707dae6bdb588f9479", "c465143866e1c8eee464e41b2ba98dc92276b44adcd58293337dfeb71a8124da"),
    ("206313MZ1A30221A11Z10000012", 12, "206313MZ1A30221A11Z10000012-A.pdf", 12, "pypdf", "bb9d2c174e0467744679c60720610c98a0b2c9dc00106652dbe65c2c857ebcf7", "4c8b53c4a837d3f402d752af1a4d8397de8e32038e4b27e1235479ff7d27492e"),
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

DAILY_ROOM_LIMIT_KEY = "nanshan_new_group_daily_room_limit"
MISC_LIMIT_KEY = "nanshan_new_group_misc_limit"
PHYSICIAN_DAILY_LIMIT_KEY = "nanshan_new_group_physician_daily_limit"
SURGERY_BASE_LIMIT_KEY = "nanshan_new_group_surgery_base_limit"
SURGERY_RATE_KEY = "nanshan_new_group_surgery_schedule_rate"

SURGERY_SCHEDULE_PERCENT_OPTIONS = (
    3, 5, 7, 8, 10, 12, 13, 15, 18, 19, 20, 25, 30, 32, 35, 38,
    40, 45, 50, 55, 60, 63, 65, 75, 85, 100,
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return " ".join(normalized.split())


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", normalize_text(text))


def is_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    version = VERSIONS.get(product_id)
    return bool(
        version
        and str(document.get("batch_id") or "") == "tii-life-032"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def semantic_phase(revision: int) -> str:
    if revision <= 5:
        return "legacy-claim-documents"
    if revision <= 8:
        return "beneficiary-identity-document"
    if revision == 9:
        return "nhi-noncovered-expense-clarification"
    return "medical-opinion-review"


def limit_entry(
    entry_id: str,
    name: str,
    unit_key: str,
    *,
    limit_rate: float = 1,
    limit_scope: str,
    aggregation_rule: str = "separate",
    benefit_group_id: str | None = None,
    amount_role: str = "limit",
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": entry_id,
        "name": name,
        "amount": None,
        "basis": "policy_recorded_limit",
        "source": "terms",
        "note": "依要保書記載限額換算；實際給付仍以符合條款的醫療費用為上限。",
        "source_ref": "第十六條醫療保險金的給付",
        "calculation_basis": "reimbursement_with_cap",
        "amount_role": amount_role,
        "unit_key": unit_key,
        "limit_scope": limit_scope,
        "aggregation_rule": aggregation_rule,
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        "conditions": conditions or [],
    }
    if limit_rate != 1:
        entry["limit_rate_percent"] = int(limit_rate * 100)
    if benefit_group_id:
        entry["benefit_group_id"] = benefit_group_id
    return entry


def coverage_entries() -> list[dict[str, Any]]:
    room_group = "nanshan-new-group-room-daily-limit"
    misc_group = "nanshan-new-group-misc-shared-limit"
    expense_choice_group = "nanshan-new-group-expense-or-cash-choice"
    entries = [
        limit_entry(
            "daily-room-reimbursement-limit",
            "每日住院費給付上限",
            DAILY_ROOM_LIMIT_KEY,
            limit_scope="per_day",
            aggregation_rule="highest",
            benefit_group_id=room_group,
            conditions=["病房、膳食及一般護理費，以每日住院費保險金限額為每日上限。"],
        ),
        limit_entry(
            "icu-daily-room-reimbursement-limit",
            "加護病房每日給付上限",
            DAILY_ROOM_LIMIT_KEY,
            limit_rate=2,
            limit_scope="per_day",
            aggregation_rule="highest",
            benefit_group_id=room_group,
            conditions=["加護病房最初七日的每日住院費限額調整為兩倍。"],
        ),
        limit_entry(
            "surgery-stay-daily-room-reimbursement-limit",
            "手術住院期間每日給付上限",
            DAILY_ROOM_LIMIT_KEY,
            limit_rate=1.5,
            limit_scope="per_day",
            aggregation_rule="highest",
            benefit_group_id=room_group,
            conditions=["以健保身分住院並接受外科手術時，非加護病房日的每日住院費限額為一點五倍。"],
        ),
        limit_entry(
            "hospital-misc-shared-reimbursement-limit",
            "住院雜費、意外急診與住院前後門診共用上限",
            MISC_LIMIT_KEY,
            limit_scope="per_hospitalization",
            aggregation_rule="highest",
            benefit_group_id=misc_group,
            conditions=["三項合計不超過要保書記載的醫院各項雜費保險金限額。"],
        ),
        {
            "id": "accident-emergency-fixed-sublimit",
            "name": "意外事故急診醫療費上限",
            "amount": 5_000,
            "basis": "per_event_limit",
            "source": "terms",
            "note": "意外事故發生後二十四小時內接受急診醫療；仍受醫院各項雜費共用上限約束。",
            "source_ref": "第十六條第二款意外事故急診醫療費保險金",
            "calculation_basis": "fixed_amount",
            "amount_role": "limit",
            "limit_scope": "per_event",
            "aggregation_rule": "cumulative_cap",
            "benefit_group_id": misc_group,
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            "conditions": ["同一事故最高新台幣五千元。"],
        },
        limit_entry(
            "pre-post-hospital-outpatient-per-visit-limit",
            "住院前後門診每次給付上限",
            PHYSICIAN_DAILY_LIMIT_KEY,
            limit_scope="per_visit",
            conditions=["住院前一週及出院後一週，每日一次；住院曾接受手術者，出院後延長為兩週。"],
        ),
        limit_entry(
            "physician-consultation-daily-limit",
            "醫師診查費每日給付上限",
            PHYSICIAN_DAILY_LIMIT_KEY,
            limit_scope="per_day",
            conditions=["同一次住院最多三百六十五日；手術時主治醫師診查費併入外科手術費。"],
        ),
        {
            "id": "surgery-schedule-limit",
            "name": "外科手術費給付上限",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "以要保書外科手術費限額乘以附表百分率；附表一百項目依條款提高為四百百分率。",
            "source_ref": "第十六條第四款及附表一外科手術費用表",
            "calculation_basis": "table_multiplier",
            "amount_role": "limit",
            "unit_key": SURGERY_BASE_LIMIT_KEY,
            "multiplier": 1,
            "rate_state_key": SURGERY_RATE_KEY,
            "rate_min_percent": 3,
            "rate_max_percent": 400,
            "limit_scope": "per_surgery",
            "aggregation_rule": "separate",
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            "conditions": [
                "不同手術位置的多項手術原則上合計不超過外科手術費限額。",
                "同一手術位置取最高附表百分率；未列手術須由保險公司比照協議。",
                "附表百分率一百的項目提高為四百，合計上限也改為四倍。",
            ],
        },
        limit_entry(
            "hospital-cash-alternative-daily",
            "住院費用補償保險金每日金額",
            DAILY_ROOM_LIMIT_KEY,
            limit_scope="per_day",
            aggregation_rule="choose_one",
            benefit_group_id=expense_choice_group,
            amount_role="payout",
            conditions=["與第十六、十七條實支實付各項保險金擇一，同一次住院最多三百六十五日。"],
        ),
        limit_entry(
            "accident-accessory-per-item-limit",
            "意外附屬品每件上限",
            DAILY_ROOM_LIMIT_KEY,
            limit_rate=2,
            limit_scope="per_item",
            aggregation_rule="cumulative_cap",
            benefit_group_id="nanshan-new-group-accident-accessory-limit",
            conditions=["不含義肢、義眼；因意外傷害所致且裝設以一次為限。"],
        ),
        limit_entry(
            "accident-accessory-aggregate-limit",
            "同一意外附屬品合計上限",
            DAILY_ROOM_LIMIT_KEY,
            limit_rate=10,
            limit_scope="per_event",
            aggregation_rule="cumulative_cap",
            benefit_group_id="nanshan-new-group-accident-accessory-limit",
            conditions=["同一意外事故含義肢、義眼的最高給付總額。"],
        ),
    ]
    return entries


def expected_entry_contracts() -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        item["id"]: {
            key: value
            for key, value in item.items()
            if key not in ignored and key != "id"
        }
        for item in coverage_entries()
    }


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    version = VERSIONS[product_id]
    if (
        document.get("page_count") != version["page_count"]
        or document.get("pages_parsed") != version["page_count"]
        or str(document.get("source_text_extractor") or "")
        != version["source_text_extractor"]
    ):
        return None
    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version[
        "source_text_sha256"
    ]:
        return None
    dense = compact_text(text)
    common_signals = (
        "每日住院費保險金",
        "加護病房寬額保險金",
        "住院費用增額補償保險金",
        "醫院各項雜費保險金",
        "意外事故急診醫療費保險金",
        "住院前後門診費用保險金",
        "醫師診查費保險金",
        "外科手術費保險金",
        "住院費用補償保險金",
        "最高補償額給付百分率",
        "三百六十五日",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(version["revision"])
    phase_checks = (
        ("受益人的身分證明" in dense, revision >= 6),
        ("已獲得全民健康保險給付的部分" in dense, revision >= 9),
        ("徵詢其他醫師之醫學專業意見" in dense, revision >= 10),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    required_policy_inputs = [
        DAILY_ROOM_LIMIT_KEY,
        MISC_LIMIT_KEY,
        PHYSICIAN_DAILY_LIMIT_KEY,
        SURGERY_BASE_LIMIT_KEY,
    ]
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "要保書記載醫療給付限額",
        "selection_guidance": (
            "請依本 productId 對應的要保書輸入每日住院費、醫院各項雜費、"
            "每日醫師診查費及外科手術費限額；手術項目再選擇附表百分率。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "nanshan-new-group-medical-benefit",
            "company_group": "nanshan_life",
            "source_batch_id": "tii-life-032",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "terms_revision": "initial" if revision == 0 else f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "currency_basis": "twd",
            "group_policy": True,
            "policy_term_years": 1,
            "plan_options": False,
            "unit_count_required": False,
            "benefit_entry_count": len(coverage_entries()),
            "actual_expense_reimbursement": True,
            "hospitalization_day_limit": 365,
            "icu_multiplier": 2,
            "icu_multiplier_day_limit": 7,
            "surgery_stay_multiplier": 1.5,
            "accident_emergency_sublimit": 5_000,
            "surgery_schedule_percent_options": list(SURGERY_SCHEDULE_PERCENT_OPTIONS),
            "surgery_schedule_100_percent_special_cap_percent": 400,
            "outpatient_surgery_covered": True,
            "hospital_cash_alternative_available": True,
            "beneficiary_identity_document_required": revision >= 6,
            "nhi_covered_amount_excluded": revision >= 9,
            "medical_opinion_review_available": revision >= 10,
            "original_receipt_required": False,
            "death_benefit_available": False,
            "premium_waiver_available": False,
            "required_policy_inputs": required_policy_inputs,
            "claim_event_inputs": [SURGERY_RATE_KEY],
            "amount_presentation": "policy_recorded_limits_with_fixed_and_schedule_multipliers",
        },
        "coverage_entries": coverage_entries(),
    }
