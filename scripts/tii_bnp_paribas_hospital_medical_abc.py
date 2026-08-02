from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any


FAMILY_FINGERPRINT = "7c9f9176d76a895d42cd96a7"
SOURCE_ROWS = (
    ("267391M11A00200", 0, "267391M11A00200-A.pdf", 8, "pypdf", "fcd2cc1321a1c65f528c1726537f68555883c1d9afd8dc5239b5d2664624e179", "bfec7e1075d503781361714dcaf8ff9cc30338881921bf2d554d5102ceb48cb5"),
    ("267391M11A00201", 1, "267391M11A00201-A.pdf", 8, "pypdf", "6214a70d51f7d6a7e31779de67b2cff63b95e29eb7c8690815d2f957e9247610", "65319771601b1a2a1e08116165dffa9f9b7f3d0feb6fc5e066d1015a74ef92ab"),
    ("267391M11A00202", 2, "267391M11A00202-A.pdf", 11, "pypdf", "a9023394868670f75bf0bedfbd25ca88c046c3d541aaf32f98a484af1aebd66a", "ce37df57fc434c00df36a61d53ac9532f3eed92da731c025dc96e375c5a31984"),
    ("267391M11A00203", 3, "267391M11A00203-A.pdf", 11, "pypdf", "4b0a9f425581e84b6ce71543c2fa69ff4b44526e1739edffc313b53aa877cd5a", "3e75ee4083f2f98d4119264fa551997c93edb3e8d288056d2b8ffe98416479a5"),
    ("267391M11A00204", 4, "267391M11A00204-A.pdf", 11, "pypdf", "010827f019a5e3d76c9ec76e67bc3ad66c7bc00830a3896e787f13198e4d565c", "c5daaf0f474684d2b2a7d13502b8927e7e604d6abc5589c54c7ff09ca99f43c1"),
    ("267391M11A00205", 5, "267391M11A00205-A.pdf", 4, "pypdf", "c27a936613a7b41316b8992b80a21abbface23346f8f0f9a97df5e0741f5cbab", "99ef71c2d15a2d100c3be81fa8240a19e65dce99f26a64f35c5d772048cce2c3"),
    ("267391M11A00206", 6, "267391M11A00206-A.pdf", 4, "pypdf", "ee65ac7e76a74345b9c117bfb47f3d7eb97e730be7d1ca81bfe6fb259d296607", "ba706d3ea99a93d1f3d1647460e0a0abe0699b95f11f0fc9e6e3efb69b673408"),
    ("267391M11A00207", 7, "267391M11A00207-A.pdf", 4, "pypdf", "848091119658dcaff39b78555a9e15665d873373f9cc63ec33eb812456341e28", "390a42c8c3bee0755fd645864daaeff541c8b414bb4802d6782419728e25396e"),
    ("267391MZ1A00221A11Z10000008", 8, "267391MZ1A00221A11Z10000008-A.pdf", 4, "pypdf", "7a01ca58eadb928ee424d27aedb5f3a15f10a420cbd36924003aa40467a0f803", "b96da0d992be9588be0e94abca5d35d8ab01a447613f05c7a4c4254291c106bf"),
    ("267391MZ1A00221A11Z10000009", 9, "267391MZ1A00221A11Z10000009-A.pdf", 4, "pypdf", "d8a91e909840a18608c53d51fbdce4b5c204ff25710ff3066ddeaccb32ff7a63", "55cc0bd984043647bf3cfe81c462681c23c837f16d1b8c50ad803c5ae9fdc4b9"),
    ("267391MZ1A00221A11Z10000010", 10, "267391MZ1A00221A11Z10000010-A.pdf", 4, "pypdf", "21971c4519f8072fe94f06ae3b6e75f3e06dbd032e56eb495bdf365a8692a690", "36d55127f43cf4001f8426e7e717e1f42fd58481275688973e0a87c737e5a40c"),
    ("267391MZ1A00221A11Z10000011", 11, "267391MZ1A00221A11Z10000011-A.pdf", 4, "pypdf", "89f4c15632a59fc493f1fffc201a86de24e43cfb90f16fb36ac8ddd8d71337f9", "2fd5885687217c8a16746cd2b1403b561bcbf9dd23bb9f5ec34c484811e690fc"),
    ("267391MZ1A00221A11Z10000012", 12, "267391MZ1A00221A11Z10000012-A.pdf", 4, "pypdf", "3b83f41982051e78008c32fb0fd29bde07c4d82858cdc12b8e4254fbaf319948", "60420b752c0c3906c7e44fc69a825daa68d25277a51175975072829d38a7f91e"),
    ("267391MZ1A00221A11Z10000013", 13, "267391MZ1A00221A11Z10000013-A.pdf", 4, "pypdf", "05f7a11ed52e949650c0c62d912118e2a8433e45e5abb0461dbb4c03cb112193", "c2a330672155a8531c40f47d5ace400429e8d5679f58609db8760a6e5ee0bc17"),
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


def normalize_terms_text(text: str) -> str:
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
        and str(document.get("batch_id") or "") == "tii-life-170"
        and document.get("document_type") == "policy_terms"
        and str(document.get("file_name") or "").lower()
        == str(version["file_name"]).lower()
    )


