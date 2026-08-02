from __future__ import annotations

from extract_tii_document_content import compact_document_summary, infer_coverage_tags


cancer_terms = " ".join(
    [
        "國際疾病傷害及死因分類標準",
        "被保險人因疾病或意外傷害事故致成完全失能",
        "癌症住院醫療保險金",
        "癌症化學醫療保險金",
    ]
)
cancer_tags = infer_coverage_tags(
    cancer_terms,
    "凱基人壽一年定期癌症醫療帳戶型健康保險附約",
    "健康保險",
)
assert "醫療險" in cancer_tags
assert "癌症險" in cancer_tags
assert "意外險" not in cancer_tags

hybrid_tags = infer_coverage_tags(
    cancer_terms,
    "富邦人壽富幼保傷害暨健康一年定期保險",
    "健康保險",
)
assert "醫療險" in hybrid_tags
assert "意外險" in hybrid_tags

official_injury_tags = infer_coverage_tags(
    "意外傷害身故與失能保障",
    "測試一年定期保險",
    "傷害保險",
)
assert "意外險" in official_injury_tags

structured_summary = compact_document_summary(
    {
        "generated_at": "2026-07-20T00:00:00+08:00",
        "records": [
            {
                "product_id": "252321R11A00304",
                "product_name": "安泰人壽防癌終身健康保險附約(第4次部分變更)",
                "insurance_category": "健康保險",
                "coverage_tags": ["醫療險", "癌症險", "失能/殘扶", "豁免/附加條款"],
                "coverage_entries": [
                    {"id": "cancer-diagnosis", "name": "罹患癌症保險金"},
                    {"id": "cancer-hospital", "name": "癌症住院醫療保險金"},
                ],
            }
        ],
    },
    "tii-life-116",
)
structured_tags = structured_summary["records"][0]["coverage_tags"]
assert structured_tags == ["醫療險", "癌症險", "豁免/附加條款"]

reviewed_summary = compact_document_summary(
    {
        "generated_at": "2026-07-20T00:00:00+08:00",
        "records": [
            {
                "product_id": "PRODUCT-1",
                "product_name": "測試醫療保險",
                "insurance_category": "健康保險",
                "coverage_tags": ["醫療險"],
                "coverage_entries": [
                    {"id": "stale", "name": "舊保障", "amount": 1},
                ],
            }
        ],
    },
    "tii-life-999",
    reviewed_records=[
        {
            "product_id": "PRODUCT-1",
            "status": "verified_reference",
            "parser_id": "parser-1",
            "source_file": "PRODUCT-1-A.pdf",
            "source_document_sha256": "a" * 64,
            "schedule_sha256": "b" * 64,
            "reviewed_at": "2026-07-29T00:00:00+08:00",
            "selection_type": "unit",
            "coverage_entries": [
                {"id": "verified", "name": "已核准保障", "amount": 1000},
            ],
        }
    ],
)
reviewed_record = reviewed_summary["records"][0]
assert reviewed_record["review_status"] == "verified_reference"
assert reviewed_record["source_document_sha256"] == "a" * 64
assert reviewed_record["schedule_sha256"] == "b" * 64
assert reviewed_record["coverage_entries"][0]["id"] == "verified"

print("tii document content tests: ok")
