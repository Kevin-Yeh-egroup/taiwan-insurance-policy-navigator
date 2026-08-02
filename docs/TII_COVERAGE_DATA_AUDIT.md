{
  "generated_at": "2026-08-01T05:32:33+08:00",
  "definitions": {
    "verified_benefit": "A coverage entry with a numeric amount or a calculable terms formula, source=terms, and source_ref.",
    "keyword_summary": "An exact term in reader_focus.coverage.terms; this is not proof of an amount.",
    "structure_status": "A consumer-facing grouping of whether a product can currently calculate benefits, needs user policy values, is pending benefit structuring, or still needs source text."
  },
  "scope": {
    "total_tii_records": 163299,
    "document_summary_records": 155005,
    "records_without_document_summary": 8294,
    "summary_files": 289,
    "life_summary_files": 198,
    "property_summary_files": 91
  },
  "actual_structured_benefits": {
    "records_with_verified_benefits": 4188,
    "records_without_verified_benefits": 159111,
    "present_by_field": {
      "給付項目": 4188,
      "保險範圍": 4188,
      "保險金": 4188,
      "住院": 446,
      "手術": 346,
      "醫療費用": 434
    },
    "missing_by_field": {
      "給付項目": 159111,
      "保險範圍": 159111,
      "保險金": 159111,
      "住院": 162853,
      "手術": 162953,
      "醫療費用": 162865
    }
  },
  "structure_status_counts": {
    "calculated": 507,
    "needs_user_input": 3692,
    "pending_structure": 150806,
    "source_pending": 8294,
    "confirmed_no_amount": 0
  },
  "structure_status_interpretation": {
    "calculated": "已完成條款給付項目、金額或可計算公式的結構化。",
    "needs_user_input": "已有條款公式，但需要保額、單位、計畫別或保單現況才能算出金額。",
    "pending_structure": "已有條款摘要或文件線索，但尚未整理成保障項目與金額；不代表條款沒有保障。",
    "source_pending": "目前只有商品清單或索引，尚未取得/整理可解析的官方條款內容。",
    "confirmed_no_amount": "已確認條款不提供固定或可自動計算金額；目前需人工標記。"
  },
  "reviewed_benefits": {
    "reviewed_product_versions": 4199,
    "records_with_any_structured_entries": 4199,
    "records_with_direct_amount": 440,
    "records_requiring_policy_state": 3692,
    "flattened_coverage_entries": 35794,
    "entry_amount_buckets": {
      "direct_amount": 22287,
      "terms_formula": 2628,
      "requires_policy_state": 10879,
      "not_numeric_or_table_detail": 0
    },
    "selection_modes": {
      "account_value": 1807,
      "face_amount": 1980,
      "fixed": 36,
      "multi_unit": 7,
      "plan": 232,
      "plan_unit": 5,
      "unit": 132
    },
    "policy_state_dependency_product_counts": {
      "保單記載限額/保單現況": 3684,
      "保單帳戶價值": 1807,
      "年金給付金額/年金因子": 1807,
      "保單價值準備金": 1054,
      "保費總和": 1054,
      "當年度保險金額": 1054,
      "前一年度末保單價值準備金": 198,
      "宣告利率": 198,
      "預定利率": 198,
      "未到期保費合計": 113,
      "保單記載住院日額": 27,
      "保單紅利/公司通知金額": 13
    },
    "interpretation": {
      "direct_amount": "條款或計畫表已提供可直接呈現的金額。",
      "terms_formula": "條款有比例、倍數或級距公式；需搭配保額、單位、計畫或條款表格呈現。",
      "requires_policy_state": "金額會隨保單帳戶價值、保價金、利率、保費、限額或事故日狀態變動，需使用者輸入或保險公司試算。",
      "not_numeric_or_table_detail": "條款目前只提供文字、非保證項目或未完整結構化的表格，不能自動算出單一金額。"
    }
  },
  "keyword_only_document_summaries": {
    "present_by_field_among_summaries": {
      "給付項目": 72600,
      "保險範圍": 40831,
      "保險金": 70304,
      "住院": 19057,
      "手術": 23153,
      "醫療費用": 8913
    },
    "missing_by_field_among_summaries": {
      "給付項目": 82405,
      "保險範圍": 114174,
      "保險金": 84701,
      "住院": 135948,
      "手術": 131852,
      "醫療費用": 146092
    },
    "missing_by_field_across_all_tii_records": {
      "給付項目": 90699,
      "保險範圍": 122468,
      "保險金": 92995,
      "住院": 144242,
      "手術": 140146,
      "醫療費用": 154386
    },
    "summary_records_missing_all_six_terms": 59891,
    "summary_records_with_all_six_terms": 3849
  }
}
