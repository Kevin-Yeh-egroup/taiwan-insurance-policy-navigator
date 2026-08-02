from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


FAMILY_FINGERPRINT = "9197658f3bf513c0a49fff37"
SOURCE_ROWS = (
    ("209342R11A00105", 0, "209342R11A00105-A.pdf", 14, "pypdf", "2b9f5cae69f5f549e4a3ade06201db66f48a819c4975a42abb060ae070de90a9", "bd4944cb4e403328512c15e93799eb5ddbac20d863517f73db9d5ef84f4427d1"),
    ("209342R11A00106", 1, "209342R11A00106-A.pdf", 14, "pypdf", "bffdfa858a584148b4c59091b5359f9f95b1d76dc004538347a4f6cdde5e1a79", "f5149ad3e41c712dfc3f91eec17634837eba62ab7c541733f75c8a5daefb67b7"),
    ("209342R11A00107", 2, "209342R11A00107-A.pdf", 13, "pypdf", "953e7987d53dfa09b4acc6f6becd762bd4c6c3ccbbe432da21c01478daa78f4a", "c59bdba95f05f9ae29274e2fb8605247c20f154a23397ee0bbdad0d1736998e6"),
    ("209342R11A00108", 3, "209342R11A00108-A.pdf", 13, "pypdf", "c16283d8bc0724e1596e786502131a4b7a4bd443ccf8bb2065fceec50ed46520", "2242fb2e25f5a89b3b0677d967adcdd5a9e4144b98204f7c1300814a240375cb"),
    ("209341RZ1A00522A11Z10000009", 4, "209341RZ1A00522A11Z10000009-A.pdf", 15, "pypdf", "a27deb1ec016232e5685b0514cd940c649dece6e8aae16df0cf5b45c41f37be8", "94f831e91802b499bcac2a968179153533082aef12d4bee358fae798270b81c6"),
    ("209341RZ1A00522A11Z10000010", 5, "209341RZ1A00522A11Z10000010-A.pdf", 15, "pypdf", "a27deb1ec016232e5685b0514cd940c649dece6e8aae16df0cf5b45c41f37be8", "94f831e91802b499bcac2a968179153533082aef12d4bee358fae798270b81c6"),
    ("209341RZ1A00522A11Z10000011", 6, "209341RZ1A00522A11Z10000011-A.pdf", 14, "pypdf", "99bb1d341f104aac35f9a424fd3ec8f3085b7c8f727a6b726f924693c6a04d65", "2dd3c367d854b29bcd05ea4a99fa2e56caa288d9aac1f6d7deaf8560f6b3ab19"),
    ("209341RZ1A00522A11Z10000012", 7, "209341RZ1A00522A11Z10000012-A.pdf", 14, "pypdf", "bfd81ed930896868fc401bd55ed6376bca9216a2f1e32c76b88abcd1c632d964", "445dcfe313b1e940a90b8ec3a641bfbfdf445e39d009bd9839d7b0c88a8fc59d"),
    ("209341RZ1A00522A11Z10000013", 8, "209341RZ1A00522A11Z10000013-A.pdf", 14, "pypdf", "d9cceb4ba78af654e2479dae21bfcb77f46186511fa801fd0fccb3cc79b86d92", "0013f5ae14c3cb4cb7d5175a6e71487c9c3865dd89e86848cb71aa355fe354e3"),
    ("209341RZ1A00522A11Z10000014", 9, "209341RZ1A00522A11Z10000014-A.pdf", 13, "pymupdf", "5d20a5e6209255b84cbb9119e5e0b21f0e85661ff64beea6d6fbda0ce5dcec5e", "980de32f4acb470e1ce5dd1384328f508330fbfcbd3e94747ddd547b4a6d4dc4"),
    ("209341RZ1A00522A11Z10000015", 10, "209341RZ1A00522A11Z10000015-A.pdf", 13, "pymupdf", "4b61788ffbe7fd6cca74f5938de2fb36fb07703d9ea5ec6dcf0319a52c57a722", "872741fd2fd889741ed91d476e611c37692d707affde6701b439f28221a5aded"),
    ("209341RZ1A00522A11Z10000016", 11, "209341RZ1A00522A11Z10000016-A.pdf", 13, "pymupdf", "24df94093b7cc07fef12cebcf4c1f5a3ef0ad730c3ae0a7c08d5d1421295cbe8", "d9dff4d86405157b964d24479744827e105222028dcea1735b49a6e44035ab83"),
    ("209341RZ1A00522A11Z10000017", 12, "209341RZ1A00522A11Z10000017-A.pdf", 13, "pymupdf", "24df94093b7cc07fef12cebcf4c1f5a3ef0ad730c3ae0a7c08d5d1421295cbe8", "d9dff4d86405157b964d24479744827e105222028dcea1735b49a6e44035ab83"),
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

EVENT_STATUS_KEY = "fubon_parent_child_waiver_event_status"
OVERLAP_STATUS_KEY = "fubon_parent_child_waiver_overlap_status"

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
    "main_policyholder_must_be_parent_of_main_insured",
    "insured_role",
    "eligible_event_types",
    "impairment_term",
    "universal_waiting_days",
    "disability_schedule_stabilization_rule",
    "premium_waiver_available",
    "premium_waiver_scope",
    "premium_waiver_until",
    "other_waiver_riders_excluded_from_scope",
    "overlap_refunds_available",
    "contract_own_waiver_periodic_refund_available",
    "other_waiver_balance_refund_available",
    "other_waiver_first_reduces_future_scope_and_rider_premium",
    "death_cash_benefit_available",
    "waiver_is_non_cash_effect",
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
    if revision <= 5:
        return "parent_death_or_legacy_disability_waiver"
    if revision <= 8:
        return "parent_death_or_impairment_waiver"
    return "parent_death_or_impairment_with_overlap_refunds"


def waiver_eligibility() -> dict[str, Any]:
    return {
        "eligibility_state_key": EVENT_STATUS_KEY,
        "ineligible_values": [
            "not_parent_policyholder",
            "no_covered_death_or_impairment",
            "confirmed_not_eligible",
        ],
        "uncertain_values": ["uncertain"],
    }


def overlap_eligibility(*, own_contract: bool) -> dict[str, Any]:
    other_only = (
        "eligible_other_waiver_only"
        if own_contract
        else "eligible_own_contract_only"
    )
    return {
        "eligibility_state_key": OVERLAP_STATUS_KEY,
        "ineligible_values": [
            other_only,
            "no_overlap",
            "event_not_eligible",
        ],
        "uncertain_values": ["uncertain"],
    }


def coverage_entries(revision: int) -> list[dict[str, Any]]:
    entries = [
        {
            "id": "future-premium-waiver",
            "name": "父母身故或失能後續期保險費豁免",
            "amount": None,
            "basis": "policy_premium",
            "source": "terms",
            "note": (
                "主約要保人為主約被保險人之父或母，且其身故或符合附表失能／殘廢程度時，"
                "豁免主約、本附約及其他附約的續期應繳保險費至繳費期滿。"
            ),
            "source_ref": "保險費的豁免",
            "calculation_basis": "waiver",
            "amount_role": "premium_waiver",
            "limit_scope": "per_policy",
            "aggregation_rule": "separate",
            "unit_key": "remaining_premium_amount",
            "policy_state_keys": ["remaining_premium_amount"],
            "result_kind": "non_cash_effect",
            "amount_stage": "non_cash_estimate",
            "conditions": [
                "主契約要保人必須是主契約被保險人的父或母，並以該要保人為本附約被保險人。",
                "事故須為本附約被保險人死亡，或符合本版本附表一及附表二的失能／殘廢程度。",
                "條款沒有一體適用的等待日數；個別失能項目的六個月治療或症狀固定要求仍依附表判定。",
                "本項是免繳續期保費的非現金效果，請填保單尚未到期且仍在豁免範圍內的保費合計。",
            ],
            **waiver_eligibility(),
        }
    ]
    if revision >= 9:
        entries.extend(
            [
                {
                    "id": "contract-own-waiver-periodic-refund",
                    "name": "主約或其他附約自身豁免之逐期保費退還",
                    "amount": None,
                    "basis": "policy_recorded_limit",
                    "source": "terms",
                    "note": (
                        "本附約豁免期間內，主約或其他附約另符合自身豁免約定時，"
                        "其自身應豁免的續期保費由公司逐期退還。"
                    ),
                    "source_ref": "保險費的豁免",
                    "calculation_basis": "policy_state_amount",
                    "amount_role": "payout",
                    "limit_scope": "per_policy",
                    "aggregation_rule": "separate",
                    "unit_key": "fubon_parent_child_contract_own_waiver_refund_amount",
                    "policy_state_keys": [
                        "fubon_parent_child_contract_own_waiver_refund_amount"
                    ],
                    "result_kind": "cash_payout",
                    "amount_stage": "insurer_quoted_amount",
                    "conditions": [
                        "僅第 9 次修訂後版本有本項重疊豁免協調。",
                        "須在本附約已符合豁免期間內，主契約或其他附約另符合其自身豁免約定。",
                        "請填保險公司逐期核定的退還保費合計，不得從其他商品借用固定金額。",
                    ],
                    **overlap_eligibility(own_contract=True),
                },
                {
                    "id": "other-waiver-rider-balance-refund",
                    "name": "其他豁免附約重疊後差額退還",
                    "amount": None,
                    "basis": "policy_recorded_limit",
                    "source": "terms",
                    "note": (
                        "本附約與其他豁免保費附約在同一繳費期間均符合時，"
                        "合計豁免保費扣除該期實際豁免額後的餘額退還要保人。"
                    ),
                    "source_ref": "保險費的豁免",
                    "calculation_basis": "policy_state_amount",
                    "amount_role": "payout",
                    "limit_scope": "per_policy",
                    "aggregation_rule": "separate",
                    "unit_key": "fubon_parent_child_other_waiver_balance_refund_amount",
                    "policy_state_keys": [
                        "fubon_parent_child_other_waiver_balance_refund_amount"
                    ],
                    "result_kind": "cash_payout",
                    "amount_stage": "insurer_quoted_amount",
                    "conditions": [
                        "僅第 9 次修訂後版本有本項重疊豁免協調。",
                        "須在事故當期由本附約與另一豁免保險費附約同時產生豁免。",
                        "請填保險公司依各契約當期保費核定的差額，不得把豁免效果重複計入現金保障。",
                    ],
                    **overlap_eligibility(own_contract=False),
                },
            ]
        )
    return entries


def expected_entry_contracts(revision: int) -> dict[str, dict[str, Any]]:
    ignored = {"source", "note", "source_ref", "conditions"}
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
    overlap = revision >= 9
    return {
        "source_product_id": product_id,
        "family_fingerprint": FAMILY_FINGERPRINT,
        "product_family": "fubon-parent-child-premium-waiver-rider",
        "company_group": "fubon_life",
        "source_batch_id": "tii-life-050",
        "terms_revision": f"partial_change_{revision}",
        "semantic_phase": semantic_phase(revision),
        "source_document_sha256": source["source_document_sha256"],
        "source_text_sha256": source["source_text_sha256"],
        "source_text_extractor": source["source_text_extractor"],
        "source_text_quality": (
            "machine_readable_exact_hash_with_duplicate_source_versions"
            if revision in {4, 5, 11, 12}
            else "machine_readable_exact_hash_pymupdf_recovery"
            if source["source_text_extractor"] == "pymupdf"
            else "machine_readable_exact_hash"
        ),
        "source_page_count": source["page_count"],
        "currency_basis": "twd",
        "rider": True,
        "main_policyholder_must_be_parent_of_main_insured": True,
        "insured_role": "main_policyholder_parent",
        "eligible_event_types": ["death", "scheduled_impairment"],
        "impairment_term": "殘廢" if revision <= 5 else "失能",
        "universal_waiting_days": 0,
        "disability_schedule_stabilization_rule": (
            "item_specific_six_month_treatment_or_stabilization_where_stated"
        ),
        "premium_waiver_available": True,
        "premium_waiver_scope": (
            "main_contract_this_rider_and_other_attached_riders_excluding_other_waiver_riders"
            if overlap
            else "main_contract_this_rider_and_other_attached_riders"
        ),
        "premium_waiver_until": "main_contract_and_rider_payment_period_end",
        "other_waiver_riders_excluded_from_scope": overlap,
        "overlap_refunds_available": overlap,
        "contract_own_waiver_periodic_refund_available": overlap,
        "other_waiver_balance_refund_available": overlap,
        "other_waiver_first_reduces_future_scope_and_rider_premium": overlap,
        "death_cash_benefit_available": False,
        "waiver_is_non_cash_effect": True,
        "required_policy_inputs": [
            EVENT_STATUS_KEY,
            "remaining_premium_amount",
            *(
                [
                    OVERLAP_STATUS_KEY,
                    "fubon_parent_child_contract_own_waiver_refund_amount",
                    "fubon_parent_child_other_waiver_balance_refund_amount",
                ]
                if overlap
                else []
            ),
        ],
        "claim_event_inputs": [EVENT_STATUS_KEY],
        "amount_presentation": (
            "policy_recorded_remaining_premiums_and_insurer_confirmed_overlap_refunds"
            if overlap
            else "policy_recorded_remaining_premiums_as_non_cash_waiver_effect"
        ),
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
        "富邦人壽親子型保險費豁免附約",
        "以主契約要保人為本附約之被保險人",
        "主契約要保人為主契約被保險人之父或母時",
        "一、死亡",
        "附表一及附表二",
        "續期應繳保險費",
        "直至主契約及本附約繳費期間屆滿時為止",
    )
    if any(compact_text(signal) not in dense for signal in common_signals):
        return None
    revision = int(source["revision"])
    legacy_signal = "給付項目:身故、殘廢時,豁免保險費"
    modern_signal = "給付項目:身故、失能時,豁免保險費"
    overlap_signals = (
        "不含其他豁免保險費附約",
        "逐期退還要保人",
        "豁免前後之應繳保險費比例",
    )
    if revision <= 5:
        if compact_text(legacy_signal) not in dense or any(
            compact_text(signal) in dense for signal in overlap_signals
        ):
            return None
    elif revision <= 8:
        if compact_text(modern_signal) not in dense or any(
            compact_text(signal) in dense for signal in overlap_signals
        ):
            return None
    elif (
        compact_text(modern_signal) not in dense
        or any(compact_text(signal) not in dense for signal in overlap_signals)
    ):
        return None
    return {
        "selection_type": "policy_state",
        "input_mode": "policy_state",
        "selection_source": "terms",
        "selection_label": "確認親子關係、事故狀態與剩餘保費",
        "selection_guidance": (
            "先確認主約要保人是主約被保險人的父或母，且父母已身故或符合本版附表失能／殘廢程度；"
            "再依保單填入仍在豁免範圍內的未到期保費。新版若有多重豁免，再填保險公司核定退還額。"
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
        fail(f"coverage Fubon parent-child waiver source product is invalid: {context}")
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
            f"coverage Fubon parent-child waiver source or version boundary is invalid: {context}"
        )
    validate_entries(
        record.get("coverage_entries"),
        expected_entry_contracts(int(source["revision"])),
        f"{context} Fubon parent-child premium waiver rider",
    )