def semantic_phase(revision: int) -> str:
    if revision <= 4:
        return "legacy_definitions"
    if revision == 5:
        return "newborn_screening_waiting_exception"
    if revision == 6:
        return "post_expiry_readmission_exclusion"
    if revision <= 9:
        return "day_hospital_legal_references"
    if revision == 10:
        return "cancer_definition_includes_in_situ"
    if revision <= 12:
        return "central_health_authority_wording"
    return "updated_day_hospital_and_preacceptance_liability"


def _entry(
    entry_id: str,
    name: str,
    note: str,
    source_ref: str,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "name": name,
        "basis": "hospital_daily_amount",
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
        "calculation_basis": "table_multiplier",
        "amount_role": "payout",
        "limit_scope": "per_hospitalization",
        "aggregation_rule": "separate",
        "unit_key": "hospital_daily_amount",
        "result_kind": "cash_payout",
        "amount_stage": "gross_contract_benefit",
        **fields,
    }


def plan_entries(coverage_type: str, benefit_article: int) -> list[dict[str, Any]]:
    if coverage_type not in {"A", "B", "C"}:
        raise ValueError(f"unsupported coverage type: {coverage_type}")
    source_prefix = f"第{benefit_article}條{coverage_type}型"
    group_id = f"bnp-hospital-abc-{coverage_type.lower()}-daily-additions"
    entries = [
        _entry(
            "general-hospital-daily-benefit",
            "一般住院醫療日額保險金",
            "住院醫療保險金日額乘實際住院日數；同一次住院最高三百六十五日。",
            f"{source_prefix}第一款",
            multiplier=1,
            quantity_state_key="hospitalization_days",
            quantity_cap=365,
        ),
        _entry(
            "cancer-hospital-daily-additional-benefit",
            "癌症住院醫療日額保險金",
            "符合本版癌症定義時，除一般住院日額外，另按日額一倍乘癌症住院日數；同一次住院最高三百六十五日。",
            f"{source_prefix}第二款",
            aggregation_rule="conditional_additive",
            benefit_group_id=group_id,
            multiplier=1,
            quantity_state_key="cancer_hospitalization_days",
            quantity_cap=365,
        ),
    ]
    if coverage_type in {"B", "C"}:
        entries.extend([
            _entry(
                "intensive-care-daily-additional-benefit",
                "加護病房日額保險金",
                "除一般住院或癌症住院日額外，另按日額一倍乘實際加護病房日數；同一次住院最高三百六十五日。",
                f"{source_prefix}第三款",
                aggregation_rule="conditional_additive",
                benefit_group_id=group_id,
                multiplier=1,
                quantity_state_key="intensive_care_days",
                quantity_cap=365,
            ),
            _entry(
                "burn-intensive-care-daily-additional-benefit",
                "燒燙傷加護病房日額保險金",
                "除一般住院日額外，另按日額兩倍乘實際燒燙傷加護病房日數；同一次住院最高三百六十五日。",
                f"{source_prefix}第四款",
                aggregation_rule="conditional_additive",
                benefit_group_id=group_id,
                multiplier=2,
                quantity_state_key="burn_unit_days",
                quantity_cap=365,
            ),
        ])
    if coverage_type == "C":
        entries.extend([
            _entry(
                "inpatient-surgery-medical-benefit",
                "住院手術醫療保險金",
                "住院期間接受手術且醫療費用收據列有手術費時，按日額三倍給付；同一次住院以一次為限。",
                f"{source_prefix}第五款",
                multiplier=3,
            ),
            _entry(
                "inpatient-treatment-procedure-medical-benefit",
                "住院治療處置醫療保險金",
                "住院期間接受治療處置且醫療費用收據列有治療處置費時，按日額三倍給付；同一次住院以一次為限。",
                f"{source_prefix}第六款",
                multiplier=3,
            ),
            _entry(
                "post-discharge-convalescence-benefit",
                "出院療養保險金",
                "按住院醫療保險金日額百分之五十乘實際住院日數；同一次住院最高三百六十五日。",
                f"{source_prefix}第七款",
                aggregation_rule="conditional_additive",
                multiplier=1,
                rate_percent=50,
                quantity_state_key="hospitalization_days",
                quantity_cap=365,
            ),
            _entry(
                "pre-post-hospital-outpatient-benefit",
                "住院前後門診醫療保險金",
                "住院前一週及出院後一週內，同一事故門診按日額百分之二十五乘實際門診日數；住院曾接受手術或治療處置時，出院後延長為兩週。",
                f"{source_prefix}第八款",
                multiplier=1,
                rate_percent=25,
                quantity_state_key="outpatient_visit_count",
                quantity_cap=21,
                conditions=[
                    "同一日門診一次或多次均以一日計。",
                    "未接受手術或治療處置時，住院前後各一週；接受手術或治療處置時，出院後延長為兩週。",
                ],
            ),
        ])
    return entries


