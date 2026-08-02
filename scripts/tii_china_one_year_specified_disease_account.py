from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "a65f76119967794809e85db3"
SOURCE_ROWS = (
    ("205351R11A54800", 0, "205351R11A54800-A.pdf", 9, "pypdf", "a9118997ecf7e08e2c95e7ffda3313b6a4595d9255611dc609b27665c508fd62", "40d8e20687fe9fd931c3e7301c108ec02e457c4706a6581ebfb4b2588bdd26ec"),
    ("205351R11A54801", 1, "205351R11A54801-A.pdf", 9, "pypdf", "a1240b6f8ca442bb87f51c8486e2dfc9819e8234243583b74caf2e535cfba8d9", "51f7891f66f9c09a26cfbc56b5c2b6b13d3f5f1ebb7d17eae115c15755cdb516"),
    ("205351R11A54802", 2, "205351R11A54802-A.pdf", 9, "pypdf", "e99168b1346e280a92820d551189605da8cf68b09003f511a221ccb9fb20930a", "1cb979c42c2eda1064fef2663565d56dbca7b264176732d546f1afa5511b8966"),
    ("205351R11A54803", 3, "205351R11A54803-A.pdf", 9, "pypdf", "73909f60029975948a4de74a884c82f9d58a2f871cb411aa05545402db61c9b6", "adb5f5ef4f36c32c272c878ab624bfb93165df332e2448275b3f1195b74ee2fd"),
    ("205351R11A54804", 4, "205351R11A54804-A.pdf", 9, "pypdf", "bf52af2164d610f06c00f2d1e880001ec6ffc639bc6675150228f6a60917f1e5", "67e762fe4d86f674717bf66afdc6eef8fdacf39e6a6586f5848ab5b1201d7f51"),
    ("205351RZ1A00321A11Z10000005", 5, "205351RZ1A00321A11Z10000005-A.pdf", 9, "pypdf", "f8af7b7b302fda0bc273d745e9a0bf5bc053fd4cc652d51bbd869b0c3ed56911", "ff7a2db79fc9b85a9f6719967c15cf14fe292a9bf06a67122d4f537c55a6b710"),
    ("205351RZ1A00321A11Z10000006", 6, "205351RZ1A00321A11Z10000006-A.pdf", 10, "pypdf", "775dff9c78527ceeddb3082dbd3c0ea866becdb683a163eb2247188d2a889d2e", "9043ea6240f6ad8c0366d8a7e8add144d97398300dbe0e8a91eec02282450084"),
    ("205351RZ1A00321A11Z10000007", 7, "205351RZ1A00321A11Z10000007-A.pdf", 10, "pypdf", "40784478d756da0a79029543312910d1728a08baf587e56ef452a1bce9a473ca", "6614668be94ddf8968025eef58f7916e5a02b65ea6e7ada7dcecdc60c922f459"),
    ("205351RZ1A00321A11Z10000008", 8, "205351RZ1A00321A11Z10000008-A.pdf", 10, "pypdf", "45b6b8bc1d9427c40a2e7fe21db2055fc9429ae3a9ca9c44c1d8641924c129d0", "e8a89096410e2aa63fbcd590e34bd9c32e2e96811238ec7344ce0ffad9dcc794"),
    ("205351RZ1A00321A11Z10000009", 9, "205351RZ1A00321A11Z10000009-A.pdf", 9, "pypdf", "a26e67814dacb1a2dcba33f64acee932873912dfb786112fc8cb3fcd6af3ad33", "e6d187177c1942a85826827a627e38bd88c53cd44f837e65e656df5c0bc1c49c"),
    ("205351RZ1A00321A11Z10000010", 10, "205351RZ1A00321A11Z10000010-A.pdf", 9, "pymupdf", "8e3d29ae82cfcb2fc1a4a6f76d669d26d338a948e13334a748411ee26e29b05e", "e4e7fae5963c14836eeba6cde6ba39f0dd2e6e4766cc0e732be174bb38fe0c73"),
    ("205351RZ1A00321A11Z10000011", 11, "205351RZ1A00321A11Z10000011-A.pdf", 9, "pypdf", "db5fce892fe02c54284c8aa09e8893dfe3a5492d53ce311b84b2000d8d4bcea7", "6c4db1cbfb25f7bfb5e8783e67496a0a78b3aa6c0c67c479d97d44368052446f"),
    ("205351RZ1A00321A11Z10000012", 12, "205351RZ1A00321A11Z10000012-A.pdf", 9, "pypdf", "46589bb3a558ca71394d61535c383f59d2ef3acc45b8544557dee7328a069ecc", "c72568cec501195466788f24c4a94ce199596425192dc362e636c14670ab50f4"),
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

CLAIM_STATUS_STATE_KEY = "china_account_specific_illness_claim_status"
BENEFIT_GROUP_ID = "china-one-year-specified-disease-account-single-benefit"
PRIMARY_ENTRY_ID = "specified-disease-account-benefit"


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
        and str(document.get("batch_id") or "") == "tii-life-026"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "original-eighteen-specified-diseases"
    if revision <= 3:
        return "legacy-definition-administrative-revisions"
    if revision <= 7:
        return "beneficiary-id-and-administrative-revisions"
    if revision <= 10:
        return "disability-wording-revision"
    return "medical-opinion-review-revision"


def eligibility_fields() -> dict[str, Any]:
    return {
        "exclusion_state_key": CLAIM_STATUS_STATE_KEY,
        "exclusion_values": ["already_paid"],
    }


def coverage_entries() -> list[dict[str, Any]]:
    return [
        {
            "id": PRIMARY_ENTRY_ID,
            "name": "特定傷病保險金",
            "amount": None,
            "basis": "face_amount",
            "source": "terms",
            "note": "首次符合該版本十八項特定傷病之一時，按保單所載保險金額給付一次；給付後附約終止。",
            "source_ref": "保單條款第十三條",
            "calculation_basis": "percentage_of_base",
            "amount_role": "payout",
            "rate_percent": 100,
            "unit_key": "face_amount",
            "limit_scope": "per_policy",
            "aggregation_rule": "choose_one",
            "benefit_group_id": BENEFIT_GROUP_ID,
            "event_key": "specified_disease",
            "event_label": "特定傷病事故",
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            "conditions": [
                "癌症須自生效日起第九十一日後首次符合定義；其他疾病須自生效日起第三十一日後首次符合定義。",
                "傷害事故所致特定傷病不受三十日等待期間限制；續保不受原三十日及九十日等待期間限制。",
                "須在附約有效期間內第一次符合該版本完整的十八項特定傷病定義。",
            ],
            **eligibility_fields(),
        },
        {
            "id": "unexpired-insurance-cost-refund",
            "name": "按日數比例計算的未到期保險成本返還",
            "amount": None,
            "basis": "policy_recorded_limit",
            "source": "terms",
            "note": "事故日按日數比例退還的未到期保險成本併入特定傷病保險金；條款未提供可自行重現的日數與進位公式。",
            "source_ref": "保單條款第十三條",
            "calculation_basis": "policy_state_amount",
            "amount_role": "payout",
            "unit_key": "unexpired_premium_refund_amount",
            "policy_state_keys": ["unexpired_premium_refund_amount"],
            "limit_scope": "per_event",
            "aggregation_rule": "conditional_additive",
            "benefit_group_id": BENEFIT_GROUP_ID,
            "applies_to_entry_ids": [PRIMARY_ENTRY_ID],
            "result_kind": "cash_payout",
            "amount_stage": "insurer_quoted_amount",
            "conditions": [
                "僅隨實際符合的特定傷病事故加計一次，不是獨立保險金。",
                "請輸入保險公司依事故日列示的返還金額；若確認為零則輸入 0。",
            ],
            **eligibility_fields(),
        },
    ]


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
    dense = re.sub(r"\s+", "", text)
    required_signals = (
        "中國人壽一年定期特定傷病帳戶型保險附約",
        "本附約僅附加於投資型保險主契約",
        "特定傷病保險金的給付",
        "本公司按其保險金額給付",
        "本附約效力即行終止",
        "按日數比例退還未到期之保險成本",
        "十八、慢性肺部疾病",
        "第九十一日",
        "第三十一日",
    )
    if any(compact_text(signal) not in dense for signal in required_signals):
        return None

    revision = int(version["revision"])
    return {
        "selection_type": "face_amount",
        "input_mode": "face_amount",
        "selection_source": "terms",
        "selection_label": "保險金額",
        "face_amount_label": "保單所載保險金額",
        "selection_guidance": "請輸入保單首頁、保險證或最近契約變更通知所載的保險金額，再確認是附約有效期間內首次符合該版本特定傷病定義，並填入保險公司列示的未到期保險成本返還額。",
        "version_characteristics": {
            "source_batch_id": "tii-life-026",
            "source_product_id": product_id,
            "family_fingerprint": FAMILY_FINGERPRINT,
            "product_family": "china-one-year-specified-disease-account-rider",
            "company_group": "kgi_china_life",
            "terms_revision": "initial" if revision == 0 else f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "insurance_amount_basis": "policy_recorded_face_amount",
            "benefit_formula": "face_amount_plus_insurer_quoted_prorated_unexpired_insurance_cost",
            "required_policy_inputs": [
                CLAIM_STATUS_STATE_KEY,
            ],
            "specified_disease_item_count": 18,
            "cancer_waiting_days": 90,
            "other_disease_waiting_days": 30,
            "accidental_injury_waiting_exception": True,
            "renewal_waiting_period_exempt": True,
            "maximum_claim_count": 1,
            "contract_terminates_after_benefit": True,
            "beneficiary_identity_document_required": revision >= 4,
            "legacy_disability_wording_present": revision <= 7,
            "medical_opinion_review_available": revision >= 11,
            "insurance_cost_deducted_from_main_policy_account": True,
            "policy_account_value_is_benefit_basis": False,
            "unexpired_insurance_cost_requires_policy_state": True,
            "unexpired_insurance_cost_proration_rule_available": False,
            "premium_waiver_available": False,
            "death_benefit_available": False,
            "disability_benefit_available": False,
            "surrender_value_available": False,
            "amount_presentation": "face_amount_plus_insurer_quoted_unexpired_insurance_cost",
        },
        "coverage_entries": coverage_entries(),
    }
