from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "ea0bed7dfec6b2c312a31e15"
SOURCE_ROWS = (
    ("202321M11A68000", 0, "202321M11A68000-A.pdf", 5, "pymupdf", "b70d122e20ceb09c6262e81a270ad71be15f9b8bd1cb59b8f1dc5f28aa4ff303", "0339e5b2a77cc262f1fe71950683de903ebc92f477fc48c057b05a48ca790589"),
    ("202321M11A68001", 1, "202321M11A68001-A.pdf", 5, "pymupdf", "3ad085326861585077f03fcfe1d72646eafe2592665492c3c6e2e87d7ebf6d39", "788a824ad0010168887cbba401bdfbc231ae5c6fd53c4fd3bc1d73f4675c9b70"),
    ("202321M11A68002", 2, "202321M11A68002-A.pdf", 5, "pymupdf", "575a9419817e1cfb63cda3ad9d415a16daddd0ea98a57f9fb1bfd20af99d9518", "b74df5200778064fd2e121111c090e1de727a79fd6591dd0746ee67a95ebeae5"),
    ("202321M11A68003", 3, "202321M11A68003-A.pdf", 6, "pypdf", "608037134403894490e58944bc2800359089c04e24ba09b70ba30d44343d02b6", "8fe373610dbcdf21430aa07dee14c4b5b0d2e607bdfef80a780a89226aab4b94"),
    ("202321M11A68004", 4, "202321M11A68004-A.pdf", 6, "pypdf", "6728a29c61a76311466e9b55e420ace44ee69a72ed8785f62c579deba3dba4f0", "f044efe7037434bcc9a8d03c6f304c830ffb918bc9ee82b8f2bf5336f700064e"),
    ("202321M11A68005", 5, "202321M11A68005-A.pdf", 6, "pypdf", "01a374ef85699ce229874dc62d3007c272711b09f4bee4609f4b657f0fc0c7fa", "b820616b4e1427737f55c02aa6495bbfbbdd5971d36ccef7597a6f899356516c"),
    ("202321MZ1A68021A11Z10000006", 6, "202321MZ1A68021A11Z10000006-A.pdf", 6, "pypdf", "f776828526186885c3055ea58d8cee5858375bdcb25cab5d344285c35ccc16b9", "d1f4cc81a342efae53e21d340d71326e759b720311e1831fa55c12777af3c801"),
    ("202321MZ1A68021A11Z10000007", 7, "202321MZ1A68021A11Z10000007-A.pdf", 6, "pypdf", "2a1466156aa53da0af4d2bde160690aca67455d14760e41b07444ec0fbc9f024", "1ffd5a38c27ff912779bcda0912726187bbe594ee08afa34c8d5ee85db424a2e"),
    ("202321MZ1A68021A11Z10000008", 8, "202321MZ1A68021A11Z10000008-A.pdf", 6, "pypdf", "35d6271ac72d3723dbdcd81c2d18e348dfdbfa64f4e0ef2f3d2d416e5f312e0d", "1b66e189f82772fad11b0f8bedbe2938a0c2108e8c6284048ed1900e5d403862"),
    ("202321MZ1A68021A11Z10000009", 9, "202321MZ1A68021A11Z10000009-A.pdf", 6, "pypdf", "42a1f88284b73eb9c59d948758262ce82f2f8c245a82c0ccdaa5ca4a362bc86b", "e0894a6971476fabf7b9a28d51e2724ea666ca071c7602e74773a7b767c038a6"),
    ("202321MZ1A68021A11Z10000010", 10, "202321MZ1A68021A11Z10000010-A.pdf", 3, "pypdf", "a4cd47ee1112b62c1749f8b4494b1e8aa0a56a983b56eacdb310d1e2ab855b02", "b687e6874558a5e3ad3c8218b46612f5b229ba06b8804aa6de45c0245abe42ba"),
    ("202321MZ1A68021A11Z10000011", 11, "202321MZ1A68021A11Z10000011-A.pdf", 3, "pypdf", "3300d0bff53145b423283abc25d7afbd786af213486d669d78f1925fed6016c2", "6b84f709442c57384d861a46c509fa2628020fe7891a8ef429a46357be703eaf"),
    ("202321MZ1A68021A11Z10000012", 12, "202321MZ1A68021A11Z10000012-A.pdf", 3, "pypdf", "29dadfcb28b0ce82c9f18fab08d67c2032593fb88bcf13a0c25170f9004068d6", "b6d3c4a7010ea93bd48363bde16e4a16a19920213818f1eac1df8b0b62dc0fb5"),
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
        return "legacy-reinstatement-ten-day-original-termination"
    if revision <= 2:
        return "reinstatement-ten-day-waiting"
    if revision == 3:
        return "post-expiry-readmission-exclusion"
    if revision <= 6:
        return "medical-corporation-and-claim-document-update"
    if revision == 7:
        return "post-expiry-readmission-restored"
    if revision == 8:
        return "inception-waiting-only"
    if revision == 9:
        return "inclusive-disability-wording-update"
    if revision == 10:
        return "modern-cancer-definition"
    return "modern-cancer-definition-medical-review"


EVENT_STATE_KEY = "taiwan_cancer_insurance_event_status"
EVENT_VALUES = {
    "eligible_cancer_hospitalization",
    "eligible_posthumous_cancer_diagnosis",
    "diagnosed_within_initial_waiting_period",
    "precontract_unaware_cancer_premium_refund",
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
        "生效日起九十日或復效日含當日起十日等待期間外首次罹患癌症"
        if revision <= 7
        else "生效日起九十日等待期間外首次罹患癌症"
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
            1_600,
            "daily_per_unit",
            "每單位每日新臺幣 1,600 元；條款明定住院日數不受限制，直至保險單失效。",
            "第八條 癌症住院醫療保險金",
            calculation_basis="per_unit_per_day",
            limit_scope="per_day",
            quantity_state_key="cancer_hospitalization_days",
            exclusion_values=event_exclusions(
                "eligible_cancer_hospitalization"
            ),
            conditions=[waiting_condition, "住院係為治療條款所定義的癌症"],
            **common,
        ),
        entry(
            "posthumous-cancer-diagnosis-daily",
            "身故後診斷癌症住院醫療保險金",
            1_600,
            "daily_per_unit",
            "身故後經解剖檢驗證明罹癌，按住院日額追溯最近一次入院日至身故日，最多四十五日。",
            "第十條 身故後診斷",
            calculation_basis="per_unit_per_day",
            limit_scope="per_event",
            quantity_state_key="cancer_hospitalization_days",
            quantity_cap=45,
            exclusion_values=event_exclusions(
                "eligible_posthumous_cancer_diagnosis"
            ),
            conditions=["身故後經解剖檢驗證明患有癌症"],
            **common,
        ),
        entry(
            "waiting-period-premium-refund",
            "等待期間內確診退還已收保險費",
            None,
            "policy_recorded_limit",
            "生效日後九十日以內確診時，無息返還已收保險費並終止或解除契約；金額須依繳費紀錄或保險公司核算。",
            "第二條 保險範圍",
            calculation_basis="policy_state_amount",
            limit_scope="per_policy",
            unit_key="taiwan_cancer_waiting_refund_amount",
            policy_state_keys=["taiwan_cancer_waiting_refund_amount"],
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
            "precontract-unaware-cancer-premium-refund",
            "投保前未知癌症退還已收保險費",
            None,
            "policy_recorded_limit",
            "投保前已曾診斷癌症，但醫師未告知且要保人或被保險人不知情時，無息返還已收保險費並解除契約。",
            "第十一條 告知義務與本契約的解除",
            calculation_basis="policy_state_amount",
            limit_scope="per_policy",
            unit_key="taiwan_cancer_precontract_refund_amount",
            policy_state_keys=[
                "taiwan_cancer_precontract_refund_amount"
            ],
            exclusion_values=event_exclusions(
                "precontract_unaware_cancer_premium_refund"
            ),
            amount_stage="insurer_quoted_amount",
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
        "台灣人壽防癌保險保險單條款",
        "癌症住院醫療保險金",
        "每天給付保險金每單位新臺幣壹仟陸佰元正",
        "其住院日數不受限制",
        "給付責任追溯自最後一次入院之日起",
        "但以不超過四十五天為限",
        "無息返還已收的保險費",
        "本契約保險金的給付,限於被保險人治療癌症",
        "醫師未予告知",
    )
    if any(signal not in dense for signal in required_signals):
        return None

    revision = int(version["revision"])
    phase_checks = (
        (
            "生效日九十天以內或復效日(含)起十天以內" in dense,
            revision <= 7,
        ),
        (
            "再次住院部分不予給付保險金" in dense,
            revision == 3 or revision >= 7,
        ),
        (
            bool(re.search(r"公、私立及醫(?:\d+-\d+)?療法人醫院", dense)),
            revision >= 4,
        ),
        ("五、受益人的身分證明" in dense, revision >= 4),
        ("身體機能障礙" in dense, revision >= 9),
        ("原位癌之疾病" in dense, revision >= 10),
        ("徵詢其他醫師之醫學專業意見" in dense, revision >= 11),
        (
            "並解除本契約。【癌症的定義】" in dense,
            revision == 0,
        ),
        (
            "本契約效力即行終止" in dense,
            revision >= 1,
        ),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None

    claim_inputs_by_event = {
        "eligible_cancer_hospitalization": [
            EVENT_STATE_KEY,
            "cancer_hospitalization_days",
        ],
        "eligible_posthumous_cancer_diagnosis": [
            EVENT_STATE_KEY,
            "cancer_hospitalization_days",
        ],
        "diagnosed_within_initial_waiting_period": [
            EVENT_STATE_KEY,
            "taiwan_cancer_waiting_refund_amount",
        ],
        "precontract_unaware_cancer_premium_refund": [
            EVENT_STATE_KEY,
            "taiwan_cancer_precontract_refund_amount",
        ],
        "not_eligible_or_uncertain": [EVENT_STATE_KEY],
    }
    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "selection_label": "投保單位數",
        "selection_guidance": (
            "請依保單面頁、保險證或批註輸入正整數單位；條款沒有明列最高單位數，因此不在此自行設定上限。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "taiwan-cancer-insurance",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "company_group": "taiwan_life",
            "source_batch_id": "tii-life-008",
            "terms_revision": f"partial_change_{revision}",
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version[
                "source_document_sha256"
            ],
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
            "maximum_units_stated_in_terms": False,
            "cancer_initial_waiting_days": 90,
            "cancer_reinstatement_waiting_days": (
                10 if revision <= 7 else 0
            ),
            "post_expiry_readmission_excluded": (
                revision == 3 or revision >= 7
            ),
            "medical_corporation_hospital_wording": revision >= 4,
            "claimant_identity_document_required": revision >= 4,
            "inclusive_disability_wording": revision >= 9,
            "modern_cancer_definition": revision >= 10,
            "medical_review_wording": revision >= 11,
            "hospital_daily_amount_per_unit": 1_600,
            "hospital_daily_day_limit": None,
            "posthumous_diagnosis_day_limit": 45,
            "waiting_period_premium_refund_available": True,
            "precontract_unaware_cancer_refund_available": True,
            "cancer_death_lump_sum_available": False,
            "home_recovery_benefit_available": False,
            "required_policy_inputs": ["unit_count"],
            "claim_event_inputs_by_event": claim_inputs_by_event,
            "amount_presentation": (
                "unit_count_with_cancer_event_and_policy_state"
            ),
        },
        "coverage_entries": coverage_entries(revision),
    }
