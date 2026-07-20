from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TAIPEI_TZ = timezone(timedelta(hours=8))
EXTRACTOR_VERSION = "tii-plan-benefits-v30"
PLAN_HEADERS = [
    "意外傷害身故",
    "意外傷害失能",
    "傷害醫療",
    "航空大眾運輸意外",
    "住院醫療",
]
PLAN_ROW_PATTERN = re.compile(
    r"\b([A-D])\s+([\d,]+)\s*萬元\s+([\d,]+)\s*萬元\s+([\d,]+)\s*萬元"
)
AMOUNT_PATTERN = re.compile(r"([\d,]+)\s*(萬元|元)")
REQUIRED_TERM_SIGNALS = [
    "意外傷害身故保險金的給付",
    "再依附表二所列之給付比例計算",
    "同一次傷害的給付總額不得超過",
    "另按附表一約定計畫別之保險金額給付航空大眾運輸意外傷害身故",
    "實際住院日數(含入院及出院當日)",
    "同一保單年度同一次住院最高日數以三百六十五日為限",
]
ARTICLE_HEADINGS = {
    "death": "意外傷害身故保險金的給付",
    "disability": "意外傷害失能保險金的給付",
    "medical": "傷害醫療保險金的給付",
    "aviation": "航空大眾運輸意外傷害身故保險金的給付",
    "hospital": "住院醫療日額保險金的給付",
}


def compact_whitespace(text: str) -> str:
    return " ".join(text.split())


def normalize_terms_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(
        r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])",
        "",
        normalized,
    )
    return compact_whitespace(normalized)


def amount_in_ntd(value: str, unit: str) -> int:
    amount = int(value.replace(",", ""))
    return amount * 10_000 if unit == "萬元" else amount


def integer_from_arabic_or_chinese(value: str) -> int:
    compact = value.strip()
    if compact.isdigit():
        return int(compact)
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    total = 0
    current = 0
    for character in compact:
        if character in digits:
            current = digits[character]
        elif character == "十":
            total += (current or 1) * 10
            current = 0
        elif character == "百":
            total += (current or 1) * 100
            current = 0
        else:
            raise ValueError(f"unsupported Chinese integer: {value}")
    return total + current


def source_page(text: str, table_start: int) -> int | None:
    matches = list(re.finditer(r"第\s*(\d+)\s*頁", text[:table_start]))
    if matches:
        return int(matches[-1].group(1))
    fractions = list(re.finditer(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", text[:table_start]))
    if fractions:
        page, total = (int(value) for value in fractions[-1].groups())
        return page if 0 < page <= total else None
    return None


def article_references(text: str) -> dict[str, str] | None:
    references = {}
    for key, heading in ARTICLE_HEADINGS.items():
        match = re.search(rf"{re.escape(heading)}\s+第\s*([一二三四五六七八九十百\d]+)\s*條", text)
        if not match:
            return None
        references[key] = f"第{match.group(1)}條"
    return references


def coverage_entry(
    entry_id: str,
    name: str,
    amount: int | None,
    basis: str,
    note: str,
    source_ref: str,
    *,
    calculation_basis: str,
    amount_role: str,
    limit_scope: str,
    aggregation_rule: str = "separate",
    rate_percent: int | float | None = None,
    rate_min_percent: int | None = None,
    rate_max_percent: int | None = None,
    multiplier: int | float | None = None,
    unit_key: str | None = None,
    conditions: list[str] | None = None,
    amount_tiers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    entry = {
        "id": entry_id,
        "name": name,
        "basis": basis,
        "calculation_basis": calculation_basis,
        "amount_role": amount_role,
        "limit_scope": limit_scope,
        "aggregation_rule": aggregation_rule,
        "source": "terms",
        "note": note,
        "source_ref": source_ref,
    }
    if amount is not None:
        entry["amount"] = amount
    if rate_percent is not None:
        entry["rate_percent"] = rate_percent
    if rate_min_percent is not None:
        entry["rate_min_percent"] = rate_min_percent
    if rate_max_percent is not None:
        entry["rate_max_percent"] = rate_max_percent
    if multiplier is not None:
        entry["multiplier"] = multiplier
    if unit_key:
        entry["unit_key"] = unit_key
    if conditions:
        entry["conditions"] = conditions
    if amount_tiers:
        entry["amount_tiers"] = amount_tiers
    return entry


DAILY_HOSPITAL_97_PRODUCT_IDS = {
    "203311R11A00102",
    "203311R11A00103",
    "203311R11A00104",
    "203311R11A00105",
    "203311R11A00106",
    "205311R11A00100",
    "205311R11A00101",
}
MEDICAL_ENDOWMENT_PRODUCT_IDS = {
    "203391M12B00100",
    "203391M12B00102",
    "203391M12B00103",
    "203391M12B00203",
    "205391M12B00100",
    "205391M12B00101",
}
MEDICAL_ENDOWMENT_FIXED_PLAN_BY_PRODUCT_ID = {
    "203391M12B00103": "plan-a",
    "203391M12B00203": "plan-b",
}

FUBON_CHILD_COMBINED_PRODUCT_IDS = {
    "209391M12D00100",
    "209391M12D00101",
    "209391M12D00300",
    "209391M19D00202",
    "209391M19D00300",
    "209391MZ9D00221A11Z10000003",
    "209391MZ9D00221A11Z10000004",
    "209391MZ9D00321A11Z10000001",
    "209391MZ9D00321A11Z10000003",
    "209391MZ9D00221A11Z10000005",
    "209391MZ9D00221A11Z10000006",
    "209391MZ9D00221A11Z10000007",
    "209391MZ9D00321A11Z10000004",
    "209391MZ9D00321A11Z10000005",
    "209391MZ9D00321A11Z10000006",
}
FUBON_NEW_CHILD_COMBINED_PRODUCT_IDS = {
    "209391M12D00300",
    "209391M19D00300",
    "209391MZ9D00321A11Z10000001",
    "209391MZ9D00321A11Z10000003",
    "209391MZ9D00321A11Z10000004",
    "209391MZ9D00321A11Z10000005",
    "209391MZ9D00321A11Z10000006",
}

FUBON_GOLDEN_COMPLETE_COMBINED_PRODUCT_VERSIONS = {
    "209391MZ9D00421A11Z10000001": {
        "document_code": "MGC21070914",
        "required_revision_signals": (
            "107.09.14 依 107.06.07 金管保壽字第 10704158370 號函修正",
        ),
        "forbidden_revision_signals": ("108.01.01", "109.01.01", "109.09.01"),
        "required_feature_signals": (
            "人體組織細胞異常增生及有轉移特性之惡性腫瘤",
            "始經病理組織切片或血液細胞學檢查診斷確定罹患",
        ),
        "cancer_definition_revision": "pre-108-pathology-or-cytology",
        "newborn_screening_revision": "original-screening-list",
        "reinstatement_notice_revision": "pre-109",
        "disability_schedule_revision": "104-revised-79-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
    },
    "209391MZ9D00421A11Z10000002": {
        "document_code": "MGC21080101",
        "required_revision_signals": (
            "108.01.01 依 107.09.17 金管保壽字第10704937510 號函修正",
        ),
        "forbidden_revision_signals": ("109.01.01", "109.09.01"),
        "required_feature_signals": (
            "組織細胞有惡性細胞不斷生長、擴張及對組織侵害的特性",
            "始經病理檢驗確定罹患",
        ),
        "cancer_definition_revision": "108-standardized-pathology",
        "newborn_screening_revision": "original-screening-list",
        "reinstatement_notice_revision": "pre-109",
        "disability_schedule_revision": "104-revised-79-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
    },
    "209391MZ9D00421A11Z10000003": {
        "document_code": "MGC21090101",
        "required_revision_signals": (
            "109.01.01 依 108.04.09 金管保壽字第10804904941 號函修正",
            "109.01.01 依 108.06.13 金管保壽字第10804933330 號函修正",
            "109.01.01 依 108.06.21 金管保壽字第10804920500 號函修正",
        ),
        "forbidden_revision_signals": ("109.09.01",),
        "required_feature_signals": (
            "遺傳性疾病之新生兒先天性代謝異常疾病檢查項目",
            "申請復效之期限屆滿前三個月",
            "鼻未缺損",
        ),
        "cancer_definition_revision": "108-standardized-pathology",
        "newborn_screening_revision": "109-genetic-disease-list",
        "reinstatement_notice_revision": "109-pre-expiry-reminder",
        "disability_schedule_revision": "109-revised-80-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
    },
    "209391MZ9D00421A11Z10000004": {
        "document_code": "MGC21090901",
        "required_revision_signals": (
            "109.09.01 依 109.07.08 金管保壽字第1090423012 號函修正",
        ),
        "forbidden_revision_signals": (),
        "required_feature_signals": (
            "遺傳性疾病之新生兒先天性代謝異常疾病檢查項目",
            "申請復效之期限屆滿前三個月",
            "鼻未缺損",
            "退還已繳保險費或身故保險金或喪葬費用保險金",
            "不得超過遺產及贈與稅法第十七條",
        ),
        "cancer_definition_revision": "108-standardized-pathology",
        "newborn_screening_revision": "109-genetic-disease-list",
        "reinstatement_notice_revision": "109-pre-expiry-reminder",
        "disability_schedule_revision": "109-revised-80-items",
        "missing_person_return_repayment_scope": "refund-or-death-benefit",
        "funeral_benefit_cap_reference": "statutory-deduction",
    },
}

FUBON_LITTLE_TYCOON_PRODUCT_IDS = {
    "209391M12D00200",
    "209391M19D00101",
    "209391MZ9D00121A11Z10000002",
    "209391MZ9D00121A11Z10000003",
    "209391MZ9D00121A11Z10000004",
    "209391MZ9D00121A11Z10000005",
    "209391MZ9D00121A11Z10000006",
    "209391MZ9D00121A11Z10000007",
}

FUBON_PROTECT_COMBINED_PRODUCT_IDS = {
    "209391M12G00200",
    "209391M11G00201",
    "209391MZ1G00221A11Z10000002",
    "209391MZ1G00221A11Z10000003",
    "209391MZ1G00221A11Z10000004",
    "209391MZ1G00221A11Z10000005",
    "209391MZ1G00221A11Z10000006",
    "209391MZ1G00221A11Z10000007",
}

FUBON_NEW_COMPLETE_COMBINED_PRODUCT_IDS = {
    "209391M12G00300",
    "209391M11G00301",
    "209391MZ1G00321A11Z10000002",
    "209391MZ1G00321A11Z10000003",
    "209391MZ1G00321A11Z10000004",
    "209391MZ1G00321A11Z10000005",
    "209391MZ1G00321A11Z10000006",
    "209391MZ1G00321A11Z10000007",
}

FUBON_NEW_COMPLETE_WAITING_PERIOD_SOURCE_CONFLICTS = [
    {
        "field": "cancer_reinstatement_waiting_days",
        "policy_terms_value": 0,
        "product_summary_value": 30,
        "authoritative_source": "policy_terms",
        "resolution": "policy_terms_precedence",
        "policy_terms_page": 2,
        "product_summary_page": 1,
        "note": "商品摘要載明復效後 30 日等待期，但保單條款載明自復效日起適用；摘要亦聲明以保單條款為準。",
    }
]

FUBON_NEW_COMPLETE_COMBINED_PRODUCT_VERSIONS = {
    "209391MZ1G00321A11Z10000004": {
        "document_code": "MGG1070914",
        "required_revision_signals": (
            "107.09.14依107.06.07金管保壽字第10704158370號函修正",
        ),
        "forbidden_revision_signals": ("108.01.01", "109.01.01", "109.09.01"),
        "required_feature_signals": (
            "完全失能保險金",
            "初次診斷罹患原位癌者或惡性腫瘤者",
        ),
        "disability_term": "失能",
        "cancer_classification": "original-two-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "104-revised-79-items",
        "truncated_schedule_tail": None,
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": FUBON_NEW_COMPLETE_WAITING_PERIOD_SOURCE_CONFLICTS,
    },
    "209391MZ1G00321A11Z10000005": {
        "document_code": "MGG1080101",
        "required_revision_signals": (
            "108.01.01依107.09.17金管保壽字第10704937510號函修正",
        ),
        "forbidden_revision_signals": ("109.01.01", "109.09.01"),
        "required_feature_signals": (
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "104-revised-79-items",
        "truncated_schedule_tail": "8-2-3",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": FUBON_NEW_COMPLETE_WAITING_PERIOD_SOURCE_CONFLICTS,
    },
    "209391MZ1G00321A11Z10000006": {
        "document_code": "MGG1090101",
        "required_revision_signals": (
            "109.01.01依108.04.09金管保壽字第10804904941號函修正",
            "109.01.01依108.06.13金管保壽字第10804933330號函修正",
            "109.01.01依108.06.21金管保壽字第10804920500號函修正",
        ),
        "forbidden_revision_signals": ("109.09.01",),
        "required_feature_signals": (
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
            "鼻未缺損",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "109-revised-80-items",
        "truncated_schedule_tail": "8-2-4",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": FUBON_NEW_COMPLETE_WAITING_PERIOD_SOURCE_CONFLICTS,
    },
    "209391MZ1G00321A11Z10000007": {
        "document_code": "MGG1090901",
        "required_revision_signals": (
            "109.09.01依109.07.08金管保壽字第1090423012號函修正",
        ),
        "forbidden_revision_signals": (),
        "required_feature_signals": (
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
            "鼻未缺損",
            "要保人或受益人應將該筆已領之退還已繳保險費或身故保險金或喪葬費用保險金歸還本公司",
            "不得超過遺產及贈與稅法第十七條",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "109-revised-80-items",
        "truncated_schedule_tail": "8-2-4",
        "missing_person_return_repayment_scope": "refund-or-death-benefit",
        "funeral_benefit_cap_reference": "statutory-deduction",
        "source_conflicts": FUBON_NEW_COMPLETE_WAITING_PERIOD_SOURCE_CONFLICTS,
    },
}

FUBON_CARDIO_DEVICE_UNIT_PRODUCT_VERSIONS = {
    "209391MZ1A00322A11Z10000000": {
        "product_kind": "heart-guard",
        "document_code": "EHC1141110",
        "required_revision_signals": ("114.11.10富壽商精字第1140003083號函備查",),
        "forbidden_revision_signals": (),
    },
    "209391RZ1A01522A11Z10000000": {
        "product_kind": "heart-care",
        "document_code": "HTR1121204",
        "required_revision_signals": ("112.12.04富壽商精字第1120005077號函備查",),
        "forbidden_revision_signals": ("113.07.01", "113.09.23"),
    },
    "209391RZ1A01522A11Z10000001": {
        "product_kind": "heart-care",
        "document_code": "HTR1130701",
        "required_revision_signals": (
            "112.12.04富壽商精字第1120005077號函備查",
            "113.07.01依112.12.18金管保壽字第11204939659號函修正",
        ),
        "forbidden_revision_signals": ("113.09.23",),
    },
    "209391RZ1A01522A11Z10000002": {
        "product_kind": "heart-care",
        "document_code": "HTR1130923",
        "required_revision_signals": (
            "112.12.04富壽商精字第1120005077號函備查",
            "113.07.01依112.12.18金管保壽字第11204939659號函修正",
            "113.09.23依113.06.28金管保壽字第11304207572號函修正",
        ),
        "forbidden_revision_signals": (),
    },
}

ANTAI_FUBON_NEW_CANCER_LIFETIME_PRODUCT_IDS = {
    "252321M12B00100",
    "209321M12B00301",
    "209321M12B00302",
    "209321M12B00303",
}

ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_VERSIONS = {
    "252321R11A00301": {
        "revision": "first-revision",
        "file_name": "252321R11A003-1-A.pdf",
        "required_revision_signals": (
            "09302034361",
            "安耀精字第94078號函備查",
        ),
        "forbidden_revision_signals": (
            "安耀精字第94107號函備查",
            "09402133930",
            "安俊精字第96045號函備查",
            "安俊精字第97016號函備查",
        ),
        "revised_contract_rules": False,
        "table_title_prefix": "各項保險金",
        "table_trailer": "11",
        "table_page": 11,
    },
    "252321R11A00302": {
        "revision": "second-revision",
        "file_name": "252321R11A003-2-A.pdf",
        "required_revision_signals": (
            "09302034361",
            "安耀精字第94078號函備查",
            "安耀精字第94107號函備查",
        ),
        "forbidden_revision_signals": (
            "09402133930",
            "安俊精字第96045號函備查",
            "安俊精字第97016號函備查",
        ),
        "revised_contract_rules": False,
        "table_title_prefix": "各項保險金",
        "table_trailer": "11",
        "table_page": 9,
    },
    "252321R11A00303": {
        "revision": "third-revision",
        "file_name": "252321R11A00303-A.pdf",
        "required_revision_signals": (
            "09302034361",
            "安耀精字第94078號函備查",
            "安耀精字第94107號函備查",
            "09402133930",
            "安俊精字第96045號函備查",
        ),
        "forbidden_revision_signals": ("安俊精字第97016號函備查",),
        "revised_contract_rules": True,
        "table_title_prefix": "",
        "table_trailer": "",
        "table_page": 7,
    },
    "252321R11A00304": {
        "revision": "fourth-revision",
        "file_name": "252321R11A00304-A.pdf",
        "required_revision_signals": (
            "09302034361",
            "安耀精字第94078號函備查",
            "安耀精字第94107號函備查",
            "09402133930",
            "安俊精字第96045號函備查",
            "安俊精字第97016號函備查",
        ),
        "forbidden_revision_signals": (),
        "revised_contract_rules": True,
        "table_title_prefix": "",
        "table_trailer": "",
        "table_page": 7,
    },
}

GLOBAL_WINTERTHUR_CANCER_ANNUITY_PRODUCT_VERSIONS = {
    "262321R11A00300": {
        "product_variant": "traditional",
        "revision": "original",
        "required_revision_signals": ("09402129990",),
        "forbidden_revision_signals": ("0950252225B", "96UCAR0001", "96UCAR0003"),
        "benefit_articles": ("十二", "十三", "十四", "十五"),
        "maximum_renewal_age": 65,
        "terminates_after_cancer": False,
        "actual_diagnosis_date_evidence_allowed": False,
    },
    "262321R11A00301": {
        "product_variant": "traditional",
        "revision": "first-revision",
        "required_revision_signals": ("09402129990", "0950252225B"),
        "forbidden_revision_signals": ("96UCAR0001", "96UCAR0003"),
        "benefit_articles": ("十三", "十四", "十五", "十六"),
        "maximum_renewal_age": 65,
        "terminates_after_cancer": False,
        "actual_diagnosis_date_evidence_allowed": False,
    },
    "262321R11A00400": {
        "product_variant": "investment-linked",
        "revision": "original",
        "required_revision_signals": ("96UCAR0001",),
        "forbidden_revision_signals": ("09402129990", "0950252225B", "96UCAR0003"),
        "benefit_articles": ("十二", "十三", "十四", "十五"),
        "maximum_renewal_age": 75,
        "terminates_after_cancer": False,
        "actual_diagnosis_date_evidence_allowed": False,
    },
    "262321R11A00401": {
        "product_variant": "investment-linked",
        "revision": "first-revision",
        "required_revision_signals": ("96UCAR0001", "96UCAR0003"),
        "forbidden_revision_signals": ("09402129990", "0950252225B"),
        "benefit_articles": ("十二", "十三", "十四", "十五"),
        "maximum_renewal_age": 75,
        "terminates_after_cancer": True,
        "actual_diagnosis_date_evidence_allowed": True,
    },
}

FUBON_EASY_COMBINED_PRODUCT_IDS = {
    "209391M12G00400",
    "209391M19G00101",
    "209391M19G00102",
    "209391MZ9G00121A11Z10000003",
    "209391MZ9G00121A11Z10000004",
    "209391MZ9G00121A11Z10000005",
    "209391MZ9G00121A11Z10000006",
    "209391MZ9G00121A11Z10000007",
    "209391MZ9G00121A11Z10000008",
}
FUBON_EASY_WAITING_PERIOD_SOURCE_CONFLICTS = [
    {
        "field": "cancer_reinstatement_waiting_days",
        "policy_terms_value": 0,
        "product_summary_value": 30,
        "authoritative_source": "policy_terms",
        "resolution": "policy_terms_precedence",
        "policy_terms_page": 2,
        "product_summary_page": 1,
        "note": "商品摘要載明復效後 30 日等待期，但保單條款載明自復效日起適用；摘要亦聲明以保單條款為準。",
    }
]
FUBON_EASY_COMBINED_PRODUCT_VERSIONS = {
    "209391MZ9G00121A11Z10000005": {
        "document_code": "MGF1070914",
        "required_revision_signals": (
            "107.09.14依107.06.07金管保壽字第10704158370號函修正",
        ),
        "forbidden_revision_signals": ("108.01.01", "109.01.01", "109.09.01"),
        "required_feature_signals": (
            "完全失能保險金",
            "初次診斷罹患原位癌者或惡性腫瘤者",
            "包含精神衛生法第三十五條所稱之日間留院",
        ),
        "disability_term": "失能",
        "cancer_classification": "original-two-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "104-revised-79-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": FUBON_EASY_WAITING_PERIOD_SOURCE_CONFLICTS,
        "table_sha256": "ed0d6a2d81fdf64763a9f52cc34af87aa5a38c86b197db7177ed018e875d95b6",
    },
    "209391MZ9G00121A11Z10000006": {
        "document_code": "MGF1080101",
        "required_revision_signals": (
            "108.01.01依107.09.17金管保壽字第10704937510號函修正",
        ),
        "forbidden_revision_signals": ("109.01.01", "109.09.01"),
        "required_feature_signals": (
            "完全失能保險金",
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
            "包含精神衛生法第三十五條所稱之日間留院",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "104-revised-79-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": [],
        "table_sha256": "9aa387cbd5ce08a73a5727e54ce3b3f39eb91d355fd9b8bfcdc0c4a419069216",
    },
    "209391MZ9G00121A11Z10000007": {
        "document_code": "MGF1090101",
        "required_revision_signals": (
            "109.01.01依108.04.09金管保壽字第10804904941號函修正",
            "109.01.01依108.06.13金管保壽字第10804933330號函修正",
            "109.01.01依108.06.21金管保壽字第10804920500號函修正",
        ),
        "forbidden_revision_signals": ("109.09.01",),
        "required_feature_signals": (
            "完全失能保險金",
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
            "包含精神衛生法第三十五條所稱之日間留院",
            "申請復效之期限屆滿前三個月",
            "鼻未缺損",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "109-revised-80-items",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
        "source_conflicts": [],
        "table_sha256": "c04c7ffaebf328f43cda200c00ac47ac7aa4b531655dd71d83dba8cee33774b8",
    },
    "209391MZ9G00121A11Z10000008": {
        "document_code": "MGF1090901",
        "required_revision_signals": (
            "109.09.01依109.07.08金管保壽字第1090423012號函修正",
        ),
        "forbidden_revision_signals": (),
        "required_feature_signals": (
            "完全失能保險金",
            "癌症(初期)",
            "癌症(輕度)或癌症(重度)",
            "包含精神衛生法第三十五條所稱之日間留院",
            "申請復效之期限屆滿前三個月",
            "鼻未缺損",
            "要保人或受益人應將該筆已領之退還已繳保險費或身故保險金或喪葬費用保險金歸還本公司",
            "不得超過遺產及贈與稅法第十七條",
        ),
        "disability_term": "失能",
        "cancer_classification": "2018-three-tier",
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": 0,
        "day_hospital_explicit": True,
        "disability_schedule_revision": "109-revised-80-items",
        "missing_person_return_repayment_scope": "refund-or-death-benefit",
        "funeral_benefit_cap_reference": "statutory-deduction",
        "source_conflicts": [],
        "table_sha256": "54f1ed6dd0c0091eb1421e6f1c9cb975d957fdb2b032b3b7bf1742310277a2ee",
    },
}
FUBON_LOHAS_COMBINED_PRODUCT_IDS = {
    "209391M12G00100",
    "209391M12G00101",
    "209391M19G00201",
    "209391MZ9G00221A11Z10000003",
    "209391MZ9G00221A11Z10000004",
}

FUBON_GOLDEN_LOHAS_COMBINED_PRODUCT_VERSIONS = {
    "209391MZ1G00421A11Z10000002": {
        "document_code": "MGA21070914",
        "required_revision_signals": (
            "107.09.14 依 107.06.07 金管保壽字第 10704158370 號函修正",
        ),
        "forbidden_revision_signals": ("109.01.01", "109.09.01", "110.01.01"),
        "disability_schedule_revision": "104-revised-79-items",
    },
    "209391MZ1G00421A11Z10000003": {
        "document_code": "MGA21090101",
        "required_revision_signals": (
            "109.01.01 依 108.06.21 金管保壽字第10804920500 號函修正",
        ),
        "forbidden_revision_signals": ("109.09.01", "110.01.01"),
        "disability_schedule_revision": "109-revised-80-items",
    },
    "209391MZ1G00421A11Z10000004": {
        "document_code": "MGA21090901",
        "required_revision_signals": (
            "109.09.01 依 109.07.08 金管保壽字第1090423012 號函修正",
        ),
        "forbidden_revision_signals": ("110.01.01",),
        "disability_schedule_revision": "109-revised-80-items",
    },
    "209391MZ1G00421A11Z10000005": {
        "document_code": "MGA21100101",
        "required_revision_signals": (
            "110.01.01 富壽商精字第1090006034 號函備查",
        ),
        "forbidden_revision_signals": (),
        "disability_schedule_revision": "109-revised-80-items",
    },
}

FUBON_NEW_LOHAS_BASE_REVISION_SIGNALS = (
    "103.05.01 富壽商精字第 1030000884 號函備查",
    "104.08.04 依 104.05.19 金管保壽字第 10402543750 號函修正",
    "104.08.04 依 104.06.24 金管保壽字第 10402049830 號函修正",
    "107.09.14 依 107.06.07 金管保壽字第 10704158370 號函修正",
)
FUBON_NEW_LOHAS_109_REVISION_SIGNALS = (
    "109.01.01 依 108.04.09 金管保壽字第 10804904941 號函修正",
    "109.01.01 依 108.06.13 金管保壽字第 10804933330 號函修正",
    "109.01.01 依 108.06.21 金管保壽字第 10804920500 號函修正",
)
FUBON_NEW_LOHAS_PRODUCT_VERSIONS = {
    "209391MZ1G00121A11Z10000002": {
        "document_code": "MGA11070914",
        "required_revision_signals": FUBON_NEW_LOHAS_BASE_REVISION_SIGNALS,
        "forbidden_revision_signals": ("109.01.01", "109.09.01", "110.01.01"),
        "required_feature_signals": (
            "受益人應將該筆已領之保險金歸還本公司",
            "不得超過訂立本契約時遺產及贈與稅法第十七條",
        ),
        "forbidden_feature_signals": (
            "申請復效之期限屆滿前三個月",
            "基於審核保險金之需要",
            "鼻未缺損",
            "要保人或受益人應將該筆已領之退還已繳保險費或保險金歸還本公司",
        ),
        "disability_schedule_revision": "104-revised-79-items",
        "reinstatement_notice_revision": "pre-109",
        "claims_medical_review_revision": "pre-109",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
    },
    "209391MZ1G00121A11Z10000003": {
        "document_code": "MGA11090101",
        "required_revision_signals": (
            *FUBON_NEW_LOHAS_BASE_REVISION_SIGNALS,
            *FUBON_NEW_LOHAS_109_REVISION_SIGNALS,
        ),
        "forbidden_revision_signals": ("109.09.01", "110.01.01"),
        "required_feature_signals": (
            "申請復效之期限屆滿前三個月",
            "基於審核保險金之需要",
            "鼻未缺損",
            "受益人應將該筆已領之保險金歸還本公司",
            "不得超過訂立本契約時遺產及贈與稅法第十七條",
        ),
        "forbidden_feature_signals": (
            "要保人或受益人應將該筆已領之退還已繳保險費或保險金歸還本公司",
        ),
        "disability_schedule_revision": "109-revised-80-items",
        "reinstatement_notice_revision": "109-pre-expiry-reminder",
        "claims_medical_review_revision": "109-revised",
        "missing_person_return_repayment_scope": "death-benefit-only",
        "funeral_benefit_cap_reference": "contract-inception",
    },
    "209391MZ1G00121A11Z10000004": {
        "document_code": "MGA11090901",
        "required_revision_signals": (
            *FUBON_NEW_LOHAS_BASE_REVISION_SIGNALS,
            *FUBON_NEW_LOHAS_109_REVISION_SIGNALS,
            "109.09.01 依 109.07.08 金管保壽字第 1090423012 號函修正",
        ),
        "forbidden_revision_signals": ("110.01.01",),
        "required_feature_signals": (
            "申請復效之期限屆滿前三個月",
            "基於審核保險金之需要",
            "鼻未缺損",
            "要保人或受益人應將該筆已領之退還已繳保險費或保險金歸還本公司",
            "不得超過遺產及贈與稅法第十七條有關遺產稅喪葬費扣除額之半數",
        ),
        "forbidden_feature_signals": (
            "不得超過訂立本契約時遺產及贈與稅法第十七條",
        ),
        "disability_schedule_revision": "109-revised-80-items",
        "reinstatement_notice_revision": "109-pre-expiry-reminder",
        "claims_medical_review_revision": "109-revised",
        "missing_person_return_repayment_scope": "refund-or-death-benefit",
        "funeral_benefit_cap_reference": "statutory-deduction",
    },
    "209391MZ1G00121A11Z10000005": {
        "document_code": "MGA11100101",
        "required_revision_signals": (
            *FUBON_NEW_LOHAS_BASE_REVISION_SIGNALS,
            *FUBON_NEW_LOHAS_109_REVISION_SIGNALS,
            "109.09.01 依 109.07.08 金管保壽字第 1090423012 號函修正",
            "110.01.01 富壽商精字第 1090006151 號函備查",
        ),
        "forbidden_revision_signals": (),
        "required_feature_signals": (
            "申請復效之期限屆滿前三個月",
            "基於審核保險金之需要",
            "鼻未缺損",
            "要保人或受益人應將該筆已領之退還已繳保險費或保險金歸還本公司",
            "不得超過遺產及贈與稅法第十七條有關遺產稅喪葬費扣除額之半數",
        ),
        "forbidden_feature_signals": (
            "不得超過訂立本契約時遺產及贈與稅法第十七條",
        ),
        "disability_schedule_revision": "109-revised-80-items",
        "reinstatement_notice_revision": "109-pre-expiry-reminder",
        "claims_medical_review_revision": "109-revised",
        "missing_person_return_repayment_scope": "refund-or-death-benefit",
        "funeral_benefit_cap_reference": "statutory-deduction",
    },
}
FUBON_NEW_LOHAS_FILE_PATTERN = re.compile(
    r"209391MZ1G00121A11Z1000000[2-5]-[AF]\.pdf"
)
FUBON_NEW_LOHAS_TABLE_SHA256 = (
    "76bb958e694c90f0e156d485ea43c38a668f3fbf7b72f1736279fa25c46c9411"
)


def parse_four_plan_amounts(text: str, label: str) -> list[int] | None:
    match = re.search(
        rf"{re.escape(label)}"
        rf".{{0,1200}}?"
        rf"計畫一\s*([\d,]+)\s*元\s*"
        rf".{{0,1200}}?"
        rf"計畫二\s*([\d,]+)\s*元"
        rf".{{0,3500}}?"
        rf"計畫三\s*([\d,]+)\s*元\s*"
        rf"計畫四\s*([\d,]+)\s*元",
        text,
    )
    if not match:
        return None
    return [int(value.replace(",", "")) for value in match.groups()]


def find_fubon_clause_start(text: str, heading: str, article: str) -> int:
    match = re.search(
        rf"【{re.escape(heading)}】.{{0,120}}?{re.escape(article)}",
        text,
    )
    return match.start() if match else -1


def compact_table_text(text: str) -> str:
    return re.sub(r"[\s,，:：()（）]", "", unicodedata.normalize("NFKC", text))


def parse_fubon_easy_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_EASY_COMBINED_PRODUCT_VERSIONS.get(product_id)
    if (
        product_id not in FUBON_EASY_COMBINED_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    if version is not None:
        required_revision_signals = tuple(
            compact_table_text(signal)
            for signal in version["required_revision_signals"]
        )
        forbidden_revision_signals = tuple(
            compact_table_text(signal)
            for signal in version["forbidden_revision_signals"]
        )
        required_feature_signals = tuple(
            compact_table_text(signal)
            for signal in version["required_feature_signals"]
        )
        document_code = version["document_code"]
        if (
            f"{document_code} 1/26" not in text
            or f"{document_code} 20/26" not in text
            or any(signal not in compact_text for signal in required_revision_signals)
            or any(signal in compact_text for signal in forbidden_revision_signals)
            or any(signal not in compact_text for signal in required_feature_signals)
        ):
            return None

    disability_term = version["disability_term"] if version else "殘廢"
    new_cancer_classification = bool(
        version and version["cancer_classification"] == "2018-three-tier"
    )
    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", f"保險範圍:完全{disability_term}保險金的給付", "第十三條"),
        ("cancer", "保險範圍:癌症保險金的給付", "第十七條"),
        ("hospital", "保險範圍:住院醫療保險金的給付", "第十八條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十一條"),
        ("accident_hospital", "保險範圍:住院醫療保險金的給付", "第二十二條"),
        ("accident_outpatient", "保險範圍:意外傷害門診手術醫療保險金的給付", "第二十三條"),
        ("accident_reimbursement", "保險範圍:意外傷害醫療保險金的給付", "第二十四條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十五條"),
        ("accident_disability", f"保險範圍:意外{disability_term}保險金的給付", "第二十六條"),
        ("accident_limit", f"意外身故保險金及意外{disability_term}保險金給付的限制", "第二十七條"),
    ]
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    required_clause_signals = (
        "富邦人壽安心輕鬆保傷害暨健康一年定期保險",
        "本契約保險期間為一年",
        "本保險為非保證續保之保險商品",
        "初次罹患癌症保險金之責任,各以一次為限",
        "同一保單年度同一次住院給付日數最高以三百六十五日為限",
        "同一保單年度同一次住院給付日數最高以七日為限",
        "自意外傷害事故發生之日起屆滿十五日仍生存",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "則附表一所載意外傷害醫療保險金之限額提高為1.35 倍",
        "同時符合二項以上大眾運輸工具意外傷害事故者",
        "要保人係投保計畫十一或計畫十二者,僅就殘廢等級第二級至第十一級給付保險金",
    )
    if version is not None:
        required_clause_signals = tuple(
            "被保險人每次意外傷害得申領之意外傷害門診手術醫療保險金"
            if signal
            == "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限"
            else signal
            for signal in required_clause_signals
        )
    if disability_term == "失能":
        required_clause_signals = tuple(
            signal.replace("殘廢", "失能") for signal in required_clause_signals
        )
    if version is not None:
        if not all(
            compact_table_text(signal) in compact_text
            for signal in required_clause_signals
        ):
            return None
    elif not all(signal in text for signal in required_clause_signals):
        return None
    has_reinstatement_waiting_period = "或復效日持續有效三十日" in text
    if not has_reinstatement_waiting_period and "自本契約生效日(或復效日)起" not in text:
        return None

    table_start = text.find("附表一:")
    table_end = text.find("附表二", table_start + 1)
    if (
        table_start < 0
        or table_end <= table_start
        or (version is not None and text.count("附表一:") != 3)
    ):
        return None
    table_text = compact_table_text(text[table_start:table_end])
    table_signals = (
        "保險金項目計畫一計畫二計畫三計畫四",
        "身故保險金或喪葬費用保險金無無50萬100萬",
        "完全殘廢保險金無無50萬100萬",
        "重大燒燙傷保險金20萬40萬40萬80萬",
        "一般意外身故保險金或喪葬費用保險金50萬100萬100萬200萬",
        "癌症手術治療保險金1萬/次1萬/次1萬/次3萬/次",
        "意外傷害住院醫療保險金1000元/日1000元/日1000元/日1500元/日",
        "意外傷害醫療保險金無無無無",
        "保險金項目計畫五計畫六計畫七計畫八",
        "身故保險金或喪葬費用保險金100萬無無50萬",
        "重大燒燙傷保險金120萬20萬40萬40萬",
        "一般意外身故保險金或喪葬費用保險金300萬50萬100萬100萬",
        "癌症手術治療保險金3萬/次1萬/次1萬/次1萬/次",
        "意外傷害醫療保險金無3萬3萬3萬",
        "一般住院醫療保險金2000元/日1500元/日1500元/日1500元/日",
        "保險金項目計畫九計畫十計畫十一計畫十二",
        "身故保險金或喪葬費用保險金100萬100萬100萬200萬",
        "完全殘廢保險金100萬100萬200萬300萬",
        "重大燒燙傷保險金80萬120萬25萬25萬",
        "一般意外身故保險金或喪葬費用保險金200萬300萬100萬100萬",
        "癌症身故保險金10萬10萬50萬50萬",
        "癌症手術治療保險金3萬/次3萬/次1萬/次3萬/次",
        "意外傷害住院醫療保險金1500元/日1500元/日無無",
        "意外傷害醫療保險金3萬3萬無無",
        "一般住院醫療保險金1500元/日2000元/日無無",
    )
    if disability_term == "失能":
        table_signals = tuple(
            signal.replace("殘廢", "失能") for signal in table_signals
        )
    if new_cancer_classification:
        table_signals = tuple(
            signal.replace("原位癌", "癌症(初期)").replace(
                "惡性腫瘤", "癌症(輕度)或癌症(重度)"
            )
            for signal in table_signals
        )
    if not all(compact_table_text(signal) in table_text for signal in table_signals):
        return None
    if version is not None and hashlib.sha256(table_text.encode("utf-8")).hexdigest() != version["table_sha256"]:
        return None

    plan_labels = (
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
        "計畫九",
        "計畫十",
        "計畫十一",
        "計畫十二",
    )
    amounts = {
        "policy_death": [0, 0, 500_000, 1_000_000, 1_000_000, 0, 0, 500_000, 1_000_000, 1_000_000, 1_000_000, 2_000_000],
        "total_disability": [0, 0, 500_000, 1_000_000, 1_000_000, 0, 0, 500_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000],
        "carcinoma_in_situ": [0, 0, 5_000, 5_000, 5_000, 0, 0, 5_000, 5_000, 5_000, 5_000, 5_000],
        "malignant_tumor": [0, 0, 50_000, 50_000, 50_000, 0, 0, 50_000, 50_000, 50_000, 50_000, 50_000],
        "major_burn": [200_000, 400_000, 400_000, 800_000, 1_200_000, 200_000, 400_000, 400_000, 800_000, 1_200_000, 250_000, 250_000],
        "accident_death": [500_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 500_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 1_000_000, 1_000_000],
        "air_death": [0, 2_000_000, 2_000_000, 4_000_000, 6_000_000, 0, 2_000_000, 2_000_000, 4_000_000, 6_000_000, 0, 0],
        "surface_death": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "fire_death": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "elevator_death": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "accident_disability": [500_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 500_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000],
        "air_disability": [0, 2_000_000, 2_000_000, 4_000_000, 6_000_000, 0, 2_000_000, 2_000_000, 4_000_000, 6_000_000, 0, 0],
        "surface_disability": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "fire_disability": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "elevator_disability": [0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 1_000_000, 1_000_000, 2_000_000, 3_000_000, 0, 0],
        "cancer_death": [100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 100_000, 500_000, 500_000],
        "cancer_surgery": [10_000, 10_000, 10_000, 30_000, 30_000, 10_000, 10_000, 10_000, 30_000, 30_000, 10_000, 30_000],
        "accident_hospital": [1_000, 1_000, 1_000, 1_500, 1_500, 1_000, 1_000, 1_000, 1_500, 1_500, 0, 0],
        "accident_icu": [1_000, 1_000, 1_000, 1_500, 1_500, 1_000, 1_000, 1_000, 1_500, 1_500, 0, 0],
        "accident_outpatient": [2_000, 2_000, 2_000, 3_000, 3_000, 2_000, 2_000, 2_000, 3_000, 3_000, 0, 0],
        "accident_reimbursement": [0, 0, 0, 0, 0, 30_000, 30_000, 30_000, 30_000, 30_000, 0, 0],
        "hospital": [1_500, 1_500, 1_500, 1_500, 2_000, 1_500, 1_500, 1_500, 1_500, 2_000, 0, 0],
        "hospital_icu": [1_500, 1_500, 1_500, 1_500, 2_000, 1_500, 1_500, 1_500, 1_500, 2_000, 0, 0],
    }

    article_pages = {
        key: source_page(text, start)
        for key, start in article_starts.items()
    }
    fallback_pages = {
        "policy_death": 4,
        "total_disability": 4,
        "cancer": 5,
        "hospital": 6,
        "major_burn": 7,
        "accident_hospital": 7,
        "accident_outpatient": 8,
        "accident_reimbursement": 8,
        "accident_death": 8,
        "accident_disability": 9,
        "accident_limit": 10,
    }
    article_pages = {
        key: article_pages[key] or fallback_pages[key]
        for key in article_pages
    }
    table_page = source_page(text, table_start) or 13
    table_ref = f"附表一，第 {table_page}-{table_page + 2} 頁"
    cancer_condition = (
        "癌症初次生效無等待期；復效須持續有效 30 日後，始經診斷確定"
        if has_reinstatement_waiting_period
        else "癌症初次生效及復效均無等待期；須於有效期間內始經診斷確定"
    )
    day_hospital_explicit = "包含精神衛生法第三十五條所稱之日間留院" in text
    revised_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    revised_109_schedule = revised_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    if version is not None:
        cancer_reinstatement_waiting_days = (
            30 if has_reinstatement_waiting_period else 0
        )
        if (
            version["cancer_initial_waiting_days"] != 0
            or cancer_reinstatement_waiting_days
            != version["cancer_reinstatement_waiting_days"]
            or day_hospital_explicit != version["day_hospital_explicit"]
        ):
            return None
        schedule_revision = version["disability_schedule_revision"]
        if schedule_revision == "104-revised-79-items":
            if not revised_104_schedule or revised_109_schedule:
                return None
        elif schedule_revision == "109-revised-80-items":
            if not revised_109_schedule:
                return None
        else:
            return None
        schedule_condition = (
            f"本版本採 109 年修正版附表三，共 80 項{disability_term}程度"
            if schedule_revision == "109-revised-80-items"
            else f"本版本採 104 年修正版附表三，共 79 項{disability_term}程度"
        )
    else:
        schedule_revision = (
            "104-revised-79-items"
            if revised_104_schedule
            else "original-75-items"
        )
        schedule_condition = (
            "本版本採 104 年修正版附表三，共 79 項殘廢程度"
            if revised_104_schedule
            else None
        )
    hospital_conditions = [
        "含入院及出院當日",
        "同一保單年度同一次住院最高 365 日",
        "同一疾病、傷害或其併發症於出院後 14 日內在同一醫院再住院，視為同一次住院",
    ]
    if day_hospital_explicit:
        hospital_conditions.append("本版本條款明列住院包含精神衛生法所稱日間留院")
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    hijack_condition = "以乘客身分搭乘大眾運輸工具遭劫持時，契約期滿後至劫持事故終了前仍延續本項保障"
    total_disability_name = f"完全{disability_term}保險金"
    early_cancer_entry_id = (
        "initial-early-cancer"
        if new_cancer_classification
        else "initial-carcinoma-in-situ"
    )
    early_cancer_name = (
        "初次罹患癌症（初期）保險金"
        if new_cancer_classification
        else "初次罹患原位癌保險金"
    )
    early_cancer_diagnosis = (
        "癌症（初期）" if new_cancer_classification else "原位癌"
    )
    other_cancer_entry_id = (
        "initial-other-cancer"
        if new_cancer_classification
        else "initial-malignant-tumor"
    )
    other_cancer_name = (
        "初次罹患癌症（輕度或重度）保險金"
        if new_cancer_classification
        else "初次罹患惡性腫瘤保險金"
    )
    other_cancer_diagnosis = (
        "癌症（輕度或重度）" if new_cancer_classification else "惡性腫瘤"
    )

    plan_options = []
    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add_amount_entry(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            note: str,
            source_ref: str,
            *,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
            amount_tiers: list[dict[str, Any]] | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            if not amount:
                return
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(amount=amount, plan=plan_label),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                    amount_tiers=amount_tiers,
                )
            )

        add_amount_entry(
            "policy_death",
            "policy-death",
            "身故保險金或喪葬費用保險金",
            "policy_total",
            "依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十二條，第 {article_pages['policy_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", "特定身分依法改為喪葬費用保險金並受法定總額限制"],
        )
        add_amount_entry(
            "total_disability",
            "total-disability",
            total_disability_name,
            "policy_total",
            f"符合附表二完全{disability_term}程度之一，依{{plan}}給付 {{amount:,}} 元後，本契約終止。",
            f"保單條款第十三條及附表二，第 {article_pages['total_disability']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", f"完全{disability_term}後身故不另給付第十二條身故保險金"],
        )
        add_amount_entry(
            "carcinoma_in_situ",
            early_cancer_entry_id,
            early_cancer_name,
            "policy_total",
            f"初次診斷罹患{early_cancer_diagnosis}，依{{plan}}給付 {{amount:,}} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )
        add_amount_entry(
            "malignant_tumor",
            other_cancer_entry_id,
            other_cancer_name,
            "policy_total",
            f"初次診斷罹患{other_cancer_diagnosis}，依{{plan}}給付 {{amount:,}} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )
        for entry_id, name, amount_key in (
            ("cancer-hospital-daily", "癌症住院醫療保險金", None),
            ("cancer-recovery-daily", "癌症出院療養保險金", None),
            ("cancer-radiotherapy-daily", "癌症放射線治療保險金", None),
            ("cancer-chemotherapy-daily", "癌症化學治療保險金", None),
        ):
            conditions = [cancer_condition]
            limit_scope = "per_day"
            if entry_id == "cancer-hospital-daily":
                conditions.append("按實際住院日數計算，含入院及出院當日")
            elif entry_id == "cancer-recovery-daily":
                conditions.append("按該次實際住院日數計算，每次住院最高 21 日")
                limit_scope = "per_hospitalization"
            else:
                conditions.append("同日多次治療仍以一日計，每保單年度最高 60 日")
                limit_scope = "annual"
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    1_000,
                    "daily_total",
                    f"每一符合條款的治療日給付 1,000 元。",
                    f"保單條款第十七條，第 {article_pages['cancer']} 頁起；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope=limit_scope,
                    conditions=conditions,
                )
            )
        add_amount_entry(
            "cancer_surgery",
            "cancer-surgery",
            "癌症手術治療保險金",
            "per_event",
            "每次符合條款的癌症或其併發症外科手術給付 {amount:,} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁起；{table_ref}",
            limit_scope="per_surgery",
            conditions=[cancer_condition],
        )
        add_amount_entry(
            "cancer_death",
            "cancer-death",
            "癌症身故保險金",
            "policy_total",
            "因癌症或其併發症身故，依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "給付後本契約終止"],
        )
        add_amount_entry(
            "hospital",
            "hospital-daily",
            "一般住院醫療保險金",
            "daily_total",
            "因疾病或傷害住院，每日給付 {amount:,} 元。",
            f"保單條款第十八條，第 {article_pages['hospital']} 頁；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            conditions=hospital_conditions,
        )
        add_amount_entry(
            "hospital_icu",
            "hospital-icu-daily",
            "加護病房住院醫療保險金",
            "daily_total",
            "入住加護病房時，除一般住院給付外，每日另給付 {amount:,} 元。",
            f"保單條款第十八條，第 {article_pages['hospital']} 頁；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            aggregation_rule="conditional_additive",
            conditions=["含轉入及轉出當日", "同一保單年度同一次住院最高 7 日", "同日轉出後再轉入不重複計算"],
        )
        add_amount_entry(
            "major_burn",
            "major-burn",
            "重大燒燙傷保險金",
            "per_event",
            "符合條款的重大燒燙傷範圍，依{plan}給付 {amount:,} 元。",
            f"保單條款第二十一條及附表四，第 {article_pages['major_burn']} 頁起；{table_ref}",
            conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存", hijack_condition],
        )
        add_amount_entry(
            "accident_hospital",
            "accident-hospital-daily",
            "意外傷害住院醫療保險金",
            "daily_total",
            "因意外傷害住院，每日給付 {amount:,} 元。",
            f"保單條款第二十二條，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            conditions=[accident_180_condition, "含入院及出院當日", "同一次意外傷害最高 365 日"],
        )
        if amounts["accident_hospital"][index]:
            accident_hospital_amount = amounts["accident_hospital"][index]
            entries.append(
                coverage_entry(
                    "fracture-without-hospitalization",
                    "骨折未住院醫療保險金",
                    accident_hospital_amount,
                    "benefit_base",
                    "未住院部分按骨折表日數乘以意外住院日額的二分之一計算。",
                    f"保單條款第二十二條骨折表，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="table_multiplier",
                    amount_role="reference",
                    limit_scope="per_injury",
                    aggregation_rule="highest",
                    multiplier=0.5,
                    conditions=["完全骨折表列 14 至 60 日", "不完全骨折按二分之一、骨骼龜裂按四分之一", "同時多處骨折僅給付較高一項"],
                )
            )
        add_amount_entry(
            "accident_icu",
            "accident-icu-daily",
            "意外傷害加護病房住院醫療保險金",
            "daily_total",
            "入住加護病房時，除意外住院給付外，每日另給付 {amount:,} 元。",
            f"保單條款第二十二條，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            aggregation_rule="conditional_additive",
            conditions=[accident_180_condition, "受同一次意外住院 365 日上限限制", "同日轉出後再轉入不重複計算"],
        )
        add_amount_entry(
            "accident_outpatient",
            "accident-outpatient-surgery",
            "意外傷害門診手術醫療保險金",
            "per_event",
            "每次意外傷害符合條款的門診手術給付 {amount:,} 元。",
            f"保單條款第二十三條，第 {article_pages['accident_outpatient']} 頁；{table_ref}",
            limit_scope="per_injury",
            conditions=["每次意外傷害限申領一次"],
        )
        reimbursement_amount = amounts["accident_reimbursement"][index]
        add_amount_entry(
            "accident_reimbursement",
            "accident-medical-reimbursement",
            "意外傷害醫療保險金",
            "per_injury_limit",
            "超過全民健康保險給付部分實支實付，一般限額 {amount:,} 元。",
            f"保單條款第二十四條及第二十九條，第 {article_pages['accident_reimbursement']} 頁起；{table_ref}",
            calculation_basis="reimbursement_with_cap",
            amount_role="limit",
            limit_scope="per_injury",
            conditions=[accident_180_condition, "申領須檢附醫療費用收據正本"],
            amount_tiers=(
                [
                    {"label": "一般限額", "amount": reimbursement_amount},
                    {"label": "以全民健康保險身分接受治療", "amount": int(reimbursement_amount * 1.35)},
                ]
                if reimbursement_amount
                else None
            ),
        )
        add_amount_entry(
            "accident_death",
            "accident-death",
            "一般意外身故保險金或喪葬費用保險金",
            "policy_total",
            "一般意外身故依{plan}給付 {amount:,} 元。",
            f"保單條款第二十五條，第 {article_pages['accident_death']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[accident_180_condition, "未滿 15 足歲者身故給付自滿 15 足歲起生效", "給付後本契約終止", hijack_condition],
        )
        for amount_key, entry_id, name, condition in (
            ("air_death", "air-transport-accident-death", "空中大眾運輸工具意外身故保險金", "以乘客身分搭乘空中大眾運輸工具"),
            ("surface_death", "surface-transport-accident-death", "水上或陸地大眾運輸工具意外身故保險金", "以乘客身分搭乘水上或陸地大眾運輸工具"),
            ("fire_death", "public-building-fire-accident-death", "公共建築物火災意外身故保險金", "火災發生前已進入戲院、旅館或其他公共建築物"),
            ("elevator_death", "elevator-accident-death", "電梯意外身故保險金", "因乘坐電梯發生意外傷害事故"),
        ):
            add_amount_entry(
                amount_key,
                entry_id,
                name,
                "policy_total",
                "符合特定事故條件時，除一般意外身故保險金外另給付 {amount:,} 元。",
                f"保單條款第二十五條，第 {article_pages['accident_death']} 頁起；{table_ref}",
                limit_scope="per_policy",
                aggregation_rule="cumulative_cap",
                conditions=[accident_180_condition, condition, "同時符合兩項以上大眾運輸工具事故時僅給付最高一項", hijack_condition],
            )

        disability_min = 5
        disability_max = 90 if index >= 10 else 100
        disability_conditions = [
            accident_180_condition,
            f"依附表三{disability_term}等級 {disability_min}% 至 {disability_max}% 比例計算",
            "同一事故多項及不同事故累計受附表一最高給付金額限制",
            f"合併既有{disability_term}時須扣除視同已給付部分",
            f"同一事故{disability_term}後身故時，依第二十七條計算差額",
            hijack_condition,
        ]
        if index >= 10:
            disability_conditions.append("計畫十一、十二僅給付第 2 至第 11 級；第 1 級不給付")
        if schedule_condition:
            disability_conditions.append(schedule_condition)
        add_amount_entry(
            "accident_disability",
            "accident-disability",
            f"一般意外{disability_term}保險金",
            "benefit_base",
            f"以 {{amount:,}} 元為計算基準，依附表三{disability_term}給付比例計算。",
            f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base",
            amount_role="base",
            limit_scope="per_policy",
            aggregation_rule="cumulative_cap",
            conditions=disability_conditions,
            rate_min_percent=disability_min,
            rate_max_percent=disability_max,
        )
        for amount_key, entry_id, name, condition in (
            ("air_disability", "air-transport-accident-disability", f"空中大眾運輸工具意外{disability_term}保險金", "以乘客身分搭乘空中大眾運輸工具"),
            ("surface_disability", "surface-transport-accident-disability", f"水上或陸地大眾運輸工具意外{disability_term}保險金", "以乘客身分搭乘水上或陸地大眾運輸工具"),
            ("fire_disability", "public-building-fire-accident-disability", f"公共建築物火災意外{disability_term}保險金", "火災發生前已進入戲院、旅館或其他公共建築物"),
            ("elevator_disability", "elevator-accident-disability", f"電梯意外{disability_term}保險金", "因乘坐電梯發生意外傷害事故"),
        ):
            add_amount_entry(
                amount_key,
                entry_id,
                name,
                "benefit_base",
                "符合特定事故條件時，以 {amount:,} 元為額外計算基準，依附表三比例給付。",
                f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_policy",
                aggregation_rule="conditional_additive",
                conditions=[accident_180_condition, condition, "同時符合兩項以上大眾運輸工具事故時僅給付最高一項", "受附表一最高給付金額限制", hijack_condition],
                rate_min_percent=5,
                rate_max_percent=100,
            )

        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    version_characteristics = {
        "cancer_initial_waiting_days": 0,
        "cancer_reinstatement_waiting_days": (
            30 if has_reinstatement_waiting_period else 0
        ),
        "day_hospital_explicit": day_hospital_explicit,
        "disability_schedule_revision": schedule_revision,
    }
    if version is not None:
        version_characteristics.update(
            {
                "disability_terminology": disability_term,
                "cancer_classification": version["cancer_classification"],
                "missing_person_return_repayment_scope": version[
                    "missing_person_return_repayment_scope"
                ],
                "funeral_benefit_cap_reference": version[
                    "funeral_benefit_cap_reference"
                ],
            }
        )
        if version["source_conflicts"]:
            version_characteristics["source_conflicts"] = version["source_conflicts"]

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至十二；系統會依該計畫顯示壽險、癌症、住院與意外保障及金額。",
        "version_characteristics": version_characteristics,
        "plan_options": plan_options,
    }


def parse_fubon_golden_lohas_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_GOLDEN_LOHAS_COMBINED_PRODUCT_VERSIONS.get(product_id)
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    required_revisions = tuple(
        compact_table_text(signal) for signal in version["required_revision_signals"]
    )
    forbidden_revisions = tuple(
        compact_table_text(signal) for signal in version["forbidden_revision_signals"]
    )
    if (
        version["document_code"] not in text
        or any(signal not in compact_text for signal in required_revisions)
        or any(signal in compact_text for signal in forbidden_revisions)
    ):
        return None

    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", "保險範圍:完全失能保險金的給付", "第十三條"),
        ("major_disease", "保險範圍:重大疾病保險金的給付", "第十八條"),
        ("mild_cancer", "保險範圍:癌症(輕度)保險金的給付", "第十九條"),
        ("hospital", "保險範圍:住院醫療保險金的給付", "第二十條"),
        ("hospital_icu", "保險範圍:加護病房住院醫療保險金的給付", "第二十一條"),
        ("burn_hospital", "保險範圍:燒燙傷中心住院醫療保險金的給付", "第二十二條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十五條"),
        ("accident_hospital", "保險範圍:意外傷害住院醫療保險金的給付", "第二十六條"),
        ("accident_icu", "保險範圍:意外傷害加護病房住院醫療保險金的給付", "第二十七條"),
        ("accident_outpatient", "保險範圍:意外傷害門診手術醫療保險金的給付", "第二十八條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十九條"),
        ("transport_death", "保險範圍:大眾運輸工具意外身故保險金或喪葬費用保險金的給付", "第三十條"),
        ("fire_death", "保險範圍:公共建築物火災意外身故保險金或喪葬費用保險金的給付", "第三十一條"),
        ("elevator_death", "保險範圍:電梯意外身故保險金或喪葬費用保險金的給付", "第三十二條"),
        ("overseas_death", "保險範圍:海外意外身故保險金或喪葬費用保險金的給付", "第三十三條"),
        ("accident_disability", "保險範圍:意外失能保險金的給付", "第三十四條"),
        ("transport_disability", "保險範圍:大眾運輸工具意外失能保險金的給付", "第三十五條"),
        ("fire_disability", "保險範圍:公共建築物火災意外失能保險金的給付", "第三十六條"),
        ("elevator_disability", "保險範圍:電梯意外失能保險金的給付", "第三十七條"),
        ("overseas_disability", "保險範圍:海外意外失能保險金的給付", "第三十八條"),
        ("accident_limit", "保險範圍:意外身故保險金及意外失能保險金給付的限制", "第三十九條"),
    ]

    def clause_start(heading: str, article: str) -> int:
        match = re.search(
            rf"【{re.escape(heading)}\s*】.{{0,120}}?{re.escape(article)}",
            text,
        )
        return match.start() if match else -1

    article_starts = {
        key: clause_start(heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    required_clause_signals = (
        "富邦人壽金樂活傷害暨健康一年定期保險",
        "本契約保障內容分二個計畫別",
        "於本契約有效期間內,本公司不受理其變更",
        "本契約生效日起持續有效三十天之期間",
        "如為癌症(輕度)或重大疾病,則係指自本契約生效日起持續有效九十天之期間",
        "本契約續保時,不受等待期間的限制",
        "每次「海外停留保障期間」最高天數以出境日起算一百八十天為限",
        "不包含全民健康保險法第五十一條所稱之日間住院及精神衛生法第三十五條所稱之日間留院",
        "本公司給付重大疾病保險金之責任,以一次為限",
        "本公司給付癌症(輕度)保險金之責任,以一次為限",
        "同一次住院之住院醫療保險金實際給付住院日數,最高以三百六十五日為限",
        "每一保單年度之住院醫療保險金之實際給付住院日數,最高僅以九十日為限",
        "同一次住院之加護病房住院醫療保險金實際給付住院日數,最高以三十日為限",
        "同一次住院之燒燙傷中心住院醫療保險金實際給付住院日數,最高以三十日為限",
        "自意外傷害事故發生之日起屆滿十五日仍生存者",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同時符合二項以上大眾運輸工具意外傷害事故者,本公司之保險責任以給付最高一項為限",
        "本公司依本條約定給付海外意外身故保險金或喪葬費用保險金時,不另行給付第三十條至第三十二條之各項保險金",
        "本公司依本條約定給付海外意外失能保險金時,不另行給付第三十五條至第三十七條之各項保險金",
    )
    if not all(
        compact_table_text(signal) in compact_text
        for signal in required_clause_signals
    ):
        return None

    table_start = text.find("附表一:")
    table_end = text.find("附表二", table_start + 1)
    if text.count("附表一:") != 1 or table_start < 0 or table_end <= table_start:
        return None
    table_text = compact_table_text(text[table_start:table_end])
    table_signals = (
        "計畫別保險金項目計畫一計畫二",
        "身故保險金或喪葬費用保險金50萬100萬",
        "完全失能保險金50萬100萬",
        "重大疾病保險金10萬20萬",
        "癌症(輕度)保險金0.5萬1萬",
        "重大燒燙傷保險金40萬40萬",
        "意外身故保險金或喪葬費用保險金100萬100萬",
        "海外意外身故保險金或喪葬費用保險金100萬100萬",
        "「空中大眾運輸工具」200萬200萬",
        "「水上大眾運輸工具」或「陸地大眾運輸工具」100萬100萬",
        "公共建築物火災意外身故保險金或喪葬費用保險金100萬100萬",
        "電梯意外身故保險金或喪葬費用保險金100萬100萬",
        "意外失能保險金致成失能等級之一100萬乘以附表三所列給付比例100萬乘以附表三所列給付比例最高給付金額100萬100萬",
        "海外意外失能保險金致成失能等級之一100萬乘以附表三所列給付比例100萬乘以附表三所列給付比例最高給付金額100萬100萬",
        "大眾運輸工具意外失能保險金「空中大眾運輸工具」致成失能等級之一200萬乘以附表三所列給付比例200萬乘以附表三所列給付比例最高給付金額200萬200萬",
        "「水上大眾運輸工具」或「陸地大眾運輸工具」致成失能等級之一100萬乘以附表三所列給付比例100萬乘以附表三所列給付比例最高給付金額100萬100萬",
        "公共建築物火災意外失能保險金致成失能等級之一100萬乘以附表三所列給付比例100萬乘以附表三所列給付比例最高給付金額100萬100萬",
        "電梯意外失能保險金致成失能等級之一100萬乘以附表三所列給付比例100萬乘以附表三所列給付比例最高給付金額100萬100萬",
        "意外傷害住院醫療保險金1000元/日1000元/日",
        "意外傷害加護病房住院醫療保險金1000元/日1000元/日",
        "意外傷害門診手術醫療保險金1000元/次1000元/次",
        "住院醫療保險金1000元/日1000元/日",
        "加護病房住院醫療保險金2500元/日2500元/日",
        "燒燙傷中心住院醫療保險金3000元/日3000元/日",
    )
    if not all(compact_table_text(signal) in table_text for signal in table_signals):
        return None

    schedule_revision = version["disability_schedule_revision"]
    has_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    has_109_schedule = has_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    if schedule_revision == "104-revised-79-items":
        if not has_104_schedule or has_109_schedule:
            return None
        schedule_condition = "本版本採 104 年修正版附表三，共 79 項失能程度"
    elif schedule_revision == "109-revised-80-items":
        if not has_109_schedule:
            return None
        schedule_condition = "本版本採 109 年修正版附表三，共 80 項失能程度"
    else:
        return None

    article_pages = {
        key: source_page(text, start) for key, start in article_starts.items()
    }
    fallback_pages = {
        "policy_death": 6,
        "total_disability": 6,
        "major_disease": 7,
        "mild_cancer": 7,
        "hospital": 7,
        "hospital_icu": 7,
        "burn_hospital": 7,
        "major_burn": 9,
        "accident_hospital": 9,
        "accident_icu": 9,
        "accident_outpatient": 9,
        "accident_death": 9,
        "transport_death": 10,
        "fire_death": 10,
        "elevator_death": 10,
        "overseas_death": 10,
        "accident_disability": 10,
        "transport_disability": 11,
        "fire_disability": 11,
        "elevator_disability": 11,
        "overseas_disability": 11,
        "accident_limit": 11,
    }
    article_pages = {
        key: article_pages[key] or fallback_pages[key]
        for key in article_pages
    }
    table_page = source_page(text, table_start) or 15
    table_ref = f"附表一，第 {table_page} 頁"
    plan_labels = ("計畫一", "計畫二")
    amounts = {
        "policy_death": (500_000, 1_000_000),
        "total_disability": (500_000, 1_000_000),
        "major_disease": (100_000, 200_000),
        "mild_cancer": (5_000, 10_000),
        "major_burn": (400_000, 400_000),
        "accident_death": (1_000_000, 1_000_000),
        "overseas_death": (1_000_000, 1_000_000),
        "air_death": (2_000_000, 2_000_000),
        "surface_death": (1_000_000, 1_000_000),
        "fire_death": (1_000_000, 1_000_000),
        "elevator_death": (1_000_000, 1_000_000),
        "accident_disability": (1_000_000, 1_000_000),
        "overseas_disability": (1_000_000, 1_000_000),
        "air_disability": (2_000_000, 2_000_000),
        "surface_disability": (1_000_000, 1_000_000),
        "fire_disability": (1_000_000, 1_000_000),
        "elevator_disability": (1_000_000, 1_000_000),
    }
    disease_condition = "疾病須於初次生效持續有效 30 日後發生；復效日起適用；續保不受等待期限制"
    major_disease_condition = "重大疾病須於初次生效持續有效 90 日後發生；復效日起適用；續保不受等待期限制"
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    overseas_condition = "須在海外停留保障期間內；每次離境起最長 180 日"
    transport_highest_condition = "同時符合空中、水上或陸地大眾運輸事故時，僅給付最高一項運輸保障"
    funeral_condition = "特定身分依法改為喪葬費用保險金並受法定總額限制"

    plan_options = []
    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add_amount(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            note: str,
            source_ref: str,
            *,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(amount=amount, plan=plan_label),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                )
            )

        add_amount(
            "policy_death",
            "policy-death",
            "身故保險金或喪葬費用保險金",
            "policy_total",
            "依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十二條，第 {article_pages['policy_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", funeral_condition],
        )
        add_amount(
            "total_disability",
            "total-disability",
            "完全失能保險金",
            "policy_total",
            "符合附表二完全失能程度之一，依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十三條及附表二，第 {article_pages['total_disability']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", "與身故保險金同時或先後符合時僅給付一項"],
        )
        add_amount(
            "major_disease",
            "major-disease",
            "重大疾病保險金",
            "policy_total",
            "符合第二條重大疾病定義時，依{plan}給付 {amount:,} 元。",
            f"保單條款第二條及第十八條，第 2-{article_pages['major_disease']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[major_disease_condition, "本契約含續保期間合計限給付一次"],
        )
        add_amount(
            "mild_cancer",
            "mild-cancer",
            "癌症（輕度）保險金",
            "policy_total",
            "符合第二條癌症（輕度）定義時，依{plan}給付 {amount:,} 元。",
            f"保單條款第二條及第十九條，第 2-{article_pages['mild_cancer']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[major_disease_condition, "本契約含續保期間合計限給付一次"],
        )

        hospital_conditions = [
            disease_condition,
            "含入院及出院當日",
            "同一次住院最高 365 日；精神疾病每一保單年度最高 90 日",
            "同一疾病、傷害或併發症於出院後 14 日內再次住院，視為同一次住院",
            "日間住院及精神衛生法所稱日間留院不在住院定義內",
        ]
        entries.extend(
            [
                coverage_entry(
                    "hospital-daily",
                    "住院醫療保險金",
                    1_000,
                    "daily_total",
                    "因疾病或傷害住院，每日給付 1,000 元。",
                    f"保單條款第二十條，第 {article_pages['hospital']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=hospital_conditions,
                ),
                coverage_entry(
                    "hospital-icu-daily",
                    "加護病房住院醫療保險金",
                    2_500,
                    "daily_total",
                    "入住加護病房時，除住院醫療保險金外，每日另給付 2,500 元。",
                    f"保單條款第二十一條，第 {article_pages['hospital_icu']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=[disease_condition, "同一次住院最高 30 日", "同日轉出後再轉入不重複計算"],
                ),
                coverage_entry(
                    "burn-center-hospital-daily",
                    "燒燙傷中心住院醫療保險金",
                    3_000,
                    "daily_total",
                    "入住燒燙傷中心時，除住院醫療保險金外，每日另給付 3,000 元。",
                    f"保單條款第二十二條，第 {article_pages['burn_hospital']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=["同一次住院最高 30 日", "燒燙傷中心設於加護中心內時不另給付加護病房日額", "同日轉出後再轉入不重複計算"],
                ),
            ]
        )
        add_amount(
            "major_burn",
            "major-burn",
            "重大燒燙傷保險金",
            "per_event",
            "符合條款重大燒燙傷範圍，依{plan}給付 {amount:,} 元。",
            f"保單條款第二十五條及附表四，第 {article_pages['major_burn']} 頁起；{table_ref}",
            conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存"],
        )
        entries.extend(
            [
                coverage_entry(
                    "accident-hospital-daily",
                    "意外傷害住院醫療保險金",
                    1_000,
                    "daily_total",
                    "因意外傷害住院，每日給付 1,000 元。",
                    f"保單條款第二十六條，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=[accident_180_condition, "含入院及出院當日", "同一次意外傷害最高 365 日"],
                ),
                coverage_entry(
                    "fracture-without-hospitalization",
                    "骨折未住院醫療保險金",
                    1_000,
                    "benefit_base",
                    "未住院部分按骨折表日數乘以 1,000 元日額的二分之一計算。",
                    f"保單條款第二十六條骨折表，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="table_multiplier",
                    amount_role="reference",
                    limit_scope="per_injury",
                    aggregation_rule="highest",
                    multiplier=0.5,
                    conditions=["完全骨折表列 14 至 60 日", "不完全骨折按完全骨折日數二分之一、骨骼龜裂按四分之一", "同時多處骨折僅給付較高一項"],
                ),
                coverage_entry(
                    "accident-icu-daily",
                    "意外傷害加護病房住院醫療保險金",
                    1_000,
                    "daily_total",
                    "入住加護病房時，除意外傷害住院給付外，每日另給付 1,000 元。",
                    f"保單條款第二十七條，第 {article_pages['accident_icu']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=[accident_180_condition, "受同一次意外傷害住院 365 日上限限制", "同日轉出後再轉入不重複計算"],
                ),
                coverage_entry(
                    "accident-outpatient-surgery",
                    "意外傷害門診手術醫療保險金",
                    1_000,
                    "per_event",
                    "每次意外傷害符合條款的門診手術給付 1,000 元。",
                    f"保單條款第二十八條，第 {article_pages['accident_outpatient']} 頁；{table_ref}",
                    calculation_basis="fixed_amount",
                    amount_role="payout",
                    limit_scope="per_injury",
                    conditions=["每次意外傷害限申領一次"],
                ),
            ]
        )

        add_amount(
            "accident_death",
            "accident-death",
            "意外身故保險金或喪葬費用保險金",
            "policy_total",
            "一般意外身故依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第二十九條，第 {article_pages['accident_death']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[accident_180_condition, funeral_condition, "給付後本契約終止"],
        )
        death_specs = (
            ("air_death", "air-transport-accident-death", "空中大眾運輸工具意外身故保險金", "以乘客身分搭乘空中大眾運輸工具", "transport_death"),
            ("surface_death", "surface-transport-accident-death", "水上或陸地大眾運輸工具意外身故保險金", "以乘客身分搭乘水上或陸地大眾運輸工具", "transport_death"),
            ("fire_death", "public-building-fire-accident-death", "公共建築物火災意外身故保險金", "火災發生前已進入戲院、旅館或其他公共建築物", "fire_death"),
            ("elevator_death", "elevator-accident-death", "電梯意外身故保險金", "因乘坐電梯發生意外傷害事故", "elevator_death"),
        )
        for amount_key, entry_id, name, condition, page_key in death_specs:
            conditions = [accident_180_condition, condition, "本項在一般意外身故保障之外另行給付", funeral_condition]
            if page_key == "transport_death":
                conditions.append(transport_highest_condition)
            add_amount(
                amount_key,
                entry_id,
                name,
                "policy_total",
                "符合特定事故條件時，依{plan}額外給付 {amount:,} 元。",
                f"保單條款第{'三十' if page_key == 'transport_death' else '三十一' if page_key == 'fire_death' else '三十二'}條，第 {article_pages[page_key]} 頁；{table_ref}",
                limit_scope="per_policy",
                aggregation_rule="conditional_additive",
                conditions=conditions,
            )
        add_amount(
            "overseas_death",
            "overseas-accident-death",
            "海外意外身故保險金",
            "policy_total",
            "海外停留保障期間內意外身故，依{plan}額外給付 {amount:,} 元。",
            f"保單條款第三十三條，第 {article_pages['overseas_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            aggregation_rule="choose_one",
            conditions=[accident_180_condition, overseas_condition, "本項在一般意外身故保障之外另行給付", "給付本項時不另給付大眾運輸、公共建築物火災或電梯意外身故保險金", funeral_condition],
        )

        disability_common = [
            accident_180_condition,
            schedule_condition,
            "同一事故多項及不同事故累計受附表一最高給付金額限制",
            "第 1 級失能給付後本契約終止",
            "同一事故失能後身故，兩者合計最高為對應意外身故保險金",
        ]
        add_amount(
            "accident_disability",
            "accident-disability",
            "意外失能保險金",
            "benefit_base",
            "以 {amount:,} 元為基準，依附表三失能等級 5% 至 100% 比例計算。",
            f"保單條款第三十四、三十九條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base",
            amount_role="base",
            limit_scope="per_policy",
            aggregation_rule="cumulative_cap",
            conditions=disability_common,
            rate_min_percent=5,
            rate_max_percent=100,
        )
        disability_specs = (
            ("air_disability", "air-transport-accident-disability", "空中大眾運輸工具意外失能保險金", "以乘客身分搭乘空中大眾運輸工具", "transport_disability"),
            ("surface_disability", "surface-transport-accident-disability", "水上或陸地大眾運輸工具意外失能保險金", "以乘客身分搭乘水上或陸地大眾運輸工具", "transport_disability"),
            ("fire_disability", "public-building-fire-accident-disability", "公共建築物火災意外失能保險金", "火災發生前已進入戲院、旅館或其他公共建築物", "fire_disability"),
            ("elevator_disability", "elevator-accident-disability", "電梯意外失能保險金", "因乘坐電梯發生意外傷害事故", "elevator_disability"),
        )
        for amount_key, entry_id, name, condition, page_key in disability_specs:
            conditions = [*disability_common, condition, "本項在一般意外失能保障之外另行給付"]
            if page_key == "transport_disability":
                conditions.append(transport_highest_condition)
            add_amount(
                amount_key,
                entry_id,
                name,
                "benefit_base",
                "符合特定事故條件時，以 {amount:,} 元為額外計算基準，依附表三比例給付。",
                f"保單條款第{'三十五' if page_key == 'transport_disability' else '三十六' if page_key == 'fire_disability' else '三十七'}條及附表三，第 {article_pages[page_key]} 頁起；{table_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_policy",
                aggregation_rule="conditional_additive",
                conditions=conditions,
                rate_min_percent=5,
                rate_max_percent=100,
            )
        add_amount(
            "overseas_disability",
            "overseas-accident-disability",
            "海外意外失能保險金",
            "benefit_base",
            "海外停留保障期間內意外失能，以 {amount:,} 元為額外計算基準，依附表三比例給付。",
            f"保單條款第三十八、三十九條及附表三，第 {article_pages['overseas_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base",
            amount_role="base",
            limit_scope="per_policy",
            aggregation_rule="choose_one",
            conditions=[*disability_common, overseas_condition, "本項在一般意外失能保障之外另行給付", "給付本項時不另給付大眾運輸、公共建築物火災或電梯意外失能保險金"],
            rate_min_percent=5,
            rate_max_percent=100,
        )
        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一或計畫二；系統會直接顯示該計畫的壽險、重大疾病、癌症、住院、燒燙傷與意外保障及金額，不需再輸入單位數。",
        "version_characteristics": {
            "disease_initial_waiting_days": 30,
            "disease_reinstatement_waiting_days": 0,
            "major_disease_initial_waiting_days": 90,
            "major_disease_reinstatement_waiting_days": 0,
            "mild_cancer_initial_waiting_days": 90,
            "mild_cancer_reinstatement_waiting_days": 0,
            "day_hospital_explicit": False,
            "day_hospital_excluded": True,
            "overseas_stay_limit_days": 180,
            "disability_schedule_revision": schedule_revision,
        },
        "plan_options": plan_options,
    }


def is_fubon_new_lohas_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id in FUBON_NEW_LOHAS_PRODUCT_VERSIONS
        or FUBON_NEW_LOHAS_FILE_PATTERN.fullmatch(file_name) is not None
    ):
        return True
    text = normalize_terms_text(str(document.get("text") or ""))
    return (
        "富邦人壽新樂活人生傷害暨健康一年定期保險" in text
        or any(
            version["document_code"] in text
            for version in FUBON_NEW_LOHAS_PRODUCT_VERSIONS.values()
        )
    )


def parse_fubon_new_lohas_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_NEW_LOHAS_PRODUCT_VERSIONS.get(product_id)
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
        or document.get("page_count") != 25
        or document.get("pages_parsed") != 25
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    document_code = version["document_code"]
    required_revision_signals = tuple(
        compact_table_text(signal) for signal in version["required_revision_signals"]
    )
    forbidden_revision_signals = tuple(
        compact_table_text(signal) for signal in version["forbidden_revision_signals"]
    )
    required_feature_signals = tuple(
        compact_table_text(signal) for signal in version["required_feature_signals"]
    )
    forbidden_feature_signals = tuple(
        compact_table_text(signal) for signal in version["forbidden_feature_signals"]
    )
    if (
        text.count("富邦人壽新樂活人生傷害暨健康一年定期保險") != 2
        or text.count(document_code) != 25
        or any(signal not in compact_text for signal in required_revision_signals)
        or any(signal in compact_text for signal in forbidden_revision_signals)
        or any(signal not in compact_text for signal in required_feature_signals)
        or any(signal in compact_text for signal in forbidden_feature_signals)
    ):
        return None

    page_markers: dict[int, re.Match[str]] = {}
    for page_number in range(1, 26):
        matches = list(
            re.finditer(
                rf"{re.escape(document_code)}\s+{page_number}\s*/\s*25\s+"
                r"商品代號\s*:\s*MGA1",
                text,
            )
        )
        if len(matches) != 1:
            return None
        page_markers[page_number] = matches[0]
    if [match.start() for match in page_markers.values()] != sorted(
        match.start() for match in page_markers.values()
    ):
        return None
    page_texts = {
        page_number: text[
            page_markers[page_number].start() : (
                page_markers[page_number + 1].start()
                if page_number < 25
                else len(text)
            )
        ]
        for page_number in range(1, 26)
    }
    required_page_signals = {
        1: ("內容摘要",),
        2: ("本契約保障內容分四個計畫別",),
        14: ("附表一", "計畫一", "計畫四"),
        15: ("意外傷害住院醫療保險金", "燒燙傷中心住院醫療保險金"),
        16: ("附表二:完全失能程度表",),
        17: ("附表三:失能程度表", "失能程度與保險金給付表"),
        21: ("註 15", "機能永久喪失及遺存各級障害"),
        22: ("上、下肢關節生理運動範圍一覽表",),
        23: ("附表四", "重大燒燙傷", "五官功能障礙表"),
        24: ("聽力喪失的認定", "鼻缺損"),
        25: ("附表五:短期費率表", "年繳短期費率表", "季繳之短期費率表"),
    }
    if any(
        compact_table_text(signal) not in compact_table_text(page_texts[page_number])
        for page_number, signals in required_page_signals.items()
        for signal in signals
    ):
        return None

    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", "保險範圍:完全失能保險金的給付", "第十三條"),
        ("major_illness", "保險範圍:重大傷病保險金的給付", "第十七條"),
        ("low_invasive_cancer", "保險範圍:低侵襲性癌症保險金的給付", "第十八條"),
        ("hospital", "保險範圍:住院醫療保險金的給付", "第十九條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十二條"),
        ("accident_hospital", "保險範圍:住院醫療保險金的給付", "第二十三條"),
        ("accident_outpatient", "保險範圍:意外傷害門診手術醫療保險金的給付", "第二十四條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十五條"),
        ("accident_disability", "保險範圍:意外失能保險金的給付", "第二十六條"),
        ("accident_limit", "意外身故保險金及意外失能保險金給付的限制", "第二十七條"),
    ]
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    required_clause_signals = (
        "富邦人壽新樂活人生傷害暨健康一年定期保險",
        "本契約保障內容分四個計畫別",
        "於本契約有效期間內,本公司不受理其變更",
        "自本契約生效日起持續有效三十日以後或復效日起所發生之疾病",
        "本契約續保時,不受三十日等待期間的限制",
        "自本契約生效日(或復效日)起持續有效九十天之期間",
        "因遭受意外傷害事故所致者,不受前述等待期間之限制",
        "本契約最高可續保至被保險人保險年齡七十五歲時之該保險期間屆滿",
        "本公司給付重大傷病保險金之責任,以一次為限",
        "本公司給付低侵襲性癌症保險金之責任,以一次為限",
        "同一次住院之一般住院醫療保險金實際給付住院日數,最高以三百六十五日為限",
        "每一保單年度之住院醫療保險金之實際給付住院日數,最高僅以九十日為限",
        "同一次住院之加護病房住院醫療保險金實際給付住院日數,最高以三十日為限",
        "同一次住院之燒燙傷中心住院醫療保險金實際給付住院日數,最高以三十日為限",
        "於出院後十四日內再次住院時,其各種保險金給付,均視為一次住院",
        "本契約有效期間屆滿後出院者,本公司就再次住院部分不予給付保險金",
        "不包含全民健康保險法第五十一條所稱之日間住院及精神衛生法第三十五條所稱之日間留院",
        "自意外傷害事故發生之日起屆滿十五日仍生存者",
        "但超過一百八十日繼續治療者,受益人若能證明被保險人之治療與該意外傷害事故具有因果關係者",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "意外傷害住院醫療保險金日額的二分之一,乘以下列骨折別所定日數給付",
        "如係不完全骨折,按完全骨折日數二分之一給付",
        "骨骼龜裂者按完全骨折日數四分之一給付",
        "如同時蒙受下列二項以上骨折時,僅給付一項較高等級的醫療保險金",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同時符合二項以上大眾運輸工具意外傷害事故者,本公司之保險責任以給付最高一項為限",
        "每次「海外停留保障期間」最高天數以出境日起算一百八十天為限",
        "被保險人申領本款保險金時,本公司不另行給付第二款至第四款之保險金",
        "失能如係附表三所列失能等級第一級者,本公司依本條約定給付各項意外失能保險金後,本契約之效力即行終止",
        "同一意外傷害事故致成失能後身故",
        "本公司之給付總金額合計最高以依第二十五條約定計算所應給付之保險金額為限",
    )
    if not all(
        compact_table_text(signal) in compact_text
        for signal in required_clause_signals
    ):
        return None
    repeated_limit_signals = (
        "同時符合二項以上大眾運輸工具意外傷害事故者,本公司之保險責任以給付最高一項為限",
        "被保險人申領本款保險金時,本公司不另行給付第二款至第四款之保險金",
    )
    if any(
        compact_text.count(compact_table_text(signal)) != 2
        for signal in repeated_limit_signals
    ):
        return None

    appendix_two_start = text.rfind("附表二:完全失能程度表")
    table_start = text.rfind("附表一", 0, appendix_two_start)
    if table_start < 0 or appendix_two_start <= table_start:
        return None
    table_segment = re.sub(
        r"MGA\d+\s+\d+\s*/\s*25\s+商品代號\s*:\s*MGA1",
        "",
        text[table_start:appendix_two_start],
    )
    table_text = compact_table_text(table_segment)
    if hashlib.sha256(table_text.encode("utf-8")).hexdigest() != FUBON_NEW_LOHAS_TABLE_SHA256:
        return None

    schedule_revision = version["disability_schedule_revision"]
    has_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    has_109_schedule = has_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    if schedule_revision == "104-revised-79-items":
        if not has_104_schedule or has_109_schedule:
            return None
        schedule_condition = "本版本採 104 年修正版附表三，共 79 項失能程度"
    elif schedule_revision == "109-revised-80-items":
        if not has_109_schedule:
            return None
        schedule_condition = "本版本採 109 年修正版附表三，共 80 項失能程度"
    else:
        return None

    article_pages = {
        key: source_page(text, start) for key, start in article_starts.items()
    }
    expected_article_pages = {
        "policy_death": 5,
        "total_disability": 5,
        "major_illness": 6,
        "low_invasive_cancer": 6,
        "hospital": 6,
        "major_burn": 8,
        "accident_hospital": 8,
        "accident_outpatient": 9,
        "accident_death": 9,
        "accident_disability": 9 if schedule_revision == "104-revised-79-items" else 10,
        "accident_limit": 10,
    }
    if article_pages != expected_article_pages:
        return None

    plan_labels = ("計畫一", "計畫二", "計畫三", "計畫四")
    amounts = {
        "policy_death": (500_000, 1_000_000, 2_000_000, 3_000_000),
        "total_disability": (500_000, 1_000_000, 2_000_000, 3_000_000),
        "major_illness": (100_000, 200_000, 400_000, 600_000),
        "low_invasive_cancer": (5_000, 10_000, 20_000, 30_000),
        "major_burn": (400_000, 400_000, 400_000, 800_000),
        "accident_death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "overseas_death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "air_death": (2_000_000, 2_000_000, 2_000_000, 4_000_000),
        "surface_death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "fire_death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "elevator_death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "accident_disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "overseas_disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "air_disability": (2_000_000, 2_000_000, 2_000_000, 4_000_000),
        "surface_disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "fire_disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "elevator_disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
        "accident_hospital": (500, 500, 500, 1_000),
        "accident_icu": (500, 500, 500, 1_000),
        "accident_outpatient": (500, 500, 500, 1_000),
        "hospital": (1_000, 1_000, 1_000, 2_000),
        "hospital_icu": (2_500, 2_500, 2_500, 5_000),
        "burn_hospital": (2_500, 2_500, 2_500, 5_000),
    }
    table_ref = "附表一，第 14-15 頁"
    disease_condition = "疾病須於初次生效持續有效 30 日後發生；復效日起發生者適用；續保不受 30 日等待期限制"
    major_condition = "須於初次生效或復效持續有效 90 日後確診；意外所致重大傷病及續保不受 90 日等待期限制"
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    overseas_condition = "須在海外停留保障期間內；每次離境起最長 180 日"
    transport_highest_condition = "同時符合空中、水上或陸地大眾運輸事故時，僅給付最高一項運輸保障"
    funeral_condition = "特定身分依法改為喪葬費用保險金並受法定總額限制"
    plan_options = []

    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            source_ref: str,
            *,
            note: str,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
            multiplier: float | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(plan=plan_label, amount=amount),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                    multiplier=multiplier,
                )
            )

        add("policy_death", "policy-death", "身故保險金或喪葬費用保險金", "policy_total", f"保單條款第十二條，第 5 頁；{table_ref}", note="依{plan}給付 {amount:,} 元後契約終止。", limit_scope="per_policy", conditions=["給付後本契約終止", funeral_condition])
        add("total_disability", "total-disability", "完全失能保險金", "policy_total", f"保單條款第十三條及附表二，第 5、16 頁；{table_ref}", note="符合附表二完全失能程度之一，依{plan}給付 {amount:,} 元後契約終止。", limit_scope="per_policy", conditions=["給付後本契約終止", "與身故保障同時或先後符合時僅給付一項"])
        add("major_illness", "major-illness", "重大傷病保險金", "policy_total", f"保單條款第二條及第十七條，第 2-6 頁；{table_ref}", note="符合重大傷病定義時，依{plan}給付 {amount:,} 元。", limit_scope="per_policy", conditions=[major_condition, "本契約含續保期間合計限給付一次"])
        add("low_invasive_cancer", "low-invasive-cancer", "低侵襲性癌症保險金", "policy_total", f"保單條款第二條及第十八條，第 2-6 頁；{table_ref}", note="符合低侵襲性癌症定義時，依{plan}給付 {amount:,} 元。", limit_scope="per_policy", conditions=[major_condition, "本契約含續保期間合計限給付一次"])

        hospital_specs = (
            ("hospital", "hospital-daily", "一般住院醫療保險金", "因疾病或傷害住院，每日給付 {amount:,} 元。", [disease_condition, "含入院及出院當日", "同一次住院最高 365 日；精神疾病每一保單年度最高 90 日", "同一疾病、傷害或併發症出院後 14 日內再次住院視為同一次住院；契約屆滿後再次住院不給付", "日間住院及日間留院不在住院定義內"], "separate"),
            ("hospital_icu", "hospital-icu-daily", "加護病房住院醫療保險金", "入住加護病房時，每日另給付 {amount:,} 元。", [disease_condition, "同一次住院最高 30 日", "同日轉出後再轉入不重複計算"], "conditional_additive"),
            ("burn_hospital", "burn-center-hospital-daily", "燒燙傷中心住院醫療保險金", "入住燒燙傷中心時，每日另給付 {amount:,} 元。", [disease_condition, "同一次住院最高 30 日", "燒燙傷中心設於加護中心內時不另給付加護病房日額", "同日轉出後再轉入不重複計算"], "conditional_additive"),
        )
        for amount_key, entry_id, name, note, conditions, aggregation_rule in hospital_specs:
            add(amount_key, entry_id, name, "daily_total", f"保單條款第十九條，第 6 頁；{table_ref}", note=note, calculation_basis="per_day", limit_scope="per_day", aggregation_rule=aggregation_rule, conditions=conditions)

        add("major_burn", "major-burn", "重大燒燙傷保險金", "per_event", f"保單條款第二十二條及附表四，第 8、23-24 頁；{table_ref}", note="符合重大燒燙傷範圍，依{plan}給付 {amount:,} 元。", conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存"])
        add("accident_hospital", "accident-hospital-daily", "意外傷害住院醫療保險金", "daily_total", f"保單條款第二十三條，第 8-9 頁；{table_ref}", note="因意外傷害住院，每日給付 {amount:,} 元。", calculation_basis="per_day", limit_scope="per_day", conditions=[accident_180_condition, "含入院及出院當日", "同一次意外傷害最高 365 日"])
        add("accident_hospital", "fracture-without-hospitalization", "骨折未住院醫療保險金", "benefit_base", f"保單條款第二十三條骨折表，第 8-9 頁；{table_ref}", note="未住院部分按骨折表日數乘以 {amount:,} 元日額的二分之一計算。", calculation_basis="table_multiplier", amount_role="reference", limit_scope="per_injury", aggregation_rule="highest", multiplier=0.5, conditions=["完全骨折表列 14 至 60 日", "不完全骨折按完全骨折日數二分之一、骨骼龜裂按四分之一", "同時多處骨折僅給付較高一項"])
        add("accident_icu", "accident-icu-daily", "意外傷害加護病房住院醫療保險金", "daily_total", f"保單條款第二十三條，第 8-9 頁；{table_ref}", note="入住加護病房時，每日另給付 {amount:,} 元。", calculation_basis="per_day", limit_scope="per_day", aggregation_rule="conditional_additive", conditions=[accident_180_condition, "同一次意外傷害最高 365 日", "同日轉出後再轉入不重複計算"])
        add("accident_outpatient", "accident-outpatient-surgery", "意外傷害門診手術醫療保險金", "per_event", f"保單條款第二十四條，第 9 頁；{table_ref}", note="每次意外傷害符合條款的門診手術給付 {amount:,} 元。", limit_scope="per_injury", conditions=[accident_180_condition, "每次意外傷害限申領一次"])

        add("accident_death", "accident-death", "一般意外身故保險金或喪葬費用保險金", "policy_total", f"保單條款第二十五、二十七條，第 9-10 頁；{table_ref}", note="一般意外身故依{plan}給付 {amount:,} 元。", limit_scope="per_policy", conditions=[accident_180_condition, funeral_condition, "給付後本契約終止"])
        death_specs = (
            ("air_death", "air-transport-accident-death", "空中大眾運輸工具意外身故保險金", "以乘客身分搭乘空中大眾運輸工具", "conditional_additive"),
            ("surface_death", "surface-transport-accident-death", "水上或陸地大眾運輸工具意外身故保險金", "以乘客身分搭乘水上或陸地大眾運輸工具", "conditional_additive"),
            ("fire_death", "public-building-fire-accident-death", "公共建築物火災意外身故保險金", "火災發生前已進入公共建築物", "conditional_additive"),
            ("elevator_death", "elevator-accident-death", "電梯意外身故保險金", "因乘坐電梯發生意外傷害事故", "conditional_additive"),
            ("overseas_death", "overseas-accident-death", "海外意外身故保險金", overseas_condition, "choose_one"),
        )
        for amount_key, entry_id, name, condition, aggregation_rule in death_specs:
            conditions = [accident_180_condition, condition, "本項在一般意外身故保障之外另行給付", funeral_condition]
            if amount_key in {"air_death", "surface_death"}:
                conditions.append(transport_highest_condition)
            if amount_key == "overseas_death":
                conditions.append("給付本項時不另給付大眾運輸、公共建築物火災或電梯意外身故保障")
            add(amount_key, entry_id, name, "policy_total", f"保單條款第二十五、二十七條，第 9-10 頁；{table_ref}", note="符合特定事故條件時，依{plan}額外給付 {amount:,} 元。", limit_scope="per_policy", aggregation_rule=aggregation_rule, conditions=conditions)

        disability_common = [accident_180_condition, schedule_condition, "同一事故多項及不同事故累計受附表一最高給付金額限制", "第 1 級失能給付後本契約終止", "同一事故失能後身故，兩者合計最高為對應意外身故保險金"]
        disability_specs = (
            ("accident_disability", "accident-disability", "一般意外失能保險金", "一般意外", "cumulative_cap"),
            ("air_disability", "air-transport-accident-disability", "空中大眾運輸工具意外失能保險金", "以乘客身分搭乘空中大眾運輸工具", "conditional_additive"),
            ("surface_disability", "surface-transport-accident-disability", "水上或陸地大眾運輸工具意外失能保險金", "以乘客身分搭乘水上或陸地大眾運輸工具", "conditional_additive"),
            ("fire_disability", "public-building-fire-accident-disability", "公共建築物火災意外失能保險金", "火災發生前已進入公共建築物", "conditional_additive"),
            ("elevator_disability", "elevator-accident-disability", "電梯意外失能保險金", "因乘坐電梯發生意外傷害事故", "conditional_additive"),
            ("overseas_disability", "overseas-accident-disability", "海外意外失能保險金", overseas_condition, "choose_one"),
        )
        for amount_key, entry_id, name, condition, aggregation_rule in disability_specs:
            conditions = [*disability_common, condition]
            if amount_key != "accident_disability":
                conditions.append("本項在一般意外失能保障之外另行給付")
            if amount_key in {"air_disability", "surface_disability"}:
                conditions.append(transport_highest_condition)
            if amount_key == "overseas_disability":
                conditions.append("給付本項時不另給付大眾運輸、公共建築物火災或電梯意外失能保障")
            add(amount_key, entry_id, name, "benefit_base", f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']}-22 頁；{table_ref}", note="以 {amount:,} 元為計算基準，依附表三失能等級 5% 至 100% 比例給付。", calculation_basis="percentage_of_base", amount_role="base", limit_scope="per_policy", aggregation_rule=aggregation_rule, conditions=conditions, rate_min_percent=5, rate_max_percent=100)

        if len(entries) != 24 or len({entry["id"] for entry in entries}) != 24:
            return None
        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至計畫四；系統會顯示該計畫的壽險、重大傷病、癌症、住院、燒燙傷與意外保障及金額，不需輸入單位數。",
        "version_characteristics": {
            "disease_initial_waiting_days": 30,
            "disease_reinstatement_waiting_days": 0,
            "major_disease_initial_waiting_days": 90,
            "major_disease_reinstatement_waiting_days": 90,
            "mild_cancer_initial_waiting_days": 90,
            "mild_cancer_reinstatement_waiting_days": 90,
            "maximum_renewal_age": 75,
            "day_hospital_explicit": False,
            "day_hospital_excluded": True,
            "overseas_stay_limit_days": 180,
            "disability_schedule_revision": schedule_revision,
            "reinstatement_notice_revision": version["reinstatement_notice_revision"],
            "missing_person_return_repayment_scope": version["missing_person_return_repayment_scope"],
            "funeral_benefit_cap_reference": version["funeral_benefit_cap_reference"],
        },
        "plan_options": plan_options,
    }


def parse_fubon_lohas_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in FUBON_LOHAS_COMBINED_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", "保險範圍:完全殘廢保險金的給付", "第十三條"),
        ("major_disease", "保險範圍:重大疾病保險金的給付", "第十七條"),
        ("hospital", "保險範圍:住院醫療保險金的給付", "第十八條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十一條"),
        ("accident_hospital", "保險範圍:住院醫療保險金的給付", "第二十二條"),
        ("accident_outpatient", "保險範圍:意外傷害門診手術醫療保險金的給付", "第二十三條"),
        ("accident_reimbursement", "保險範圍:意外傷害醫療保險金的給付", "第二十四條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十五條"),
        ("accident_disability", "保險範圍:意外殘廢保險金的給付", "第二十六條"),
        ("accident_limit", "意外身故保險金及意外殘廢保險金給付的限制", "第二十七條"),
    ]
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    required_clause_signals = (
        "富邦人壽樂活人生傷害暨健康一年定期保險",
        "本契約保障內容分八個計畫別",
        "於本契約有效期間內,本公司不受理其變更",
        "持續有效九十日以後開始發生",
        "但因意外傷害所致者,或本契約續保時,不受九十日等待期間之限制",
        "同時符合第十二條、第十三條或本條約定中之二項以上者",
        "同一保單年度同一次住院之一般住院醫療保險金實際給付住院日數,最高以三百六十五日為限",
        "同一保單年度同一次住院之加護病房保險金實際給付住院日數,最高以三十日為限",
        "每次事故給付日數最長以三十日為限",
        "自意外傷害事故發生之日起屆滿十五日仍生存",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同一次傷害的給付總額不得超過二萬元",
        "則每次意外傷害醫療保險金限額提高為二萬七仟元",
        "同時符合二項以上大眾運輸工具意外傷害事故者",
    )
    if not all(signal in text for signal in required_clause_signals):
        return None

    table_start = text.find("附表一:")
    table_end = text.find("附表二", table_start + 1)
    if table_start < 0 or table_end <= table_start:
        return None
    table_text = compact_table_text(text[table_start:table_end])
    table_signals = (
        "計畫一計畫二計畫三計畫四計畫五計畫六計畫七計畫八",
        "身故保險金或喪葬費用保險金無20萬20萬50萬無20萬20萬50萬",
        "完全殘廢保險金無20萬20萬50萬無20萬20萬50萬",
        "重大疾病保險金無20萬20萬50萬無20萬20萬50萬",
        "重大燒燙傷保險金40萬40萬80萬80萬40萬40萬80萬80萬",
        "一般意外身故保險金或喪葬費用保險金100萬100萬200萬200萬100萬100萬200萬200萬",
        "意外傷害醫療保險金2萬2萬2萬2萬無無無無",
        "意外傷害住院醫療保險金500元/日",
        "意外傷害加護病房住院醫療保險金500元/日",
        "意外傷害門診手術醫療保險金1000元/次",
        "一般住院醫療保險金1000元/日",
        "加護病房住院醫療保險金2000元/日",
        "燒燙傷中心住院醫療保險金3000元/日",
    )
    if not all(compact_table_text(signal) in table_text for signal in table_signals):
        return None

    plan_labels = (
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
    )
    amounts = {
        "policy_death": [0, 200_000, 200_000, 500_000, 0, 200_000, 200_000, 500_000],
        "total_disability": [0, 200_000, 200_000, 500_000, 0, 200_000, 200_000, 500_000],
        "major_disease": [0, 200_000, 200_000, 500_000, 0, 200_000, 200_000, 500_000],
        "major_burn": [400_000, 400_000, 800_000, 800_000, 400_000, 400_000, 800_000, 800_000],
        "accident_death": [1_000_000, 1_000_000, 2_000_000, 2_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000],
        "air_death": [0, 2_000_000, 4_000_000, 4_000_000, 0, 2_000_000, 4_000_000, 4_000_000],
        "surface_death": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "fire_death": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "elevator_death": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "accident_disability": [1_000_000, 1_000_000, 2_000_000, 2_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000],
        "air_disability": [0, 2_000_000, 4_000_000, 4_000_000, 0, 2_000_000, 4_000_000, 4_000_000],
        "surface_disability": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "fire_disability": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "elevator_disability": [0, 1_000_000, 2_000_000, 2_000_000, 0, 1_000_000, 2_000_000, 2_000_000],
        "accident_reimbursement": [20_000, 20_000, 20_000, 20_000, 0, 0, 0, 0],
    }

    article_pages = {
        key: source_page(text, start)
        for key, start in article_starts.items()
    }
    fallback_pages = {
        "policy_death": 5,
        "total_disability": 5,
        "major_disease": 6,
        "hospital": 7,
        "major_burn": 8,
        "accident_hospital": 9,
        "accident_outpatient": 9,
        "accident_reimbursement": 9,
        "accident_death": 10,
        "accident_disability": 11,
        "accident_limit": 12,
    }
    article_pages = {
        key: article_pages[key] or fallback_pages[key]
        for key in article_pages
    }
    table_page = source_page(text, table_start) or 16
    table_ref = f"附表一，第 {table_page}-{table_page + 1} 頁"
    day_hospital_explicit = "住院(含日間留院)診療" in text
    post_expiry_readmission_excluded = "本契約有效期間屆滿後出院者" in text
    revised_disability_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    disease_condition = "疾病須於初次生效持續有效 30 日後發生；復效後及續保不受 30 日等待期限制"
    major_disease_condition = (
        "初次生效或復效須持續有效 90 日後開始發生並經診斷；"
        "因意外傷害所致或續保不受 90 日等待期限制"
    )
    major_disease_definitions = (
        "條款所列七項重大疾病：心肌梗塞、冠狀動脈繞道手術、腦中風、"
        "慢性腎衰竭（尿毒症）、癌症、癱瘓、重大器官移植手術"
    )
    hospital_conditions = [
        disease_condition,
        "含入院及出院當日",
        "同一保單年度同一次住院最高 365 日",
        "同一疾病、傷害或併發症於出院後 14 日內在同一醫院再次住院，視為同一次住院",
    ]
    if day_hospital_explicit:
        hospital_conditions.append("本版本條款明列住院包含精神衛生法所稱日間留院")
    if post_expiry_readmission_excluded:
        hospital_conditions.append("於契約有效期間屆滿後出院者，再次住院部分不予給付")
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    hijack_condition = "以乘客身分搭乘大眾運輸工具遭劫持時，契約期滿後至完全脫離被劫持狀況前仍延續本項保障；不增加給付金額"

    plan_options = []
    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add_amount_entry(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            note: str,
            source_ref: str,
            *,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
            amount_tiers: list[dict[str, Any]] | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            if not amount:
                return
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(amount=amount, plan=plan_label),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                    amount_tiers=amount_tiers,
                )
            )

        add_amount_entry(
            "policy_death",
            "policy-death",
            "身故保險金或喪葬費用保險金",
            "policy_total",
            "依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十二條，第 {article_pages['policy_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", "特定身分依法改為喪葬費用保險金並受法定總額限制"],
        )
        add_amount_entry(
            "total_disability",
            "total-disability",
            "完全殘廢保險金",
            "policy_total",
            "符合附表二完全殘廢程度之一，依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十三條及附表二，第 {article_pages['total_disability']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止"],
        )
        add_amount_entry(
            "major_disease",
            "major-disease",
            "重大疾病保險金",
            "policy_total",
            "符合條款重大疾病定義時，依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第二條及第十七條，第 2-{article_pages['major_disease']} 頁；{table_ref}",
            limit_scope="per_policy",
            aggregation_rule="highest",
            conditions=[major_disease_condition, major_disease_definitions, "同時符合身故、完全殘廢或重大疾病二項以上時僅給付一項", "給付後本契約終止"],
        )
        entries.extend(
            [
                coverage_entry(
                    "hospital-daily",
                    "一般住院醫療保險金",
                    1_000,
                    "daily_total",
                    "因疾病或傷害住院，每日給付 1,000 元。",
                    f"保單條款第十八條，第 {article_pages['hospital']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=hospital_conditions,
                ),
                coverage_entry(
                    "hospital-icu-daily",
                    "加護病房住院醫療保險金",
                    2_000,
                    "daily_total",
                    "入住加護病房時，除一般住院給付外，每日另給付 2,000 元。",
                    f"保單條款第十八條，第 {article_pages['hospital']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=[disease_condition, "同一保單年度同一次住院最高 30 日", "同日轉出後再轉入不重複計算", "入住燒燙傷中心且位於加護病房內時不重複給付本項"],
                ),
                coverage_entry(
                    "burn-center-hospital-daily",
                    "燒燙傷中心住院醫療保險金",
                    3_000,
                    "daily_total",
                    "入住燒燙傷中心時，除一般住院給付外，每日另給付 3,000 元。",
                    f"保單條款第十八條，第 {article_pages['hospital']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=["每次事故最高 30 日", "燒燙傷中心設於加護病房內時不另給付一般或意外加護病房日額", "同日轉出後再轉入不重複計算"],
                ),
            ]
        )
        add_amount_entry(
            "major_burn",
            "major-burn",
            "重大燒燙傷保險金",
            "per_event",
            "符合條款重大燒燙傷範圍，依{plan}給付 {amount:,} 元。",
            f"保單條款第二十一條及附表四，第 {article_pages['major_burn']} 頁起；{table_ref}",
            conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存", hijack_condition],
        )
        entries.extend(
            [
                coverage_entry(
                    "accident-hospital-daily",
                    "意外傷害住院醫療保險金",
                    500,
                    "daily_total",
                    "因意外傷害住院，每日給付 500 元。",
                    f"保單條款第二十二條，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=[accident_180_condition, "含入院及出院當日", "同一次意外傷害最高 365 日"],
                ),
                coverage_entry(
                    "fracture-without-hospitalization",
                    "骨折未住院醫療保險金",
                    500,
                    "benefit_base",
                    "未住院部分按骨折表日數乘以 500 元日額的二分之一計算。",
                    f"保單條款第二十二條骨折表，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="table_multiplier",
                    amount_role="reference",
                    limit_scope="per_injury",
                    aggregation_rule="highest",
                    multiplier=0.5,
                    conditions=["完全骨折表列 14 至 60 日", "不完全骨折按完全骨折日數二分之一、骨骼龜裂按四分之一", "同時多處骨折僅給付較高一項"],
                ),
                coverage_entry(
                    "accident-icu-daily",
                    "意外傷害加護病房住院醫療保險金",
                    500,
                    "daily_total",
                    "入住加護病房時，除意外傷害住院給付外，每日另給付 500 元。",
                    f"保單條款第二十二條，第 {article_pages['accident_hospital']} 頁起；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=[accident_180_condition, "受同一次意外傷害住院 365 日上限限制", "同日轉出後再轉入不重複計算"],
                ),
                coverage_entry(
                    "accident-outpatient-surgery",
                    "意外傷害門診手術醫療保險金",
                    1_000,
                    "per_event",
                    "每次意外傷害符合條款的門診手術給付 1,000 元。",
                    f"保單條款第二十三條，第 {article_pages['accident_outpatient']} 頁；{table_ref}",
                    calculation_basis="fixed_amount",
                    amount_role="payout",
                    limit_scope="per_injury",
                    conditions=["每次意外傷害限申領一次"],
                ),
            ]
        )
        reimbursement_amount = amounts["accident_reimbursement"][index]
        add_amount_entry(
            "accident_reimbursement",
            "accident-medical-reimbursement",
            "意外傷害醫療保險金",
            "per_injury_limit",
            "超過全民健康保險給付部分實支實付，一般限額 {amount:,} 元。",
            f"保單條款第二十四條及第二十九條，第 {article_pages['accident_reimbursement']} 頁起；{table_ref}",
            calculation_basis="reimbursement_with_cap",
            amount_role="limit",
            limit_scope="per_injury",
            conditions=[accident_180_condition, "每次意外傷害一般限額 20,000 元；以全民健康保險身分接受治療時提高為 27,000 元", "申領須檢附醫療費用收據正本"],
            amount_tiers=(
                [
                    {"label": "一般限額", "amount": reimbursement_amount},
                    {"label": "以全民健康保險身分接受治療", "amount": 27_000},
                ]
                if reimbursement_amount
                else None
            ),
        )
        add_amount_entry(
            "accident_death",
            "accident-death",
            "一般意外身故保險金或喪葬費用保險金",
            "policy_total",
            "一般意外身故依{plan}給付 {amount:,} 元。",
            f"保單條款第二十五條，第 {article_pages['accident_death']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[accident_180_condition, "未滿 15 足歲者身故給付自滿 15 足歲起生效", "給付後本契約終止", hijack_condition],
        )
        for amount_key, entry_id, name, condition in (
            ("air_death", "air-transport-accident-death", "空中大眾運輸工具意外身故保險金", "以乘客身分搭乘空中大眾運輸工具"),
            ("surface_death", "surface-transport-accident-death", "水上或陸地大眾運輸工具意外身故保險金", "以乘客身分搭乘水上或陸地大眾運輸工具"),
            ("fire_death", "public-building-fire-accident-death", "公共建築物火災意外身故保險金", "火災發生前已進入戲院、旅館或其他公共建築物"),
            ("elevator_death", "elevator-accident-death", "電梯意外身故保險金", "因乘坐電梯發生意外傷害事故"),
        ):
            add_amount_entry(
                amount_key,
                entry_id,
                name,
                "policy_total",
                "符合特定事故條件時，除一般意外身故保險金外另給付 {amount:,} 元。",
                f"保單條款第二十五條，第 {article_pages['accident_death']} 頁起；{table_ref}",
                limit_scope="per_policy",
                aggregation_rule="conditional_additive",
                conditions=[accident_180_condition, condition, "同時符合兩項以上大眾運輸工具事故時僅給付最高一項", hijack_condition],
            )

        disability_conditions = [
            accident_180_condition,
            "依附表三殘廢等級 5% 至 100% 比例計算",
            "同一事故多項及不同事故累計受附表一最高給付金額限制",
            "合併既有殘廢時須扣除視同已給付部分",
            "同一事故殘廢後身故時，依第二十七條計算差額",
            hijack_condition,
        ]
        if revised_disability_schedule:
            disability_conditions.append("本版本採 104 年修正版附表三，共 79 項殘廢程度")
        add_amount_entry(
            "accident_disability",
            "accident-disability",
            "一般意外殘廢保險金",
            "benefit_base",
            "以 {amount:,} 元為計算基準，依附表三殘廢給付比例計算。",
            f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base",
            amount_role="base",
            limit_scope="per_policy",
            aggregation_rule="cumulative_cap",
            conditions=disability_conditions,
            rate_min_percent=5,
            rate_max_percent=100,
        )
        for amount_key, entry_id, name, condition in (
            ("air_disability", "air-transport-accident-disability", "空中大眾運輸工具意外殘廢保險金", "以乘客身分搭乘空中大眾運輸工具"),
            ("surface_disability", "surface-transport-accident-disability", "水上或陸地大眾運輸工具意外殘廢保險金", "以乘客身分搭乘水上或陸地大眾運輸工具"),
            ("fire_disability", "public-building-fire-accident-disability", "公共建築物火災意外殘廢保險金", "火災發生前已進入戲院、旅館或其他公共建築物"),
            ("elevator_disability", "elevator-accident-disability", "電梯意外殘廢保險金", "因乘坐電梯發生意外傷害事故"),
        ):
            add_amount_entry(
                amount_key,
                entry_id,
                name,
                "benefit_base",
                "符合特定事故條件時，以 {amount:,} 元為額外計算基準，依附表三比例給付。",
                f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_policy",
                aggregation_rule="conditional_additive",
                conditions=[accident_180_condition, condition, "同時符合兩項以上大眾運輸工具事故時僅給付最高一項", "受附表一最高給付金額限制", hijack_condition],
                rate_min_percent=5,
                rate_max_percent=100,
            )

        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至八；系統會直接顯示該計畫的壽險、重大疾病、住院、燒燙傷與意外保障及金額，不需再輸入單位數。",
        "version_characteristics": {
            "disease_initial_waiting_days": 30,
            "major_disease_initial_waiting_days": 90,
            "major_disease_reinstatement_waiting_days": 90,
            "day_hospital_explicit": day_hospital_explicit,
            "post_expiry_readmission_excluded": post_expiry_readmission_excluded,
            "disability_schedule_revision": (
                "104-revised-71-items"
                if revised_disability_schedule
                else "original-67-items"
            ),
        },
        "plan_options": plan_options,
    }


def parse_fubon_child_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in FUBON_CHILD_COMBINED_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    required_signals = (
        "富幼保傷害暨健康一年定期保險",
        "持續有效三十日以後",
        "每日一仟元",
        "五十萬元之癌症身故保險金",
        "四十萬元之重大燒燙傷保險金",
        "二仟元之金額",
        "五萬四仟元",
        "一佰萬元意外身故保險金",
    )
    disability_term = (
        "失能"
        if "【保險範圍:意外失能保險金的給付】" in text
        else "殘廢"
    )
    if not all(signal in text for signal in required_signals) or not any(
        signal in text
        for signal in ("附表二所列殘廢程度", "附表二所列失能程度")
    ):
        return None

    cancer_start = find_fubon_clause_start(
        text, "保險範圍:癌症保險金的給付", "第十二條"
    )
    article_13_start = find_fubon_clause_start(
        text, "保險範圍:住院醫療保險金的給付", "第十三條"
    )
    article_16_start = find_fubon_clause_start(
        text, "保險範圍:重大燒燙傷保險金的給付", "第十六條"
    )
    article_17_start = find_fubon_clause_start(
        text, "保險範圍:住院醫療保險金的給付", "第十七條"
    )
    article_18_start = find_fubon_clause_start(
        text, "保險範圍:意外傷害門診手術醫療保險金的給付", "第十八條"
    )
    article_19_start = find_fubon_clause_start(
        text, "保險範圍:意外傷害醫療保險金的給付", "第十九條"
    )
    article_20_start = find_fubon_clause_start(
        text, "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十條"
    )
    article_21_start = find_fubon_clause_start(
        text, f"保險範圍:意外{disability_term}保險金的給付", "第二十一條"
    )
    if not (
        0 <= cancer_start < article_13_start < article_16_start < article_17_start < article_18_start
        < article_19_start < article_20_start < article_21_start
    ):
        return None

    health_text = text[article_13_start:article_16_start]
    accident_text = text[article_17_start:article_21_start]
    hospital_amounts = parse_four_plan_amounts(
        health_text,
        "日額計畫別住院醫療保險金日額",
    )
    caregiver_amounts = parse_four_plan_amounts(
        health_text,
        "日額計畫別住院看護保險金日額",
    )
    burn_center_amounts = parse_four_plan_amounts(
        health_text,
        "日額計畫別燒燙傷中心住院醫療保險金日額",
    )
    if hospital_amounts != [1_000, 1_000, 2_000, 2_000]:
        return None
    if caregiver_amounts != [500, 500, 1_000, 1_000]:
        return None
    if burn_center_amounts != [3_000, 3_000, 6_000, 6_000]:
        return None

    is_new_product = product_id in FUBON_NEW_CHILD_COMBINED_PRODUCT_IDS
    if is_new_product:
        accident_hospital_amounts = parse_four_plan_amounts(
            accident_text,
            "日額計畫別意外傷害住院醫療保險金日額",
        )
        accident_icu_amounts = parse_four_plan_amounts(
            accident_text,
            "日額計畫別意外傷害加護病房住院醫療保險金日額",
        )
        if accident_hospital_amounts != [1_005, 1_005, 1_010, 1_010]:
            return None
        if accident_icu_amounts != [1_005, 1_005, 1_010, 1_010]:
            return None
    else:
        old_accident_signals = (
            "本公司按每日一仟元之金額,乘以其實際住院日數",
            "另按每日一仟元之金額,乘以其實際入住加護病房日數",
        )
        if not all(signal in accident_text for signal in old_accident_signals):
            return None
        accident_hospital_amounts = [1_000] * 4
        accident_icu_amounts = [1_000] * 4

    fixed_amount_signals = (
        "最高以二十一日為限",
        "每次手術本公司給付一萬元",
        "最高給付日數以六十日為限",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "骨折未住院治療",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同一次傷害的給付總額不得超過四萬元",
        "要保人投保本契約計畫一及計畫三者,無本條約定之適用",
        "給付比例計算所得之金額",
        "累計給付金額最高以一佰萬元為限",
        "11 5%",
    )
    if not all(signal in text for signal in fixed_amount_signals):
        return None

    cancer_page = source_page(text, cancer_start) or 3
    hospital_page = source_page(text, article_13_start) or 3
    burn_page = source_page(text, article_16_start) or 6
    accident_hospital_page = source_page(text, article_17_start) or 6
    outpatient_page = source_page(text, article_18_start) or 7
    reimbursement_page = source_page(text, article_19_start) or 7
    death_page = source_page(text, article_20_start) or 7
    disability_page = source_page(text, article_21_start) or 8
    cancer_definition_start = text.find("「癌症」")
    cancer_definition_end = text.find("「外科手術治療」", cancer_definition_start)
    cancer_definition = text[cancer_definition_start:cancer_definition_end]
    if "生效日起持續有效三十日以後或復效日起所發生" in cancer_definition:
        cancer_waiting = "癌症須於初次生效持續有效 30 日後發生；復效日起發生及續保不受此等待期限制"
    else:
        cancer_waiting = "癌症須自初次生效或復效起持續有效 30 日後發生；續保不受此等待期限制"
    disease_waiting = (
        "疾病須於初次生效持續有效 30 日後發生；復效日起發生及續保不受此等待期限制；"
        "零歲投保者的條款所列新生兒篩檢疾病另有例外"
    )
    burn_center_limit = (
        "每次事故最高給付 30 日"
        if "每次事故給付日數最長以三十日為限" in health_text
        else "同一次住院最高給付 30 日"
    )
    hospital_conditions = [
        disease_waiting,
        "包含入院及出院當日",
        "同一次住院最高給付 365 日",
    ]
    if "因精神疾病住院" in health_text:
        hospital_conditions.append("精神疾病住院每保單年度最高給付 90 日")
    if "住院(含日間留院)" in health_text:
        hospital_conditions.append("本版本條款明列住院包含日間留院")
    if "但不包含全民健康保險法第五十一條所稱之日間住院" in text:
        hospital_conditions.append("本版本條款明列不包含全民健保日間住院及精神衛生法日間留院")
    hijack_extension = (
        "以乘客身分搭乘大眾運輸工具遭劫持時，契約期滿後至劫持事故終了前，第十六、二十、二十一條保障仍延續"
        if "因遭劫持" in text
        else None
    )
    guardianship_funeral_limit = (
        "受監護宣告尚未撤銷者改為喪葬費用保險金，且受法定總額上限限制"
        if "受監護宣告尚未撤銷者" in text
        else None
    )
    nasal_disability_item = (
        "本版本附表二另列鼻未缺損但鼻功能永久遺存顯著障害，給付比例 5%"
        if "鼻未缺損" in text
        and any(
            signal in text
            for signal in ("鼻功能永久遺存顯著障害", "鼻機能永久遺存顯著障害")
        )
        else None
    )

    plan_options = []
    for index, plan_label in enumerate(("計畫一", "計畫二", "計畫三", "計畫四")):
        hospital_amount = hospital_amounts[index]
        caregiver_amount = caregiver_amounts[index]
        burn_center_amount = burn_center_amounts[index]
        accident_hospital_amount = accident_hospital_amounts[index]
        accident_icu_amount = accident_icu_amounts[index]
        entries = [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                1_000,
                "daily_total",
                "因治療癌症或其併發症住院，每日給付 1,000 元，按實際住院日數計算。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[cancer_waiting, "包含入院及出院當日"],
            ),
            coverage_entry(
                "cancer-recovery-daily",
                "癌症出院療養保險金",
                1_000,
                "daily_total",
                "癌症住院後出院療養，每日給付 1,000 元，按該次實際住院日數計算。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_hospitalization",
                conditions=[cancer_waiting, "每次住院最高給付 21 日"],
            ),
            coverage_entry(
                "cancer-surgery",
                "癌症手術治療保險金",
                10_000,
                "per_event",
                "因治療癌症或其併發症接受外科手術，每次手術給付 10,000 元。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_surgery",
                conditions=[cancer_waiting],
            ),
            coverage_entry(
                "cancer-radiotherapy-daily",
                "癌症放射線治療保險金",
                1_000,
                "daily_total",
                "住院或門診接受放射線治療，每治療日給付 1,000 元；同日多次仍以一日計。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="annual",
                conditions=[cancer_waiting, "每保單年度最高給付 60 日"],
            ),
            coverage_entry(
                "cancer-chemotherapy-daily",
                "癌症化學治療保險金",
                1_000,
                "daily_total",
                "住院或門診接受化學治療，每治療日給付 1,000 元；同日多次仍以一日計。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="annual",
                conditions=[cancer_waiting, "每保單年度最高給付 60 日"],
            ),
            coverage_entry(
                "cancer-death",
                "癌症身故保險金",
                500_000,
                "policy_total",
                "因癌症或其併發症身故，給付 500,000 元後契約終止。",
                f"保單條款第十二條，第 {cancer_page} 頁",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_policy",
                conditions=[cancer_waiting, "給付後本契約終止"],
            ),
            coverage_entry(
                "hospital-daily",
                "一般住院醫療保險金",
                hospital_amount,
                "daily_total",
                f"依{plan_label}住院醫療保險金日額，每日給付 {hospital_amount:,} 元。",
                f"保單條款第十三條及計畫表，第 {hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=hospital_conditions,
            ),
            coverage_entry(
                "hospital-icu-daily",
                "加護病房住院醫療保險金",
                hospital_amount * 2,
                "daily_total",
                f"入住加護病房時，除一般住院給付外，每日另給付 {hospital_amount * 2:,} 元。",
                f"保單條款第十三條及計畫表，第 {hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=["同一次住院最高給付 30 日", "燒燙傷中心設於加護病房時不重複給付"],
            ),
            coverage_entry(
                "hospital-caregiver-daily",
                "住院看護保險金",
                caregiver_amount,
                "daily_total",
                f"依{plan_label}住院看護日額，每日給付 {caregiver_amount:,} 元。",
                f"保單條款第十三條及計畫表，第 {hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=["包含入院及出院當日", "同一次住院最高給付 365 日"],
            ),
            coverage_entry(
                "burn-center-hospital-daily",
                "燒燙傷中心住院醫療保險金",
                burn_center_amount,
                "daily_total",
                f"因燒燙傷入住燒燙傷中心時，除一般住院給付外，每日另給付 {burn_center_amount:,} 元。",
                f"保單條款第十三條及計畫表，第 {hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=[burn_center_limit, "設於加護病房時不另給付加護病房住院醫療保險金"],
            ),
            coverage_entry(
                "major-burn",
                "重大燒燙傷保險金",
                400_000,
                "per_event",
                "符合條款所列重大燒燙傷範圍，並於事故後屆滿 15 日仍生存，給付 400,000 元。",
                f"保單條款第十六條，第 {burn_page} 頁",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_event",
                conditions=[
                    "事故發生後屆滿 15 日仍生存",
                    "燒燙傷程度須符合附表三",
                    "契約期間累積給付次數與總額上限，條款未另行明示",
                    *([hijack_extension] if hijack_extension else []),
                ],
            ),
            coverage_entry(
                "accident-hospital-daily",
                "意外傷害住院醫療保險金",
                accident_hospital_amount,
                "daily_total",
                f"因意外傷害住院，每日給付 {accident_hospital_amount:,} 元。",
                f"保單條款第十七條，第 {accident_hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=["包含入院及出院當日", "同一次意外傷害最高給付 365 日"],
            ),
            coverage_entry(
                "fracture-without-hospitalization",
                "骨折未住院醫療保險金",
                accident_hospital_amount,
                "benefit_base",
                "未住院部分按骨折表日數乘以意外傷害住院日額的二分之一；表列完全骨折日數為 14 至 60 日。",
                f"保單條款第十七條及骨折表，第 {accident_hospital_page} 頁起",
                calculation_basis="table_multiplier",
                amount_role="reference",
                limit_scope="per_injury",
                aggregation_rule="highest",
                multiplier=0.5,
                conditions=[
                    "不完全骨折按完全骨折日數二分之一計",
                    "骨骼龜裂按完全骨折日數四分之一計",
                    "同時多處骨折僅給付較高一項",
                ],
            ),
            coverage_entry(
                "accident-icu-daily",
                "意外傷害加護病房住院醫療保險金",
                accident_icu_amount,
                "daily_total",
                f"因意外傷害入住加護病房，除意外住院給付外，每日另給付 {accident_icu_amount:,} 元。",
                f"保單條款第十七條，第 {accident_hospital_page} 頁起",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=["受同一次意外傷害住院 365 日上限限制", "同日轉出後再轉入不得重複計算"],
            ),
            coverage_entry(
                "accident-outpatient-surgery",
                "意外傷害門診手術醫療保險金",
                2_000,
                "per_event",
                "因意外傷害經診斷須進行門診手術，每次意外傷害給付 2,000 元。",
                f"保單條款第十八條，第 {outpatient_page} 頁",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_injury",
                conditions=["每次意外傷害限申領一次"],
            ),
            coverage_entry(
                "accident-death",
                "意外身故保險金或喪葬費用保險金",
                1_000_000,
                "policy_total",
                "意外傷害事故發生後 180 日內身故，給付 1,000,000 元；超過 180 日須證明因果關係。",
                f"保單條款第二十條，第 {death_page} 頁起",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_policy",
                conditions=[
                    "未滿 15 足歲者身故給付自滿 15 足歲起生效",
                    "給付後本契約終止",
                    *([guardianship_funeral_limit] if guardianship_funeral_limit else []),
                    *([hijack_extension] if hijack_extension else []),
                ],
            ),
            coverage_entry(
                "accident-disability",
                f"意外{disability_term}保險金",
                1_000_000,
                "benefit_base",
                f"以 1,000,000 元為基準，依附表二{disability_term}等級 5% 至 100% 比例計算。",
                f"保單條款第二十一條及附表二，第 {disability_page} 頁起",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                rate_min_percent=5,
                rate_max_percent=100,
                conditions=[
                    "同一事故多項合計最高 1,000,000 元",
                    "不同事故累計給付最高 1,000,000 元",
                    f"同一事故{disability_term}後身故，身故與{disability_term}合計最高 1,000,000 元",
                    *([nasal_disability_item] if nasal_disability_item else []),
                    *([hijack_extension] if hijack_extension else []),
                ],
            ),
        ]
        if index in (1, 3):
            entries.insert(
                -2,
                coverage_entry(
                    "accident-medical-reimbursement",
                    "意外傷害醫療保險金",
                    40_000,
                    "per_injury_limit",
                    "就實際醫療費用超過全民健康保險給付部分實支實付；一般上限 40,000 元，以全民健康保險身分治療時上限提高為 54,000 元。",
                    f"保單條款第十九條，第 {reimbursement_page} 頁",
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_injury",
                    conditions=["僅計畫二及計畫四適用", "事故後 180 日內治療；超過 180 日須證明因果關係"],
                    amount_tiers=[
                        {"label": "一般情形", "amount": 40_000},
                        {"label": "以全民健康保險身分治療", "amount": 54_000},
                    ],
                ),
            )
        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至四；系統會顯示該版本與計畫的癌症、住院及意外保障。",
        "plan_options": plan_options,
    }


def parse_fubon_golden_complete_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_GOLDEN_COMPLETE_COMBINED_PRODUCT_VERSIONS.get(product_id)
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    required_revision_signals = tuple(
        compact_table_text(signal) for signal in version["required_revision_signals"]
    )
    forbidden_revision_signals = tuple(
        compact_table_text(signal) for signal in version["forbidden_revision_signals"]
    )
    required_feature_signals = tuple(
        compact_table_text(signal) for signal in version["required_feature_signals"]
    )
    if (
        version["document_code"] not in text
        or any(signal not in compact_text for signal in required_revision_signals)
        or any(signal in compact_text for signal in forbidden_revision_signals)
        or any(signal not in compact_text for signal in required_feature_signals)
    ):
        return None

    article_specs = (
        ("cancer", "保險範圍:癌症保險金的給付", "第十二條"),
        ("hospital", "保險範圍:住院醫療保險金的給付", "第十三條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第十六條"),
        ("accident_hospital", "保險範圍:住院醫療保險金的給付", "第十七條"),
        (
            "accident_outpatient",
            "保險範圍:意外傷害門診手術醫療保險金的給付",
            "第十八條",
        ),
        ("accident_reimbursement", "保險範圍:意外傷害醫療保險金的給付", "第十九條"),
        (
            "accident_death",
            "保險範圍:意外身故保險金或喪葬費用保險金的給付",
            "第二十條",
        ),
        ("accident_disability", "保險範圍:意外失能保險金的給付", "第二十一條"),
        (
            "natural_disaster_disability",
            "保險範圍:天然災害意外傷害二至十一級失能保險金的給付",
            "第二十二條",
        ),
        (
            "accident_combined_limit",
            "意外身故保險金及意外失能保險金給付的限制",
            "第二十三條",
        ),
    )
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    table_start = text.find("附表一:", article_starts["accident_combined_limit"])
    appendix_2_start = text.find("附表二:", table_start + 1)
    appendix_3_start = text.find("附表三", appendix_2_start + 1)
    if not (
        article_starts["accident_combined_limit"]
        < table_start
        < appendix_2_start
        < appendix_3_start
    ):
        return None

    required_clause_signals = (
        "富邦人壽金圓滿傷害暨健康一年定期保險",
        "本契約保障內容分四個計畫別",
        "本契約最高可續保至被保險人保險年齡七十五歲",
        "每一次出院後給付的癌症出院療養保險金日數最高以二十一日為限",
        "每次手術本公司給付一萬元癌症手術治療保險金",
        "給付二十萬元之癌症身故保險金後本契約效力即行終止",
        "同一次住院之住院醫療保險金實際給付住院日數最高以三百六十五日為限",
        "每一保單年度之住院醫療保險金之實際給付住院日數最高僅以九十日為限",
        "同一次住院之加護病房住院醫療保險金實際給付住院日數最高以三十日為限",
        "同一次住院之住院看護保險金實際給付住院日數最高以三百六十五日為限",
        "同一次住院給付日數最長以三十日為限",
        "自意外傷害事故發生之日起屆滿十五日仍生存者本公司給付四十萬元",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "未住院部分本公司按下列骨折別所定日數乘以",
        "的二分之一給付",
        "不完全骨折按完全骨折日數二分之一給付",
        "骨骼龜裂者按完全骨折日數四分之一給付",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同一次傷害的給付總額不得超過四萬元",
        "每次意外傷害醫療保險金限額提高為五萬四仟元",
        "要保人投保本契約計畫一及計畫三者無本條約定之適用",
        "給付一佰萬元意外身故保險金或喪葬費用保險金",
        "按一佰萬元之金額對照該表所列之給付比例計算所得之金額給付意外失能保險金",
        "另按一佰萬元之金額對照該表所列之給付比例計算所得金額",
        "累計給付金額最高以一佰萬元為限",
    )
    compact_clause_signals = tuple(
        compact_table_text(signal) for signal in required_clause_signals
    )
    if any(signal not in compact_text for signal in compact_clause_signals):
        return None
    cancer_clause_text = text[
        article_starts["cancer"] : article_starts["hospital"]
    ]
    if not all(
        re.search(rf"{benefit}:.{{0,750}}?六十日為限", cancer_clause_text)
        for benefit in ("癌症放射線治療保險金", "癌症化學治療保險金")
    ):
        return None

    table_text = compact_table_text(text[table_start:appendix_2_start])
    table_signals = (
        "附表一計畫別保險金項目計畫一計畫二計畫三計畫四",
        "意外身故保險金或喪葬費用保險金100萬",
        "癌症身故保險金額20萬",
        "重大燒燙傷保險金40萬",
        "意外失能保險金致成失能等級之一100萬乘以附表二所列給付比例最高給付金額100萬",
        "天然災害意外傷害二至十一級失能保險金致成二至十一級失能等級之一100萬乘以附表二所列給付比例最高給付金額100萬",
        "癌症住院醫療保險金1000元/日",
        "癌症出院療養保險金1000元/日",
        "癌症手術治療保險金10000元/次",
        "癌症放射線治療保險金1000元/日",
        "癌症化學治療保險金1000元/日",
        "意外傷害醫療保險金04萬04萬",
        "意外傷害住院醫療保險金1000元/日",
        "意外傷害加護病房住院醫療保險金1000元/日",
        "意外傷害門診手術醫療保險金2000元/次",
        "住院醫療保險金1000元/日1000元/日2000元/日2000元/日",
        "加護病房住院醫療保險金2000元/日2000元/日4000元/日4000元/日",
        "燒燙傷中心住院醫療保險金3000元/日3000元/日6000元/日6000元/日",
        "住院看護保險金500元/日500元/日1000元/日1000元/日",
    )
    if not all(compact_table_text(signal) in table_text for signal in table_signals):
        return None

    old_disability_schedule = version["disability_schedule_revision"] == "104-revised-79-items"
    if old_disability_schedule:
        if "1-1-5" not in text or "8-2-9" not in text or "鼻未缺損" in text:
            return None
    elif not all(signal in text for signal in ("1-1-5", "4-1-2", "8-2-9", "鼻未缺損")):
        return None

    page_by_article = {
        key: source_page(text, start)
        for key, start in article_starts.items()
    }
    expected_pages = {
        "cancer": 3,
        "hospital": 4,
        "major_burn": 5,
        "accident_hospital": 5 if old_disability_schedule else 6,
        "accident_outpatient": 6,
        "accident_reimbursement": 6 if old_disability_schedule else 7,
        "accident_death": 7,
        "accident_disability": 7,
        "natural_disaster_disability": 7,
        "accident_combined_limit": 8,
    }
    table_page = source_page(text, table_start)
    appendix_2_page = source_page(text, appendix_2_start)
    appendix_3_page = source_page(text, appendix_3_start)
    if (
        page_by_article != expected_pages
        or table_page != 11
        or appendix_2_page != 12
        or appendix_3_page != 18
    ):
        return None

    cancer_diagnosis_condition = (
        "須經病理組織切片或血液細胞學檢查診斷確定"
        if version["cancer_definition_revision"] == "pre-108-pathology-or-cytology"
        else "須經病理檢驗確定"
    )
    cancer_conditions = [
        "癌症須於初次生效持續有效 90 日後發生；復效日起發生及續保不受等待期限制",
        cancer_diagnosis_condition,
    ]
    hospital_conditions = [
        "疾病須於初次生效持續有效 30 日後發生；復效日起發生及續保不受等待期限制",
        "包含入院及出院當日",
        "同一次住院最高給付 365 日",
        "精神疾病住院每保單年度最高給付 90 日",
        "不包含全民健保日間住院及精神衛生法日間留院",
    ]
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    disability_schedule_condition = (
        "本版本採 104 年修正版附表二，共 79 項失能程度"
        if old_disability_schedule
        else "本版本採 109 年修正版附表二，共 80 項失能程度"
    )
    table_ref = "附表一，第 11 頁"
    disability_table_ref = "附表二，第 12 頁起"
    burn_table_ref = "附表三，第 18 頁"
    accident_hospital_page = page_by_article["accident_hospital"]
    reimbursement_page = page_by_article["accident_reimbursement"]
    plan_amounts = (
        (1_000, 2_000, 3_000, 500),
        (1_000, 2_000, 3_000, 500),
        (2_000, 4_000, 6_000, 1_000),
        (2_000, 4_000, 6_000, 1_000),
    )

    plan_options = []
    for index, plan_label in enumerate(("計畫一", "計畫二", "計畫三", "計畫四")):
        hospital_amount, icu_amount, burn_center_amount, caregiver_amount = plan_amounts[index]
        entries = [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                1_000,
                "daily_total",
                "因治療癌症或其併發症住院，每日給付 1,000 元。",
                f"保單條款第十二條，第 3 頁起；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[*cancer_conditions, "包含入院及出院當日；同日出院再入院不得重複計算"],
            ),
            coverage_entry(
                "cancer-recovery-daily",
                "癌症出院療養保險金",
                1_000,
                "daily_total",
                "癌症住院後出院療養，每日給付 1,000 元，按該次實際住院日數計算。",
                f"保單條款第十二條，第 3 頁起；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_hospitalization",
                conditions=[*cancer_conditions, "每次出院最高給付 21 日"],
            ),
            coverage_entry(
                "cancer-surgery",
                "癌症手術治療保險金",
                10_000,
                "per_event",
                "因治療癌症或其併發症接受外科手術，每次給付 10,000 元。",
                f"保單條款第十二條，第 4 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_surgery",
                conditions=cancer_conditions,
            ),
            coverage_entry(
                "cancer-radiotherapy-daily",
                "癌症放射線治療保險金",
                1_000,
                "daily_total",
                "住院或門診接受放射線治療，每治療日給付 1,000 元；同日多次仍以一日計。",
                f"保單條款第十二條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="annual",
                conditions=[*cancer_conditions, "每保單年度最高給付 60 日"],
            ),
            coverage_entry(
                "cancer-chemotherapy-daily",
                "癌症化學治療保險金",
                1_000,
                "daily_total",
                "住院或門診接受化學治療，每治療日給付 1,000 元；同日多次仍以一日計。",
                f"保單條款第十二條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="annual",
                conditions=[*cancer_conditions, "每保單年度最高給付 60 日"],
            ),
            coverage_entry(
                "cancer-death",
                "癌症身故保險金",
                200_000,
                "policy_total",
                "因癌症或其併發症身故，給付 200,000 元後契約終止。",
                f"保單條款第十二條，第 4 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_policy",
                conditions=[*cancer_conditions, "給付後本契約終止"],
            ),
            coverage_entry(
                "hospital-daily",
                "住院醫療保險金",
                hospital_amount,
                "daily_total",
                f"依{plan_label}住院醫療日額，每日給付 {hospital_amount:,} 元。",
                f"保單條款第十三條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=hospital_conditions,
            ),
            coverage_entry(
                "hospital-icu-daily",
                "加護病房住院醫療保險金",
                icu_amount,
                "daily_total",
                f"入住加護病房時，除住院醫療保險金外，每日另給付 {icu_amount:,} 元。",
                f"保單條款第十三條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=["同一次住院最高給付 30 日", "燒燙傷中心設於加護病房時不重複給付"],
            ),
            coverage_entry(
                "hospital-caregiver-daily",
                "住院看護保險金",
                caregiver_amount,
                "daily_total",
                f"依{plan_label}住院看護日額，每日給付 {caregiver_amount:,} 元。",
                f"保單條款第十三條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=["包含入院及出院當日", "同一次住院最高給付 365 日"],
            ),
            coverage_entry(
                "burn-center-hospital-daily",
                "燒燙傷中心住院醫療保險金",
                burn_center_amount,
                "daily_total",
                f"因燒燙傷入住燒燙傷中心時，除住院醫療保險金外，每日另給付 {burn_center_amount:,} 元。",
                f"保單條款第十三條，第 4 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=["同一次住院最高給付 30 日", "設於加護病房時不另給付加護病房住院醫療保險金"],
            ),
            coverage_entry(
                "major-burn",
                "重大燒燙傷保險金",
                400_000,
                "per_event",
                "符合條款所列重大燒燙傷範圍，且事故後屆滿 15 日仍生存，給付 400,000 元。",
                f"保單條款第十六條，第 5 頁起；{burn_table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_event",
                conditions=["事故發生後屆滿 15 日仍生存", "燒燙傷程度須符合附表三"],
            ),
            coverage_entry(
                "accident-hospital-daily",
                "意外傷害住院醫療保險金",
                1_000,
                "daily_total",
                "因意外傷害住院，每日給付 1,000 元。",
                f"保單條款第十七條，第 {accident_hospital_page} 頁起；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[accident_180_condition, "包含入院及出院當日", "同一次意外傷害最高給付 365 日"],
            ),
            coverage_entry(
                "fracture-without-hospitalization",
                "骨折未住院醫療保險金",
                1_000,
                "benefit_base",
                "未住院部分按骨折表日數乘以意外傷害住院日額 1,000 元的二分之一計算。",
                f"保單條款第十七條骨折表，第 {accident_hospital_page} 頁起",
                calculation_basis="table_multiplier",
                amount_role="reference",
                limit_scope="per_injury",
                aggregation_rule="highest",
                multiplier=0.5,
                conditions=[
                    "完全骨折表列 14 至 60 日",
                    "不完全骨折按完全骨折日數二分之一；骨骼龜裂按四分之一",
                    "同時多處骨折僅給付較高一項",
                ],
            ),
            coverage_entry(
                "accident-icu-daily",
                "意外傷害加護病房住院醫療保險金",
                1_000,
                "daily_total",
                "因意外傷害入住加護病房，除意外住院給付外，每日另給付 1,000 元。",
                f"保單條款第十七條，第 {accident_hospital_page} 頁起；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=[accident_180_condition, "受同一次意外傷害住院 365 日上限限制", "同日轉出後再轉入不得重複計算"],
            ),
            coverage_entry(
                "accident-outpatient-surgery",
                "意外傷害門診手術醫療保險金",
                2_000,
                "per_event",
                "因意外傷害經診斷須進行門診手術，每次意外傷害給付 2,000 元。",
                f"保單條款第十八條，第 6 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_injury",
                conditions=["每次意外傷害限申領一次"],
            ),
            coverage_entry(
                "accident-death",
                "意外身故保險金或喪葬費用保險金",
                1_000_000,
                "policy_total",
                "意外傷害身故給付 1,000,000 元後契約終止。",
                f"保單條款第二十條，第 7 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_policy",
                conditions=[
                    accident_180_condition,
                    "未滿 15 足歲者身故給付自滿 15 足歲起生效",
                    "受監護宣告尚未撤銷者改為喪葬費用保險金，且受法定總額上限限制",
                    "給付後本契約終止",
                ],
            ),
            coverage_entry(
                "accident-disability",
                "意外失能保險金",
                1_000_000,
                "benefit_base",
                "以 1,000,000 元為基準，依附表二失能等級 5% 至 100% 比例計算。",
                f"保單條款第二十一、二十三條，第 7 頁起；{disability_table_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_policy",
                aggregation_rule="cumulative_cap",
                rate_min_percent=5,
                rate_max_percent=100,
                conditions=[
                    accident_180_condition,
                    disability_schedule_condition,
                    "同一事故多項及不同事故累計最高 1,000,000 元",
                    "第 1 級失能給付後本契約終止",
                    "同一事故失能後身故，兩者合計最高 1,000,000 元",
                    "合併既有失能時須扣除視同已給付部分",
                ],
            ),
            coverage_entry(
                "natural-disaster-accident-disability",
                "天然災害意外傷害二至十一級失能保險金",
                1_000_000,
                "benefit_base",
                "天然災害意外造成第 2 至 11 級失能時，除意外失能保險金外，再以 1,000,000 元為基準按附表二 5% 至 90% 比例計算。",
                f"保單條款第二十二條，第 7 頁起；{disability_table_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_policy",
                aggregation_rule="cumulative_cap",
                rate_min_percent=5,
                rate_max_percent=90,
                conditions=[
                    accident_180_condition,
                    "失能診斷確定日仍生存",
                    disability_schedule_condition,
                    "同一天然災害事故多項及不同事故累計最高 1,000,000 元",
                    "合併既有失能時須扣除視同已給付部分",
                ],
            ),
        ]
        if index in (1, 3):
            entries.insert(
                -3,
                coverage_entry(
                    "accident-medical-reimbursement",
                    "意外傷害醫療保險金",
                    40_000,
                    "per_injury_limit",
                    "就實際醫療費用超過全民健康保險給付部分實支實付；一般上限 40,000 元，以全民健康保險身分治療時提高為 54,000 元。",
                    f"保單條款第十九條，第 {reimbursement_page} 頁；{table_ref}",
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_injury",
                    conditions=["僅計畫二及計畫四適用", accident_180_condition],
                    amount_tiers=[
                        {"label": "一般情形", "amount": 40_000},
                        {"label": "以全民健康保險身分治療", "amount": 54_000},
                    ],
                ),
            )
        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至四；計畫二及計畫四另含意外傷害醫療實支實付，無需輸入單位數或保額。",
        "version_characteristics": {
            "disease_initial_waiting_days": 30,
            "disease_reinstatement_waiting_days": 0,
            "cancer_initial_waiting_days": 90,
            "cancer_reinstatement_waiting_days": 0,
            "maximum_renewal_age": 75,
            "day_hospital_explicit": False,
            "day_hospital_excluded": True,
            "cancer_definition_revision": version["cancer_definition_revision"],
            "newborn_screening_revision": version["newborn_screening_revision"],
            "reinstatement_notice_revision": version["reinstatement_notice_revision"],
            "disability_schedule_revision": version["disability_schedule_revision"],
            "missing_person_return_repayment_scope": version[
                "missing_person_return_repayment_scope"
            ],
            "funeral_benefit_cap_reference": version["funeral_benefit_cap_reference"],
        },
        "plan_options": plan_options,
    }


def parse_fubon_little_tycoon_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in FUBON_LITTLE_TYCOON_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    disability_term = "失能" if "意外失能保險金的給付" in text else "殘廢"
    required_signals = (
        "富邦人壽小富翁傷害暨健康一年定期保險",
        "本契約保障內容分二個計畫別",
        "保險範圍:癌症保險金的給付",
        "同一保單年度同一次住院最高日數以三十日為限",
        "每次意外傷害事故給付日數不得超過九十日",
        "意外傷害住院醫療保險金日額的二分之一",
        "不完全骨折,按完全骨折日數二分之一給付",
        "骨骼龜裂者按完全骨折日數四分之一給付",
        f"保險範圍:意外{disability_term}保險金的給付",
    )
    if not all(signal in text for signal in required_signals):
        return None

    cancer_start = find_fubon_clause_start(
        text, "保險範圍:癌症保險金的給付", "第十二條"
    )
    hospital_start = find_fubon_clause_start(
        text, "保險範圍:住院醫療日額保險金的給付", "第十三條"
    )
    accident_hospital_start = find_fubon_clause_start(
        text, "保險範圍:意外傷害住院醫療保險金的給付", "第十六條"
    )
    accident_death_start = find_fubon_clause_start(
        text, "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第十七條"
    )
    accident_disability_start = find_fubon_clause_start(
        text,
        f"保險範圍:意外{disability_term}保險金的給付",
        "第十八條",
    )
    table_start = text.rfind("附表一:")
    if not (
        0
        <= cancer_start
        < hospital_start
        < accident_hospital_start
        < accident_death_start
        < accident_disability_start
        < table_start
    ):
        return None

    table_text = compact_table_text(text[table_start : table_start + 900])
    table_signals = (
        "附表一計畫別保險金項目計畫一計畫二",
        "意外身故保險金或喪葬費用保險金100萬100萬",
        "癌症身故保險金60萬60萬",
        "100萬乘以附表二所列給付比例100萬乘以附表二所列給付比例",
        "最高給付金額100萬100萬",
        "癌症住院醫療保險金3000元/日",
        "癌症出院療養保險金1500元/日",
        "癌症手術治療保險金60000元/次",
        "癌症放射線治療保險金3000元/日",
        "意外傷害住院醫療保險金1000元/日",
        "住院醫療日額保險金1000元/日無",
    )
    if not all(signal in table_text for signal in table_signals):
        return None

    has_cancer_waiting_period = "復效日持續有效三十日" in text
    cancer_waiting_days = 30 if has_cancer_waiting_period else 0
    cancer_condition = (
        "癌症須自生效或復效起持續有效 30 日後，始經診斷確定"
        if has_cancer_waiting_period
        else "癌症無等待期；須於契約有效期間內始經診斷確定"
    )
    day_hospital_explicit = "包含精神衛生法第三十五條所稱之日間留院" in text
    revised_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    revised_109_schedule = revised_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    if revised_109_schedule:
        schedule_revision = "109-revised-80-items"
        schedule_condition = "本版本採 109 年修正版附表二，共 80 項失能程度"
    elif revised_104_schedule:
        schedule_revision = "104-revised-79-items"
        schedule_condition = f"本版本採 104 年修正版附表二，共 79 項{disability_term}程度"
    else:
        schedule_revision = "original-75-items"
        schedule_condition = "本版本附表二共 75 項殘廢程度"

    cancer_page = source_page(text, cancer_start) or 3
    hospital_page = source_page(text, hospital_start) or 4
    accident_hospital_page = source_page(text, accident_hospital_start) or 5
    accident_death_page = source_page(text, accident_death_start) or 5
    accident_disability_page = source_page(text, accident_disability_start) or 6
    table_page = source_page(text, table_start) or 9
    table_ref = f"附表一，第 {table_page} 頁"
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    hospital_conditions = [
        "含入院及出院當日",
        "同一保單年度同一次住院最高 30 日",
        "同一疾病、傷害或其併發症於出院後 14 日內在同一醫院再住院，視為同一次住院",
        "契約期滿後出院者，再次住院部分不給付",
    ]
    if day_hospital_explicit:
        hospital_conditions.append("本版本住院定義明列包含精神衛生法所稱日間留院")

    plan_options = []
    for plan_index, plan_label in enumerate(("計畫一", "計畫二")):
        entries = [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                3_000,
                "daily_total",
                "因治療癌症或其併發症住院，每日給付 3,000 元。",
                f"保單條款第十二條，第 {cancer_page} 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[cancer_condition, "含入院及出院當日；同日出院再入院不得重複計算"],
            ),
            coverage_entry(
                "cancer-recovery-daily",
                "癌症出院療養保險金",
                1_500,
                "daily_total",
                "癌症住院後在家療養，每日給付 1,500 元。",
                f"保單條款第十二條，第 {cancer_page} 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_hospitalization",
                conditions=[
                    cancer_condition,
                    "每次最高以該次實際癌症住院日數為限",
                    "療養給付期間再住院、死亡或契約終止，未經過日數的給付須扣除",
                ],
            ),
            coverage_entry(
                "cancer-surgery",
                "癌症手術治療保險金",
                60_000,
                "per_event",
                "因治療癌症或其併發症接受外科手術，每次給付 60,000 元。",
                f"保單條款第十二條，第 {cancer_page} 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_surgery",
                conditions=[cancer_condition],
            ),
            coverage_entry(
                "cancer-radiotherapy-daily",
                "癌症放射線治療保險金",
                3_000,
                "daily_total",
                "住院或門診接受放射線治療，每個治療日給付 3,000 元。",
                f"保單條款第十二條，第 {cancer_page} 頁；{table_ref}",
                calculation_basis="per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[cancer_condition, "同日治療一次或多次均以一日計"],
            ),
            coverage_entry(
                "cancer-death",
                "癌症身故保險金",
                600_000,
                "policy_total",
                "因癌症或其併發症身故，給付 600,000 元後契約終止。",
                f"保單條款第十二條，第 {cancer_page} 頁；{table_ref}",
                calculation_basis="fixed_amount",
                amount_role="payout",
                limit_scope="per_policy",
                conditions=[cancer_condition, "給付後本契約終止"],
            ),
        ]
        if plan_index == 0:
            entries.append(
                coverage_entry(
                    "hospital-daily",
                    "住院醫療日額保險金",
                    1_000,
                    "daily_total",
                    "計畫一因疾病或傷害住院，每日給付 1,000 元；計畫二無此項保障。",
                    f"保單條款第十三條，第 {hospital_page} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=hospital_conditions,
                )
            )
        entries.extend(
            [
                coverage_entry(
                    "accident-hospital-daily",
                    "意外傷害住院醫療保險金",
                    1_000,
                    "daily_total",
                    "因意外傷害住院，每日給付 1,000 元。",
                    f"保單條款第十六條，第 {accident_hospital_page} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    conditions=[accident_180_condition, "含入院及出院當日", "每次意外傷害最高給付 90 日"],
                ),
                coverage_entry(
                    "fracture-without-hospitalization",
                    "骨折未住院醫療保險金",
                    1_000,
                    "benefit_base",
                    "未住院部分按骨折表日數乘以意外住院日額 1,000 元的二分之一計算。",
                    f"保單條款第十六條骨折表，第 {accident_hospital_page} 頁起；{table_ref}",
                    calculation_basis="table_multiplier",
                    amount_role="reference",
                    limit_scope="per_injury",
                    aggregation_rule="highest",
                    multiplier=0.5,
                    conditions=[
                        "完全骨折表列 14 至 60 日",
                        "不完全骨折按完全骨折日數二分之一；骨骼龜裂按四分之一",
                        "同時多處骨折僅給付較高一項",
                    ],
                ),
                coverage_entry(
                    "accident-death",
                    "意外身故保險金或喪葬費用保險金",
                    1_000_000,
                    "policy_total",
                    "意外傷害身故給付 1,000,000 元後契約終止。",
                    f"保單條款第十七條，第 {accident_death_page} 頁；{table_ref}",
                    calculation_basis="fixed_amount",
                    amount_role="payout",
                    limit_scope="per_policy",
                    conditions=[
                        accident_180_condition,
                        "未滿 15 足歲者身故給付自滿 15 足歲起生效",
                        "特定身分依法改為喪葬費用保險金並受法定總額限制",
                        "給付後本契約終止",
                    ],
                ),
                coverage_entry(
                    "accident-disability",
                    f"意外{disability_term}保險金",
                    1_000_000,
                    "benefit_base",
                    f"以 1,000,000 元為基準，依附表二{disability_term}等級 5% 至 100% 比例計算。",
                    f"保單條款第十八、十九條及附表二，第 {accident_disability_page} 頁起；{table_ref}",
                    calculation_basis="percentage_of_base",
                    amount_role="base",
                    limit_scope="per_policy",
                    aggregation_rule="cumulative_cap",
                    rate_min_percent=5,
                    rate_max_percent=100,
                    conditions=[
                        accident_180_condition,
                        schedule_condition,
                        "同一事故多項及不同事故累計最高 1,000,000 元",
                        f"第 1 級{disability_term}給付後本契約終止",
                        f"同一事故{disability_term}後身故，兩者合計最高 1,000,000 元",
                        "合併既有狀態時須扣除視同已給付部分",
                    ],
                ),
            ]
        )
        plan_options.append(
            {
                "value": f"plan-{plan_index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一或計畫二；兩者的癌症與意外保障相同，只有計畫一另含每日 1,000 元住院醫療日額。",
        "version_characteristics": {
            "cancer_initial_waiting_days": cancer_waiting_days,
            "cancer_reinstatement_waiting_days": cancer_waiting_days,
            "day_hospital_explicit": day_hospital_explicit,
            "disability_schedule_revision": schedule_revision,
        },
        "plan_options": plan_options,
    }


def parse_fubon_protect_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in FUBON_PROTECT_COMBINED_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    disability_term = "失能" if "意外失能保險金的給付" in text else "殘廢"
    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", f"保險範圍:完全{disability_term}保險金的給付", "第十三條"),
        ("cancer", "保險範圍:初次罹患癌症保險金的給付", "第十七條"),
        ("reimbursement", "保險範圍:實支實付型醫療保險金的給付", "第十八條"),
        ("cash_choice", "保險範圍:住院醫療日額保險金選擇權的行使", "第十九條"),
        ("additional_daily", "保險範圍:日額型住院醫療保險金的給付", "第二十條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十三條"),
        ("accident_reimbursement", "保險範圍:意外傷害醫療保險金的給付", "第二十四條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十五條"),
        ("accident_disability", f"保險範圍:意外{disability_term}保險金的給付", "第二十六條"),
        ("accident_limit", f"意外身故保險金及意外{disability_term}保險金給付的限制", "第二十七條"),
    ]
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    compact_text = compact_table_text(text)
    required_clause_signals = (
        "富邦人壽保倍平安傷害暨健康一年定期保險",
        "本契約保障內容分十八個計畫別",
        "同一次住院期間之給付日數以三十一日為限",
        "同一次住院期間給付日數最高以七日為限",
        "僅得就第十八條所約定各項實支實付保險金或本條約定之住院醫療日額保險金選擇一類申請給付",
        "每顆義齒最高給付以新臺幣五仟元為限",
        "但每日以新臺幣五佰元為限",
        "本公司於新臺幣五仟元之範圍內給付",
        "附表一所載意外傷害醫療保險金之限額提高為1.35倍",
        "自意外傷害事故發生之日起屆滿十五日仍生存",
        "重大燒燙傷保險金之申領以一次為限",
        "同一次傷害的給付總額不得超過附表一所載意外傷害醫療保險金之限額",
    )
    if not all(compact_table_text(signal) in compact_text for signal in required_clause_signals):
        return None

    table_start = text.find("附表一:")
    table_end = text.find("附表二", table_start + 1)
    if table_start < 0 or table_end <= table_start:
        return None
    table_text = compact_table_text(text[table_start:table_end])
    table_signals = (
        "計畫一計畫二計畫三計畫四計畫五",
        "身故保險金或喪葬費用保險金無無無100萬100萬",
        "意外身故保險金或喪葬費用保險金100萬200萬300萬100萬200萬",
        "重大燒燙傷保險金25萬50萬75萬25萬50萬",
        "意外傷害醫療保險金3萬3萬3萬3萬3萬",
        "每日病房費1500元每日加護病房費1500元每次住院手術費36000元",
        "每次住院醫療費28056元",
        "計畫六計畫七計畫八計畫九計畫十",
        "意外身故保險金或喪葬費用保險金300萬200萬300萬200萬300萬",
        "一般住院醫療日額無無無1000元/日1000元/日",
        "計畫十一計畫十二計畫十三計畫十四計畫十五",
        "意外傷害醫療保險金無無無3萬3萬",
        "計畫十六計畫十七計畫十八",
        "意外身故保險金或喪葬費用保險金100萬200萬300萬",
        "一般住院醫療日額1000元/日1000元/日1000元/日",
    )
    if not all(compact_table_text(signal) in table_text for signal in table_signals):
        return None

    plan_labels = (
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
        "計畫九",
        "計畫十",
        "計畫十一",
        "計畫十二",
        "計畫十三",
        "計畫十四",
        "計畫十五",
        "計畫十六",
        "計畫十七",
        "計畫十八",
    )
    amounts = {
        "policy_death": [0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000, 0, 0, 0, 2_000_000, 1_000_000, 2_000_000, 1_000_000, 1_000_000],
        "total_disability": [0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000, 0, 0, 0, 2_000_000, 1_000_000, 2_000_000, 1_000_000, 1_000_000],
        "early_cancer": [0, 0, 0, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000, 0, 0, 0, 5_000, 5_000, 5_000, 5_000, 5_000],
        "other_cancer": [0, 0, 0, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000, 0, 0, 0, 50_000, 50_000, 50_000, 50_000, 50_000],
        "accident_death": [1_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000],
        "accident_disability": [1_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 3_000_000],
        "major_burn": [250_000, 500_000, 750_000, 250_000, 500_000, 750_000, 500_000, 750_000, 500_000, 750_000, 250_000, 500_000, 750_000, 250_000, 250_000, 250_000, 500_000, 750_000],
        "accident_reimbursement": [30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 0, 0, 0, 30_000, 30_000, 30_000, 30_000, 30_000],
        "additional_hospital": [0, 0, 0, 0, 0, 0, 0, 0, 1_000, 1_000, 0, 0, 0, 0, 1_000, 1_000, 1_000, 1_000],
    }

    article_pages = {key: source_page(text, start) for key, start in article_starts.items()}
    fallback_pages = {
        "policy_death": 4,
        "total_disability": 4,
        "cancer": 5,
        "reimbursement": 5,
        "cash_choice": 7,
        "additional_daily": 7,
        "major_burn": 8,
        "accident_reimbursement": 8,
        "accident_death": 8,
        "accident_disability": 9,
        "accident_limit": 9,
    }
    article_pages = {
        key: article_pages[key] or fallback_pages[key] for key in article_pages
    }
    table_page = source_page(text, table_start) or 12
    table_ref = f"附表一，第 {table_page}-{table_page + 3} 頁"

    has_cancer_waiting_period = "復效日持續有效三十日" in text
    cancer_waiting_days = 30 if has_cancer_waiting_period else 0
    cancer_condition = (
        "癌症須自生效或復效起持續有效 30 日後，始經診斷確定"
        if has_cancer_waiting_period
        else "癌症無等待期；須於契約有效期間內始經診斷確定"
    )
    new_cancer_classification = "癌症(初期)" in text
    early_cancer_name = "初次罹患癌症（初期）保險金" if new_cancer_classification else "初次罹患原位癌保險金"
    other_cancer_name = (
        "初次罹患癌症（輕度或重度）保險金"
        if new_cancer_classification
        else "初次罹患惡性腫瘤保險金"
    )
    day_hospital_explicit = "包含精神衛生法第三十五條所稱之日間留院" in text
    revised_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    revised_109_schedule = revised_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    if revised_109_schedule:
        schedule_revision = "109-revised-80-items"
        schedule_condition = "本版本採 109 年修正版附表三，共 80 項失能程度"
    elif revised_104_schedule:
        schedule_revision = "104-revised-79-items"
        schedule_condition = f"本版本採 104 年修正版附表三，共 79 項{disability_term}程度"
    else:
        schedule_revision = "original-75-items"
        schedule_condition = "本版本附表三共 75 項殘廢程度"

    hospital_conditions = [
        "同一次住院每日病房費最多給付 31 日",
        "實支實付與第十九條住院日額，同一次住院僅能擇一申領",
    ]
    if day_hospital_explicit:
        hospital_conditions.append("本版本住院定義明列包含精神衛生法所稱日間留院")
    if "投保時已投保其他商業實支實付型醫療保險" in text:
        hospital_conditions.append("日間留院時，如投保時已有其他商業實支實付醫療險而未通知，條款改以日額方式給付")
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"

    plan_options = []
    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add_plan_amount(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            note: str,
            source_ref: str,
            *,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
            amount_tiers: list[dict[str, Any]] | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            if not amount:
                return
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(amount=amount, plan=plan_label),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                    amount_tiers=amount_tiers,
                )
            )

        add_plan_amount(
            "policy_death",
            "policy-death",
            "身故保險金或喪葬費用保險金",
            "policy_total",
            "依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十二條，第 {article_pages['policy_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", "特定身分依法改為喪葬費用保險金並受法定總額限制"],
        )
        add_plan_amount(
            "total_disability",
            "total-disability",
            f"完全{disability_term}保險金",
            "policy_total",
            f"符合附表二完全{disability_term}程度之一，依{{plan}}給付 {{amount:,}} 元後，本契約終止。",
            f"保單條款第十三條及附表二，第 {article_pages['total_disability']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[f"給付後本契約終止", f"完全{disability_term}後身故不另給付第十二條身故保險金"],
        )
        add_plan_amount(
            "early_cancer",
            "initial-early-cancer",
            early_cancer_name,
            "policy_total",
            "初次診斷符合條款的早期癌症分類，依{plan}給付 {amount:,} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )
        add_plan_amount(
            "other_cancer",
            "initial-other-cancer",
            other_cancer_name,
            "policy_total",
            "初次診斷符合條款的其他癌症分類，依{plan}給付 {amount:,} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )

        reimbursement_ref = f"保單條款第十八條，第 {article_pages['reimbursement']} 頁起；{table_ref}"
        entries.extend(
            [
                coverage_entry(
                    "hospital-room-reimbursement",
                    "每日病房費用保險金",
                    1_500,
                    "daily_total",
                    "按實際病房、膳食、一般護理及醫師診察費用給付。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_day",
                    aggregation_rule="choose_one",
                    conditions=hospital_conditions,
                    amount_tiers=[
                        {"label": "附表一限額", "amount": 1_500},
                        {"label": "條款第十八條 1.35 倍適用時", "amount": 2_025},
                    ],
                ),
                coverage_entry(
                    "hospital-icu-reimbursement",
                    "每日加護病房費用保險金",
                    1_500,
                    "daily_total",
                    "加護病房費用超過每日病房費限額的部分，另於每日 1,500 元內實支實付。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=["同一次住院最高給付 7 日", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "hospital-surgery-reimbursement-base",
                    "住院或門診手術費用保險金基準",
                    36_000,
                    "benefit_base",
                    "實際手術費給付上限，以 36,000 元乘附表五的手術百分率計算。",
                    reimbursement_ref,
                    calculation_basis="percentage_of_base",
                    amount_role="base",
                    limit_scope="per_surgery",
                    conditions=["同次手術同一位置涉及二項以上器官時，按附表五最高百分率一項", "附表五未列手術由雙方比照程度相當項目協議"],
                ),
                coverage_entry(
                    "hospital-medical-reimbursement",
                    "住院醫療費或門診手術醫療費保險金",
                    28_056,
                    "per_event",
                    "每次住院或門診手術，按條款所列實際醫療費用給付，附表一限額 28,056 元。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_hospitalization",
                    aggregation_rule="cumulative_cap",
                    conditions=["條款第十八條約定適用時限額提高為 1.35 倍", "病房超額可依條款併入，但總額仍受本項限額", "已獲全民健康保險給付的部分不重複給付"],
                ),
                coverage_entry(
                    "dental-prosthesis-sublimit",
                    "意外住院義齒贗復費子限額",
                    5_000,
                    "per_event",
                    "同一意外住院造成牙齒斷落並裝置義齒時，每顆最高 5,000 元。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_event",
                    aggregation_rule="cumulative_cap",
                    conditions=["計入每次住院醫療費 28,056 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "pre-post-hospital-outpatient-sublimit",
                    "住院前後門診費子限額",
                    500,
                    "daily_total",
                    "住院前一週及出院後一週因同一事故門診，每日最高 500 元。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_day",
                    aggregation_rule="cumulative_cap",
                    conditions=["住院期間接受手術者，出院後門診期間延長為兩週", "計入每次住院醫療費 28,056 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "accident-emergency-sublimit",
                    "未住院意外急診醫療費子限額",
                    5_000,
                    "per_event",
                    "意外急診但未住院時，實際急診費用最高給付 5,000 元。",
                    reimbursement_ref,
                    calculation_basis="reimbursement_with_cap",
                    amount_role="limit",
                    limit_scope="per_event",
                    aggregation_rule="cumulative_cap",
                    conditions=["計入每次住院醫療費 28,056 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "hospital-cash-alternative-daily",
                    "住院醫療日額保險金（實支替代）",
                    1_500,
                    "daily_total",
                    "不申領第十八條實支實付時，可改按每日病房費 1,500 元乘實際住院日數給付。",
                    f"保單條款第十九條，第 {article_pages['cash_choice']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="choose_one",
                    conditions=["同一次住院與第十八條實支實付僅能擇一", "同一次住院最高給付 31 日", *( ["本版本明列日間留院適用"] if day_hospital_explicit else [] )],
                ),
                coverage_entry(
                    "hospital-cash-alternative-icu-daily",
                    "加護病房日額保險金（實支替代）",
                    1_500,
                    "daily_total",
                    "選擇住院日額且入住加護病房時，每日另給付 1,500 元。",
                    f"保單條款第十九條，第 {article_pages['cash_choice']} 頁；{table_ref}",
                    calculation_basis="per_day",
                    amount_role="payout",
                    limit_scope="per_day",
                    aggregation_rule="conditional_additive",
                    conditions=["須先選擇第十九條住院日額，不與第十八條實支實付併領", "同一次住院最高給付 7 日"],
                ),
            ]
        )

        add_plan_amount(
            "additional_hospital",
            "additional-hospital-daily",
            "一般住院醫療保險金（額外日額）",
            "daily_total",
            "除第十八條或第十九條給付外，依{plan}每日另給付 {amount:,} 元。",
            f"保單條款第二十條，第 {article_pages['additional_daily']} 頁；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            aggregation_rule="conditional_additive",
            conditions=["含入院及出院當日", "同一保單年度同一次住院最高給付 31 日", *( ["本版本明列日間留院適用"] if day_hospital_explicit else [] )],
        )
        add_plan_amount(
            "additional_hospital",
            "additional-hospital-icu-daily",
            "加護病房住院醫療保險金（額外日額）",
            "daily_total",
            "入住加護病房時，除一般額外住院日額外，每日再給付 {amount:,} 元。",
            f"保單條款第二十條，第 {article_pages['additional_daily']} 頁；{table_ref}",
            calculation_basis="per_day",
            limit_scope="per_day",
            aggregation_rule="conditional_additive",
            conditions=["同一保單年度同一次住院最高給付 7 日", "同日轉出後再轉入不重複計算"],
        )
        add_plan_amount(
            "major_burn",
            "major-burn",
            "重大燒燙傷保險金",
            "per_event",
            "符合條款重大燒燙傷範圍，依{plan}給付 {amount:,} 元。",
            f"保單條款第二十三條及附表四，第 {article_pages['major_burn']} 頁起；{table_ref}",
            conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存", "本契約與本公司其他相關契約合計最高 2,500,000 元", "保險期間內限申領一次"],
        )

        reimbursement_amount = amounts["accident_reimbursement"][index]
        add_plan_amount(
            "accident_reimbursement",
            "accident-medical-reimbursement",
            "意外傷害醫療保險金",
            "per_injury_limit",
            "超過全民健康保險給付部分實支實付，一般限額 {amount:,} 元。",
            f"保單條款第二十四條，第 {article_pages['accident_reimbursement']} 頁；{table_ref}",
            calculation_basis="reimbursement_with_cap",
            amount_role="limit",
            limit_scope="per_injury",
            aggregation_rule="cumulative_cap",
            conditions=[accident_180_condition],
            amount_tiers=(
                [
                    {"label": "一般限額", "amount": reimbursement_amount},
                    {"label": "以全民健康保險身分接受治療", "amount": int(reimbursement_amount * 1.35)},
                ]
                if reimbursement_amount
                else None
            ),
        )
        add_plan_amount(
            "accident_death",
            "accident-death",
            "意外身故保險金或喪葬費用保險金",
            "policy_total",
            "意外身故依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第二十五條，第 {article_pages['accident_death']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=[accident_180_condition, "未滿 15 足歲者身故給付自滿 15 足歲起生效", "特定身分依法改為喪葬費用保險金並受法定總額限制", "給付後本契約終止"],
        )
        add_plan_amount(
            "accident_disability",
            "accident-disability",
            f"意外{disability_term}保險金",
            "benefit_base",
            f"以 {{amount:,}} 元為基準，依附表三{disability_term}等級 5% 至 100% 比例計算。",
            f"保單條款第二十六、二十七條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base",
            amount_role="base",
            limit_scope="per_policy",
            aggregation_rule="cumulative_cap",
            conditions=[accident_180_condition, schedule_condition, "同一事故多項及不同事故累計受附表一最高給付金額限制", f"第 1 級{disability_term}給付後本契約終止", f"同一事故{disability_term}後身故，兩者合計最高為意外身故保險金", "合併既有狀態時須扣除視同已給付部分"],
            rate_min_percent=5,
            rate_max_percent=100,
        )

        plan_options.append(
            {
                "value": f"plan-{index + 1}",
                "label": plan_label,
                "coverage_entries": entries,
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至十八；本商品不需填單位數，系統會依計畫顯示壽險、癌症、住院、燒燙傷與意外保障。",
        "version_characteristics": {
            "cancer_initial_waiting_days": cancer_waiting_days,
            "cancer_reinstatement_waiting_days": cancer_waiting_days,
            "day_hospital_explicit": day_hospital_explicit,
            "disability_schedule_revision": schedule_revision,
        },
        "plan_options": plan_options,
    }


def parse_fubon_cardio_device_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    version = FUBON_CARDIO_DEVICE_UNIT_PRODUCT_VERSIONS.get(product_id)
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or str(document.get("file_name") or "") != f"{product_id}-A.pdf"
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    required_revisions = tuple(
        compact_table_text(signal) for signal in version["required_revision_signals"]
    )
    forbidden_revisions = tuple(
        compact_table_text(signal) for signal in version["forbidden_revision_signals"]
    )
    if (
        version["document_code"] not in text
        or any(signal not in compact_text for signal in required_revisions)
        or any(signal in compact_text for signal in forbidden_revisions)
    ):
        return None

    medical_heading = "【保險範圍:醫材補助保險金的給付】"
    no_claim_heading = "【保險範圍:無理賠回饋保險金的給付】"
    medical_start = text.find(medical_heading)
    no_claim_start = text.find(no_claim_heading, medical_start + 1)
    exclusion_start = text.find("【除外責任】", no_claim_start + 1)
    if (
        medical_start < 0
        or no_claim_start <= medical_start
        or exclusion_start <= no_claim_start
        or text.count(medical_heading) != 1
        or text.count(no_claim_heading) != 1
    ):
        return None

    medical_page = source_page(text, medical_start)
    no_claim_page = source_page(text, no_claim_start)
    if medical_page != 2 or no_claim_page != 2:
        return None

    clause_text = compact_table_text(text[medical_start:exclusion_start])
    common_signals = (
        "【保險範圍醫材補助保險金的給付】第八條",
        "以首次接受該項手術日期當時之保單年度對應下表所列之給付金額給付「醫材補助保險金」",
        "【保險範圍無理賠回饋保險金的給付】第九條",
    )
    if any(signal not in clause_text for signal in common_signals):
        return None

    if version["product_kind"] == "heart-guard":
        if "富邦人壽心動守護定期健康保險" not in text:
            return None
        table_signals = (
            "手術項目每投保單位給付金額第一保單年度第二保單年度第三保單年度起",
            "1.心導管檢查併心臟血管支架置放術2萬元4萬元8萬元",
            "2.心律調節器植入術2萬元4萬元8萬元",
            "3.主動脈瓣或二尖瓣或三尖瓣置換手術4萬元8萬元16萬元",
            "4.心室輔助裝置植入術8萬元16萬元32萬元",
            "前項所列四項手術項目於本契約有效期間內「醫材補助保險金」之給付各以一次為限",
            "第一項所列四項手術項目本公司均已給付時本契約效力即行終止",
            "未曾發生第八條所約定之任一項保險事故且保險期間屆滿仍生存者本公司按年繳保險費總和之60%計算給付「無理賠回饋保險金」",
        )
        benefit_specs = (
            (
                "cardiac-stent-placement",
                "心導管檢查併心臟血管支架置放術",
                (20_000, 40_000, 80_000),
            ),
            (
                "pacemaker-implantation",
                "心律調節器植入術",
                (20_000, 40_000, 80_000),
            ),
            (
                "heart-valve-replacement",
                "主動脈瓣或二尖瓣或三尖瓣置換手術",
                (40_000, 80_000, 160_000),
            ),
            (
                "ventricular-assist-device",
                "心室輔助裝置植入術",
                (80_000, 160_000, 320_000),
            ),
        )
        tier_labels = ("第一保單年度", "第二保單年度", "第三保單年度起")
        refund_rate = 60
        contract_name = "本契約"
        total_item_count = 4
        disease_waiting_signal = (
            "本契約生效日起持續有效三十日以後或復效日起所發生之疾病"
        )
    else:
        if "富邦人壽心有醫靠定期健康保險附約" not in text:
            return None
        table_signals = (
            "手術項目每投保單位給付金額第一保單年度第二保單年度起",
            "1.心導管檢查併心臟血管支架置放術3萬元10萬元",
            "2.心律調節器植入術3萬元10萬元",
            "3.「主動脈瓣或二尖瓣或三尖瓣置換手術」、「兩個瓣膜換置手術」或「三個瓣膜換置手術」6萬元20萬元",
            "4.心室輔助裝置植入術9萬元30萬元",
            "5.體外循環維生系統ECMO建立9萬元30萬元",
            "前項「主動脈瓣或二尖瓣或三尖瓣置換手術」、「兩個瓣膜換置手術」及「三個瓣膜換置手術」屬同一給付項目",
            "本公司給付一次瓣膜置換手術之醫材補助保險金後就其他瓣膜置換手術不再負醫材補助保險金的給付之責",
            "第一項所列五項手術項目本公司均已給付時本附約效力即行終止",
            "未曾發生第八條所約定之保險事故且保險期間屆滿時仍生存者本公司按年繳保險費總和的百分之三十計算給付「無理賠回饋保險金」",
        )
        benefit_specs = (
            (
                "cardiac-stent-placement",
                "心導管檢查併心臟血管支架置放術",
                (30_000, 100_000),
            ),
            (
                "pacemaker-implantation",
                "心律調節器植入術",
                (30_000, 100_000),
            ),
            (
                "heart-valve-replacement-group",
                "主動脈瓣、二尖瓣或三尖瓣置換手術（含兩個或三個瓣膜換置）",
                (60_000, 200_000),
            ),
            (
                "ventricular-assist-device",
                "心室輔助裝置植入術",
                (90_000, 300_000),
            ),
            (
                "ecmo-establishment",
                "體外循環維生系統（ECMO）建立",
                (90_000, 300_000),
            ),
        )
        tier_labels = ("第一保單年度", "第二保單年度起")
        refund_rate = 30
        contract_name = "本附約"
        total_item_count = 5
        disease_waiting_signal = (
            "本附約生效日起持續有效三十日以後或復效日起所發生之疾病"
        )

    full_text_signals = (
        disease_waiting_signal,
        "被保險人因下列原因所致之疾病或傷害而接受手術診療者本公司不負給付醫材補助保險金的責任",
        "被保險人之故意行為包括自殺及自殺未遂",
    )
    if any(signal not in clause_text for signal in table_signals) or any(
        compact_table_text(signal) not in compact_text for signal in full_text_signals
    ):
        return None

    table_ref = "保單條款第 2、8、10 條，第 1 至 3 頁"
    shared_conditions = [
        "依首次接受該項手術日期當時的保單年度決定給付級距",
        "疾病須於契約生效後持續有效 30 日以後發生；復效則自復效日起發生者適用，傷害不受此疾病等待期限制",
        "同一項手術項目於契約有效期間內以給付一次為限",
        f"全部 {total_item_count} 項手術項目均已給付時，{contract_name}效力即行終止",
        "須排除第 10 條所列故意、犯罪、非法毒品、美容或非必要整型、可見先天畸形、非直接治療及條款所列生育或不孕等除外責任；條款明列例外仍依原條款辦理",
    ]
    coverage_entries = []
    for entry_id, name, tier_amounts in benefit_specs:
        conditions = list(shared_conditions)
        if entry_id == "heart-valve-replacement-group":
            conditions.append(
                "主動脈瓣、二尖瓣、三尖瓣、兩個瓣膜及三個瓣膜換置手術屬同一給付項目，共用一次給付"
            )
        coverage_entries.append(
            coverage_entry(
                entry_id,
                name,
                tier_amounts[0],
                "per_unit",
                "表列金額為每投保單位給付額；請依手術發生時的保單年度級距乘以有效投保單位數。",
                table_ref,
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="lifetime",
                conditions=conditions,
                amount_tiers=[
                    {"label": label, "amount": amount}
                    for label, amount in zip(tier_labels, tier_amounts)
                ],
            )
        )

    coverage_entries.append(
        coverage_entry(
            "no-claim-refund",
            "無理賠回饋保險金",
            None,
            "benefit_base",
            f"保險期間內未發生第八條約定事故且期滿仍生存時，按年繳保險費總和的 {refund_rate}% 給付；此為條款公式，並非固定金額。",
            "保單條款第 2、9 條，第 1 至 2 頁",
            calculation_basis="percentage_of_base",
            amount_role="payout",
            limit_scope="per_policy",
            rate_percent=refund_rate,
            conditions=[
                "保險期間內未曾發生第八條約定的保險事故",
                "保險期間屆滿時被保險人仍生存",
                "實際金額須依條款定義的年繳保險費總和計算",
            ],
        )
    )

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "selection_label": "投保單位數",
        "selection_guidance": "請依保單面頁輸入正整數投保單位數；醫材補助會按手術發生時的保單年度級距換算。",
        "coverage_entries": coverage_entries,
    }


def parse_fubon_new_complete_combined_plan_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_NEW_COMPLETE_COMBINED_PRODUCT_VERSIONS.get(product_id)
    if (
        product_id not in FUBON_NEW_COMPLETE_COMBINED_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    compact_text = compact_table_text(text)
    if version is not None:
        required_revision_signals = tuple(
            compact_table_text(signal)
            for signal in version["required_revision_signals"]
        )
        forbidden_revision_signals = tuple(
            compact_table_text(signal)
            for signal in version["forbidden_revision_signals"]
        )
        required_feature_signals = tuple(
            compact_table_text(signal)
            for signal in version["required_feature_signals"]
        )
        if (
            version["document_code"] not in text
            or any(signal not in compact_text for signal in required_revision_signals)
            or any(signal in compact_text for signal in forbidden_revision_signals)
            or any(signal not in compact_text for signal in required_feature_signals)
        ):
            return None

    disability_term = version["disability_term"] if version else "殘廢"
    new_cancer_classification = bool(
        version and version["cancer_classification"] == "2018-three-tier"
    )
    article_specs = [
        ("policy_death", "保險範圍:身故保險金或喪葬費用保險金的給付", "第十二條"),
        ("total_disability", f"保險範圍:完全{disability_term}保險金的給付", "第十三條"),
        ("cancer", "保險範圍:癌症保險金的給付", "第十七條"),
        ("reimbursement", "保險範圍:實支實付型醫療保險金的給付", "第十八條"),
        ("cash_choice", "保險範圍:住院醫療日額保險金選擇權的行使", "第十九條"),
        ("major_burn", "保險範圍:重大燒燙傷保險金的給付", "第二十二條"),
        ("accident_hospital", "保險範圍:住院醫療保險金的給付", "第二十三條"),
        ("accident_outpatient", "保險範圍:意外傷害門診手術醫療保險金的給付", "第二十四條"),
        ("accident_reimbursement", "保險範圍:意外傷害醫療保險金的給付", "第二十五條"),
        ("accident_death", "保險範圍:意外身故保險金或喪葬費用保險金的給付", "第二十六條"),
        ("accident_disability", f"保險範圍:意外{disability_term}保險金的給付", "第二十七條"),
        ("accident_limit", f"意外身故保險金及意外{disability_term}保險金給付的限制", "第二十八條"),
    ]
    article_starts = {
        key: find_fubon_clause_start(text, heading, article)
        for key, heading, article in article_specs
    }
    if any(start < 0 for start in article_starts.values()) or list(
        article_starts.values()
    ) != sorted(article_starts.values()):
        return None

    required_clause_signals = (
        "富邦人壽新圓滿傷害暨健康一年定期保險",
        "本契約保障內容分二十個計畫別",
        "被保險人於同一次住院期間之給付日數以三百六十五日為限",
        "同一次住院期間給付日數最高以七日為限",
        "每顆義齒最高給付以新臺幣五仟元為限",
        "但每日以新臺幣五佰元為限",
        "本公司於新臺幣五仟元之範圍內給付",
        "醫療保險金的限額提高為1.35倍",
        "每次住院醫療費限額改按除以三十後再乘以實際住院天數所得之金額計算",
        "僅得就第十八條所約定各項實支實付保險金或本條約定之住院醫療日額保險金選擇一類申請給付",
        "自意外傷害事故發生之日起屆滿十五日仍生存",
        "同一次意外傷害給付日數不得超過三百六十五日",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "同一次傷害的給付總額不得超過附表一所載意外傷害醫療保險金之限額",
        "同時符合二項以上大眾運輸工具意外傷害事故者本公司之保險責任以給付最高一項為限",
        "除按第一款約定給付一般意外身故保險金外另按要保人投保計畫別對照附表一所載金額給付",
        "除按第一款約定給付一般意外殘廢保險金外另按要保人投保計畫別對照附表一計算所得之金額給付",
    )
    if disability_term == "失能":
        required_clause_signals = tuple(
            signal.replace("殘廢", "失能") for signal in required_clause_signals
        )
    if not all(
        compact_table_text(signal) in compact_text
        for signal in required_clause_signals
    ):
        return None

    table_starts = [match.start() for match in re.finditer("附表一:", text)]
    table_end = text.find("附表二", table_starts[-1] + 1) if table_starts else -1
    if len(table_starts) != 4 or table_end <= table_starts[-1]:
        return None
    table_sections = []
    for index, start in enumerate(table_starts):
        end = table_starts[index + 1] if index + 1 < len(table_starts) else table_end
        table_sections.append(compact_table_text(text[start:end]))

    # Every monetary row in the four-page appendix is pinned here. Repeated
    # all-plan amounts are printed once in the source table and are checked once.
    table_signals_by_page = (
        (
            "計畫別保險金項目計畫一計畫二計畫三計畫四計畫五",
            "身故保險金或喪葬費用保險金無無無100萬100萬",
            "完全殘廢保險金無無無100萬100萬",
            "原位癌無無無5000元5000元",
            "惡性腫瘤無無無50000元50000元",
            "重大燒燙傷保險金25萬50萬75萬25萬50萬",
            "一般意外身故保險金或喪葬費用保險金100萬200萬300萬100萬200萬",
            "大眾運輸工具意外身故保險金或喪葬費用保險金「空中大眾運輸工具」無",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」無",
            "公共建築物火災意外身故保險金或喪葬費用保險金無",
            "電梯意外身故保險金或喪葬費用保險金無",
            "一般意外殘廢保險金致成殘廢等級之一100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例",
            "大眾運輸工具意外殘廢保險金「空中大眾運輸工具」致成殘廢等級之一無最高給付金額無",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」致成殘廢等級之一無最高給付金額無",
            "公共建築物火災意外殘廢保險金致成殘廢等級之一無最高給付金額無",
            "電梯意外殘廢保險金致成殘廢等級之一無最高給付金額無",
            "癌症手術治療保險金1萬/次1萬/次1萬/次3萬/次3萬/次",
            "癌症住院醫療保險金1000元/日",
            "癌症出院療養保險金1000元/日",
            "癌症放射線治療保險金1000元/日",
            "癌症化學治療保險金1000元/日",
            "意外傷害住院醫療保險金1000元/日",
            "意外傷害加護病房住院醫療保險金1000元/日",
            "意外傷害門診手術醫療保險金2000元/次",
            "意外傷害醫療保險金3萬",
            "實支實付型醫療保險金每日病房費1500元每日加護病房費1500元每次住院手術費36000元每次住院醫療費84168元",
        ),
        (
            "計畫別保險金項目計畫六計畫七計畫八計畫九計畫十",
            "身故保險金或喪葬費用保險金100萬200萬200萬200萬200萬",
            "完全殘廢保險金100萬200萬200萬200萬200萬",
            "原位癌5000元5000元5000元5000元5000元",
            "惡性腫瘤50000元50000元50000元50000元50000元",
            "重大燒燙傷保險金75萬50萬75萬50萬75萬",
            "一般意外身故保險金或喪葬費用保險金300萬200萬300萬200萬300萬",
            "大眾運輸工具意外身故保險金或喪葬費用保險金「空中大眾運輸工具」無",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」無",
            "公共建築物火災意外身故保險金或喪葬費用保險金無",
            "電梯意外身故保險金或喪葬費用保險金無",
            "一般意外殘廢保險金致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例",
            "大眾運輸工具意外殘廢保險金「空中大眾運輸工具」致成殘廢等級之一無最高給付金額無",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」致成殘廢等級之一無最高給付金額無",
            "公共建築物火災意外殘廢保險金致成殘廢等級之一無最高給付金額無",
            "電梯意外殘廢保險金致成殘廢等級之一無最高給付金額無",
            "癌症手術治療保險金3萬/次3萬/次3萬/次3萬/次3萬/次",
            "癌症住院醫療保險金1000元/日",
            "癌症出院療養保險金1000元/日",
            "癌症放射線治療保險金1000元/日",
            "癌症化學治療保險金1000元/日",
            "意外傷害住院醫療保險金1000元/日1000元/日1000元/日1500元/日1500元/日",
            "意外傷害加護病房住院醫療保險金1000元/日1000元/日1000元/日1500元/日1500元/日",
            "意外傷害門診手術醫療保險金2000元/次2000元/次2000元/次3000元/次3000元/次",
            "意外傷害醫療保險金3萬3萬3萬3萬3萬",
            "實支實付型醫療保險金每日病房費1500元每日加護病房費1500元每次住院手術費36000元每次住院醫療費84168元",
        ),
        (
            "計畫別保險金項目計畫十一計畫十二計畫十三計畫十四計畫十五",
            "身故保險金或喪葬費用保險金無無無100萬100萬",
            "完全殘廢保險金無無無100萬100萬",
            "原位癌無無無5000元5000元",
            "惡性腫瘤無無無50000元50000元",
            "重大燒燙傷保險金40萬80萬120萬40萬80萬",
            "一般意外身故保險金或喪葬費用保險金100萬200萬300萬100萬200萬",
            "「空中大眾運輸工具」無無無200萬400萬",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」無無無100萬200萬",
            "公共建築物火災意外身故保險金或喪葬費用保險金無無無100萬200萬",
            "電梯意外身故保險金或喪葬費用保險金無無無100萬200萬",
            "一般意外殘廢保險金致成殘廢等級之一100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例",
            "「空中大眾運輸工具」致成殘廢等級之一無無無200萬乘以附表三所列給付比例400萬乘以附表三所列給付比例最高給付金額無無無200萬400萬",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例最高給付金額無無無100萬200萬",
            "公共建築物火災意外殘廢保險金致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例最高給付金額無無無100萬200萬",
            "電梯意外殘廢保險金致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例最高給付金額無無無100萬200萬",
            "癌症手術治療保險金1萬/次1萬/次1萬/次3萬/次3萬/次",
            "癌症住院醫療保險金1000元/日",
            "癌症出院療養保險金1000元/日",
            "癌症放射線治療保險金1000元/日",
            "癌症化學治療保險金1000元/日",
            "意外傷害住院醫療保險金1000元/日1000元/日1000元/日1000元/日1000元/日",
            "意外傷害加護病房住院醫療保險金1000元/日1000元/日1000元/日1000元/日1000元/日",
            "意外傷害門診手術醫療保險金2000元/次2000元/次2000元/次2000元/次2000元/次",
            "意外傷害醫療保險金無無無無無",
            "實支實付型醫療保險金每日病房費1500元每日加護病房費1500元每次住院手術費36000元每次住院醫療費84168元",
        ),
        (
            "計畫別保險金項目計畫十六計畫十七計畫十八計畫十九計畫二十",
            "身故保險金或喪葬費用保險金100萬200萬200萬200萬200萬",
            "完全殘廢保險金100萬200萬200萬200萬200萬",
            "原位癌5000元5000元5000元5000元5000元",
            "惡性腫瘤50000元50000元50000元50000元50000元",
            "重大燒燙傷保險金120萬80萬120萬80萬120萬",
            "一般意外身故保險金或喪葬費用保險金300萬200萬300萬200萬300萬",
            "「空中大眾運輸工具」600萬400萬600萬400萬600萬",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」300萬200萬300萬200萬300萬",
            "公共建築物火災意外身故保險金或喪葬費用保險金300萬200萬300萬200萬300萬",
            "電梯意外身故保險金或喪葬費用保險金300萬200萬300萬200萬300萬",
            "一般意外殘廢保險金致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例",
            "「空中大眾運輸工具」致成殘廢等級之一600萬乘以附表三所列給付比例400萬乘以附表三所列給付比例600萬乘以附表三所列給付比例400萬乘以附表三所列給付比例600萬乘以附表三所列給付比例最高給付金額600萬400萬600萬400萬600萬",
            "「水上大眾運輸工具」或「陸地大眾運輸工具」致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例最高給付金額300萬200萬300萬200萬300萬",
            "公共建築物火災意外殘廢保險金致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例最高給付金額300萬200萬300萬200萬300萬",
            "電梯意外殘廢保險金致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例最高給付金額300萬200萬300萬200萬300萬",
            "癌症手術治療保險金3萬/次3萬/次3萬/次3萬/次3萬/次",
            "癌症住院醫療保險金1000元/日",
            "癌症出院療養保險金1000元/日",
            "癌症放射線治療保險金1000元/日",
            "癌症化學治療保險金1000元/日",
            "意外傷害住院醫療保險金1000元/日1000元/日1000元/日1500元/日1500元/日",
            "意外傷害加護病房住院醫療保險金1000元/日1000元/日1000元/日1500元/日1500元/日",
            "意外傷害門診手術醫療保險金2000元/次2000元/次2000元/次3000元/次3000元/次",
            "意外傷害醫療保險金無無無無無",
            "實支實付型醫療保險金每日病房費1500元每日加護病房費1500元每次住院手術費36000元每次住院醫療費84168元",
        ),
    )
    if disability_term == "失能":
        table_signals_by_page = tuple(
            tuple(signal.replace("殘廢", "失能") for signal in signals)
            for signals in table_signals_by_page
        )
    if new_cancer_classification:
        table_signals_by_page = tuple(
            tuple(
                signal.replace("原位癌", "癌症(初期)").replace(
                    "惡性腫瘤", "癌症(輕度)或癌症(重度)"
                )
                for signal in signals
            )
            for signals in table_signals_by_page
        )
    if product_id == "209391M12G00300":
        original_reordered_indexes = (
            {7, 11, 12, 13, 14, 15, 25},
            {7, 11, 12, 13, 14, 15, 25},
            {11, 12, 13, 14, 15, 25},
            {11, 12, 13, 14, 15, 25},
        )
        if any(
            compact_table_text(signal) not in section
            for section, signals, reordered in zip(
                table_sections,
                table_signals_by_page,
                original_reordered_indexes,
            )
            for signal_index, signal in enumerate(signals)
            if signal_index not in reordered
        ):
            return None
        original_reordered_signals = (
            (
                "「空中大眾運輸工具」無大眾運輸工具意外身故保險金或喪葬費用保險金「水上大眾運輸工具」或「陸地大眾運輸工具」無",
                "致成殘廢等級之一100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例一般意外殘廢保險金最高給付金額100萬200萬300萬100萬200萬",
                "致成殘廢等級之一無「空中大眾運輸工具」最高給付金額無",
                "致成殘廢等級之一無大眾運輸工具意外殘廢保險金「水上大眾運輸工具」或「陸地大眾運輸工具」最高給付金額無",
                "致成殘廢等級之一無公共建築物火災意外殘廢保險金最高給付金額無",
                "致成殘廢等級之一無電梯意外殘廢保險金最高給付金額無",
                "每日病房費1500元每日加護病房費1500元每次住院手術費36000元實支實付型醫療保險金每次住院醫療費84168元",
            ),
            (
                "「空中大眾運輸工具」無大眾運輸工具意外身故保險金或喪葬費用保險金「水上大眾運輸工具」或「陸地大眾運輸工具」無",
                "致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例一般意外殘廢保險金最高給付金額300萬200萬300萬200萬300萬",
                "致成殘廢等級之一無「空中大眾運輸工具」最高給付金額無",
                "致成殘廢等級之一無大眾運輸工具意外殘廢保險金「水上大眾運輸工具」或「陸地大眾運輸工具」最高給付金額無",
                "致成殘廢等級之一無公共建築物火災意外殘廢保險金最高給付金額無",
                "致成殘廢等級之一無電梯意外殘廢保險金最高給付金額無",
                "每日病房費1500元每日加護病房費1500元每次住院手術費36000元實支實付型醫療保險金每次住院醫療費84168元",
            ),
            (
                "致成殘廢等級之一100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例一般意外殘廢保險金最高給付金額100萬200萬300萬100萬200萬",
                "致成殘廢等級之一無無無200萬乘以附表三所列給付比例400萬乘以附表三所列給付比例「空中大眾運輸工具」最高給付金額無無無200萬400萬",
                "致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例大眾運輸工具意外殘廢保險金「水上大眾運輸工具」或「陸地大眾運輸工具」最高給付金額無無無100萬200萬",
                "致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例公共建築物火災意外殘廢保險金最高給付金額無無無100萬200萬",
                "致成殘廢等級之一無無無100萬乘以附表三所列給付比例200萬乘以附表三所列給付比例電梯意外殘廢保險金最高給付金額無無無100萬200萬",
                "每日病房費1500元每日加護病房費1500元每次住院手術費36000元實支實付型醫療保險金每次住院醫療費84168元",
            ),
            (
                "致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例一般意外殘廢保險金最高給付金額300萬200萬300萬200萬300萬",
                "致成殘廢等級之一600萬乘以附表三所列給付比例400萬乘以附表三所列給付比例600萬乘以附表三所列給付比例400萬乘以附表三所列給付比例600萬乘以附表三所列給付比例「空中大眾運輸工具」最高給付金額600萬400萬600萬400萬600萬",
                "致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例大眾運輸工具意外殘廢保險金「水上大眾運輸工具」或「陸地大眾運輸工具」最高給付金額300萬200萬300萬200萬300萬",
                "致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例公共建築物火災意外殘廢保險金最高給付金額300萬200萬300萬200萬300萬",
                "致成殘廢等級之一300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例200萬乘以附表三所列給付比例300萬乘以附表三所列給付比例電梯意外殘廢保險金最高給付金額300萬200萬300萬200萬300萬",
                "每日病房費1500元每日加護病房費1500元每次住院手術費36000元實支實付型醫療保險金每次住院醫療費84168元",
            ),
        )
        if any(
            not all(compact_table_text(signal) in section for signal in signals)
            for section, signals in zip(table_sections, original_reordered_signals)
        ):
            return None
    elif any(
        not all(compact_table_text(signal) in section for signal in signals)
        for section, signals in zip(table_sections, table_signals_by_page)
    ):
        return None

    plan_labels = tuple(
        f"計畫{label}"
        for label in (
            "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
        )
    )
    amounts = {
        "policy_death": [0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000, 0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000],
        "total_disability": [0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000, 0, 0, 0, 1_000_000, 1_000_000, 1_000_000, 2_000_000, 2_000_000, 2_000_000, 2_000_000],
        "early_cancer": [0, 0, 0, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000, 0, 0, 0, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000, 5_000],
        "other_cancer": [0, 0, 0, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000, 0, 0, 0, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000, 50_000],
        "major_burn": [250_000, 500_000, 750_000, 250_000, 500_000, 750_000, 500_000, 750_000, 500_000, 750_000, 400_000, 800_000, 1_200_000, 400_000, 800_000, 1_200_000, 800_000, 1_200_000, 800_000, 1_200_000],
        "general_accident": [1_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000],
        "air_transport": [0] * 13 + [2_000_000, 4_000_000, 6_000_000, 4_000_000, 6_000_000, 4_000_000, 6_000_000],
        "other_special": [0] * 13 + [1_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000, 2_000_000, 3_000_000],
        "cancer_surgery": [10_000, 10_000, 10_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 10_000, 10_000, 10_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000, 30_000],
        "accident_hospital": [1_000] * 8 + [1_500, 1_500] + [1_000] * 8 + [1_500, 1_500],
        "accident_icu": [1_000] * 8 + [1_500, 1_500] + [1_000] * 8 + [1_500, 1_500],
        "accident_outpatient": [2_000] * 8 + [3_000, 3_000] + [2_000] * 8 + [3_000, 3_000],
        "accident_reimbursement": [30_000] * 10 + [0] * 10,
    }

    article_pages = {key: source_page(text, start) for key, start in article_starts.items()}
    fallback_pages = {
        "policy_death": 4,
        "total_disability": 4,
        "cancer": 5,
        "reimbursement": 6,
        "cash_choice": 8,
        "major_burn": 9,
        "accident_hospital": 9,
        "accident_outpatient": 10,
        "accident_reimbursement": 10,
        "accident_death": 10,
        "accident_disability": 11,
        "accident_limit": 12,
    }
    article_pages = {
        key: article_pages[key] or fallback_pages[key] for key in article_pages
    }
    table_page = source_page(text, table_starts[0]) or 15
    table_ref = f"附表一，第 {table_page}-{table_page + 3} 頁"

    has_reinstatement_waiting_period = "或復效日持續有效三十日" in text
    no_reinstatement_waiting_period = "自本契約生效日(或復效日)起" in text
    if not has_reinstatement_waiting_period and not no_reinstatement_waiting_period:
        return None
    cancer_initial_waiting_days = 0
    cancer_reinstatement_waiting_days = 30 if has_reinstatement_waiting_period else 0
    day_hospital_explicit = "包含精神衛生法第三十五條所稱之日間留院" in text
    if version is not None and (
        cancer_initial_waiting_days != version["cancer_initial_waiting_days"]
        or cancer_reinstatement_waiting_days
        != version["cancer_reinstatement_waiting_days"]
        or day_hospital_explicit != version["day_hospital_explicit"]
    ):
        return None
    cancer_condition = (
        "癌症初次生效無等待期；復效須持續有效 30 日後，始經診斷確定"
        if has_reinstatement_waiting_period
        else "癌症初次生效及復效均無等待期；須於有效期間內始經診斷確定"
    )
    revised_104_schedule = all(signal in text for signal in ("1-1-5", "8-2-9"))
    revised_109_schedule = revised_104_schedule and all(
        signal in text for signal in ("4-1-2", "鼻未缺損")
    )
    truncated_schedule_tail = (
        version["truncated_schedule_tail"] if version is not None else None
    )
    truncated_schedule_cache = bool(
        truncated_schedule_tail
        and "1-1-5" in text
        and truncated_schedule_tail in text
        and "8-2-8" not in text
    )
    if version is not None:
        schedule_revision = version["disability_schedule_revision"]
        if schedule_revision == "104-revised-79-items":
            if not ((revised_104_schedule and not revised_109_schedule) or truncated_schedule_cache):
                return None
            if "4-1-2" in text or "鼻未缺損" in text:
                return None
        elif schedule_revision == "109-revised-80-items":
            if not (
                revised_109_schedule
                or (
                    truncated_schedule_cache
                    and "4-1-2" in text
                    and "鼻未缺損" in text
                )
            ):
                return None
        else:
            return None
        schedule_condition = (
            f"本版本採 109 年修正版附表三，共 80 項{disability_term}程度"
            if schedule_revision == "109-revised-80-items"
            else f"本版本採 104 年修正版附表三，共 79 項{disability_term}程度"
        )
    elif product_id.endswith(("000002", "000003")):
        truncated_104_cache = (
            product_id == "209391MZ1G00321A11Z10000002"
            and "1-1-5" in text
            and "8-2-3" in text
            and "8-2-8" not in text
        )
        if not (revised_104_schedule or truncated_104_cache):
            return None
        schedule_revision = "104-revised-79-items"
        schedule_condition = "本版本採 104 年修正版附表三，共 79 項殘廢程度"
    else:
        if "1-1-5" in text or "8-2-9" in text:
            return None
        schedule_revision = "original-75-items"
        schedule_condition = "本版本附表三共 75 項殘廢程度"

    hospital_conditions = [
        "同一次住院每日病房費最多給付 365 日",
        "實支實付與第十九條住院日額，同一次住院僅能擇一申領",
    ]
    if day_hospital_explicit:
        hospital_conditions.append("本版本住院定義明列包含精神衛生法所稱日間留院")
    if "投保時已投保其他商業實支實付型醫療保險" in text:
        hospital_conditions.append("日間留院時，如投保時已有其他商業實支實付醫療險而未通知，條款改以日額方式給付")
    accident_180_condition = "事故後 180 日內；超過 180 日須證明與該事故具有因果關係"
    transport_highest_condition = "同時符合二項以上空中、水上或陸地大眾運輸事故時，僅給付最高一項運輸保障"
    special_additive_condition = "本項在一般意外保障之外另行給付"
    total_disability_name = f"完全{disability_term}保險金"
    early_cancer_name = (
        "初次罹患癌症（初期）保險金"
        if new_cancer_classification
        else "初次罹患原位癌保險金"
    )
    other_cancer_name = (
        "初次罹患癌症（輕度或重度）保險金"
        if new_cancer_classification
        else "初次罹患惡性腫瘤保險金"
    )
    early_cancer_diagnosis = "癌症（初期）" if new_cancer_classification else "原位癌"
    other_cancer_diagnosis = (
        "癌症（輕度或重度）" if new_cancer_classification else "惡性腫瘤"
    )

    plan_options = []
    for index, plan_label in enumerate(plan_labels):
        entries: list[dict[str, Any]] = []

        def add_amount(
            amount_key: str,
            entry_id: str,
            name: str,
            basis: str,
            note: str,
            source_ref: str,
            *,
            calculation_basis: str = "fixed_amount",
            amount_role: str = "payout",
            limit_scope: str = "per_event",
            aggregation_rule: str = "separate",
            conditions: list[str] | None = None,
            rate_min_percent: int | None = None,
            rate_max_percent: int | None = None,
            amount_tiers: list[dict[str, Any]] | None = None,
        ) -> None:
            amount = amounts[amount_key][index]
            if not amount:
                return
            entries.append(
                coverage_entry(
                    entry_id,
                    name,
                    amount,
                    basis,
                    note.format(amount=amount, plan=plan_label),
                    source_ref,
                    calculation_basis=calculation_basis,
                    amount_role=amount_role,
                    limit_scope=limit_scope,
                    aggregation_rule=aggregation_rule,
                    conditions=conditions,
                    rate_min_percent=rate_min_percent,
                    rate_max_percent=rate_max_percent,
                    amount_tiers=amount_tiers,
                )
            )

        add_amount(
            "policy_death", "policy-death", "身故保險金或喪葬費用保險金", "policy_total",
            "依{plan}給付 {amount:,} 元後，本契約終止。",
            f"保單條款第十二條，第 {article_pages['policy_death']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", "特定身分依法改為喪葬費用保險金並受法定總額限制"],
        )
        add_amount(
            "total_disability", "total-disability", total_disability_name, "policy_total",
            f"符合附表二完全{disability_term}程度之一，依{{plan}}給付 {{amount:,}} 元後，本契約終止。",
            f"保單條款第十三條及附表二，第 {article_pages['total_disability']} 頁起；{table_ref}",
            limit_scope="per_policy",
            conditions=["給付後本契約終止", f"完全{disability_term}後身故不另給付第十二條身故保險金"],
        )
        add_amount(
            "early_cancer", "initial-early-cancer", early_cancer_name, "policy_total",
            f"初次診斷{early_cancer_diagnosis}，依{{plan}}給付 {{amount:,}} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )
        add_amount(
            "other_cancer", "initial-other-cancer", other_cancer_name, "policy_total",
            f"初次診斷{other_cancer_diagnosis}，依{{plan}}給付 {{amount:,}} 元。",
            f"保單條款第十七條，第 {article_pages['cancer']} 頁；{table_ref}",
            limit_scope="per_policy",
            conditions=[cancer_condition, "生效前未曾罹患癌症", "含續保契約合計限給付一次"],
        )

        cancer_ref = f"保單條款第十七條，第 {article_pages['cancer']} 頁；{table_ref}"
        add_amount(
            "cancer_surgery", "cancer-surgery", "癌症手術治療保險金", "per_event",
            "每次癌症或其併發症之外科手術，依{plan}給付 {amount:,} 元。", cancer_ref,
            conditions=[cancer_condition],
        )
        for entry_id, name, limit_scope, conditions in (
            ("cancer-hospital-daily", "癌症住院醫療保險金", "per_day", [cancer_condition, "包含入院及出院當日"]),
            ("cancer-discharge-recovery-daily", "癌症出院療養保險金", "per_hospitalization", [cancer_condition, "每次住院最高給付 21 日"]),
            ("cancer-radiotherapy-daily", "癌症放射線治療保險金", "annual", [cancer_condition, "每日治療一次或多次均以一日計", "同一保單年度最高給付 60 日"]),
            ("cancer-chemotherapy-daily", "癌症化學治療保險金", "annual", [cancer_condition, "每日治療一次或多次均以一日計", "同一保單年度最高給付 60 日"]),
        ):
            entries.append(
                coverage_entry(
                    entry_id, name, 1_000, "daily_total",
                    f"依{plan_label}每一符合條件的給付日給付 1,000 元。", cancer_ref,
                    calculation_basis="per_day", amount_role="payout",
                    limit_scope=limit_scope, conditions=conditions,
                )
            )

        reimbursement_ref = f"保單條款第十八條，第 {article_pages['reimbursement']} 頁起；{table_ref}"
        entries.extend(
            [
                coverage_entry(
                    "hospital-room-reimbursement", "每日病房費用保險金", 1_500, "daily_total",
                    "按實際病房、膳食、一般護理及醫師診察費用給付。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_day",
                    aggregation_rule="choose_one", conditions=hospital_conditions,
                    amount_tiers=[{"label": "附表一限額", "amount": 1_500}, {"label": "條款第十八條 1.35 倍適用時", "amount": 2_025}],
                ),
                coverage_entry(
                    "hospital-icu-reimbursement", "每日加護病房費用保險金", 1_500, "daily_total",
                    "加護病房費用超過每日病房費限額的部分，每日另於 1,500 元內實支實付。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_day",
                    aggregation_rule="conditional_additive", conditions=["同一次住院最高給付 7 日", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "hospital-surgery-reimbursement-base", "住院或門診手術費用保險金基準", 36_000, "benefit_base",
                    "實際手術費給付上限，以 36,000 元乘附表五的手術百分率計算。", reimbursement_ref,
                    calculation_basis="percentage_of_base", amount_role="base", limit_scope="per_surgery",
                    conditions=["同次手術同一位置涉及二項以上器官時，按附表五最高百分率一項", "附表五未列手術由雙方比照程度相當項目協議", "條款第十八條約定適用時限額提高為 1.35 倍"],
                    amount_tiers=[{"label": "附表一基準", "amount": 36_000}, {"label": "條款第十八條 1.35 倍適用時的基準", "amount": 48_600}],
                ),
                coverage_entry(
                    "hospital-medical-reimbursement", "住院醫療費或門診手術醫療費保險金", 84_168, "per_event",
                    "每次住院或門診手術，按條款所列實際醫療費用給付，附表一限額 84,168 元。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_hospitalization",
                    aggregation_rule="cumulative_cap",
                    conditions=["條款第十八條約定適用時限額提高為 1.35 倍", "同次住院超過 30 日時，以 84,168 元除以 30 再乘實際住院日數", "病房超額可依條款併入，但總額仍受本項限額", "已獲全民健康保險給付的部分不重複給付"],
                    amount_tiers=[{"label": "附表一限額", "amount": 84_168}, {"label": "條款第十八條 1.35 倍適用時", "amount": 113_627}],
                ),
                coverage_entry(
                    "dental-prosthesis-sublimit", "意外住院義齒贗復費子限額", 5_000, "per_event",
                    "同一意外住院造成牙齒斷落並裝置義齒時，每顆最高 5,000 元。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_event",
                    aggregation_rule="cumulative_cap", conditions=["計入每次住院醫療費 84,168 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "pre-post-hospital-outpatient-sublimit", "住院前後門診費子限額", 500, "daily_total",
                    "住院前一週及出院後一週因同一事故門診，每日最高 500 元。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_day",
                    aggregation_rule="cumulative_cap", conditions=["住院期間接受手術者，出院後門診期間延長為兩週", "計入每次住院醫療費 84,168 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "accident-emergency-sublimit", "未住院意外急診醫療費子限額", 5_000, "per_event",
                    "意外急診但未住院時，實際急診費用最高給付 5,000 元。", reimbursement_ref,
                    calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_event",
                    aggregation_rule="cumulative_cap", conditions=["計入每次住院醫療費 84,168 元限額", "條款第十八條的 1.35 倍提高不適用本項"],
                ),
                coverage_entry(
                    "hospital-cash-alternative-daily", "住院醫療日額保險金（實支替代）", 1_500, "daily_total",
                    "不申領第十八條實支實付時，可改按每日病房費 1,500 元乘實際住院日數給付。",
                    f"保單條款第十九條，第 {article_pages['cash_choice']} 頁；{table_ref}",
                    calculation_basis="per_day", amount_role="payout", limit_scope="per_day", aggregation_rule="choose_one",
                    conditions=["同一次住院與第十八條實支實付僅能擇一", "同一次住院最高給付 365 日", *(["本版本明列日間留院適用"] if day_hospital_explicit else [])],
                ),
                coverage_entry(
                    "hospital-cash-alternative-icu-daily", "加護病房日額保險金（實支替代）", 1_500, "daily_total",
                    "選擇住院日額且入住加護病房時，每日另給付 1,500 元。",
                    f"保單條款第十九條，第 {article_pages['cash_choice']} 頁；{table_ref}",
                    calculation_basis="per_day", amount_role="payout", limit_scope="per_day", aggregation_rule="conditional_additive",
                    conditions=["須先選擇第十九條住院日額，不與第十八條實支實付併領", "同一次住院最高給付 7 日"],
                ),
            ]
        )

        add_amount(
            "major_burn", "major-burn", "重大燒燙傷保險金", "per_event",
            "符合條款重大燒燙傷範圍，依{plan}給付 {amount:,} 元。",
            f"保單條款第二十二條及附表四，第 {article_pages['major_burn']} 頁起；{table_ref}",
            conditions=["二度燒燙傷面積大於全身 20%、三度大於全身 10%，或顏面燒燙傷合併五官功能障礙", "事故後屆滿 15 日仍生存"],
        )
        add_amount(
            "accident_hospital", "accident-hospital-daily", "意外傷害住院醫療保險金", "daily_total",
            "依{plan}按實際住院日數每日給付 {amount:,} 元。",
            f"保單條款第二十三條，第 {article_pages['accident_hospital']} 頁；{table_ref}",
            calculation_basis="per_day", limit_scope="per_day",
            conditions=[accident_180_condition, "包含入院及出院當日", "同一次意外傷害最高給付 365 日", "骨折未住院依完全、不完全或龜裂比例及骨折日數表計算；多項骨折僅取較高一項"],
        )
        add_amount(
            "accident_icu", "accident-icu-daily", "意外傷害加護病房住院醫療保險金", "daily_total",
            "入住加護病房時，除意外住院日額外，每日另給付 {amount:,} 元。",
            f"保單條款第二十三條，第 {article_pages['accident_hospital']} 頁；{table_ref}",
            calculation_basis="per_day", limit_scope="per_day", aggregation_rule="conditional_additive",
            conditions=[accident_180_condition, "與意外住院日額相同，受同一次意外傷害 365 日上限限制", "同日轉出後再轉入不重複計算"],
        )
        add_amount(
            "accident_outpatient", "accident-outpatient-surgery", "意外傷害門診手術醫療保險金", "per_event",
            "每次意外傷害門診手術依{plan}給付 {amount:,} 元。",
            f"保單條款第二十四條，第 {article_pages['accident_outpatient']} 頁；{table_ref}",
            conditions=["每次意外傷害限申領一次"],
        )
        reimbursement_amount = amounts["accident_reimbursement"][index]
        add_amount(
            "accident_reimbursement", "accident-medical-reimbursement", "意外傷害醫療保險金", "per_injury_limit",
            "超過全民健康保險給付部分實支實付，一般限額 {amount:,} 元。",
            f"保單條款第二十五條，第 {article_pages['accident_reimbursement']} 頁；{table_ref}",
            calculation_basis="reimbursement_with_cap", amount_role="limit", limit_scope="per_injury", aggregation_rule="cumulative_cap",
            conditions=[accident_180_condition],
            amount_tiers=([{"label": "一般限額", "amount": reimbursement_amount}, {"label": "以全民健康保險身分接受治療", "amount": int(reimbursement_amount * 1.35)}] if reimbursement_amount else None),
        )
        add_amount(
            "general_accident", "accident-death", "一般意外身故保險金或喪葬費用保險金", "policy_total",
            "一般意外身故依{plan}給付 {amount:,} 元。",
            f"保單條款第二十六條，第 {article_pages['accident_death']} 頁起；{table_ref}",
            limit_scope="per_policy", conditions=[accident_180_condition, "給付後本契約終止"],
        )
        add_amount(
            "general_accident", "accident-disability", f"一般意外{disability_term}保險金", "benefit_base",
            f"以 {{amount:,}} 元為基準，依附表三{disability_term}等級 5% 至 100% 比例計算。",
            f"保單條款第二十七、二十八條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
            calculation_basis="percentage_of_base", amount_role="base", limit_scope="per_policy", aggregation_rule="cumulative_cap",
            conditions=[accident_180_condition, schedule_condition, "同一事故多項及不同事故累計受附表一最高給付金額限制", f"同一事故{disability_term}後身故，兩者合計最高為一般意外身故保險金"],
            rate_min_percent=5, rate_max_percent=100,
        )

        for amount_key, prefix, display_name, transport_only in (
            ("air_transport", "air-transport", "空中大眾運輸工具", True),
            ("other_special", "water-land-transport", "水上或陸地大眾運輸工具", True),
            ("other_special", "public-building-fire", "公共建築物火災", False),
            ("other_special", "elevator", "電梯", False),
        ):
            special_conditions = [special_additive_condition, accident_180_condition]
            if transport_only:
                special_conditions.insert(1, transport_highest_condition)
            add_amount(
                amount_key, f"{prefix}-accident-death", f"{display_name}意外身故保險金或喪葬費用保險金", "policy_total",
                "除一般意外身故保障外，符合{plan}條件時另給付 {amount:,} 元。",
                f"保單條款第二十六條，第 {article_pages['accident_death']} 頁起；{table_ref}",
                limit_scope="per_policy", aggregation_rule="conditional_additive", conditions=special_conditions,
            )
            add_amount(
                amount_key, f"{prefix}-accident-disability", f"{display_name}意外{disability_term}保險金", "benefit_base",
                f"除一般意外{disability_term}保障外，以 {{amount:,}} 元為基準，按附表三 5% 至 100% 比例另行給付。",
                f"保單條款第二十七、二十八條及附表三，第 {article_pages['accident_disability']} 頁起；{table_ref}",
                calculation_basis="percentage_of_base", amount_role="base", limit_scope="per_policy",
                aggregation_rule="conditional_additive", conditions=[*special_conditions, schedule_condition],
                rate_min_percent=5, rate_max_percent=100,
            )

        plan_options.append(
            {"value": f"plan-{index + 1}", "label": plan_label, "coverage_entries": entries}
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "selection_label": "保障計畫",
        "selection_guidance": "請依保單首頁選擇計畫一至二十；本商品不需填單位數，系統會依計畫顯示壽險、癌症、實支實付、燒燙傷與意外保障。",
        "version_characteristics": {
            "cancer_initial_waiting_days": cancer_initial_waiting_days,
            "cancer_reinstatement_waiting_days": cancer_reinstatement_waiting_days,
            "day_hospital_explicit": day_hospital_explicit,
            "disability_schedule_revision": schedule_revision,
            **(
                {
                    "disability_terminology": disability_term,
                    "cancer_classification": version["cancer_classification"],
                    "missing_person_return_repayment_scope": version[
                        "missing_person_return_repayment_scope"
                    ],
                    "funeral_benefit_cap_reference": version[
                        "funeral_benefit_cap_reference"
                    ],
                    "source_conflicts": version["source_conflicts"],
                }
                if version is not None
                else {}
            ),
        },
        "plan_options": plan_options,
    }


def parse_prudential_china_daily_hospital_face_amount(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in DAILY_HOSPITAL_97_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    required_signals = (
        "新住院日額型定期健康保險附約",
        "住院保險金的給付",
        "加護病房費用保險金的給付",
        "住院保險金日額",
        "三百六十五日",
        "一千倍",
        "第十一條",
        "第十二條",
    )
    if not all(signal in text for signal in required_signals):
        return None

    hospital_start = text.find("住院保險金的給付")
    intensive_care_start = text.find("加護病房費用保險金的給付")
    cap_start = text.find("一千倍")
    hospital_clause = text[hospital_start:intensive_care_start]
    intensive_care_clause = text[intensive_care_start : intensive_care_start + 420]
    cap_clause = text[max(0, cap_start - 220) : cap_start + 180]
    if not (
        "含始日及終日" in hospital_clause
        and "乘以" in hospital_clause
        and "另行給付" in intensive_care_clause
        and "每日按其" in intensive_care_clause
        and "累計已領取" in cap_clause
        and "住院保險金日額" in cap_clause
    ):
        return None

    hospital_page = source_page(text, hospital_start) or 3
    cap_page = source_page(text, cap_start) or 2
    return {
        "selection_type": "face_amount",
        "input_mode": "face_amount",
        "selection_source": "terms",
        "selection_label": "住院保險金日額",
        "selection_guidance": "請填保單首頁記載的「住院保險金日額」；住院與加護病房給付會依此換算。",
        "coverage_entries": [
            coverage_entry(
                "hospital-daily",
                "住院保險金",
                None,
                "benefit_base",
                "按實際住院日數（含入院及出院當日）每日給付一倍住院保險金日額，每次住院最高 365 日。",
                f"保單條款第十條、第十一條，第 {hospital_page} 頁",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="per_day",
                rate_percent=100,
                conditions=["包含入院及出院當日", "每次住院最高給付 365 日"],
            ),
            coverage_entry(
                "intensive-care-daily",
                "加護病房費用保險金",
                None,
                "benefit_base",
                "住進加護病房治療期間，每日另行給付一倍住院保險金日額，每次住院最高 365 日。",
                f"保單條款第十條、第十二條，第 {hospital_page} 頁",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                rate_percent=100,
                conditions=["加護病房期間另行給付", "包含入院及出院當日", "每次住院最高給付 365 日"],
            ),
            coverage_entry(
                "cumulative-benefit-termination-threshold",
                "累積總給付終止門檻",
                None,
                "benefit_base",
                "第十一條及第十二條累積領取總額達住院保險金日額的一千倍時，本附約終止。",
                f"保單條款第八條，第 {cap_page} 頁",
                calculation_basis="table_multiplier",
                amount_role="reference",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                multiplier=1_000,
                conditions=["住院保險金日額減少時，按減少後日額重新計算門檻"],
            ),
        ],
    }


def parse_prudential_china_medical_endowment_plan_unit(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in MEDICAL_ENDOWMENT_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    dense_text = re.sub(r"\s+", "", text)
    required_signals = (
        "歡喜安康醫療養老保險",
        "住院日額保險金的給付",
        "加護病房或燒燙傷中心日額保險金的給付",
        "身故保險金的給付",
        "完全殘廢保險金的給付",
        "滿期保險金的給付",
        "保險給付的限制",
        "六小時",
        "三百六十五日",
        "一千二百五十倍",
        "一點零二倍",
        "一點零五倍",
    )
    if not all(signal in text for signal in required_signals):
        return None

    table_start = text.rfind("保險單位給付項目")
    if table_start < 0:
        return None
    table_dense_start = dense_text.rfind("保險單位給付項目")
    table_text = dense_text[table_dense_start : table_dense_start + 520]
    unit_match = re.search(
        r"保險單位給付項目"
        r"5單位10單位15單位20單位25單位30單位"
        r"住院日額\(最高365天\)"
        r"([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元"
        r"加護病房或燒燙傷中心日額\(最高365天\)"
        r"([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元([\d,]+)元"
        r"註[:：]每一保險單位為日額([\d,]+)元",
        table_text,
    )
    if not unit_match:
        return None
    amounts = [int(value.replace(",", "")) for value in unit_match.groups()]
    expected_row = [500, 1_000, 1_500, 2_000, 2_500, 3_000]
    if amounts[:6] != expected_row or amounts[6:12] != expected_row or amounts[12] != 100:
        return None

    hospital_start = text.find("住院日額保險金的給付")
    intensive_care_start = text.find("加護病房或燒燙傷中心日額保險金的給付")
    death_start = text.find("身故保險金的給付", intensive_care_start)
    disability_start = text.find("完全殘廢保險金的給付", death_start)
    maturity_start = text.find("滿期保險金的給付", disability_start)
    limit_start = text.find("保險給付的限制", maturity_start)
    if min(
        hospital_start,
        intensive_care_start,
        death_start,
        disability_start,
        maturity_start,
        limit_start,
    ) < 0:
        return None

    hospital_clause = text[hospital_start:intensive_care_start]
    intensive_care_clause = text[intensive_care_start:death_start]
    death_clause = text[death_start:disability_start]
    disability_clause = text[disability_start:maturity_start]
    maturity_clause = text[maturity_start:limit_start]
    limit_clause = text[limit_start : limit_start + 260]
    clause_checks = (
        "實際住院日數" in hospital_clause,
        "含始日及終日" in hospital_clause,
        "乘以當時有效之" in hospital_clause,
        "另按實際進住" in intensive_care_clause,
        "乘以當時有效之" in intensive_care_clause,
        "應已繳保險費" in death_clause and "保單價值準備金" in death_clause,
        "應已繳保險費" in disability_clause and "保單價值準備金" in disability_clause,
        "甲型" in maturity_clause and "乙型" in maturity_clause,
        "一千二百五十倍" in limit_clause,
    )
    if not all(clause_checks):
        return None

    hospital_page = source_page(text, hospital_start) or 3
    death_page = source_page(text, death_start) or hospital_page
    maturity_page = source_page(text, maturity_start) or death_page
    limit_page = source_page(text, limit_start) or maturity_page
    table_page = source_page(text, table_start)
    table_ref = "保單條款保險利益表" + (f"，第 {table_page} 頁" if table_page else "")
    same_stay_condition = (
        "出院後 14 日內於同一醫院再次住院，視為同一次住院"
        if "出院後十四日內於同一醫院再次住院" in text
        else "兩次以上住院且每次出院至下次住院未超過 14 日，視為同一次住院"
    )

    def plan_entries(plan: str) -> list[dict[str, Any]]:
        maturity_rate = 102 if plan == "plan-a" else 105
        plan_label = "甲型" if plan == "plan-a" else "乙型"
        return [
            coverage_entry(
                "hospital-daily",
                "住院日額保險金",
                100,
                "daily_per_unit",
                "每一保險單位的住院日額為每日 100 元；按同一次住院的實際住院日數給付。",
                f"保單條款第十三條，第 {hospital_page} 頁；{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    "經醫師診斷須住院，或於醫院持續診療達 6 小時（含）以上",
                    "包含入院及出院當日",
                    "每次住院最高給付 365 日",
                    "疾病須在契約生效滿 30 日後發生；復效後發生者依條款定義",
                    same_stay_condition,
                ],
            ),
            coverage_entry(
                "intensive-care-burn-center-daily",
                "加護病房或燒燙傷中心日額保險金",
                100,
                "daily_per_unit",
                "進住加護病房或燒燙傷中心期間，除住院日額外，每一保險單位每日另給付 100 元。",
                f"保單條款第十四條，第 {hospital_page} 頁；{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                conditions=["符合條件時另加住院日額給付", "包含始日及終日", "每次住院最高給付 365 日"],
            ),
            coverage_entry(
                "medical-lifetime-cap",
                "醫療保險金累計上限",
                125_000,
                "per_unit",
                "第十三條與第十四條合計給付上限為住院日額的 1,250 倍；每單位換算為 125,000 元。",
                f"保單條款第十八條，第 {limit_page} 頁；{table_ref}",
                calculation_basis="per_unit",
                amount_role="limit",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=[
                    "住院日額與加護病房或燒燙傷中心日額合併計入此上限",
                    "此為目前投保單位的名目累計上限；實際剩餘額須扣除已領醫療保險金，並確認是否曾減少單位",
                ],
            ),
            coverage_entry(
                "death-benefit",
                "身故保險金",
                None,
                "benefit_base",
                "取身故當時應已繳保險費（繳費期間內另加按日數比例計算的當期已繳未到期保費）與保單價值準備金二者較高者。",
                f"保單條款第十五條，第 {death_page} 頁",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="highest",
                rate_percent=100,
                conditions=["給付後契約終止", "實際金額需依保單年度、保費與當時保單價值準備金確認"],
            ),
            coverage_entry(
                "total-disability-benefit",
                "完全殘廢保險金",
                None,
                "benefit_base",
                "取完全殘廢診斷確定時應已繳保險費（繳費期間內另加按日數比例計算的當期已繳未到期保費）與保單價值準備金二者較高者。",
                f"保單條款第十六條，第 {death_page} 頁",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="highest",
                rate_percent=100,
                conditions=["須符合附件二完全殘廢程度之一", "給付後契約終止", "實際金額需依保單年度、保費與當時保單價值準備金確認"],
            ),
            coverage_entry(
                "maturity-benefit",
                f"滿期保險金（{plan_label}）",
                None,
                "benefit_base",
                f"被保險人於滿期日仍生存且契約有效時，按應已繳保險費的 {maturity_rate}% 給付。",
                f"保單條款第十七條，第 {maturity_page} 頁",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="per_policy",
                rate_percent=maturity_rate,
                conditions=["給付後契約終止", "實際金額需依保單面頁繳費年期、住院日額與標準體月繳保費確認"],
            ),
        ]

    fixed_plan = MEDICAL_ENDOWMENT_FIXED_PLAN_BY_PRODUCT_ID.get(product_id)
    if fixed_plan:
        plan_label = "甲型" if fixed_plan == "plan-a" else "乙型"
        return {
            "selection_type": "unit",
            "input_mode": "unit",
            "selection_source": "terms",
            "selection_label": "投保單位數",
            "selection_guidance": f"此版本名稱已標示{plan_label}；請填保單面頁的投保單位數，每一單位住院日額為 100 元。",
            "coverage_entries": plan_entries(fixed_plan),
        }

    return {
        "selection_type": "plan_unit",
        "input_mode": "plan_unit",
        "selection_source": "terms",
        "selection_label": "保障型別與投保單位數",
        "selection_guidance": "請依保單面頁選擇甲型或乙型，並填投保單位數；每一單位住院日額為 100 元。",
        "plan_options": [
            {"value": "plan-a", "label": "甲型", "coverage_entries": plan_entries("plan-a")},
            {"value": "plan-b", "label": "乙型", "coverage_entries": plan_entries("plan-b")},
        ],
    }


def parse_accident_abcd_plan_table(document: dict[str, Any]) -> dict[str, Any] | None:
    raw_text = str(document.get("text") or "")
    text = compact_whitespace(raw_text)
    signature = "各計畫別投保金額"
    table_start = text.find(signature)
    if table_start < 0:
        return None

    next_table = re.search(r"附表\s*二", text[table_start:])
    table_end = table_start + next_table.start() if next_table else min(len(text), table_start + 2_000)
    table_text = text[table_start:table_end]
    if not all(header in table_text for header in PLAN_HEADERS) or not all(
        signal in text for signal in REQUIRED_TERM_SIGNALS
    ):
        return None
    article_refs = article_references(text)
    if not article_refs:
        return None

    rows = list(PLAN_ROW_PATTERN.finditer(table_text))
    if [row.group(1) for row in rows] != ["A", "B", "C", "D"]:
        return None

    shared_region = table_text[rows[0].end() : rows[1].start()]
    shared_amounts = [
        (amount_in_ntd(match.group(1), match.group(2)), match.group(2))
        for match in AMOUNT_PATTERN.finditer(shared_region)
    ]
    aviation_amount = next((amount for amount, unit in shared_amounts if unit == "萬元"), None)
    daily_amount = next((amount for amount, unit in shared_amounts if unit == "元"), None)
    if not aviation_amount or not daily_amount:
        return None

    page = source_page(text, table_start)
    table_ref = "附表一" + (f"，第 {page} 頁" if page else "")
    disability_table_match = re.search(r"失能程度與保險金\s*給付表", text[table_end:])
    disability_table_start = table_end + disability_table_match.start() if disability_table_match else -1
    disability_table_text = text[disability_table_start:] if disability_table_start >= 0 else ""
    disability_percentages = [int(value) for value in re.findall(r"(\d{1,3})%", disability_table_text)]
    if not disability_percentages:
        return None
    disability_min_percent = min(disability_percentages)
    disability_max_percent = max(disability_percentages)
    plans = []
    for row in rows:
        plan, death, disability, medical = row.groups()
        death_amount = amount_in_ntd(death, "萬元")
        disability_amount = amount_in_ntd(disability, "萬元")
        medical_amount = amount_in_ntd(medical, "萬元")
        plans.append(
            {
                "value": plan,
                "label": f"計畫 {plan}",
                "coverage_entries": [
                    coverage_entry(
                        "accidental-death",
                        "意外傷害身故保險金",
                        death_amount,
                        "policy_total",
                        "符合條款約定的意外傷害身故時給付。",
                        f"保單條款{article_refs['death']}及{table_ref}",
                        calculation_basis="fixed_amount",
                        amount_role="payout",
                        limit_scope="per_event",
                    ),
                    coverage_entry(
                        "accidental-disability",
                        "意外傷害失能保險金",
                        disability_amount,
                        "benefit_base",
                        "實際給付依附表二比例"
                        f"（{disability_min_percent}% 至 {disability_max_percent}%）計算，"
                        f"約為 {disability_amount * disability_min_percent // 100:,} 元至 {disability_amount * disability_max_percent // 100:,} 元。",
                        f"保單條款{article_refs['disability']}、{table_ref}及附表二",
                        calculation_basis="percentage_of_base",
                        amount_role="base",
                        limit_scope="per_event",
                        rate_min_percent=disability_min_percent,
                        rate_max_percent=disability_max_percent,
                    ),
                    coverage_entry(
                        "injury-medical",
                        "傷害醫療保險金",
                        medical_amount,
                        "per_injury_limit",
                        "同一次傷害採實支實付，累計給付不超過本限額。",
                        f"保單條款{article_refs['medical']}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_injury",
                        aggregation_rule="cumulative_cap",
                    ),
                    coverage_entry(
                        "aviation-accidental-death",
                        "航空大眾運輸意外傷害身故保險金",
                        aviation_amount,
                        "additional_benefit",
                        "本項為額外給付；加上一般意外身故保險金，"
                        f"符合航空事故身故時合計 {death_amount + aviation_amount:,} 元。",
                        f"保單條款{article_refs['aviation']}及{table_ref}",
                        calculation_basis="additional_benefit",
                        amount_role="payout",
                        limit_scope="per_event",
                        aggregation_rule="conditional_additive",
                    ),
                    coverage_entry(
                        "hospital-daily",
                        "住院醫療日額保險金",
                        daily_amount,
                        "daily_total",
                        "按實際住院日數給付，含入院及出院當日；同一保單年度同一次住院最高 365 日。",
                        f"保單條款{article_refs['hospital']}及{table_ref}",
                        calculation_basis="per_day",
                        amount_role="payout",
                        limit_scope="per_day",
                    ),
                ],
            }
        )
    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "plan_options": plans,
    }


THREE_PLAN_HEADER_PATTERN = re.compile(
    r"附表\s*一\s*[:：]\s*投保計[劃畫]別內容\s*"
    r"單位\s*[:：]\s*新臺幣元\s*"
    r"項目\s*[\\/]\s*計[劃畫]別\s*"
    r"計[劃畫]一\s+計[劃畫]二\s+計[劃畫]三"
)
THREE_PLAN_ROW_LABELS = {
    "hospital_daily": "住院日額保險金",
    "inpatient_medical": "住院醫療費用保險金限額",
    "outpatient_surgery_or_procedure": "門診手術或特定處置費用保險金限額",
    "outpatient_visit": "住院前後門診保險金",
    "annual_cap": "每年保險金給付總限額",
}
THREE_PLAN_REQUIRED_HEADINGS = {
    "hospital_daily": "住院日額保險金之給付",
    "inpatient_medical": "住院醫療費用保險金（實支實付）之給付",
    "outpatient_surgery": "門診手術費用保險金（實支實付）之給付",
    "special_procedure": "特定處置費用保險金（實支實付）之給付",
    "outpatient_visit": "住院前後門診保險金之給付",
    "nhi_adjustment": "醫療費用未經全民健康保險給付者之處理方式",
    "benefit_limit": "保險金給付之限制",
}


def heading_article_references(text: str) -> dict[str, str]:
    references = {}
    for heading, article in re.findall(
        r"【([^】]+)】\s*第\s*([一二三四五六七八九十百零〇\d]+)\s*條",
        text,
    ):
        references[compact_whitespace(heading)] = f"第{article}條"
    return references


def parse_three_plan_row(table_text: str, label: str) -> list[int] | None:
    amount = r"([\d,]+)(?:\s*/\s*(?:日|次))?"
    match = re.search(
        rf"{re.escape(label)}\s+{amount}\s+{amount}\s+{amount}",
        table_text,
    )
    if not match:
        return None
    values = [int(match.group(index).replace(",", "")) for index in (1, 2, 3)]
    return values if all(value > 0 for value in values) else None


def parse_three_plan_medical_table(document: dict[str, Any]) -> dict[str, Any] | None:
    text = compact_whitespace(str(document.get("text") or ""))
    header = THREE_PLAN_HEADER_PATTERN.search(text)
    if not header:
        return None

    next_appendix = re.search(r"附表\s*二", text[header.end() :])
    table_end = header.end() + next_appendix.start() if next_appendix else min(
        len(text), header.end() + 2_000
    )
    table_text = text[header.start() : table_end]
    if re.search(r"計[劃畫]四", table_text):
        return None

    rows = {
        key: parse_three_plan_row(table_text, label)
        for key, label in THREE_PLAN_ROW_LABELS.items()
    }
    if any(values is None for values in rows.values()):
        return None

    article_refs = heading_article_references(text)
    if any(heading not in article_refs for heading in THREE_PLAN_REQUIRED_HEADINGS.values()):
        return None

    nhi_rate_match = re.search(
        r"實際支付之各項費用的\s*(\d{1,3})\s*%\s*給付",
        text,
    )
    if not nhi_rate_match:
        return None
    nhi_rate = int(nhi_rate_match.group(1))
    if not 0 < nhi_rate <= 100:
        return None

    page = source_page(text, header.start())
    table_ref = "附表一" + (f"，第 {page} 頁" if page else "")
    plan_labels = [("1", "計畫一"), ("2", "計畫二"), ("3", "計畫三")]
    plans = []
    for index, (plan_value, plan_label) in enumerate(plan_labels):
        hospital_daily = rows["hospital_daily"][index]
        inpatient_medical = rows["inpatient_medical"][index]
        surgery_or_procedure = rows["outpatient_surgery_or_procedure"][index]
        outpatient_visit = rows["outpatient_visit"][index]
        annual_cap = rows["annual_cap"][index]
        plans.append(
            {
                "value": plan_value,
                "label": plan_label,
                "coverage_entries": [
                    coverage_entry(
                        "hospital-daily",
                        "住院日額保險金",
                        hospital_daily,
                        "daily_total",
                        "按實際住院日數給付，金額依所選計畫計算。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['hospital_daily']]}及{table_ref}",
                        calculation_basis="per_day",
                        amount_role="payout",
                        limit_scope="per_day",
                    ),
                    coverage_entry(
                        "inpatient-medical-limit",
                        "住院醫療費用保險金限額",
                        inpatient_medical,
                        "per_event",
                        "住院醫療費用採實支實付並受本限額及年度總限額約束；"
                        f"未經全民健康保險給付時，依實際支付費用的 {nhi_rate}% 給付。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['inpatient_medical']]}、"
                        f"{article_refs[THREE_PLAN_REQUIRED_HEADINGS['nhi_adjustment']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_hospitalization",
                        aggregation_rule="cumulative_cap",
                    ),
                    coverage_entry(
                        "outpatient-surgery-limit",
                        "門診手術費用保險金限額",
                        surgery_or_procedure,
                        "per_event",
                        "門診手術費用採實支實付；若同時符合特定處置給付，兩者擇一給付。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['outpatient_surgery']]}、"
                        f"{article_refs[THREE_PLAN_REQUIRED_HEADINGS['benefit_limit']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_event",
                        aggregation_rule="choose_one",
                    ),
                    coverage_entry(
                        "special-procedure-limit",
                        "特定處置費用保險金限額",
                        surgery_or_procedure,
                        "per_event",
                        "特定處置費用採實支實付；若同時符合門診手術給付，兩者擇一給付。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['special_procedure']]}、"
                        f"{article_refs[THREE_PLAN_REQUIRED_HEADINGS['benefit_limit']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_event",
                        aggregation_rule="choose_one",
                    ),
                    coverage_entry(
                        "pre-post-outpatient",
                        "住院前後門診保險金",
                        outpatient_visit,
                        "per_event",
                        "依條款約定期間內的實際門診次數給付，每日最多一次。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['outpatient_visit']]}及{table_ref}",
                        calculation_basis="fixed_amount",
                        amount_role="payout",
                        limit_scope="per_event",
                        aggregation_rule="cumulative_cap",
                    ),
                    coverage_entry(
                        "annual-medical-cap",
                        "每年保險金給付總限額",
                        annual_cap,
                        "annual_limit",
                        "同一保單年度累計給付達本限額後，不再給付其他醫療保險金。",
                        f"保單條款{article_refs[THREE_PLAN_REQUIRED_HEADINGS['benefit_limit']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="annual",
                        aggregation_rule="cumulative_cap",
                    ),
                ],
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "plan_options": plans,
    }


FUBON_CANCER_HEADINGS = {
    "diagnosis": "罹患癌症保險金的給付",
    "hospital": "癌症住院醫療保險金的給付",
    "recovery": "癌症出院療養保險金的給付",
    "surgery": "癌症外科手術醫療保險金的給付",
    "outpatient": "癌症門診醫療保險金的給付",
    "radiation": "癌症放射線治療保險金的給付",
    "chemotherapy": "癌症化學治療保險金的給付",
    "hospice": "癌症安寧照護保險金的給付",
}
FUBON_CANCER_TABLE_PATTERN = re.compile(
    r"罹患癌症保險金.*?第一保單年度至第二十保單年度.*?"
    r"(?P<diagnosis_early>[\d,]+)\s*元.*?第二十一保單年度\s*\(\s*含\s*\)\s*起.*?"
    r"(?P<diagnosis_late>[\d,]+)\s*元.*?"
    r"癌症住院醫療保險金.*?第\s*1\s*-\s*90\s*日.*?"
    r"(?P<hospital_first>[\d,]+)\s*元\s*/\s*日.*?第\s*91\s*日起.*?"
    r"(?P<hospital_later>[\d,]+)\s*元\s*/\s*日.*?"
    r"癌症出院療養保險金\s+(?P<recovery>[\d,]+)\s*元\s*/\s*日.*?"
    r"癌症外科手術醫療保險金\s+(?P<surgery>[\d,]+)\s*元\s*/\s*次.*?"
    r"癌症門診醫療保險金\s+(?P<outpatient>[\d,]+)\s*元\s*/\s*日.*?"
    r"癌症放射線治療保險金\s+(?P<radiation>[\d,]+)\s*元\s*/\s*日.*?"
    r"癌症化學治療保險金\s+(?P<chemotherapy>[\d,]+)\s*元\s*/\s*日.*?"
    r"癌症安寧照護保險金.*?(?P<hospice>[\d,]+)\s*元\s*/\s*年",
)


def heading_reference(text: str, heading: str) -> str | None:
    match = re.search(
        rf"{re.escape(heading)}\s*】?.{{0,100}}?第\s*([一二三四五六七八九十百零〇廿卅卌\d]+)\s*條",
        text,
    )
    return f"第{match.group(1)}條" if match else None


def parse_fubon_cancer_unit_table(document: dict[str, Any]) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    table_start = text.rfind("附表一")
    if table_start < 0:
        return None
    table_text = text[table_start : min(len(text), table_start + 2_400)]
    if "每承保單位數給付金額" not in table_text:
        return None

    row_match = FUBON_CANCER_TABLE_PATTERN.search(table_text)
    if not row_match:
        return None
    amounts = {
        key: int(value.replace(",", ""))
        for key, value in row_match.groupdict().items()
    }
    if any(amount <= 0 for amount in amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in FUBON_CANCER_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    required_signals = [
        "實際承保有效之單位數",
        "百分之十五",
        "十四日內",
        "不論其每日門診次數為一次或多次",
        "不論其每日治療次數為一次或多次",
        "第二、三、四、五個罹患確定日之周年日",
    ]
    if not all(signal in text for signal in required_signals):
        return None

    early_cancer = (
        "癌症（初期）"
        if "癌症(初期)" in text
        else "第一期前列腺癌或原位癌"
    )
    hospice_exclusion = (
        "癌症（初期）不給付"
        if early_cancer == "癌症（初期）"
        else "第一期前列腺癌、原位癌或惡性黑色素瘤以外之皮膚癌不給付"
    )
    page = source_page(text, table_start)
    table_ref = "附表一" + (f"，第 {page} 頁" if page else "")
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{table_ref}"

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "cancer-diagnosis",
                "罹患癌症保險金",
                amounts["diagnosis_early"],
                "per_unit",
                "給付額依確診當時的保單年度級距；累計給付須扣除已領取的本項保險金。",
                terms_ref("diagnosis"),
                calculation_basis="tiered_or_stepped",
                amount_role="reference",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                amount_tiers=[
                    {
                        "label": "第 1 至 20 保單年度",
                        "amount": amounts["diagnosis_early"],
                    },
                    {
                        "label": "第 21 保單年度起",
                        "amount": amounts["diagnosis_late"],
                    },
                ],
                conditions=[
                    f"{early_cancer}按上述金額的 15% 給付",
                ],
            ),
            coverage_entry(
                "cancer-hospital-days-1-90",
                "癌症住院醫療保險金（同一次住院第 1 至 90 日）",
                amounts["hospital_first"],
                "daily_per_unit",
                "按同一次住院的實際住院日數給付。",
                terms_ref("hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-hospital-days-91-plus",
                "癌症住院醫療保險金（同一次住院第 91 日起）",
                amounts["hospital_later"],
                "daily_per_unit",
                "同一次住院超過 90 日後，按其後實際住院日數給付。",
                terms_ref("hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院療養保險金",
                amounts["recovery"],
                "daily_per_unit",
                "符合癌症住院醫療給付並出院後，按該次實際住院日數計算。",
                terms_ref("recovery"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-surgery",
                "癌症外科手術醫療保險金",
                amounts["surgery"],
                "per_unit",
                "每次切除手術給付；同一癌症、同一手術位置於前次手術日起 14 日內的手術視為同一次。",
                terms_ref("surgery"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                conditions=[f"治療{early_cancer}時按每次金額的 15% 給付"],
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                amounts["outpatient"],
                "daily_per_unit",
                "按實際接受門診治療的日數給付；同一日多次門診仍以一日計。",
                terms_ref("outpatient"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線治療保險金",
                amounts["radiation"],
                "daily_per_unit",
                "住院或門診接受放射線治療均適用；同一日多次治療仍以一日計。",
                terms_ref("radiation"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學治療保險金",
                amounts["chemotherapy"],
                "daily_per_unit",
                "住院或門診接受化學治療均適用；同一日多次治療仍以一日計。",
                terms_ref("chemotherapy"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-hospice-anniversary",
                "癌症安寧照護保險金",
                amounts["hospice"],
                "per_unit",
                "自罹患確定日起算第 1 至第 5 個周年日仍生存時，每一周年各給付一次。",
                terms_ref("hospice"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="annual",
                aggregation_rule="cumulative_cap",
                conditions=[hospice_exclusion, "第 6 年起不再給付"],
            ),
        ],
    }


PRUDENTIAL_CANCER_HEADINGS = {
    "hospital": "癌症住院醫療保險金及其申領",
    "surgery": "癌症住院手術費用保險金及其申領",
    "recovery": "癌症出院後療養保險金及其申領",
    "outpatient": "癌症門診醫療保險金及其申領",
    "radiation": "癌症放射線醫療保險金及其申領",
    "chemotherapy": "癌症化學醫療保險金及其申領",
    "marrow": "癌症骨髓移植保險金及其申領",
    "prosthetic_limb": "癌症義肢裝設保險金及其申領",
    "dentures": "癌症義齒裝設保險金及其申領",
    "termination": "附約的終止",
}
PRUDENTIAL_CANCER_TABLE_PATTERN = re.compile(
    r"附表\s*(?P<appendix>[二三])\s*幣值單位.*?"
    r"給付項目\s*每投保單位給付之保險金.*?"
    r"癌症住院醫療保險金\s*\(\s*每日\s*\)\s*(?P<hospital>[\d,]+)\s*元.*?"
    r"癌症住院手術費用保險金\s*(?P<surgery>[\d,]+)\s*元.*?"
    r"癌症出院後療養保險金\s*\(\s*每日\s*\)\s*(?P<recovery>[\d,]+)\s*元.*?"
    r"癌症門診醫療保險金\s*\(\s*每日\s*\)\s*(?P<outpatient>[\d,]+)\s*元.*?"
    r"癌症放射線醫療保險金\s*\(\s*每日\s*\)\s*(?P<radiation>[\d,]+)\s*元.*?"
    r"癌症化學醫療保險金\s*\(\s*每日\s*\)\s*(?P<chemotherapy>[\d,]+)\s*元.*?"
    r"癌症骨髓移植保險金\s*(?P<marrow>[\d,]+)\s*元.*?"
    r"癌症義肢裝設保險金\s*(?P<prosthetic_limb>[\d,]+)\s*元.*?"
    r"癌症義齒裝設保險金\s*(?P<dentures>[\d,]+)\s*元"
)


def parse_prudential_cancer_account_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    table_matches = list(PRUDENTIAL_CANCER_TABLE_PATTERN.finditer(text))
    if len(table_matches) != 1:
        return None
    table_match = table_matches[0]
    amounts = {
        key: int(value.replace(",", ""))
        for key, value in table_match.groupdict().items()
        if key != "appendix"
    }
    if any(amount <= 0 for amount in amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in PRUDENTIAL_CANCER_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    required_signals = [
        "本附約累積給付保險金總額每投保單位超過新台幣二百萬元時",
        "每次住院期間以給付一次為限",
        "接受骨髓移植醫療時,不給付本項住院手術費用保險金",
        "不論其每日門診次數為一次或多次",
        "不論其每日接受放射線治療次數為一次或多次",
        "不論其每日接受化學治療次數為一次或多次",
        "四肢各以給付一次為限",
        "同一保單年度內以給付一次為限",
    ]
    if not all(signal in text for signal in required_signals):
        return None

    page = source_page(text, table_match.start())
    appendix_ref = f"附表{table_match.group('appendix')}" + (
        f"，第 {page} 頁" if page else ""
    )
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{appendix_ref}"

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                amounts["hospital"],
                "daily_per_unit",
                "按實際住院日數給付，包含入院及出院當日。",
                terms_ref("hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-inpatient-surgery",
                "癌症住院手術費用保險金",
                amounts["surgery"],
                "per_unit",
                "每次住院期間限給付一次；接受骨髓移植醫療時不另給付本項。",
                terms_ref("surgery"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_hospitalization",
                aggregation_rule="choose_one",
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院後療養保險金",
                amounts["recovery"],
                "daily_per_unit",
                "出院後按該次實際住院日數給付，包含入院及出院當日。",
                terms_ref("recovery"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                amounts["outpatient"],
                "daily_per_unit",
                "未住院期間接受必要門診治療時給付；同日多次及同一療程依條款合併計次。",
                terms_ref("outpatient"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線醫療保險金",
                amounts["radiation"],
                "daily_per_unit",
                "住院或門診接受放射線治療均適用；同一日多次治療仍以一日計。",
                terms_ref("radiation"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學醫療保險金",
                amounts["chemotherapy"],
                "daily_per_unit",
                "住院或門診接受化學治療均適用；同一日多次治療仍以一日計。",
                terms_ref("chemotherapy"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-marrow-transplant",
                "癌症骨髓移植保險金",
                amounts["marrow"],
                "per_unit",
                "符合條款並接受骨髓移植治療時給付；不與同次住院手術費用保險金併計。",
                terms_ref("marrow"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="choose_one",
            ),
            coverage_entry(
                "cancer-prosthetic-limb",
                "癌症義肢裝設保險金",
                amounts["prosthetic_limb"],
                "per_unit",
                "因癌症或併發症截肢並裝設義肢時給付；附約有效期間內四肢各限一次。",
                terms_ref("prosthetic_limb"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "cancer-dentures",
                "癌症義齒裝設保險金",
                amounts["dentures"],
                "per_unit",
                "因癌症或相關治療而需裝設義齒時給付；同一保單年度限一次。",
                terms_ref("dentures"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="annual",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "cancer-total-benefit-threshold",
                "癌症保險金累積給付終止門檻",
                2_000_000,
                "per_unit",
                "含續保期間的各項保險金累積總額每單位超過 200 萬元時，附約依條款終止；條款未明示將最後一次給付截減至本門檻。",
                f"保單條款{article_refs['termination']}",
                calculation_basis="per_unit",
                amount_role="reference",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
            ),
        ],
    }


KGI_CHINA_LIFE_CANCER_ACCOUNT_TITLE = "一年定期癌症醫療帳戶型健康保險附約"
KGI_CHINA_LIFE_CANCER_ACCOUNT_ID = re.compile(
    r"205321(?:R11A545\d{2}|RZ1A00121A11Z100000\d{2})"
)
KGI_CHINA_LIFE_CANCER_ACCOUNT_AMOUNTS = (
    2_000,
    30_000,
    1_000,
    1_000,
    3_000,
    3_000,
    100_000,
    20_000,
    20_000,
    2_000_000,
)


def normalize_kgi_china_life_cancer_account_text(text: str) -> str:
    normalized = normalize_terms_text(text)
    normalized = re.sub(r"(?:附表){2,4}三{2,4}", "附表三", normalized)
    normalized = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", normalized)
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    normalized = normalized.replace(
        "每投保單位給付之保險金給付項癌症",
        "給付項目每投保單位給付之保險金癌症",
    )
    corrections = {
        "要保人名定本附約所稱": "要保人【名詞定義】 第二條本附約所稱",
        "癌症住院醫療葆險金及其申領": "癌症住院醫療保險金及其申領",
        "癌症門診醫療保險命其申": "癌症門診醫療保險金及其申領",
        "癌症骨髓移植保險金及其申領 】 第十九被": (
            "癌症骨髓移植保險金及其申領 】 第十九條被"
        ),
        "癌症義肢裝設呆險金及其申領": "癌症義肢裝設保險金及其申領",
        "不論其母钙一籔為一次或多次": "不論其每日門診次數為一次或多次",
    }
    for source, replacement in corrections.items():
        normalized = normalized.replace(source, replacement)
    return re.sub(
        r"接受骨髓移植醫療時\s*,\s*不給付本項住院手術費用保險金",
        "接受骨髓移植醫療時,不給付本項住院手術費用保險金",
        normalized,
    )


def parse_kgi_china_life_cancer_account_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    if (
        document.get("document_type") != "policy_terms"
        or not KGI_CHINA_LIFE_CANCER_ACCOUNT_ID.fullmatch(product_id)
    ):
        return None

    text = normalize_kgi_china_life_cancer_account_text(
        str(document.get("text") or "")
    )
    if KGI_CHINA_LIFE_CANCER_ACCOUNT_TITLE not in text:
        return None
    definition_ref = heading_reference(text, "名詞定義")
    if not definition_ref:
        return None
    if not all(
        signal in text
        for signal in ["等待期間", "本附約生效日起算九十日", "等待期間屆滿後"]
    ):
        return None

    schedule = parse_prudential_cancer_account_unit_table(
        {**document, "text": text}
    )
    if not schedule:
        return None
    amount_signature = tuple(
        int(entry.get("amount") or 0) for entry in schedule["coverage_entries"]
    )
    if amount_signature != KGI_CHINA_LIFE_CANCER_ACCOUNT_AMOUNTS:
        return None

    page_markers = list(re.finditer(r"(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)", text))
    if page_markers:
        appendix_page, page_total = (
            int(value) for value in page_markers[-1].groups()
        )
    else:
        aucr_markers = list(
            re.finditer(
                r"【\s*AUCR\s*】\s*-\s*(\d+)(?:\s*/\s*(\d+))?\s*-",
                text,
            )
        )
        if not aucr_markers:
            return None
        page, total = aucr_markers[-1].groups()
        appendix_page = int(page)
        page_total = int(total or page)
    if appendix_page <= 0 or appendix_page > page_total:
        return None

    waiting_condition = "癌症保障限附約生效日起 90 日（含）的等待期間屆滿後發生"
    if "復效日起算九十日" in text:
        waiting_condition += "；復效時另自復效日起算 90 日（含）"
    for entry in schedule["coverage_entries"]:
        if entry.get("amount_role") != "payout":
            continue
        conditions = [waiting_condition, *(entry.get("conditions") or [])]
        entry["conditions"] = list(dict.fromkeys(conditions))
        entry["source_ref"] = entry["source_ref"].replace(
            "保單條款",
            f"保單條款{definition_ref}、",
            1,
        )
        entry["source_ref"] = re.sub(
            r"附表三(?:，第 \d+ 頁)?",
            f"附表三，第 {appendix_page} 頁",
            entry["source_ref"],
        )
    return schedule


PRUDENTIAL_FIVE_YEAR_HEADINGS = {
    "termination": "累積總給付金額限制與附約的終止",
    "hospital": "癌症住院醫療保險金及其申領",
    "surgery": "癌症住院手術費用保險金及其申領",
    "recovery": "癌症出院後療養保險金及其申領",
    "outpatient": "癌症門診醫療保險金及其申領",
    "radiation": "癌症放射線醫療保險金及其申領",
    "chemotherapy": "癌症化學治療保險金及其申領",
    "marrow": "癌症骨髓移植保險金及其申領",
    "prosthetic_limb": "癌症義肢裝設保險金及其申領",
    "dentures": "癌症義齒裝設保險金及其申領",
}
PRUDENTIAL_FIVE_YEAR_ROWS = {
    "hospital": ("癌症住院醫療保險金", "每日"),
    "recovery": ("癌症出院後療養保險金", "每日"),
    "outpatient": ("癌症門診醫療保險金", "每日"),
    "radiation": ("癌症放射線醫療保險金", "每日"),
    "chemotherapy": ("癌症化學治療保險金", "每日"),
    "marrow": ("癌症骨髓移植保險金", "每次"),
    "prosthetic_limb": ("癌症義肢裝設保險金", "每次"),
    "dentures": ("癌症義齒裝設保險金", "每次"),
}


def appendix_row_amount(table_text: str, label: str, cadence: str) -> int | None:
    match = re.search(
        rf"{re.escape(label)}\s*\(\s*{re.escape(cadence)}\s*\)\s*([\d,]+)\s*元",
        table_text,
    )
    if not match:
        return None
    amount = int(match.group(1).replace(",", ""))
    return amount if amount > 0 else None


def parse_prudential_cancer_five_year_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    table_start = text.rfind("【附件三】")
    if table_start < 0:
        return None
    table_end = text.find("【附件四】", table_start)
    table_text = text[table_start : table_end if table_end >= 0 else table_start + 2_500]
    if "每投保單位給付之保險金" not in table_text:
        return None

    amounts = {
        key: appendix_row_amount(table_text, label, cadence)
        for key, (label, cadence) in PRUDENTIAL_FIVE_YEAR_ROWS.items()
    }
    surgery_match = re.search(
        r"非原位癌之癌症\s*(?P<non_in_situ>[\d,]+)\s*元\s*"
        r"癌症住院手術費用保險金\s*\(\s*每次\s*\)\s*"
        r"原位癌\s*(?P<in_situ>[\d,]+)\s*元",
        table_text,
    )
    if any(amount is None for amount in amounts.values()) or not surgery_match:
        return None
    surgery_amounts = {
        key: int(value.replace(",", ""))
        for key, value in surgery_match.groupdict().items()
    }
    if any(amount <= 0 for amount in surgery_amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in PRUDENTIAL_FIVE_YEAR_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    required_signals = [
        "累積給付保險金總額每投保單位達新台幣二百萬元",
        "接受骨髓移植醫療、義肢裝設及義齒裝設時,不給付本項手術費用保險金",
        "不論其每日門診次數為一次或多次,均以一日計",
        "不論其每日接受放射線醫療次數為一次或多次,均以一日計",
        "不論其每日接受化學治療次數為一次或多次,均以一日計",
        "同一保單年度內以給付一次為限",
    ]
    if not all(signal in text for signal in required_signals):
        return None

    page = source_page(text, table_start)
    appendix_ref = "附件三" + (f"，第 {page} 頁" if page else "")
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{appendix_ref}"

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                amounts["hospital"],
                "daily_per_unit",
                "按投保單位及實際住院日數給付，住院始日與終日均計入。",
                terms_ref("hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-inpatient-surgery",
                "癌症住院手術費用保險金",
                surgery_amounts["non_in_situ"],
                "per_unit",
                "每次住院期間依癌症類型擇一給付；骨髓移植、義肢及義齒裝設不另給付本項。",
                terms_ref("surgery"),
                calculation_basis="tiered_or_stepped",
                amount_role="reference",
                limit_scope="per_hospitalization",
                aggregation_rule="choose_one",
                amount_tiers=[
                    {
                        "label": "非原位癌之癌症",
                        "amount": surgery_amounts["non_in_situ"],
                    },
                    {"label": "原位癌", "amount": surgery_amounts["in_situ"]},
                ],
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院後療養保險金",
                amounts["recovery"],
                "daily_per_unit",
                "按投保單位及該次住院日數給付出院後療養保險金。",
                terms_ref("recovery"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                amounts["outpatient"],
                "daily_per_unit",
                "按實際門診治療日數給付，同一日不論門診次數均以一日計。",
                terms_ref("outpatient"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線醫療保險金",
                amounts["radiation"],
                "daily_per_unit",
                "按實際接受放射線醫療日數給付，同一日多次仍以一日計。",
                terms_ref("radiation"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學治療保險金",
                amounts["chemotherapy"],
                "daily_per_unit",
                "按實際接受化學治療日數給付，同一日多次仍以一日計。",
                terms_ref("chemotherapy"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "cancer-marrow-transplant",
                "癌症骨髓移植保險金",
                amounts["marrow"],
                "per_unit",
                "每次接受符合條款約定的骨髓移植治療時給付。",
                terms_ref("marrow"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="choose_one",
            ),
            coverage_entry(
                "cancer-prosthetic-limb",
                "癌症義肢裝設保險金",
                amounts["prosthetic_limb"],
                "per_unit",
                "因癌症接受截肢手術並裝設義肢時，依條款約定給付。",
                terms_ref("prosthetic_limb"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "cancer-dentures",
                "癌症義齒裝設保險金",
                amounts["dentures"],
                "per_unit",
                "因癌症或相關治療裝設義齒時給付，同一保單年度以一次為限。",
                terms_ref("dentures"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="annual",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "cancer-total-benefit-threshold",
                "癌症保險金累積給付終止門檻",
                2_000_000,
                "per_unit",
                "每投保單位累積給付保險金達 200 萬元時，本附約依條款約定終止。",
                f"保單條款{article_refs['termination']}",
                calculation_basis="per_unit",
                amount_role="reference",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
            ),
        ],
    }


KGI_CHINA_LIFE_FIVE_YEAR_TITLE = "癌症五年定期醫療保險附約(96)"
KGI_CHINA_LIFE_FIVE_YEAR_HEADINGS = {
    "definition": "名詞定義",
    **PRUDENTIAL_FIVE_YEAR_HEADINGS,
}


def parse_kgi_china_life_cancer_five_year_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    text = normalize_terms_text(str(document.get("text") or ""))
    if not product_id.startswith("205321") or KGI_CHINA_LIFE_FIVE_YEAR_TITLE not in text:
        return None

    table_start = text.rfind("附件三")
    if table_start < 0:
        return None
    table_end = text.find("附件四", table_start)
    table_text = text[table_start : table_end if table_end >= 0 else table_start + 2_500]
    if "每投保單位給付之保險金" not in table_text:
        return None
    table_text = re.sub(r"(?<=\d)\s*,\s*(?=\d)", ",", table_text)
    table_text = re.sub(r"(?<=\d)\s+(?=\d)", "", table_text)

    amounts = {
        key: appendix_row_amount(table_text, label, cadence)
        for key, (label, cadence) in PRUDENTIAL_FIVE_YEAR_ROWS.items()
    }
    surgery_patterns = [
        re.compile(
            r"非原位癌之癌症\s*(?P<non_in_situ>[\d,]+)\s*元\s*"
            r"癌症住院手術費用保險金\s*\(\s*每次\s*\)\s*"
            r"原位癌\s*(?P<in_situ>[\d,]+)\s*元"
        ),
        re.compile(
            r"癌症住院手術費用保險金\s*\(\s*每次\s*\)\s*"
            r"非原位癌之癌症\s*(?P<non_in_situ>[\d,]+)\s*元\s*"
            r"原位癌\s*(?P<in_situ>[\d,]+)\s*元"
        ),
    ]
    surgery_match = next(
        (pattern.search(table_text) for pattern in surgery_patterns if pattern.search(table_text)),
        None,
    )
    if any(amount is None for amount in amounts.values()) or not surgery_match:
        return None
    surgery_amounts = {
        key: int(value.replace(",", ""))
        for key, value in surgery_match.groupdict().items()
    }
    if any(amount <= 0 for amount in surgery_amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in KGI_CHINA_LIFE_FIVE_YEAR_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None

    termination_match = re.search(
        r"累積給付保險金總額每投保單位達新台幣"
        r"(?P<amount>[一二三四五六七八九十百零〇]+)萬元"
        r"\s*時\s*[,，]?\s*本附約效力即行終止",
        text,
    )
    if not termination_match:
        return None
    threshold = integer_from_arabic_or_chinese(termination_match.group("amount")) * 10_000
    if threshold not in {500_000, 2_000_000}:
        return None
    amount_signature = (
        amounts["hospital"],
        surgery_amounts["non_in_situ"],
        surgery_amounts["in_situ"],
        amounts["recovery"],
        amounts["outpatient"],
        amounts["radiation"],
        amounts["chemotherapy"],
        amounts["marrow"],
        amounts["prosthetic_limb"],
        amounts["dentures"],
        threshold,
    )
    allowed_signatures = {
        (2_000, 30_000, 3_000, 1_000, 1_000, 3_000, 3_000, 100_000, 20_000, 20_000, 2_000_000),
        (500, 7_500, 750, 250, 250, 750, 750, 25_000, 5_000, 5_000, 500_000),
    }
    if amount_signature not in allowed_signatures:
        return None

    waiting_start = text.find("等待期間屆滿後")
    if waiting_start < 0:
        return None
    waiting_text = text[max(0, waiting_start - 180) : waiting_start + 900]
    if not all(
        signal in waiting_text
        for signal in ["本附約承保之", "本附約生效日", "九十日"]
    ):
        return None

    required_signals = [
        "接受骨髓移植醫療",
        "義肢裝設",
        "義齒裝設",
        "不給付本項手術費用保險金",
        "每日門診次數",
        "每日接受放射線醫療次數",
        "每日接受化學治療次數",
        "同一保單年度內以給付一次為限",
    ]
    if not all(signal in text for signal in required_signals):
        return None

    waiting_condition = "癌症保障限附約生效日起 90 日（含）的等待期間屆滿後發生"
    if "復效日起算九十日" in waiting_text:
        waiting_condition += "；復效時另自復效日起算 90 日（含）"

    page = source_page(text, table_start)
    appendix_ref = "附件三" + (f"，第 {page} 頁" if page else "")
    terms_ref = lambda key: (
        f"保單條款{article_refs['definition']}、{article_refs[key]}及{appendix_ref}"
    )

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                amounts["hospital"],
                "daily_per_unit",
                "按投保單位及實際住院日數給付，住院始日與終日均計入。",
                terms_ref("hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-inpatient-surgery",
                "癌症住院手術費用保險金",
                surgery_amounts["non_in_situ"],
                "per_unit",
                "每次住院期間依癌症類型擇一給付。",
                terms_ref("surgery"),
                calculation_basis="tiered_or_stepped",
                amount_role="reference",
                limit_scope="per_hospitalization",
                aggregation_rule="choose_one",
                amount_tiers=[
                    {
                        "label": "非原位癌之癌症",
                        "amount": surgery_amounts["non_in_situ"],
                    },
                    {"label": "原位癌", "amount": surgery_amounts["in_situ"]},
                ],
                conditions=[
                    waiting_condition,
                    "骨髓移植、義肢及義齒裝設不給付本項手術費用保險金",
                ],
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院後療養保險金",
                amounts["recovery"],
                "daily_per_unit",
                "按投保單位及該次住院日數給付出院後療養保險金。",
                terms_ref("recovery"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                amounts["outpatient"],
                "daily_per_unit",
                "按實際門診治療日數給付，同一日不論門診次數均以一日計。",
                terms_ref("outpatient"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線醫療保險金",
                amounts["radiation"],
                "daily_per_unit",
                "按實際接受放射線醫療日數給付，同一日多次仍以一日計。",
                terms_ref("radiation"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學治療保險金",
                amounts["chemotherapy"],
                "daily_per_unit",
                "按實際接受化學治療日數給付，同一日多次仍以一日計。",
                terms_ref("chemotherapy"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-marrow-transplant",
                "癌症骨髓移植保險金",
                amounts["marrow"],
                "per_unit",
                "每次接受符合條款約定的骨髓移植治療時給付。",
                terms_ref("marrow"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="choose_one",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-prosthetic-limb",
                "癌症義肢裝設保險金",
                amounts["prosthetic_limb"],
                "per_unit",
                "因癌症接受截肢手術並裝設義肢時，依條款約定給付。",
                terms_ref("prosthetic_limb"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                aggregation_rule="cumulative_cap",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-dentures",
                "癌症義齒裝設保險金",
                amounts["dentures"],
                "per_unit",
                "因癌症或相關治療裝設義齒時給付。",
                terms_ref("dentures"),
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="annual",
                aggregation_rule="cumulative_cap",
                conditions=[waiting_condition, "同一保單年度以給付一次為限"],
            ),
            coverage_entry(
                "cancer-total-benefit-threshold",
                "癌症保險金累積給付終止門檻",
                threshold,
                "per_unit",
                f"每投保單位累積給付保險金達 {threshold:,} 元時，本附約依條款約定終止。",
                f"保單條款{article_refs['termination']}",
                calculation_basis="per_unit",
                amount_role="reference",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
            ),
        ],
    }


FUBON_INPATIENT_HEADINGS = {
    "medical": "住院醫療費用保險金之給付",
    "daily_option": "住院日額補償保險金選擇給付",
    "benefit_limit": "保險金給付之限制",
    "nhi_adjustment": "醫療費用未經全民健康保險給付者之處理方式",
}
FUBON_INPATIENT_PRODUCT_VERSIONS = {
    "209311R11A00310": {
        "document_code": "NHR11030501",
        "required_revision_signal": "103.05.01富壽商精字第1030000520號函備查",
        "required_version_signals": (
            "自本公司收到要保人書面通知時,開始生效",
            "本公司於必要時得經其同意調閱被保險人之就醫相關資料",
            "因投保年齡的錯誤,而致短繳保險費者,應補足其差額",
        ),
    },
    "209311RZ1A00721A11Z10000011": {
        "document_code": "NHR11040804",
        "required_revision_signal": "104.08.04依104.06.24金管保壽字第10402049830號函修正",
        "required_version_signals": (
            "自本公司收到要保人書面或其他約定方式通知時,開始生效",
            "真實投保年齡較本公司保險費率表所載最高年齡為大者,本附約無效",
            "本公司於必要時得經其同意調閱被保險人之就醫相關資料",
        ),
    },
    "209311RZ1A00721A11Z10000012": {
        "document_code": "NHR11090101",
        "required_revision_signal": "109.01.01依108.04.09金管保壽字第10804904941號函修正",
        "required_version_signals": (
            "中央衛生主管機關所公告「遺傳性疾病之新生兒先天性代謝異常疾病檢查項目」",
            "得徵詢其他醫師之醫學專業意見",
            "真實投保年齡較本公司保險費率表所載最高年齡為大者,本附約無效",
        ),
    },
    "209311RZ1A00721A11Z10000013": {
        "document_code": "NHR11090701",
        "required_revision_signal": "109.07.01依108.12.30金管保壽字第1080439731號函修正",
        "required_version_signals": (
            "中央衛生主管機關所公告「遺傳性疾病之新生兒先天性代謝異常疾病檢查項目」",
            "得徵詢其他醫師之醫學專業意見",
            "基於保戶服務,本公司於保險契約停止效力後至得申請復效之期限屆滿前三個月",
        ),
    },
}
FUBON_INPATIENT_LEGACY_PRODUCT_IDS = {
    "209311R11A00305",
    "209311R11A00306",
    "209311R11A00308",
    "209311R11A00309",
}
FUBON_INPATIENT_FILE_PATTERN = re.compile(
    r"(?:209311R11A00310|209311RZ1A00721A11Z1000001[123])-[AF]\.pdf"
)
FUBON_INPATIENT_EXPECTED_AMOUNTS = {
    "room": 110,
    "icu": 220,
    "burn_center": 330,
    "inpatient_medical": 8_800,
    "home_recovery": 66,
    "surgery": 5_500,
    "surgery_recovery": 1_650,
}
FUBON_INPATIENT_DAILY_AMOUNT = 143
FUBON_INPATIENT_SURGERY_RATE_COUNT = 123
FUBON_INPATIENT_SURGERY_RATES_SHA256 = (
    "b3869a4f52d37ac3b40dfc69176b6467d21fd44ae102c30d439e3f1ea2e2fba6"
)
FUBON_INPATIENT_ROWS = {
    "room": ("每日病房費用保險金", "每日"),
    "icu": ("加護病房費用保險金", "每日"),
    "burn_center": ("燒燙傷中心費用保險金", "每日"),
    "inpatient_medical": ("住院醫療費用保險金", "每次"),
    "home_recovery": ("出院在家療養保險金", "每日"),
    "surgery": ("手術費用保險金", "每次"),
    "surgery_recovery": ("手術出院療養保險金", "每次"),
}


def is_fubon_inpatient_medical_strict_source(document: dict[str, Any]) -> bool:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    dense_text = re.sub(
        r"\s+", "", normalize_terms_text(str(document.get("text") or ""))
    )
    return (
        product_id in FUBON_INPATIENT_PRODUCT_VERSIONS
        or FUBON_INPATIENT_FILE_PATTERN.fullmatch(file_name) is not None
        or any(
            version["document_code"] in dense_text
            for version in FUBON_INPATIENT_PRODUCT_VERSIONS.values()
        )
    )


def limit_table_row_amount(table_text: str, label: str, cadence: str) -> int | None:
    match = re.search(
        rf"{re.escape(label)}\s*{re.escape(cadence)}\s*([\d,]+)\s*元",
        table_text,
    )
    if not match:
        return None
    amount = int(match.group(1).replace(",", ""))
    return amount if amount > 0 else None


def parse_fubon_inpatient_medical_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    version = FUBON_INPATIENT_PRODUCT_VERSIONS.get(product_id)
    legacy_source = product_id in FUBON_INPATIENT_LEGACY_PRODUCT_IDS
    if (
        (version is None and not legacy_source)
        or document.get("document_type") != "policy_terms"
        or file_name != f"{product_id}-A.pdf"
        or (
            version is not None
            and (
                document.get("page_count") != 10
                or document.get("pages_parsed") != 10
            )
        )
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    dense_text = re.sub(r"\s+", "", text)
    document_code = version["document_code"] if version else None
    if version is not None:
        if (
            dense_text.count(document_code) != 10
            or any(
                f"{document_code}{page}/10" not in dense_text
                for page in range(1, 11)
            )
            or version["required_revision_signal"] not in dense_text
            or not all(
                signal in dense_text
                for signal in version["required_version_signals"]
            )
        ):
            return None

        required_document_signals = (
            "富邦人壽新綜合住院醫療保險附約",
            "商品代號:NHR1",
            "自本附約生效日起持續有效三十日或復效日以後所發生之疾病",
            "不包含全民健康保險法第五十一條所稱之日間住院",
            "同一次住院最高給付日數以三百六十五日為限",
            "每次手術費用保險金限額",
            "本公司按本條第一款所支付「每日病房費用保險金」的百分之六十給付",
            "本公司按本條第五款所支付「手術費用保險金」的百分之三十給付",
            "於出院後十四日內再次住院時",
            "超過的天數加倍給付",
            "最高僅以三十二日為限",
            "則不得再申領第十二條各項保險金",
            "已獲得全民健康保險給付的部分,本公司不予給付保險金",
            "實際支付之各項費用之六十五%給付",
            "半年繳總保費=年繳總保費×0.520",
            "季繳總保費=年繳總保費×0.262",
            "月繳總保費=年繳總保費×0.088",
        )
        if (
            not all(signal in dense_text for signal in required_document_signals)
            or dense_text.count("同一次住院最高給付日數以九十日為限")
            != 2
        ):
            return None

    table_start_in_text = text.rfind("附表一")
    table_start = dense_text.rfind("附表一")
    if table_start < 0:
        return None
    table_end = dense_text.find("附表二", table_start)
    if table_end < 0:
        return None
    table_text = dense_text[table_start:table_end]
    if "每一單位給付限額" not in table_text or "每一單位給付金額" not in table_text:
        return None

    amounts = {
        key: limit_table_row_amount(table_text, label, cadence)
        for key, (label, cadence) in FUBON_INPATIENT_ROWS.items()
    }
    if legacy_source and amounts["burn_center"] is None:
        amounts["burn_center"] = limit_table_row_amount(
            table_text, "燒燙傷中心病房費用保險金", "每日"
        )
    daily_amount = limit_table_row_amount(
        table_text, "住院醫療定額保險金", "每日"
    )
    if (
        amounts != FUBON_INPATIENT_EXPECTED_AMOUNTS
        or daily_amount != FUBON_INPATIENT_DAILY_AMOUNT
    ):
        return None

    expected_tiers = (
        ("31~60", 2),
        ("61~90", 3),
        ("91~180", 4),
        ("181~365", 5),
    )
    if not all(
        f"住院天數{days}天者,每次「住院醫療費用保險金」給付限額為上表之{multiplier}倍"
        in table_text
        for days, multiplier in expected_tiers
    ):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in FUBON_INPATIENT_HEADINGS.items()
    }
    if article_refs != {
        "medical": "第十二條",
        "daily_option": "第十四條",
        "benefit_limit": "第十九條",
        "nhi_adjustment": "第二十條",
    }:
        return None

    nhi_match = re.search(
        r"實際支付之各項費用之([一二三四五六七八九十百零〇\d]{1,5})%給付",
        dense_text,
    )
    if not nhi_match:
        return None
    nhi_rate = integer_from_arabic_or_chinese(nhi_match.group(1))
    if nhi_rate != 65:
        return None

    if version is not None:
        page_ten_start = dense_text.find(f"{document_code}10/10", table_end)
        if page_ten_start < 0:
            return None
        surgery_table_text = dense_text[table_end:page_ten_start]
    else:
        surgery_table_text = dense_text[table_end:]
    required_surgery_table_signals = (
        "附表二:手術項目給付比率表",
        "A、腹部和消化系統",
        "剖腹探查術、結腸切開術65%",
        "三個瓣膜置換術500%",
        "N、泌尿系統",
        "膀胱切開伴隨尿道導管插入63%",
        "如手術項目未包括於上表時",
    )
    if not all(signal in surgery_table_text for signal in required_surgery_table_signals):
        return None
    surgery_rates = [
        int(value) for value in re.findall(r"(?<!\d)(\d{1,3})\s*%", surgery_table_text)
    ]
    surgery_rate_signature = hashlib.sha256(
        ",".join(str(rate) for rate in surgery_rates).encode("ascii")
    ).hexdigest()
    if (
        len(surgery_rates) != FUBON_INPATIENT_SURGERY_RATE_COUNT
        or surgery_rate_signature != FUBON_INPATIENT_SURGERY_RATES_SHA256
    ):
        return None
    surgery_min = min(surgery_rates)
    surgery_max = max(surgery_rates)
    if surgery_min != 10 or surgery_max != 500:
        return None

    appendix_two_start = text.find("附表二", table_start_in_text)
    if (
        table_start_in_text < 0
        or appendix_two_start < 0
        or (
            version is not None
            and (
                source_page(text, table_start_in_text) != 7
                or source_page(text, appendix_two_start) != 8
            )
        )
    ):
        return None
    page = source_page(text, table_start_in_text)
    table_ref = "附表一" + (f"，第 {page} 頁" if page else "")
    surgery_ref = "附表二"
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{table_ref}"
    inpatient_base = amounts["inpatient_medical"]

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "hospital-room-limit",
                "每日病房費用保險金限額",
                amounts["room"],
                "daily_per_unit",
                "按實際病房相關費用給付，每日及同一事故給付日數均受條款限制。",
                terms_ref("medical"),
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "intensive-care-limit",
                "加護病房費用保險金限額",
                amounts["icu"],
                "daily_per_unit",
                "按實際加護病房費用給付，每日受限額約束，同一事故最高 90 日。",
                terms_ref("medical"),
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "burn-center-limit",
                "燒燙傷中心病房費用保險金限額",
                amounts["burn_center"],
                "daily_per_unit",
                "按實際燒燙傷中心費用給付，每日受限額約束，同一事故最高 90 日。",
                terms_ref("medical"),
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "inpatient-medical-limit",
                "住院醫療費用保險金限額",
                inpatient_base,
                "per_unit",
                "同一次住院依住院日數提高限額；未以健保身分就醫時，按實際費用的"
                f" {nhi_rate}% 給付，仍受各項限額約束。",
                f"{terms_ref('medical')}及保單條款{article_refs['nhi_adjustment']}",
                calculation_basis="tiered_or_stepped",
                amount_role="limit",
                limit_scope="per_hospitalization",
                aggregation_rule="cumulative_cap",
                amount_tiers=[
                    {"label": "住院 1 至 30 日", "amount": inpatient_base},
                    {"label": "住院 31 至 60 日", "amount": inpatient_base * 2},
                    {"label": "住院 61 至 90 日", "amount": inpatient_base * 3},
                    {"label": "住院 91 至 180 日", "amount": inpatient_base * 4},
                    {"label": "住院 181 至 365 日", "amount": inpatient_base * 5},
                ],
            ),
            coverage_entry(
                "hospital-surgery-base",
                "手術費用保險金限額基數",
                amounts["surgery"],
                "per_unit",
                f"實際限額為每單位基數乘以手術表比例（{surgery_min}% 至 {surgery_max}%）。",
                f"{terms_ref('medical')}及{surgery_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_surgery",
                aggregation_rule="cumulative_cap",
                rate_min_percent=surgery_min,
                rate_max_percent=surgery_max,
            ),
            coverage_entry(
                "home-recovery-limit",
                "出院在家療養保險金限額",
                amounts["home_recovery"],
                "daily_per_unit",
                "按已給付每日病房費用保險金的 60% 計算，表列金額為每單位每日上限。",
                terms_ref("medical"),
                calculation_basis="percentage_of_base",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                rate_min_percent=60,
                rate_max_percent=60,
            ),
            coverage_entry(
                "surgery-recovery-base",
                "手術出院療養保險金限額基數",
                amounts["surgery_recovery"],
                "per_unit",
                "按已給付手術費用保險金的 30% 計算；表列基數仍依手術表比例調整。",
                f"{terms_ref('medical')}及{surgery_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_surgery",
                aggregation_rule="conditional_additive",
                rate_min_percent=surgery_min,
                rate_max_percent=surgery_max,
            ),
            coverage_entry(
                "hospital-daily-option",
                "住院日額補償保險金",
                daily_amount,
                "daily_per_unit",
                "可改選住院日額；第 31 日起的超過天數加倍給付，選擇本項即不得再申領實支各項。",
                terms_ref("daily_option"),
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="choose_one",
                amount_tiers=[
                    {"label": "住院第 1 至 30 日", "amount": daily_amount},
                    {"label": "住院第 31 日起", "amount": daily_amount * 2},
                ],
            ),
        ],
    }


RITAI_DUAL_UNIT_INPATIENT_PRODUCT_IDS = {
    "205311R11A50800",
    "205311R11A50801",
    "205311R11A50802",
    "262311R11A00600",
    "262311R11A00601",
}


def parse_ritai_dual_unit_inpatient_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    if (
        product_id not in RITAI_DUAL_UNIT_INPATIENT_PRODUCT_IDS
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    table_start = text.rfind("住院醫療保險金表")
    table_end = text.find("附表一", table_start)
    if table_start < 0 or table_end < 0:
        return None
    table_text = re.sub(r"\s+", "", text[table_start:table_end])

    hospital_unit_match = re.search(
        r"住院醫療保險金一單位[:：]?新台幣?([\d,]+)元", table_text
    )
    surgery_unit_match = re.search(
        r"手術及雜費保險金一單位[:：]?新台幣?([\d,]+)元", table_text
    )
    if not hospital_unit_match or not surgery_unit_match:
        return None
    hospital_unit = int(hospital_unit_match.group(1).replace(",", ""))
    surgery_unit = int(surgery_unit_match.group(1).replace(",", ""))

    row_patterns = {
        "hospital_daily": r"住院日額保險金([\d,]+)",
        "intensive_care": r"加護病房日額保險金([\d,]+)",
        "burn_center": r"燒燙傷中心日額保險金([\d,]+)",
        "outpatient": r"住院前後七天門診保險金\(每次\)([\d,]+)",
        "surgery_base": r"手術定額保險金.*?([\d,]+)(?=住院之第)",
        "misc_first": r"住院之第1-7日\(每日\)([\d,]+)",
        "misc_later": r"住院之第8日(?:以後)?\(每日\)([\d,]+)",
    }
    amounts = {
        key: first_positive_amount(table_text, pattern)
        for key, pattern in row_patterns.items()
    }
    expected_amounts = {
        "hospital_daily": hospital_unit,
        "intensive_care": hospital_unit,
        "burn_center": hospital_unit,
        "outpatient": hospital_unit * 30 // 100,
        "surgery_base": surgery_unit,
        "misc_first": surgery_unit * 6 // 100,
        "misc_later": surgery_unit * 3 // 100,
    }
    if amounts != expected_amounts:
        return None

    article_refs = {
        "hospital": heading_reference(text, "住院醫療保險金之給付"),
        "surgery": heading_reference(text, "手術及雜費保險金之給付"),
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    required_signals = [
        "住院前後七天門診保險金",
        "不含加護病房及燒燙傷中心之合計住院給付日數",
        "最高以三百六十五日為限",
        "同一次手術中於同一手術位置",
        "每次住院期間最高給付天數以三百六十五天為限",
    ]
    if not all(signal in text for signal in required_signals):
        return None

    surgery_rates = [
        int(value)
        for value in re.findall(r"(?<!\d)(\d{1,3})\s*%", text[table_end:])
    ]
    if not surgery_rates or min(surgery_rates) != 2 or max(surgery_rates) != 400:
        return None

    waiting_condition = (
        "疾病須於初次生效持續有效 30 日後發生；復效日起發生及續保不受等待期限制"
        if "持續有效三十日或復效日以後" in text
        else "疾病須於生效日起持續有效 30 日後發生；續保不受等待期限制"
    )
    hospital_ref = (
        f"保單條款{article_refs['hospital']}及住院醫療保險金表"
    )
    surgery_ref = (
        f"保單條款{article_refs['surgery']}、手術及雜費保險金表及附表一"
    )
    hospital_unit_key = "hospital_medical"
    surgery_unit_key = "surgery_misc"

    return {
        "selection_type": "multi_unit",
        "input_mode": "multi_unit",
        "selection_source": "terms",
        "selection_label": "兩項投保單位數",
        "selection_guidance": (
            "請依保單首頁分別填寫住院醫療保險金與手術及雜費保險金的單位數；"
            "兩者可能不同，系統會各自換算。"
        ),
        "unit_fields": [
            {"key": hospital_unit_key, "label": "住院醫療保險金單位數"},
            {"key": surgery_unit_key, "label": "手術及雜費保險金單位數"},
        ],
        "coverage_entries": [
            coverage_entry(
                "hospital-daily",
                "住院日額保險金",
                amounts["hospital_daily"],
                "daily_per_unit",
                "按住院醫療保險金投保單位數及實際住院日數給付。",
                hospital_ref,
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                unit_key=hospital_unit_key,
                conditions=[waiting_condition, "一般住院給付最高 365 日；正式條款明列不含加護病房及燒燙傷中心日數"],
            ),
            coverage_entry(
                "intensive-care-daily",
                "加護病房日額保險金",
                amounts["intensive_care"],
                "daily_per_unit",
                "入住加護病房時，除住院日額外每日另行給付。",
                hospital_ref,
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                unit_key=hospital_unit_key,
                conditions=[waiting_condition, "轉出加護病房之日計入給付日數"],
            ),
            coverage_entry(
                "burn-center-daily",
                "燒燙傷中心日額保險金",
                amounts["burn_center"],
                "daily_per_unit",
                "入住燒燙傷中心時，除住院日額外每日另行給付。",
                hospital_ref,
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
                unit_key=hospital_unit_key,
                conditions=[waiting_condition, "轉出燒燙傷中心之日計入給付日數"],
            ),
            coverage_entry(
                "pre-post-outpatient",
                "住院前後七天門診保險金",
                amounts["outpatient"],
                "per_unit",
                "住院前七天及出院後七天內，因同一疾病、傷害或併發症門診時按次給付。",
                hospital_ref,
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_event",
                unit_key=hospital_unit_key,
                conditions=[waiting_condition, "每次門診給付，條款未另列次數上限"],
            ),
            coverage_entry(
                "inpatient-surgery-base",
                "手術定額保險金基數",
                amounts["surgery_base"],
                "per_unit",
                "實際給付為每單位基數乘以手術附表比例（2% 至 400%）。",
                surgery_ref,
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_surgery",
                unit_key=surgery_unit_key,
                rate_min_percent=2,
                rate_max_percent=400,
                conditions=[waiting_condition, "同一次手術同一位置涉及多器官時只採最高比例", "未列名手術須協議比照相當項目"],
            ),
            coverage_entry(
                "inpatient-misc-daily",
                "住院雜費保險金",
                amounts["misc_first"],
                "daily_per_unit",
                "按手術及雜費保險金投保單位數及住院日數級距給付。",
                surgery_ref,
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="per_hospitalization",
                unit_key=surgery_unit_key,
                conditions=[waiting_condition, "每次住院最高給付 365 日"],
                amount_tiers=[
                    {"label": "住院第 1 至 7 日", "amount": amounts["misc_first"]},
                    {"label": "住院第 8 日起", "amount": amounts["misc_later"]},
                ],
            ),
        ],
    }


ANNUAL_INPATIENT_ACCOUNT_HEADINGS = {
    "hospital_daily": "住院日額醫療保險金及其申領",
    "intensive_care": "加護病房保險金及其申領",
    "cancer_hospital": "癌症住院醫療保險金及其申領",
    "home_care": "居家療養看護保險金及其申領",
    "surgery": "住院手術保險金及其申領",
    "outpatient": "住院前後門診保險金及其申領",
    "medical_expense": "住院醫療雜費保險金及其申領",
}


def first_positive_amount(table_text: str, pattern: str) -> int | None:
    match = re.search(pattern, table_text)
    if not match:
        return None
    amount = int(match.group(1).replace(",", ""))
    return amount if amount > 0 else None


def parse_annual_inpatient_account_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    table_start = text.rfind("附表二")
    if table_start < 0:
        return None
    table_end = text.find("附表三", table_start)
    if table_end < 0:
        return None
    table_text = text[table_start:table_end]
    if not re.search(r"每\s*1,?000\s*元保險金額之給付金額", table_text):
        return None

    intensive_care_start = table_text.find("加護病房保險金")
    if intensive_care_start < 0:
        return None
    daily_section = table_text[:intensive_care_start]
    if not all(
        signal in daily_section
        for signal in ["住院 30 日", "第 31 日起至 90 日", "第 91 日起"]
    ):
        return None
    daily_amounts = [
        int(value.replace(",", ""))
        for value in re.findall(r"([\d,]+)\s*元\s*/\s*日", daily_section)
    ]
    if len(daily_amounts) != 3 or any(amount <= 0 for amount in daily_amounts):
        return None

    row_patterns = {
        "intensive_care": r"加護病房保險金.*?([\d,]+)\s*元\s*/\s*日",
        "cancer_hospital": r"癌症住院醫療保險金.*?([\d,]+)\s*元\s*/\s*日",
        "home_care": r"居家療養看護保險金.*?([\d,]+)\s*元\s*/\s*日",
        "surgery": r"住院手術保險金.*?([\d,]+)\s*元\s*/\s*次\s*[×xX*]",
        "outpatient": r"住院前後門診保險金.*?([\d,]+)\s*元\s*/\s*日",
        "medical_expense": r"住院醫療雜費保險金.*?([\d,]+)\s*元\s*/\s*日",
    }
    amounts = {
        key: first_positive_amount(table_text, pattern)
        for key, pattern in row_patterns.items()
    }
    if any(amount is None for amount in amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in ANNUAL_INPATIENT_ACCOUNT_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    if "依附表二所列金額" not in text or "手術項目給付比率" not in text:
        return None
    if not re.search(
        r"住院前\s*(?:一|1)\s*週.*?(?:出院)?後\s*(?:二|2)\s*週",
        text,
    ):
        return None

    surgery_table_text = text[table_end : min(len(text), table_end + 16_000)]
    surgery_rates = [
        float(value)
        for value in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*%", surgery_table_text)
    ]
    if not surgery_rates:
        return None
    surgery_min = min(surgery_rates)
    surgery_max = max(surgery_rates)
    if surgery_min <= 0 or surgery_max < surgery_min or surgery_max > 1000:
        return None
    surgery_min_value: int | float = int(surgery_min) if surgery_min.is_integer() else surgery_min
    surgery_max_value: int | float = int(surgery_max) if surgery_max.is_integer() else surgery_max

    page = source_page(text, table_start)
    table_ref = "附表二" + (f"，第 {page} 頁" if page else "")
    surgery_ref = "附表三"
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{table_ref}"
    unit_note = "每 1 單位代表條款所列每 1,000 元保險金額。"

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "hospital-daily-tiered",
                "住院日額醫療保險金",
                daily_amounts[0],
                "per_unit",
                f"{unit_note}按同一次住院的日數級距給付。",
                terms_ref("hospital_daily"),
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="per_day",
                amount_tiers=[
                    {"label": "住院第 1 至 30 日", "amount": daily_amounts[0]},
                    {"label": "住院第 31 至 90 日", "amount": daily_amounts[1]},
                    {"label": "住院第 91 日起", "amount": daily_amounts[2]},
                ],
            ),
            coverage_entry(
                "intensive-care-daily",
                "加護病房保險金",
                amounts["intensive_care"],
                "daily_per_unit",
                f"{unit_note}按實際住進加護病房的日數另行給付。",
                terms_ref("intensive_care"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
            ),
            coverage_entry(
                "cancer-hospital-daily",
                "癌症住院醫療保險金",
                amounts["cancer_hospital"],
                "daily_per_unit",
                f"{unit_note}因條款定義的癌症住院時，按實際住院日數另行給付。",
                terms_ref("cancer_hospital"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
            ),
            coverage_entry(
                "home-care-daily",
                "居家療養看護保險金",
                amounts["home_care"],
                "daily_per_unit",
                f"{unit_note}符合住院日額給付並出院後，按該次住院日數給付。",
                terms_ref("home_care"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="conditional_additive",
            ),
            coverage_entry(
                "inpatient-surgery-base",
                "住院手術保險金基數",
                amounts["surgery"],
                "per_unit",
                f"{unit_note}實際給付為基數乘以附表三手術比例"
                f"（{surgery_min_value}% 至 {surgery_max_value}%）。",
                f"{terms_ref('surgery')}及{surgery_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_surgery",
                rate_min_percent=surgery_min_value,
                rate_max_percent=surgery_max_value,
            ),
            coverage_entry(
                "pre-post-outpatient-daily",
                "住院前後門診保險金",
                amounts["outpatient"],
                "daily_per_unit",
                f"{unit_note}住院前一週及出院後二週內，按實際門診日數給付。",
                terms_ref("outpatient"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
            coverage_entry(
                "inpatient-medical-expense-daily",
                "住院醫療雜費保險金",
                amounts["medical_expense"],
                "daily_per_unit",
                f"{unit_note}符合條款列舉的住院醫療費用時，按實際住院日數給付。",
                terms_ref("medical_expense"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
            ),
        ],
    }


GROUP_INPATIENT_LIMIT_HEADINGS = {
    "room": "每日病房費用保險金之給付",
    "medical": "住院醫療費用保險金之給付",
    "surgery": "手術費用保險金之給付",
    "daily_option": "住院日額補償保險金選擇給付",
    "nhi_adjustment": "醫療費用未經全民健康保險給付者之處理方式",
    "benefit_limit": "保險金給付之限制",
}


def parse_group_inpatient_limit_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    table_start = text.rfind("附表一")
    if table_start < 0:
        return None
    table_end = text.find("附表二", table_start)
    if table_end < 0:
        return None
    table_text = re.sub(r"\s+", "", text[table_start:table_end])
    if "各項給付限額表" not in table_text:
        return None

    row_patterns = {
        "room": r"每日病房費用保險金限額([\d,]+)元[×xX*]投保單位",
        "medical": r"每次住院醫療費用保險金限額([\d,]+)元[×xX*]投保單位",
        "surgery": r"每次手術費用保險金限額([\d,]+)元[×xX*]投保單位",
    }
    amounts = {
        key: first_positive_amount(table_text, pattern)
        for key, pattern in row_patterns.items()
    }
    if any(amount is None for amount in amounts.values()):
        return None

    article_refs = {
        key: heading_reference(text, heading)
        for key, heading in GROUP_INPATIENT_LIMIT_HEADINGS.items()
    }
    if any(reference is None for reference in article_refs.values()):
        return None
    required_signals = [
        "每次住院給付之金額不得超過",
        "同一次手術中於同一手術位置",
        "則不得再申領",
    ]
    if not all(signal in text for signal in required_signals):
        return None
    if not re.search(
        r"每次不得超過附表一.{0,30}每日病房費用保險金限額.{0,30}百分之六十",
        text,
    ):
        return None

    nhi_match = re.search(r"實際支付之各項費用之\s*(\d{1,3})\s*%\s*給付", text)
    if not nhi_match:
        return None
    nhi_rate = int(nhi_match.group(1))
    if not 0 < nhi_rate <= 100:
        return None
    emergency_match = re.search(
        r"意外傷害事故二十四小時內.{0,180}?最高以新台幣\s*([\d, ]+)\s*元為限",
        text,
    )
    if not emergency_match:
        return None
    emergency_amount = int(re.sub(r"[,\s]", "", emergency_match.group(1)))
    if emergency_amount <= 0:
        return None

    surgery_table_end = text.find("附表三", table_end)
    surgery_table_text = text[
        table_end : surgery_table_end if surgery_table_end > table_end else min(len(text), table_end + 16_000)
    ]
    compact_surgery_table = re.sub(r"\s+", "", surgery_table_text)
    surgery_rates = [
        float(value)
        for value in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)%", compact_surgery_table)
    ]
    if not surgery_rates:
        return None
    surgery_min = min(surgery_rates)
    surgery_max = max(surgery_rates)
    if surgery_min <= 0 or surgery_max < surgery_min or surgery_max > 1000:
        return None
    surgery_min_value: int | float = int(surgery_min) if surgery_min.is_integer() else surgery_min
    surgery_max_value: int | float = int(surgery_max) if surgery_max.is_integer() else surgery_max

    room_amount = amounts["room"]
    outpatient_amount = room_amount * 60
    if outpatient_amount % 100:
        return None
    outpatient_amount //= 100
    page = source_page(text, table_start)
    table_ref = "附表一" + (f"，第 {page} 頁" if page else "")
    surgery_ref = "附表二"
    terms_ref = lambda key: f"保單條款{article_refs[key]}及{table_ref}"
    unit_note = "表列金額乘以投保單位數。"
    reimbursement_note = (
        f"{unit_note}按實際自行負擔及非健保給付範圍的費用核付；"
        f"未以健保身分就醫時按實際費用的 {nhi_rate}% 給付，仍受限額約束。"
    )

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "hospital-room-limit",
                "每日病房費用保險金限額",
                room_amount,
                "daily_per_unit",
                reimbursement_note,
                f"{terms_ref('room')}及保單條款{article_refs['nhi_adjustment']}",
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "inpatient-medical-limit",
                "每次住院醫療費用保險金限額",
                amounts["medical"],
                "per_unit",
                reimbursement_note,
                f"{terms_ref('medical')}及保單條款{article_refs['nhi_adjustment']}",
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_hospitalization",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "pre-post-outpatient-limit",
                "住院前後門診醫療費用限額",
                outpatient_amount,
                "daily_per_unit",
                f"{unit_note}住院前後七日因同一事故門診時，每日以一次為限；"
                "每次上限為每日病房費用保險金限額的 60%。",
                terms_ref("medical"),
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_day",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "accident-emergency-limit",
                "意外急診醫療費用限額",
                emergency_amount,
                "per_event",
                "因意外傷害事故於二十四小時內接受急診時，按實際費用給付；"
                "本項併入住院醫療費用保險金限額計算。",
                terms_ref("medical"),
                calculation_basis="reimbursement_with_cap",
                amount_role="limit",
                limit_scope="per_event",
                aggregation_rule="cumulative_cap",
            ),
            coverage_entry(
                "hospital-surgery-limit-base",
                "每次手術費用保險金限額基數",
                amounts["surgery"],
                "per_unit",
                f"{unit_note}實際限額為基數乘以附表二手術比例"
                f"（{surgery_min_value}% 至 {surgery_max_value}%），並依實際手術費核付。",
                f"{terms_ref('surgery')}及{surgery_ref}",
                calculation_basis="percentage_of_base",
                amount_role="base",
                limit_scope="per_surgery",
                aggregation_rule="cumulative_cap",
                rate_min_percent=surgery_min_value,
                rate_max_percent=surgery_max_value,
            ),
            coverage_entry(
                "hospital-daily-option",
                "住院日額補償保險金",
                room_amount,
                "daily_per_unit",
                f"{unit_note}可改選按實際住院日數給付；選擇本項後不得再申領三項實支保險金。",
                terms_ref("daily_option"),
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                aggregation_rule="choose_one",
            ),
        ],
    }


GROUP_PLAN_LIMIT_HEADINGS = {
    "inpatient": "住院醫療費用保險金之給付",
    "outpatient_surgery": "門診手術費用補償保險金之給付",
    "shared_limit": "住院醫療費用保險金及門診手術費用補償保險金給付之限制",
    "daily_option": "住院日額補償保險金之給付",
    "nhi_adjustment": "醫療費用未經全民健康保險給付者之處理方式",
}
GROUP_PLAN_LIMIT_HEADER_PATTERN = re.compile(
    r"附表\s*二\s*[:：]\s*各計[劃畫]別所對應之給付限制"
)


def parse_group_plan_amounts(
    table_text: str,
    label_pattern: str,
    unit_pattern: str,
) -> list[int] | None:
    label = re.search(label_pattern, table_text)
    if not label:
        return None
    following = table_text[label.end() :]
    next_row = re.search(r"日額給付型|最高給付\s*住院日數", following)
    row_text = following[: next_row.start()] if next_row else following
    amounts = [
        amount_in_ntd(match.group(1), match.group(2))
        for match in re.finditer(rf"([\d,]+)\s*({unit_pattern})", row_text)
    ]
    return amounts if len(amounts) == 11 and all(amount > 0 for amount in amounts) else None


def parse_group_plan_inpatient_limit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    header = GROUP_PLAN_LIMIT_HEADER_PATTERN.search(text)
    if not header:
        return None

    table_text = text[header.start() :]
    plan_codes = re.findall(r"計[劃畫]\s*([A-K])", table_text)
    if plan_codes[:11] != list("ABCDEFGHIJK") or len(plan_codes) != 11:
        return None

    reimbursement_limits = parse_group_plan_amounts(
        table_text,
        r"實支實付型\s*保險金\s*限額",
        r"萬元|元",
    )
    daily_amounts = parse_group_plan_amounts(
        table_text,
        r"日額給付型\s*住院\s*日額",
        r"元",
    )
    days_match = re.search(
        r"最高給付\s*住院日數(?P<days>(?:\s*[\d,]+\s*日){11})",
        table_text,
    )
    if not reimbursement_limits or not daily_amounts or not days_match:
        return None
    maximum_days = [
        int(value.replace(",", ""))
        for value in re.findall(r"([\d,]+)\s*日", days_match.group("days"))
    ]
    if len(maximum_days) != 11 or any(day <= 0 for day in maximum_days):
        return None

    article_refs = heading_article_references(text)
    if any(heading not in article_refs for heading in GROUP_PLAN_LIMIT_HEADINGS.values()):
        return None
    nhi_rate_match = re.search(
        r"實際支付之各項費用之\s*(\d{1,3})\s*%\s*給付",
        text,
    )
    if not nhi_rate_match:
        return None
    nhi_rate = int(nhi_rate_match.group(1))
    if not 0 < nhi_rate <= 100:
        return None

    page = source_page(text, header.start())
    table_ref = "附表二" + (f"，第 {page} 頁" if page else "")
    plans = []
    for index, plan_code in enumerate("ABCDEFGHIJK"):
        shared_limit = reimbursement_limits[index]
        daily_amount = daily_amounts[index]
        maximum_day = maximum_days[index]
        plans.append(
            {
                "value": plan_code,
                "label": f"計劃 {plan_code}",
                "coverage_entries": [
                    coverage_entry(
                        "inpatient-medical-shared-limit",
                        "住院醫療費用保險金限額",
                        shared_limit,
                        "per_event",
                        "同一事故採實支實付，並與門診手術費用補償保險金共用本限額；"
                        f"未經全民健康保險給付時，按實際支付費用的 {nhi_rate}% 給付。",
                        f"保單條款{article_refs[GROUP_PLAN_LIMIT_HEADINGS['inpatient']]}、"
                        f"{article_refs[GROUP_PLAN_LIMIT_HEADINGS['shared_limit']]}、"
                        f"{article_refs[GROUP_PLAN_LIMIT_HEADINGS['nhi_adjustment']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_event",
                        aggregation_rule="cumulative_cap",
                    ),
                    coverage_entry(
                        "outpatient-surgery-shared-limit",
                        "門診手術費用補償保險金限額",
                        shared_limit,
                        "per_event",
                        "門診手術採實支實付，並與住院醫療費用保險金共用同一事故限額；"
                        f"未經全民健康保險給付時，按實際支付費用的 {nhi_rate}% 給付。",
                        f"保單條款{article_refs[GROUP_PLAN_LIMIT_HEADINGS['outpatient_surgery']]}、"
                        f"{article_refs[GROUP_PLAN_LIMIT_HEADINGS['shared_limit']]}、"
                        f"{article_refs[GROUP_PLAN_LIMIT_HEADINGS['nhi_adjustment']]}及{table_ref}",
                        calculation_basis="reimbursement_with_cap",
                        amount_role="limit",
                        limit_scope="per_event",
                        aggregation_rule="cumulative_cap",
                    ),
                    coverage_entry(
                        "hospital-daily-option",
                        "住院日額補償保險金",
                        daily_amount,
                        "daily_total",
                        f"按實際住院日數給付，同一次住院最高 {maximum_day} 日；"
                        "選擇本項後，不得再申領同一次住院的住院醫療費用保險金。",
                        f"保單條款{article_refs[GROUP_PLAN_LIMIT_HEADINGS['daily_option']]}及{table_ref}",
                        calculation_basis="per_day",
                        amount_role="payout",
                        limit_scope="per_day",
                        aggregation_rule="choose_one",
                        conditions=[f"同一次住院最高給付 {maximum_day} 日"],
                    ),
                ],
            }
        )

    return {
        "selection_type": "plan",
        "input_mode": "plan",
        "selection_source": "terms",
        "plan_options": plans,
    }


GROUP_CANCER_FIXED_HEADINGS = {
    "coverage": "保險範圍",
    "hospital": "癌症每次住院醫療保險金及其申請",
    "surgery": "癌症每次住院手術費用保險金及其申請",
    "recovery": "癌症療養保險金及其申請",
}
GROUP_CANCER_FIXED_TABLE_MARKER = "每投保單位給付之保險金"


def parse_group_cancer_fixed_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    text = normalize_terms_text(str(document.get("text") or ""))
    marker_start = text.find(GROUP_CANCER_FIXED_TABLE_MARKER)
    if marker_start < 0:
        return None
    attachment_matches = list(
        re.finditer(r"附件\s*([一二])", text[:marker_start])
    )
    if not attachment_matches:
        return None
    header = attachment_matches[-1]
    if marker_start - header.start() > 1_000:
        return None
    next_attachment = re.search(
        r"附件\s*[一二三四]",
        text[marker_start + len(GROUP_CANCER_FIXED_TABLE_MARKER) :],
    )
    table_end = (
        marker_start
        + len(GROUP_CANCER_FIXED_TABLE_MARKER)
        + next_attachment.start()
        if next_attachment
        else len(text)
    )
    table_text = text[header.start() : table_end]

    hospital_match = re.search(
        r"癌症每次住院醫療保險金\s*每日\s*([\d,]+)\s*元",
        table_text,
    )
    surgery_heading_present = "癌症每次住院手術費用保險金" in table_text
    non_in_situ_match = re.search(
        r"非原位癌之癌症\s*每次\s*([\d,]+)\s*元",
        table_text,
    )
    in_situ_match = re.search(
        r"(?<!非)原位癌\s*每次\s*([\d,]+)\s*元",
        table_text,
    )
    recovery_match = re.search(
        r"癌症療養保險金\s*\(\s*最高以給付\s*(\d+)\s*日為限\s*\)\s*"
        r"每日\s*([\d,]+)\s*元",
        table_text,
    )
    if (
        not hospital_match
        or not surgery_heading_present
        or not non_in_situ_match
        or not in_situ_match
        or not recovery_match
    ):
        return None

    hospital_amount = int(hospital_match.group(1).replace(",", ""))
    non_in_situ_amount = int(non_in_situ_match.group(1).replace(",", ""))
    in_situ_amount = int(in_situ_match.group(1).replace(",", ""))
    recovery_days = int(recovery_match.group(1))
    recovery_amount = int(recovery_match.group(2).replace(",", ""))
    if (
        min(
            hospital_amount,
            non_in_situ_amount,
            in_situ_amount,
            recovery_days,
            recovery_amount,
        )
        <= 0
        or non_in_situ_amount <= in_situ_amount
    ):
        return None

    article_refs = heading_article_references(text)
    if any(heading not in article_refs for heading in GROUP_CANCER_FIXED_HEADINGS.values()):
        return None
    coverage_start = text.find("【保險範圍】")
    next_heading = (
        re.search(r"【[^】]+】", text[coverage_start + len("【保險範圍】") :])
        if coverage_start >= 0
        else None
    )
    coverage_end = (
        coverage_start + len("【保險範圍】") + next_heading.start()
        if next_heading
        else -1
    )
    coverage_text = (
        text[coverage_start:coverage_end]
        if coverage_start >= 0 and coverage_end > coverage_start
        else ""
    )
    waiting_period_verified = all(
        signal in coverage_text for signal in ("第六十一日", "六十日", "以內")
    )
    recovery_term_match = re.search(
        r"癌症療養保險金及其申請.*?最高以給付\s*(\d+)\s*日為限",
        text,
    )
    if (
        not waiting_period_verified
        or not recovery_term_match
        or int(recovery_term_match.group(1)) != recovery_days
    ):
        return None

    page = source_page(text, header.start())
    table_ref = f"附件{header.group(1)}" + (f"，第 {page} 頁" if page else "")
    waiting_note = "參加契約滿 60 日後，自第 61 日起開始癌症保障。"
    waiting_condition = "癌症保障自參加契約第 61 日起開始"
    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "coverage_entries": [
            coverage_entry(
                "cancer-hospital-daily",
                "癌症每次住院醫療保險金",
                hospital_amount,
                "daily_per_unit",
                f"{waiting_note}按投保單位數及實際住院日數給付，含入院及出院日。",
                f"保單條款{article_refs[GROUP_CANCER_FIXED_HEADINGS['coverage']]}、"
                f"{article_refs[GROUP_CANCER_FIXED_HEADINGS['hospital']]}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-inpatient-surgery",
                "癌症每次住院手術費用保險金",
                non_in_situ_amount,
                "per_unit",
                f"{waiting_note}每次住院期間以給付一次為限；金額依非原位癌或原位癌區分。",
                f"保單條款{article_refs[GROUP_CANCER_FIXED_HEADINGS['coverage']]}、"
                f"{article_refs[GROUP_CANCER_FIXED_HEADINGS['surgery']]}及{table_ref}",
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="per_hospitalization",
                conditions=[waiting_condition, "每次住院期間以給付一次為限"],
                amount_tiers=[
                    {"label": "非原位癌之癌症", "amount": non_in_situ_amount},
                    {"label": "原位癌", "amount": in_situ_amount},
                ],
            ),
            coverage_entry(
                "cancer-recovery-daily",
                "癌症療養保險金",
                recovery_amount,
                "daily_per_unit",
                f"{waiting_note}按投保單位數及住院日數給付，每次住院最高 {recovery_days} 日。",
                f"保單條款{article_refs[GROUP_CANCER_FIXED_HEADINGS['coverage']]}、"
                f"{article_refs[GROUP_CANCER_FIXED_HEADINGS['recovery']]}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, f"每次住院最高給付 {recovery_days} 日"],
            ),
        ],
    }


def parse_global_winterthur_cancer_annuity_face_amount(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    version = GLOBAL_WINTERTHUR_CANCER_ANNUITY_PRODUCT_VERSIONS.get(product_id)
    file_name = str(document.get("file_name") or "")
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or not file_name.endswith("-A.pdf")
    ):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    dense_text = compact_table_text(text)
    is_investment_linked = version["product_variant"] == "investment-linked"
    expected_title = "環球瑞泰人壽防癌健康保險附約"
    investment_marker = "本附約僅附加於投資型保險主契約且本附約保險費自主契約保單帳戶價值中扣除之"
    if expected_title not in text or "瑞士商環球瑞泰人壽保險股份有限公司台灣分公司" not in dense_text:
        return None
    if is_investment_linked != ("環球瑞泰人壽防癌健康保險附約(投資型商品版)" in text):
        return None
    if is_investment_linked != (investment_marker in dense_text):
        return None
    if any(signal not in text for signal in version["required_revision_signals"]):
        return None
    if any(signal in text for signal in version["forbidden_revision_signals"]):
        return None

    common_clause_signals = (
        "本公司對本附約應負之保險責任自被保險人於本附約的生效日或復效日起持續有效之第九十一日開始",
        "但本附約續保者則自本附約續保之日開始",
        "本附約即行終止本公司無息退還本附約保險費",
        "初次罹患原位癌保險金",
        "初次罹患癌症保險金",
        "癌症療養年金",
        "被保險人身故二者先屆至者",
        "被保險人罹患原位癌時本公司不負前述「癌症療養年金」之給付責任",
        "自該被保險人身故之日回溯至第三十日",
    )
    if any(signal not in dense_text for signal in common_clause_signals):
        return None

    article_specs = (
        ("初次罹患原位癌保險金", version["benefit_articles"][0]),
        ("初次罹患癌症保險金", version["benefit_articles"][1]),
        ("癌症療養年金", version["benefit_articles"][2]),
        ("身故後診斷為癌症", version["benefit_articles"][3]),
    )
    article_starts = []
    article_refs = {}
    for heading, expected_article in article_specs:
        match = re.search(
            rf"【{re.escape(heading)}\s*】\s*第\s*([一二三四五六七八九十廿]+)\s*條",
            text,
        )
        if not match or match.group(1) != expected_article:
            return None
        article_starts.append(match.start())
        article_refs[heading] = f"第{expected_article}條"
    if article_starts != sorted(article_starts) or len(set(article_starts)) != 4:
        return None

    expected_maximum_age = "六十五歲" if version["maximum_renewal_age"] == 65 else "七十五歲"
    if f"續保之保險年齡最高為{expected_maximum_age}" not in dense_text:
        return None
    premium_advance_present = "【保險費的墊繳】" in text
    if premium_advance_present != (
        version["product_variant"] == "traditional" and version["revision"] == "first-revision"
    ):
        return None
    revised_investment_definition = "「初次罹患癌症或原位癌」" in text
    if revised_investment_definition != (
        version["product_variant"] == "investment-linked"
        and version["revision"] == "first-revision"
    ):
        return None

    termination_signal = "被保險人初次罹患癌症後本附約效力自次一保單週月日起即行終止要保人免繳本附約保險費"
    if (termination_signal in dense_text) != version["terminates_after_cancer"]:
        return None
    evidence_signal = "受益人如能舉證說明則依其實際罹患癌症之日期處理"
    if (evidence_signal in dense_text) != version["actual_diagnosis_date_evidence_allowed"]:
        return None

    table_marker = "【附表一】保險金給付表"
    if text.count(table_marker) != 1:
        return None
    table_start = text.find(table_marker)
    table_end = text.find("【附表二】癌症項目", table_start)
    if table_end <= table_start:
        return None
    compact_table = compact_table_text(text[table_start:table_end])
    table_match = re.fullmatch(
        r"【附表一】保險金給付表給付項目投保每萬元保險金額"
        r"1\.初次罹患癌症保險金給付以一次為限新台幣(\d+)元"
        r"2\.初次罹患原位癌保險金給付以一次為限新台幣(\d+)元"
        r"療養年金週年日給付金額"
        r"1新台幣(\d+)元2新台幣(\d+)元3新台幣(\d+)元4新台幣(\d+)元"
        r"3\.癌症療養年金5~9新台幣(\d+)元5?",
        compact_table,
    )
    if not table_match:
        return None
    table_amounts = tuple(int(value) for value in table_match.groups())
    expected_amounts = (10_000, 1_000, 9_000, 8_000, 7_000, 6_000, 2_000)
    if table_amounts != expected_amounts:
        return None
    if any(amount % 100 for amount in table_amounts):
        return None

    cancer_amount, in_situ_amount, *annuity_amounts = table_amounts
    cancer_rate = cancer_amount // 100
    in_situ_rate = in_situ_amount // 100
    annuity_rates = [amount // 100 for amount in annuity_amounts]
    waiting_condition = "生效日或復效日起 90 日內不負癌症保障責任；自第 91 日開始保障"
    renewal_condition = "續保自續保日起開始保障，不另計 90 日等待期"
    annuity_conditions = [
        waiting_condition,
        renewal_condition,
        "須先領取初次罹患癌症保險金",
        "被保險人於該療養年金週年日仍生存",
        "原位癌不給付癌症療養年金",
        "最長給付至第 9 個療養年金週年日或身故，二者先到者",
    ]
    if version["terminates_after_cancer"]:
        annuity_conditions.append("初次罹患癌症後附約自次一保單週月日起終止，療養年金仍依本條約定給付")

    in_situ_article = article_refs["初次罹患原位癌保險金"]
    cancer_article = article_refs["初次罹患癌症保險金"]
    annuity_article = article_refs["癌症療養年金"]
    appendix_ref = "附表一（保險金給付表），第 4 頁"
    annuity_specs = (
        ("year-1", "第 1 個療養年金週年日", annuity_rates[0], "每次罹患癌症限一次"),
        ("year-2", "第 2 個療養年金週年日", annuity_rates[1], "每次罹患癌症限一次"),
        ("year-3", "第 3 個療養年金週年日", annuity_rates[2], "每次罹患癌症限一次"),
        ("year-4", "第 4 個療養年金週年日", annuity_rates[3], "每次罹患癌症限一次"),
        ("years-5-9", "第 5 至第 9 個療養年金週年日", annuity_rates[4], "每個週年日各一次，最多五次"),
    )
    annuity_entries = [
        coverage_entry(
            f"cancer-recovery-annuity-{entry_id}",
            f"癌症療養年金（{label}）",
            None,
            "benefit_base",
            f"每次按保險金額的 {rate}% 給付；{frequency_note}。",
            f"保單條款{annuity_article}及{appendix_ref}",
            calculation_basis="percentage_of_base",
            amount_role="payout",
            limit_scope="annual",
            rate_percent=rate,
            conditions=annuity_conditions,
        )
        for entry_id, label, rate, frequency_note in annuity_specs
    ]

    return {
        "selection_type": "face_amount",
        "input_mode": "face_amount",
        "selection_source": "terms",
        "selection_label": "保險金額",
        "selection_guidance": "請輸入保單首頁所載保險金額；系統會依附表一換算原位癌、癌症與各年度療養年金。",
        "version_characteristics": {
            "product_variant": version["product_variant"],
            "revision": version["revision"],
            "cancer_initial_waiting_days": 90,
            "cancer_reinstatement_waiting_days": 90,
            "cancer_renewal_waiting_days": 0,
            "maximum_renewal_age": version["maximum_renewal_age"],
            "terminates_next_policy_month_after_initial_cancer": version[
                "terminates_after_cancer"
            ],
            "post_death_actual_diagnosis_date_evidence_allowed": version[
                "actual_diagnosis_date_evidence_allowed"
            ],
            "annuity_anniversary_basis": (
                "initial-cancer-benefit-payment-date"
                if is_investment_linked
                else "policy-anniversary-after-diagnosis"
            ),
        },
        "coverage_entries": [
            coverage_entry(
                "initial-carcinoma-in-situ",
                "初次罹患原位癌保險金",
                None,
                "benefit_base",
                f"按保險金額的 {in_situ_rate}% 給付一次；給付後仍須繳費以維持附約。",
                f"保單條款{in_situ_article}及{appendix_ref}",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="lifetime",
                rate_percent=in_situ_rate,
                conditions=[
                    waiting_condition,
                    renewal_condition,
                    "給付以一次為限",
                    "原位癌不給付癌症療養年金",
                ],
            ),
            coverage_entry(
                "initial-cancer",
                "初次罹患癌症保險金",
                None,
                "benefit_base",
                f"按保險金額的 {cancer_rate}% 給付一次，不含原位癌。",
                f"保單條款{cancer_article}及{appendix_ref}",
                calculation_basis="percentage_of_base",
                amount_role="payout",
                limit_scope="lifetime",
                rate_percent=cancer_rate,
                conditions=[waiting_condition, renewal_condition, "給付以一次為限", "不含原位癌"],
            ),
            *annuity_entries,
        ],
    }


ANTAI_CANCER_LIFETIME_RIDER_ARTICLES = (
    ("罹患癌症保險金的給付", "八"),
    ("癌症住院醫療保險金的給付", "九"),
    ("癌症出院療養保險金的給付", "十"),
    ("癌症外科手術醫療保險金的給付", "十一"),
    ("癌症門診醫療保險金的給付", "十二"),
    ("癌症放射線治療保險金的給付", "十三"),
    ("癌症化學治療保險金的給付", "十四"),
    ("癌症安寧照護保險金的給付", "十五"),
    ("住院次數及日數之計算", "十六"),
    ("身故後發現罹患癌症的給付方式", "十七"),
)


def repair_antai_cancer_lifetime_rider_text(text: str) -> str:
    proof_signals = (
        "安泰人壽防癌終身健康保險附約",
        "【罹患癌症保險金的給付】",
        "附表一",
    )
    if all(signal in text for signal in proof_signals):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    return repaired if all(signal in repaired for signal in proof_signals) else text


def parse_antai_cancer_lifetime_rider_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    version = ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_VERSIONS.get(product_id)
    if (
        version is None
        or document.get("document_type") != "policy_terms"
        or str(document.get("file_name") or "") != version["file_name"]
    ):
        return None

    raw_text = str(document.get("text") or "")
    text = normalize_terms_text(repair_antai_cancer_lifetime_rider_text(raw_text))
    dense_text = compact_table_text(text)
    if text.count("安泰人壽防癌終身健康保險附約") != 1:
        return None

    required_revisions = tuple(
        compact_table_text(signal) for signal in version["required_revision_signals"]
    )
    forbidden_revisions = tuple(
        compact_table_text(signal) for signal in version["forbidden_revision_signals"]
    )
    if any(signal not in dense_text for signal in required_revisions):
        return None
    if any(signal in dense_text for signal in forbidden_revisions):
        return None

    old_contract_signals = (
        "則以被保險人之法定繼承人為該部分保險金之受益人",
        "主契約有撤銷、解除、終止、消滅或變更為展期定期或減額繳清保險之情形時",
    )
    revised_contract_signals = (
        "則以主契約之身故保險金受益人為該部分保險金之受益人",
        "主契約變更為減額繳清保險時除同時辦理終止本附約之作業外本附約之效力仍繼續有效",
        "主契約變更為展期定期保險或因要保人終止時除同時辦理終止本附約之作業外本附約之效力持續至本附約當期已繳保險費期滿後終止",
    )
    required_contract_signals = (
        revised_contract_signals
        if version["revised_contract_rules"]
        else old_contract_signals
    )
    forbidden_contract_signals = (
        old_contract_signals
        if version["revised_contract_rules"]
        else revised_contract_signals
    )
    if any(
        compact_table_text(signal) not in dense_text
        for signal in required_contract_signals
    ):
        return None
    if any(
        compact_table_text(signal) in dense_text
        for signal in forbidden_contract_signals
    ):
        return None

    range_match = re.search(r"【保險範圍】\s*第\s*([一二三四五六七八九十]+)\s*條", text)
    if not range_match or range_match.group(1) != "七":
        return None
    termination_match = re.search(
        r"【附約的終止】\s*第\s*([一二三四五六七八九十]+)\s*條",
        text,
    )
    if not termination_match or termination_match.group(1) != "十九":
        return None

    article_starts = []
    article_refs = {}
    for heading, expected_article in ANTAI_CANCER_LIFETIME_RIDER_ARTICLES:
        if text.count(f"【{heading}】") != 1:
            return None
        match = re.search(
            rf"【{re.escape(heading)}】\s*第\s*([一二三四五六七八九十]+)\s*條",
            text,
        )
        if not match or match.group(1) != expected_article:
            return None
        article_starts.append(match.start())
        article_refs[heading] = f"第{expected_article}條"
    if article_starts != sorted(article_starts) or len(set(article_starts)) != len(
        ANTAI_CANCER_LIFETIME_RIDER_ARTICLES
    ):
        return None

    required_formula_signals = (
        "罹患癌症保險金之保單年度數之「每承保單位數給付金額」乘以該被保險人當時實際承保有效之單位數計算所得之金額",
        "「每承保單位數給付金額」的百分之十五乘以該被保險人當時實際承保有效之單位數所得之金額",
        "扣除已申領「罹患癌症保險金」數額後之剩餘金額範圍內",
        "癌症住院醫療日額以該日額乘以該被保險人該次之實際住院日數計算所得之金額",
        "癌症出院療養日額以該日額乘以該被保險人之該次實際住院日數計算所得之金額",
        "癌症外科手術醫療保險金之每次之「每承保單位數給付金額」乘以該被保險人當時實際承保有效之單位數計算所得之金額",
        "癌症外科手術醫療保險金之每次之「每承保單位數給付金額」的百分之十五乘以該被保險人當時實際承保有效之單位數計算所得之金額",
        "癌症門診醫療日額以該日額乘以該被保險人該次實際接受門診治療之日數",
        "癌症放射線治療日額以該日額乘以該被保險人該次實際接受放射線治療之日數",
        "癌症化學治療日額以該日額乘以該被保險人該次實際接受化學治療之日數",
        "癌症安寧照護保險金之每年之「每承保單位數給付金額」乘以該被保險人當時實際承保有效之單位數計算所得之金額",
    )
    required_rule_signals = (
        "自本附約生效日或自復效日、加保生效日起且持續有效九十日以後",
        "於出院後十四日內再次住院時其各種保險金之給付視為同一次住院辦理",
        "同一手術位置需接受二次含以上的外科切除手術時自接受前次外科切除手術治療當日起十四日內含之所有外科切除手術皆視為同一次外科切除手術",
        "不論其每日門診次數為一次或多次均以一日計",
        "不論其每日治療次數為一次或多次均以一日計",
        "不論其每日接受化學治療次數為一次或多次均以一日計",
        "以血管注射進行的化學治療法",
        "第二、三、四、五個罹患確定日之周年日午夜十二時終了時仍生存者亦同",
        "自罹患確定日起算之第六年含以後之各周年日",
        "第一期前列腺癌、原位癌或惡性黑色素瘤以外之皮膚癌時本公司不負前述「癌症安寧照護保險金」之給付責任",
        "但若被保險人身故前未因癌症而住院治療者本公司僅依第八條約定給付「罹患癌症保險金」",
        "被保險人最後一次住院之始日係在本附約對於該被保險人應負保險金給付之觀察期間屆滿以前者本附約對該被保險人即自始失其效力",
        "本附約對於各被保險人之效力於各該被保險人保險年齡達九十五歲後之第一個保單週年日午夜十二時即行終止",
    )
    required_signals = (*required_formula_signals, *required_rule_signals)
    if any(compact_table_text(signal) not in dense_text for signal in required_signals):
        return None

    if text.count("附表一:") != 1:
        return None
    table_start = text.rfind("附表一:")
    compact_table = compact_table_text(text[table_start:])
    table_match = re.fullmatch(
        r"附表一(?P<title>各項保險金)?「每承保單位數給付金額」單位新台幣"
        r"保險金項目每承保單位數給付金額"
        r"罹患癌症保險金第一保單年度至第二十保單年度末日午夜十二時經診斷確定罹患癌症(?P<cancer_1_20>\d+)元"
        r"第二十一保單年度含起經診斷確定罹患癌症(?P<cancer_21_plus>\d+)元"
        r"癌症住院醫療保險金同一次第1-90日(?P<hospital_1_90>\d+)元/日"
        r"住院第91日起(?P<hospital_91_plus>\d+)元/日"
        r"癌症出院療養保險金(?P<discharge>\d+)元/日"
        r"癌症外科手術醫療保險金(?P<surgery>\d+)元/次"
        r"癌症門診醫療保險金(?P<outpatient>\d+)元/日"
        r"癌症放射線治療保險金(?P<radiation>\d+)元/日"
        r"癌症化學治療保險金(?P<chemotherapy>\d+)元/日"
        r"癌症安寧照護保險金罹患癌症確定日後起算的第1、2、3、4、5個周年日當日午夜十二時終了仍生存(?P<palliative>\d+)元/年"
        r"(?P<trailer>11)?",
        compact_table,
    )
    if not table_match:
        return None
    if (table_match.group("title") or "") != version["table_title_prefix"]:
        return None
    if (table_match.group("trailer") or "") != version["table_trailer"]:
        return None

    amount_keys = (
        "cancer_1_20",
        "cancer_21_plus",
        "hospital_1_90",
        "hospital_91_plus",
        "discharge",
        "surgery",
        "outpatient",
        "radiation",
        "chemotherapy",
        "palliative",
    )
    amounts = tuple(int(table_match.group(key)) for key in amount_keys)
    if amounts != (50_000, 75_000, 1_200, 1_800, 600, 15_000, 500, 500, 800, 20_000):
        return None
    (
        cancer_1_20,
        cancer_21_plus,
        hospital_1_90,
        hospital_91_plus,
        discharge,
        surgery,
        outpatient,
        radiation,
        chemotherapy,
        palliative,
    ) = amounts

    early_cancer_rate = 15
    waiting_condition = "生效日、復效日或增加承保單位數生效日起持續有效 90 日後，才開始癌症保障"
    readmission_condition = "同一癌症或其併發症出院後 14 日內再次住院，視為同一次住院"
    coverage_end_condition = "保險年齡達 95 歲後第一個保單週年日午夜 12 時，附約效力終止"
    unit_note = "每承保單位金額須乘以保單當時實際有效的承保單位數。"
    table_ref = f"附表一（每承保單位數給付金額），第 {version['table_page']} 頁"

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "selection_label": "承保單位數",
        "selection_guidance": "請輸入保單首頁所載的有效承保單位數；各項金額以 A 類保單條款附表一為準。",
        "coverage_entries": [
            coverage_entry(
                "cancer-diagnosis",
                "罹患癌症保險金",
                cancer_1_20,
                "per_unit",
                f"{unit_note}第 1 至 20 保單年度每單位 {cancer_1_20:,} 元，第 21 保單年度起每單位 {cancer_21_plus:,} 元；第一期前列腺癌或原位癌按適用金額的 {early_cancer_rate}% 給付。",
                f"保單條款{article_refs['罹患癌症保險金的給付']}及{table_ref}",
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=[
                    waiting_condition,
                    "再次罹患癌症時，僅在適用金額扣除已申領罹患癌症保險金後的餘額內給付",
                    coverage_end_condition,
                ],
                amount_tiers=[
                    {"label": "第 1 至 20 保單年度／一般癌症", "amount": cancer_1_20},
                    {
                        "label": "第 1 至 20 保單年度／第一期前列腺癌或原位癌",
                        "amount": cancer_1_20 * early_cancer_rate // 100,
                    },
                    {"label": "第 21 保單年度起／一般癌症", "amount": cancer_21_plus},
                    {
                        "label": "第 21 保單年度起／第一期前列腺癌或原位癌",
                        "amount": cancer_21_plus * early_cancer_rate // 100,
                    },
                ],
            ),
            coverage_entry(
                "cancer-hospital-days-1-90",
                "癌症住院醫療保險金（同一次住院第 1 至 90 日）",
                hospital_1_90,
                "daily_per_unit",
                f"{unit_note}按每單位日額乘以實際住院日數給付。",
                f"保單條款{article_refs['癌症住院醫療保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "同一次住院第 1 至 90 日",
                    readmission_condition,
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-hospital-days-91-plus",
                "癌症住院醫療保險金（同一次住院第 91 日起）",
                hospital_91_plus,
                "daily_per_unit",
                f"{unit_note}按每單位日額乘以實際住院日數給付。",
                f"保單條款{article_refs['癌症住院醫療保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "同一次住院第 91 日起",
                    readmission_condition,
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院療養保險金",
                discharge,
                "daily_per_unit",
                f"{unit_note}出院後按每單位日額乘以該次實際住院日數給付。",
                f"保單條款{article_refs['癌症出院療養保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "須符合癌症住院醫療保險金的住院條件",
                    readmission_condition,
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-surgery",
                "癌症外科手術醫療保險金",
                surgery,
                "per_unit",
                f"{unit_note}一般癌症每次每單位 {surgery:,} 元；第一期前列腺癌或原位癌按 {early_cancer_rate}% 給付。",
                f"保單條款{article_refs['癌症外科手術醫療保險金的給付']}及{table_ref}",
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="per_surgery",
                aggregation_rule="choose_one",
                conditions=[
                    waiting_condition,
                    "同一手術位置自前次手術日起 14 日內的外科切除手術視為同一次，只給付一次",
                    coverage_end_condition,
                ],
                amount_tiers=[
                    {"label": "一般癌症", "amount": surgery},
                    {
                        "label": "第一期前列腺癌或原位癌",
                        "amount": surgery * early_cancer_rate // 100,
                    },
                ],
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                outpatient,
                "daily_per_unit",
                f"{unit_note}按實際接受門診治療日數給付。",
                f"保單條款{article_refs['癌症門診醫療保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "同一日門診一次或多次均以一日計",
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線治療保險金",
                radiation,
                "daily_per_unit",
                f"{unit_note}住院或門診接受放射線治療，按實際治療日數給付。",
                f"保單條款{article_refs['癌症放射線治療保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "同一日治療一次或多次均以一日計",
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學治療保險金",
                chemotherapy,
                "daily_per_unit",
                f"{unit_note}住院或門診接受以血管注射進行的化學治療，按實際治療日數給付。",
                f"保單條款{article_refs['癌症化學治療保險金的給付']}及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[
                    waiting_condition,
                    "化學治療限以血管注射進行",
                    "同一日接受化學治療一次或多次均以一日計",
                    coverage_end_condition,
                ],
            ),
            coverage_entry(
                "cancer-palliative-care",
                "癌症安寧照護保險金",
                palliative,
                "per_unit",
                f"{unit_note}罹患確定日後第 1 至第 5 個周年日仍生存者，每年給付一次。",
                f"保單條款{article_refs['癌症安寧照護保險金的給付']}及{table_ref}",
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="annual",
                conditions=[
                    waiting_condition,
                    "限罹患確定日後第 1 至第 5 個周年日，共最多五次",
                    "自罹患確定日起第 6 年起不給付",
                    "第一期前列腺癌、原位癌或惡性黑色素瘤以外之皮膚癌不給付",
                    coverage_end_condition,
                ],
            ),
        ],
    }


NEW_CANCER_LIFETIME_HEADINGS = [
    "保險範圍(一)-「罹患癌症保險金」的給付",
    "保險範圍(二)-「癌症住院醫療保險金」的給付",
    "保險範圍(三)-「癌症出院療養保險金」的給付",
    "保險範圍(四)-「癌症門診醫療保險金」的給付",
    "保險範圍(五)-「癌症手術醫療保險金」的給付",
    "保險範圍(六)-「癌症放射線治療保險金」的給付",
    "保險範圍(七)-「癌症化學治療保險金」的給付",
    "保險範圍(八)-「骨髓或幹細胞移植保險金」的給付",
    "保險範圍(九)-「完全殘廢保險金」的給付",
    "保險範圍(十)-「身故保險金或喪葬費用保險金」的給付",
    "保險範圍(十一)-「祝壽保險金」的給付",
]


def parse_antai_fubon_new_cancer_lifetime_unit_table(
    document: dict[str, Any],
) -> dict[str, Any] | None:
    product_id = str(document.get("product_id") or "")
    if product_id not in ANTAI_FUBON_NEW_CANCER_LIFETIME_PRODUCT_IDS:
        return None
    if document.get("document_type") != "policy_terms":
        return None
    if not str(document.get("file_name") or "").endswith("-A.pdf"):
        return None

    text = normalize_terms_text(str(document.get("text") or ""))
    if "新防癌終身健康保險" not in text:
        return None
    if any(heading not in text for heading in NEW_CANCER_LIFETIME_HEADINGS):
        return None

    compact_text = compact_table_text(text)
    required_term_signals = [
        "自本契約生效日或復效日起且持續有效九十日以後",
        "於出院後十四日內再次住院時",
        "不論其每日門診次數為一次或多次均以一日計",
        "不論其每日治療次數為一次或多次均以一日計",
        "不論其每日接受化學治療次數為一次或多次均以一日計",
        "以注射方式",
        "本契約有效期間內「骨髓或幹細胞移植保險金」的給付以一次為限",
        "保險年齡達一百一十歲後之保單周年日",
        "第十條至第十七條",
    ]
    if any(signal not in compact_text for signal in required_term_signals):
        return None

    table_start = text.rfind("附表一")
    table_end = text.find("附表二", table_start)
    if table_start < 0 or table_end <= table_start:
        return None
    compact_table = compact_table_text(text[table_start:table_end])
    required_table_signals = [
        "附表一各項保險金「每承保單位給付金額」",
        "繳費期間內",
        "50000元7500元特定癌症",
        "繳費期間屆滿後",
        "75000元11250元特定癌症",
        "第1-90日1200元/日",
        "同一次住院第91日起1800元/日",
        "癌症出院療養保險金600元/日",
        "癌症門診醫療保險金500元/日",
        "特定癌症惡性腫瘤切除3000元/次",
        "惡性腫瘤切除15000元/次",
        "癌症放射線治療保險金500元/日",
        "癌症化學治療保險金1200元/日",
        "骨髓或幹細胞移植保險金50000元",
        "每一承保單位新臺幣100萬元扣除已給付的各項保險金累計數額後之餘額",
        "每一承保單位之總給付金額以新臺幣100萬元為上限",
    ]
    if any(signal not in compact_table for signal in required_table_signals):
        return None

    revised_funeral_rule = "遺產稅喪葬費扣除額之半數" in compact_text
    if revised_funeral_rule != (product_id == "209321M12B00303"):
        return None
    funeral_rule = (
        "2010-estate-tax-half-deduction"
        if revised_funeral_rule
        else "pre-2010-fixed-funeral-cap"
    )
    funeral_condition = (
        "喪葬費用保險金另受訂約時遺產稅喪葬費扣除額半數及同公司多張契約合計上限約束"
        if revised_funeral_rule
        else "喪葬費用保險金另受當時主管機關公告額度及跨公司合計上限約束"
    )

    table_page = source_page(text, table_start)
    if product_id == "252321M12B00100":
        table_ref = "附表一，第 8 至 9 頁"
    else:
        table_ref = "附表一" + (f"，第 {table_page} 頁" if table_page else "，第 8 頁")
    waiting_condition = "初次生效或復效日起持續有效 90 日以後始開始癌症保障"
    unit_note = "表列金額乘以理賠時實際有效承保單位數。"
    pool_note = (
        "顯示金額為扣除前保障池基準；實際給付為 1,000,000 元乘以理賠時實際有效承保單位數，"
        "再扣除第十條至第十七條已給付的癌症相關保險金累計數額。"
    )
    pool_conditions = [
        "須扣除第十條至第十七條已給付的癌症相關保險金累計數額",
        "實際餘額需依已領理賠總額計算",
        "給付後契約終止",
    ]

    return {
        "selection_type": "unit",
        "input_mode": "unit",
        "selection_source": "terms",
        "selection_label": "承保單位數",
        "selection_guidance": "請依保單首頁輸入正整數承保單位數；系統會換算每項給付與 100 萬元保障池基準。",
        "version_characteristics": {
            "cancer_waiting_days": 90,
            "specific_cancer_rate_percent": 15,
            "per_unit_total_cap": 1_000_000,
            "funeral_benefit_rule": funeral_rule,
        },
        "coverage_entries": [
            coverage_entry(
                "cancer-diagnosis",
                "罹患癌症保險金",
                50_000,
                "per_unit",
                f"{unit_note}僅本項依繳費期間內或期滿後區分金額；特定癌症為各期金額的 15%。",
                f"保單條款第十條及{table_ref}",
                calculation_basis="tiered_or_stepped",
                amount_role="payout",
                limit_scope="lifetime",
                conditions=[
                    waiting_condition,
                    "癌症疾病與特定癌症的本項給付各以一次為限，依實際診斷擇一金額給付",
                ],
                amount_tiers=[
                    {"label": "繳費期間內／癌症疾病", "amount": 50_000},
                    {"label": "繳費期間內／特定癌症", "amount": 7_500},
                    {"label": "繳費期滿後／癌症疾病", "amount": 75_000},
                    {"label": "繳費期滿後／特定癌症", "amount": 11_250},
                ],
            ),
            coverage_entry(
                "cancer-hospital-days-1-90",
                "癌症住院醫療保險金（同一次住院第 1 至 90 日）",
                1_200,
                "daily_per_unit",
                f"{unit_note}按實際住院日數給付，含住院及出院當日。",
                f"保單條款第十一條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, "同一癌症出院後 14 日內再次住院視為同一次住院"],
            ),
            coverage_entry(
                "cancer-hospital-days-91-plus",
                "癌症住院醫療保險金（同一次住院第 91 日起）",
                1_800,
                "daily_per_unit",
                f"{unit_note}第 91 日起按實際住院日數給付，並非住院給付總日數上限。",
                f"保單條款第十一條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, "同一癌症出院後 14 日內再次住院視為同一次住院"],
            ),
            coverage_entry(
                "cancer-discharge-recovery",
                "癌症出院療養保險金",
                600,
                "daily_per_unit",
                f"{unit_note}按該次癌症住院的實際住院日數給付。",
                f"保單條款第十二條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-outpatient",
                "癌症門診醫療保險金",
                500,
                "daily_per_unit",
                f"{unit_note}同日多次癌症門診仍以一日計。",
                f"保單條款第十三條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, "每日門診一次或多次均以一日計"],
            ),
            coverage_entry(
                "specific-cancer-surgery",
                "特定癌症惡性腫瘤切除保險金",
                3_000,
                "per_unit",
                f"{unit_note}依每次外科切除手術給付，不與一般惡性腫瘤切除金額相加。",
                f"保單條款第十四條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_surgery",
                aggregation_rule="choose_one",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "malignant-tumor-surgery",
                "惡性腫瘤切除保險金",
                15_000,
                "per_unit",
                f"{unit_note}依每次外科切除手術給付，不與特定癌症切除金額相加。",
                f"保單條款第十四條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="per_surgery",
                aggregation_rule="choose_one",
                conditions=[waiting_condition],
            ),
            coverage_entry(
                "cancer-radiation",
                "癌症放射線治療保險金",
                500,
                "daily_per_unit",
                f"{unit_note}同日多次放射線治療仍以一日計。",
                f"保單條款第十五條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, "每日治療一次或多次均以一日計"],
            ),
            coverage_entry(
                "cancer-chemotherapy",
                "癌症化學治療保險金",
                1_200,
                "daily_per_unit",
                f"{unit_note}限以注射方式接受化學治療，同日多次仍以一日計。",
                f"保單條款第十六條及{table_ref}",
                calculation_basis="per_unit_per_day",
                amount_role="payout",
                limit_scope="per_day",
                conditions=[waiting_condition, "限注射方式；每日一次或多次均以一日計"],
            ),
            coverage_entry(
                "marrow-stem-cell-transplant",
                "骨髓或幹細胞移植保險金",
                50_000,
                "per_unit",
                unit_note,
                f"保單條款第十七條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="payout",
                limit_scope="lifetime",
                conditions=[waiting_condition, "本契約有效期間內以給付一次為限"],
            ),
            coverage_entry(
                "total-disability-remaining-pool",
                "完全殘廢保險金（保障池餘額）",
                1_000_000,
                "per_unit",
                pool_note,
                f"保單條款第十八條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="base",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=pool_conditions,
            ),
            coverage_entry(
                "death-funeral-remaining-pool",
                "身故保險金或喪葬費用保險金（保障池餘額）",
                1_000_000,
                "per_unit",
                pool_note,
                f"保單條款第十九條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="base",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=[*pool_conditions, funeral_condition],
            ),
            coverage_entry(
                "maturity-remaining-pool",
                "祝壽保險金（保障池餘額）",
                1_000_000,
                "per_unit",
                f"{pool_note}於保險年齡達 110 歲後的保單周年日仍生存時給付。",
                f"保單條款第二十條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="base",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=[*pool_conditions, "保險年齡達 110 歲後之保單周年日仍生存"],
            ),
            coverage_entry(
                "lifetime-total-benefit-cap",
                "每單位總給付上限",
                1_000_000,
                "per_unit",
                "第十條至第二十條各項保險金共用本累計保障池；達上限時契約終止。",
                f"保單條款第九條及{table_ref}",
                calculation_basis="per_unit",
                amount_role="limit",
                limit_scope="lifetime",
                aggregation_rule="cumulative_cap",
                conditions=["各項保險金累計達上限時契約終止"],
            ),
        ],
    }


PLAN_TABLE_PARSERS = [
    (
        "global-winterthur-cancer-annuity-face-amount-v1",
        parse_global_winterthur_cancer_annuity_face_amount,
    ),
    (
        "antai-cancer-lifetime-rider-unit-v1",
        parse_antai_cancer_lifetime_rider_unit_table,
    ),
    (
        "antai-fubon-new-cancer-lifetime-unit-v1",
        parse_antai_fubon_new_cancer_lifetime_unit_table,
    ),
    (
        "fubon-cardio-device-unit-v1",
        parse_fubon_cardio_device_unit_table,
    ),
    (
        "fubon-new-complete-combined-plan-v1",
        parse_fubon_new_complete_combined_plan_table,
    ),
    (
        "fubon-protect-combined-plan-v1",
        parse_fubon_protect_combined_plan_table,
    ),
    (
        "fubon-golden-lohas-combined-plan-v1",
        parse_fubon_golden_lohas_combined_plan_table,
    ),
    (
        "fubon-new-lohas-combined-plan-v1",
        parse_fubon_new_lohas_combined_plan_table,
    ),
    (
        "fubon-lohas-combined-plan-v1",
        parse_fubon_lohas_combined_plan_table,
    ),
    (
        "fubon-easy-combined-plan-v1",
        parse_fubon_easy_combined_plan_table,
    ),
    (
        "fubon-golden-complete-combined-plan-v1",
        parse_fubon_golden_complete_combined_plan_table,
    ),
    (
        "fubon-child-combined-plan-v1",
        parse_fubon_child_combined_plan_table,
    ),
    (
        "fubon-little-tycoon-plan-v1",
        parse_fubon_little_tycoon_plan_table,
    ),
    (
        "prudential-china-daily-hospital-face-amount-v1",
        parse_prudential_china_daily_hospital_face_amount,
    ),
    (
        "prudential-china-medical-endowment-plan-unit-v1",
        parse_prudential_china_medical_endowment_plan_unit,
    ),
    ("accident-abcd-v1", parse_accident_abcd_plan_table),
    ("three-plan-medical-v1", parse_three_plan_medical_table),
    ("fubon-cancer-unit-v1", parse_fubon_cancer_unit_table),
    (
        "kgi-china-life-cancer-account-unit-v1",
        parse_kgi_china_life_cancer_account_unit_table,
    ),
    ("prudential-cancer-account-unit-v1", parse_prudential_cancer_account_unit_table),
    (
        "prudential-cancer-five-year-unit-v1",
        parse_prudential_cancer_five_year_unit_table,
    ),
    (
        "kgi-china-life-cancer-five-year-unit-v1",
        parse_kgi_china_life_cancer_five_year_unit_table,
    ),
    ("fubon-inpatient-medical-unit-v1", parse_fubon_inpatient_medical_unit_table),
    (
        "ritai-dual-unit-inpatient-v1",
        parse_ritai_dual_unit_inpatient_table,
    ),
    (
        "annual-inpatient-account-unit-v1",
        parse_annual_inpatient_account_unit_table,
    ),
    (
        "group-inpatient-limit-unit-v1",
        parse_group_inpatient_limit_unit_table,
    ),
    (
        "group-plan-inpatient-limit-v1",
        parse_group_plan_inpatient_limit_table,
    ),
    (
        "group-cancer-fixed-unit-v1",
        parse_group_cancer_fixed_unit_table,
    ),
]


def parse_plan_table_with_parser(
    document: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    product_id = str(document.get("product_id") or "")
    file_name = str(document.get("file_name") or "")
    strict_antai_cancer_rider_source = (
        product_id in ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_VERSIONS
        or re.fullmatch(r"252321R11A003(?:-[12]|0[34])-[AF]\.pdf", file_name)
        is not None
    )
    if strict_antai_cancer_rider_source:
        schedule = parse_antai_cancer_lifetime_rider_unit_table(document)
        return (
            "antai-cancer-lifetime-rider-unit-v1",
            schedule,
        ) if schedule else None

    if is_fubon_new_lohas_strict_source(document):
        schedule = parse_fubon_new_lohas_combined_plan_table(document)
        return (
            "fubon-new-lohas-combined-plan-v1",
            schedule,
        ) if schedule else None

    if is_fubon_inpatient_medical_strict_source(document):
        schedule = parse_fubon_inpatient_medical_unit_table(document)
        return (
            "fubon-inpatient-medical-unit-v1",
            schedule,
        ) if schedule else None

    for parser_id, parser in PLAN_TABLE_PARSERS:
        schedule = parser(document)
        if schedule:
            return parser_id, schedule
    return None


def parse_plan_table(document: dict[str, Any]) -> dict[str, Any] | None:
    result = parse_plan_table_with_parser(document)
    return result[1] if result else None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(canonical.encode("utf-8"))


def complete_strict_source_document(
    document: dict[str, Any], source_path: Path
) -> dict[str, Any]:
    if (
        not (
            is_fubon_new_lohas_strict_source(document)
            or is_fubon_inpatient_medical_strict_source(document)
        )
        or not source_path.is_file()
    ):
        return document

    try:
        from pypdf import PdfReader

        reader = PdfReader(source_path, strict=False)
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return document

    return {
        **document,
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


def build_proposal_payload(
    *,
    batch_id: str,
    documents: list[dict[str, Any]],
    public_product_ids: set[str],
    documents_dir: Path,
) -> dict[str, Any]:
    matches: dict[str, list[dict[str, Any]]] = {}
    for document in documents:
        product_id = str(document.get("product_id") or "")
        if not product_id:
            continue
        file_name = str(document.get("file_name") or "")
        source_path = documents_dir / batch_id / product_id / file_name
        document = complete_strict_source_document(document, source_path)
        parsed = parse_plan_table_with_parser(document)
        if not parsed:
            continue
        parser_id, schedule = parsed
        source_document_sha256 = (
            sha256_bytes(source_path.read_bytes()) if source_path.is_file() else None
        )
        matches.setdefault(product_id, []).append(
            {
                "parser_id": parser_id,
                "source_file": file_name,
                "source_document_sha256": source_document_sha256,
                "source_text_sha256": sha256_bytes(
                    str(document.get("text") or "").encode("utf-8")
                ),
                "schedule_sha256": sha256_json(schedule),
                "schedule": schedule,
            }
        )

    proposals = []
    for product_id, candidates in sorted(matches.items()):
        status = "proposed"
        reasons = []
        if product_id not in public_product_ids:
            status = "manual_review_required"
            reasons.append("missing_public_content_record")
        if len(candidates) != 1:
            status = "manual_review_required"
            reasons.append("multiple_matching_source_documents")
            if len({candidate["schedule_sha256"] for candidate in candidates}) > 1:
                reasons.append("conflicting_extracted_schedules")
        if any(not candidate["source_document_sha256"] for candidate in candidates):
            status = "manual_review_required"
            reasons.append("missing_source_document")

        proposal = {
            "product_id": product_id,
            "status": status,
            "review_reasons": reasons,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
        proposals.append(proposal)

    return {
        "schema_version": 1,
        "extractor_version": EXTRACTOR_VERSION,
        "generated_at": datetime.now(TAIPEI_TZ).isoformat(timespec="seconds"),
        "batch_id": batch_id,
        "proposal_count": len(proposals),
        "proposed_count": sum(item["status"] == "proposed" for item in proposals),
        "manual_review_count": sum(
            item["status"] == "manual_review_required" for item in proposals
        ),
        "proposals": proposals,
    }


def approved_schedules(
    proposal_payload: dict[str, Any],
    approval_payload: dict[str, Any],
    existing_reviewed_records: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if approval_payload.get("batch_id") != proposal_payload.get("batch_id"):
        raise SystemExit("approval batch_id does not match proposal batch_id")

    proposals = {
        item["product_id"]: item for item in proposal_payload.get("proposals", [])
    }
    existing_by_product_id = {
        str(record.get("product_id") or ""): record
        for record in (existing_reviewed_records or [])
        if record.get("product_id")
    }
    schedules = {}
    reviewed_records = []
    for review in approval_payload.get("reviews", []):
        if review.get("decision") != "approved":
            continue
        product_id = str(review.get("product_id") or "")
        proposal = proposals.get(product_id)
        if not proposal or proposal.get("status") != "proposed":
            raise SystemExit(f"approved product has no promotable proposal: {product_id}")
        candidate = proposal["candidates"][0]
        protected_fields = [
            "parser_id",
            "source_file",
            "source_document_sha256",
            "schedule_sha256",
        ]
        mismatches = [
            field for field in protected_fields if review.get(field) != candidate.get(field)
        ]
        existing_record = existing_by_product_id.get(product_id)
        if mismatches:
            frozen_review_fields = [
                *protected_fields,
                "reviewed_by",
                "reviewed_at",
                "review_note",
            ]
            if existing_record and all(
                existing_record.get(field) == review.get(field)
                for field in frozen_review_fields
            ):
                reviewed_records.append(existing_record)
                continue
            raise SystemExit(
                f"stale or mismatched approval for {product_id}: {', '.join(mismatches)}"
            )
        if not review.get("reviewed_by") or not review.get("reviewed_at"):
            raise SystemExit(f"approval lacks reviewer metadata: {product_id}")

        schedules[product_id] = candidate["schedule"]
        reviewed_record = {
            "product_id": product_id,
            "status": "verified_reference",
            "extractor_version": proposal_payload["extractor_version"],
            **{field: candidate[field] for field in protected_fields},
            "reviewed_by": review["reviewed_by"],
            "reviewed_at": review["reviewed_at"],
            "review_note": str(review.get("review_note") or ""),
            **candidate["schedule"],
        }
        unchanged_review_fields = [
            *protected_fields,
            "reviewed_by",
            "reviewed_at",
            "review_note",
        ]
        if existing_record and all(
            existing_record.get(field) == reviewed_record.get(field)
            for field in unchanged_review_fields
        ):
            reviewed_record = existing_record
        reviewed_records.append(reviewed_record)
    return schedules, reviewed_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build review proposals and promote approved TII plan benefit tables."
    )
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--raw-dir", type=Path, default=Path("work/tii-document-text"))
    parser.add_argument("--documents-dir", type=Path, default=Path("work/tii-documents"))
    parser.add_argument("--content-dir", type=Path, default=Path("data/tii/document-content"))
    parser.add_argument(
        "--proposal-dir", type=Path, default=Path("work/tii-benefit-proposals")
    )
    parser.add_argument(
        "--reviewed-dir", type=Path, default=Path("data/tii/reviewed-benefits")
    )
    parser.add_argument("--approval-file", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    raw_path = args.raw_dir / f"{args.batch_id}-text.json"
    content_path = args.content_dir / f"{args.batch_id}.json"
    if not raw_path.exists() or not content_path.exists():
        raise SystemExit(f"missing input for {args.batch_id}: {raw_path} or {content_path}")

    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    content_payload = json.loads(content_path.read_text(encoding="utf-8"))
    public_product_ids = {
        str(record.get("product_id") or "") for record in content_payload.get("records", [])
    }
    proposal_payload = build_proposal_payload(
        batch_id=args.batch_id,
        documents=raw_payload.get("documents", []),
        public_product_ids=public_product_ids,
        documents_dir=args.documents_dir,
    )
    proposal_path = args.proposal_dir / f"{args.batch_id}.json"
    if not args.dry_run:
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(
            json.dumps(proposal_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    promoted_ids = []
    if args.approval_file:
        if not args.approval_file.is_file():
            raise SystemExit(f"missing approval file: {args.approval_file}")
        approval_payload = json.loads(args.approval_file.read_text(encoding="utf-8"))
        reviewed_path = args.reviewed_dir / f"{args.batch_id}.json"
        existing_reviewed_records = []
        if reviewed_path.is_file():
            existing_reviewed_records = json.loads(
                reviewed_path.read_text(encoding="utf-8")
            ).get("records", [])
        schedules, reviewed_records = approved_schedules(
            proposal_payload,
            approval_payload,
            existing_reviewed_records,
        )
        for record in content_payload.get("records", []):
            product_id = str(record.get("product_id") or "")
            schedule = schedules.get(product_id)
            if schedule:
                record.update(schedule)
                promoted_ids.append(product_id)
        if set(promoted_ids) != set(schedules):
            missing = sorted(set(schedules) - set(promoted_ids))
            raise SystemExit(f"approved schedules have no public content record: {missing}")
        if promoted_ids and not args.dry_run:
            generated_at = datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")
            content_payload["generated_at"] = generated_at
            content_path.write_text(
                json.dumps(content_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            args.reviewed_dir.mkdir(parents=True, exist_ok=True)
            reviewed_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "generated_at": generated_at,
                        "batch_id": args.batch_id,
                        "record_count": len(reviewed_records),
                        "records": reviewed_records,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

    print(
        json.dumps(
            {
                "status": "ok",
                "batch_id": args.batch_id,
                "proposal_count": proposal_payload["proposal_count"],
                "proposed_count": proposal_payload["proposed_count"],
                "manual_review_count": proposal_payload["manual_review_count"],
                "product_ids": [
                    proposal["product_id"] for proposal in proposal_payload["proposals"]
                ],
                "promoted_count": len(promoted_ids),
                "promoted_product_ids": promoted_ids,
                "proposal_path": str(proposal_path),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