def expected_entry_contracts(
    coverage_type: str,
    benefit_article: int,
) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref"}
    return {
        entry["id"]: {
            key: value
            for key, value in entry.items()
            if key not in ignored and key != "id"
        }
        for entry in plan_entries(coverage_type, benefit_article)
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
    text = normalize_terms_text(str(document.get("text") or ""))
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != version["source_text_sha256"]:
        return None
    dense_text = re.sub(r"\s+", "", text)
    revision = int(version["revision"])
    benefit_article = 5 if revision == 13 else 4
    article_start = dense_text.find(
        f"第{'五' if benefit_article == 5 else '四'}條",
        1000,
    )
    type_a_start = dense_text.find("甲型:", article_start)
    type_b_start = dense_text.find("乙型:", type_a_start + 3)
    type_c_start = dense_text.find("丙型:", type_b_start + 3)
    next_article = dense_text.find(
        f"第{'六' if benefit_article == 5 else '五'}條",
        type_c_start + 3,
    )
    if (
        article_start < 0
        or not (article_start < type_a_start < type_b_start < type_c_start < next_article)
        or "本公司依被保險人購買本契約選定之類型"
        not in dense_text[article_start:type_a_start]
    ):
        return None
    sections = {
        "A": dense_text[type_a_start:type_b_start],
        "B": dense_text[type_b_start:type_c_start],
        "C": dense_text[type_c_start:next_article],
    }
    benefit_names = (
        "一般住院醫療日額保險金",
        "癌症住院醫療日額保險金",
        "加護病房日額保險金",
        "燒燙傷加護病房日額保險金",
        "住院手術醫療保險金",
        "住院治療處置醫療保險金",
        "出院療養保險金",
        "住院前後門診醫療保險金",
    )
    expected_by_type = {
        "A": benefit_names[:2],
        "B": benefit_names[:4],
        "C": benefit_names,
    }
    expected_365_counts = {"A": 2, "B": 4, "C": 5}
    for coverage_type, section in sections.items():
        expected = expected_by_type[coverage_type]
        forbidden = set(benefit_names) - set(expected)
        if (
            any(name not in section for name in expected)
            or any(name in section for name in forbidden)
            or section.count("三百六十五日") != expected_365_counts[coverage_type]
            or "九十日" in section
        ):
            return None
    type_c = sections["C"]
    if (
        type_c.count("三倍") < 2
        or "百分之五十" not in type_c
        or "百分之二十五" not in type_c
        or "前一週" not in type_c
        or "延長為兩週" not in type_c
    ):
        return None
    phase_signals = (
        ("新生兒先天性代謝異常疾病篩檢項目", revision >= 5),
        ("有效期間屆滿後出院", revision >= 6),
        ("日間住院", revision >= 7),
        ("惡性腫瘤或原位癌", revision >= 10),
        ("中央衛生主管機關", revision >= 11),
        ("日間留院/日間照護", revision == 13),
        ("預收相當於第一期保險費", revision == 13),
    )
    if any(
        (signal in dense_text) is not expected
        for signal, expected in phase_signals
    ):
        return None
    if revision == 13:
        if "第五十一條" in dense_text or "第三十五條" in dense_text:
            return None
    elif revision >= 7 and (
        "第五十一條" not in dense_text or "第三十五條" not in dense_text
    ):
        return None

    required_by_plan = {
        "A": [
            "hospital_daily_amount",
            "hospitalization_days",
            "cancer_hospitalization_days",
        ],
        "B": [
            "hospital_daily_amount",
            "hospitalization_days",
            "cancer_hospitalization_days",
            "intensive_care_days",
            "burn_unit_days",
        ],
        "C": [
            "hospital_daily_amount",
            "hospitalization_days",
            "cancer_hospitalization_days",
            "intensive_care_days",
            "burn_unit_days",
            "outpatient_visit_count",
        ],
    }
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障型別與住院醫療保險金日額",
        "selection_guidance": (
            "請先依保單選擇甲型、乙型或丙型，再輸入保單記載的住院醫療保險金日額；"
            "系統會依所選型別顯示條款給付，事故日數只填實際符合條款的日數。"
        ),
        "version_characteristics": {
            "source_product_id": product_id,
            "product_family": "bnp-paribas-hospital-medical-abc",
            "family_fingerprint": FAMILY_FINGERPRINT,
            "company_group": "bnp_paribas_cardif_life",
            "source_batch_id": "tii-life-170",
            "terms_revision": (
                "original" if revision == 0 else f"partial_change_{revision}"
            ),
            "semantic_phase": semantic_phase(revision),
            "source_document_sha256": version["source_document_sha256"],
            "source_text_sha256": version["source_text_sha256"],
            "source_text_extractor": version["source_text_extractor"],
            "source_text_quality": "machine_readable_exact_hash",
            "source_page_count": version["page_count"],
            "standalone_policy": True,
            "policy_period_years": 1,
            "guaranteed_renewal": True,
            "coverage_type_options": ["A", "B", "C"],
            "daily_amount_source": "policy_or_latest_endorsement",
            "benefit_article": benefit_article,
            "disease_waiting_days": 30,
            "renewal_waiting_period_carryover": True,
            "newborn_screening_waiting_exception": revision >= 5,
            "same_hospital_readmission_days": 14,
            "post_expiry_readmission_excluded": revision >= 6,
            "day_hospital_excluded": revision >= 7,
            "day_hospital_legal_reference_revision": (
                "current_statutes_with_day_care"
                if revision == 13
                else "nhi_article_51_and_mental_health_article_35"
                if revision >= 7
                else "not_explicit"
            ),
            "cancer_waiting_days": 30,
            "cancer_definition_revision": (
                "malignant_tumor_or_in_situ"
                if revision >= 10
                else "legacy_malignant_tumor"
            ),
            "health_authority_wording": (
                "central_health_authority"
                if revision >= 11
                else "executive_yuan_department_of_health"
            ),
            "hospitalization_day_limit_per_benefit": 365,
            "general_hospital_daily_multiplier": 1,
            "cancer_hospital_daily_additional_multiplier": 1,
            "intensive_care_daily_additional_multiplier": 1,
            "burn_intensive_care_daily_additional_multiplier": 2,
            "inpatient_surgery_multiplier": 3,
            "inpatient_treatment_procedure_multiplier": 3,
            "post_discharge_convalescence_rate_percent": 50,
            "outpatient_rate_percent": 25,
            "outpatient_pre_days": 7,
            "outpatient_post_days": 7,
            "outpatient_post_procedure_days": 14,
            "reimbursement_benefit": False,
            "death_unexpired_premium_refund": True,
            "preacceptance_liability_rule_added": revision == 13,
            "required_policy_inputs": ["hospital_daily_amount"],
            "required_policy_inputs_by_plan": required_by_plan,
            "claim_event_inputs_by_plan": {
                plan: fields[1:]
                for plan, fields in required_by_plan.items()
            },
            "amount_presentation": (
                "selected_type_and_policy_daily_amount_with_claim_event_quantities"
            ),
        },
        "plan_options": [
            {
                "value": coverage_type,
                "label": f"{coverage_type}型",
                "coverage_entries": plan_entries(
                    coverage_type,
                    benefit_article,
                ),
            }
            for coverage_type in ("A", "B", "C")
        ],
    }
