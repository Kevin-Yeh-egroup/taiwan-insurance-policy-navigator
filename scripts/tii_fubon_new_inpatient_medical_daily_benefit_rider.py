from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "6c8e64b63d75f0f2000a8023"
SOURCE_ROWS = (
    ("209311R11A00100", 0, "209311R11A001-A.pdf", 3, "pypdf", "6af8b16a2924ec57d1c8ec74c73845830a4def1f4560e0e926aa69208a02f73f", "0b4b87f2945cac85c2e0d44c112e8ec69e01e37d1b07b89721fb1d48a882c6e6"),
    ("209311R11A00101", 1, "209311R11A00101-A.pdf", 4, "pymupdf", "ca628888c286bacbb405bd9fe3260b2721732ac1b23e19a2cf24120de12a02cb", "1206668affa06e54e51790a862baaad180246fea99a7535c88fe4265cf776a13"),
    ("209311R11A00102", 2, "209311R11A00102-A.pdf", 4, "pymupdf", "84077509c1e35dc9fd21e8b3f08488ca000832acbde1b1225ea16bffd74ea9e7", "f5a1aa4e44353abe158d45e4021117b580a5c912f63bd7f5e2569fb477cbc834"),
    ("209311R11A00103", 3, "209311R11A00103-A.pdf", 4, "pymupdf", "d0809406f57417f0e9bc54cd3dfd33e1ab064169d93e94722be046301eedf0a6", "19d5891f2ef6544e75e21b3b27483ccd0eae362b8b43406ba6c88103cddde9da"),
    ("209311R11A00104", 4, "209311R11A00104-A.pdf", 4, "pypdf", "2050ca1f06d1c678704d211dd17fe45ea5c96ccbc53214e54f089f6fed5e19fe", "75ea163ab1ddf86b459ff55d718f746544b20bfb3de23a7e8cc50fd5e633d2a4"),
    ("209311R11A00105", 5, "209311R11A00105-A.pdf", 4, "pypdf", "839279e011cb2e276f51a325b0cd6430d8c7bdf5b268b8c05d27411e83a86053", "552f30b14adf02be6f25b8ca67cc5509739c6cedcf8106d91b0a50900854d0dc"),
    ("209311R11A00106", 6, "209311R11A00106-A.pdf", 4, "pypdf", "839279e011cb2e276f51a325b0cd6430d8c7bdf5b268b8c05d27411e83a86053", "552f30b14adf02be6f25b8ca67cc5509739c6cedcf8106d91b0a50900854d0dc"),
    ("209311R11A00107", 7, "209311R11A00107-A.pdf", 6, "pypdf", "8d8e0b1781210546c12feb0a5263ca402c6e16028813f8a8b4ad9d7de7587e9b", "a14cd8ccf3ee33c4d80a4e451e9ecd43abd4caa21152cedf781cece651864663"),
    ("209311R11A00108", 8, "209311R11A00108-A.pdf", 6, "pypdf", "9010a030294ecc5d1936463d81405d6ec56c72c433a0f13fab6fcb28b1428e83", "a054cf01ce8a19c99f3c5ce291f39f7dc27aaf61f85ad9fe0f9f14ce44991384"),
    ("209311R11A00109", 9, "209311R11A00109-A.pdf", 6, "pypdf", "96848c828978511e32acc0021f7cbd7539ceabf2160b5e45b773b3fa0383654e", "944f9bfe5cec83e8df93543571979288416e2845ae838ff411ef7508b30f637f"),
    ("209311RZ1A00921A11Z10000010", 10, "209311RZ1A00921A11Z10000010-A.pdf", 6, "pypdf", "4453e3385eed372d0b8de236a62505e0d17af81a096570885ab77f60b2f9642c", "f0fcb247c023b037774c60b5c1be074994c7d33c6f5ef14b1a51f5a376198de8"),
    ("209311RZ1A00921A11Z10000011", 11, "209311RZ1A00921A11Z10000011-A.pdf", 6, "pypdf", "6591ceaed01ec712ff13bc538c7764c482ae4cc6c3dc60f6fe119aeb6982ecf8", "bcfe3280892029ce39a9f2d8580f54de3aa4663a0eac56f2f726a1e5bbb44fbe"),
    ("209311RZ1A00921A11Z10000012", 12, "209311RZ1A00921A11Z10000012-A.pdf", 6, "pypdf", "9ecc90d74dba7bfdafb143d06ff8c60347808ba070bb86f8c975ffca617d06d4", "30d7fa75bb025c43696f7a2e014140e8eb09eefa441681ff890214b2a417c074"),
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

EVENT_STATUS_KEY = "fubon_new_inpatient_daily_event_status"

VERSION_FIELDS = {
    "source_product_id",
    "family_fingerprint",
    "product_family",
    "company_group",
    "source_batch_id",
    "terms_revision",
    "semantic_phase",
    "source_document_sha256",
    "source_text_sha256",
    "source_text_extractor",
    "source_text_quality",
    "source_page_count",
    "currency_basis",
    "rider",
    "policy_period_years",
    "daily_amount_source",
    "benefit_article",
    "benefit_entry_count",
    "hospital_daily_formula",
    "eligible_days_include_admission_and_discharge",
    "hospital_day_limit",
    "hospital_day_limit_scope",
    "disease_waiting_days",
    "accident_waiting_period_exempt",
    "newborn_screening_exception",
    "same_hospital_readmission_days",
    "post_expiry_readmission_excluded",
    "day_hospital_excluded",
    "day_hospital_legal_reference_revision",
    "claim_medical_review_clause",
    "independent_surgery_benefit",
    "independent_intensive_care_benefit",
    "reimbursement_benefit",
    "death_benefit_available",
    "premium_waiver_available",
    "required_policy_inputs",
    "claim_event_inputs",
    "amount_presentation",
}


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
        and str(document.get("batch_id") or "") == "tii-life-050"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
        and str(document.get("source_document_sha256") or "")
        == version["source_document_sha256"]
    )


