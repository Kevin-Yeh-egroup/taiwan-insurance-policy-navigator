from __future__ import annotations

from scan_tii_benefit_candidates import candidate_from_document


TEXT = " ".join(
    [
        "【住院日額保險金之給付】 第十三條",
        "依附表一所列計畫別給付。",
        "附表一 計畫一 計畫二",
        "住院日額保險金 1,000 元 2,000 元",
    ]
)
DOCUMENT = {
    "product_id": "product-a",
    "file_name": "terms.pdf",
    "text": TEXT,
}

first = candidate_from_document(
    "tii-life-test",
    DOCUMENT,
    {"company": "測試人壽", "product_name": "測試醫療險", "insurance_category": "健康保險"},
)
second = candidate_from_document("tii-life-test", DOCUMENT, {})
assert first is not None
assert first["candidate_id"] == second["candidate_id"]
assert "plan" in first["signals"]
assert first["template_fingerprint"]

missing_amount = {**DOCUMENT, "text": TEXT.replace("1,000 元 2,000 元", "依條款辦理")}
assert candidate_from_document("tii-life-test", missing_amount, {}) is None

cross_document_heading = {**DOCUMENT, "text": "【住院日額保險金之給付】 第十三條"}
cross_document_amount = {**DOCUMENT, "text": "附表一 計畫一 1,000 元"}
assert candidate_from_document("tii-life-test", cross_document_heading, {}) is None
assert candidate_from_document("tii-life-test", cross_document_amount, {}) is None

spaced_document = {
    **DOCUMENT,
    "text": TEXT.replace("住院日額保險金", "住 院 日 額 保 險 金").replace("附表一", "附 表 一"),
}
assert candidate_from_document("tii-life-test", spaced_document, {}) is not None

print("tii benefit candidate scanner tests: ok")