def semantic_phase(revision: int) -> str:
    if revision == 0:
        return "original_legacy_title_90_day_readmission"
    if revision == 1:
        return "first_change_90_day_readmission"
    if revision <= 6:
        return "fourteen_day_readmission_policy_year_cap"
    if revision == 7:
        return "newborn_screening_exception"
    if revision == 8:
        return "post_expiry_readmission_exclusion"
    if revision <= 10:
        return "day_hospital_exclusion"
    return "central_authority_newborn_and_medical_opinion"


def eligibility(revision: int) -> dict[str, Any]:
    ineligible = [
        "disease_waiting_not_met",
        "confirmed_not_eligible",
    ]
    uncertain = ["uncertain"]
    if revision < 7:
        ineligible.append("eligible_newborn_screening_exception")
    if revision >= 9:
        ineligible.append("day_hospital_or_day_stay")
    else:
        uncertain.append("day_hospital_or_day_stay")
    if revision >= 8:
        ineligible.append("post_expiry_readmission")
    else:
        uncertain.append("post_expiry_readmission")
    return {
        "eligibility_state_key": EVENT_STATUS_KEY,
        "ineligible_values": ineligible,
        "uncertain_values": uncertain,
    }


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    return [
        {
            "id": "hospital-daily-tiered-benefit",
            "name": "住院日額保險金",
            "amount": None,
            "basis": "hospital_daily_amount",
            "source": "terms",
            "note": (
                "依保險單所載住院醫療保險金日額與實際住院日數分段計算；"
                "第 1 至 30 日為 1 倍、第 31 至 180 日為 2 倍、第 181 至 365 日為 3 倍。"
            ),
            "source_ref": "住院日額保險金的給付",
            "calculation_basis": "tiered_or_stepped",
            "amount_role": "payout",
            "limit_scope": "per_hospitalization",
            "aggregation_rule": "separate",
            "quantity_state_key": "hospitalization_days",
            "quantity_cap": 365,
            "policy_state_keys": ["hospital_daily_amount", "hospitalization_days"],
            "amount_tiers": [
                {"label": "第 1 至 30 日", "multiplier": 1, "min_quantity": 1, "max_quantity": 30},
                {"label": "第 31 至 180 日", "multiplier": 2, "min_quantity": 31, "max_quantity": 180},
                {"label": "第 181 至 365 日", "multiplier": 3, "min_quantity": 181, "max_quantity": 365},
            ],
            "result_kind": "cash_payout",
            "amount_stage": "gross_contract_benefit",
            **eligibility(revision),
        }
    ]


def expected_entry_contracts(revision: int) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        entry["id"]: {
            key: value
            for key, value in entry.items()
            if key not in ignored and key != "id"
        }
        for entry in coverage_entries(revision)
    }


def expected_identity(product_id: str) -> dict[str, Any]:
    source = VERSIONS[product_id]
    revision = int(source["revision"])
    return {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "fubon-new-inpatient-medical-daily-benefit-rider",
        "company_group": "fubon_life",
        "source_batch_id": "tii-life-050",
        "terms_revision": f"partial_change_{revision}",
        "semantic_phase": semantic_phase(revision),
        "source_document_sha256": source["source_document_sha256"],
        "source_text_sha256": source["source_text_sha256"],
        "source_text_extractor": source["source_text_extractor"],
        "source_text_quality": (
            "machine_readable_exact_hash_pymupdf_recovery"
            if source["source_text_extractor"] == "pymupdf"
            else "machine_readable_exact_hash"
        ),
        "source_page_count": source["page_count"],
        "currency_basis": "twd",
        "rider": True,
        "policy_period_years": 1,
        "daily_amount_source": "policy_recorded_hospital_daily_amount",
        "benefit_article": "住院日額保險金的給付",
        "benefit_entry_count": 1,
        "hospital_daily_formula": "days_1_30_x1_days_31_180_x2_days_181_365_x3",
        "eligible_days_include_admission_and_discharge": True,
        "hospital_day_limit": 365,
        "hospital_day_limit_scope": (
            "per_payment_or_hospitalization"
            if revision <= 1
            else "per_policy_year_per_hospitalization"
        ),
        "disease_waiting_days": 30,
        "accident_waiting_period_exempt": True,
        "newborn_screening_exception": revision >= 7,
        "same_hospital_readmission_days": 90 if revision <= 1 else 14,
        "post_expiry_readmission_excluded": revision >= 8,
        "day_hospital_excluded": revision >= 9,
        "day_hospital_legal_reference_revision": revision >= 9,
        "claim_medical_review_clause": revision >= 11,
        "independent_surgery_benefit": False,
        "independent_intensive_care_benefit": False,
        "reimbursement_benefit": False,
        "death_benefit_available": False,
        "premium_waiver_available": False,
        "required_policy_inputs": ["hospital_daily_amount"],
        "claim_event_inputs": [EVENT_STATUS_KEY, "hospitalization_days"],
        "amount_presentation": "policy_recorded_daily_amount_with_exact_tiered_days",
    }


def parse_policy(document: dict[str, Any]) -> dict[str, Any] | None:
    if not is_strict_source(document):
        return None
    product_id = str(document.get("product_id") or "")
    source = VERSIONS[product_id]
    if (
        document.get("page_count") != source["page_count"]
        or document.get("pages_parsed") != source["page_count"]
        or str(document.get("source_text_extractor") or "")
        != source["source_text_extractor"]
    ):
        return None
    text = normalize_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != source[
        "source_text_sha256"
    ]:
        return None
    dense = compact_text(text)
    common_signals = (
        "新住院醫療日額給付保險附約",
        "住院日額保險金的給付",
        "在三十日之內者",
        "超過三十日至一百八十日者",
        "超過一百八十日者",
        "三百六十五日",
        "含出院及入院當日",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(source["revision"])
    phase_checks = (
        ("再入院日期未超過九十天" in dense, revision <= 1),
        ("出院後十四日內再次住院" in dense, revision >= 2),
        ("同一保單年度同一次住院" in dense, revision >= 2),
        ("新生兒先天性代謝異常疾病" in dense, revision >= 7),
        ("本附約有效期間屆滿後出院者" in dense, revision >= 8),
        ("全民健康保險法第五十一條所稱之日間住院" in dense, revision >= 9),
        ("徵詢其他醫師之醫學專業意見" in dense, revision >= 11),
    )
    if any(actual is not expected for actual, expected in phase_checks):
        return None
    independent_benefit_headings = (
        "住院手術醫療保險金的給付",
        "加護病房保險金的給付",
        "燒燙傷病房保險金的給付",
        "住院醫療費用保險金的給付",
    )
    if any(compact_text(signal) in dense for signal in independent_benefit_headings):
        return None
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "填入住院日額與本次住院狀態",
        "selection_guidance": (
            "請依這個 productId 的保單首頁或最近批註填入住院醫療保險金日額，"
            "再填實際住院日數與事故資格；系統會依本版本條款分段計算。"
        ),
        "plan_options": [],
        "version_characteristics": expected_identity(product_id),
        "coverage_entries": coverage_entries(revision),
    }


def validate_contract(
    record: dict[str, Any],
    version: dict[str, Any],
    context: str,
    *,
    fail: Callable[[str], None],
    validate_entries: Callable[[object, dict[str, dict[str, Any]], str], None],
) -> None:
    product_id = str(version.get("source_product_id") or "")
    source = VERSIONS.get(product_id)
    if source is None:
        fail(f"coverage Fubon new inpatient daily source product is invalid: {context}")
    revision = int(source["revision"])
    if (
        record.get("product_id") not in {None, product_id}
        or record.get("selection_type") != "policy_state"
        or record.get("input_mode") != "policy_state"
        or record.get("selection_source") != "terms"
        or record.get("plan_options") != []
        or any(
            version.get(key) != value
            for key, value in expected_identity(product_id).items()
        )
    ):
        fail(
            f"coverage Fubon new inpatient daily source or version boundary is invalid: {context}"
        )
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(revision),
        f"{context} Fubon new inpatient medical daily benefit rider",
    )
