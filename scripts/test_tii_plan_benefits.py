from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    approved_schedules,
    compact_table_text,
    compact_whitespace,
    complete_strict_source_document,
    build_proposal_payload,
    china_life_jinhaoyi_disability_percentages,
    normalize_terms_text,
    parse_antai_cancer_lifetime_rider_unit_table,
    parse_antai_cancer_medical_term_family_unit,
    parse_antai_fubon_new_cancer_lifetime_unit_table,
    parse_antai_new_cancer_lifetime_r11_unit_table,
    parse_antai_specific_major_disease_health_unit_table,
    parse_annual_inpatient_account_unit_table,
    parse_chaoyang_xingnong_group_inpatient_unit_table,
    parse_chaoyang_xingnong_student_group_fixed_schedule,
    parse_fubon_cancer_unit_table,
    parse_fubon_cardio_device_unit_table,
    parse_fubon_child_combined_plan_table,
    parse_fubon_anxin_456_accident_health_fixed_schedule,
    parse_fubon_easy_combined_plan_table,
    parse_fubon_golden_lohas_combined_plan_table,
    parse_fubon_new_lohas_combined_plan_table,
    parse_fubon_golden_complete_combined_plan_table,
    parse_fubon_golden_health_whole_life_table,
    parse_fubon_golden_luck_universal_whole_life_formula,
    parse_fubon_golden_medical_device_unit_table,
    parse_fubon_666_accident_health_plan_table,
    parse_fubon_family_gift_accident_health_plan_table,
    parse_fubon_hsl_inpatient_unit_table,
    parse_fubon_xianganbao_accident_medical_rider_face_amount,
    parse_fubon_new_pingan_accident_plan_table,
    parse_fubon_inpatient_medical_unit_table,
    parse_fubon_little_tycoon_plan_table,
    parse_fubon_lohas_combined_plan_table,
    parse_china_legacy_cancer_whole_life_unit_table,
    parse_china_life_jinhaoyi_face_amount,
    parse_china_life_xinhaoyi_face_amount,
    parse_china_life_dameiwang_usd_periodic_whole_life_formula,
    parse_china_life_meilifeng_usd_periodic_whole_life_formula,
    parse_china_life_meilexiangtui_usd_survival_whole_life_formula,
    parse_china_life_foreign_currency_interest_endowment_formula,
    parse_china_life_foreign_currency_interest_whole_life_formula,
    parse_china_life_group_endowment_face_amount,
    parse_fubon_new_complete_combined_plan_table,
    parse_fubon_new_shouhu_jinnang_accident_health_plan_table,
    parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table,
    parse_fubon_haozhouquan_accident_health_plan_table,
    parse_fubon_health_limit_up_accident_health_fixed_schedule,
    parse_fubon_comprehensive_accident_plan_table,
    parse_fubon_million_heart_accident_health_plan_table,
    parse_fubon_million_new_life_accident_health_plan_table,
    parse_fubon_new_million_heart_accident_health_plan_table,
    parse_fubon_new_million_heart_accident_health_legacy_plan_table,
    parse_fubon_vision_life_accident_health_plan_table,
    parse_fubon_anxin_financial_life_accident_health_plan_table,
    parse_fubon_protect_combined_plan_table,
    parse_fubon_statutory_infectious_plan_table,
    parse_fubon_tiantian_anxin_500_accident_health_plan_table,
    parse_fubon_changanbao_life_service_face_amount,
    parse_fubon_yongai_life_service_face_amount,
    parse_fubon_tzu_chi_marrow_group_life_medical_table,
    parse_fubon_wanan_365_accident_plan_table,
    parse_fubon_golden_guard_accident_health_plan_table,
    parse_fubon_xinfu_life_accident_health_plan_table,
    parse_hsingfu_fuyu_dwa_whole_life_face_amount,
    parse_hsingfu_platinum_endowment_face_amount,
    parse_fubon_legacy_investment_life_face_amount,
    parse_investment_life_guaranteed_face_amount_formula,
    parse_variable_annuity_account_value_formula,
    parse_kgi_china_legacy_investment_life_maturity_face_amount,
    parse_legacy_investment_life_face_or_account_value,
    TAIWAN_XINFUMANZAI_USD_VARIABLE_LIFE_REVISIONS,
    parse_taiwan_age111_variable_universal_life,
    parse_taiwan_xinfumanzai_usd_variable_life,
    parse_taiwan_xinfu_life_maturity_guarantee,
    parse_taiwan_xindeyi_variable_universal_life,
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus,
    parse_taiwan_zhiduoxin_variable_universal_life,
    parse_farglory_kangfu_medical_plan_table,
    parse_global_e_road_peace_overseas_illness_face_amount,
    parse_global_nccu_student_group_fixed_schedule,
    parse_global_ritai_financial_expert_variable_universal_life,
    parse_global_ritai_financial_head_variable_universal_life,
    parse_group_inpatient_limit_unit_table,
    parse_group_plan_inpatient_limit_table,
    parse_group_cancer_fixed_unit_table,
    parse_global_winterthur_cancer_annuity_face_amount,
    parse_kgi_china_life_ritai_cancer_annuity_face_amount,
    parse_kgi_china_life_cancer_account_unit_table,
    parse_kgi_china_life_cancer_five_year_unit_table,
    parse_prudential_cancer_account_unit_table,
    parse_prudential_cancer_five_year_unit_table,
    parse_prudential_daily_hospital_96_plan_table,
    parse_prudential_china_daily_hospital_face_amount,
    parse_prudential_china_life_accident_account_face_amount,
    parse_prudential_china_life_one_three_five_accident_face_amount,
    parse_prudential_group_specific_accident_rider_face_amount,
    parse_prudential_fire_mass_transit_accident_face_amount,
    parse_prudential_china_fixed_hospital_medical_plan_table,
    parse_prudential_china_medical_endowment_plan_unit,
    PRUDENTIAL_SHARED_GENERATIONS_VARIABLE_UNIVERSAL_LIFE_REVISIONS,
    parse_prudential_chuangfu_variable_life,
    parse_prudential_shared_generations_variable_universal_life,
    parse_prudential_legacy_investment_life_face_amount,
    parse_prudential_youyou_legacy_investment_life_maturity_face_amount,
    parse_ritai_dual_unit_inpatient_table,
    parse_plan_table_with_parser,
    parse_taiwan_fishermen_group_medical_plan_table,
    parse_taiwan_drug_anxin_cancer_precision_plan_table,
    parse_taiwan_gold_group_inpatient_limit_plan_table,
    parse_taiwan_group_inpatient_limit_plan_table,
    parse_taiwan_shishizai_inpatient_plan_table,
    parse_taiwan_chuanshi_fuli_whole_life_formula,
    parse_taiwan_fixed_return_whole_life_formula,
    parse_taiwan_interest_rate_accident_whole_life_formula,
    parse_taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health,
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health,
    parse_taiwan_wudong_legacy_variable_universal_life,
    parse_taiwan_interest_rate_endowment_formula,
    parse_taiwan_interest_rate_specific_disease_whole_life_formula,
    parse_taiwan_interest_rate_specific_disease_survival_whole_life_formula,
    parse_taiwan_usd_endowment_formula,
    parse_taiwan_qianwan_chuxing_a_accident_face_amount,
    parse_taiwan_group_long_term_care_service_face_amount,
    parse_taiwan_taipei_student_group_fixed_schedule,
    parse_taiwan_interest_rate_return_whole_life_formula,
    parse_taiwan_fengfu_meili_usd_interest_whole_life,
    parse_taiwan_interest_rate_whole_life_formula,
    parse_taiwan_interest_rate_survival_whole_life_formula,
    parse_taiwan_funeral_service_rider_fixed,
    parse_taiwan_longzaitian_funeral_service_rider_fixed,
    parse_taiwan_longai_funeral_service_whole_life_fixed,
    parse_taiwan_funeral_service_whole_life_early_tower_plan,
    parse_taiwan_funeral_service_whole_life_early_plan,
    parse_taiwan_funeral_service_whole_life_plan,
    parse_taiwan_yibao_3xiang_medical_whole_life_face_amount,
    parse_taiwan_yixiang_health_medical_whole_life_fixed,
    parse_taiwan_lehuo_health_medical_whole_life_fixed,
    parse_taiwan_participating_return_whole_life_formula,
    parse_taiwan_participating_whole_life_formula,
    parse_taiwan_platinum_account_endowment_formula,
    parse_taiwan_simple_term_life_formula,
    parse_taiwan_usd_no_disability_formula,
    parse_taiwan_term_life_formula,
    parse_taiwan_long_term_care_whole_life_formula,
    parse_taiwan_yiqijianzhi_specific_disease_face_amount,
    parse_taiwan_qianwan_chuxing_b_endowment_face_amount,
    parse_three_plan_medical_table,
    parse_yuanta_new_accident_medical_rider_face_amount,
    parse_yuanta_personal_accident_rider_face_amount,
    parse_yuanta_funxinyou_accident_medical_addendum_limit,
    parse_yuanta_health_life_early_face_amount,
    parse_yuanta_anxin100_critical_illness_face_amount,
    parse_yuanta_zhen_anxin_return_cancer_face_amount,
    parse_yuanta_zhenai_baby_return_life_face_amount,
    parse_yuanta_yuanman225_interest_endowment_formula,
    parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula,
    parse_yuanta_yuanqi_shizu_hospital_medical_plan_table,
    parse_yuanta_group_hospital_medical_plan_table,
    parse_yuanta_new_account_medical_type_daily,
    parse_yuanta_xiangan_medical_plan_table,
    parse_yuanta_xiangyouxin_medical_plan_table,
    repair_antai_cancer_lifetime_rider_text,
)


HEADINGS = " ".join(
    [
        "【住院日額保險金之給付】 第十三條",
        "【住院醫療費用保險金（實支實付）之給付】 第十四條",
        "【門診手術費用保險金（實支實付）之給付】 第十五條",
        "【特定處置費用保險金（實支實付）之給付】 第十六條",
        "【住院前後門診保險金之給付】 第十七條",
        "【醫療費用未經全民健康保險給付者之處理方式】 第十八條",
        "實際支付之各項費用的 70% 給付",
        "【保險金給付之限制】 第二十條",
    ]
)
TABLE = " ".join(
    [
        "第 7 頁，共 9 頁",
        "附表一：投保計劃別內容",
        "單位：新臺幣元",
        r"項目\計劃別 計劃一 計劃二 計劃三",
        "住院日額保險金 1,000/日 2,000/日 3,000/日",
        "住院醫療費用保險金限額 50,000 100,000 150,000",
        "門診手術或特定處置費用保險金限額 30,000 30,000 30,000",
        "住院前後門診保險金 600/次 800/次 1,000/次",
        "每年保險金給付總限額 500,000 1,000,000 1,500,000",
        "附表二：特定處置項目",
    ]
)


schedule = parse_three_plan_medical_table({"text": f"{HEADINGS} {TABLE}"})
assert schedule is not None
assert schedule["selection_type"] == "plan"
assert [plan["label"] for plan in schedule["plan_options"]] == ["計畫一", "計畫二", "計畫三"]

plan_two = schedule["plan_options"][1]
entries = {entry["id"]: entry for entry in plan_two["coverage_entries"]}
assert entries["hospital-daily"]["amount"] == 2_000
assert entries["hospital-daily"]["calculation_basis"] == "per_day"
assert entries["inpatient-medical-limit"]["amount"] == 100_000
assert entries["inpatient-medical-limit"]["amount_role"] == "limit"
assert entries["outpatient-surgery-limit"]["aggregation_rule"] == "choose_one"
assert entries["special-procedure-limit"]["aggregation_rule"] == "choose_one"
assert entries["pre-post-outpatient"]["amount"] == 800
assert entries["annual-medical-cap"]["amount"] == 1_000_000
assert entries["annual-medical-cap"]["limit_scope"] == "annual"
assert all(entry["source"] == "terms" for entry in entries.values())
assert all("附表一" in entry["source_ref"] for entry in entries.values())

missing_row = TABLE.replace("每年保險金給付總限額 500,000 1,000,000 1,500,000", "")
assert parse_three_plan_medical_table({"text": f"{HEADINGS} {missing_row}"}) is None

missing_heading = HEADINGS.replace("【保險金給付之限制】 第二十條", "")
assert parse_three_plan_medical_table({"text": f"{missing_heading} {TABLE}"}) is None

four_plan_table = TABLE.replace("計劃三", "計劃三 計劃四")
assert parse_three_plan_medical_table({"text": f"{HEADINGS} {four_plan_table}"}) is None

FUBON_HEADINGS = " ".join(
    [
        "【保險範圍：罹患癌症保險金的給付】 第八條 實際承保有效之單位數 百分之十五",
        "【保險範圍：癌症住院醫療保險金的給付】 第九條",
        "【保險範圍：癌症出院療養保險金的給付】 第十條",
        "【保險範圍：癌症外科手術醫療保險金的給付】 第十一條 十四日內",
        "【保險範圍：癌症門診醫療保險金的給付】 第十二條 不論其每日門診次數為一次或多次",
        "【保險範圍：癌症放射線治療保險金的給付】 第十三條 不論其每日治療次數為一次或多次",
        "【保險範圍：癌症化學治療保險金的給付】 第十四條",
        "【保險範圍：癌症安寧照護保險金的給付】 第十五條 第二、三、四、五個罹患確定日之周年日 癌症(初期)時",
    ]
)
FUBON_TABLE = " ".join(
    [
        "PCC 7/7 附表一：每承保單位數給付金額",
        "罹患癌症保險金 第一保單年度至第二十保單年度 50,000 元",
        "第二十一保單年度(含)起 75,000 元",
        "癌症住院醫療保險金 同一次住院第 1-90 日 1,200 元/日 第 91 日起 1,800 元/日",
        "癌症出院療養保險金 600 元/日",
        "癌症外科手術醫療保險金 15,000 元/次",
        "癌症門診醫療保險金 500 元/日",
        "癌症放射線治療保險金 500 元/日",
        "癌症化學治療保險金 800 元/日",
        "癌症安寧照護保險金 第 1、2、3、4、5 個周年日仍生存 20,000 元/年",
    ]
)

fubon_schedule = parse_fubon_cancer_unit_table({"text": f"{FUBON_HEADINGS} {FUBON_TABLE}"})
assert fubon_schedule is not None
assert fubon_schedule["selection_type"] == "unit"
assert fubon_schedule["input_mode"] == "unit"
fubon_entries = {entry["id"]: entry for entry in fubon_schedule["coverage_entries"]}
assert len(fubon_entries) == 9
assert fubon_entries["cancer-diagnosis"]["amount"] == 50_000
assert fubon_entries["cancer-diagnosis"]["calculation_basis"] == "tiered_or_stepped"
assert fubon_entries["cancer-diagnosis"]["amount_tiers"] == [
    {"label": "第 1 至 20 保單年度", "amount": 50_000},
    {"label": "第 21 保單年度起", "amount": 75_000},
]
assert "15%" in fubon_entries["cancer-diagnosis"]["conditions"][0]
assert fubon_entries["cancer-hospital-days-1-90"]["amount"] == 1_200
assert fubon_entries["cancer-hospital-days-91-plus"]["amount"] == 1_800
assert fubon_entries["cancer-surgery"]["amount"] == 15_000
assert fubon_entries["cancer-surgery"]["calculation_basis"] == "per_unit"
assert fubon_entries["cancer-hospice-anniversary"]["amount"] == 20_000
assert all("附表一，第 7 頁" in entry["source_ref"] for entry in fubon_entries.values())

spaced_fubon = FUBON_TABLE.replace("附表一", "附 表 一").replace("癌症安寧", "癌症 安寧")
assert parse_fubon_cancer_unit_table({"text": f"{FUBON_HEADINGS} {spaced_fubon}"}) is not None
assert parse_fubon_cancer_unit_table({"text": FUBON_TABLE}) is None
assert parse_fubon_cancer_unit_table(
    {"text": f"{FUBON_HEADINGS} {FUBON_TABLE.replace('15,000 元/次', '')}"}
) is None

PRUDENTIAL_HEADINGS = " ".join(
    [
        "【附約的終止】 第十條 本附約累積給付保險金總額每投保單位超過新台幣二百萬元時",
        "【癌症住院醫療保險金及其申領】 第十三條",
        "【癌症住院手術費用保險金及其申領】 第十四條 每次住院期間以給付一次為限 接受骨髓移植醫療時,不給付本項住院手術費用保險金",
        "【癌症出院後療養保險金及其申領】 第十五條",
        "【癌症門診醫療保險金及其申領】 第十六條 不論其每日門診次數為一次或多次",
        "【癌症放射線醫療保險金及其申領】 第十七條 不論其每日接受放射線治療次數為一次或多次",
        "【癌症化學醫療保險金及其申領】 第十八條 不論其每日接受化學治療次數為一次或多次",
        "【癌症骨髓移植保險金及其申領】 第十九條",
        "【癌症義肢裝設保險金及其申領】 第廿條 四肢各以給付一次為限",
        "【癌症義齒裝設保險金及其申領】 第廿一條 同一保單年度內以給付一次為限",
    ]
)
PRUDENTIAL_TABLE = " ".join(
    [
        "CUCR 10/10 附表二 幣值單位：新台幣元 給付項目 每投保單位給付之保險金",
        "癌症住院醫療保險金(每日) 2,000 元",
        "癌症住院手術費用保險金 30,000 元",
        "癌症出院後療養保險金(每日) 1,000 元",
        "癌症門診醫療保險金(每日) 1,000 元",
        "癌症放射線醫療保險金(每日) 3,000 元",
        "癌症化學醫療保險金(每日) 3,000 元",
        "癌症骨髓移植保險金 100,000 元",
        "癌症義肢裝設保險金 20,000 元",
        "癌症義齒裝設保險金 20,000 元",
    ]
)

prudential_schedule = parse_prudential_cancer_account_unit_table(
    {"text": f"{PRUDENTIAL_HEADINGS} {PRUDENTIAL_TABLE}"}
)
assert prudential_schedule is not None
assert prudential_schedule["selection_type"] == "unit"
prudential_entries = {
    entry["id"]: entry for entry in prudential_schedule["coverage_entries"]
}
assert len(prudential_entries) == 10
assert prudential_entries["cancer-hospital-daily"]["amount"] == 2_000
assert prudential_entries["cancer-inpatient-surgery"]["amount"] == 30_000
assert prudential_entries["cancer-inpatient-surgery"]["aggregation_rule"] == "choose_one"
assert prudential_entries["cancer-marrow-transplant"]["amount"] == 100_000
assert prudential_entries["cancer-dentures"]["limit_scope"] == "annual"
assert prudential_entries["cancer-total-benefit-threshold"]["amount"] == 2_000_000
assert prudential_entries["cancer-total-benefit-threshold"]["amount_role"] == "reference"
assert all(
    "附表二，第 10 頁" in entry["source_ref"]
    for entry_id, entry in prudential_entries.items()
    if entry_id != "cancer-total-benefit-threshold"
)
assert parse_prudential_cancer_account_unit_table({"text": PRUDENTIAL_TABLE}) is None
assert parse_prudential_cancer_account_unit_table(
    {"text": f"{PRUDENTIAL_HEADINGS} {PRUDENTIAL_TABLE.replace('100,000 元', '')}"}
) is None

KGI_ACCOUNT_HEADINGS = " ".join(
    [
        "中國人壽一年定期癌症醫療帳戶型健康保險附約",
        "【名詞定義】 第二條 本附約承保之癌症為被保險人在等待期間屆滿後所發生者為限 "
        "本附約所稱等待期間係指本附約生效日起算九十日(含)或復效日起算九十日(含)之期間",
        PRUDENTIAL_HEADINGS,
    ]
)
KGI_ACCOUNT_DOCUMENT = {
    "product_id": "205321R11A54500",
    "document_type": "policy_terms",
    "text": f"{KGI_ACCOUNT_HEADINGS} {PRUDENTIAL_TABLE.replace('附表二', '附表三')}",
}
kgi_account_schedule = parse_kgi_china_life_cancer_account_unit_table(
    KGI_ACCOUNT_DOCUMENT
)
assert kgi_account_schedule is not None
kgi_account_entries = {
    entry["id"]: entry for entry in kgi_account_schedule["coverage_entries"]
}
assert len(kgi_account_entries) == 10
assert kgi_account_entries["cancer-hospital-daily"]["amount"] == 2_000
assert kgi_account_entries["cancer-inpatient-surgery"]["amount"] == 30_000
assert kgi_account_entries["cancer-total-benefit-threshold"]["amount"] == 2_000_000
assert "復效時另自復效日起算 90 日" in kgi_account_entries["cancer-hospital-daily"][
    "conditions"
][0]
assert "第二條" in kgi_account_entries["cancer-hospital-daily"]["source_ref"]
assert "附表三，第 10 頁" in kgi_account_entries["cancer-hospital-daily"]["source_ref"]

duplicated_kgi_account = {
    **KGI_ACCOUNT_DOCUMENT,
    "text": KGI_ACCOUNT_DOCUMENT["text"].replace("附表三", "附表附表附表附表三三三三"),
}
assert parse_kgi_china_life_cancer_account_unit_table(duplicated_kgi_account) is not None
no_total_page_kgi_account = {
    **KGI_ACCOUNT_DOCUMENT,
    "text": KGI_ACCOUNT_DOCUMENT["text"].replace("CUCR 10/10", "【AUCR】-10-"),
}
assert parse_kgi_china_life_cancer_account_unit_table(no_total_page_kgi_account) is not None

ocr_kgi_account = {
    **KGI_ACCOUNT_DOCUMENT,
    "product_id": "205321R11A54503",
    "text": KGI_ACCOUNT_DOCUMENT["text"]
    .replace("癌症住院醫療保險金及其申領", "癌症住院醫療葆險金及其申領")
    .replace("癌症門診醫療保險金及其申領", "癌症門診醫療保險命其申")
    .replace("癌症骨髓移植保險金及其申領】 第十九條", "癌症骨髓移植保險金及其申領 】 第十九被")
    .replace("癌症義肢裝設保險金及其申領", "癌症義肢裝設呆險金及其申領")
    .replace("不論其每日門診次數為一次或多次", "不論其母钙一籔為一次或多次")
    .replace(
        "給付項目 每投保單位給付之保險金 癌症",
        "每投保單位給付之保險金 給付項 癌症",
    )
    .replace("接受骨髓移植醫療時,不給付", "接受骨髓移植醫療時 , 不給付")
    .replace("1,000 元", "1 , 0 0 0 元"),
}
assert parse_kgi_china_life_cancer_account_unit_table(ocr_kgi_account) is not None
assert parse_kgi_china_life_cancer_account_unit_table(
    {**KGI_ACCOUNT_DOCUMENT, "product_id": "205321R11A99900"}
) is None
assert parse_kgi_china_life_cancer_account_unit_table(
    {
        **KGI_ACCOUNT_DOCUMENT,
        "text": KGI_ACCOUNT_DOCUMENT["text"].replace("等待期間屆滿後", "確診後"),
    }
) is None
assert parse_kgi_china_life_cancer_account_unit_table(
    {
        **KGI_ACCOUNT_DOCUMENT,
        "text": KGI_ACCOUNT_DOCUMENT["text"].replace("30,000 元", "31,000 元"),
    }
) is None

PRUDENTIAL_FIVE_YEAR_HEADINGS = " ".join(
    [
        "【累積總給付金額限制與附約的終止】 第十條 累積給付保險金總額每投保單位達新台幣二百萬元",
        "【癌症住院醫療保險金及其申領】 第十三條",
        "【癌症住院手術費用保險金及其申領】 第十四條 接受骨髓移植醫療、義肢裝設及義齒裝設時,不給付本項手術費用保險金",
        "【癌症出院後療養保險金及其申領】 第十五條",
        "【癌症門診醫療保險金及其申領】 第十六條 不論其每日門診次數為一次或多次,均以一日計",
        "【癌症放射線醫療保險金及其申領】 第十七條 不論其每日接受放射線醫療次數為一次或多次,均以一日計",
        "【癌症化學治療保險金及其申領】 第十八條 不論其每日接受化學治療次數為一次或多次,均以一日計",
        "【癌症骨髓移植保險金及其申領】 第十九條",
        "【癌症義肢裝設保險金及其申領】 第廿條",
        "【癌症義齒裝設保險金及其申領】 第廿一條 同一保單年度內以給付一次為限",
    ]
)
PRUDENTIAL_FIVE_YEAR_TABLE = " ".join(
    [
        "DCTR 8/8 【附件三】 幣值單位:新台幣元 給付項目 每投保單位給付之保險金",
        "癌症住院醫療保險金(每日) 2,000 元",
        "非原位癌之癌症 30,000 元 癌症住院手術費用保險金(每次) 原位癌 3,000 元",
        "癌症出院後療養保險金(每日) 1,000 元",
        "癌症門診醫療保險金(每日) 1,000 元",
        "癌症放射線醫療保險金(每日) 3,000 元",
        "癌症化學治療保險金(每日) 3,000 元",
        "癌症骨髓移植保險金(每次) 100,000 元",
        "癌症義肢裝設保險金(每次) 20,000 元",
        "癌症義齒裝設保險金(每次) 20,000 元",
        "【附件四】",
    ]
)

five_year_schedule = parse_prudential_cancer_five_year_unit_table(
    {"text": f"{PRUDENTIAL_FIVE_YEAR_HEADINGS} {PRUDENTIAL_FIVE_YEAR_TABLE}"}
)
assert five_year_schedule is not None
five_year_entries = {
    entry["id"]: entry for entry in five_year_schedule["coverage_entries"]
}
assert len(five_year_entries) == 10
assert five_year_entries["cancer-hospital-daily"]["amount"] == 2_000
assert five_year_entries["cancer-inpatient-surgery"]["amount_tiers"] == [
    {"label": "非原位癌之癌症", "amount": 30_000},
    {"label": "原位癌", "amount": 3_000},
]
assert five_year_entries["cancer-marrow-transplant"]["amount"] == 100_000
assert five_year_entries["cancer-total-benefit-threshold"]["amount"] == 2_000_000
assert parse_prudential_cancer_five_year_unit_table(
    {"text": PRUDENTIAL_FIVE_YEAR_TABLE}
) is None
assert parse_prudential_cancer_five_year_unit_table(
    {
        "text": f"{PRUDENTIAL_FIVE_YEAR_HEADINGS} "
        f"{PRUDENTIAL_FIVE_YEAR_TABLE.replace('100,000 元', '')}"
    }
) is None

KGI_FIVE_YEAR_HEADINGS = " ".join(
    [
        "凱基人壽癌症五年定期醫療保險附約(96)",
        "【名詞定義】 第二條 本附約承保之『癌症』為被保險人在等待期間屆滿後所發生者為限 "
        "本附約所稱『等待期間』係指本附約生效日起算九十日(含)之期間",
        "【累積總給付金額限制與附約的終止】 第十條 "
        "累積給付保險金總額每投保單位達新台幣五十萬元時，本附約效力即行終止",
        "【癌症住院醫療保險金及其申領】 第十三條",
        "【癌症住院手術費用保險金及其申領】 第十四條 "
        "接受骨髓移植醫療、義肢裝設及義齒裝設時，不給付本項手術費用保險金",
        "【癌症出院後療養保險金及其申領】 第十五條",
        "【癌症門診醫療保險金及其申領】 第十六條 每日門診次數均以一日計",
        "【癌症放射線醫療保險金及其申領】 第十七條 每日接受放射線醫療次數均以一日計",
        "【癌症化學治療保險金及其申領】 第十八條 每日接受化學治療次數均以一日計",
        "【癌症骨髓移植保險金及其申領】 第十九條",
        "【癌症義肢裝設保險金及其申領】 第廿條",
        "【癌症義齒裝設保險金及其申領】 第廿一條 同一保單年度內以給付一次為限",
    ]
)
KGI_FIVE_YEAR_TABLE = " ".join(
    [
        "FCTR 11/11 【附件三】 幣值單位:新台幣元 給付項目 每投保單位給付之保險金",
        "癌症住院醫療保險金(每日) 500 元",
        "癌症住院手術費用保險金(每次) 非原位癌之癌症 7,500 元 原位癌 750 元",
        "癌症出院後療養保險金(每日) 250 元",
        "癌症門診醫療保險金(每日) 250 元",
        "癌症放射線醫療保險金(每日) 750 元",
        "癌症化學治療保險金(每日) 750 元",
        "癌症骨髓移植保險金(每次) 25,000 元",
        "癌症義肢裝設保險金(每次) 5,000 元",
        "癌症義齒裝設保險金(每次) 5,000 元",
        "【附件四】",
    ]
)

kgi_five_year_schedule = parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321RZ1A00222A11Z10000011",
        "text": f"{KGI_FIVE_YEAR_HEADINGS} {KGI_FIVE_YEAR_TABLE}",
    }
)
assert kgi_five_year_schedule is not None
kgi_five_year_entries = {
    entry["id"]: entry for entry in kgi_five_year_schedule["coverage_entries"]
}
assert len(kgi_five_year_entries) == 10
assert kgi_five_year_entries["cancer-hospital-daily"]["amount"] == 500
assert kgi_five_year_entries["cancer-inpatient-surgery"]["amount_tiers"] == [
    {"label": "非原位癌之癌症", "amount": 7_500},
    {"label": "原位癌", "amount": 750},
]
assert kgi_five_year_entries["cancer-discharge-recovery"]["amount"] == 250
assert kgi_five_year_entries["cancer-marrow-transplant"]["amount"] == 25_000
assert kgi_five_year_entries["cancer-total-benefit-threshold"]["amount"] == 500_000
assert "90 日" in kgi_five_year_entries["cancer-hospital-daily"]["conditions"][0]
assert "第二條、第十三條及附件三，第 11 頁" in kgi_five_year_entries[
    "cancer-hospital-daily"
]["source_ref"]

kgi_original_headings = KGI_FIVE_YEAR_HEADINGS.replace(
    "新台幣五十萬元", "新台幣二百萬元"
).replace(
    "之期間",
    "或復效日起算九十日(含)之期間",
    1,
)
kgi_original_table = KGI_FIVE_YEAR_TABLE.replace(
    "癌症住院醫療保險金(每日) 500 元",
    "癌症住院醫療保險金(每日) 2,000 元",
).replace(
    "癌症住院手術費用保險金(每次) 非原位癌之癌症 7,500 元 原位癌 750 元",
    "非原位癌之癌症 30,000 元 癌症住院手術費用保險金(每次) 原位癌 3,000 元",
).replace(
    "癌症出院後療養保險金(每日) 250 元",
    "癌症出院後療養保險金(每日) 1,000 元",
).replace(
    "癌症門診醫療保險金(每日) 250 元",
    "癌症門診醫療保險金(每日) 1,000 元",
).replace(
    "癌症放射線醫療保險金(每日) 750 元",
    "癌症放射線醫療保險金(每日) 3,000 元",
).replace(
    "癌症化學治療保險金(每日) 750 元",
    "癌症化學治療保險金(每日) 3,000 元",
).replace(
    "癌症骨髓移植保險金(每次) 25,000 元",
    "癌症骨髓移植保險金(每次) 100,000 元",
).replace(
    "癌症義肢裝設保險金(每次) 5,000 元",
    "癌症義肢裝設保險金(每次) 20,000 元",
).replace(
    "癌症義齒裝設保險金(每次) 5,000 元",
    "癌症義齒裝設保險金(每次) 20,000 元",
)
kgi_original_schedule = parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321R11A00200",
        "text": f"{kgi_original_headings} {kgi_original_table}",
    }
)
assert kgi_original_schedule is not None
kgi_original_entries = {
    entry["id"]: entry for entry in kgi_original_schedule["coverage_entries"]
}
assert kgi_original_entries["cancer-hospital-daily"]["amount"] == 2_000
assert kgi_original_entries["cancer-total-benefit-threshold"]["amount"] == 2_000_000
assert "復效時" in kgi_original_entries["cancer-hospital-daily"]["conditions"][0]

duplicated_kgi_table = KGI_FIVE_YEAR_TABLE.replace(
    "【附件三】", "【【附件三附件三】】"
)
assert parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321R11A00204",
        "text": f"{KGI_FIVE_YEAR_HEADINGS} {duplicated_kgi_table}",
    }
) is not None
assert parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321R11A00204",
        "text": f"{KGI_FIVE_YEAR_HEADINGS} "
        f"{KGI_FIVE_YEAR_TABLE.replace('原位癌 750 元', '')}",
    }
) is None
assert parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321R11A00204",
        "text": f"{KGI_FIVE_YEAR_HEADINGS.replace('九十日', '')} {KGI_FIVE_YEAR_TABLE}",
    }
) is None
assert parse_kgi_china_life_cancer_five_year_unit_table(
    {
        "product_id": "205321R11A00204",
        "text": f"{KGI_FIVE_YEAR_HEADINGS} {kgi_original_table}",
    }
) is None
assert parse_kgi_china_life_cancer_five_year_unit_table(
    {"product_id": "203321R11A00204", "text": f"{KGI_FIVE_YEAR_HEADINGS} {KGI_FIVE_YEAR_TABLE}"}
) is None

RITAI_DUAL_UNIT_TEXT = " ".join(
    [
        "中國人壽瑞泰住院醫療保險附約(投資型商品版-定額加強型)",
        "疾病係指被保險人自本附約生效日起，且持續有效三十日或復效日以後發生之疾病，但續保者不受限制。",
        "【住院醫療保險金之給付】 第六條",
        "住院前後七天門診保險金",
        "不含加護病房及燒燙傷中心之合計住院給付日數，最高以三百六十五日為限",
        "【手術及雜費保險金之給付】 第七條",
        "同一次手術中於同一手術位置接受兩項器官以上手術時，按最高一項計算",
        "每次住院期間最高給付天數以三百六十五天為限",
        "住院醫療保險金表 住院醫療保險金一單位：新台幣500元",
        "住院日額保險金 500 加護病房日額保險金 500 燒燙傷中心日額保險金 500",
        "住院前後七天門診保險金（每次）150",
        "手術及雜費保險金表 手術及雜費保險金一單位：新台幣5,000元",
        "手術定額保險金（按手術名稱及費用表，最高者可達400%）5,000",
        "住院之第1-7日（每日）300 住院雜費保險金 住院之第8日以後（每日）150",
        "附表一 手術名稱及費用表 角膜異物除去術 2% 兩個以上瓣膜換置術 400%",
    ]
)
ritai_schedule = parse_ritai_dual_unit_inpatient_table(
    {
        "product_id": "205311R11A50801",
        "document_type": "policy_terms",
        "file_name": "205311R11A50801-A.pdf",
        "text": RITAI_DUAL_UNIT_TEXT,
    }
)
assert ritai_schedule is not None
assert ritai_schedule["selection_type"] == "multi_unit"
assert [field["key"] for field in ritai_schedule["unit_fields"]] == [
    "hospital_medical",
    "surgery_misc",
]
ritai_entries = {entry["id"]: entry for entry in ritai_schedule["coverage_entries"]}
assert len(ritai_entries) == 6
assert ritai_entries["hospital-daily"]["amount"] == 500
assert ritai_entries["hospital-daily"]["unit_key"] == "hospital_medical"
assert ritai_entries["pre-post-outpatient"]["amount"] == 150
assert ritai_entries["inpatient-surgery-base"]["amount"] == 5_000
assert ritai_entries["inpatient-surgery-base"]["rate_min_percent"] == 2
assert ritai_entries["inpatient-surgery-base"]["rate_max_percent"] == 400
assert ritai_entries["inpatient-misc-daily"]["unit_key"] == "surgery_misc"
assert ritai_entries["inpatient-misc-daily"]["amount_tiers"] == [
    {"label": "住院第 1 至 7 日", "amount": 300},
    {"label": "住院第 8 日起", "amount": 150},
]
assert parse_ritai_dual_unit_inpatient_table(
    {
        "product_id": "205311R11A50801",
        "document_type": "product_summary",
        "file_name": "205311R11A50801-F.pdf",
        "text": RITAI_DUAL_UNIT_TEXT,
    }
) is None
assert parse_ritai_dual_unit_inpatient_table(
    {
        "product_id": "205311R11A50801",
        "document_type": "policy_terms",
        "file_name": "205311R11A50801-A.pdf",
        "text": RITAI_DUAL_UNIT_TEXT.replace("住院之第8日以後（每日）150", ""),
    }
) is None

RITAI_FIXED_ENHANCED_PRODUCT_IDS = (
    "262311R11A00201",
    "262311R11A00202",
)
RITAI_FIXED_ENHANCED_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-158"
)


def ritai_fixed_enhanced_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    path = RITAI_FIXED_ENHANCED_ROOT / product_id / file_name
    reader = PdfReader(path, strict=False)
    text = normalize_terms_text("\n".join(page.extract_text() or "" for page in reader.pages))
    return {
        "product_id": product_id,
        "file_name": file_name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(reader.pages),
        "pages_parsed": len(reader.pages),
        "text": text,
    }


ritai_fixed_enhanced_schedules = {
    product_id: parse_ritai_dual_unit_inpatient_table(
        ritai_fixed_enhanced_document(product_id)
    )
    for product_id in RITAI_FIXED_ENHANCED_PRODUCT_IDS
}
assert all(ritai_fixed_enhanced_schedules.values())
assert all(
    schedule["selection_type"] == schedule["input_mode"] == "multi_unit"
    for schedule in ritai_fixed_enhanced_schedules.values()
)
assert all(
    [field["key"] for field in schedule["unit_fields"]]
    == ["hospital_medical", "surgery_misc"]
    for schedule in ritai_fixed_enhanced_schedules.values()
)
for product_id, schedule in ritai_fixed_enhanced_schedules.items():
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == 6
    assert entries["hospital-daily"]["amount"] == 500
    assert entries["intensive-care-daily"]["amount"] == 500
    assert entries["burn-center-daily"]["amount"] == 500
    assert entries["pre-post-outpatient"]["amount"] == 150
    assert entries["inpatient-surgery-base"]["amount"] == 5_000
    assert entries["inpatient-surgery-base"]["rate_min_percent"] == 2
    assert entries["inpatient-surgery-base"]["rate_max_percent"] == 400
    assert entries["inpatient-misc-daily"]["amount_tiers"] == [
        {"label": "住院第 1 至 7 日", "amount": 300},
        {"label": "住院第 8 日起", "amount": 150},
    ]
    assert entries["hospital-daily"]["unit_key"] == "hospital_medical"
    assert entries["inpatient-misc-daily"]["unit_key"] == "surgery_misc"
    assert parse_plan_table_with_parser(ritai_fixed_enhanced_document(product_id))[0] == (
        "ritai-dual-unit-inpatient-v1"
    )
assert parse_ritai_dual_unit_inpatient_table(
    ritai_fixed_enhanced_document("262311R11A00201", "F")
) is None
bad_ritai_fixed_enhanced_amount = {
    **ritai_fixed_enhanced_document("262311R11A00202"),
    "text": ritai_fixed_enhanced_document("262311R11A00202")["text"].replace(
        "住院之第 8 日以後 (每日) 150", "住院之第 8 日以後 (每日) 140", 1
    ),
}
assert parse_ritai_dual_unit_inpatient_table(bad_ritai_fixed_enhanced_amount) is None

ANNUAL_ACCOUNT_HEADINGS = " ".join(
    [
        "【住院日額醫療保險金及其申領】 第十三條 依附表二所列金額",
        "【加護病房保險金及其申領】 第十四條",
        "【癌症住院醫療保險金及其申領】 第十五條",
        "【居家療養看護保險金及其申領】 第十六條",
        "【住院手術保險金及其申領】 第十七條 手術項目給付比率",
        "【住院前後門診保險金及其申領】 第十八條 住院前一週 出院後二週",
        "【住院醫療雜費保險金及其申領】 第十九條",
    ]
)
ANNUAL_ACCOUNT_TABLE = " ".join(
    [
        "DUHI 10/11 【附表二】 幣值單位:新台幣元 給付項目 每 1,000 元保險金額之給付金額",
        "住院日額醫療保險金(每日) 住院 30 日(含)以下 1,000 元/日",
        "住院超過 30 日,第 31 日起至 90 日(含) 1,500 元/日",
        "住院超過 90 日,第 91 日起 2,000 元/日",
        "加護病房保險金(每日) 1,000 元/日",
        "癌症住院醫療保險金(每日) 1,000 元/日",
        "居家療養看護保險金(每日) 500 元/日",
        "住院手術保險金(每次) 10,000 元/次×手術項目給付比率",
        "住院前後門診保險金(住院前1週、後2週)(每日) 250 元/日",
        "住院醫療雜費保險金(每日) 200 元/日",
        "【附表三】 手術名稱及費用表 2% 17.5% 300%",
    ]
)

annual_account_schedule = parse_annual_inpatient_account_unit_table(
    {"text": f"{ANNUAL_ACCOUNT_HEADINGS} {ANNUAL_ACCOUNT_TABLE}"}
)
assert annual_account_schedule is not None
assert annual_account_schedule["selection_type"] == "unit"
annual_account_entries = {
    entry["id"]: entry for entry in annual_account_schedule["coverage_entries"]
}
assert len(annual_account_entries) == 7
assert annual_account_entries["hospital-daily-tiered"]["amount_tiers"] == [
    {"label": "住院第 1 至 30 日", "amount": 1_000},
    {"label": "住院第 31 至 90 日", "amount": 1_500},
    {"label": "住院第 91 日起", "amount": 2_000},
]
assert annual_account_entries["intensive-care-daily"]["amount"] == 1_000
assert annual_account_entries["inpatient-surgery-base"]["amount"] == 10_000
assert annual_account_entries["inpatient-surgery-base"]["rate_min_percent"] == 2
assert annual_account_entries["inpatient-surgery-base"]["rate_max_percent"] == 300
assert annual_account_entries["inpatient-medical-expense-daily"]["amount"] == 200
assert all("每 1 單位代表" in entry["note"] for entry in annual_account_entries.values())
assert parse_annual_inpatient_account_unit_table({"text": ANNUAL_ACCOUNT_TABLE}) is None
assert parse_annual_inpatient_account_unit_table(
    {"text": f"{ANNUAL_ACCOUNT_HEADINGS} {ANNUAL_ACCOUNT_TABLE.replace('200 元/日', '')}"}
) is None

GROUP_INPATIENT_LIMIT_HEADINGS = " ".join(
    [
        "【每日病房費用保險金之給付】 第六條 每次住院給付之金額不得超過",
        "【住院醫療費用保險金之給付】 第七條 每次不得超過附表一「每日病房費用保險金限額」的百分之六十 意外傷害事故二十四小時內接受急診，最高以新台幣 5,000 元為限",
        "【手術費用保險金之給付】 第八條 同一次手術中於同一手術位置",
        "【住院日額補償保險金選擇給付】 第九條 則不得再申領",
        "【醫療費用未經全民健康保險給付者之處理方式】 第十條 實際支付之各項費用之 65% 給付",
        "【保險金給付之限制】 第十三條",
    ]
)
GROUP_INPATIENT_LIMIT_TABLE = " ".join(
    [
        "附表一 各項給付限額表 給付項目 給付限制",
        "每日病房費用保險金限額 100 元 × 投保單位",
        "每次住院醫療費用保險金限額 3,000 元 × 投保單位",
        "每次手術費用保險金限額 4,000 元 × 投保單位",
        "附表二 手術名稱及費用表 10% 125% 500%",
        "附表三 經驗分紅計算公式",
    ]
)

group_inpatient_schedule = parse_group_inpatient_limit_unit_table(
    {"text": f"{GROUP_INPATIENT_LIMIT_HEADINGS} {GROUP_INPATIENT_LIMIT_TABLE}"}
)
assert group_inpatient_schedule is not None
assert group_inpatient_schedule["selection_type"] == "unit"
group_inpatient_entries = {
    entry["id"]: entry for entry in group_inpatient_schedule["coverage_entries"]
}
assert len(group_inpatient_entries) == 6
assert group_inpatient_entries["hospital-room-limit"]["amount"] == 100
assert group_inpatient_entries["hospital-room-limit"]["calculation_basis"] == "reimbursement_with_cap"
assert group_inpatient_entries["inpatient-medical-limit"]["amount"] == 3_000
assert group_inpatient_entries["pre-post-outpatient-limit"]["amount"] == 60
assert group_inpatient_entries["accident-emergency-limit"]["amount"] == 5_000
assert group_inpatient_entries["accident-emergency-limit"]["basis"] == "per_event"
assert group_inpatient_entries["hospital-surgery-limit-base"]["amount"] == 4_000
assert group_inpatient_entries["hospital-surgery-limit-base"]["rate_min_percent"] == 10
assert group_inpatient_entries["hospital-surgery-limit-base"]["rate_max_percent"] == 500
assert group_inpatient_entries["hospital-daily-option"]["aggregation_rule"] == "choose_one"
assert "65%" in group_inpatient_entries["inpatient-medical-limit"]["note"]
assert parse_group_inpatient_limit_unit_table({"text": GROUP_INPATIENT_LIMIT_TABLE}) is None
assert parse_group_inpatient_limit_unit_table(
    {
        "text": f"{GROUP_INPATIENT_LIMIT_HEADINGS} "
        f"{GROUP_INPATIENT_LIMIT_TABLE.replace('3,000 元 × 投保單位', '')}"
    }
) is None
spaced_group_table = GROUP_INPATIENT_LIMIT_TABLE.replace("100%", "1 0 0 %").replace(
    "500%", "5 0 0 %"
)
assert parse_group_inpatient_limit_unit_table(
    {"text": f"{GROUP_INPATIENT_LIMIT_HEADINGS} {spaced_group_table}"}
) is not None

GROUP_PLAN_LIMIT_HEADINGS = " ".join(
    [
        "【住院醫療費用保險金之給付】 第十七條",
        "【門診手術費用補償保險金之給付】 第十八條",
        "【住院醫療費用保險金及門診手術費用補償保險金給付之限制】 第十九條",
        "【住院日額補償保險金之給付】 第二十條",
        "【醫療費用未經全民健康保險給付者之處理方式】 第二十三條 實際支付之各項費用之 100％給付",
    ]
)
GROUP_PLAN_LIMIT_TABLE = " ".join(
    [
        "第 8 頁，共 8 頁",
        "附表二：各計劃別所對應之給付限制 單位：新臺幣",
        "給付型態 項目 計劃A 計劃B 計劃C 計劃D 計劃E 計劃F 計劃G 計劃H 計劃I 計劃J 計劃K",
        "實支實付型 保險金限額 6萬元 8萬元 10萬元 12萬元 14萬元 20萬元 3萬元 7萬元 5萬元 8萬元 10萬元",
        "日額給付型 住院日額 600元 1,200元 1,800元 2,400元 3,000元 4,800元 900元 1,000元 500元 800元 1,000元",
        "最高給付住院日數 31日 31日 31日 31日 31日 31日 31日 31日 31日 31日 31日",
    ]
)

group_plan_schedule = parse_group_plan_inpatient_limit_table(
    {"text": f"{GROUP_PLAN_LIMIT_HEADINGS} {GROUP_PLAN_LIMIT_TABLE}"}
)
assert group_plan_schedule is not None
assert group_plan_schedule["selection_type"] == "plan"
assert [plan["label"] for plan in group_plan_schedule["plan_options"]] == [
    f"計劃 {code}" for code in "ABCDEFGHIJK"
]
plan_f_entries = {
    entry["id"]: entry
    for entry in group_plan_schedule["plan_options"][5]["coverage_entries"]
}
assert len(plan_f_entries) == 3
assert plan_f_entries["inpatient-medical-shared-limit"]["amount"] == 200_000
assert plan_f_entries["outpatient-surgery-shared-limit"]["amount"] == 200_000
assert plan_f_entries["inpatient-medical-shared-limit"]["aggregation_rule"] == "cumulative_cap"
assert "共用" in plan_f_entries["outpatient-surgery-shared-limit"]["note"]
assert "100%" in plan_f_entries["inpatient-medical-shared-limit"]["note"]
assert plan_f_entries["hospital-daily-option"]["amount"] == 4_800
assert plan_f_entries["hospital-daily-option"]["aggregation_rule"] == "choose_one"
assert plan_f_entries["hospital-daily-option"]["conditions"] == [
    "同一次住院最高給付 31 日"
]
plan_g_entries = {
    entry["id"]: entry
    for entry in group_plan_schedule["plan_options"][6]["coverage_entries"]
}
assert plan_g_entries["inpatient-medical-shared-limit"]["amount"] == 30_000
assert plan_g_entries["hospital-daily-option"]["amount"] == 900
assert all(
    "附表二，第 8 頁" in entry["source_ref"]
    for plan in group_plan_schedule["plan_options"]
    for entry in plan["coverage_entries"]
)
assert parse_group_plan_inpatient_limit_table({"text": GROUP_PLAN_LIMIT_TABLE}) is None
assert parse_group_plan_inpatient_limit_table(
    {
        "text": f"{GROUP_PLAN_LIMIT_HEADINGS} "
        f"{GROUP_PLAN_LIMIT_TABLE.replace('計劃K', '')}"
    }
) is None
assert parse_group_plan_inpatient_limit_table(
    {
        "text": f"{GROUP_PLAN_LIMIT_HEADINGS} "
        f"{GROUP_PLAN_LIMIT_TABLE.replace('31日 31日', '31日', 1)}"
    }
) is None

GROUP_CANCER_FIXED_HEADINGS = " ".join(
    [
        "【保險範圍】 第五條 被保險人自參加本契約起第六十一日開始；六十日(含)以內確診者退還保險費",
        "【癌症每次住院醫療保險金及其申請】 第十四條 按其投保單位及住院日數給付",
        "【癌症每次住院手術費用保險金及其申請】 第十五條 每次住院期間以給付一次為限",
        "【癌症療養保險金及其申請】 第十六條 每次住院期間最高以給付30日為限",
    ]
)
GROUP_CANCER_FIXED_TABLE = " ".join(
    [
        "6/7 【附件一】 幣值單位：新台幣元 給付項目 每投保單位給付之保險金",
        "癌症每次住院醫療保險金 每日500元",
        "癌症每次住院手術費用保險金 非原位癌之癌症 每次7,500元 原位癌 每次750元",
        "癌症療養保險金 (最高以給付30日為限) 每日500元",
        "7/7 【附件二】團體經驗分紅計算公式",
    ]
)

group_cancer_schedule = parse_group_cancer_fixed_unit_table(
    {"text": f"{GROUP_CANCER_FIXED_HEADINGS} {GROUP_CANCER_FIXED_TABLE}"}
)
assert group_cancer_schedule is not None
assert group_cancer_schedule["selection_type"] == "unit"
group_cancer_entries = {
    entry["id"]: entry for entry in group_cancer_schedule["coverage_entries"]
}
assert len(group_cancer_entries) == 3
assert group_cancer_entries["cancer-hospital-daily"]["amount"] == 500
assert group_cancer_entries["cancer-hospital-daily"]["calculation_basis"] == "per_unit_per_day"
assert group_cancer_entries["cancer-inpatient-surgery"]["amount_tiers"] == [
    {"label": "非原位癌之癌症", "amount": 7_500},
    {"label": "原位癌", "amount": 750},
]
assert group_cancer_entries["cancer-inpatient-surgery"]["conditions"][-1] == (
    "每次住院期間以給付一次為限"
)
assert group_cancer_entries["cancer-recovery-daily"]["amount"] == 500
assert group_cancer_entries["cancer-recovery-daily"]["conditions"][-1] == (
    "每次住院最高給付 30 日"
)
assert all(
    "第 61 日" in entry["note"] for entry in group_cancer_entries.values()
)
assert all(
    "附件一，第 6 頁" in entry["source_ref"]
    for entry in group_cancer_entries.values()
)
assert parse_group_cancer_fixed_unit_table({"text": GROUP_CANCER_FIXED_TABLE}) is None
assert parse_group_cancer_fixed_unit_table(
    {
        "text": f"{GROUP_CANCER_FIXED_HEADINGS} "
        f"{GROUP_CANCER_FIXED_TABLE.replace('每次750元', '')}"
    }
) is None
assert parse_group_cancer_fixed_unit_table(
    {
        "text": f"{GROUP_CANCER_FIXED_HEADINGS.replace('最高以給付30日', '最高以給付29日')} "
        f"{GROUP_CANCER_FIXED_TABLE}"
    }
) is None
older_group_cancer_table = " ".join(
    [
        "5/6 【附件一】國際疾病傷害及死因分類標準",
        "6/6 【附件二】 幣值單位：新台幣元 給付項目 每投保單位給付之保險金",
        "癌症每次住院醫療保險金 每日500元",
        "非原位癌之癌症 每次7,500元 癌症每次住院手術費用保險金 原位癌 每次750元",
        "癌症療養保險金 (最高以給付30日為限) 每日500元",
        "【附件三】團體經驗分紅計算公式",
    ]
)
older_group_cancer_schedule = parse_group_cancer_fixed_unit_table(
    {"text": f"{GROUP_CANCER_FIXED_HEADINGS} {older_group_cancer_table}"}
)
assert older_group_cancer_schedule is not None
assert all(
    "附件二，第 6 頁" in entry["source_ref"]
    for entry in older_group_cancer_schedule["coverage_entries"]
)
duplicated_group_cancer_text = (
    f"{GROUP_CANCER_FIXED_HEADINGS.replace('第六十一日開始', '第六十一日本契約起第六十一日開始')} "
    f"{older_group_cancer_table.replace('【附件二】', '【【附件二附件二】】')}"
)
duplicated_group_cancer_schedule = parse_group_cancer_fixed_unit_table(
    {"text": duplicated_group_cancer_text}
)
assert duplicated_group_cancer_schedule is not None
assert duplicated_group_cancer_schedule["coverage_entries"][1]["amount_tiers"][0][
    "amount"
] == 7_500

PRUDENTIAL_DAILY_HOSPITAL_96_ROOT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-014"
    / "203311R11A00101"
)


def prudential_daily_hospital_96_document(suffix: str = "A") -> dict:
    file_name = "203311R11A00101-A.pdf" if suffix == "A" else "203311R11A00101-F.PDF"
    pdf_path = PRUDENTIAL_DAILY_HOSPITAL_96_ROOT / file_name
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": "203311R11A00101",
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


prudential_daily_96_document = prudential_daily_hospital_96_document()
prudential_daily_96_schedule = parse_prudential_daily_hospital_96_plan_table(
    prudential_daily_96_document
)
assert prudential_daily_96_schedule is not None
parser_id, parsed_schedule = parse_plan_table_with_parser(prudential_daily_96_document)
assert parser_id == "prudential-daily-hospital-96-plan-v1"
assert parsed_schedule == prudential_daily_96_schedule
assert prudential_daily_96_schedule["selection_type"] == "plan"
assert prudential_daily_96_schedule["selection_source"] == "terms"
assert prudential_daily_96_schedule["version_characteristics"] == {
    "terms_revision": "96-first-revision",
    "filing_date": "96.08.31",
    "filing_number": "保誠總字第960667號",
    "plan_count": 6,
    "daily_hospital_days_limit": 365,
    "intensive_care_days_limit": 365,
    "same_hospital_readmission_days": 14,
    "cumulative_termination_daily_multiplier": 1_000,
    "disability_terminology": "完全殘廢",
    "no_surrender_value": True,
}
expected_daily_96 = {
    "FHIR-5": 500,
    "FHIR-10": 1_000,
    "FHIR-15": 1_500,
    "FHIR-20": 2_000,
    "FHIR-25": 2_500,
    "FHIR-30": 3_000,
}
assert [option["label"] for option in prudential_daily_96_schedule["plan_options"]] == list(
    expected_daily_96
)
for option in prudential_daily_96_schedule["plan_options"]:
    entries = {entry["id"]: entry for entry in option["coverage_entries"]}
    daily_amount = expected_daily_96[option["label"]]
    assert set(entries) == {
        "hospital-daily",
        "intensive-care-daily",
        "cumulative-benefit-termination-threshold",
    }
    assert entries["hospital-daily"]["amount"] == daily_amount
    assert entries["hospital-daily"]["source"] == "terms"
    assert entries["hospital-daily"]["limit_scope"] == "per_day"
    assert entries["intensive-care-daily"]["amount"] == daily_amount
    assert entries["intensive-care-daily"]["aggregation_rule"] == "conditional_additive"
    assert entries["cumulative-benefit-termination-threshold"]["amount"] == daily_amount * 1_000
    assert entries["cumulative-benefit-termination-threshold"]["multiplier"] == 1_000
assert parse_prudential_daily_hospital_96_plan_table(
    prudential_daily_hospital_96_document("F")
) is None
assert parse_prudential_daily_hospital_96_plan_table(
    {**prudential_daily_96_document, "product_id": "203311R11A00100"}
) is None
assert parse_prudential_daily_hospital_96_plan_table(
    {
        **prudential_daily_96_document,
        "text": prudential_daily_96_document["text"].replace("3,000 元", "3,100 元", 1),
    }
) is None
indexed_prudential_daily_96 = {
    **prudential_daily_96_document,
    "page_count": 1,
    "pages_parsed": 1,
    "text": prudential_daily_96_document["text"].split("FHIR 2/5")[0],
}
prudential_daily_96_completed = complete_strict_source_document(
    indexed_prudential_daily_96,
    PRUDENTIAL_DAILY_HOSPITAL_96_ROOT / "203311R11A00101-A.pdf",
)
assert prudential_daily_96_completed["page_count"] == 5
assert parse_prudential_daily_hospital_96_plan_table(prudential_daily_96_completed) is not None

DAILY_HOSPITAL_97_TERMS = " ".join(
    [
        "IHIR 1/8 保誠人壽新住院日額型定期健康保險附約(97)保險單條款",
        "IHIR 2/8 【附約的終止】 第八條",
        "被保險人依本附約條款第十一條及第十二條累計已領取之各項保險金總額已達其投保之「住院保險金日額」之一千倍時，本附約即行終止。",
        "本附約「住院保險金日額」減少時，累積總給付金額依減少後「住院保險金日額」之一千倍計算。",
        "IHIR 3/8 【保險範圍】 第十條 因疾病或傷害住院診療時，本公司依第十一條至第十二條之約定給付保險金。",
        "【住院保險金的給付】 第十一條 按其住院日數（含始日及終日）乘以「住院保險金日額」給付住院保險金，但每次住院期間給付日數最高以三百六十五日為限。",
        "【加護病房費用保險金的給付】 第十二條 於加護病房治療期間（含始日及終日），本公司每日按其「住院保險金日額」另行給付每日加護病房費用保險金，但每次住院期間給付日數最高以三百六十五日為限。",
    ]
)
daily_hospital_schedule = parse_prudential_china_daily_hospital_face_amount(
    {
        "product_id": "203311R11A00106",
        "file_name": "203311R11A00106-A.pdf",
        "document_type": "policy_terms",
        "text": DAILY_HOSPITAL_97_TERMS,
    }
)
assert daily_hospital_schedule is not None
assert daily_hospital_schedule["selection_type"] == "face_amount"
assert daily_hospital_schedule["selection_label"] == "住院保險金日額"
daily_hospital_entries = {
    entry["id"]: entry for entry in daily_hospital_schedule["coverage_entries"]
}
assert set(daily_hospital_entries) == {
    "hospital-daily",
    "intensive-care-daily",
    "cumulative-benefit-termination-threshold",
}
assert daily_hospital_entries["hospital-daily"]["rate_percent"] == 100
assert "amount" not in daily_hospital_entries["hospital-daily"]
assert daily_hospital_entries["intensive-care-daily"]["aggregation_rule"] == (
    "conditional_additive"
)
assert daily_hospital_entries["cumulative-benefit-termination-threshold"][
    "multiplier"
] == 1_000
assert "第 2 頁" in daily_hospital_entries[
    "cumulative-benefit-termination-threshold"
]["source_ref"]
assert parse_prudential_china_daily_hospital_face_amount(
    {
        "product_id": "203311R11A00106",
        "file_name": "203311R11A00106-F.pdf",
        "document_type": "policy_summary",
        "text": DAILY_HOSPITAL_97_TERMS,
    }
) is None
assert parse_prudential_china_daily_hospital_face_amount(
    {
        "product_id": "unrelated-product",
        "file_name": "unrelated-product-A.pdf",
        "document_type": "policy_terms",
        "text": DAILY_HOSPITAL_97_TERMS,
    }
) is None

TII_LIFE_014_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-014"
)
TII_LIFE_026_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-026"
)
FIXED_HOSPITAL_MEDICAL_PRODUCT_BATCHES = {
    "203311R11A00205": ("tii-life-014", TII_LIFE_014_ROOT),
    "203311R11A00206": ("tii-life-014", TII_LIFE_014_ROOT),
    "205311RZ1A00322A11Z10000013": ("tii-life-026", TII_LIFE_026_ROOT),
}


def fixed_hospital_medical_document(product_id: str, suffix: str = "A") -> dict:
    _, root = FIXED_HOSPITAL_MEDICAL_PRODUCT_BATCHES[product_id]
    pdf_path = root / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


fixed_hospital_expected = {
    "hospital-daily": (500, 1_000, 1_500, 2_000, 2_500, 3_000),
    "intensive-care-daily": (500, 1_000, 1_500, 2_000, 2_500, 3_000),
    "surgery-benefit-base": (10_000, 20_000, 30_000, 40_000, 50_000, 60_000),
    "surgery-benefit-per-hospitalization-cap": (
        30_000,
        60_000,
        90_000,
        120_000,
        150_000,
        180_000,
    ),
    "cumulative-benefit-termination-threshold": (
        500_000,
        1_000_000,
        1_500_000,
        2_000_000,
        2_500_000,
        3_000_000,
    ),
}
fixed_hospital_expected_revisions = {
    "203311R11A00205": ("101-revised", "完全殘廢", False, False, False, False),
    "203311R11A00206": ("102-revised", "完全殘廢", False, True, False, False),
    "205311RZ1A00322A11Z10000013": (
        "113-revised",
        "完全失能",
        True,
        True,
        True,
        True,
    ),
}
for product_id, (
    expected_revision,
    expected_disability_term,
    expected_day_hospital_excluded,
    expected_post_expiry_excluded,
    expected_medical_opinion_revision,
    expected_forced_execution_exception,
) in fixed_hospital_expected_revisions.items():
    document = fixed_hospital_medical_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 10
    schedule = parse_prudential_china_fixed_hospital_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-china-fixed-hospital-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "保險計劃"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計劃5",
        "計劃10",
        "計劃15",
        "計劃20",
        "計劃25",
        "計劃30",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["disability_terminology"] == expected_disability_term
    assert characteristics["disease_initial_waiting_days"] == 0
    assert characteristics["daily_hospital_days_limit"] == 365
    assert characteristics["intensive_care_days_limit"] == 365
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["surgery_base_daily_multiplier"] == 20
    assert characteristics["surgery_total_cap_daily_multiplier"] == 60
    assert characteristics["cumulative_termination_daily_multiplier"] == 1_000
    assert characteristics["day_hospital_excluded"] is expected_day_hospital_excluded
    assert (
        characteristics["post_expiry_readmission_excluded"]
        is expected_post_expiry_excluded
    )
    assert (
        characteristics["claims_review_medical_opinion_revision"]
        is expected_medical_opinion_revision
    )
    assert (
        characteristics["main_contract_forced_execution_exception"]
        is expected_forced_execution_exception
    )

    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert len(entries) == len(plan["coverage_entries"]) == 5
        assert set(entries) == set(fixed_hospital_expected)
        for entry_id, amounts in fixed_hospital_expected.items():
            assert entries[entry_id]["amount"] == amounts[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert entries[entry_id].get("conditions")
        assert entries["hospital-daily"]["calculation_basis"] == "per_day"
        assert entries["intensive-care-daily"]["aggregation_rule"] == (
            "conditional_additive"
        )
        assert entries["surgery-benefit-base"]["calculation_basis"] == (
            "percentage_of_base"
        )
        assert entries["surgery-benefit-base"]["amount_role"] == "base"
        assert entries["surgery-benefit-base"]["rate_min_percent"] == 2
        assert entries["surgery-benefit-base"]["rate_max_percent"] == 300
        assert entries["surgery-benefit-per-hospitalization-cap"]["amount_role"] == (
            "limit"
        )
        assert (
            entries["surgery-benefit-per-hospitalization-cap"]["limit_scope"]
            == "per_hospitalization"
        )
        assert entries["cumulative-benefit-termination-threshold"]["multiplier"] == (
            1_000
        )

    source_path = FIXED_HOSPITAL_MEDICAL_PRODUCT_BATCHES[product_id][1] / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 10
    assert (
        parse_prudential_china_fixed_hospital_medical_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_prudential_china_fixed_hospital_medical_plan_table(
            fixed_hospital_medical_document(product_id, "F")
        )
        is None
    )

fixed_hospital_base = fixed_hospital_medical_document("203311R11A00205")
assert parse_prudential_china_fixed_hospital_medical_plan_table(
    {**fixed_hospital_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_prudential_china_fixed_hospital_medical_plan_table(
    {**fixed_hospital_base, "document_type": "product_summary"}
) is None
assert parse_prudential_china_fixed_hospital_medical_plan_table(
    {
        **fixed_hospital_base,
        "text": fixed_hospital_base["text"].replace(
            "500 元 1,000 元 1,500 元 2,000 元 2,500 元 3,000 元",
            "600 元 1,000 元 1,500 元 2,000 元 2,500 元 3,000 元",
            1,
        ),
    }
) is None

CHINA_LEGACY_CANCER_PRODUCT_IDS = (
    "205321R11A02300",
    "205321R11A02301",
)
CHINA_LEGACY_CANCER_FILES = {
    "205321R11A02300": "205321R11A023-A.pdf",
    "205321R11A02301": "205321R11A02301-A.pdf",
}
CHINA_LEGACY_CANCER_PAGES = {
    "205321R11A02300": 8,
    "205321R11A02301": 7,
}
CHINA_LEGACY_CANCER_REVISIONS = {
    "205321R11A02300": "original",
    "205321R11A02301": "94-revised",
}


def china_legacy_cancer_document(product_id: str, suffix: str = "A") -> dict:
    file_name = (
        CHINA_LEGACY_CANCER_FILES[product_id]
        if suffix == "A"
        else CHINA_LEGACY_CANCER_FILES[product_id].replace("-A.pdf", "-F.pdf")
    )
    pdf_path = TII_LIFE_026_ROOT / product_id / file_name
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


china_legacy_expected = {
    "cancer-diagnosis": 30_000,
    "cancer-hospital-daily": 2_000,
    "cancer-surgery": 30_000,
    "cancer-discharge-recovery": 1_000,
    "cancer-outpatient": 1_000,
    "cancer-death": 300_000,
}
for product_id in CHINA_LEGACY_CANCER_PRODUCT_IDS:
    document = china_legacy_cancer_document(product_id)
    assert document["file_name"] == CHINA_LEGACY_CANCER_FILES[product_id]
    assert document["page_count"] == document["pages_parsed"] == CHINA_LEGACY_CANCER_PAGES[product_id]
    schedule = parse_china_legacy_cancer_whole_life_unit_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "china-legacy-cancer-whole-life-unit-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "unit"
    assert schedule["selection_label"] == "投保單位數"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == CHINA_LEGACY_CANCER_REVISIONS[product_id]
    assert characteristics["cancer_responsibility_start_day"] == 31
    assert characteristics["premium_waiver_disability_levels"] == "1-3"
    assert characteristics["minor_funeral_benefit_rule"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 6
    assert {entry_id: entry["amount"] for entry_id, entry in entries.items()} == (
        china_legacy_expected
    )
    assert entries["cancer-diagnosis"]["limit_scope"] == "lifetime"
    assert entries["cancer-hospital-daily"]["calculation_basis"] == (
        "per_unit_per_day"
    )
    assert entries["cancer-discharge-recovery"]["calculation_basis"] == (
        "per_unit_per_day"
    )
    assert entries["cancer-outpatient"]["limit_scope"] == "per_event"
    assert entries["cancer-death"]["limit_scope"] == "per_policy"
    assert all("始期日起第 31 日" in " ".join(entry["conditions"]) for entry in entries.values())
    assert "喪葬費用保險金" in " ".join(entries["cancer-death"]["conditions"])

    source_path = TII_LIFE_026_ROOT / product_id / CHINA_LEGACY_CANCER_FILES[product_id]
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == CHINA_LEGACY_CANCER_PAGES[product_id]
    assert parse_china_legacy_cancer_whole_life_unit_table(completed_document) == schedule
    assert parse_china_legacy_cancer_whole_life_unit_table(
        china_legacy_cancer_document(product_id, "F")
    ) is None

china_legacy_base = china_legacy_cancer_document("205321R11A02300")
assert parse_china_legacy_cancer_whole_life_unit_table(
    {**china_legacy_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_china_legacy_cancer_whole_life_unit_table(
    {**china_legacy_base, "document_type": "product_summary"}
) is None
assert parse_china_legacy_cancer_whole_life_unit_table(
    {
        **china_legacy_base,
        "text": china_legacy_base["text"].replace("投保金額 300,000 元", "投保金額 400,000 元", 1),
    }
) is None

MEDICAL_ENDOWMENT_TERMS = " ".join(
    [
        "1/14 保誠人壽歡喜安康醫療養老保險甲型/乙型",
        "【名詞定義】 第二條 疾病係指被保險人自本契約生效日起三十日後或復效日起所發生之疾病。",
        "每次住院期間於出院後十四日內於同一醫院再次住院時，視為一次住院辦理。",
        "3/14 【住院日額保險金的給付】 第十三條 經醫師診斷確定必須住院或於醫院持續診療達六小時（含）以上者，",
        "按同一次住院期間之實際住院日數（含始日及終日）乘以當時有效之住院日額給付，但最高以三百六十五日為限。",
        "【加護病房或燒燙傷中心日額保險金的給付】 第十四條 除住院日額保險金外，另按實際進住日數（含始日及終日）乘以當時有效之住院日額給付，最高以三百六十五日為限。",
        "【身故保險金的給付】 第十五條 按應已繳保險費與保單價值準備金二款所得金額之最大者給付。",
        "【完全殘廢保險金的給付】 第十六條 按應已繳保險費與保單價值準備金二款所得金額之最大者給付。",
        "【滿期保險金的給付】 第十七條 甲型為應已繳保險費的一點零二倍；乙型為應已繳保險費的一點零五倍。",
        "4/14 【保險給付的限制】 第十八條 第十三條與第十四條各項保險金合計總額以住院日額之一千二百五十倍為上限。",
        "7/14 【保險利益】 保險單位 給付項目 5 單位 10 單位 15 單位 20 單位 25 單位 30 單位",
        "住院日額 (最高 365 天) 500 元 1,000 元 1,500 元 2,000 元 2,500 元 3,000 元",
        "加護病房或燒燙傷中心日額 (最高 365 天) 500 元 1,000 元 1,500 元 2,000 元 2,500 元 3,000 元",
        "註：每一保險單位為日額 100 元。",
    ]
)
medical_endowment_schedule = parse_prudential_china_medical_endowment_plan_unit(
    {
        "product_id": "203391M12B00102",
        "file_name": "203391M12B00102-A.pdf",
        "document_type": "policy_terms",
        "text": MEDICAL_ENDOWMENT_TERMS,
    }
)
assert medical_endowment_schedule is not None
assert medical_endowment_schedule["selection_type"] == "plan_unit"
assert [plan["label"] for plan in medical_endowment_schedule["plan_options"]] == ["甲型", "乙型"]
medical_endowment_plan_a = {
    entry["id"]: entry for entry in medical_endowment_schedule["plan_options"][0]["coverage_entries"]
}
medical_endowment_plan_b = {
    entry["id"]: entry for entry in medical_endowment_schedule["plan_options"][1]["coverage_entries"]
}
assert medical_endowment_plan_a["hospital-daily"]["amount"] == 100
assert medical_endowment_plan_a["hospital-daily"]["calculation_basis"] == "per_unit_per_day"
assert medical_endowment_plan_a["intensive-care-burn-center-daily"]["aggregation_rule"] == "conditional_additive"
assert medical_endowment_plan_a["medical-lifetime-cap"]["amount"] == 125_000
assert medical_endowment_plan_a["medical-lifetime-cap"]["limit_scope"] == "lifetime"
assert medical_endowment_plan_a["maturity-benefit"]["rate_percent"] == 102
assert medical_endowment_plan_b["maturity-benefit"]["rate_percent"] == 105
assert "第 7 頁" in medical_endowment_plan_a["hospital-daily"]["source_ref"]

fixed_medical_endowment_schedule = parse_prudential_china_medical_endowment_plan_unit(
    {
        "product_id": "203391M12B00203",
        "file_name": "203391M12B00203-A.pdf",
        "document_type": "policy_terms",
        "text": MEDICAL_ENDOWMENT_TERMS,
    }
)
assert fixed_medical_endowment_schedule is not None
assert fixed_medical_endowment_schedule["selection_type"] == "unit"
assert "乙型" in fixed_medical_endowment_schedule["selection_guidance"]
assert fixed_medical_endowment_schedule["coverage_entries"][-1]["rate_percent"] == 105
assert parse_prudential_china_medical_endowment_plan_unit(
    {
        "product_id": "203391M12B00102",
        "file_name": "203391M12B00102-F.pdf",
        "document_type": "product_summary",
        "text": MEDICAL_ENDOWMENT_TERMS,
    }
) is None
assert parse_prudential_china_medical_endowment_plan_unit(
    {
        "product_id": "203391M12B00102",
        "file_name": "203391M12B00102-A.pdf",
        "document_type": "policy_terms",
        "text": MEDICAL_ENDOWMENT_TERMS.replace("註：每一保險單位為日額 100 元。", ""),
    }
) is None

FUBON_CHILD_COMMON_TERMS = " ".join(
    [
        "第 1 頁 富邦人壽新富幼保傷害暨健康一年定期保險",
        "【名詞定義】 第二條 疾病係指本契約生效日起持續有效三十日以後所發生之疾病。癌症亦須持續有效三十日以後發生。",
        "第 3 頁 【保險範圍:癌症保險金的給付】 第十二條",
        "每日一仟元給付癌症住院醫療保險金。癌症出院療養保險金最高以二十一日為限。",
        "每次手術本公司給付一萬元癌症手術治療保險金。癌症放射線及化學治療最高給付日數以六十日為限。",
        "給付五十萬元之癌症身故保險金。",
        "【保險範圍:住院醫療保險金的給付】 第十三條 住院(含日間留院)，因精神疾病住院每年最高九十日。",
        "日額計畫別住院醫療保險金日額 計畫一 1,000 元 計畫二 1,000 元 計畫三 2,000 元 計畫四 2,000 元",
        "日額計畫別住院看護保險金日額 計畫一 500 元 計畫二 500 元 計畫三 1,000 元 計畫四 1,000 元",
        "日額計畫別燒燙傷中心住院醫療保險金日額 計畫一 3,000 元 計畫二 3,000 元 計畫三 6,000 元 計畫四 6,000 元；同一次住院給付日數最長以三十日為限。",
        "第 6 頁 【保險範圍:重大燒燙傷保險金的給付】 第十六條 給付四十萬元之重大燒燙傷保險金。",
        "【保險範圍:住院醫療保險金的給付】 第十七條 {accident_terms}",
        "同一次意外傷害給付日數不得超過三百六十五日。骨折未住院治療，依骨折日數表計算。",
        "第 7 頁 【保險範圍:意外傷害門診手術醫療保險金的給付】 第十八條",
        "本公司按二仟元之金額給付。每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限。",
        "【保險範圍:意外傷害醫療保險金的給付】 第十九條 同一次傷害的給付總額不得超過四萬元。",
        "以全民健康保險身分接受治療者提高為五萬四仟元。要保人投保本契約計畫一及計畫三者,無本條約定之適用。",
        "【保險範圍:意外身故保險金或喪葬費用保險金的給付】 第二十條 給付一佰萬元意外身故保險金。",
        "第 8 頁 【保險範圍:意外殘廢保險金的給付】 第二十一條",
        "致成附表二所列殘廢程度之一者，按一佰萬元之金額對照該表所列之給付比例計算所得之金額。",
        "不同事故累計給付金額最高以一佰萬元為限。附表二 殘廢等級 11 5%",
    ]
)
FUBON_OLD_ACCIDENT_TERMS = " ".join(
    [
        "本公司按每日一仟元之金額,乘以其實際住院日數。",
        "另按每日一仟元之金額,乘以其實際入住加護病房日數。",
    ]
)
FUBON_NEW_ACCIDENT_TERMS = " ".join(
    [
        "日額計畫別意外傷害住院醫療保險金日額 計畫一 1,005 元 計畫二 1,005 元 計畫三 1,010 元 計畫四 1,010 元",
        "日額計畫別意外傷害加護病房住院醫療保險金日額 計畫一 1,005 元 計畫二 1,005 元 計畫三 1,010 元 計畫四 1,010 元",
    ]
)

old_child_schedule = parse_fubon_child_combined_plan_table(
    {
        "product_id": "209391M12D00100",
        "file_name": "209391M12D00100-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_CHILD_COMMON_TERMS.format(accident_terms=FUBON_OLD_ACCIDENT_TERMS),
    }
)
assert old_child_schedule is not None
assert old_child_schedule["selection_type"] == "plan"
assert [plan["label"] for plan in old_child_schedule["plan_options"]] == [
    "計畫一",
    "計畫二",
    "計畫三",
    "計畫四",
]
assert [len(plan["coverage_entries"]) for plan in old_child_schedule["plan_options"]] == [
    17,
    18,
    17,
    18,
]
old_plan_four_entries = {
    entry["id"]: entry
    for entry in old_child_schedule["plan_options"][3]["coverage_entries"]
}
assert old_plan_four_entries["hospital-daily"]["amount"] == 2_000
assert old_plan_four_entries["hospital-icu-daily"]["amount"] == 4_000
assert old_plan_four_entries["accident-hospital-daily"]["amount"] == 1_000
assert old_plan_four_entries["fracture-without-hospitalization"]["multiplier"] == 0.5
assert old_plan_four_entries["accident-disability"]["rate_min_percent"] == 5
assert old_plan_four_entries["accident-disability"]["rate_max_percent"] == 100
assert old_plan_four_entries["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般情形", "amount": 40_000},
    {"label": "以全民健康保險身分治療", "amount": 54_000},
]
assert "本版本條款明列住院包含日間留院" in old_plan_four_entries[
    "hospital-daily"
]["conditions"]
assert "同一次住院最高給付 30 日" in old_plan_four_entries[
    "burn-center-hospital-daily"
]["conditions"]

new_child_schedule = parse_fubon_child_combined_plan_table(
    {
        "product_id": "209391M12D00300",
        "file_name": "209391M12D00300-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_CHILD_COMMON_TERMS.format(accident_terms=FUBON_NEW_ACCIDENT_TERMS),
    }
)
assert new_child_schedule is not None
assert [
    next(
        entry["amount"]
        for entry in plan["coverage_entries"]
        if entry["id"] == "accident-hospital-daily"
    )
    for plan in new_child_schedule["plan_options"]
] == [1_005, 1_005, 1_010, 1_010]
assert not any(
    entry["id"] == "accident-medical-reimbursement"
    for entry in new_child_schedule["plan_options"][0]["coverage_entries"]
)

FUBON_LATE_CHILD_TERMS = (
    FUBON_CHILD_COMMON_TERMS.format(accident_terms=FUBON_NEW_ACCIDENT_TERMS)
    .replace(
        "【保險範圍:住院醫療保險金的給付】 第十三條",
        "【保險範圍:住院醫療保險金的給付】 MGC11090901 4/21 商品代號:MGC1 第十三條",
    )
    .replace("意外殘廢保險金", "意外失能保險金")
    .replace("附表二所列殘廢程度", "附表二所列失能程度")
    .replace("殘廢等級", "失能等級")
    + " 但不包含全民健康保險法第五十一條所稱之日間住院及精神衛生法所稱之日間留院。"
    + " 訂立本契約時以受監護宣告尚未撤銷者為被保險人。"
    + " 鼻未缺損但鼻功能永久遺存顯著障害，給付比例 5%。"
    + " 被保險人以乘客身分搭乘大眾運輸工具,因遭劫持,契約期滿後至劫持事故終了前仍負第十六條、第二十條及第二十一條給付責任。"
)
late_child_schedule = parse_fubon_child_combined_plan_table(
    {
        "product_id": "209391MZ9D00321A11Z10000006",
        "file_name": "209391MZ9D00321A11Z10000006-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_LATE_CHILD_TERMS,
    }
)
assert late_child_schedule is not None
late_plan_four_entries = {
    entry["id"]: entry
    for entry in late_child_schedule["plan_options"][3]["coverage_entries"]
}
assert late_plan_four_entries["accident-hospital-daily"]["amount"] == 1_010
assert late_plan_four_entries["accident-disability"]["name"] == "意外失能保險金"
assert "附表二失能等級" in late_plan_four_entries["accident-disability"]["note"]
assert "本版本條款明列不包含全民健保日間住院及精神衛生法日間留院" in late_plan_four_entries[
    "hospital-daily"
]["conditions"]
assert "契約期間累積給付次數與總額上限，條款未另行明示" in late_plan_four_entries[
    "major-burn"
]["conditions"]
assert "受監護宣告尚未撤銷者改為喪葬費用保險金，且受法定總額上限限制" in late_plan_four_entries[
    "accident-death"
]["conditions"]
assert "本版本附表二另列鼻未缺損但鼻功能永久遺存顯著障害，給付比例 5%" in late_plan_four_entries[
    "accident-disability"
]["conditions"]
assert any(
    "大眾運輸工具遭劫持" in condition
    for condition in late_plan_four_entries["accident-disability"]["conditions"]
)
assert parse_fubon_child_combined_plan_table(
    {
        "product_id": "209391M12D00300",
        "file_name": "209391M12D00300-F.pdf",
        "document_type": "policy_summary",
        "text": FUBON_CHILD_COMMON_TERMS.format(accident_terms=FUBON_NEW_ACCIDENT_TERMS),
    }
) is None
assert parse_fubon_child_combined_plan_table(
    {
        "product_id": "unrelated-product",
        "file_name": "unrelated-product-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_CHILD_COMMON_TERMS.format(accident_terms=FUBON_NEW_ACCIDENT_TERMS),
    }
) is None

FUBON_LITTLE_TYCOON_TABLE = " ".join(
    [
        "附表一： 計畫別 保險金項目 計畫一 計畫二",
        "意外身故保險金或喪葬費用保險金 100 萬 100 萬",
        "癌症身故保險金 60 萬 60 萬",
        "意外{disability_term}保險金 致成{disability_term}等級之一",
        "100 萬乘以附表二所列給付比例 100 萬乘以附表二所列給付比例",
        "最高給付金額 100 萬 100 萬",
        "癌症住院醫療保險金 3,000 元/日",
        "癌症出院療養保險金 1,500 元/日",
        "癌症手術治療保險金 60,000 元/次",
        "癌症放射線治療保險金 3,000 元/日",
        "意外傷害住院醫療保險金 1,000 元/日",
        "住院醫療日額保險金 1,000 元/日 無",
    ]
)


def fubon_little_tycoon_terms(
    *,
    disability_term: str = "殘廢",
    cancer_waiting_days: int = 30,
    day_hospital: bool = False,
    schedule_items: int = 75,
) -> str:
    waiting_text = "(或復效日持續有效三十日)後" if cancer_waiting_days else "(或復效日)起"
    day_hospital_text = "包含精神衛生法第三十五條所稱之日間留院。" if day_hospital else ""
    schedule_signals = ""
    if schedule_items >= 79:
        schedule_signals += " 附表二項次 1-1-5 8-2-9。"
    if schedule_items == 80:
        schedule_signals += " 4-1-2 鼻未缺損而鼻機能永久遺存顯著障害者。"
    return " ".join(
        [
            "FBI 1/17 富邦人壽小富翁傷害暨健康一年定期保險",
            "本契約保障內容分二個計畫別，各計畫別之給付內容詳附表一。",
            f"九、住院：正式辦理住院手續並確實接受診療者。{day_hospital_text}",
            "【保險範圍：癌症保險金的給付】 第十二條",
            f"被保險人自本契約生效日{waiting_text}之有效期間內始經診斷確定罹患癌症。",
            "癌症住院、出院療養、手術、放射線及身故依附表一給付。",
            "FBI 4/17 【保險範圍：住院醫療日額保險金的給付】 第十三條",
            "因疾病或傷害住院，按實際住院日數給付；同一保單年度同一次住院最高日數以三十日為限。",
            "FBI 5/17 【保險範圍：意外傷害住院醫療保險金的給付】 第十六條",
            "事故後一百八十日內住院，每次意外傷害事故給付日數不得超過九十日。",
            "骨折未住院部分按骨折日數乘以意外傷害住院醫療保險金日額的二分之一給付。",
            "不完全骨折,按完全骨折日數二分之一給付；骨骼龜裂者按完全骨折日數四分之一給付。",
            "FBI 6/17 【保險範圍：意外身故保險金或喪葬費用保險金的給付】 第十七條",
            "意外傷害事故後一百八十日內身故者給付。",
            f"【保險範圍：意外{disability_term}保險金的給付】 第十八條",
            f"事故後一百八十日內致成附表二所列{disability_term}程度之一者給付。",
            "FBI 9/17",
            FUBON_LITTLE_TYCOON_TABLE.format(disability_term=disability_term),
            schedule_signals,
        ]
    )


little_tycoon_old = parse_fubon_little_tycoon_plan_table(
    {
        "product_id": "209391M12D00200",
        "file_name": "209391M12D00200-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_little_tycoon_terms(),
    }
)
assert little_tycoon_old is not None
assert little_tycoon_old["selection_type"] == "plan"
assert little_tycoon_old["version_characteristics"] == {
    "cancer_initial_waiting_days": 30,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": False,
    "disability_schedule_revision": "original-75-items",
}
assert [option["label"] for option in little_tycoon_old["plan_options"]] == [
    "計畫一",
    "計畫二",
]
old_plan_one = {
    entry["id"]: entry
    for entry in little_tycoon_old["plan_options"][0]["coverage_entries"]
}
old_plan_two = {
    entry["id"]: entry
    for entry in little_tycoon_old["plan_options"][1]["coverage_entries"]
}
assert old_plan_one["hospital-daily"]["amount"] == 1_000
assert "hospital-daily" not in old_plan_two
assert old_plan_one["cancer-hospital-daily"]["amount"] == 3_000
assert old_plan_one["cancer-recovery-daily"]["amount"] == 1_500
assert old_plan_one["cancer-surgery"]["amount"] == 60_000
assert old_plan_one["cancer-radiotherapy-daily"]["amount"] == 3_000
assert old_plan_one["cancer-death"]["amount"] == 600_000
assert old_plan_one["accident-hospital-daily"]["amount"] == 1_000
assert old_plan_one["fracture-without-hospitalization"]["multiplier"] == 0.5
assert old_plan_one["accident-death"]["amount"] == 1_000_000
assert old_plan_one["accident-disability"]["rate_min_percent"] == 5
assert old_plan_one["accident-disability"]["rate_max_percent"] == 100

little_tycoon_104 = parse_fubon_little_tycoon_plan_table(
    {
        "product_id": "209391MZ9D00121A11Z10000002",
        "file_name": "209391MZ9D00121A11Z10000002-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_little_tycoon_terms(day_hospital=True, schedule_items=79),
    }
)
assert little_tycoon_104 is not None
assert little_tycoon_104["version_characteristics"] == {
    "cancer_initial_waiting_days": 30,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
}

little_tycoon_109 = parse_fubon_little_tycoon_plan_table(
    {
        "product_id": "209391MZ9D00121A11Z10000007",
        "file_name": "209391MZ9D00121A11Z10000007-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_little_tycoon_terms(
            disability_term="失能",
            cancer_waiting_days=0,
            day_hospital=True,
            schedule_items=80,
        ),
    }
)
assert little_tycoon_109 is not None
assert little_tycoon_109["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "109-revised-80-items",
}
new_plan_one = {
    entry["id"]: entry
    for entry in little_tycoon_109["plan_options"][0]["coverage_entries"]
}
assert new_plan_one["accident-disability"]["name"] == "意外失能保險金"
assert "80 項失能程度" in new_plan_one["accident-disability"]["conditions"][1]
assert any("日間留院" in condition for condition in new_plan_one["hospital-daily"]["conditions"])
assert parse_fubon_little_tycoon_plan_table(
    {
        "product_id": "209391M12D00200",
        "file_name": "209391M12D00200-F.pdf",
        "document_type": "product_summary",
        "text": fubon_little_tycoon_terms(),
    }
) is None
assert parse_fubon_little_tycoon_plan_table(
    {
        "product_id": "unrelated-product",
        "file_name": "unrelated-product-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_little_tycoon_terms(),
    }
) is None

FUBON_PROTECT_TABLE = " ".join(
    [
        "附表一： 計畫一 計畫二 計畫三 計畫四 計畫五",
        "身故保險金或喪葬費用保險金 無 無 無 100 萬 100 萬",
        "意外身故保險金或喪葬費用保險金 100 萬 200 萬 300 萬 100 萬 200 萬",
        "重大燒燙傷保險金 25 萬 50 萬 75 萬 25 萬 50 萬",
        "意外傷害醫療保險金 3 萬 3 萬 3 萬 3 萬 3 萬",
        "每日病房費 1,500 元 每日加護病房費 1,500 元 每次住院手術費 36,000 元",
        "每次住院醫療費 28,056 元",
        "計畫六 計畫七 計畫八 計畫九 計畫十",
        "意外身故保險金或喪葬費用保險金 300 萬 200 萬 300 萬 200 萬 300 萬",
        "一般住院醫療日額 無 無 無 1,000 元/日 1,000 元/日",
        "計畫十一 計畫十二 計畫十三 計畫十四 計畫十五",
        "意外傷害醫療保險金 無 無 無 3 萬 3 萬",
        "計畫十六 計畫十七 計畫十八",
        "意外身故保險金或喪葬費用保險金 100 萬 200 萬 300 萬",
        "一般住院醫療日額 1,000 元/日 1,000 元/日 1,000 元/日",
        "附表二",
    ]
)


def fubon_protect_terms(
    *,
    disability_term: str = "殘廢",
    cancer_waiting_days: int = 30,
    day_hospital: bool = False,
    schedule_items: int = 75,
    new_cancer_classification: bool = False,
) -> str:
    waiting_text = (
        "本契約生效日(或復效日持續有效三十日)後"
        if cancer_waiting_days
        else "本契約生效日(或復效日)起"
    )
    cancer_text = (
        "癌症(初期)、癌症(輕度)或癌症(重度)"
        if new_cancer_classification
        else "原位癌或惡性腫瘤"
    )
    day_hospital_text = (
        "住院定義包含精神衛生法第三十五條所稱之日間留院。"
        "被保險人於投保時已投保其他商業實支實付型醫療保險而未通知本公司者，改以日額方式給付。"
        if day_hospital
        else ""
    )
    schedule_signals = ""
    if schedule_items >= 79:
        schedule_signals += " 附表三項次 1-1-5 8-2-9。"
    if schedule_items == 80:
        schedule_signals += " 4-1-2 鼻未缺損但鼻功能永久遺存顯著障害。"
    return " ".join(
        [
            "MGE 1/27 富邦人壽保倍平安傷害暨健康一年定期保險",
            "本契約保障內容分十八個計畫別，各計畫別給付內容詳附表一。",
            day_hospital_text,
            "MGE 4/27 【保險範圍：身故保險金或喪葬費用保險金的給付】 第十二條",
            f"【保險範圍：完全{disability_term}保險金的給付】 第十三條",
            "MGE 5/27 【保險範圍：初次罹患癌症保險金的給付】 第十七條",
            f"被保險人於{waiting_text}初次診斷確定罹患{cancer_text}。",
            "MGE 6/27 【保險範圍：實支實付型醫療保險金的給付】 第十八條",
            "同一次住院期間之給付日數,以三十一日為限。",
            "同一次住院期間給付日數最高以七日為限。",
            "每顆義齒最高給付以新臺幣五仟元為限。",
            "住院前後門診費但每日以新臺幣五佰元為限。",
            "未住院意外急診本公司於新臺幣五仟元之範圍內給付。",
            "附表一所載意外傷害醫療保險金之限額提高為1.35倍。",
            "MGE 7/27 【保險範圍：住院醫療日額保險金選擇權的行使】 第十九條",
            "被保險人於同一次住院,僅得就第十八條所約定各項實支實付保險金,或本條約定之住院醫療日額保險金選擇一類申請給付。",
            "【保險範圍：日額型住院醫療保險金的給付】 第二十條",
            "MGE 8/27 【保險範圍：重大燒燙傷保險金的給付】 第二十三條",
            "自意外傷害事故發生之日起屆滿十五日仍生存。重大燒燙傷保險金之申領以一次為限。",
            "【保險範圍：意外傷害醫療保險金的給付】 第二十四條",
            "同一次傷害的給付總額不得超過附表一所載意外傷害醫療保險金之限額。",
            "【保險範圍：意外身故保險金或喪葬費用保險金的給付】 第二十五條",
            f"MGE 9/27 【保險範圍：意外{disability_term}保險金的給付】 第二十六條",
            f"【意外身故保險金及意外{disability_term}保險金給付的限制】 第二十七條",
            "MGE 12/27",
            FUBON_PROTECT_TABLE,
            schedule_signals,
        ]
    )


protect_old = parse_fubon_protect_combined_plan_table(
    {
        "product_id": "209391M12G00200",
        "file_name": "209391M12G00200-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_protect_terms(),
    }
)
assert protect_old is not None
assert protect_old["selection_type"] == "plan"
assert protect_old["version_characteristics"] == {
    "cancer_initial_waiting_days": 30,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": False,
    "disability_schedule_revision": "original-75-items",
}
assert [plan["label"] for plan in protect_old["plan_options"]] == [
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
]
assert [len(plan["coverage_entries"]) for plan in protect_old["plan_options"]] == [
    13, 13, 13, 17, 17, 17, 17, 17, 19, 19, 12, 12, 12, 17, 19, 19, 19, 19
]
protect_plan_one = {
    entry["id"]: entry for entry in protect_old["plan_options"][0]["coverage_entries"]
}
assert "policy-death" not in protect_plan_one
assert "initial-early-cancer" not in protect_plan_one
assert protect_plan_one["hospital-room-reimbursement"]["amount_tiers"] == [
    {"label": "附表一限額", "amount": 1_500},
    {"label": "條款第十八條 1.35 倍適用時", "amount": 2_025},
]
assert protect_plan_one["hospital-surgery-reimbursement-base"]["amount"] == 36_000
assert protect_plan_one["hospital-surgery-reimbursement-base"]["calculation_basis"] == "percentage_of_base"
assert protect_plan_one["hospital-medical-reimbursement"]["amount"] == 28_056
assert protect_plan_one["dental-prosthesis-sublimit"]["amount"] == 5_000
assert protect_plan_one["pre-post-hospital-outpatient-sublimit"]["amount"] == 500
assert protect_plan_one["accident-emergency-sublimit"]["amount"] == 5_000
assert protect_plan_one["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般限額", "amount": 30_000},
    {"label": "以全民健康保險身分接受治療", "amount": 40_500},
]
assert protect_plan_one["accident-death"]["amount"] == 1_000_000
assert protect_plan_one["accident-disability"]["rate_min_percent"] == 5
assert protect_plan_one["accident-disability"]["rate_max_percent"] == 100

protect_plan_nine = {
    entry["id"]: entry for entry in protect_old["plan_options"][8]["coverage_entries"]
}
assert protect_plan_nine["policy-death"]["amount"] == 2_000_000
assert protect_plan_nine["initial-early-cancer"]["amount"] == 5_000
assert protect_plan_nine["initial-other-cancer"]["amount"] == 50_000
assert protect_plan_nine["additional-hospital-daily"]["amount"] == 1_000
assert protect_plan_nine["additional-hospital-icu-daily"]["amount"] == 1_000

protect_plan_eleven = {
    entry["id"]: entry for entry in protect_old["plan_options"][10]["coverage_entries"]
}
assert "policy-death" not in protect_plan_eleven
assert "initial-early-cancer" not in protect_plan_eleven
assert "accident-medical-reimbursement" not in protect_plan_eleven
assert "additional-hospital-daily" not in protect_plan_eleven
assert protect_plan_eleven["accident-death"]["amount"] == 1_000_000

protect_plan_eighteen = {
    entry["id"]: entry for entry in protect_old["plan_options"][17]["coverage_entries"]
}
assert protect_plan_eighteen["policy-death"]["amount"] == 1_000_000
assert protect_plan_eighteen["accident-death"]["amount"] == 3_000_000
assert protect_plan_eighteen["major-burn"]["amount"] == 750_000

protect_latest = parse_fubon_protect_combined_plan_table(
    {
        "product_id": "209391MZ1G00221A11Z10000007",
        "file_name": "209391MZ1G00221A11Z10000007-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_protect_terms(
            disability_term="失能",
            cancer_waiting_days=0,
            day_hospital=True,
            schedule_items=80,
            new_cancer_classification=True,
        ),
    }
)
assert protect_latest is not None
assert protect_latest["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "109-revised-80-items",
}
protect_latest_plan = {
    entry["id"]: entry for entry in protect_latest["plan_options"][17]["coverage_entries"]
}
assert protect_latest_plan["total-disability"]["name"] == "完全失能保險金"
assert protect_latest_plan["initial-early-cancer"]["name"] == "初次罹患癌症（初期）保險金"
assert protect_latest_plan["initial-other-cancer"]["name"] == "初次罹患癌症（輕度或重度）保險金"
assert protect_latest_plan["accident-disability"]["name"] == "意外失能保險金"
assert "80 項失能程度" in protect_latest_plan["accident-disability"]["conditions"][1]
assert any(
    "日間留院" in condition
    for condition in protect_latest_plan["hospital-room-reimbursement"]["conditions"]
)
assert parse_fubon_protect_combined_plan_table(
    {
        "product_id": "209391M12G00200",
        "file_name": "209391M12G00200-F.pdf",
        "document_type": "product_summary",
        "text": fubon_protect_terms(),
    }
) is None
assert parse_fubon_protect_combined_plan_table(
    {
        "product_id": "unrelated-product",
        "file_name": "unrelated-product-A.pdf",
        "document_type": "policy_terms",
        "text": fubon_protect_terms(),
    }
) is None


TII_LIFE_050_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
FUBON_NEW_COMPLETE_PRODUCT_IDS = (
    "209391M12G00300",
    "209391M11G00301",
    "209391MZ1G00321A11Z10000002",
    "209391MZ1G00321A11Z10000003",
    "209391MZ1G00321A11Z10000004",
    "209391MZ1G00321A11Z10000005",
    "209391MZ1G00321A11Z10000006",
    "209391MZ1G00321A11Z10000007",
)


def fubon_new_complete_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


assert EXTRACTOR_VERSION == "tii-plan-benefits-v196"

TII_LIFE_011_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-011"
)
TII_LIFE_017_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-017"
)
TII_LIFE_029_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-029"
)
TII_LIFE_053_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-053"
)
TII_LIFE_161_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-161"
)
TII_LIFE_167_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-167"
)
TII_VARIABLE_ANNUITY_ROOTS = {
    "tii-life-012": Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-012",
    "tii-life-054": Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-054",
    "tii-life-168": Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-168",
}
TII_LIFE_167_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-167-text.json"
    ).read_text(encoding="utf-8")
)["documents"]


def investment_life_document(batch_id: str, product_id: str, suffix: str = "A") -> dict:
    roots = {
        "tii-life-011": TII_LIFE_011_ROOT,
        "tii-life-017": TII_LIFE_017_ROOT,
        "tii-life-029": TII_LIFE_029_ROOT,
        "tii-life-053": TII_LIFE_053_ROOT,
        "tii-life-161": TII_LIFE_161_ROOT,
        "tii-life-167": TII_LIFE_167_ROOT,
    }
    if batch_id == "tii-life-167":
        file_name = f"{product_id}-{suffix}.pdf"
        fixture = next(
            document
            for document in TII_LIFE_167_TEXT_FIXTURE
            if document.get("product_id") == product_id
            and document.get("file_name") == file_name
        )
        return {
            "batch_id": batch_id,
            "product_id": product_id,
            "product_name": "投資型壽險測試保單",
            "file_name": file_name,
            "document_type": "policy_terms" if suffix == "A" else "product_summary",
            "text": normalize_terms_text(str(fixture.get("text") or "")),
        }
    root = roots[batch_id]
    file_name = f"{product_id}-{suffix}.pdf"
    if batch_id == "tii-life-161" and product_id == "262141M31A00200":
        file_name = f"262141M31A002-{suffix}.pdf"
    if batch_id == "tii-life-161" and product_id == "262141M31A00300":
        file_name = f"262141M31A003-{suffix}.pdf"
    pdf_path = root / product_id / file_name
    page_texts = [
        page.extract_text() or "" for page in PdfReader(pdf_path, strict=False).pages
    ]
    return {
        "batch_id": batch_id,
        "product_id": product_id,
        "product_name": "投資型壽險測試保單",
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


def variable_annuity_document(batch_id: str, product_id: str, suffix: str = "A") -> dict:
    root = TII_VARIABLE_ANNUITY_ROOTS[batch_id]
    file_name = f"{product_id}-{suffix}.pdf"
    pdf_path = root / product_id / file_name
    page_texts = [
        page.extract_text() or "" for page in PdfReader(pdf_path, strict=False).pages
    ]
    return {
        "batch_id": batch_id,
        "product_id": product_id,
        "product_name": "",
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


investment_life_expected = {
    ("tii-life-011", "202131MV1A05B23A11Z90000000"): {
        "company_group": "taiwan_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_wu",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-011", "202131MV1A34923B11C90000010"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi_bing_ding_minor_age_15",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-011", "202131MV1A42423Z11C90000007"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi_bing_ding_minor_age_15",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-011", "202131MV1A42423Z11C90000008"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi_bing_ding_minor_age_15",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-011", "202131MV1A42423Z11C90000009"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi_bing_ding_minor_age_15",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-011", "202131MV1A69823A11C90000003"): {
        "company_group": "taiwan_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-011", "202131MV1A79923A11Z90000002"): {
        "company_group": "taiwan_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "basic_amount_less_deduction_less_account_value",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-011", "202131MV1A85A23B11Z90000000"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_wu",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-011", "202131MV1AUFL23A11C90000019"): {
        "company_group": "taiwan_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_111_policy_anniversary",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_age_111_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 111,
        "net_risk_formula_type": "jia_yi_bing_ding_minor_age_15",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-017", "203131MU1A00123A11Z90000042"): {
        "company_group": "prudential",
        "currency_basis": "twd",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A00123A11Z90000036"): {
        "company_group": "prudential",
        "currency_basis": "twd",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A00323B11Z90000019"): {
        "company_group": "prudential",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A03223Z11Z90000003"): {
        "company_group": "prudential",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A03523A11Z90000000"): {
        "company_group": "prudential",
        "currency_basis": "twd",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-029", "205131MV1A03823A11C90000006"): {
        "company_group": "kgi_china_life",
        "currency_basis": "twd",
        "maturity_trigger": "policy_maturity_date",
        "maturity_formula": "net_amount_at_risk_plus_policy_account_value_at_policy_maturity_date",
        "maturity_interest": True,
        "maturity_age": None,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A00323B11Z90000017"): {
        "company_group": "prudential",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MU1A00123A11Z90000037"): {
        "company_group": "prudential",
        "currency_basis": "twd",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-029", "205131MV1A00123A11C90000001"): {
        "company_group": "kgi_china_life",
        "currency_basis": "twd",
        "maturity_trigger": "policy_maturity_date",
        "maturity_formula": "policy_account_value_at_policy_maturity_date",
        "maturity_interest": False,
        "maturity_age": None,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-053", "209131MV1A00123A11Z90000010"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 110,
        "net_risk_formula_type": "jia_yi",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-053", "209131MV1A00323Z11Z90000004"): {
        "company_group": "fubon_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 110,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-053", "209131MV1A02023A11C90000000"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 110,
        "net_risk_formula_type": "jia_yi",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-053", "209131MV1A02123B11C90000000"): {
        "company_group": "fubon_life",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 110,
        "net_risk_formula_type": "jia_yi",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-053", "209131MV1A00723A11Z90000000"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 110,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": True,
    },
    ("tii-life-053", "209131MV1A01823A11C90000000"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 110,
        "net_risk_formula_type": "jia_yi",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A02323A11Z90000003"): {
        "company_group": "prudential",
        "currency_basis": "twd",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-017", "203131MV1A02423B11Z90000000"): {
        "company_group": "prudential",
        "currency_basis": "foreign_currency",
        "maturity_trigger": "age_99_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_99_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 99,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
    ("tii-life-167", "264131MV1AVLO23A11Z90000004"): {
        "company_group": "global_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_96_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_96_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 96,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-167", "264131MV1AVLW23A11Z90000002"): {
        "company_group": "global_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_100_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_100_policy_anniversary",
        "maturity_interest": True,
        "maturity_age": 100,
        "net_risk_formula_type": "not_classified",
        "minor_death": False,
        "minor_disability": False,
    },
    ("tii-life-167", "264131MV1AVLN23A11Z90000002"): {
        "company_group": "global_life",
        "currency_basis": "twd",
        "maturity_trigger": "age_110_policy_anniversary",
        "maturity_formula": "policy_account_value_at_age_110_policy_anniversary",
        "maturity_interest": False,
        "maturity_age": 110,
        "net_risk_formula_type": "not_classified",
        "minor_death": True,
        "minor_disability": False,
    },
}
for (batch_id, product_id), expected in investment_life_expected.items():
    document = investment_life_document(batch_id, product_id)
    schedule = parse_investment_life_guaranteed_face_amount_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "investment-life-guaranteed-face-amount-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "investment-linked-life-guaranteed-face-amount"
    )
    assert characteristics["company_group"] == expected["company_group"]
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert characteristics["maturity_trigger"] == expected["maturity_trigger"]
    if expected["maturity_age"] is None:
        assert "maturity_age" not in characteristics
    else:
        assert characteristics["maturity_age"] == expected["maturity_age"]
    assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]
    assert characteristics["maturity_interest_crediting"] == expected["maturity_interest"]
    assert (
        characteristics["net_amount_at_risk_formula_type"]
        == expected["net_risk_formula_type"]
    )
    assert (
        characteristics["minor_death_before_age_15_account_value_rule"]
        == expected["minor_death"]
    )
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        == expected["minor_disability"]
    )
    assert characteristics["death_benefit_formula"] == "policy_insurance_amount"
    assert characteristics["total_disability_benefit_formula"] == "policy_insurance_amount"
    assert characteristics["complete_disability_table_item_count"] == 7
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["death-or-funeral-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert entries["maturity-benefit"]["basis"] == "policy_recorded_limit"

    source_path = (
        {
            "tii-life-011": TII_LIFE_011_ROOT,
            "tii-life-017": TII_LIFE_017_ROOT,
            "tii-life-029": TII_LIFE_029_ROOT,
            "tii-life-053": TII_LIFE_053_ROOT,
            "tii-life-167": TII_LIFE_167_ROOT,
        }[batch_id]
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = indexed_document["text"].split("【祝壽保險金的申領】")[0]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_investment_life_guaranteed_face_amount_formula(completed_document)
        == schedule
    )
    assert parse_investment_life_guaranteed_face_amount_formula(
        investment_life_document(batch_id, product_id, "F")
    ) is None
    assert parse_investment_life_guaranteed_face_amount_formula(
        {**document, "file_name": f"{product_id}-F.pdf"}
    ) is None

first_investment_life_document = investment_life_document(
    "tii-life-017", "203131MU1A00123A11Z90000042"
)
assert parse_investment_life_guaranteed_face_amount_formula(
    {**first_investment_life_document, "product_id": "203131MU1A00123A11Z90000041"}
) is None
assert parse_investment_life_guaranteed_face_amount_formula(
    {
        **first_investment_life_document,
        "text": first_investment_life_document["text"].replace(
            "按「保險金額」給付身故保險金",
            "按「其他金額」給付身故保險金",
            1,
        ),
    }
) is None

variable_annuity_expected = {
    ("tii-life-012", "202421MU1A65413A11C90000000"): {
        "company_group": "taiwan_life",
        "currency_basis": "twd",
        "death_code": "minimum-death-benefit-before-annuity-start",
    },
    ("tii-life-012", "202421MU1A65513B11C90000000"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "death_code": "minimum-death-benefit-before-annuity-start",
    },
    ("tii-life-012", "202421M31AZP003"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "death_code": "account-value-return-before-annuity-start",
    },
    ("tii-life-012", "202421M31AZS001"): {
        "company_group": "taiwan_life",
        "currency_basis": "foreign_currency",
        "death_code": "account-value-return-before-annuity-start",
    },
    ("tii-life-054", "209421M31A00359"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "death_code": "account-value-return-before-annuity-start",
        "guarantee_period_options_years": [5, 10, 15, 20],
    },
    ("tii-life-054", "209421MV1A00223A11Z90000034"): {
        "company_group": "fubon_life",
        "currency_basis": "twd",
        "death_code": "account-value-return-before-annuity-start",
        "guarantee_period_options_years": [5, 10, 15, 20],
    },
    ("tii-life-168", "264421M31AEVA00"): {
        "company_group": "global_life",
        "currency_basis": "twd",
        "death_code": "account-value-return-before-annuity-start",
        "guarantee_period_options_years": [10],
        "max_annuity_start_age": 80,
        "max_annuity_payment_age": 110,
        "full_account_value": True,
    },
}

for (batch_id, product_id), expected in variable_annuity_expected.items():
    document = variable_annuity_document(batch_id, product_id)
    schedule = parse_variable_annuity_account_value_formula(document)
    assert schedule is not None
    assert schedule["selection_type"] == "account_value"
    assert schedule["input_mode"] == "account_value"
    assert schedule["selection_label"]
    version = schedule["version_characteristics"]
    assert version["product_family"] == (
        "investment-linked-variable-annuity-account-value"
    )
    assert version["company_group"] == expected["company_group"]
    assert version["currency_basis"] == expected["currency_basis"]
    if "guarantee_period_options_years" in expected:
        assert (
            version["guarantee_period_options_years"]
            == expected["guarantee_period_options_years"]
        )
    if "max_annuity_start_age" in expected:
        assert version["max_annuity_start_age"] == expected["max_annuity_start_age"]
    if "max_annuity_payment_age" in expected:
        assert version["max_annuity_payment_age"] == expected["max_annuity_payment_age"]

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert "annuity-payment" in entries
    assert entries["annuity-payment"]["basis"] == "policy_account_value"
    assert (
        entries["annuity-payment"]["calculation_basis"]
        == "account_value_annuity_factor"
    )
    assert entries["annuity-payment"]["unit_key"] == "annuity_amount"
    assert expected["death_code"] in entries
    assert "unpaid-annuity-balance" in entries
    if expected.get("full_account_value"):
        assert "full-account-value-withdrawal-at-annuity-start" in entries

    assert parse_variable_annuity_account_value_formula(
        {**document, "file_name": f"{product_id}-F.pdf"}
    ) is None


kgi_china_legacy_investment_expected = {
    "205141M31A53806": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A53807": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A53810": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A53811": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A53814": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A53815": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
    },
    "205141M31A54006": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A54007": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A54008": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A54009": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A54010": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
    },
    "205141M31A54011": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A54012": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A54013": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A54014": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A54015": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "current_year_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
    },
    "205141M31A54502": {
        "formula": "greater_of_face_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
    },
    "205141M31A54702": {
        "formula": "greater_of_face_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
    },
    "205141M31A54902": {
        "formula": "greater_of_face_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54100": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54101": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": True,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54110": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54200": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "basic_premium_times_face_amount_ratio",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54202": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "basic_premium_times_face_amount_ratio",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54203": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "basic_premium_times_face_amount_ratio",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54204": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "basic_premium_times_face_amount_ratio",
        "valuation_schedule_ref": "附表四",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54402": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54403": {
        "formula": "selectable_type_a_greater_of_basic_amount_or_account_value_times_value_ratio_type_b_greater_of_basic_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54602": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A54802": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55000": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55001": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55002": {
        "formula": "greater_of_basic_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55100": {
        "formula": "greater_of_face_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "foreign_currency",
        "payment_currency_label": "人民幣",
    },
    "205141M31A55200": {
        "formula": "greater_of_face_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55201": {
        "formula": "greater_of_face_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205141M31A55202": {
        "formula": "selectable_type_a_greater_of_basic_amount_or_account_value_times_value_ratio_type_b_greater_of_basic_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00123A11C90000000": {
        "formula": "greater_of_basic_amount_or_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00323A11C90000016": {
        "formula": "face_amount_plus_policy_account_value",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00423A11C90000004": {
        "formula": "selectable_type_a_greater_of_basic_amount_or_account_value_times_value_ratio_type_b_greater_of_basic_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00523A11C90000003": {
        "formula": "greater_of_basic_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00623A11C90000000": {
        "formula": "selectable_type_a_greater_of_basic_amount_or_account_value_times_value_ratio_type_b_greater_of_basic_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A00923A11C90000000": {
        "formula": "greater_of_basic_amount_plus_account_value_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
    "205131MV1A01023A11C90000000": {
        "formula": "greater_of_basic_amount_or_account_value_times_value_ratio",
        "basis": "policy_insurance_amount",
        "valuation_schedule_ref": "附表三",
        "premium_waiver": False,
        "currency_basis": "twd",
        "payment_currency_label": "新台幣",
    },
}
for product_id, expected in kgi_china_legacy_investment_expected.items():
    document = investment_life_document("tii-life-029", product_id)
    schedule = parse_kgi_china_legacy_investment_life_maturity_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "kgi-china-legacy-investment-life-maturity-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "kgi-china-legacy-investment-linked-life-maturity-face-amount"
    )
    assert characteristics["company_group"] == "kgi_china_life"
    assert characteristics["currency_basis"] == expected.get("currency_basis", "twd")
    assert (
        characteristics["payment_currency_label"]
        == expected.get("payment_currency_label", "新台幣")
    )
    assert characteristics["death_total_disability_amount_formula"] == expected["formula"]
    assert characteristics["insurance_amount_basis"] == expected["basis"]
    assert characteristics["valuation_schedule_ref"] == expected["valuation_schedule_ref"]
    assert characteristics["premium_waiver_available"] == expected["premium_waiver"]
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert (
        characteristics["maturity_benefit_formula"]
        == "policy_account_value_at_age_99_policy_anniversary"
    )
    assert characteristics["death_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["minor_death_before_age_15_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is True
    )
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    expected_entries = {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    if expected["premium_waiver"]:
        expected_entries.add("disability-premium-waiver")
        assert entries["disability-premium-waiver"]["calculation_basis"] == "waiver"
    assert set(entries) == expected_entries
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["death-or-funeral-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_path = TII_LIFE_029_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_kgi_china_legacy_investment_life_maturity_face_amount(completed_document)
        == schedule
    )
    assert parse_kgi_china_legacy_investment_life_maturity_face_amount(
        {
            **document,
            "document_type": "product_summary",
            "file_name": f"{product_id}-F.pdf",
        }
    ) is None

first_kgi_china_legacy_investment_document = investment_life_document(
    "tii-life-029", "205141M31A53806"
)
assert parse_kgi_china_legacy_investment_life_maturity_face_amount(
    {**first_kgi_china_legacy_investment_document, "product_id": "205141M31A53805"}
) is None
assert parse_kgi_china_legacy_investment_life_maturity_face_amount(
    {
        **first_kgi_china_legacy_investment_document,
        "text": first_kgi_china_legacy_investment_document["text"].replace(
            "滿期保險金的給付",
            "其他保險金的給付",
            1,
        ),
    }
) is None

taiwan_xinxiangle_product_id = "202131MV1AUFL23A11C90000018"
taiwan_xinxiangle_document = investment_life_document(
    "tii-life-011", taiwan_xinxiangle_product_id
)
taiwan_xinxiangle_schedule = (
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus(
        taiwan_xinxiangle_document
    )
)
assert taiwan_xinxiangle_schedule is not None
taiwan_xinxiangle_integrated = parse_plan_table_with_parser(
    taiwan_xinxiangle_document
)
assert taiwan_xinxiangle_integrated is not None
assert (
    taiwan_xinxiangle_integrated[0]
    == "taiwan-xinxiangle-investment-life-age111-value-bonus-v1"
)
assert taiwan_xinxiangle_integrated[1] == taiwan_xinxiangle_schedule
assert taiwan_xinxiangle_schedule["selection_type"] == "face_amount"
assert taiwan_xinxiangle_schedule["input_mode"] == "face_amount"
assert taiwan_xinxiangle_schedule["selection_label"] == "基本保額"
taiwan_xinxiangle_characteristics = taiwan_xinxiangle_schedule[
    "version_characteristics"
]
assert (
    taiwan_xinxiangle_characteristics["product_family"]
    == "taiwan-xinxiangle-investment-linked-life-age111-value-bonus"
)
assert taiwan_xinxiangle_characteristics["company_group"] == "taiwan_life"
assert taiwan_xinxiangle_characteristics["insurance_type_required"] is True
assert taiwan_xinxiangle_characteristics["insurance_type_options"] == [
    "甲型",
    "乙型",
]
assert (
    taiwan_xinxiangle_characteristics["net_amount_at_risk_formula_type"]
    == "type_a_basic_amount_less_account_value_nonnegative_type_b_basic_amount"
)
assert taiwan_xinxiangle_characteristics["maturity_age"] == 111
assert (
    taiwan_xinxiangle_characteristics["maturity_trigger"]
    == "age_111_policy_anniversary"
)
assert (
    taiwan_xinxiangle_characteristics["maturity_benefit_formula"]
    == "policy_insurance_amount_at_age_111_policy_anniversary"
)
assert (
    taiwan_xinxiangle_characteristics["survival_benefit_formula"]
    == "policy_insurance_amount_at_age_111_policy_anniversary"
)
assert taiwan_xinxiangle_characteristics["policy_value_bonus_available"] is True
assert taiwan_xinxiangle_characteristics["policy_value_bonus_rate_percent"] == 0.5
assert taiwan_xinxiangle_characteristics["policy_value_bonus_frequency_years"] == 3
assert (
    taiwan_xinxiangle_characteristics["minor_death_before_age_15_account_value_rule"]
    is True
)
assert (
    taiwan_xinxiangle_characteristics[
        "minor_disability_before_age_15_account_value_rule"
    ]
    is True
)
assert (
    taiwan_xinxiangle_characteristics["complete_disability_schedule_ref"]
    == "附表五"
)
taiwan_xinxiangle_entries = {
    entry["id"]: entry for entry in taiwan_xinxiangle_schedule["coverage_entries"]
}
assert set(taiwan_xinxiangle_entries) == {
    "survival-benefit",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "policy-value-bonus",
}
assert taiwan_xinxiangle_entries["survival-benefit"]["rate_percent"] == 100
assert (
    taiwan_xinxiangle_entries["survival-benefit"]["unit_key"]
    == "policy_insurance_amount"
)
assert taiwan_xinxiangle_entries["policy-value-bonus"]["rate_percent"] == 0.5
assert (
    taiwan_xinxiangle_entries["policy-value-bonus"]["unit_key"]
    == "average_daily_policy_account_value"
)
taiwan_xinxiangle_source_path = (
    TII_LIFE_011_ROOT
    / taiwan_xinxiangle_product_id
    / f"{taiwan_xinxiangle_product_id}-A.pdf"
)
taiwan_xinxiangle_indexed_document = {
    key: value
    for key, value in taiwan_xinxiangle_document.items()
    if key not in {"page_count", "pages_parsed"}
}
taiwan_xinxiangle_indexed_document["text"] = ""
taiwan_xinxiangle_completed_document = complete_strict_source_document(
    taiwan_xinxiangle_indexed_document, taiwan_xinxiangle_source_path
)
assert (
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus(
        taiwan_xinxiangle_completed_document
    )
    == taiwan_xinxiangle_schedule
)
assert (
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus(
        investment_life_document("tii-life-011", taiwan_xinxiangle_product_id, "F")
    )
    is None
)
assert (
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus(
        {**taiwan_xinxiangle_document, "product_id": "202131MV1AUFL23A11C90000017"}
    )
    is None
)
assert (
    parse_taiwan_xinxiangle_investment_life_age111_value_bonus(
        {
            **taiwan_xinxiangle_document,
            "text": taiwan_xinxiangle_document["text"].replace(
                "每日保單帳戶價值之平均值的千分之五",
                "每日保單帳戶價值之平均值",
                1,
            ),
        }
    )
    is None
)

taiwan_age111_variable_universal_expected = {
    "202131MV1A34923B11C90000009": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "terms_revision": "第9次部分變更",
        "insurance_type_options": ["甲型", "乙型", "丙型", "丁型"],
        "entry_count": 3,
        "policy_value_bonus_available": False,
    },
    "202131MV1A38223A11C90000006": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "第6次部分變更",
        "insurance_type_options": ["甲型", "乙型", "丙型", "丁型"],
        "entry_count": 4,
        "policy_value_bonus_available": True,
        "policy_value_bonus_type": "fixed_rate",
        "policy_value_bonus_rate_percent": 0.2,
    },
    "202131MV1A38623A11C90000006": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "第6次部分變更",
        "insurance_type_options": ["甲型", "乙型", "丙型", "丁型"],
        "entry_count": 4,
        "policy_value_bonus_available": True,
        "policy_value_bonus_type": "appendix_five_schedule",
        "policy_value_bonus_schedule_len": 6,
    },
    "202131MV1A62923J11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "人民幣",
        "terms_revision": "原始版本",
        "insurance_type_options": ["甲型", "乙型", "丙型", "丁型"],
        "entry_count": 3,
        "policy_value_bonus_available": False,
    },
    "202131MV1A66823Z11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "約定外幣",
        "terms_revision": "原始版本",
        "insurance_type_options": ["甲型", "乙型"],
        "entry_count": 3,
        "policy_value_bonus_available": False,
    },
}
for product_id, expected in taiwan_age111_variable_universal_expected.items():
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_age111_variable_universal_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-age111-variable-universal-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "taiwan-age111-variable-universal-life"
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert characteristics["payment_currency_label"] == expected["payment_currency_label"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["variable_universal_life_policy"] is True
    assert (
        characteristics["foreign_currency_policy"]
        is (expected["currency_basis"] == "foreign_currency")
    )
    assert characteristics["insurance_type_required"] is True
    assert (
        characteristics["insurance_type_options"]
        == expected["insurance_type_options"]
    )
    assert (
        characteristics["insurance_amount_formula"]
        == "net_amount_at_risk_plus_policy_account_value"
    )
    assert (
        characteristics["death_total_disability_amount_formula"]
        == "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["net_amount_at_risk_required"] is True
    assert characteristics["insurance_deduction_amount_required"] is True
    assert characteristics["maturity_age"] == 111
    assert characteristics["maturity_trigger"] == "age_111_policy_anniversary"
    assert characteristics["valuation_schedule_ref"] == "附表四"
    assert characteristics["complete_disability_schedule_ref"] == "附表一"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert (
        characteristics["minor_death_before_age_15_account_value_rule"]
        is True
    )
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is True
    )
    assert characteristics["policy_value_bonus_available"] is expected[
        "policy_value_bonus_available"
    ]
    if expected["policy_value_bonus_available"]:
        assert (
            characteristics["policy_value_bonus_type"]
            == expected["policy_value_bonus_type"]
        )
        if "policy_value_bonus_rate_percent" in expected:
            assert (
                characteristics["policy_value_bonus_rate_percent"]
                == expected["policy_value_bonus_rate_percent"]
            )
        if "policy_value_bonus_schedule_len" in expected:
            assert len(characteristics["policy_value_bonus_schedule"]) == expected[
                "policy_value_bonus_schedule_len"
            ]
    else:
        assert "policy_value_bonus_type" not in characteristics
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    expected_entries = {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    if expected["policy_value_bonus_available"]:
        expected_entries.add("policy-value-bonus")
    assert set(entries) == expected_entries
    assert len(entries) == expected["entry_count"]
    assert entries["maturity-benefit"]["unit_key"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert entries["death-or-funeral-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["unit_key"] == "policy_insurance_amount"
    if "policy-value-bonus" in entries:
        assert (
            entries["policy-value-bonus"]["unit_key"]
            == "average_daily_policy_account_value"
        )

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value for key, value in document.items() if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_taiwan_age111_variable_universal_life(completed_document) == schedule
    assert (
        parse_taiwan_age111_variable_universal_life(
            investment_life_document("tii-life-011", product_id, "F")
        )
        is None
    )
    assert (
        parse_taiwan_age111_variable_universal_life(
            {**document, "product_id": "wrong-product"}
        )
        is None
    )

first_taiwan_age111_variable_universal_document = investment_life_document(
    "tii-life-011", "202131MV1A34923B11C90000009"
)
assert (
    parse_taiwan_age111_variable_universal_life(
        {
            **first_taiwan_age111_variable_universal_document,
            "text": first_taiwan_age111_variable_universal_document["text"].replace(
                "主要給付項目",
                "主要項目",
            ),
        }
    )
    is None
)

taiwan_xinfumanzai_usd_variable_life_ids = [
    "202131MV1A96022B11Z90000000",
    "202131MV1A96022B11Z90000001",
    "202131MV1A96022B11Z90000002",
    "202131MV1A96022B11Z90000003",
]
for product_id in taiwan_xinfumanzai_usd_variable_life_ids:
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_xinfumanzai_usd_variable_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-xinfumanzai-usd-variable-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "taiwan-xinfumanzai-usd-variable-life"
    )
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == "foreign_currency"
    assert characteristics["payment_currency_label"] == "美元"
    assert (
        characteristics["terms_revision"]
        == TAIWAN_XINFUMANZAI_USD_VARIABLE_LIFE_REVISIONS[product_id][
            "terms_revision"
        ]
    )
    assert (
        characteristics["filing_number"]
        == TAIWAN_XINFUMANZAI_USD_VARIABLE_LIFE_REVISIONS[product_id][
            "filing_number"
        ]
    )
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["variable_life_policy"] is True
    assert characteristics["single_premium_policy"] is True
    assert characteristics["foreign_currency_policy"] is True
    assert (
        characteristics["insurance_amount_formula"]
        == "basic_amount_plus_policy_account_value"
    )
    assert (
        characteristics["death_total_disability_amount_formula"]
        == "basic_amount_plus_policy_account_value"
    )
    assert characteristics["net_amount_at_risk_required"] is True
    assert characteristics["net_amount_at_risk_formula_type"] == "basic_amount"
    assert characteristics["basic_amount_required"] is True
    assert (
        characteristics["maturity_trigger"]
        == "investment_target_operation_period_maturity"
    )
    assert (
        characteristics["maturity_benefit_formula"]
        == "appendix_six_investment_target_maturity_formula"
    )
    assert characteristics["maturity_interest_crediting"] is True
    assert (
        characteristics["maturity_interest_rate_source"]
        == "specified_bank_usd_demand_deposit_rate_daily_simple_interest"
    )
    assert (
        characteristics["maturity_reduced_by_partial_withdrawal_or_policy_loan_offset"]
        is True
    )
    assert characteristics["reinstatement_excludes_maturity_benefit"] is True
    assert characteristics["valuation_schedule_ref"] == "附表四"
    assert characteristics["linked_investment_appendix"] == "附表六之一"
    assert characteristics["linked_investment_type"] == "international_bond"
    assert characteristics["unlinked_investment_appendices"] == [
        "附表六之二",
        "附表六之三",
    ]
    assert characteristics["account_value_return_on_time_bar"] is True
    assert characteristics["guardianship_funeral_benefit_rule"] is True
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["complete_disability_schedule_ref"] == "附表一"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["disability_term"] == "失能"
    assert characteristics["total_disability_term"] == "完全失能"
    assert characteristics["non_participating_policy"] is True
    assert characteristics["policy_dividend_available"] is False

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == (
        "investment_target_maturity_formula"
    )
    assert entries["death-or-funeral-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value for key, value in document.items() if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_taiwan_xinfumanzai_usd_variable_life(completed_document) == schedule
    assert (
        parse_taiwan_xinfumanzai_usd_variable_life(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_taiwan_xinfumanzai_usd_variable_life(
            {**document, "file_name": f"{product_id}-B.pdf"}
        )
        is None
    )

first_taiwan_xinfumanzai_usd_variable_life_document = investment_life_document(
    "tii-life-011", "202131MV1A96022B11Z90000000"
)
assert "美元計價" in first_taiwan_xinfumanzai_usd_variable_life_document["text"]
assert (
    parse_taiwan_xinfumanzai_usd_variable_life(
        {
            **first_taiwan_xinfumanzai_usd_variable_life_document,
            "text": first_taiwan_xinfumanzai_usd_variable_life_document[
                "text"
            ].replace("美元計價", ""),
        }
    )
    is None
)

taiwan_xinfu_life_maturity_guarantee_expected = {
    "202131MV1A59422A11Z90000001": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "107-09-14-regulatory-revision",
        "filing_number": "台壽字第1062330001號",
        "foreign_currency_policy": False,
    },
    "202131MV1A59422A11Z90000002": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "108-04-24-filing-revision",
        "filing_number": "台壽字第1062330001號",
        "foreign_currency_policy": False,
    },
    "202131MV1A59422A11Z90000003": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "108-07-05-filing-revision",
        "filing_number": "台壽字第1062330001號",
        "foreign_currency_policy": False,
    },
    "202131MV1A59422A11Z90000004": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "terms_revision": "109-01-01-filing-revision",
        "filing_number": "台壽字第1062330001號",
        "foreign_currency_policy": False,
    },
    "202131MV1A59522B11Z90000001": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "terms_revision": "107-09-14-regulatory-revision",
        "filing_number": "台壽字第1062330002號",
        "foreign_currency_policy": True,
    },
    "202131MV1A59522B11Z90000002": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "terms_revision": "108-04-24-filing-revision",
        "filing_number": "台壽字第1062330002號",
        "foreign_currency_policy": True,
    },
    "202131MV1A59522B11Z90000003": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "terms_revision": "108-07-05-filing-revision",
        "filing_number": "台壽字第1062330002號",
        "foreign_currency_policy": True,
    },
    "202131MV1A59522B11Z90000004": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "terms_revision": "109-01-01-regulatory-revision",
        "filing_number": "台壽字第1062330002號",
        "foreign_currency_policy": True,
    },
}
for product_id, expected in taiwan_xinfu_life_maturity_guarantee_expected.items():
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_xinfu_life_maturity_guarantee(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-xinfu-life-maturity-guarantee-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "taiwan-xinfu-life-investment-linked-life-maturity-guarantee"
    )
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert (
        characteristics["payment_currency_label"]
        == expected["payment_currency_label"]
    )
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["filing_number"] == expected["filing_number"]
    assert (
        characteristics["foreign_currency_policy"]
        is expected["foreign_currency_policy"]
    )
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["single_premium_policy"] is True
    assert characteristics["insurance_amount_basis"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["insurance_amount_formula"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["net_amount_at_risk_required"] is True
    assert characteristics["net_amount_at_risk_formula_type"] == "basic_amount"
    assert characteristics["death_benefit_formula"] == "policy_insurance_amount"
    assert (
        characteristics["total_disability_benefit_formula"]
        == "policy_insurance_amount"
    )
    assert (
        characteristics["maturity_trigger"]
        == "investment_target_operation_period_end"
    )
    assert characteristics["maturity_benefit_formula"] == (
        "investment_target_formula_amount_or_policy_account_value_after_reinstatement"
    )
    assert (
        characteristics["maturity_guaranteed_amount_formula_ref"]
        == "附表六之一"
    )
    assert characteristics["maturity_income_amount_formula_ref"] == "附表六之二"
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["investment_target_value_required"] is True
    assert characteristics["valuation_schedule_ref"] == "附表四"
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert (
        characteristics["minor_death_before_age_15_account_value_rule"]
        is False
    )
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is False
    )
    assert characteristics["complete_disability_schedule_ref"] == "附表一"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["legacy_disability_wording"] is False
    assert characteristics["disability_term"] == "失能"
    assert characteristics["total_disability_term"] == "完全失能"
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-guaranteed-amount",
        "maturity-income-amount",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert (
        entries["maturity-guaranteed-amount"]["unit_key"]
        == "appendix_6_1_formula_amount"
    )
    assert (
        entries["maturity-income-amount"]["unit_key"]
        == "appendix_6_2_formula_amount"
    )
    assert (
        entries["death-or-funeral-benefit"]["unit_key"]
        == "policy_insurance_amount"
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert "完全殘廢" not in " ".join(entry["name"] for entry in entries.values())

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_taiwan_xinfu_life_maturity_guarantee(completed_document) == schedule
    assert (
        parse_taiwan_xinfu_life_maturity_guarantee(
            investment_life_document("tii-life-011", product_id, "F")
        )
        is None
    )

first_taiwan_xinfu_life_document = investment_life_document(
    "tii-life-011", "202131MV1A59422A11Z90000001"
)
assert (
    parse_taiwan_xinfu_life_maturity_guarantee(
        {**first_taiwan_xinfu_life_document, "product_id": "202131MV1A59422A11Z90000000"}
    )
    is None
)
assert (
    parse_taiwan_xinfu_life_maturity_guarantee(
        {
            **first_taiwan_xinfu_life_document,
            "text": first_taiwan_xinfu_life_document["text"].replace(
                "滿期保證金額計算公式",
                "滿期保證金額",
                1,
            ),
        }
    )
    is None
)

taiwan_wudong_legacy_variable_universal_life_expected = {
    "202191M31AZE002": "第2次部分變更",
    "202191M31AZE003": "第3次部分變更",
    "202191M31AZE004": "96-12-31-filing-revision",
    "202191M31AZE005": "97-03-20-filing-revision",
    "202191M31AZE006": "第6次部分變更",
    "202191M31AZE007": "97-08-26-regulatory-revision",
    "202191M31AZE008": "第8次部分變更",
    "202191M31AZE009": "97-12-08-filing-revision",
    "202191M31AZE010": "97-12-26-filing-revision",
    "202191M31AZE011": "98-07-20-filing-revision",
    "202191M31AZE012": "第12次部分變更",
    "202191M31AZE014": "98-12-15-filing-revision",
    "202191M31AZE015": "第15次部分變更",
}
for (
    product_id,
    terms_revision,
) in taiwan_wudong_legacy_variable_universal_life_expected.items():
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_wudong_legacy_variable_universal_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-wudong-legacy-variable-universal-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "taiwan-wudong-legacy-variable-universal-life"
    )
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新台幣"
    assert characteristics["terms_revision"] == terms_revision
    assert characteristics["filing_number"] == "96台壽投商字第00064號"
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["variable_universal_life_policy"] is True
    assert characteristics["insurance_type_required"] is True
    assert characteristics["insurance_type_options"] == ["甲型", "乙型"]
    assert (
        characteristics["insurance_amount_basis"]
        == "death_total_disability_insurance_amount"
    )
    assert (
        characteristics["death_total_disability_amount_formula"]
        == "contract_selected_formula_by_type_a_or_b"
    )
    assert characteristics["net_amount_at_risk_required"] is True
    assert characteristics["net_amount_at_risk_formula_type"] == (
        "death_total_disability_amount_less_account_value"
    )
    assert (
        characteristics["terminal_illness_benefit_formula"]
        == "50_percent_of_death_total_disability_insurance_amount"
    )
    assert characteristics["terminal_illness_rate_percent"] == 50
    assert characteristics["terminal_illness_survival_months_max"] == 6
    assert (
        characteristics["terminal_illness_type_b_policy_value_multiplier_condition"]
        is True
    )
    assert (
        characteristics["maturity_benefit_formula"]
        == "policy_account_value_at_age_110_policy_anniversary"
    )
    assert characteristics["maturity_trigger"] == "age_110_policy_anniversary"
    assert characteristics["maturity_age"] == 110
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["valuation_reference"] == (
        "appendix_1_investment_target_unit_value_date"
    )
    assert characteristics["account_value_return_on_time_bar"] is True
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["minor_death_before_age_14_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_14_account_value_rule"]
        is False
    )
    assert characteristics["complete_disability_schedule_ref"] == "附件五"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    assert characteristics["policy_dividend_available"] is False
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "survival-benefit",
        "death-benefit",
        "funeral-benefit",
        "total-disability-benefit",
        "terminal-illness-benefit",
    }
    assert entries["survival-benefit"]["unit_key"] == "policy_account_value"
    assert entries["survival-benefit"]["rate_percent"] == 100
    assert (
        entries["death-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert entries["funeral-benefit"]["unit_key"] == "net_amount_at_risk"
    assert entries["funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["total-disability-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert (
        entries["terminal-illness-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["terminal-illness-benefit"]["rate_percent"] == 50

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_taiwan_wudong_legacy_variable_universal_life(completed_document)
        == schedule
    )
    assert (
        parse_taiwan_wudong_legacy_variable_universal_life(
            investment_life_document("tii-life-011", product_id, "F")
        )
        is None
    )

first_taiwan_wudong_document = investment_life_document(
    "tii-life-011", "202191M31AZE004"
)
assert (
    parse_taiwan_wudong_legacy_variable_universal_life(
        {**first_taiwan_wudong_document, "product_id": "202191M31AZE003"}
    )
    is None
)
assert (
    parse_taiwan_wudong_legacy_variable_universal_life(
        {
            **first_taiwan_wudong_document,
            "text": first_taiwan_wudong_document["text"].replace(
                "百分之五十給付生命末期保險金",
                "給付生命末期保險金",
                1,
            ),
        }
    )
    is None
)

taiwan_xindeyi_variable_universal_life_expected = {
    "202191M31AZG002": "第2次部分變更",
    "202191M31AZG003": "第3次部分變更",
    "202191M31AZG004": "第4次部分變更",
    "202191M31AZG005": "第5次部分變更",
    "202191M31AZG006": "第6次部分變更",
    "202191M31AZG007": "第7次部分變更",
    "202191M31AZG008": "第8次部分變更",
    "202191M31AZG009": "第9次部分變更",
    "202191M31AZG010": "第10次部分變更",
    "202191M31AZG011": "第11次部分變更",
    "202191M31AZG012": "第12次部分變更",
    "202191M31AZG013": "第13次部分變更",
    "202191M31AZG014": "第14次部分變更",
    "202191M31AZG015": "第15次部分變更",
    "202191M31AZG016": "第16次部分變更",
    "202191M31AZG017": "第17次部分變更",
    "202191M31AZG018": "第18次部分變更",
    "202191M31AZG019": "第19次部分變更",
    "202191M31AZG020": "第20次部分變更",
    "202191M31AZG021": "第21次部分變更",
    "202191M31AZG022": "第22次部分變更",
    "202191M31AZG023": "第23次部分變更",
}
for (
    product_id,
    terms_revision,
) in taiwan_xindeyi_variable_universal_life_expected.items():
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_xindeyi_variable_universal_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-xindeyi-variable-universal-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "taiwan-xindeyi-variable-universal-life"
    )
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新台幣"
    assert characteristics["terms_revision"] == terms_revision
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["insurance_amount_basis"] == "policy_face_amount"
    assert (
        characteristics["death_total_disability_amount_formula"]
        == "face_amount_plus_policy_account_value"
    )
    assert (
        characteristics["death_benefit_formula"]
        == "death_total_disability_insurance_amount"
    )
    assert characteristics["funeral_benefit_formula"] == (
        "policy_face_amount_subject_to_statutory_cap_plus_account_value_return"
    )
    assert (
        characteristics["total_disability_benefit_formula"]
        == "death_total_disability_insurance_amount"
    )
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_age_99_policy_anniversary"
    )
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["face_amount_required"] is True
    assert characteristics["valuation_schedule_ref"] == "附件四"
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["minor_death_before_age_14_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_14_account_value_rule"]
        is False
    )
    assert characteristics["complete_disability_schedule_ref"] == "附件五"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["total_disability_term"] == "完全殘廢"
    assert characteristics["policy_dividend_available"] is False
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert entries["funeral-benefit"]["unit_key"] == "policy_face_amount"
    assert entries["funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["total-disability-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_taiwan_xindeyi_variable_universal_life(completed_document) == schedule
    assert (
        parse_taiwan_xindeyi_variable_universal_life(
            investment_life_document("tii-life-011", product_id, "F")
        )
        is None
    )

first_taiwan_xindeyi_document = investment_life_document(
    "tii-life-011", "202191M31AZG002"
)
assert (
    parse_taiwan_xindeyi_variable_universal_life(
        {**first_taiwan_xindeyi_document, "product_id": "202191M31AZG001"}
    )
    is None
)
assert (
    parse_taiwan_xindeyi_variable_universal_life(
        {
            **first_taiwan_xindeyi_document,
            "text": first_taiwan_xindeyi_document["text"].replace(
                "保險金額與保單帳戶價值兩者之總和",
                "保險金額",
                1,
            ),
        }
    )
    is None
)

taiwan_zhiduoxin_variable_universal_life_expected = {
    "202191M31AZQ000": (
        "原始版本",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ001": (
        "第1次部分變更",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ002": (
        "第2次部分變更",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ003": (
        "第3次部分變更",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ004": (
        "第4次部分變更",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ005": (
        "第5次部分變更",
        "face_amount_plus_policy_account_value",
        "全殘廢",
    ),
    "202191M31AZQ006": (
        "第6次部分變更",
        "net_amount_at_risk_plus_policy_account_value",
        "完全殘廢",
    ),
    "202191MV1AZQ023A11C90000007": (
        "第7次部分變更",
        "net_amount_at_risk_plus_policy_account_value",
        "完全殘廢",
    ),
    "202191MV1AZQ023A11C90000008": (
        "第8次部分變更",
        "net_amount_at_risk_plus_policy_account_value",
        "完全殘廢",
    ),
}
for (
    product_id,
    (
        terms_revision,
        death_total_disability_amount_formula,
        total_disability_term,
    ),
) in taiwan_zhiduoxin_variable_universal_life_expected.items():
    document = investment_life_document("tii-life-011", product_id)
    schedule = parse_taiwan_zhiduoxin_variable_universal_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-zhiduoxin-variable-universal-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "taiwan-zhiduoxin-variable-universal-life"
    )
    assert characteristics["company_group"] == "taiwan_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新台幣"
    assert characteristics["terms_revision"] == terms_revision
    assert (
        characteristics["death_total_disability_amount_formula"]
        == death_total_disability_amount_formula
    )
    assert characteristics["death_benefit_formula"] == (
        "death_total_disability_insurance_amount_after_age_15"
    )
    assert characteristics["minor_death_account_value_return_formula"] == (
        "policy_account_value_before_age_15"
    )
    assert characteristics["death_benefit_effective_age"] == 15
    assert characteristics["minor_death_before_age_15_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is False
    )
    assert characteristics["mental_disability_funeral_benefit_rule"] is True
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert characteristics["valuation_schedule_ref"] == "附件四"
    assert characteristics["complete_disability_schedule_ref"] == "附件五"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["total_disability_term"] == total_disability_term
    assert characteristics["policy_dividend_available"] is False
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "minor-death-account-value-return",
        "funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert (
        entries["minor-death-account-value-return"]["unit_key"]
        == "policy_account_value"
    )
    assert entries["funeral-benefit"]["unit_key"] == "policy_face_amount"
    assert entries["funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["total-disability-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_path = TII_LIFE_011_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_taiwan_zhiduoxin_variable_universal_life(completed_document) == schedule
    assert (
        parse_taiwan_zhiduoxin_variable_universal_life(
            investment_life_document("tii-life-011", product_id, "F")
        )
        is None
    )

first_taiwan_zhiduoxin_document = investment_life_document(
    "tii-life-011", "202191M31AZQ000"
)
assert (
    parse_taiwan_zhiduoxin_variable_universal_life(
        {**first_taiwan_zhiduoxin_document, "product_id": "202191M31AZQ006"}
    )
    is None
)
assert (
    parse_taiwan_zhiduoxin_variable_universal_life(
        {
            **first_taiwan_zhiduoxin_document,
            "text": first_taiwan_zhiduoxin_document["text"].replace(
                "滿十五足歲之日起發生效力",
                "滿十五足歲",
                1,
            ),
        }
    )
    is None
)

global_ritai_financial_expert_product_ids = [
    "262141M31A00200",
    "262141M31A00201",
    "262141M31A00202",
    "262141M31A00203",
    "262141M31A00204",
    "262141M31A00205",
    "262141M31A00206",
    "262141M31A00207",
    "262141M31A00208",
    "262141M31A00209",
    "262141M31A00210",
    "262141M31A00211",
]
global_ritai_formula = (
    "selectable_type_a_greater_of_face_amount_or_policy_account_value_"
    "type_b_face_amount_plus_policy_account_value"
)
for product_id in global_ritai_financial_expert_product_ids:
    document = investment_life_document("tii-life-161", product_id)
    schedule = parse_global_ritai_financial_expert_variable_universal_life(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "global-ritai-financial-expert-variable-universal-life-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "global-ritai-financial-expert-variable-universal-life"
    )
    assert characteristics["company_group"] == "global_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新台幣"
    assert characteristics["insurance_type_required"] is True
    assert characteristics["insurance_type_options"] == ["A型", "B型"]
    assert characteristics["insurance_amount_basis"] == "policy_face_amount"
    assert (
        characteristics["death_total_disability_amount_formula"]
        == global_ritai_formula
    )
    assert characteristics["death_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["maturity_trigger"] == "age_100_policy_anniversary"
    assert characteristics["maturity_age"] == 100
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_age_100_policy_anniversary"
    )
    assert characteristics["risk_amount_required"] is True
    assert characteristics["risk_amount_formula_type"] == (
        "type_a_face_amount_less_account_value_nonnegative_type_b_face_amount"
    )
    assert characteristics["complete_disability_schedule_ref"] == "附表二"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert (
        entries["total-disability-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_file_name = (
        "262141M31A002-A.pdf"
        if product_id == "262141M31A00200"
        else f"{product_id}-A.pdf"
    )
    source_path = TII_LIFE_161_ROOT / product_id / source_file_name
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_global_ritai_financial_expert_variable_universal_life(
            completed_document
        )
        == schedule
    )
    assert (
        parse_global_ritai_financial_expert_variable_universal_life(
            investment_life_document("tii-life-161", product_id, "F")
        )
        is None
    )

first_global_ritai_document = investment_life_document(
    "tii-life-161", "262141M31A00200"
)
assert (
    parse_global_ritai_financial_expert_variable_universal_life(
        {**first_global_ritai_document, "product_id": "262141M31A00212"}
    )
    is None
)
assert (
    parse_global_ritai_financial_expert_variable_universal_life(
        {
            **first_global_ritai_document,
            "file_name": "262141M31A00200-A.pdf",
        }
    )
    is None
)
assert (
    parse_global_ritai_financial_expert_variable_universal_life(
        {
            **first_global_ritai_document,
            "text": first_global_ritai_document["text"].replace(
                "年齡達一百歲之保單週年日仍生存",
                "年齡達一百歲之保單週年日",
                1,
            ),
        }
    )
    is None
)

global_ritai_financial_head_product_ids = [
    "262141M31A00300",
    "262141M31A00301",
    "262141M31A00302",
    "262141M31A00303",
    "262141M31A00304",
    "262141M31A00305",
]
for product_id in global_ritai_financial_head_product_ids:
    document = investment_life_document("tii-life-161", product_id)
    schedule = parse_global_ritai_financial_head_variable_universal_life(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "global-ritai-financial-head-variable-universal-life-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "global-ritai-financial-head-variable-universal-life"
    )
    assert characteristics["company_group"] == "global_life"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["insurance_type_required"] is True
    assert characteristics["insurance_type_options"] == ["A型", "B型"]
    assert characteristics["insurance_amount_basis"] == "policy_face_amount"
    assert (
        characteristics["death_total_disability_amount_formula"]
        == global_ritai_formula
    )
    assert characteristics["maturity_trigger"] == "age_100_policy_anniversary"
    assert characteristics["maturity_age"] == 100
    assert characteristics["risk_amount_required"] is True
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["minor_death_before_age_14_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_14_account_value_rule"]
        is False
    )
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert (
        entries["total-disability-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["total-disability-benefit"]["rate_percent"] == 100

    source_file_name = (
        "262141M31A003-A.pdf"
        if product_id == "262141M31A00300"
        else f"{product_id}-A.pdf"
    )
    source_path = TII_LIFE_161_ROOT / product_id / source_file_name
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_global_ritai_financial_head_variable_universal_life(
            completed_document
        )
        == schedule
    )
    assert (
        parse_global_ritai_financial_head_variable_universal_life(
            investment_life_document("tii-life-161", product_id, "F")
        )
        is None
    )

first_global_ritai_head_document = investment_life_document(
    "tii-life-161", "262141M31A00300"
)
assert (
    parse_global_ritai_financial_head_variable_universal_life(
        {**first_global_ritai_head_document, "product_id": "262141M31A00306"}
    )
    is None
)
assert (
    parse_global_ritai_financial_head_variable_universal_life(
        {
            **first_global_ritai_head_document,
            "file_name": "262141M31A00300-A.pdf",
        }
    )
    is None
)

prudential_shared_generations_expected = {
    "203131MV1A01123A11C90000000": "附表四",
    "203131MV1A01123A11C90000001": "附表四",
    "203131MV1A01123A11C90000002": "附表五",
}
for (
    product_id,
    complete_disability_schedule_ref,
) in prudential_shared_generations_expected.items():
    document = investment_life_document("tii-life-017", product_id)
    schedule = parse_prudential_shared_generations_variable_universal_life(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "prudential-shared-generations-variable-universal-life-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "prudential-shared-generations-variable-universal-life"
    )
    assert characteristics["company_group"] == "prudential"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新臺幣"
    assert (
        characteristics["terms_revision"]
        == PRUDENTIAL_SHARED_GENERATIONS_VARIABLE_UNIVERSAL_LIFE_REVISIONS[
            product_id
        ]["terms_revision"]
    )
    assert (
        characteristics["filing_number"]
        == PRUDENTIAL_SHARED_GENERATIONS_VARIABLE_UNIVERSAL_LIFE_REVISIONS[
            product_id
        ]["filing_number"]
    )
    assert characteristics["investment_linked_policy"] is True
    assert characteristics["variable_universal_life_policy"] is True
    assert characteristics["dual_insured_policy"] is True
    assert characteristics["primary_insured_role"] == "child"
    assert characteristics["secondary_insured_role"] == "parent"
    assert characteristics["insured_relationship_required"] == "parent_child"
    assert characteristics["basic_amount_same_for_both_insured"] is True
    assert characteristics["basic_amount_max_target_premium_multiple"] == 10
    assert characteristics["primary_basic_amount_effective_age"] == 25
    assert characteristics["secondary_coverage_before_primary_age"] == 25
    assert characteristics["target_premium_single_payment"] is True
    assert characteristics["excess_premium_allowed"] is True
    assert characteristics["insurance_amount_basis"] == (
        "dual_insured_age_25_tiered_formula"
    )
    assert characteristics["insurance_amount_formula"] == (
        "basic_amount_plus_policy_account_value_after_primary_age_25"
    )
    assert characteristics["net_amount_at_risk_required"] is True
    assert characteristics["net_amount_at_risk_formula_type"] == "basic_amount"
    assert (
        characteristics["primary_death_before_age_25_formula"]
        == "policy_account_value_return"
    )
    assert (
        characteristics["primary_death_after_age_25_formula"]
        == "basic_amount_plus_policy_account_value"
    )
    assert (
        characteristics["secondary_death_before_primary_age_25_formula"]
        == "basic_amount"
    )
    assert (
        characteristics["primary_total_disability_before_age_25_formula"]
        == "policy_account_value_return"
    )
    assert (
        characteristics["primary_total_disability_after_age_25_formula"]
        == "basic_amount_plus_policy_account_value"
    )
    assert (
        characteristics["secondary_total_disability_before_primary_age_25_formula"]
        == "basic_amount"
    )
    assert characteristics["maturity_trigger"] == (
        "primary_insured_age_99_policy_anniversary"
    )
    assert characteristics["maturity_age"] == 99
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_primary_insured_age_99_policy_anniversary"
    )
    assert characteristics["maturity_interest_crediting"] is False
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["investment_target_value_required"] is True
    assert characteristics["redemption_valuation_timing_required"] is True
    assert characteristics["valuation_reference"] == "redemption_valuation_timing"
    assert characteristics["insurance_cost_refund_after_event"] is True
    assert characteristics["account_value_return_on_time_bar"] is True
    assert characteristics["mental_disability_funeral_benefit_rule"] is True
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert (
        characteristics["complete_disability_schedule_ref"]
        == complete_disability_schedule_ref
    )
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    assert characteristics["non_participating_policy"] is True
    assert characteristics["policy_dividend_available"] is False
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "survival-benefit",
        "primary-death-before-age-25-account-value-return",
        "primary-death-after-age-25-benefit",
        "secondary-death-before-primary-age-25-benefit",
        "funeral-benefit",
        "primary-total-disability-before-age-25-account-value-return",
        "primary-total-disability-after-age-25-benefit",
        "secondary-total-disability-before-primary-age-25-benefit",
    }
    assert entries["survival-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["primary-death-before-age-25-account-value-return"]["unit_key"]
        == "policy_account_value"
    )
    assert entries["primary-death-after-age-25-benefit"]["unit_key"] == (
        "basic_amount_plus_policy_account_value"
    )
    assert entries["primary-death-after-age-25-benefit"]["rate_percent"] == 100
    assert entries["secondary-death-before-primary-age-25-benefit"][
        "unit_key"
    ] == "basic_amount"
    assert (
        entries["funeral-benefit"]["unit_key"]
        == "statutory_funeral_cap_plus_account_value_return"
    )
    assert (
        entries[
            "primary-total-disability-before-age-25-account-value-return"
        ]["unit_key"]
        == "policy_account_value"
    )
    assert entries["primary-total-disability-after-age-25-benefit"][
        "unit_key"
    ] == "basic_amount_plus_policy_account_value"
    assert (
        entries["secondary-total-disability-before-primary-age-25-benefit"][
            "unit_key"
        ]
        == "basic_amount"
    )

    source_path = TII_LIFE_017_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_prudential_shared_generations_variable_universal_life(
            completed_document
        )
        == schedule
    )
    assert (
        parse_prudential_shared_generations_variable_universal_life(
            investment_life_document("tii-life-017", product_id, "F")
        )
        is None
    )

first_prudential_shared_generations_document = investment_life_document(
    "tii-life-017", "203131MV1A01123A11C90000000"
)
assert (
    parse_prudential_shared_generations_variable_universal_life(
        {**first_prudential_shared_generations_document, "product_id": "wrong"}
    )
    is None
)
assert (
    parse_prudential_shared_generations_variable_universal_life(
        {
            **first_prudential_shared_generations_document,
            "text": first_prudential_shared_generations_document[
                "text"
            ].replace("分為主被保險人及次被保險人", ""),
        }
    )
    is None
)

prudential_chuangfu_expected = {
    "203141M31A01200": "原始版本",
    "203141M31A01201": "第1次部份變更",
    "203141M31A01202": "第2次部份變更",
    "203141M31A01203": "第3次部份變更",
    "203141M31A01204": "第4次部份變更",
    "203141M31A01205": "第5次部份變更",
}
for product_id, terms_revision in prudential_chuangfu_expected.items():
    document = investment_life_document("tii-life-017", product_id)
    schedule = parse_prudential_chuangfu_variable_life(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-chuangfu-variable-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "prudential-chuangfu-variable-life"
    assert characteristics["company_group"] == "prudential"
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == "新臺幣"
    assert characteristics["terms_revision"] == terms_revision
    assert characteristics["insurance_amount_basis"] == (
        "accumulated_premium_balance_times_coverage_premium_ratio"
    )
    assert characteristics["insurance_amount_formula"] == (
        "accumulated_premium_balance_times_coverage_premium_ratio"
    )
    assert characteristics["death_total_disability_amount_formula"] == (
        "greater_of_insurance_amount_or_policy_account_value"
    )
    assert characteristics["death_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_age_99_policy_anniversary"
    )
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["accumulated_premium_balance_required"] is True
    assert characteristics["coverage_premium_ratio_required"] is True
    assert characteristics["risk_amount_formula_type"] == (
        "insurance_amount_less_policy_account_value_nonnegative"
    )
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["complete_disability_schedule_ref"] == "附表五"
    assert characteristics["complete_disability_table_item_count"] == 7
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["name"] == "滿期保險金"
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-or-funeral-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert "完全失能" not in " ".join(entry["name"] for entry in entries.values())

    source_path = TII_LIFE_017_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_prudential_chuangfu_variable_life(completed_document) == schedule
    assert (
        parse_prudential_chuangfu_variable_life(
            investment_life_document("tii-life-017", product_id, "F")
        )
        is None
    )

first_prudential_chuangfu_document = investment_life_document(
    "tii-life-017", "203141M31A01200"
)
assert (
    parse_prudential_chuangfu_variable_life(
        {**first_prudential_chuangfu_document, "product_id": "203141M31A01206"}
    )
    is None
)
assert (
    parse_prudential_chuangfu_variable_life(
        {
            **first_prudential_chuangfu_document,
            "text": first_prudential_chuangfu_document["text"].replace(
                "身故、完全殘廢保險金額」係指下列二者中金額較大者",
                "身故、完全殘廢保險金額」係指其他金額",
                1,
            ),
        }
    )
    is None
)

prudential_youyou_legacy_investment_expected = {
    "203141M31A00516": {
        "payment_currency_label": "新台幣",
        "premium_waiver_schedule_ref": "附表四",
    },
    "203141M31A00517": {
        "payment_currency_label": "新台幣",
        "premium_waiver_schedule_ref": "附表四",
    },
    "203141M31A00518": {
        "payment_currency_label": "新台幣",
        "premium_waiver_schedule_ref": "附表四",
    },
    "203141M31A00519": {
        "payment_currency_label": "新台幣",
        "premium_waiver_schedule_ref": "附表四",
    },
    "203141M31A00520": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00521": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00522": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00523": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00524": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00525": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00526": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00527": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00528": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
    "203141M31A00529": {
        "payment_currency_label": "新臺幣",
        "premium_waiver_schedule_ref": "附表五",
    },
}
for product_id, expected in prudential_youyou_legacy_investment_expected.items():
    document = investment_life_document("tii-life-017", product_id)
    schedule = parse_prudential_youyou_legacy_investment_life_maturity_face_amount(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "prudential-youyou-legacy-investment-life-maturity-face-amount-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "prudential-youyou-legacy-investment-linked-life-maturity-face-amount"
    )
    assert characteristics["company_group"] == "prudential"
    assert characteristics["currency_basis"] == "twd"
    assert (
        characteristics["payment_currency_label"]
        == expected["payment_currency_label"]
    )
    assert characteristics["insurance_amount_basis"] == (
        "policy_basic_insurance_amount"
    )
    assert characteristics["death_total_disability_amount_formula"] == (
        "face_amount_plus_policy_account_value"
    )
    assert characteristics["death_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "death_total_disability_insurance_amount"
    )
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert characteristics["maturity_benefit_formula"] == (
        "policy_account_value_at_age_99_policy_anniversary"
    )
    assert characteristics["policy_account_value_required"] is True
    assert characteristics["risk_amount_required"] is False
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["funeral_benefit_excludes_account_value"] is True
    assert characteristics["minor_death_before_age_15_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is True
    )
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["premium_waiver_disability_levels"] == "2-6"
    assert (
        characteristics["premium_waiver_schedule_ref"]
        == expected["premium_waiver_schedule_ref"]
    )
    assert characteristics["premium_waiver_until"] == "age_65_policy_anniversary"
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "disability-premium-waiver",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert (
        entries["death-or-funeral-benefit"]["unit_key"]
        == "death_total_disability_insurance_amount"
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert (
        entries["disability-premium-waiver"]["calculation_basis"]
        == "waiver"
    )
    assert entries["disability-premium-waiver"]["amount_role"] == "premium_waiver"
    assert (
        expected["premium_waiver_schedule_ref"]
        in " ".join(entries["disability-premium-waiver"]["conditions"])
    )
    assert "完全失能" not in " ".join(entry["name"] for entry in entries.values())

    source_path = TII_LIFE_017_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_prudential_youyou_legacy_investment_life_maturity_face_amount(
            completed_document
        )
        == schedule
    )
    assert (
        parse_prudential_youyou_legacy_investment_life_maturity_face_amount(
            investment_life_document("tii-life-017", product_id, "F")
        )
        is None
    )

first_prudential_youyou_document = investment_life_document(
    "tii-life-017", "203141M31A00516"
)
assert (
    parse_prudential_youyou_legacy_investment_life_maturity_face_amount(
        {**first_prudential_youyou_document, "product_id": "203141M31A00515"}
    )
    is None
)
assert (
    parse_prudential_youyou_legacy_investment_life_maturity_face_amount(
        {
            **first_prudential_youyou_document,
            "text": first_prudential_youyou_document["text"].replace(
                "身故、完全殘廢保險金額」係指下列二者加總之值",
                "身故、完全殘廢保險金額」係指其他金額",
                1,
            ),
        }
    )
    is None
)

legacy_face_or_account_value_expected = {
    ("tii-life-017", "203141M31A00210"): {
        "company_group": "prudential",
        "death_benefit_cap_rule": True,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-017", "203141M31A00211"): {
        "company_group": "prudential",
        "death_benefit_cap_rule": True,
        "payment_currency_label": "新台幣",
    },
    **{
        ("tii-life-017", f"203141M31A003{suffix:02d}"): {
            "company_group": "prudential",
            "death_benefit_cap_rule": False,
            "payment_currency_label": "新台幣",
        }
        for suffix in range(19, 30)
    },
    ("tii-life-029", "205141M31A53605"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53606"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53607"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53608"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53609"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53610"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53611"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53705"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53706"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53707"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53708"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
    ("tii-life-029", "205141M31A53709"): {
        "company_group": "kgi_china_life",
        "death_benefit_cap_rule": False,
        "payment_currency_label": "新台幣",
    },
}
legacy_face_or_account_value_roots = {
    "tii-life-017": TII_LIFE_017_ROOT,
    "tii-life-029": TII_LIFE_029_ROOT,
}
for (
    batch_id,
    product_id,
), expected in legacy_face_or_account_value_expected.items():
    document = investment_life_document(batch_id, product_id)
    schedule = parse_legacy_investment_life_face_or_account_value(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "legacy-investment-life-face-or-account-value-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert (
        characteristics["product_family"]
        == "legacy-investment-linked-life-face-or-account-value"
    )
    assert characteristics["company_group"] == expected["company_group"]
    assert characteristics["currency_basis"] == "twd"
    assert characteristics["payment_currency_label"] == expected["payment_currency_label"]
    assert (
        characteristics["insurance_amount_basis"]
        == "accumulated_premium_balance_times_face_amount_ratio"
    )
    assert characteristics["death_total_disability_amount_formula"] == (
        "greater_of_face_amount_or_policy_account_value"
    )
    assert characteristics["death_benefit_cap_rule"] == expected[
        "death_benefit_cap_rule"
    ]
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert characteristics["complete_disability_schedule_ref"] == "附表五"
    assert characteristics["funeral_benefit_limit_rule"] is False
    assert characteristics["minor_death_before_age_15_account_value_rule"] is False
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert entries["death-benefit"]["unit_key"] == (
        "death_total_disability_insurance_amount"
    )
    assert entries["death-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert "喪葬" not in " ".join(entry["name"] for entry in entries.values())

    source_path = (
        legacy_face_or_account_value_roots[batch_id]
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value for key, value in document.items() if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert parse_legacy_investment_life_face_or_account_value(completed_document) == schedule
    assert parse_legacy_investment_life_face_or_account_value(
        {
            **document,
            "document_type": "product_summary",
            "file_name": f"{product_id}-F.pdf",
        }
    ) is None

first_face_or_account_value_document = investment_life_document(
    "tii-life-017", "203141M31A00210"
)
assert parse_legacy_investment_life_face_or_account_value(
    {**first_face_or_account_value_document, "product_id": "203141M31A00212"}
) is None
assert parse_legacy_investment_life_face_or_account_value(
    {
        **first_face_or_account_value_document,
        "text": first_face_or_account_value_document["text"].replace(
            "二者中金額較大者",
            "二者中金額相同者",
            1,
        ),
    }
) is None

fubon_legacy_investment_expected = {
    "209131MV1A00123A11Z90000000": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00123A11Z90000001": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00123A11Z90000006": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00123A11Z90000007": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00123A11Z90000009": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00223Z11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000001": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000002": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000003": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000004": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000005": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000006": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000007": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000008": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00223Z11Z90000009": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00323Z11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00323Z11Z90000002": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00523Z11Z90000001": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00523Z11Z90000002": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "外幣",
    },
    "209131MV1A00623A11Z90000000": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00623A11Z90000001": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
    "209131MV1A00623A11Z90000002": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
    },
}
for product_id, expected in fubon_legacy_investment_expected.items():
    document = investment_life_document("tii-life-053", product_id)
    schedule = parse_fubon_legacy_investment_life_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-legacy-investment-life-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "fubon-legacy-investment-linked-life-face-amount"
    )
    assert characteristics["company_group"] == "fubon_life"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert (
        characteristics["payment_currency_label"]
        == expected["payment_currency_label"]
    )
    assert characteristics["maturity_trigger"] == "age_110_policy_anniversary"
    assert characteristics["maturity_age"] == 110
    assert (
        characteristics["maturity_benefit_formula"]
        == "policy_account_value_at_age_110_policy_anniversary"
    )
    assert characteristics["insurance_amount_formula"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["death_benefit_formula"] == "policy_insurance_amount"
    assert characteristics["total_disability_benefit_formula"] == (
        "policy_insurance_amount"
    )
    assert characteristics["net_amount_at_risk_formula_type"] == "jia_yi"
    assert characteristics["basic_amount_formula_type"] == (
        "basic_amount_by_selected_type"
    )
    assert characteristics["minor_death_before_age_15_account_value_rule"] is True
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is True
    )
    assert characteristics["complete_disability_schedule_ref"] == "附表四"
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["death-or-funeral-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["name"] == "完全殘廢保險金"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert "完全失能" not in " ".join(entry["name"] for entry in entries.values())

    source_path = TII_LIFE_053_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_fubon_legacy_investment_life_face_amount(completed_document)
        == schedule
    )
    assert parse_fubon_legacy_investment_life_face_amount(
        {
            **document,
            "document_type": "product_summary",
            "file_name": f"{product_id}-F.pdf",
        }
    ) is None

first_fubon_legacy_document = investment_life_document(
    "tii-life-053", "209131MV1A00123A11Z90000001"
)
assert parse_fubon_legacy_investment_life_face_amount(
    {**first_fubon_legacy_document, "product_id": "209131MV1A00123A11Z90000010"}
) is None
assert parse_fubon_legacy_investment_life_face_amount(
    {
        **first_fubon_legacy_document,
        "text": first_fubon_legacy_document["text"].replace(
            "按保險金額給付完全殘廢保險金",
            "按其他金額給付完全殘廢保險金",
            1,
        ),
    }
) is None

prudential_legacy_investment_expected = {
    "203131MV1A00323B11Z90000015": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表六",
    },
    "203131MV1A01023A11C90000000": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "target_premium_times_amount_factor",
        "complete_disability_schedule_ref": "附表六",
    },
    "203131MV1A01523Z11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "本契約計價貨幣",
        "basic_amount_formula_type": "target_premium_times_amount_factor",
        "complete_disability_schedule_ref": "附表七",
    },
    "203131MV1A00623B11C90000008": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "美元",
        "basic_amount_formula_type": "target_premium_times_two_with_account_value_ratio_adjustment",
        "complete_disability_schedule_ref": "附表六",
    },
    "203141M31A01700": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "人民幣",
        "basic_amount_formula_type": "target_premium_times_amount_factor",
        "complete_disability_schedule_ref": "附表六",
    },
    "203141M31A00330": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00123A11Z90000031": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00123A11Z90000032": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00123A11Z90000033": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_death_before_age_15": False,
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00123A11Z90000034": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表六",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00123A11Z90000035": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表六",
        "minor_disability_before_age_15": False,
    },
    "203141M31A01206": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00423A11Z90000007": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00423A11Z90000008": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00423A11Z90000009": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00423A11Z90000010": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "minor_disability_before_age_15": False,
    },
    "203131MV1A00423A11Z90000011": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表六",
        "minor_disability_before_age_15": False,
    },
    "203131MU1A00123A11Z90000031": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "policy_recorded_basic_amount",
        "complete_disability_schedule_ref": "完全殘廢程度表",
        "net_risk_formula_type": "basic_amount",
    },
    "203131MV1A00923A11Z90000001": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "policy_recorded_basic_amount",
        "complete_disability_schedule_ref": "附表五",
        "net_risk_formula_type": "basic_amount",
    },
    "203131MV1A01923A11Z90000000": {
        "currency_basis": "twd",
        "payment_currency_label": "新臺幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "net_risk_formula_type": "basic_amount_less_account_value_nonnegative",
    },
    "203131MV1A02023Z11Z90000000": {
        "currency_basis": "foreign_currency",
        "payment_currency_label": "本契約計價貨幣",
        "basic_amount_formula_type": "accumulated_premium_balance_times_ratio",
        "complete_disability_schedule_ref": "附表五",
        "net_risk_formula_type": "basic_amount_less_account_value_nonnegative",
    },
}
for product_id, expected in prudential_legacy_investment_expected.items():
    document = investment_life_document("tii-life-017", product_id)
    schedule = parse_prudential_legacy_investment_life_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-legacy-investment-life-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "prudential-legacy-investment-linked-life-face-amount"
    )
    assert characteristics["company_group"] == "prudential"
    assert characteristics["currency_basis"] == expected["currency_basis"]
    assert (
        characteristics["payment_currency_label"]
        == expected["payment_currency_label"]
    )
    assert (
        characteristics["basic_amount_formula_type"]
        == expected["basic_amount_formula_type"]
    )
    assert characteristics["maturity_trigger"] == "age_99_policy_anniversary"
    assert characteristics["maturity_age"] == 99
    assert (
        characteristics["maturity_benefit_formula"]
        == "policy_account_value_at_age_99_policy_anniversary"
    )
    assert characteristics["insurance_amount_formula"] == (
        "net_amount_at_risk_plus_policy_account_value"
    )
    assert characteristics["death_benefit_formula"] == "policy_insurance_amount"
    assert characteristics["total_disability_benefit_formula"] == (
        "policy_insurance_amount"
    )
    assert characteristics["net_amount_at_risk_formula_type"] == expected.get(
        "net_risk_formula_type", "basic_amount_less_account_value_nonnegative"
    )
    assert characteristics["minor_death_before_age_15_account_value_rule"] is expected.get(
        "minor_death_before_age_15", True
    )
    assert (
        characteristics["minor_disability_before_age_15_account_value_rule"]
        is expected.get("minor_disability_before_age_15", True)
    )
    assert characteristics["legacy_disability_wording"] is True
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["total_disability_term"] == "完全殘廢"
    assert (
        characteristics["complete_disability_schedule_ref"]
        == expected["complete_disability_schedule_ref"]
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "maturity-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
    }
    assert entries["maturity-benefit"]["unit_key"] == "policy_account_value"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["death-or-funeral-benefit"]["unit_key"] == "policy_insurance_amount"
    assert entries["total-disability-benefit"]["name"] == "完全殘廢保險金"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert "完全失能" not in " ".join(entry["name"] for entry in entries.values())

    source_path = TII_LIFE_017_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert (
        parse_prudential_legacy_investment_life_face_amount(completed_document)
        == schedule
    )
    assert parse_prudential_legacy_investment_life_face_amount(
        investment_life_document("tii-life-017", product_id, "F")
    ) is None

first_prudential_legacy_document = investment_life_document(
    "tii-life-017", "203131MV1A00323B11Z90000015"
)
assert parse_prudential_legacy_investment_life_face_amount(
    {**first_prudential_legacy_document, "product_id": "203131MV1A00323B11Z90000014"}
) is None
assert parse_prudential_legacy_investment_life_face_amount(
    {
        **first_prudential_legacy_document,
        "text": first_prudential_legacy_document["text"].replace(
            "按「保險金額」給付完全殘廢保險金",
            "按「其他金額」給付完全殘廢保險金",
            1,
        ),
    }
) is None

HSINGFU_FUYU_DWA_PRODUCT_ID = "215141M21A00102"
HSINGFU_FUYU_DWA_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-075"
)


def hsingfu_fuyu_dwa_document(suffix: str = "A") -> dict:
    file_name = "215141M21A00202-A.pdf" if suffix == "A" else f"{HSINGFU_FUYU_DWA_PRODUCT_ID}-{suffix}.pdf"
    pdf_path = HSINGFU_FUYU_DWA_ROOT / HSINGFU_FUYU_DWA_PRODUCT_ID / file_name
    page_texts = [page.extract_text() or "" for page in PdfReader(pdf_path, strict=False).pages]
    return {
        "batch_id": "tii-life-075",
        "product_id": HSINGFU_FUYU_DWA_PRODUCT_ID,
        "file_name": file_name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


hsingfu_fuyu_dwa_schedule = parse_hsingfu_fuyu_dwa_whole_life_face_amount(
    hsingfu_fuyu_dwa_document()
)
assert hsingfu_fuyu_dwa_schedule is not None
hsingfu_fuyu_dwa_integrated = parse_plan_table_with_parser(hsingfu_fuyu_dwa_document())
assert hsingfu_fuyu_dwa_integrated is not None
assert hsingfu_fuyu_dwa_integrated[0] == (
    "hsingfu-fuyu-dwa-whole-life-face-amount-v1"
)
assert hsingfu_fuyu_dwa_integrated[1] == hsingfu_fuyu_dwa_schedule
assert hsingfu_fuyu_dwa_schedule["selection_type"] == "face_amount"
assert hsingfu_fuyu_dwa_schedule["selection_label"] == "保險金額"
assert hsingfu_fuyu_dwa_schedule["version_characteristics"] == {
    "product_family": "hsingfu-fuyu-dwa-whole-life",
    "terms_revision": "second-partial-revision",
    "source_file_id": "215141M21A00202",
    "partial_change_filing_date": "95.10.02",
    "planned_interest_rate_percent": 2.75,
    "declared_rate_addition_available": True,
    "declared_rate_frequency": "monthly",
    "face_amount_formula": "before_age_15_policy_anniversary_basic_face_amount_then_basic_plus_cumulative_paid_up_addition",
    "insurance_amount_age_15_switch": True,
    "maturity_age": 110,
    "death_benefit_rate_percent": 100,
    "total_disability_benefit_rate_percent": 100,
    "premium_waiver_disability_levels": "2-6",
    "unexpired_premium_proration_included": True,
    "funeral_benefit_limit_rule": True,
    "non_participating_policy": True,
    "paid_up_addition_reference_required": True,
}
hsingfu_fuyu_dwa_entries = {
    entry["id"]: entry for entry in hsingfu_fuyu_dwa_schedule["coverage_entries"]
}
assert set(hsingfu_fuyu_dwa_entries) == {
    "declared-rate-paid-up-addition",
    "maturity-age-110",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "disability-premium-waiver",
}
assert hsingfu_fuyu_dwa_entries["maturity-age-110"]["rate_percent"] == 100
assert hsingfu_fuyu_dwa_entries["death-or-funeral-benefit"]["basis"] == "face_amount"
assert hsingfu_fuyu_dwa_entries["total-disability-benefit"]["rate_percent"] == 100
assert hsingfu_fuyu_dwa_entries["disability-premium-waiver"]["amount_role"] == "reference"
assert hsingfu_fuyu_dwa_entries["declared-rate-paid-up-addition"]["unit_key"] == (
    "declared_rate_paid_up_addition"
)
hsingfu_fuyu_dwa_source_path = (
    HSINGFU_FUYU_DWA_ROOT / HSINGFU_FUYU_DWA_PRODUCT_ID / "215141M21A00202-A.pdf"
)
hsingfu_fuyu_dwa_indexed = {
    key: value
    for key, value in hsingfu_fuyu_dwa_document().items()
    if key not in {"page_count", "pages_parsed"}
}
hsingfu_fuyu_dwa_indexed["text"] = hsingfu_fuyu_dwa_indexed["text"].split(
    "【保險契約的構成】"
)[0]
hsingfu_fuyu_dwa_completed = complete_strict_source_document(
    hsingfu_fuyu_dwa_indexed, hsingfu_fuyu_dwa_source_path
)
assert hsingfu_fuyu_dwa_completed["page_count"] == 19
assert (
    parse_hsingfu_fuyu_dwa_whole_life_face_amount(hsingfu_fuyu_dwa_completed)
    == hsingfu_fuyu_dwa_schedule
)
assert parse_hsingfu_fuyu_dwa_whole_life_face_amount(
    {**hsingfu_fuyu_dwa_document(), "product_id": "215141M21A00103"}
) is None
assert parse_hsingfu_fuyu_dwa_whole_life_face_amount(
    {**hsingfu_fuyu_dwa_document(), "document_type": "product_summary"}
) is None
assert parse_hsingfu_fuyu_dwa_whole_life_face_amount(
    {
        **hsingfu_fuyu_dwa_document(),
        "text": hsingfu_fuyu_dwa_document()["text"].replace(
            "第二級至第六級殘廢程度之一者",
            "第二級至第三級殘廢程度之一者",
            1,
        ),
    }
) is None

HSINGFU_PLATINUM_ENDOWMENT_PRODUCT_ID = "215121M11A05608"


def hsingfu_platinum_endowment_document(suffix: str = "A") -> dict:
    file_name = f"{HSINGFU_PLATINUM_ENDOWMENT_PRODUCT_ID}-{suffix}.pdf"
    pdf_path = HSINGFU_FUYU_DWA_ROOT / HSINGFU_PLATINUM_ENDOWMENT_PRODUCT_ID / file_name
    page_texts = [
        page.extract_text() or "" for page in PdfReader(pdf_path, strict=False).pages
    ]
    return {
        "batch_id": "tii-life-075",
        "product_id": HSINGFU_PLATINUM_ENDOWMENT_PRODUCT_ID,
        "file_name": file_name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


hsingfu_platinum_schedule = parse_hsingfu_platinum_endowment_face_amount(
    hsingfu_platinum_endowment_document()
)
assert hsingfu_platinum_schedule is not None
hsingfu_platinum_integrated = parse_plan_table_with_parser(
    hsingfu_platinum_endowment_document()
)
assert hsingfu_platinum_integrated is not None
assert hsingfu_platinum_integrated[0] == (
    "hsingfu-platinum-endowment-face-amount-v1"
)
assert hsingfu_platinum_integrated[1] == hsingfu_platinum_schedule
assert hsingfu_platinum_schedule["selection_type"] == "face_amount"
assert hsingfu_platinum_schedule["selection_label"] == "當年度保險金額"
assert hsingfu_platinum_schedule["version_characteristics"] == {
    "product_family": "hsingfu-platinum-endowment",
    "terms_revision": "eighth-partial-revision",
    "filing_number": "92.01.28 福算字第 0240 號",
    "latest_revision_basis": "100.9.1 依 100.4.11 金管保品字第 10002523040 號函修正",
    "annual_insured_amount_formula": "first_policy_year_policy_face_amount_then_annual_face_amount_step_accumulation",
    "maturity_benefit_formula": "annual_insured_amount_at_policy_maturity",
    "death_benefit_rate_percent": 100,
    "total_disability_benefit_rate_percent": 100,
    "funeral_benefit_limit_rule": True,
    "non_participating_policy": True,
    "annual_insured_amount_table_required": True,
}
hsingfu_platinum_entries = {
    entry["id"]: entry for entry in hsingfu_platinum_schedule["coverage_entries"]
}
assert set(hsingfu_platinum_entries) == {
    "annual-insured-amount-reference",
    "maturity-benefit",
    "death-or-funeral-benefit",
    "total-disability-benefit",
}
assert hsingfu_platinum_entries["maturity-benefit"]["rate_percent"] == 100
assert hsingfu_platinum_entries["death-or-funeral-benefit"]["unit_key"] == (
    "annual_insured_amount"
)
assert hsingfu_platinum_entries["total-disability-benefit"]["aggregation_rule"] == (
    "choose_one"
)
assert hsingfu_platinum_entries["annual-insured-amount-reference"]["amount_role"] == (
    "reference"
)
hsingfu_platinum_source_path = (
    HSINGFU_FUYU_DWA_ROOT
    / HSINGFU_PLATINUM_ENDOWMENT_PRODUCT_ID
    / "215121M11A05608-A.pdf"
)
hsingfu_platinum_indexed = {
    key: value
    for key, value in hsingfu_platinum_endowment_document().items()
    if key not in {"page_count", "pages_parsed"}
}
hsingfu_platinum_indexed["text"] = hsingfu_platinum_indexed["text"].split(
    "【保險契約的構成】"
)[0]
hsingfu_platinum_completed = complete_strict_source_document(
    hsingfu_platinum_indexed, hsingfu_platinum_source_path
)
assert hsingfu_platinum_completed["page_count"] == 10
assert (
    parse_hsingfu_platinum_endowment_face_amount(hsingfu_platinum_completed)
    == hsingfu_platinum_schedule
)
assert parse_hsingfu_platinum_endowment_face_amount(
    {**hsingfu_platinum_endowment_document(), "product_id": "215121M11A05607"}
) is None
assert parse_hsingfu_platinum_endowment_face_amount(
    {**hsingfu_platinum_endowment_document(), "document_type": "product_summary"}
) is None
assert parse_hsingfu_platinum_endowment_face_amount(
    {
        **hsingfu_platinum_endowment_document(),
        "text": hsingfu_platinum_endowment_document()["text"].replace(
            "第二保單年度起每年按保單保險金額每滿該一保單年度",
            "第二保單年度起依另行約定調整",
            1,
        ),
    }
) is None

TII_LIFE_009_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-009-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
TII_LIFE_009_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-009"
)


def taiwan_interest_whole_life_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_009_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


taiwan_platinum_account_cases = {
    "202121M21AYI001": {
        "product_code": "YI0",
        "terms_revision": "original",
        "page_count": 11,
        "death_entry_id": "death-benefit",
        "death_entry_name": "身故保險金",
        "funeral_benefit_limit_rule": False,
    },
    "202121M21AYI103": {
        "product_code": "YI1",
        "terms_revision": "third-partial-revision",
        "page_count": 12,
        "death_entry_id": "death-or-funeral-benefit",
        "death_entry_name": "身故保險金或喪葬費用保險金",
        "funeral_benefit_limit_rule": True,
    },
}
for product_id, expected in taiwan_platinum_account_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_platinum_account_endowment_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-platinum-account-endowment-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "taiwan-platinum-account-endowment"
    assert characteristics["product_code"] == expected["product_code"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["policy_value_reserve_required"] is True
    assert characteristics["maturity_benefit_formula"] == (
        "policy_value_reserve_at_policy_maturity"
    )
    assert characteristics["death_benefit_formula"] == (
        "greater_of_insurance_amount_and_policy_value_reserve_plus_unexpired_insurance_cost"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "greater_of_insurance_amount_and_policy_value_reserve_plus_unexpired_insurance_cost"
    )
    assert (
        characteristics["funeral_benefit_limit_rule"]
        is expected["funeral_benefit_limit_rule"]
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "policy-value-reserve-reference",
        "maturity-benefit",
        expected["death_entry_id"],
        "total-disability-benefit",
    }
    assert entries[expected["death_entry_id"]]["name"] == expected["death_entry_name"]
    assert entries[expected["death_entry_id"]]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["aggregation_rule"] == "choose_one"
    assert entries["maturity-benefit"]["unit_key"] == "policy_value_reserve"
    assert entries["policy-value-reserve-reference"]["amount_role"] == "reference"
    source_path = TII_LIFE_009_ROOT / product_id / f"{product_id}-A.pdf"
    indexed = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed["text"] = indexed["text"].split("【保險契約的構成】")[0]
    completed = complete_strict_source_document(indexed, source_path)
    assert completed["page_count"] == expected["page_count"]
    assert parse_taiwan_platinum_account_endowment_formula(completed) == schedule
    assert (
        parse_taiwan_platinum_account_endowment_formula(
            {**document, "product_id": "202121M21AYI999"}
        )
        is None
    )
    assert (
        parse_taiwan_platinum_account_endowment_formula(
            {**taiwan_interest_whole_life_document(product_id, "F")}
        )
        is None
    )


taiwan_yibao_3xiang_cases = {
    "202191MZ1B83123A11Z10000000": "original",
    "202191MZ1B83123A11Z10000001": "first-regulatory-revision",
    "202191MZ1B83123A11Z10000002": "second-company-revision",
    "202191MZ1B83123A11Z10000003": "third-regulatory-revision",
}
for product_id, expected_revision in taiwan_yibao_3xiang_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_yibao_3xiang_medical_whole_life_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-yibao-3xiang-medical-whole-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["disease_waiting_days"] == 30
    assert characteristics["cancer_waiting_days"] == 90
    assert characteristics["initial_cancer_multiplier"] == 5
    assert characteristics["mild_cancer_multiplier"] == 20
    assert characteristics["severe_cancer_multiplier"] == 100
    assert characteristics["hospital_care_fraction"] == "2/3"
    assert characteristics["no_hospital_claim_bonus_rate_percent"] == 1.2
    assert characteristics["premium_refund_interest_rate_percent"] == 1.75
    assert characteristics["medical_lifetime_cap_amount"] == 25_000_000
    assert characteristics["premium_waiver_disability_levels"] == "1-6"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "initial-cancer-benefit",
        "mild-cancer-benefit",
        "severe-cancer-benefit",
        "hospital-daily-benefit",
        "hospital-care-benefit",
        "inpatient-surgery-specific-treatment-benefit",
        "outpatient-surgery-specific-treatment-benefit",
        "no-hospital-claim-bonus",
        "death-or-funeral-benefit",
        "maturity-benefit",
        "premium-waiver",
        "premium-refund-with-interest-under-age-16",
        "medical-benefit-lifetime-cap",
    }
    assert entries["initial-cancer-benefit"]["multiplier"] == 5
    assert entries["mild-cancer-benefit"]["multiplier"] == 20
    assert entries["severe-cancer-benefit"]["multiplier"] == 100
    assert entries["hospital-daily-benefit"]["limit_scope"] == "per_day"
    assert entries["hospital-daily-benefit"]["multiplier"] == 1
    assert entries["hospital-care-benefit"]["rate_percent"] == 66.6667
    assert entries["inpatient-surgery-specific-treatment-benefit"]["multiplier"] == 5
    assert entries["outpatient-surgery-specific-treatment-benefit"]["multiplier"] == 1
    assert entries["no-hospital-claim-bonus"]["rate_percent"] == 1.2
    assert entries["no-hospital-claim-bonus"]["unit_key"] == "annual_premium_total"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["unit_key"] == "annual_premium_total_at_age_110"
    assert entries["premium-refund-with-interest-under-age-16"]["amount_role"] == "payout"
    assert entries["medical-benefit-lifetime-cap"]["amount"] == 25_000_000
    assert entries["medical-benefit-lifetime-cap"]["amount_role"] == "limit"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert (
    parse_taiwan_yibao_3xiang_medical_whole_life_face_amount(
        taiwan_interest_whole_life_document("202191MZ1B83123A11Z10000000", "F")
    )
    is None
)
wrong_taiwan_yibao_document = {
    **taiwan_interest_whole_life_document("202191MZ1B83123A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert (
    parse_taiwan_yibao_3xiang_medical_whole_life_face_amount(
        wrong_taiwan_yibao_document
    )
    is None
)


taiwan_yixiang_health_medical_cases = {
    "202191MZ1B89723A11Z10000000": "original",
    "202191MZ1B89723A11Z10000001": "first-regulatory-revision",
}
for product_id, expected_revision in taiwan_yixiang_health_medical_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_yixiang_health_medical_whole_life_fixed(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-yixiang-health-medical-whole-life-fixed-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    assert schedule["selection_label"] == "固定保險金額 5,000 元"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "taiwan-yixiang-health-medical-whole-life"
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fixed_policy_face_amount"] == 5_000
    assert characteristics["disease_waiting_days"] == 30
    assert characteristics["cancer_waiting_days"] == 90
    assert characteristics["initial_cancer_multiplier"] == 5
    assert characteristics["mild_cancer_multiplier"] == 10
    assert characteristics["severe_cancer_multiplier"] == 50
    assert characteristics["hospital_daily_amount"] == 5_000
    assert characteristics["special_room_daily_amount"] == 5_000
    assert characteristics["inpatient_surgery_specific_treatment_amount"] == 25_000
    assert characteristics["outpatient_surgery_specific_treatment_amount"] == 5_000
    assert characteristics["no_hospital_claim_bonus_rate_percent"] == 1.4
    assert characteristics["premium_refund_interest_available"] is False
    assert characteristics["medical_lifetime_cap_amount"] == 25_000_000
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "initial-cancer-benefit",
        "mild-cancer-benefit",
        "severe-cancer-benefit",
        "hospital-daily-benefit",
        "special-room-daily-benefit",
        "inpatient-surgery-specific-treatment-benefit",
        "outpatient-surgery-specific-treatment-benefit",
        "no-hospital-claim-bonus",
        "death-or-funeral-benefit",
        "maturity-benefit",
        "premium-waiver",
        "annual-premium-total-refund-under-age-16",
        "medical-benefit-lifetime-cap",
    }
    assert entries["initial-cancer-benefit"]["amount"] == 25_000
    assert entries["mild-cancer-benefit"]["amount"] == 50_000
    assert entries["severe-cancer-benefit"]["amount"] == 250_000
    assert entries["hospital-daily-benefit"]["amount"] == 5_000
    assert entries["hospital-daily-benefit"]["calculation_basis"] == "per_day"
    assert entries["special-room-daily-benefit"]["amount"] == 5_000
    assert entries["special-room-daily-benefit"]["limit_scope"] == "per_day"
    assert entries["inpatient-surgery-specific-treatment-benefit"]["amount"] == 25_000
    assert entries["outpatient-surgery-specific-treatment-benefit"]["amount"] == 5_000
    assert entries["no-hospital-claim-bonus"]["rate_percent"] == 1.4
    assert entries["no-hospital-claim-bonus"]["unit_key"] == "annual_premium_total"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["unit_key"] == "annual_premium_total_at_age_110"
    assert entries["annual-premium-total-refund-under-age-16"]["unit_key"] == "annual_premium_total"
    assert entries["medical-benefit-lifetime-cap"]["amount"] == 25_000_000
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())
    assert (
        parse_taiwan_yixiang_health_medical_whole_life_fixed(
            taiwan_interest_whole_life_document(product_id, "F")
        )
        is None
    )

    source_path = TII_LIFE_009_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = document["text"].split("第三條")[0]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 29
    assert parse_taiwan_yixiang_health_medical_whole_life_fixed(completed_document) == schedule

wrong_taiwan_yixiang_document = {
    **taiwan_interest_whole_life_document("202191MZ1B89723A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert (
    parse_taiwan_yixiang_health_medical_whole_life_fixed(
        wrong_taiwan_yixiang_document
    )
    is None
)


taiwan_lehuo_health_medical_cases = {
    "202191MZ1B89823A11Z10000000": "original",
    "202191MZ1B89823A11Z10000001": "first-regulatory-revision",
}
for product_id, expected_revision in taiwan_lehuo_health_medical_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_lehuo_health_medical_whole_life_fixed(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-lehuo-health-medical-whole-life-fixed-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    assert schedule["selection_label"] == "固定保險金額 5,000 元"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == "taiwan-lehuo-health-medical-whole-life"
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fixed_policy_face_amount"] == 5_000
    assert characteristics["disease_waiting_days"] == 30
    assert characteristics["cancer_waiting_days"] == 90
    assert characteristics["initial_cancer_multiplier"] == 5
    assert characteristics["mild_cancer_multiplier"] == 20
    assert characteristics["severe_cancer_multiplier"] == 100
    assert characteristics["specific_disease_multiplier"] == 100
    assert characteristics["hospital_daily_amount"] == 5_000
    assert characteristics["special_room_daily_amount"] == 5_000
    assert characteristics["inpatient_surgery_specific_treatment_amount"] == 25_000
    assert characteristics["outpatient_surgery_specific_treatment_amount"] == 5_000
    assert characteristics["medical_device_amount"] == 50_000
    assert characteristics["no_hospital_claim_bonus_rate_percent"] == 1.1
    assert characteristics["premium_waiver_triggers"] == "specific_disease_or_disability_levels_1_to_6"
    assert characteristics["premium_refund_interest_available"] is False
    assert characteristics["medical_lifetime_cap_amount"] == 25_000_000
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "initial-cancer-benefit",
        "mild-cancer-benefit",
        "severe-cancer-benefit",
        "specific-disease-benefit",
        "hospital-daily-benefit",
        "special-room-daily-benefit",
        "inpatient-surgery-specific-treatment-benefit",
        "outpatient-surgery-specific-treatment-benefit",
        "artificial-lens-device-benefit",
        "artificial-hip-device-benefit",
        "artificial-knee-device-benefit",
        "cardiovascular-stent-device-benefit",
        "no-hospital-claim-bonus",
        "death-or-funeral-benefit",
        "maturity-benefit",
        "premium-waiver",
        "annual-premium-total-refund-under-age-16",
        "medical-benefit-lifetime-cap",
    }
    assert entries["initial-cancer-benefit"]["amount"] == 25_000
    assert entries["mild-cancer-benefit"]["amount"] == 100_000
    assert entries["severe-cancer-benefit"]["amount"] == 500_000
    assert entries["specific-disease-benefit"]["amount"] == 500_000
    assert entries["hospital-daily-benefit"]["amount"] == 5_000
    assert entries["hospital-daily-benefit"]["calculation_basis"] == "per_day"
    assert entries["special-room-daily-benefit"]["amount"] == 5_000
    assert entries["inpatient-surgery-specific-treatment-benefit"]["amount"] == 25_000
    assert entries["outpatient-surgery-specific-treatment-benefit"]["amount"] == 5_000
    assert entries["artificial-lens-device-benefit"]["amount"] == 50_000
    assert entries["artificial-hip-device-benefit"]["amount"] == 50_000
    assert entries["artificial-knee-device-benefit"]["amount"] == 50_000
    assert entries["cardiovascular-stent-device-benefit"]["amount"] == 50_000
    assert entries["no-hospital-claim-bonus"]["rate_percent"] == 1.1
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["unit_key"] == "annual_premium_total_at_age_110"
    assert entries["annual-premium-total-refund-under-age-16"]["unit_key"] == "annual_premium_total"
    assert entries["medical-benefit-lifetime-cap"]["amount"] == 25_000_000
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())
    assert (
        parse_taiwan_lehuo_health_medical_whole_life_fixed(
            taiwan_interest_whole_life_document(product_id, "F")
        )
        is None
    )

    source_path = TII_LIFE_009_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = document["text"].split("第三條")[0]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 30
    assert parse_taiwan_lehuo_health_medical_whole_life_fixed(completed_document) == schedule

wrong_taiwan_lehuo_document = {
    **taiwan_interest_whole_life_document("202191MZ1B89823A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert (
    parse_taiwan_lehuo_health_medical_whole_life_fixed(
        wrong_taiwan_lehuo_document
    )
    is None
)


taiwan_fixed_return_cases = {
    "202121MZ1A02A23A11Z10000000": {
        "product_family": "taiwan-yiliqi-fixed-return-whole-life",
        "terms_revision": "original",
        "survival_min": 1.04,
        "survival_max": 6.24,
        "monthly": False,
    },
    "202121MZ1A02A23A11Z10000001": {
        "product_family": "taiwan-yiliqi-fixed-return-whole-life",
        "terms_revision": "first-regulatory-revision",
        "survival_min": 1.04,
        "survival_max": 6.24,
        "monthly": False,
    },
    "202121MZ1A53A23A11Z10000000": {
        "product_family": "taiwan-jinduobei-fixed-return-whole-life",
        "terms_revision": "original",
        "survival_min": 0.98,
        "survival_max": 5.88,
        "monthly": True,
    },
}
for product_id, expected in taiwan_fixed_return_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_fixed_return_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-fixed-return-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == expected["product_family"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["currency"] == "TWD"
    assert characteristics["value_sharing_bonus"] is False
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["post_fifth_policy_year_face_amount_multiplier"] == 3.6
    assert characteristics["maturity_age"] == 100
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["installment_period_min_years"] == 5
    assert characteristics["installment_period_max_years"] == 30
    assert characteristics["minimum_annual_installment_amount"] == 36_000
    assert characteristics["survival_rate_min_percent"] == expected["survival_min"]
    assert characteristics["survival_rate_max_percent"] == expected["survival_max"]
    assert (
        characteristics["monthly_survival_benefit_available"]
        is expected["monthly"]
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "survival-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["survival-benefit"]["calculation_basis"] == "percentage_of_base"
    assert entries["survival-benefit"]["rate_min_percent"] == expected["survival_min"]
    assert entries["survival-benefit"]["rate_max_percent"] == expected["survival_max"]
    assert entries["survival-benefit"]["unit_key"] == "previous_policy_year_basic_face_amount"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["aggregation_rule"] == "highest"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["aggregation_rule"] == "highest"
    assert entries["maturity-benefit"]["unit_key"] == "age_99_annual_insured_amount"
    assert entries["installment-periodic-benefit"]["amount_role"] == "reference"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert (
    parse_taiwan_fixed_return_whole_life_formula(
        taiwan_interest_whole_life_document("202121MZ1A02A23A11Z10000000", "F")
    )
    is None
)
wrong_taiwan_fixed_return_document = {
    **taiwan_interest_whole_life_document("202121MZ1A02A23A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert parse_taiwan_fixed_return_whole_life_formula(
    wrong_taiwan_fixed_return_document
) is None


taiwan_interest_cases = {
    "202131MA1A08A23J11Z10000000": {
        "currency": "CNY",
        "expected_rate": 1.50,
        "annual_formula": "first_two_policy_years_premium_total_then_face_plus_accumulated",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A11A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.50,
        "annual_formula": "single_premium_face_plus_accumulated_or_two_year_first_year_106",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "annual_insured_amount_times_coefficient_table",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A82123B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.05,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions",
        "premium_component": "premium_total_times_1_03",
        "maturity_formula": "annual_insured_amount_times_coefficient_table",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A88923B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions",
        "premium_component": "none",
        "maturity_formula": "annual_insured_amount",
        "death_calculation": "percentage_of_base",
        "premium_waiver": True,
    },
    "202131MA1A99523A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A69A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_policy_year_premium_total_then_face_plus_accumulated",
        "premium_component": "premium_total",
        "maturity_formula": "annual_insured_amount_times_coefficient_table",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A81723A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 0.75,
        "annual_formula": "first_five_policy_years_premium_total_times_1_02_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_02",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A82223B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "premium_period_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "annual_insured_amount",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A88423B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "premium_period_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "annual_insured_amount",
        "death_calculation": "greater_of",
        "premium_waiver": True,
    },
    "202131MA1A42A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A44A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A45A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": None,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A45A23B11Z10000001": {
        "currency": "USD",
        "expected_rate": None,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A47A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": None,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A47A23B11Z10000001": {
        "currency": "USD",
        "expected_rate": None,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA1A57A23A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.25,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA4B94423B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "premium_period_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "annual_insured_amount",
        "death_calculation": "greater_of",
        "premium_waiver": True,
    },
    "202131MA1A95823B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": True,
    },
    "202131MA1A99123B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.50,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA9B91923B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
        "statutory_infectious": True,
    },
    "202131MA2A23A23A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 2.00,
        "annual_formula": "first_three_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA2A92023A11Z10000000": {
        "currency": "TWD",
        "expected_rate": None,
        "annual_formula": "payment_period_2_6_front_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA2A96923A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
    "202131MA2A99323A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "death_calculation": "greater_of",
        "premium_waiver": False,
    },
}
for product_id, expected in taiwan_interest_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "保單價值準備金" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == expected["currency"]
    assert characteristics["expected_interest_rate_percent"] == expected["expected_rate"]
    assert characteristics["annual_insured_amount_formula"] == expected["annual_formula"]
    assert characteristics["premium_component"] == expected["premium_component"]
    assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]
    assert characteristics["maturity_age"] == 111
    assert characteristics["value_sharing_bonus"] is True
    assert characteristics["premium_waiver_available"] is expected["premium_waiver"]
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
    }
    assert (
        entries["death-or-funeral-benefit"]["calculation_basis"]
        == expected["death_calculation"]
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert entries["value-sharing-bonus"]["calculation_basis"] == "unknown"
    assert entries["value-sharing-bonus"]["basis"] == "policy_recorded_limit"
    assert ("premium-waiver" in entries) is expected["premium_waiver"]
    if expected.get("statutory_infectious"):
        assert characteristics["statutory_infectious_comfort_benefit"] is True
        assert characteristics["statutory_infectious_rate_percent"] == 1
        assert characteristics["statutory_infectious_policy_year_limit"] == 1
        assert characteristics["statutory_infectious_limit_times"] == 1
        assert "statutory-infectious-comfort-benefit" in entries
        infectious_entry = entries["statutory-infectious-comfort-benefit"]
        assert infectious_entry["calculation_basis"] == "percentage_of_base"
        assert infectious_entry["basis"] == "face_amount"
        assert infectious_entry["rate_percent"] == 1
        assert infectious_entry["limit_scope"] == "per_policy"
    else:
        assert "statutory_infectious_comfort_benefit" not in characteristics
        assert "statutory-infectious-comfort-benefit" not in entries
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert parse_taiwan_interest_rate_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA1A08A23J11Z10000000", "F")
) is None
assert parse_taiwan_interest_rate_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA9B91923B11Z10000000", "F")
) is None
assert (
    parse_taiwan_interest_rate_whole_life_formula(
        {
            **taiwan_interest_whole_life_document("202131MA9B91923B11Z10000000"),
            "text": taiwan_interest_whole_life_document(
                "202131MA9B91923B11Z10000000"
            )["text"].replace(
                "保險金額的 1%給付法定傳染病慰問保險金",
                "保險金額的 2%給付法定傳染病慰問保險金",
                1,
            ),
        }
    )
    is None
)
wrong_taiwan_interest_document = {
    **taiwan_interest_whole_life_document("202131MA1A08A23J11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert parse_taiwan_interest_rate_whole_life_formula(
    wrong_taiwan_interest_document
) is None
taiwan_interest_indexed = taiwan_interest_whole_life_document(
    "202131MA1A08A23J11Z10000000"
)
taiwan_interest_completed = complete_strict_source_document(
    {
        **taiwan_interest_indexed,
        "text": taiwan_interest_indexed["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202131MA1A08A23J11Z10000000"
    / "202131MA1A08A23J11Z10000000-A.pdf",
)
assert taiwan_interest_completed["page_count"] == 10
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_interest_completed) is not None

taiwan_fengfu_meili_product_id = "202131MA9B91023B11Z10000000"
taiwan_fengfu_meili_indexed = taiwan_interest_whole_life_document(
    taiwan_fengfu_meili_product_id
)
taiwan_fengfu_meili_completed = complete_strict_source_document(
    taiwan_fengfu_meili_indexed,
    TII_LIFE_009_ROOT
    / taiwan_fengfu_meili_product_id
    / f"{taiwan_fengfu_meili_product_id}-A.pdf",
)
assert taiwan_fengfu_meili_completed["page_count"] == 14
taiwan_fengfu_meili_schedule = parse_taiwan_fengfu_meili_usd_interest_whole_life(
    taiwan_fengfu_meili_completed
)
assert taiwan_fengfu_meili_schedule is not None
integrated = parse_plan_table_with_parser(taiwan_fengfu_meili_completed)
assert integrated is not None
assert integrated[0] == "taiwan-fengfu-meili-usd-interest-whole-life-v1"
assert integrated[1] == taiwan_fengfu_meili_schedule
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_fengfu_meili_completed) is None
assert taiwan_fengfu_meili_schedule["selection_type"] == "face_amount"
assert taiwan_fengfu_meili_schedule["selection_label"] == "基本保險金額"
characteristics = taiwan_fengfu_meili_schedule["version_characteristics"]
assert characteristics["product_family"] == "taiwan-fengfu-meili-usd-interest-whole-life"
assert characteristics["terms_revision"] == "110-original"
assert characteristics["filing_number"] == "台壽字第1102320155號函備查"
assert characteristics["currency"] == "USD"
assert characteristics["expected_interest_rate_percent"] == 1.75
assert characteristics["annual_insured_amount_formula"] == (
    "first_three_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient"
)
assert characteristics["death_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total"
)
assert characteristics["total_disability_benefit_available"] is False
assert characteristics["maturity_benefit_formula"] == (
    "greater_of_annual_insured_amount_and_premium_total_times_1_06"
)
assert characteristics["premium_component"] == "premium_total_times_1_06"
assert characteristics["premium_multiplier"] == 1.06
assert characteristics["maturity_age"] == 111
assert characteristics["installment_benefit_available"] is True
assert characteristics["premium_waiver_available"] is True
assert characteristics["premium_waiver_disability_grade_min"] == 1
assert characteristics["premium_waiver_disability_grade_max"] == 9
assert characteristics["statutory_infectious_comfort_benefit"] is True
assert characteristics["statutory_infectious_rate_percent"] == 1
assert characteristics["statutory_infectious_policy_year_limit"] == 1
assert characteristics["statutory_infectious_limit_times"] == 1
entries = {
    entry["id"]: entry
    for entry in taiwan_fengfu_meili_schedule["coverage_entries"]
}
assert set(entries) == {
    "value-sharing-bonus",
    "death-or-funeral-benefit",
    "maturity-benefit",
    "premium-waiver",
    "statutory-infectious-comfort-benefit",
    "installment-periodic-benefit",
}
assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
assert entries["death-or-funeral-benefit"]["aggregation_rule"] == "highest"
assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
assert entries["maturity-benefit"]["aggregation_rule"] == "highest"
assert entries["premium-waiver"]["calculation_basis"] == "unknown"
assert entries["premium-waiver"]["amount_role"] == "reference"
assert entries["statutory-infectious-comfort-benefit"]["basis"] == "face_amount"
assert entries["statutory-infectious-comfort-benefit"]["rate_percent"] == 1
assert entries["installment-periodic-benefit"]["amount_role"] == "reference"
assert "total-disability-benefit" not in entries
assert all(entry["source"] == "terms" for entry in entries.values())
assert all(entry.get("conditions") for entry in entries.values())
assert (
    parse_taiwan_fengfu_meili_usd_interest_whole_life(
        taiwan_interest_whole_life_document(taiwan_fengfu_meili_product_id, "F")
    )
    is None
)
assert (
    parse_taiwan_fengfu_meili_usd_interest_whole_life(
        {**taiwan_fengfu_meili_completed, "product_id": "wrong-product"}
    )
    is None
)
assert (
    parse_taiwan_fengfu_meili_usd_interest_whole_life(
        {
            **taiwan_fengfu_meili_completed,
            "text": taiwan_fengfu_meili_completed["text"].replace(
                "保險金額的 1%給付法定傳染病慰問保險金",
                "保險金額的 2%給付法定傳染病慰問保險金",
            ),
        }
    )
    is None
)
assert (
    parse_taiwan_fengfu_meili_usd_interest_whole_life(
        {
            **taiwan_fengfu_meili_completed,
            "text": taiwan_fengfu_meili_completed["text"] + "完全失能保險金",
        }
    )
    is None
)

taiwan_yaozuan_chuanshi_product_id = "202131MA9B12B23B11Z10000000"
taiwan_yaozuan_chuanshi_indexed = taiwan_interest_whole_life_document(
    taiwan_yaozuan_chuanshi_product_id
)
taiwan_yaozuan_chuanshi_completed = complete_strict_source_document(
    taiwan_yaozuan_chuanshi_indexed,
    TII_LIFE_009_ROOT
    / taiwan_yaozuan_chuanshi_product_id
    / f"{taiwan_yaozuan_chuanshi_product_id}-A.pdf",
)
assert taiwan_yaozuan_chuanshi_completed["page_count"] == 21
taiwan_yaozuan_chuanshi_schedule = (
    parse_taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health(
        taiwan_yaozuan_chuanshi_completed
    )
)
assert taiwan_yaozuan_chuanshi_schedule is not None
integrated = parse_plan_table_with_parser(taiwan_yaozuan_chuanshi_completed)
assert integrated is not None
assert integrated[0] == "taiwan-yaozuan-chuanshi-usd-whole-life-cancer-health-v1"
assert integrated[1] == taiwan_yaozuan_chuanshi_schedule
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_yaozuan_chuanshi_completed) is None
assert taiwan_yaozuan_chuanshi_schedule["selection_type"] == "face_amount"
assert taiwan_yaozuan_chuanshi_schedule["selection_label"] == "基本保險金額"
characteristics = taiwan_yaozuan_chuanshi_schedule["version_characteristics"]
assert characteristics["product_family"] == (
    "taiwan-yaozuan-chuanshi-usd-whole-life-cancer-health"
)
assert characteristics["terms_revision"] == "114-original"
assert characteristics["filing_number"] == "台壽字第1142320109號"
assert characteristics["currency"] == "USD"
assert characteristics["expected_interest_rate_percent"] == 2.5
assert characteristics["payment_period_options"] == [10, 12]
assert characteristics["cancer_waiting_days"] == 90
assert characteristics["special_treatment_rate_percent"] == 50
assert characteristics["robotic_surgery_rate_percent"] == 2.5
assert characteristics["special_treatment_lifetime_limit_times"] == 1
assert characteristics["robotic_surgery_lifetime_limit_times"] == 1
assert characteristics["robotic_surgery_system_table_required"] is True
assert characteristics["health_surrender_value_available"] is False
assert characteristics["health_unpaid_premium_refund_available"] is False
assert characteristics["annual_insured_amount_formula"] == (
    "face_amount_plus_accumulated_paid_up_additions_times_coefficient"
)
assert characteristics["death_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total"
)
assert characteristics["total_disability_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total"
)
assert characteristics["maturity_benefit_formula"] == (
    "greater_of_annual_insured_amount_and_premium_total_times_1_06"
)
assert characteristics["premium_component"] == "premium_total_times_1_06"
assert characteristics["premium_multiplier"] == 1.06
assert characteristics["maturity_age"] == 111
entries = {
    entry["id"]: entry
    for entry in taiwan_yaozuan_chuanshi_schedule["coverage_entries"]
}
assert set(entries) == {
    "value-sharing-bonus",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "special-treatment-benefit",
    "cancer-robotic-surgery-benefit",
    "maturity-benefit",
    "installment-periodic-benefit",
}
assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
assert entries["special-treatment-benefit"]["rate_percent"] == 50
assert entries["special-treatment-benefit"]["unit_key"] == (
    "basic_face_amount_times_annual_insured_amount_coefficient"
)
assert entries["cancer-robotic-surgery-benefit"]["basis"] == "face_amount"
assert entries["cancer-robotic-surgery-benefit"]["rate_percent"] == 2.5
assert all(entry["source"] == "terms" for entry in entries.values())
assert (
    parse_taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health(
        taiwan_interest_whole_life_document(taiwan_yaozuan_chuanshi_product_id, "F")
    )
    is None
)
assert (
    parse_taiwan_yaozuan_chuanshi_usd_whole_life_cancer_health(
        {**taiwan_yaozuan_chuanshi_completed, "product_id": "wrong-product"}
    )
    is None
)

taiwan_lehuo_meili_product_id = "202131MA9B91A23B11Z10000000"
taiwan_lehuo_meili_indexed = taiwan_interest_whole_life_document(
    taiwan_lehuo_meili_product_id
)
taiwan_lehuo_meili_completed = complete_strict_source_document(
    taiwan_lehuo_meili_indexed,
    TII_LIFE_009_ROOT
    / taiwan_lehuo_meili_product_id
    / f"{taiwan_lehuo_meili_product_id}-A.pdf",
)
assert taiwan_lehuo_meili_completed["page_count"] == 20
taiwan_lehuo_meili_schedule = (
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health(
        taiwan_lehuo_meili_completed
    )
)
assert taiwan_lehuo_meili_schedule is not None
integrated = parse_plan_table_with_parser(taiwan_lehuo_meili_completed)
assert integrated is not None
assert integrated[0] == "taiwan-lehuo-meili-usd-whole-life-cancer-health-v1"
assert integrated[1] == taiwan_lehuo_meili_schedule
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_lehuo_meili_completed) is None
assert taiwan_lehuo_meili_schedule["selection_type"] == "face_amount"
assert taiwan_lehuo_meili_schedule["selection_label"] == "基本保險金額"
characteristics = taiwan_lehuo_meili_schedule["version_characteristics"]
assert characteristics["product_family"] == (
    "taiwan-lehuo-meili-usd-whole-life-cancer-health"
)
assert characteristics["terms_revision"] == "114-original"
assert characteristics["filing_number"] == "台壽字第1142320067號"
assert characteristics["currency"] == "USD"
assert characteristics["expected_interest_rate_percent"] == 2.5
assert characteristics["cancer_waiting_days"] == 90
assert characteristics["special_treatment_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total_times_1_06"
)
assert characteristics["special_treatment_lifetime_limit_times"] == 1
assert characteristics["special_treatment_item_count"] == 5
assert characteristics["special_treatment_payment_period_only"] is True
assert characteristics["terminal_benefits_choose_one_rule"] is True
assert characteristics["annual_insured_amount_formula"] == (
    "face_amount_plus_accumulated_paid_up_additions_times_coefficient"
)
assert characteristics["death_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total"
)
assert characteristics["total_disability_benefit_formula"] == (
    "greater_of_annual_insured_amount_reserve_and_premium_total"
)
assert characteristics["maturity_benefit_formula"] == (
    "greater_of_annual_insured_amount_and_premium_total_times_1_06"
)
assert characteristics["premium_component"] == "premium_total_times_1_06"
assert characteristics["premium_multiplier"] == 1.06
assert characteristics["maturity_age"] == 111
entries = {
    entry["id"]: entry
    for entry in taiwan_lehuo_meili_schedule["coverage_entries"]
}
assert set(entries) == {
    "value-sharing-bonus",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "special-treatment-benefit",
    "maturity-benefit",
    "installment-periodic-benefit",
}
assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
assert entries["death-or-funeral-benefit"]["aggregation_rule"] == "choose_one"
assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
assert entries["total-disability-benefit"]["aggregation_rule"] == "choose_one"
assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
assert entries["maturity-benefit"]["aggregation_rule"] == "choose_one"
assert entries["special-treatment-benefit"]["calculation_basis"] == "greater_of"
assert entries["special-treatment-benefit"]["aggregation_rule"] == "choose_one"
assert entries["special-treatment-benefit"]["rate_percent"] == 100
assert entries["special-treatment-benefit"]["unit_key"] == "annual_insured_amount"
assert "90日" in " ".join(entries["special-treatment-benefit"]["conditions"])
assert "僅給付其中一項" in " ".join(
    entries["special-treatment-benefit"]["conditions"]
)
assert all(entry["source"] == "terms" for entry in entries.values())
assert all(entry.get("conditions") for entry in entries.values())
assert (
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health(
        taiwan_interest_whole_life_document(taiwan_lehuo_meili_product_id, "F")
    )
    is None
)
assert (
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health(
        {**taiwan_lehuo_meili_completed, "product_id": "wrong-product"}
    )
    is None
)
assert (
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health(
        {
            **taiwan_lehuo_meili_completed,
            "text": taiwan_lehuo_meili_completed["text"].replace(
                "年繳應繳保險費總和的 1.06 倍",
                "年繳應繳保險費總和的 1.10 倍",
            ),
        }
    )
    is None
)
assert (
    parse_taiwan_lehuo_meili_usd_whole_life_cancer_health(
        {
            **taiwan_lehuo_meili_completed,
            "text": taiwan_lehuo_meili_completed["text"]
            + "癌症特定機械手臂微創切除手術醫療保險金",
        }
    )
    is None
)

taiwan_longai_funeral_product_id = "202131MZ2A40B23A12Z10000000"
taiwan_longai_funeral_indexed = taiwan_interest_whole_life_document(
    taiwan_longai_funeral_product_id
)
taiwan_longai_funeral_completed = complete_strict_source_document(
    taiwan_longai_funeral_indexed,
    TII_LIFE_009_ROOT
    / taiwan_longai_funeral_product_id
    / f"{taiwan_longai_funeral_product_id}-A.pdf",
)
assert taiwan_longai_funeral_completed["page_count"] == 16
taiwan_longai_funeral_schedule = (
    parse_taiwan_longai_funeral_service_whole_life_fixed(
        taiwan_longai_funeral_completed
    )
)
assert taiwan_longai_funeral_schedule is not None
integrated = parse_plan_table_with_parser(taiwan_longai_funeral_completed)
assert integrated is not None
assert integrated[0] == "taiwan-longai-funeral-service-whole-life-fixed-v1"
assert integrated[1] == taiwan_longai_funeral_schedule
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_longai_funeral_completed) is None
assert taiwan_longai_funeral_schedule["selection_type"] == "fixed"
assert taiwan_longai_funeral_schedule["input_mode"] == "fixed"
assert taiwan_longai_funeral_schedule["selection_label"] == "保險金額"
characteristics = taiwan_longai_funeral_schedule["version_characteristics"]
assert characteristics["product_family"] == "taiwan-longai-funeral-service-whole-life"
assert characteristics["terms_revision"] == "115-original"
assert characteristics["filing_number"] == "台壽字第1152320048號"
assert characteristics["currency"] == "TWD"
assert characteristics["fixed_face_amount"] == 240_000
assert characteristics["annual_insured_amount_formula"] == (
    "annual_premium_total_times_1_06"
)
assert characteristics["service_provider"] == "龍巖股份有限公司"
assert characteristics["service_option_count"] == 2
assert characteristics["funeral_service_amount"] == 240_000
assert characteristics["funeral_service_from_policy_year"] == 3
assert characteristics["service_lifetime_limit_times"] == 1
assert characteristics["cash_conversion_allowed"] is False
assert characteristics["non_attributable_unavailable_cash_rate_percent"] == 100
assert characteristics["attributable_unavailable_cash_rate_percent"] == 110
assert characteristics["first_two_policy_year_death_premium_multiplier"] == 1.06
assert characteristics["death_after_third_policy_year_cash_amount"] == 240_000
assert characteristics["accidental_death_amount"] == 100_000
assert characteristics["accidental_death_max_age"] == 85
assert characteristics["accident_claim_days"] == 180
assert characteristics["maturity_age"] == 111
assert characteristics["premium_waiver_available"] is True
assert characteristics["premium_waiver_disability_grade_min"] == 1
assert characteristics["premium_waiver_disability_grade_max"] == 6
assert characteristics["funeral_benefit_limit_rule"] is True
entries = {
    entry["id"]: entry
    for entry in taiwan_longai_funeral_schedule["coverage_entries"]
}
assert set(entries) == {
    "funeral-service-benefit",
    "death-first-two-policy-years",
    "death-after-third-policy-year-service-exception",
    "non-attributable-funeral-service-unavailable-cash",
    "company-fault-funeral-service-unavailable-cash",
    "accidental-death-before-85",
    "maturity-benefit",
    "premium-waiver",
}
assert entries["funeral-service-benefit"]["amount"] == 240_000
assert entries["funeral-service-benefit"]["calculation_basis"] == "fixed_amount"
assert entries["funeral-service-benefit"]["aggregation_rule"] == "choose_one"
assert "台灣本島" in " ".join(entries["funeral-service-benefit"]["conditions"])
assert entries["death-first-two-policy-years"]["rate_percent"] == 106
assert entries["death-first-two-policy-years"]["unit_key"] == "annual_premium_total"
assert entries["death-after-third-policy-year-service-exception"]["amount"] == 240_000
assert entries["non-attributable-funeral-service-unavailable-cash"]["amount"] == 240_000
assert entries["company-fault-funeral-service-unavailable-cash"]["amount"] == 264_000
assert entries["accidental-death-before-85"]["amount"] == 100_000
assert entries["accidental-death-before-85"]["aggregation_rule"] == "conditional_additive"
assert entries["maturity-benefit"]["amount"] == 240_000
assert entries["premium-waiver"]["calculation_basis"] == "unknown"
assert all(entry["source"] == "terms" for entry in entries.values())
assert all(entry.get("conditions") for entry in entries.values())
assert (
    parse_taiwan_longai_funeral_service_whole_life_fixed(
        taiwan_interest_whole_life_document(taiwan_longai_funeral_product_id, "F")
    )
    is None
)
assert (
    parse_taiwan_longai_funeral_service_whole_life_fixed(
        {**taiwan_longai_funeral_completed, "product_id": "wrong-product"}
    )
    is None
)
assert (
    parse_taiwan_longai_funeral_service_whole_life_fixed(
        {
            **taiwan_longai_funeral_completed,
            "text": taiwan_longai_funeral_completed["text"].replace(
                "新臺幣 24 萬元",
                "新臺幣 25 萬元",
            ),
        }
    )
    is None
)
assert (
    parse_taiwan_longai_funeral_service_whole_life_fixed(
        {
            **taiwan_longai_funeral_completed,
            "text": taiwan_longai_funeral_completed["text"].replace(
                "第三保單年度(含)以後身故",
                "第四保單年度(含)以後身故",
            ),
        }
    )
    is None
)

taiwan_longzaitian_funeral_product_id = "202131RZ1A73023A12Z10000000"
taiwan_longzaitian_funeral_indexed = taiwan_interest_whole_life_document(
    taiwan_longzaitian_funeral_product_id
)
taiwan_longzaitian_funeral_completed = complete_strict_source_document(
    taiwan_longzaitian_funeral_indexed,
    TII_LIFE_009_ROOT
    / taiwan_longzaitian_funeral_product_id
    / f"{taiwan_longzaitian_funeral_product_id}-A.pdf",
)
assert taiwan_longzaitian_funeral_completed["page_count"] == 10
taiwan_longzaitian_funeral_schedule = (
    parse_taiwan_longzaitian_funeral_service_rider_fixed(
        taiwan_longzaitian_funeral_completed
    )
)
assert taiwan_longzaitian_funeral_schedule is not None
integrated = parse_plan_table_with_parser(taiwan_longzaitian_funeral_completed)
assert integrated is not None
assert integrated[0] == "taiwan-longzaitian-funeral-service-rider-fixed-v1"
assert integrated[1] == taiwan_longzaitian_funeral_schedule
assert parse_taiwan_funeral_service_rider_fixed(taiwan_longzaitian_funeral_completed) is None
assert parse_taiwan_interest_rate_whole_life_formula(taiwan_longzaitian_funeral_completed) is None
assert taiwan_longzaitian_funeral_schedule["selection_type"] == "fixed"
assert taiwan_longzaitian_funeral_schedule["input_mode"] == "fixed"
characteristics = taiwan_longzaitian_funeral_schedule["version_characteristics"]
assert characteristics["product_family"] == "taiwan-longzaitian-funeral-service-rider"
assert characteristics["terms_revision"] == "108-original"
assert characteristics["filing_date"] == "108-03-15"
assert characteristics["service_option_count"] == 2
assert characteristics["service_amount"] == 210_000
assert characteristics["funeral_service_from_policy_year"] == 4
assert characteristics["service_scope_taiwan_main_island"] is True
assert characteristics["service_lifetime_limit_times"] == 1
assert characteristics["cash_conversion_allowed"] is False
assert characteristics["non_attributable_unavailable_cash_rate_percent"] == 100
assert characteristics["attributable_unavailable_cash_rate_percent"] == 110
assert characteristics["first_three_policy_year_death_premium_multiplier"] == 1.06
assert characteristics["maturity_age"] == 111
assert characteristics["maturity_benefit_amount"] == 210_000
assert characteristics["funeral_benefit_limit_rule"] is True
assert characteristics["reduced_paid_up_excludes_funeral_service"] is True
assert characteristics["fixed_terms_amount"] is True
assert characteristics["non_participating_policy"] is True
assert "accidental_death_amount" not in characteristics
assert "premium_waiver_available" not in characteristics
entries = {
    entry["id"]: entry
    for entry in taiwan_longzaitian_funeral_schedule["coverage_entries"]
}
assert set(entries) == {
    "funeral-service-benefit",
    "death-first-three-policy-years",
    "death-after-fourth-policy-year-service-exception",
    "non-attributable-funeral-service-unavailable-cash",
    "company-fault-funeral-service-unavailable-cash",
    "maturity-age-111-benefit",
    "reduced-paid-up-excludes-funeral-service",
}
assert entries["funeral-service-benefit"]["amount"] == 210_000
assert entries["funeral-service-benefit"]["amount_role"] == "reference"
assert entries["funeral-service-benefit"]["aggregation_rule"] == "choose_one"
assert entries["death-first-three-policy-years"]["rate_percent"] == 106
assert entries["death-first-three-policy-years"]["unit_key"] == "annual_premium_total"
assert entries["death-after-fourth-policy-year-service-exception"]["amount"] == 210_000
assert entries["non-attributable-funeral-service-unavailable-cash"]["amount"] == 210_000
assert entries["company-fault-funeral-service-unavailable-cash"]["amount"] == 231_000
assert entries["maturity-age-111-benefit"]["amount"] == 210_000
assert entries["reduced-paid-up-excludes-funeral-service"].get("amount") is None
assert entries["reduced-paid-up-excludes-funeral-service"]["amount_role"] == "reference"
assert all(entry["source"] == "terms" for entry in entries.values())
assert all(entry.get("conditions") for entry in entries.values())
assert (
    parse_taiwan_longzaitian_funeral_service_rider_fixed(
        {**taiwan_longzaitian_funeral_completed, "file_name": "wrong-file.pdf"}
    )
    is None
)
assert (
    parse_taiwan_longzaitian_funeral_service_rider_fixed(
        {**taiwan_longzaitian_funeral_completed, "product_id": "wrong-product"}
    )
    is None
)

taiwan_interest_endowment_cases = {
    "202121MA1A34A22D11Z10000000": {
        "currency": "AUD",
        "expected_rate": 2.00,
        "policy_period_years": 7,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions",
        "foreign_currency": True,
    },
    "202121MA1A43A22B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.50,
        "policy_period_years": 7,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions",
        "foreign_currency": True,
    },
    "202121MA1A88A22A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.25,
        "policy_period_years": 30,
        "annual_formula": "first_two_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "foreign_currency": False,
    },
}
for product_id, expected in taiwan_interest_endowment_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_endowment_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-endowment-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "基本保險金額" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == expected["currency"]
    assert characteristics["expected_interest_rate_percent"] == expected["expected_rate"]
    assert characteristics["policy_period_years"] == expected["policy_period_years"]
    assert characteristics["annual_insured_amount_formula"] == expected["annual_formula"]
    assert characteristics["maturity_benefit_formula"] == "annual_insured_amount"
    assert characteristics["value_sharing_bonus"] is True
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["foreign_currency_policy"] is expected["foreign_currency"]
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["maturity-benefit"]["name"] == "滿期保險金"
    assert entries["maturity-benefit"]["calculation_basis"] == "percentage_of_base"
    assert "滿期公式類型" in entries["maturity-benefit"]["conditions"][0]
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert all(entry["source"] == "terms" for entry in entries.values())

assert parse_taiwan_interest_rate_endowment_formula(
    taiwan_interest_whole_life_document("202121MA1A34A22D11Z10000000", "F")
) is None

taiwan_interest_specific_disease_cases = {
    "202131MA5B28A23B11Z10000000": "original",
    "202131MA5B28A23B11Z10000001": "114-regulatory-revision",
}
for product_id, expected_revision in taiwan_interest_specific_disease_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_specific_disease_whole_life_formula(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-specific-disease-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "特定傷病" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["currency"] == "USD"
    assert characteristics["expected_interest_rate_percent"] == 2.5
    assert characteristics["value_sharing_bonus"] is True
    assert characteristics["specific_disease_waiting_days"] == 30
    assert characteristics["specific_disease_names"] == [
        "嚴重阿茲海默氏症",
        "嚴重巴金森氏症",
    ]
    assert characteristics["specific_disease_count"] == 2
    assert characteristics["specific_disease_one_time_benefit"] is True
    assert characteristics["specific_disease_disability_exclusive"] is True
    assert characteristics["annual_insured_amount_formula"] == (
        "first_five_policy_years_premium_total_times_1_06_then_"
        "face_plus_accumulated_times_coefficient"
    )
    assert characteristics["specific_disease_benefit_formula"] == (
        "greater_of_annual_insured_amount_reserve_and_premium_total_times_1_06"
    )
    assert characteristics["maturity_benefit_formula"] == (
        "greater_of_annual_insured_amount_and_premium_total_times_1_06"
    )
    assert characteristics["premium_component"] == "premium_total_times_1_06"
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["maturity_age"] == 111
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["minimum_annual_installment_amount"] == 1200
    assert characteristics["minimum_annual_installment_currency"] == "USD"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "specific-disease-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["specific-disease-benefit"]["calculation_basis"] == "greater_of"
    assert entries["specific-disease-benefit"]["aggregation_rule"] == "highest"
    assert "嚴重阿茲海默氏症" in entries["specific-disease-benefit"]["conditions"][0]
    assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
    assert all(entry["source"] == "terms" for entry in entries.values())

assert parse_taiwan_interest_rate_specific_disease_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA5B28A23B11Z10000000", "F")
) is None

taiwan_interest_specific_disease_survival_cases = {
    "202131MA5B29A23B11Z10000000": "original",
    "202131MA5B29A23B11Z10000001": "114-regulatory-revision",
}
for product_id, expected_revision in taiwan_interest_specific_disease_survival_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_specific_disease_survival_whole_life_formula(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "taiwan-interest-rate-specific-disease-survival-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "特定傷病保險金" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["currency"] == "USD"
    assert characteristics["expected_interest_rate_percent"] == 2.5
    assert characteristics["specific_disease_benefit_formula"] == (
        "basic_face_amount_times_5_percent"
    )
    assert characteristics["specific_disease_rate_percent"] == 5
    assert characteristics["specific_disease_one_time_benefit"] is True
    assert characteristics["specific_disease_disability_exclusive"] is False
    assert characteristics["total_disability_benefit_available"] is False
    assert characteristics["annual_insured_amount_formula"] == (
        "first_three_policy_years_premium_total_times_1_06_then_"
        "face_plus_accumulated_times_coefficient"
    )
    assert characteristics["maturity_benefit_formula"] == (
        "greater_of_annual_insured_amount_and_premium_total_times_1_06"
    )
    assert characteristics["premium_component"] == "premium_total_times_1_06"
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["minimum_annual_installment_amount"] == 1200
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert "total-disability-benefit" not in entries
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "specific-disease-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    specific_entry = entries["specific-disease-benefit"]
    assert specific_entry["calculation_basis"] == "percentage_of_base"
    assert specific_entry["basis"] == "face_amount"
    assert specific_entry["rate_percent"] == 5
    assert specific_entry["unit_key"] == "basic_face_amount"
    assert "嚴重巴金森氏症" in specific_entry["conditions"][0]
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
    assert all(entry["source"] == "terms" for entry in entries.values())

assert parse_taiwan_interest_rate_specific_disease_survival_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA5B29A23B11Z10000000", "F")
) is None

taiwan_usd_endowment_cases = {
    "202121MZ1A30B22B11Z10000000": {
        "label": "基本保險金額",
        "period": 10,
        "formula": (
            "single_premium_face_amount_times_coefficient_or_"
            "two_year_first_year_premium_total_then_face_amount_times_coefficient"
        ),
        "maturity": "annual_insured_amount",
        "revision": "original",
        "coefficient_table_required": True,
    },
    "202121MZ1A77A22B11Z10000000": {
        "label": "保險金額",
        "period": 7,
        "formula": "face_amount",
        "maturity": "face_amount",
        "revision": "original",
        "coefficient_table_required": False,
    },
    "202121MZ1A77A22B11Z10000001": {
        "label": "保險金額",
        "period": 7,
        "formula": "face_amount",
        "maturity": "face_amount",
        "revision": "first-partial-revision",
        "coefficient_table_required": False,
    },
}
for product_id, expected in taiwan_usd_endowment_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_usd_endowment_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-usd-endowment-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == expected["label"]
    assert expected["label"] in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == "USD"
    assert characteristics["value_sharing_bonus"] is False
    assert characteristics["policy_period_years"] == expected["period"]
    assert characteristics["face_amount_label"] == expected["label"]
    assert characteristics["annual_insured_amount_formula"] == expected["formula"]
    assert characteristics["maturity_benefit_formula"] == expected["maturity"]
    assert characteristics["terms_revision"] == expected["revision"]
    assert characteristics["premium_component"] == "premium_total"
    assert characteristics["premium_multiplier"] == 1.0
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["minimum_annual_installment_amount"] == 1200
    assert characteristics["minimum_annual_installment_currency"] == "USD"
    assert characteristics["coefficient_table_required"] is expected[
        "coefficient_table_required"
    ]
    assert characteristics["payment_period_required"] is expected[
        "coefficient_table_required"
    ]
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["aggregation_rule"] == "highest"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["name"] == "滿期保險金"
    assert entries["maturity-benefit"]["calculation_basis"] == "percentage_of_base"
    assert all(entry["source"] == "terms" for entry in entries.values())

assert parse_taiwan_usd_endowment_formula(
    taiwan_interest_whole_life_document("202121MZ1A30B22B11Z10000000", "F")
) is None

taiwan_interest_accident_cases = {
    "202131MA2A87923A11Z10000000": {
        "product_family": "chuan-cheng-fu-man",
        "terms_revision": "original",
        "age_16_special": True,
        "accident_age_16_wording": True,
        "minor_death_rule": True,
    },
    "202131MA2A87923A11Z10000001": {
        "product_family": "chuan-cheng-fu-man",
        "terms_revision": "first-partial-revision",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
    "202131MA2A88623A11Z10000000": {
        "product_family": "chuan-cheng-fu-li",
        "terms_revision": "original",
        "age_16_special": True,
        "accident_age_16_wording": True,
        "minor_death_rule": True,
    },
    "202131MA2A88623A11Z10000001": {
        "product_family": "chuan-cheng-fu-li",
        "terms_revision": "first-partial-revision",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
    "202131MA2A88623A11Z10000002": {
        "product_family": "chuan-cheng-fu-li",
        "terms_revision": "second-partial-revision",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
}
for product_id, expected in taiwan_interest_accident_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_accident_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-accident-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == "TWD"
    assert characteristics["expected_interest_rate_percent"] == 1.85
    assert characteristics["product_family"] == expected["product_family"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert (
        characteristics["age_16_value_sharing_special_rule"]
        is expected["age_16_special"]
    )
    assert (
        characteristics["accidental_death_min_age_16_wording"]
        is expected["accident_age_16_wording"]
    )
    assert (
        characteristics["minor_death_under_15_funeral_benefit_rule"]
        is expected["minor_death_rule"]
    )
    assert characteristics["annual_insured_amount_formula"] == (
        "face_amount_plus_accumulated_paid_up_additions"
    )
    assert characteristics["death_benefit_formula"] == (
        "greater_of_annual_insured_amount_and_annual_premium_total"
    )
    assert characteristics["accidental_death_benefit_formula"] == (
        "death_benefit_plus_annual_insured_amount"
    )
    assert characteristics["maturity_benefit_formula"] == (
        "greater_of_annual_insured_amount_and_annual_premium_total_at_age_110"
    )
    assert characteristics["installment_period_min_years"] == 5
    assert characteristics["installment_period_max_years"] == 30
    assert characteristics["minimum_annual_installment_amount"] == 36_000
    assert characteristics["premium_waiver_disability_grade_min"] == 1
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["accident_claim_days"] == 180
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "injury-rider-surrender-value-refund-on-non-accident-death",
        "accidental-death-additional-benefit",
        "maturity-age-111-benefit",
        "premium-waiver-disability-grade-one-to-six",
        "installment-periodic-benefit",
        "installment-low-annual-payment-lump-sum",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["accidental-death-additional-benefit"]["aggregation_rule"]
        == "conditional_additive"
    )
    assert entries["accidental-death-additional-benefit"]["rate_percent"] == 100
    assert entries["maturity-age-111-benefit"]["calculation_basis"] == "greater_of"
    assert entries["premium-waiver-disability-grade-one-to-six"]["amount_role"] == (
        "reference"
    )
    all_conditions = " ".join(
        condition
        for entry in entries.values()
        for condition in entry.get("conditions", [])
    )
    assert ("保險年齡未滿 16 歲" in all_conditions) is expected[
        "accident_age_16_wording"
    ]
    assert ("16 歲前，增值回饋分享金於繳費期間採抵繳" in all_conditions) is (
        expected["age_16_special"]
    )
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert parse_taiwan_interest_rate_accident_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA2A87923A11Z10000000", "F")
) is None
wrong_taiwan_interest_accident_document = {
    **taiwan_interest_whole_life_document("202131MA2A87923A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert parse_taiwan_interest_rate_accident_whole_life_formula(
    wrong_taiwan_interest_accident_document
) is None
taiwan_interest_accident_indexed = taiwan_interest_whole_life_document(
    "202131MA2A87923A11Z10000000"
)
taiwan_interest_accident_completed = complete_strict_source_document(
    {
        **taiwan_interest_accident_indexed,
        "text": taiwan_interest_accident_indexed["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202131MA2A87923A11Z10000000"
    / "202131MA2A87923A11Z10000000-A.pdf",
)
assert taiwan_interest_accident_completed["page_count"] == 12
assert (
    parse_taiwan_interest_rate_accident_whole_life_formula(
        taiwan_interest_accident_completed
    )
    is not None
)

taiwan_chuanshi_fuli_cases = {
    "202131MA2A81823A11Z10000000": {
        "terms_revision": "original",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
    "202131MA2A81823A11Z10000001": {
        "terms_revision": "first-partial-revision",
        "age_16_special": True,
        "accident_age_16_wording": True,
        "minor_death_rule": True,
    },
    "202131MA2A81823A11Z10000002": {
        "terms_revision": "second-partial-revision",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
    "202131MA2A81823A11Z10000003": {
        "terms_revision": "third-regulatory-revision",
        "age_16_special": False,
        "accident_age_16_wording": False,
        "minor_death_rule": False,
    },
}
for product_id, expected in taiwan_chuanshi_fuli_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_chuanshi_fuli_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-chuanshi-fuli-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == "TWD"
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["expected_interest_rate_schedule"] == {
        "two_year_payment_period_percent": 0.75,
        "six_year_payment_period_percent": 1.50,
    }
    assert characteristics["payment_period_options"] == [2, 6]
    assert (
        characteristics["age_16_value_sharing_special_rule"]
        is expected["age_16_special"]
    )
    assert (
        characteristics["accidental_death_min_age_16_wording"]
        is expected["accident_age_16_wording"]
    )
    assert (
        characteristics["minor_death_under_15_funeral_benefit_rule"]
        is expected["minor_death_rule"]
    )
    assert characteristics["annual_insured_amount_formula"] == (
        "two_year_first_two_or_six_year_first_five_premium_total_times_1_02_then_face_plus_accumulated_times_coefficient"
    )
    assert characteristics["death_benefit_formula"] == (
        "greater_of_annual_insured_amount_reserve_ratio_and_premium_total_times_1_02"
    )
    assert characteristics["total_disability_benefit_formula"] == (
        "greater_of_annual_insured_amount_reserve_ratio_and_premium_total_times_1_02"
    )
    assert characteristics["accidental_death_rate_percent"] == 50
    assert characteristics["total_disability_living_assistance_rate_percent"] == 10
    assert characteristics["total_disability_living_assistance_max_payments"] == 10
    assert characteristics["premium_waiver_disability_grade_min"] == 2
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["premium_multiplier"] == 1.02
    assert characteristics["coefficient_table_required"] is True
    assert len(characteristics["policy_reserve_ratio_schedule"]) == 7
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "injury-rider-surrender-value-refund-on-non-accident-death",
        "accidental-death-additional-benefit",
        "total-disability-benefit",
        "total-disability-injury-rider-surrender-value-refund",
        "total-disability-living-assistance-benefit",
        "maturity-age-111-benefit",
        "premium-waiver-disability-grade-two-to-six",
        "installment-periodic-benefit",
        "installment-low-annual-payment-lump-sum",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["multiplier"] == 1.02
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["multiplier"] == 1.02
    assert entries["accidental-death-additional-benefit"]["rate_percent"] == 50
    assert (
        entries["accidental-death-additional-benefit"]["aggregation_rule"]
        == "conditional_additive"
    )
    assert entries["total-disability-living-assistance-benefit"]["rate_percent"] == 10
    assert (
        entries["total-disability-living-assistance-benefit"]["aggregation_rule"]
        == "cumulative_cap"
    )
    assert entries["maturity-age-111-benefit"]["multiplier"] == 1.02
    all_conditions = " ".join(
        condition
        for entry in entries.values()
        for condition in entry.get("conditions", [])
    )
    assert ("保險年齡未滿 16 歲" in all_conditions) is expected[
        "accident_age_16_wording"
    ]
    assert ("16 歲前，增值回饋分享金於繳費期間採抵繳" in all_conditions) is (
        expected["age_16_special"]
    )
    assert "最高給付次數以 10 次為限" in all_conditions
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert parse_taiwan_chuanshi_fuli_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA2A81823A11Z10000000", "F")
) is None
wrong_taiwan_chuanshi_fuli_document = {
    **taiwan_interest_whole_life_document("202131MA2A81823A11Z10000000"),
    "product_id": "wrong-product",
    "file_name": "wrong-product-A.pdf",
}
assert parse_taiwan_chuanshi_fuli_whole_life_formula(
    wrong_taiwan_chuanshi_fuli_document
) is None
taiwan_chuanshi_fuli_indexed = taiwan_interest_whole_life_document(
    "202131MA2A81823A11Z10000000"
)
taiwan_chuanshi_fuli_completed = complete_strict_source_document(
    {
        **taiwan_chuanshi_fuli_indexed,
        "text": taiwan_chuanshi_fuli_indexed["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202131MA2A81823A11Z10000000"
    / "202131MA2A81823A11Z10000000-A.pdf",
)
assert taiwan_chuanshi_fuli_completed["page_count"] == 14
assert (
    parse_taiwan_chuanshi_fuli_whole_life_formula(
        taiwan_chuanshi_fuli_completed
    )
    is not None
)

taiwan_survival_interest_cases = {
    "202131MA1A03B23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
        "premium_waiver": False,
    },
    "202131MA1A05A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.25,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
    },
    "202131MA1A22A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.50,
        "annual_formula": "first_three_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
        "death_calculation": "greater_of",
        "maturity_calculation": "greater_of",
    },
    "202131MA1A22A23B11Z10000001": {
        "currency": "USD",
        "expected_rate": 2.50,
        "annual_formula": "first_three_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
        "death_calculation": "greater_of",
        "maturity_calculation": "greater_of",
    },
    "202131MA1A58B23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.50,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
        "waiver_condition": "第一級至第六級失能",
        "installment_condition": "美元 1,200 元",
    },
    "202131MA1A90A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.50,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
        "waiver_condition": "第一級至第六級失能",
        "installment_condition": "美元 1,200 元",
    },
    "202131MA1A82923B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_three_policy_years_premium_total_times_1_1_then_face_plus_accumulated",
        "premium_component": "premium_total_times_1_1",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_1",
        "premium_waiver": True,
    },
    "202131MA1A91823B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.00,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions",
        "premium_component": "none",
        "maturity_formula": "annual_insured_amount",
        "premium_waiver": True,
        "death_calculation": "percentage_of_base",
        "maturity_calculation": "percentage_of_base",
    },
    "202131MA1A94023B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "premium_period_6_10_20_front_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
    },
    "202131MA1A94223B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_three_policy_years_premium_total_times_1_1_then_face_plus_accumulated",
        "premium_component": "premium_total_times_1_1",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_1",
        "premium_waiver": True,
        "death_calculation": "greater_of",
        "maturity_calculation": "greater_of",
    },
    "202131MA1A94523B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
        "premium_waiver": True,
        "waiver_condition": "第一級至第九級失能",
        "installment_condition": "美元 200 元",
    },
}
taiwan_survival_interest_additional_product_ids = [
    "202131MA1A01A23B11Z10000000",
    "202131MA1A01A23B11Z10000001",
    "202131MA1A24A23B11Z10000000",
    "202131MA1A24A23B11Z10000001",
    "202131MA1A75A23B11E10000000",
    "202131MA1A97323B11Z10000000",
    "202131MA1A97323B11Z10000001",
    "202131MA1A97423B11Z10000000",
    "202131MA1A97423B11Z10000001",
    "202131MA1A97423B11Z10000002",
    "202131MA1A97923B11Z10000000",
    "202131MA1A97923B11Z10000001",
    "202131MA1A98123A11Z10000000",
    "202131MA1A98123A11Z10000001",
    "202131MA1A98223A11Z10000000",
    "202131MA1A98223A11Z10000001",
]
for product_id, expected in taiwan_survival_interest_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_survival_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-survival-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == expected["currency"]
    assert characteristics["expected_interest_rate_percent"] == expected["expected_rate"]
    assert characteristics["annual_insured_amount_formula"] == expected["annual_formula"]
    assert characteristics["premium_component"] == expected["premium_component"]
    assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]
    assert characteristics["total_disability_benefit_formula"] == "not_applicable"
    assert characteristics["premium_waiver_available"] is expected["premium_waiver"]
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert "total-disability-benefit" not in entries
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "maturity-benefit",
    }
    assert ("premium-waiver" in entries) is expected["premium_waiver"]
    if "waiver_condition" in expected:
        assert expected["waiver_condition"] in " ".join(
            entries["premium-waiver"]["conditions"]
        )
    if "installment_condition" in expected:
        assert expected["installment_condition"] in " ".join(
            entries["installment-periodic-benefit"]["conditions"]
        )
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == expected.get(
        "death_calculation", "greater_of"
    )
    assert entries["maturity-benefit"]["calculation_basis"] == expected.get(
        "maturity_calculation", "greater_of"
    )
    assert all(entry["source"] == "terms" for entry in entries.values())

for product_id in taiwan_survival_interest_additional_product_ids:
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_survival_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-survival-whole-life-formula-v1"
    assert integrated[1] == schedule
    characteristics = schedule["version_characteristics"]
    assert characteristics["total_disability_benefit_formula"] == "not_applicable"
    assert characteristics["premium_waiver_available"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert "total-disability-benefit" not in entries
    assert set(entries) >= {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "maturity-benefit",
        "premium-waiver",
        "installment-periodic-benefit",
        "terminal-illness-advance-benefit",
    }
    terminal_entry = entries["terminal-illness-advance-benefit"]
    assert terminal_entry["calculation_basis"] == "percentage_of_base"
    assert terminal_entry["rate_percent"] == 50
    assert terminal_entry["unit_key"] == "death_or_funeral_benefit"

assert parse_taiwan_interest_rate_survival_whole_life_formula(
    taiwan_interest_whole_life_document("202131MA1A03B23B11Z10000000", "F")
) is None

taiwan_participating_product_ids = [
    "202131MZ1A09B23B11Z10000000",
    "202131MZ1A09B23B11Z10000001",
    "202131MZ1A17B23B11Z10000000",
    "202131MZ1A18B23B11Z10000000",
    "202131MZ1A21B23B11Z10000000",
    "202131MZ1A23B23B11Z10000000",
    "202131MZ1A67A23B11Z10000000",
    "202131MZ1A67A23B11Z10000001",
    "202131MZ1A83A23A11Z10000000",
    "202131MZ1A83A23A11Z10000001",
]
taiwan_participating_cases = {
    "202131MZ1A09B23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 6,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
    },
    "202131MZ1A17B23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 4,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
    },
    "202131MZ1A18B23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 3,
        "annual_formula": "first_two_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
    },
    "202131MZ1A21B23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 3,
        "annual_formula": "first_policy_year_premium_total_then_face_plus_accumulated",
        "premium_component": "premium_total",
        "maturity_formula": "annual_insured_amount_times_coefficient_table",
    },
    "202131MZ1A23B23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 4,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
    },
    "202131MZ1A67A23B11Z10000000": {
        "currency": "USD",
        "dividend_start": 4,
        "annual_formula": "face_amount_plus_accumulated_paid_up_additions_times_coefficient",
        "premium_component": "premium_total_times_1_06",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total_times_1_06",
    },
    "202131MZ1A83A23A11Z10000000": {
        "currency": "TWD",
        "dividend_start": 3,
        "annual_formula": "first_three_policy_years_premium_total_then_face_plus_accumulated_times_coefficient",
        "premium_component": "premium_total",
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_total",
    },
}
for product_id in taiwan_participating_product_ids:
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_participating_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-participating-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "保單價值準備金" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["maturity_age"] == 111
    assert characteristics["participating_policy"] is True
    assert characteristics["policy_dividend_available"] is True
    assert characteristics["policy_dividend_guaranteed"] is False
    assert characteristics["terminal_policy_dividend_available"] is True
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["terminal_illness_advance_available"] is False
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "policy-dividend",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert "premium-waiver" not in entries
    assert "terminal-illness-advance-benefit" not in entries
    assert entries["policy-dividend"]["amount_role"] == "reference"
    assert entries["policy-dividend"]["calculation_basis"] == "unknown"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())
    if product_id in taiwan_participating_cases:
        expected = taiwan_participating_cases[product_id]
        assert characteristics["currency"] == expected["currency"]
        assert (
            characteristics["annual_policy_dividend_start_year"]
            == expected["dividend_start"]
        )
        assert characteristics["annual_insured_amount_formula"] == expected["annual_formula"]
        assert characteristics["premium_component"] == expected["premium_component"]
        assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]

assert parse_taiwan_participating_whole_life_formula(
    taiwan_interest_whole_life_document("202131MZ1A09B23B11Z10000000", "F")
) is None

taiwan_participating_return_cases = {
    "202121MZ1A81A23A11Z10000000": "roc-114-05-01",
    "202121MZ1A81A23A11Z10000001": "roc-115-01-01-regulatory-revision",
}
for product_id, expected_revision in taiwan_participating_return_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_participating_return_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-participating-return-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    assert "繳費年期" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["currency"] == "TWD"
    assert characteristics["participating_policy"] is True
    assert characteristics["policy_dividend_available"] is True
    assert characteristics["policy_dividend_guaranteed"] is False
    assert characteristics["annual_policy_dividend_start_year"] == 2
    assert characteristics["terminal_policy_dividend_available"] is True
    assert characteristics["terminal_policy_dividend_start_year"] == 6
    assert (
        characteristics["annual_insured_amount_formula"]
        == "premium_period_premium_total_times_1_04_minus_face_amount_coeff_then_face_amount"
    )
    assert (
        characteristics["survival_benefit_formula"]
        == "1_32_1_61_1_05_1_25_step_schedule_on_previous_face_amount"
    )
    assert characteristics["survival_rate_min_percent"] == 1.05
    assert characteristics["survival_rate_max_percent"] == 1.61
    assert characteristics["monthly_survival_benefit_available"] is False
    assert (
        characteristics["death_benefit_formula"]
        == "greater_of_annual_insured_amount_reserve_and_premium_component"
    )
    assert (
        characteristics["total_disability_benefit_formula"]
        == "greater_of_annual_insured_amount_reserve_and_premium_component"
    )
    assert characteristics["maturity_benefit_formula"] == "age_99_face_amount"
    assert (
        characteristics["premium_component"]
        == "premium_total_times_1_04_minus_face_amount_times_coefficient"
    )
    assert characteristics["premium_multiplier"] == 1.04
    assert characteristics["maturity_age"] == 100
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["terminal_illness_advance_available"] is False
    assert characteristics["policy_face_amount_required"] is True
    assert characteristics["premium_total_required"] is True
    assert characteristics["coefficient_table_required"] is True
    assert characteristics["payment_period_required"] is True
    assert characteristics["foreign_currency_policy"] is False
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "policy-dividend",
        "survival-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["policy-dividend"]["amount_role"] == "reference"
    assert entries["survival-benefit"]["calculation_basis"] == "percentage_of_base"
    assert entries["survival-benefit"]["rate_min_percent"] == 1.05
    assert entries["survival-benefit"]["rate_max_percent"] == 1.61
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["unit_key"] == "face_amount_at_age_99"
    assert entries["maturity-benefit"]["calculation_basis"] == "percentage_of_base"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

assert parse_taiwan_participating_return_whole_life_formula(
    taiwan_interest_whole_life_document("202121MZ1A81A23A11Z10000000", "F")
) is None
taiwan_participating_return_completed = complete_strict_source_document(
    {
        **taiwan_interest_whole_life_document("202121MZ1A81A23A11Z10000000"),
        "text": taiwan_interest_whole_life_document(
            "202121MZ1A81A23A11Z10000000"
        )["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202121MZ1A81A23A11Z10000000"
    / "202121MZ1A81A23A11Z10000000-A.pdf",
)
assert taiwan_participating_return_completed["page_count"] == 11
assert (
    parse_taiwan_participating_return_whole_life_formula(
        taiwan_participating_return_completed
    )
    is not None
)

taiwan_term_life_cases = {
    "202131MZ1A29B22A11Z10000000": {
        "parser_id": "taiwan-term-life-formula-v1",
        "selection_label": "基本保險金額",
        "terms_revision": "roc-115-03-09",
        "currency": "TWD",
        "product_form": "level_term_life",
        "annual_formula": "basic_face_amount_times_appendix_2_coefficient",
        "annual_schedule": "level_1_0_by_policy_duration",
        "death_formula": "greater_of_annual_insured_amount_and_premium_total",
        "calculation_basis": "greater_of",
        "premium_total_required": True,
        "foreign_currency_policy": False,
        "exchange_rate_risk_disclosure": False,
        "installment_min_annual_payment": 36_000,
        "installment_min_annual_payment_currency": "TWD",
        "page_count": 9,
    },
    "202131RZ1A86022B11Z10000000": {
        "parser_id": "taiwan-term-life-formula-v1",
        "selection_label": "保險金額",
        "terms_revision": "roc-110-03-22",
        "currency": "USD",
        "product_form": "usd_decreasing_term_life_rider",
        "annual_formula": "face_amount_times_appendix_2_coefficient",
        "annual_schedule": "age_and_term_decreasing_coefficient_table",
        "death_formula": "annual_insured_amount",
        "calculation_basis": "percentage_of_base",
        "premium_total_required": False,
        "foreign_currency_policy": True,
        "exchange_rate_risk_disclosure": True,
        "installment_min_annual_payment": 1_200,
        "installment_min_annual_payment_currency": "USD",
        "page_count": 10,
    },
}
for product_id, expected in taiwan_term_life_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_term_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == expected["parser_id"]
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == expected["selection_label"]
    assert "附表係數" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["currency"] == expected["currency"]
    assert characteristics["product_form"] == expected["product_form"]
    assert characteristics["participating_policy"] is False
    assert (
        characteristics["annual_insured_amount_formula"]
        == expected["annual_formula"]
    )
    assert (
        characteristics["annual_insured_amount_schedule"]
        == expected["annual_schedule"]
    )
    assert characteristics["death_benefit_formula"] == expected["death_formula"]
    assert (
        characteristics["total_disability_benefit_formula"]
        == expected["death_formula"]
    )
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["policy_face_amount_required"] is True
    assert (
        characteristics["premium_total_required"]
        is expected["premium_total_required"]
    )
    assert characteristics["coefficient_table_required"] is True
    assert characteristics["payment_period_required"] is True
    assert characteristics["insurance_period_required"] is True
    assert (
        characteristics["foreign_currency_policy"]
        is expected["foreign_currency_policy"]
    )
    assert (
        characteristics["exchange_rate_risk_disclosure"]
        is expected["exchange_rate_risk_disclosure"]
    )
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert (
        characteristics["installment_min_annual_payment"]
        == expected["installment_min_annual_payment"]
    )
    assert (
        characteristics["installment_min_annual_payment_currency"]
        == expected["installment_min_annual_payment_currency"]
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "installment-periodic-benefit",
    }
    assert (
        entries["death-or-funeral-benefit"]["calculation_basis"]
        == expected["calculation_basis"]
    )
    assert (
        entries["total-disability-benefit"]["calculation_basis"]
        == expected["calculation_basis"]
    )
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert entries["installment-periodic-benefit"]["amount_role"] == "reference"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())
    completed = complete_strict_source_document(
        {**document, "text": document["text"][:1500]},
        TII_LIFE_009_ROOT / product_id / f"{product_id}-A.pdf",
    )
    assert completed["page_count"] == expected["page_count"]
    assert parse_taiwan_term_life_formula(completed) is not None

assert parse_taiwan_term_life_formula(
    taiwan_interest_whole_life_document("202131MZ1A29B22A11Z10000000", "F")
) is None

taiwan_simple_term_life_document = taiwan_interest_whole_life_document(
    "202131MZ1A98A22A11Z10000000"
)
taiwan_simple_term_life_schedule = parse_taiwan_simple_term_life_formula(
    taiwan_simple_term_life_document
)
assert taiwan_simple_term_life_schedule is not None
taiwan_simple_term_life_integrated = parse_plan_table_with_parser(
    taiwan_simple_term_life_document
)
assert taiwan_simple_term_life_integrated is not None
assert taiwan_simple_term_life_integrated[0] == "taiwan-simple-term-life-formula-v1"
assert taiwan_simple_term_life_integrated[1] == taiwan_simple_term_life_schedule
assert taiwan_simple_term_life_schedule["selection_label"] == "保險金額"
taiwan_simple_term_life_characteristics = taiwan_simple_term_life_schedule[
    "version_characteristics"
]
assert taiwan_simple_term_life_characteristics["terms_revision"] == "roc-114-08-08"
assert taiwan_simple_term_life_characteristics["filing_number"] == "1142320086"
assert taiwan_simple_term_life_characteristics["product_form"] == "simple_level_term_life"
assert (
    taiwan_simple_term_life_characteristics["death_benefit_formula"]
    == "face_amount_plus_prorated_unearned_premium"
)
assert (
    taiwan_simple_term_life_characteristics["total_disability_benefit_formula"]
    == "face_amount_plus_prorated_unearned_premium"
)
assert taiwan_simple_term_life_characteristics["installment_benefit_available"] is False
assert taiwan_simple_term_life_characteristics["coefficient_table_required"] is False
assert taiwan_simple_term_life_characteristics["surrender_value_available"] is True
taiwan_simple_term_life_entries = {
    entry["id"]: entry for entry in taiwan_simple_term_life_schedule["coverage_entries"]
}
assert set(taiwan_simple_term_life_entries) == {
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "surrender-value-reference",
}
assert (
    taiwan_simple_term_life_entries["death-or-funeral-benefit"]["calculation_basis"]
    == "percentage_of_base"
)
assert (
    taiwan_simple_term_life_entries["total-disability-benefit"]["calculation_basis"]
    == "percentage_of_base"
)
assert (
    taiwan_simple_term_life_entries["surrender-value-reference"]["amount_role"]
    == "reference"
)

taiwan_usd_no_disability_cases = {
    "202131MZ1A43B23B11Z10000000": {
        "maturity_label": "祝壽保險金",
        "participating_policy": True,
        "policy_period_years": None,
        "maturity_age": 111,
        "entry_ids": {
            "death-or-funeral-benefit",
            "maturity-benefit",
            "installment-periodic-benefit",
            "terminal-policy-dividend-reference",
        },
        "death_formula": "greater_of_annual_insured_amount_policy_reserve_ratio_paid_premium_total_1_01",
        "maturity_formula": "greater_of_annual_insured_amount_at_age_110_paid_premium_total_1_01",
    },
    "202121MZ1A57B22B11Z10000000": {
        "maturity_label": "滿期保險金",
        "participating_policy": False,
        "policy_period_years": 10,
        "maturity_age": None,
        "entry_ids": {
            "death-or-funeral-benefit",
            "maturity-benefit",
            "installment-periodic-benefit",
        },
        "death_formula": "greater_of_annual_insured_amount_policy_reserve_ratio_paid_premium_total",
        "maturity_formula": "annual_insured_amount_at_policy_maturity",
    },
}
for product_id, expected in taiwan_usd_no_disability_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_usd_no_disability_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-usd-no-disability-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_label"] == "基本保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["currency"] == "USD"
    assert characteristics["maturity_label"] == expected["maturity_label"]
    assert characteristics["participating_policy"] is expected["participating_policy"]
    assert characteristics["policy_period_years"] == expected["policy_period_years"]
    if expected["maturity_age"] is None:
        assert "maturity_age" not in characteristics
    else:
        assert characteristics["maturity_age"] == expected["maturity_age"]
    assert characteristics["death_benefit_formula"] == expected["death_formula"]
    assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]
    assert characteristics["installment_min_annual_payment"] == 1_200
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == expected["entry_ids"]
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["name"] == expected["maturity_label"]
    assert entries["installment-periodic-benefit"]["amount_role"] == "reference"
    if expected["maturity_label"] == "滿期保險金":
        assert entries["maturity-benefit"]["calculation_basis"] == "percentage_of_base"
        assert entries["maturity-benefit"]["rate_percent"] == 100
    else:
        assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
        assert entries["terminal-policy-dividend-reference"]["amount_role"] == "reference"

taiwan_long_term_care_whole_life_cases = {
    "202191MZ6G84423A11Z10000000": {
        "terms_revision": "roc-109-11-30",
        "filing_number": "1092320180",
    },
    "202191MZ6G84423A11Z10000001": {
        "terms_revision": "roc-110-07-01-first-revision",
        "filing_number": "1102320053",
    },
}
for product_id, expected in taiwan_long_term_care_whole_life_cases.items():
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_long_term_care_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-long-term-care-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    assert "長期照顧保險金" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["filing_number"] == expected["filing_number"]
    assert characteristics["currency"] == "TWD"
    assert characteristics["product_form"] == "long_term_care_whole_life"
    assert characteristics["participating_policy"] is False
    assert (
        characteristics["annual_insured_amount_formula"]
        == "first_3_years_annual_premium_total_times_1_06_then_face_amount"
    )
    assert (
        characteristics["long_term_care_benefit_formula"]
        == "first_3_years_annual_premium_total_then_50_percent_face_amount"
    )
    assert characteristics["long_term_care_persistence_months"] == 3
    assert characteristics["long_term_care_adl_impairments_required"] == 3
    assert characteristics["long_term_care_cdr_min"] == 2
    assert characteristics["long_term_care_benefit_lifetime_limit"] == 1
    assert characteristics["accidental_death_benefit_formula"] == "additional_face_amount"
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["maturity_age"] == 100
    assert characteristics["installment_benefit_available"] is True
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["policy_face_amount_required"] is True
    assert characteristics["policy_reserve_required"] is True
    assert characteristics["premium_total_required"] is True
    assert characteristics["policy_reserve_ratio_required"] is False
    assert characteristics["coefficient_table_required"] is False
    assert characteristics["payment_period_required"] is True
    assert characteristics["long_term_care_claim_offset_required"] is True
    assert characteristics["foreign_currency_policy"] is False
    assert characteristics["funeral_benefit_limit_rule"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "long-term-care-benefit",
        "death-or-funeral-benefit",
        "accidental-death-additional-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "premium-waiver",
        "installment-periodic-benefit",
    }
    assert entries["long-term-care-benefit"]["calculation_basis"] == "unknown"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert (
        entries["accidental-death-additional-benefit"]["calculation_basis"]
        == "percentage_of_base"
    )
    assert entries["accidental-death-additional-benefit"]["rate_percent"] == 100
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert entries["maturity-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert entries["premium-waiver"]["amount_role"] == "reference"
    assert entries["installment-periodic-benefit"]["amount_role"] == "reference"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())
    completed = complete_strict_source_document(
        {**document, "text": document["text"][:1500]},
        TII_LIFE_009_ROOT / product_id / f"{product_id}-A.pdf",
    )
    assert completed["page_count"] == 10
    assert parse_taiwan_long_term_care_whole_life_formula(completed) is not None

assert parse_taiwan_long_term_care_whole_life_formula(
    taiwan_interest_whole_life_document("202191MZ6G84423A11Z10000000", "F")
) is None

taiwan_return_interest_product_ids = [
    "202121MA2G92223A11Z10000000",
    "202121MA2A15A23A11Z10000000",
    "202121MA2A15A23A11Z10000001",
    "202121MA2A97123A11Z10000000",
    "202121MA2A97123A11Z10000002",
    "202121MA1A56A23B11Z10000000",
    "202121MA1A32A23B11Z10000000",
    "202121MA1A70A23A11Z10000000",
    "202121MA1A74A23B11Z10000000",
    "202121MA1A91223B11Z10000000",
    "202121MA1A91223B11Z10000001",
    "202121MA1A91223B11Z10000002",
    "202121MA1A91323B11Z10000000",
    "202121MA1A92323B11Z10000000",
    "202121MA1A92323B11Z10000001",
    "202121MA1A92323B11Z10000002",
    "202121MA1A92823A11Z10000000",
    "202121MA1A92823A11Z10000001",
    "202121MA1A92823A11Z10000002",
    "202121MA1A95423B11Z10000000",
    "202121MA1A95423B11Z10000001",
    "202121MA1A95523B11Z10000000",
    "202121MA1A95523B11Z10000001",
    "202121MA1A96823B11Z10000000",
    "202121MA1A96823B11Z10000001",
    "202121MA1A96823B11Z10000002",
]
taiwan_return_interest_cases = {
    "202121MA2G92223A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 0.75,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_2_1_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 1.0,
        "survival_max": 2.0,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
        "mass_transit_rate": 50.0,
        "specific_cancer_rate": 1.0,
    },
    "202121MA2A15A23A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_43_2_86_0_92_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.92,
        "survival_max": 2.86,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
        "mass_transit_rate": 25.0,
    },
    "202121MA2A15A23A11Z10000001": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_43_2_86_0_92_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.92,
        "survival_max": 2.86,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
        "mass_transit_rate": 25.0,
    },
    "202121MA2A97123A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_30_2_60_0_85_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.85,
        "survival_max": 2.60,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
        "mass_transit_rate": 50.0,
    },
    "202121MA2A97123A11Z10000002": {
        "currency": "TWD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_30_2_60_0_85_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.85,
        "survival_max": 2.60,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
        "mass_transit_rate": 50.0,
    },
    "202121MA1A56A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 2.50,
        "annual_formula": "face_plus_accumulated_paid_up_additions_times_3_6_percent",
        "survival_formula": "selected_survival_age_previous_annual_insured_amount_to_age_99",
        "survival_min": 100.0,
        "survival_max": 100.0,
        "monthly": False,
        "maturity_formula": "age_99_face_plus_accumulated_paid_up_additions_times_1_6",
        "maturity_multiplier": "fixed_1_6x",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A32A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "premium_period_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated",
        "survival_formula": "2_or_4_year_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 6.0,
        "survival_max": 12.0,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_times_5_and_premium_component",
        "maturity_multiplier": "fixed_5x",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A70A23A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.25,
        "annual_formula": "first_two_policy_years_premium_total_times_1_01_minus_coeff_then_face_plus_accumulated_times_1_7",
        "survival_formula": "1_50_3_00_1_77_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 1.5,
        "survival_max": 3.0,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_01_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A74A23B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "premium_period_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated",
        "survival_formula": "3_6_10_year_schedule_with_monthly_8_4_percent_option",
        "survival_min": 4.0,
        "survival_max": 8.0,
        "monthly": True,
        "maturity_formula": "greater_of_annual_insured_amount_by_payment_period_multiplier_and_premium_component",
        "maturity_multiplier": "payment_period_3_6_10_years_multiplier_5_6_7",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A91223B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated_times_1_6",
        "survival_formula": "2_4_1_4_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 1.4,
        "survival_max": 4.0,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A91323B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated",
        "survival_formula": "0_21_to_1_5_long_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.21,
        "survival_max": 1.5,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A92323B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated",
        "survival_formula": "post_premium_period_1_5_percent_on_previous_face_plus_accumulated",
        "survival_min": 1.5,
        "survival_max": 1.5,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A92823A11Z10000000": {
        "currency": "TWD",
        "expected_rate": 1.50,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated_times_annual_factor_table",
        "survival_formula": "0_25_to_1_5_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.25,
        "survival_max": 1.5,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A95423B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.00,
        "annual_formula": "first_two_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated_times_1_6",
        "survival_formula": "2_06_4_12_1_05_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 1.05,
        "survival_max": 4.12,
        "monthly": False,
        "maturity_formula": "greater_of_annual_insured_amount_and_premium_component",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A95523B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.75,
        "annual_formula": "first_five_policy_years_premium_total_times_1_06_minus_coeff_then_face_plus_accumulated_times_1_6",
        "survival_formula": "0_62_to_1_9_step_schedule_on_previous_face_plus_accumulated",
        "survival_min": 0.62,
        "survival_max": 3.1,
        "monthly": False,
        "maturity_formula": "annual_insured_amount",
        "maturity_multiplier": "none",
        "premium_component": "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient",
        "standard_premium_table": False,
    },
    "202121MA1A96823B11Z10000000": {
        "currency": "USD",
        "expected_rate": 1.50,
        "annual_formula": "face_plus_accumulated_paid_up_additions",
        "survival_formula": "2_or_4_year_premium_table_schedule_with_monthly_option",
        "survival_min": 2.3,
        "survival_max": 10.76,
        "monthly": True,
        "maturity_formula": "greater_of_annual_insured_amount_times_5_and_premium_component",
        "maturity_multiplier": "fixed_5x",
        "premium_component": "premium_total_times_1_06_minus_standard_premium_table_times_coefficient",
        "standard_premium_table": True,
    },
}
for product_id in taiwan_return_interest_product_ids:
    document = taiwan_interest_whole_life_document(product_id)
    schedule = parse_taiwan_interest_rate_return_whole_life_formula(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-interest-rate-return-whole-life-formula-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "基本保險金額"
    assert "繳費年期" in schedule["selection_guidance"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["maturity_age"] == 100
    assert characteristics["value_sharing_bonus"] is True
    assert characteristics["premium_waiver_available"] is False
    assert characteristics["payment_period_required"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) >= {
        "value-sharing-bonus",
        "survival-benefit",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["survival-benefit"]["calculation_basis"] == "percentage_of_base"
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert all(entry["source"] == "terms" for entry in entries.values())
    mass_transit_entry = entries.get(
        "mass-transit-accidental-death-or-funeral-additional"
    )
    if characteristics["mass_transit_accidental_death_available"]:
        assert mass_transit_entry is not None
        assert mass_transit_entry["calculation_basis"] == "percentage_of_base"
        assert mass_transit_entry["aggregation_rule"] == "conditional_additive"
        assert (
            mass_transit_entry["rate_percent"]
            == characteristics["mass_transit_accidental_death_rate_percent"]
        )
        assert characteristics["mass_transit_accidental_death_claim_age_limit"] == 85
        assert characteristics["accident_claim_days"] == 180
    else:
        assert mass_transit_entry is None
    specific_cancer_entry = entries.get("specific-site-cancer-benefit")
    if characteristics.get("specific_cancer_benefit_available"):
        assert specific_cancer_entry is not None
        assert specific_cancer_entry["calculation_basis"] == "percentage_of_base"
        assert specific_cancer_entry["basis"] == "face_amount"
        assert specific_cancer_entry["limit_scope"] == "per_policy"
        assert (
            specific_cancer_entry["rate_percent"]
            == characteristics["specific_cancer_rate_percent"]
        )
        assert characteristics["specific_cancer_waiting_days"] == 90
        assert characteristics["specific_cancer_lifetime_limit_times"] == 1
        assert characteristics["specific_cancer_basis"] == "basic_face_amount"
    else:
        assert specific_cancer_entry is None
    if product_id in taiwan_return_interest_cases:
        expected = taiwan_return_interest_cases[product_id]
        assert characteristics["currency"] == expected["currency"]
        assert characteristics["expected_interest_rate_percent"] == expected["expected_rate"]
        assert characteristics["annual_insured_amount_formula"] == expected["annual_formula"]
        assert characteristics["survival_benefit_formula"] == expected["survival_formula"]
        assert characteristics["survival_rate_min_percent"] == expected["survival_min"]
        assert characteristics["survival_rate_max_percent"] == expected["survival_max"]
        assert characteristics["monthly_survival_benefit_available"] is expected["monthly"]
        assert characteristics["maturity_benefit_formula"] == expected["maturity_formula"]
        assert characteristics["maturity_multiplier_formula"] == expected["maturity_multiplier"]
        assert characteristics["premium_component"] == expected["premium_component"]
        assert (
            characteristics["standard_premium_table_required"]
            is expected["standard_premium_table"]
        )
        if "mass_transit_rate" in expected:
            assert (
                characteristics["mass_transit_accidental_death_rate_percent"]
                == expected["mass_transit_rate"]
            )
            assert mass_transit_entry is not None
            assert mass_transit_entry["rate_percent"] == expected["mass_transit_rate"]
        if "specific_cancer_rate" in expected:
            assert (
                characteristics["specific_cancer_rate_percent"]
                == expected["specific_cancer_rate"]
            )
            assert specific_cancer_entry is not None
            assert specific_cancer_entry["rate_percent"] == expected["specific_cancer_rate"]
        assert (
            entries["survival-benefit"]["rate_min_percent"]
            == expected["survival_min"]
        )
        assert (
            entries["survival-benefit"]["rate_max_percent"]
            == expected["survival_max"]
        )

assert parse_taiwan_interest_rate_return_whole_life_formula(
    taiwan_interest_whole_life_document("202121MA1A32A23B11Z10000000", "F")
) is None
taiwan_meixin_youtui_document = taiwan_interest_whole_life_document(
    "202121MA1A56A23B11Z10000000"
)
taiwan_meixin_youtui_schedule = parse_taiwan_interest_rate_return_whole_life_formula(
    taiwan_meixin_youtui_document
)
assert taiwan_meixin_youtui_schedule is not None
taiwan_meixin_youtui_characteristics = taiwan_meixin_youtui_schedule[
    "version_characteristics"
]
assert (
    taiwan_meixin_youtui_characteristics["annual_insured_amount_formula"]
    == "face_plus_accumulated_paid_up_additions_times_3_6_percent"
)
assert (
    taiwan_meixin_youtui_characteristics["survival_benefit_formula"]
    == "selected_survival_age_previous_annual_insured_amount_to_age_99"
)
assert (
    taiwan_meixin_youtui_characteristics["maturity_benefit_formula"]
    == "age_99_face_plus_accumulated_paid_up_additions_times_1_6"
)
assert (
    taiwan_meixin_youtui_characteristics["premium_component"]
    == "premium_total_times_1_06_minus_face_plus_accumulated_times_coefficient"
)
assert taiwan_meixin_youtui_characteristics["currency"] == "USD"
assert taiwan_meixin_youtui_characteristics["expected_interest_rate_percent"] == 2.5
assert taiwan_meixin_youtui_characteristics["mass_transit_accidental_death_available"] is False
assert taiwan_meixin_youtui_characteristics["accident_claim_days"] is None
taiwan_meixin_youtui_entries = {
    entry["id"]: entry for entry in taiwan_meixin_youtui_schedule["coverage_entries"]
}
assert taiwan_meixin_youtui_entries["survival-benefit"]["unit_key"] == (
    "previous_policy_year_annual_insured_amount"
)
assert taiwan_meixin_youtui_entries["survival-benefit"]["basis"] == (
    "policy_recorded_limit"
)
assert taiwan_meixin_youtui_entries["survival-benefit"]["rate_min_percent"] == 100.0
assert taiwan_meixin_youtui_entries["survival-benefit"]["rate_max_percent"] == 100.0
assert taiwan_meixin_youtui_entries["maturity-benefit"]["multiplier"] == 1.6
assert parse_taiwan_interest_rate_return_whole_life_formula(
    taiwan_interest_whole_life_document("202121MA1A56A23B11Z10000000", "F")
) is None
assert parse_taiwan_interest_rate_return_whole_life_formula(
    {**taiwan_meixin_youtui_document, "product_id": "202121MA1A56A23B11Z19999999"}
) is None
assert parse_taiwan_interest_rate_return_whole_life_formula(
    {
        **taiwan_meixin_youtui_document,
        "text": taiwan_meixin_youtui_document["text"].replace("之值的 3.6%", "之值的 3.5%", 1),
    }
) is None
assert parse_taiwan_interest_rate_return_whole_life_formula(
    {
        **taiwan_meixin_youtui_document,
        "text": taiwan_meixin_youtui_document["text"].replace("之值的 1.6 倍", "之值的 1.5 倍", 1),
    }
) is None
taiwan_meixin_youtui_completed = complete_strict_source_document(
    {
        **taiwan_meixin_youtui_document,
        "text": taiwan_meixin_youtui_document["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202121MA1A56A23B11Z10000000"
    / "202121MA1A56A23B11Z10000000-A.pdf",
)
assert taiwan_meixin_youtui_completed["page_count"] == 11
assert (
    parse_taiwan_interest_rate_return_whole_life_formula(
        taiwan_meixin_youtui_completed
    )
    is not None
)
taiwan_return_completed = complete_strict_source_document(
    {
        **taiwan_interest_whole_life_document("202121MA1A32A23B11Z10000000"),
        "text": taiwan_interest_whole_life_document(
            "202121MA1A32A23B11Z10000000"
        )["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202121MA1A32A23B11Z10000000"
    / "202121MA1A32A23B11Z10000000-A.pdf",
)
assert taiwan_return_completed["page_count"] == 12
assert (
    parse_taiwan_interest_rate_return_whole_life_formula(taiwan_return_completed)
    is not None
)
taiwan_return_mass_transit_completed = complete_strict_source_document(
    {
        **taiwan_interest_whole_life_document("202121MA2A15A23A11Z10000000"),
        "text": taiwan_interest_whole_life_document(
            "202121MA2A15A23A11Z10000000"
        )["text"][:1500],
    },
    TII_LIFE_009_ROOT
    / "202121MA2A15A23A11Z10000000"
    / "202121MA2A15A23A11Z10000000-A.pdf",
)
assert taiwan_return_mass_transit_completed["page_count"] == 11
assert (
    parse_taiwan_interest_rate_return_whole_life_formula(
        taiwan_return_mass_transit_completed
    )
    is not None
)

fubon_new_complete_schedules = {
    product_id: parse_fubon_new_complete_combined_plan_table(
        fubon_new_complete_document(product_id)
    )
    for product_id in FUBON_NEW_COMPLETE_PRODUCT_IDS
}
assert all(fubon_new_complete_schedules.values())
assert all(
    len(schedule["plan_options"]) == 20
    for schedule in fubon_new_complete_schedules.values()
)
new_complete_original = fubon_new_complete_schedules["209391M12G00300"]
new_complete_revision_one = fubon_new_complete_schedules["209391M11G00301"]
new_complete_revision_two = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000002"
]
new_complete_revision_three = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000003"
]
new_complete_revision_four = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000004"
]
new_complete_revision_five = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000005"
]
new_complete_revision_six = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000006"
]
new_complete_revision_seven = fubon_new_complete_schedules[
    "209391MZ1G00321A11Z10000007"
]
assert new_complete_original["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": False,
    "disability_schedule_revision": "original-75-items",
}
assert new_complete_revision_one["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "original-75-items",
}
assert new_complete_revision_two["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
}
assert new_complete_revision_three["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
}
assert new_complete_revision_four["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
    "disability_terminology": "失能",
    "cancer_classification": "original-two-tier",
    "missing_person_return_repayment_scope": "death-benefit-only",
    "funeral_benefit_cap_reference": "contract-inception",
    "source_conflicts": [
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
    ],
}
assert new_complete_revision_five["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
    "disability_terminology": "失能",
    "cancer_classification": "2018-three-tier",
    "missing_person_return_repayment_scope": "death-benefit-only",
    "funeral_benefit_cap_reference": "contract-inception",
    "source_conflicts": new_complete_revision_four["version_characteristics"][
        "source_conflicts"
    ],
}
assert new_complete_revision_six["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "109-revised-80-items",
    "disability_terminology": "失能",
    "cancer_classification": "2018-three-tier",
    "missing_person_return_repayment_scope": "death-benefit-only",
    "funeral_benefit_cap_reference": "contract-inception",
    "source_conflicts": new_complete_revision_four["version_characteristics"][
        "source_conflicts"
    ],
}
assert new_complete_revision_seven["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "109-revised-80-items",
    "disability_terminology": "失能",
    "cancer_classification": "2018-three-tier",
    "missing_person_return_repayment_scope": "refund-or-death-benefit",
    "funeral_benefit_cap_reference": "statutory-deduction",
    "source_conflicts": new_complete_revision_four["version_characteristics"][
        "source_conflicts"
    ],
}

new_complete_plan_one = {
    entry["id"]: entry
    for entry in new_complete_original["plan_options"][0]["coverage_entries"]
}
assert "policy-death" not in new_complete_plan_one
assert "initial-early-cancer" not in new_complete_plan_one
assert new_complete_plan_one["cancer-surgery"]["amount"] == 10_000
assert new_complete_plan_one["cancer-hospital-daily"]["amount"] == 1_000
assert new_complete_plan_one["hospital-room-reimbursement"]["amount"] == 1_500
assert new_complete_plan_one["hospital-icu-reimbursement"]["amount"] == 1_500
assert new_complete_plan_one["hospital-surgery-reimbursement-base"]["amount"] == 36_000
assert new_complete_plan_one["hospital-medical-reimbursement"]["amount"] == 84_168
assert new_complete_plan_one["dental-prosthesis-sublimit"]["amount"] == 5_000
assert new_complete_plan_one["pre-post-hospital-outpatient-sublimit"]["amount"] == 500
assert new_complete_plan_one["accident-emergency-sublimit"]["amount"] == 5_000
assert new_complete_plan_one["hospital-cash-alternative-daily"]["aggregation_rule"] == "choose_one"
assert new_complete_plan_one["major-burn"]["amount"] == 250_000
assert new_complete_plan_one["accident-hospital-daily"]["amount"] == 1_000
assert new_complete_plan_one["accident-outpatient-surgery"]["amount"] == 2_000
assert new_complete_plan_one["accident-medical-reimbursement"]["amount"] == 30_000
assert new_complete_plan_one["accident-death"]["amount"] == 1_000_000
assert "air-transport-accident-death" not in new_complete_plan_one

new_complete_plan_fourteen = {
    entry["id"]: entry
    for entry in new_complete_original["plan_options"][13]["coverage_entries"]
}
assert new_complete_plan_fourteen["policy-death"]["amount"] == 1_000_000
assert new_complete_plan_fourteen["major-burn"]["amount"] == 400_000
assert new_complete_plan_fourteen["accident-death"]["amount"] == 1_000_000
assert new_complete_plan_fourteen["air-transport-accident-death"]["amount"] == 2_000_000
assert new_complete_plan_fourteen["water-land-transport-accident-death"]["amount"] == 1_000_000
assert new_complete_plan_fourteen["public-building-fire-accident-death"]["amount"] == 1_000_000
assert new_complete_plan_fourteen["elevator-accident-death"]["amount"] == 1_000_000
assert "accident-medical-reimbursement" not in new_complete_plan_fourteen
assert new_complete_plan_fourteen["air-transport-accident-death"][
    "aggregation_rule"
] == "conditional_additive"
assert any(
    "僅給付最高一項運輸保障" in condition
    for condition in new_complete_plan_fourteen[
        "air-transport-accident-death"
    ]["conditions"]
)

new_complete_plan_twenty = {
    entry["id"]: entry
    for entry in new_complete_original["plan_options"][19]["coverage_entries"]
}
assert new_complete_plan_twenty["policy-death"]["amount"] == 2_000_000
assert new_complete_plan_twenty["initial-other-cancer"]["amount"] == 50_000
assert new_complete_plan_twenty["major-burn"]["amount"] == 1_200_000
assert new_complete_plan_twenty["accident-death"]["amount"] == 3_000_000
assert new_complete_plan_twenty["air-transport-accident-death"]["amount"] == 6_000_000
assert new_complete_plan_twenty["water-land-transport-accident-death"]["amount"] == 3_000_000
assert new_complete_plan_twenty["public-building-fire-accident-death"]["amount"] == 3_000_000
assert new_complete_plan_twenty["elevator-accident-death"]["amount"] == 3_000_000
assert new_complete_plan_twenty["air-transport-accident-disability"]["amount"] == 6_000_000
assert new_complete_plan_twenty["accident-hospital-daily"]["amount"] == 1_500
assert new_complete_plan_twenty["accident-icu-daily"]["amount"] == 1_500
assert new_complete_plan_twenty["accident-outpatient-surgery"]["amount"] == 3_000
assert "accident-medical-reimbursement" not in new_complete_plan_twenty

assert parse_fubon_new_complete_combined_plan_table(
    fubon_new_complete_document("209391M12G00300", "F")
) is None
unrelated_new_complete_document = {
    **fubon_new_complete_document("209391M12G00300"),
    "product_id": "unrelated-product",
    "file_name": "unrelated-product-A.pdf",
}
assert parse_fubon_new_complete_combined_plan_table(
    unrelated_new_complete_document
) is None
bad_new_complete_amount = {
    **fubon_new_complete_document("209391M11G00301"),
    "text": fubon_new_complete_document("209391M11G00301")["text"].replace(
        "84,168", "84,167", 1
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_new_complete_amount) is None

new_complete_revision_four_plan = {
    entry["id"]: entry
    for entry in new_complete_revision_four["plan_options"][19]["coverage_entries"]
}
assert new_complete_revision_four_plan["total-disability"]["name"] == "完全失能保險金"
assert new_complete_revision_four_plan["initial-early-cancer"]["name"] == "初次罹患原位癌保險金"
assert new_complete_revision_four_plan["initial-other-cancer"]["name"] == "初次罹患惡性腫瘤保險金"
assert new_complete_revision_four_plan["accident-disability"]["name"] == "一般意外失能保險金"
assert any(
    "104 年修正版附表三，共 79 項失能程度" in condition
    for condition in new_complete_revision_four_plan["accident-disability"]["conditions"]
)

new_complete_revision_five_plan = {
    entry["id"]: entry
    for entry in new_complete_revision_five["plan_options"][19]["coverage_entries"]
}
assert new_complete_revision_five_plan["initial-early-cancer"]["name"] == "初次罹患癌症（初期）保險金"
assert new_complete_revision_five_plan["initial-other-cancer"]["name"] == "初次罹患癌症（輕度或重度）保險金"
assert "癌症（初期）" in new_complete_revision_five_plan["initial-early-cancer"]["note"]
assert "癌症（輕度或重度）" in new_complete_revision_five_plan["initial-other-cancer"]["note"]

for schedule in (new_complete_revision_six, new_complete_revision_seven):
    plan = {
        entry["id"]: entry
        for entry in schedule["plan_options"][19]["coverage_entries"]
    }
    assert any(
        "109 年修正版附表三，共 80 項失能程度" in condition
        for condition in plan["accident-disability"]["conditions"]
    )

for product_id in FUBON_NEW_COMPLETE_PRODUCT_IDS[4:]:
    assert parse_fubon_new_complete_combined_plan_table(
        fubon_new_complete_document(product_id, "F")
    ) is None

wrong_new_complete_version = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000004"),
    "product_id": "209391MZ1G00321A11Z10000005",
    "file_name": "209391MZ1G00321A11Z10000005-A.pdf",
}
assert parse_fubon_new_complete_combined_plan_table(wrong_new_complete_version) is None

bad_revision_signal = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000004"),
    "text": fubon_new_complete_document("209391MZ1G00321A11Z10000004")["text"].replace(
        "10704158370", "10704158371"
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_revision_signal) is None

bad_cancer_classification = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000005"),
    "text": fubon_new_complete_document("209391MZ1G00321A11Z10000005")["text"].replace(
        "癌症(初期)", "癌症(早期)"
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_cancer_classification) is None

bad_109_disability_schedule = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000006"),
    "text": fubon_new_complete_document("209391MZ1G00321A11Z10000006")["text"].replace(
        "鼻未缺損", "鼻部未缺損"
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_109_disability_schedule) is None

bad_revision_seven_return_rule = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000007"),
    "text": fubon_new_complete_document("209391MZ1G00321A11Z10000007")["text"].replace(
        "退還已繳保險費或身故保險金或喪葬費用保險金",
        "身故保險金或喪葬費用保險金",
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_revision_seven_return_rule) is None

bad_revision_seven_amount = {
    **fubon_new_complete_document("209391MZ1G00321A11Z10000007"),
    "text": fubon_new_complete_document("209391MZ1G00321A11Z10000007")["text"].replace(
        "84,168", "84,167", 1
    ),
}
assert parse_fubon_new_complete_combined_plan_table(bad_revision_seven_amount) is None


FUBON_CARDIO_DEVICE_PRODUCT_IDS = (
    "209391MZ1A00322A11Z10000000",
    "209391RZ1A01522A11Z10000000",
    "209391RZ1A01522A11Z10000001",
    "209391RZ1A01522A11Z10000002",
)


def fubon_cardio_device_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


cardio_schedules = {
    product_id: parse_fubon_cardio_device_unit_table(
        fubon_cardio_device_document(product_id)
    )
    for product_id in FUBON_CARDIO_DEVICE_PRODUCT_IDS
}
assert all(cardio_schedules.values())
assert all(schedule["selection_type"] == "unit" for schedule in cardio_schedules.values())
assert all(schedule["input_mode"] == "unit" for schedule in cardio_schedules.values())
assert all("正整數" in schedule["selection_guidance"] for schedule in cardio_schedules.values())

heart_guard_entries = {
    entry["id"]: entry
    for entry in cardio_schedules[
        "209391MZ1A00322A11Z10000000"
    ]["coverage_entries"]
}
assert len(heart_guard_entries) == 5
assert heart_guard_entries["cardiac-stent-placement"]["amount_tiers"] == [
    {"label": "第一保單年度", "amount": 20_000},
    {"label": "第二保單年度", "amount": 40_000},
    {"label": "第三保單年度起", "amount": 80_000},
]
assert heart_guard_entries["pacemaker-implantation"]["amount_tiers"] == [
    {"label": "第一保單年度", "amount": 20_000},
    {"label": "第二保單年度", "amount": 40_000},
    {"label": "第三保單年度起", "amount": 80_000},
]
assert heart_guard_entries["heart-valve-replacement"]["amount_tiers"] == [
    {"label": "第一保單年度", "amount": 40_000},
    {"label": "第二保單年度", "amount": 80_000},
    {"label": "第三保單年度起", "amount": 160_000},
]
assert heart_guard_entries["ventricular-assist-device"]["amount_tiers"] == [
    {"label": "第一保單年度", "amount": 80_000},
    {"label": "第二保單年度", "amount": 160_000},
    {"label": "第三保單年度起", "amount": 320_000},
]
assert all(
    entry["basis"] == "per_unit"
    and entry["calculation_basis"] == "tiered_or_stepped"
    and entry["source_ref"] == "保單條款第 2、8、10 條，第 1 至 3 頁"
    for entry_id, entry in heart_guard_entries.items()
    if entry_id != "no-claim-refund"
)
heart_guard_refund = heart_guard_entries["no-claim-refund"]
assert "amount" not in heart_guard_refund
assert heart_guard_refund["calculation_basis"] == "percentage_of_base"
assert heart_guard_refund["rate_percent"] == 60
assert heart_guard_refund["source_ref"] == "保單條款第 2、9 條，第 1 至 2 頁"
assert "年繳保險費總和" in heart_guard_refund["note"]
assert "並非固定金額" in heart_guard_refund["note"]
assert any(
    "持續有效 30 日" in condition
    for condition in heart_guard_entries["cardiac-stent-placement"]["conditions"]
)
assert any(
    "第 10 條" in condition
    for condition in heart_guard_entries["cardiac-stent-placement"]["conditions"]
)

for product_id in FUBON_CARDIO_DEVICE_PRODUCT_IDS[1:]:
    heart_care_entries = {
        entry["id"]: entry
        for entry in cardio_schedules[product_id]["coverage_entries"]
    }
    assert len(heart_care_entries) == 6
    assert heart_care_entries["cardiac-stent-placement"]["amount_tiers"] == [
        {"label": "第一保單年度", "amount": 30_000},
        {"label": "第二保單年度起", "amount": 100_000},
    ]
    assert heart_care_entries["pacemaker-implantation"]["amount_tiers"] == [
        {"label": "第一保單年度", "amount": 30_000},
        {"label": "第二保單年度起", "amount": 100_000},
    ]
    assert heart_care_entries["heart-valve-replacement-group"]["amount_tiers"] == [
        {"label": "第一保單年度", "amount": 60_000},
        {"label": "第二保單年度起", "amount": 200_000},
    ]
    assert heart_care_entries["ventricular-assist-device"]["amount_tiers"] == [
        {"label": "第一保單年度", "amount": 90_000},
        {"label": "第二保單年度起", "amount": 300_000},
    ]
    assert heart_care_entries["ecmo-establishment"]["amount_tiers"] == [
        {"label": "第一保單年度", "amount": 90_000},
        {"label": "第二保單年度起", "amount": 300_000},
    ]
    assert all(
        entry["basis"] == "per_unit"
        and entry["source_ref"] == "保單條款第 2、8、10 條，第 1 至 3 頁"
        for entry_id, entry in heart_care_entries.items()
        if entry_id != "no-claim-refund"
    )
    assert any(
        "共用一次給付" in condition
        for condition in heart_care_entries["heart-valve-replacement-group"][
            "conditions"
        ]
    )
    assert all(
        any("全部 5 項" in condition for condition in entry["conditions"])
        for entry_id, entry in heart_care_entries.items()
        if entry_id != "no-claim-refund"
    )
    assert all(
        any("持續有效 30 日" in condition for condition in entry["conditions"])
        and any("第 10 條" in condition for condition in entry["conditions"])
        for entry_id, entry in heart_care_entries.items()
        if entry_id != "no-claim-refund"
    )
    assert "amount" not in heart_care_entries["no-claim-refund"]
    assert heart_care_entries["no-claim-refund"]["rate_percent"] == 30

assert parse_fubon_cardio_device_unit_table(
    fubon_cardio_device_document("209391MZ1A00322A11Z10000000", "F")
) is None
assert parse_fubon_cardio_device_unit_table(
    fubon_cardio_device_document("209391RZ1A01522A11Z10000000", "F")
) is None
unrelated_cardio_document = {
    **fubon_cardio_device_document("209391MZ1A00322A11Z10000000"),
    "product_id": "unrelated-product",
    "file_name": "unrelated-product-A.pdf",
}
assert parse_fubon_cardio_device_unit_table(unrelated_cardio_document) is None

bad_heart_guard_amount = {
    **fubon_cardio_device_document("209391MZ1A00322A11Z10000000"),
    "text": fubon_cardio_device_document("209391MZ1A00322A11Z10000000")[
        "text"
    ].replace("32萬元", "31萬元", 1),
}
assert parse_fubon_cardio_device_unit_table(bad_heart_guard_amount) is None
bad_heart_care_amount = {
    **fubon_cardio_device_document("209391RZ1A01522A11Z10000002"),
    "text": fubon_cardio_device_document("209391RZ1A01522A11Z10000002")[
        "text"
    ].replace("30 萬元", "29 萬元", 1),
}
assert parse_fubon_cardio_device_unit_table(bad_heart_care_amount) is None

wrong_heart_care_version = {
    **fubon_cardio_device_document("209391RZ1A01522A11Z10000000"),
    "product_id": "209391RZ1A01522A11Z10000001",
    "file_name": "209391RZ1A01522A11Z10000001-A.pdf",
}
assert parse_fubon_cardio_device_unit_table(wrong_heart_care_version) is None


FUBON_GOLDEN_MEDICAL_DEVICE_PRODUCT_IDS = (
    "209391RZ1A01622A11Z10000000",
    "209391RZ1A01622A11Z10000001",
)
FUBON_GOLDEN_MEDICAL_DEVICE_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-050"
)


def fubon_golden_medical_device_document(
    product_id: str, suffix: str = "A", *, complete: bool = True
) -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    document = next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )
    if not complete:
        return document
    return complete_strict_source_document(
        document,
        FUBON_GOLDEN_MEDICAL_DEVICE_ROOT / product_id / file_name,
    )


golden_medical_device_schedules = {
    product_id: parse_fubon_golden_medical_device_unit_table(
        fubon_golden_medical_device_document(product_id)
    )
    for product_id in FUBON_GOLDEN_MEDICAL_DEVICE_PRODUCT_IDS
}
assert all(golden_medical_device_schedules.values())
assert all(
    parse_plan_table_with_parser(fubon_golden_medical_device_document(product_id))[0]
    == "fubon-golden-medical-device-unit-v1"
    for product_id in FUBON_GOLDEN_MEDICAL_DEVICE_PRODUCT_IDS
)
assert all(
    schedule["selection_type"] == schedule["input_mode"] == "unit"
    for schedule in golden_medical_device_schedules.values()
)
assert all(
    schedule["selection_label"] == "投保單位數"
    for schedule in golden_medical_device_schedules.values()
)
assert golden_medical_device_schedules[
    "209391RZ1A01622A11Z10000000"
]["version_characteristics"] == {
    "terms_revision": "original",
    "disease_initial_waiting_days": 30,
    "maximum_coverage_age": 74,
    "benefit_tiers_by_policy_year": True,
    "unit_reduction_revision": False,
    "all_items_paid_termination": True,
}
assert golden_medical_device_schedules[
    "209391RZ1A01622A11Z10000001"
]["version_characteristics"] == {
    "terms_revision": "114-revised",
    "disease_initial_waiting_days": 30,
    "maximum_coverage_age": 74,
    "benefit_tiers_by_policy_year": True,
    "unit_reduction_revision": True,
    "all_items_paid_termination": True,
}

golden_medical_device_entries = {
    entry["id"]: entry
    for entry in golden_medical_device_schedules[
        "209391RZ1A01622A11Z10000000"
    ]["coverage_entries"]
}
assert len(golden_medical_device_entries) == 9
assert golden_medical_device_entries["intraocular-lens-implant"]["amount_tiers"] == [
    {"label": "第一保單年度每單位", "amount": 10_000},
    {"label": "第二保單年度每單位", "amount": 20_000},
    {"label": "第三保單年度起每單位", "amount": 30_000},
]
assert golden_medical_device_entries["cardiac-catheter-stent"]["amount_tiers"] == [
    {"label": "第一保單年度每單位", "amount": 30_000},
    {"label": "第二保單年度每單位", "amount": 60_000},
    {"label": "第三保單年度起每單位", "amount": 90_000},
]
assert golden_medical_device_entries["heart-valve-replacement"]["amount_tiers"] == [
    {"label": "第一保單年度每單位", "amount": 50_000},
    {"label": "第二保單年度每單位", "amount": 100_000},
    {"label": "第三保單年度起每單位", "amount": 150_000},
]
assert golden_medical_device_entries["ecmo-setup"]["amount_tiers"] == [
    {"label": "第一保單年度每單位", "amount": 100_000},
    {"label": "第二保單年度每單位", "amount": 200_000},
    {"label": "第三保單年度起每單位", "amount": 300_000},
]
assert golden_medical_device_entries["ecmo-setup"]["amount"] == 300_000
assert all(
    entry["basis"] == "per_unit"
    and entry["calculation_basis"] == "tiered_or_stepped"
    and entry["source_ref"] == "保單條款第八條及醫材補助給付表, 第 2 至 3 頁"
    for entry in golden_medical_device_entries.values()
)
assert any(
    "保單年度" in condition
    for condition in golden_medical_device_entries["ecmo-setup"]["conditions"]
)
assert any(
    "每眼每一保單年度一次" in condition
    for condition in golden_medical_device_entries["intraocular-lens-implant"][
        "conditions"
    ]
)
assert any(
    "每側關節每一保單年度一次" in condition
    for condition in golden_medical_device_entries["artificial-knee-replacement"][
        "conditions"
    ]
)
assert any(
    "屬同一給付項目" in condition
    for condition in golden_medical_device_entries["heart-valve-replacement"][
        "conditions"
    ]
)
assert all(
    parse_fubon_golden_medical_device_unit_table(
        fubon_golden_medical_device_document(product_id, "F")
    )
    is None
    for product_id in FUBON_GOLDEN_MEDICAL_DEVICE_PRODUCT_IDS
)
assert parse_fubon_golden_medical_device_unit_table(
    {
        **fubon_golden_medical_device_document(
            "209391RZ1A01622A11Z10000000"
        ),
        "document_type": "product_summary",
    }
) is None

golden_medical_device_indexed = fubon_golden_medical_device_document(
    "209391RZ1A01622A11Z10000000",
    complete=False,
)
golden_medical_device_completed = complete_strict_source_document(
    golden_medical_device_indexed,
    FUBON_GOLDEN_MEDICAL_DEVICE_ROOT
    / "209391RZ1A01622A11Z10000000"
    / "209391RZ1A01622A11Z10000000-A.pdf",
)
assert golden_medical_device_completed["page_count"] == 5
assert parse_fubon_golden_medical_device_unit_table(
    golden_medical_device_completed
) == golden_medical_device_schedules["209391RZ1A01622A11Z10000000"]

bad_golden_medical_device_amount = {
    **fubon_golden_medical_device_document("209391RZ1A01622A11Z10000000"),
    "text": fubon_golden_medical_device_document(
        "209391RZ1A01622A11Z10000000"
    )["text"].replace("10萬元 20萬元 30萬元", "10萬元 20萬元 29萬元", 1),
}
assert parse_fubon_golden_medical_device_unit_table(
    bad_golden_medical_device_amount
) is None

wrong_golden_medical_device_version = {
    **fubon_golden_medical_device_document("209391RZ1A01622A11Z10000000"),
    "product_id": "209391RZ1A01622A11Z10000001",
    "file_name": "209391RZ1A01622A11Z10000001-A.pdf",
}
assert parse_fubon_golden_medical_device_unit_table(
    wrong_golden_medical_device_version
) is None


FUBON_EASY_TABLE_SIGNALS = " ".join(
    [
        "保險金項目 計畫一 計畫二 計畫三 計畫四",
        "身故保險金或喪葬費用保險金 無 無 50 萬 100 萬",
        "完全殘廢保險金 無 無 50 萬 100 萬",
        "重大燒燙傷保險金 20 萬 40 萬 40 萬 80 萬",
        "一般意外身故保險金或喪葬費用保險金 50 萬 100 萬 100 萬 200 萬",
        "癌症手術治療保險金 1 萬/次 1 萬/次 1 萬/次 3 萬/次",
        "意外傷害住院醫療保險金 1,000 元/日 1,000 元/日 1,000 元/日 1,500 元/日",
        "意外傷害醫療保險金 無 無 無 無",
        "保險金項目 計畫五 計畫六 計畫七 計畫八",
        "身故保險金或喪葬費用保險金 100 萬 無 無 50 萬",
        "重大燒燙傷保險金 120 萬 20 萬 40 萬 40 萬",
        "一般意外身故保險金或喪葬費用保險金 300 萬 50 萬 100 萬 100 萬",
        "癌症手術治療保險金 3 萬/次 1 萬/次 1 萬/次 1 萬/次",
        "意外傷害醫療保險金 無 3 萬 3 萬 3 萬",
        "一般住院醫療保險金 2,000 元/日 1,500 元/日 1,500 元/日 1,500 元/日",
        "保險金項目 計畫九 計畫十 計畫十一 計畫十二",
        "身故保險金或喪葬費用保險金 100 萬 100 萬 100 萬 200 萬",
        "完全殘廢保險金 100 萬 100 萬 200 萬 300 萬",
        "重大燒燙傷保險金 80 萬 120 萬 25 萬 25 萬",
        "一般意外身故保險金或喪葬費用保險金 200 萬 300 萬 100 萬 100 萬",
        "癌症身故保險金 10 萬 10 萬 50 萬 50 萬",
        "癌症手術治療保險金 3 萬/次 3 萬/次 1 萬/次 3 萬/次",
        "意外傷害住院醫療保險金 1,500 元/日 1,500 元/日 無 無",
        "意外傷害醫療保險金 3 萬 3 萬 無 無",
        "一般住院醫療保險金 1,500 元/日 2,000 元/日 無 無",
    ]
)
FUBON_EASY_TERMS = " ".join(
    [
        "第 1 頁 富邦人壽安心輕鬆保傷害暨健康一年定期保險",
        "【本保險為非保證續保之保險商品】 本契約保險期間為一年。",
        "第 4 頁 【保險範圍:身故保險金或喪葬費用保險金的給付】 第十二條",
        "【保險範圍:完全殘廢保險金的給付】 第十三條",
        "第 5 頁 【保險範圍:癌症保險金的給付】 第十七條",
        "被保險人自本契約生效日(或復效日持續有效三十日)後始經診斷。",
        "初次罹患癌症保險金之責任,各以一次為限。",
        "第 6 頁 【保險範圍:住院醫療保險金的給付】 第十八條",
        "同一保單年度同一次住院給付日數最高以三百六十五日為限。",
        "同一保單年度同一次住院給付日數最高以七日為限。",
        "第 7 頁 【保險範圍:重大燒燙傷保險金的給付】 第二十一條",
        "自意外傷害事故發生之日起屆滿十五日仍生存。",
        "【保險範圍:住院醫療保險金的給付】 第二十二條",
        "同一次意外傷害給付日數不得超過三百六十五日。",
        "第 8 頁 【保險範圍:意外傷害門診手術醫療保險金的給付】 第二十三條",
        "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限。",
        "【保險範圍:意外傷害醫療保險金的給付】 第二十四條",
        "則附表一所載意外傷害醫療保險金之限額提高為1.35 倍。",
        "【保險範圍:意外身故保險金或喪葬費用保險金的給付】 第二十五條",
        "同時符合二項以上大眾運輸工具意外傷害事故者。",
        "第 9 頁 【保險範圍:意外殘廢保險金的給付】 第二十六條",
        "要保人係投保計畫十一或計畫十二者,僅就殘廢等級第二級至第十一級給付保險金。",
        "第 10 頁 【意外身故保險金及意外殘廢保險金給付的限制】 第二十七條",
        f"第 13 頁 附表一: {FUBON_EASY_TABLE_SIGNALS} 附表二",
    ]
)
fubon_easy_schedule = parse_fubon_easy_combined_plan_table(
    {
        "product_id": "209391M12G00400",
        "file_name": "209391M12G00400-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_EASY_TERMS,
    }
)
assert fubon_easy_schedule is not None
assert fubon_easy_schedule["selection_label"] == "保障計畫"
assert fubon_easy_schedule["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 30,
    "day_hospital_explicit": False,
    "disability_schedule_revision": "original-75-items",
}
assert [plan["label"] for plan in fubon_easy_schedule["plan_options"]] == [
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
]
assert [len(plan["coverage_entries"]) for plan in fubon_easy_schedule["plan_options"]] == [
    15,
    23,
    27,
    27,
    27,
    16,
    24,
    28,
    28,
    28,
    13,
    13,
]
plan_one_entries = {
    entry["id"]: entry
    for entry in fubon_easy_schedule["plan_options"][0]["coverage_entries"]
}
assert "policy-death" not in plan_one_entries
assert "accident-medical-reimbursement" not in plan_one_entries
assert plan_one_entries["major-burn"]["amount"] == 200_000
assert "初次生效無等待期" in plan_one_entries["cancer-hospital-daily"]["conditions"][0]
assert "復效須持續有效 30 日" in plan_one_entries["cancer-hospital-daily"]["conditions"][0]
plan_six_entries = {
    entry["id"]: entry
    for entry in fubon_easy_schedule["plan_options"][5]["coverage_entries"]
}
assert plan_six_entries["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般限額", "amount": 30_000},
    {"label": "以全民健康保險身分接受治療", "amount": 40_500},
]
plan_twelve_entries = {
    entry["id"]: entry
    for entry in fubon_easy_schedule["plan_options"][11]["coverage_entries"]
}
assert plan_twelve_entries["policy-death"]["amount"] == 2_000_000
assert plan_twelve_entries["total-disability"]["amount"] == 3_000_000
assert plan_twelve_entries["cancer-death"]["amount"] == 500_000
assert plan_twelve_entries["accident-disability"]["amount"] == 3_000_000
assert plan_twelve_entries["accident-disability"]["rate_max_percent"] == 90
assert "hospital-daily" not in plan_twelve_entries
assert "accident-hospital-daily" not in plan_twelve_entries
assert all(
    entry["amount"] > 0
    for plan in fubon_easy_schedule["plan_options"]
    for entry in plan["coverage_entries"]
)
assert all(
    "附表一" in entry["source_ref"]
    for plan in fubon_easy_schedule["plan_options"]
    for entry in plan["coverage_entries"]
)

fubon_easy_revision_four = parse_fubon_easy_combined_plan_table(
    {
        "product_id": "209391MZ9G00121A11Z10000004",
        "file_name": "209391MZ9G00121A11Z10000004-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_EASY_TERMS.replace(
            "自本契約生效日(或復效日持續有效三十日)後",
            "自本契約生效日(或復效日)起之有效期間內",
        ),
    }
)
assert fubon_easy_revision_four is not None
assert fubon_easy_revision_four["version_characteristics"][
    "cancer_reinstatement_waiting_days"
] == 0
revision_four_cancer = next(
    entry
    for entry in fubon_easy_revision_four["plan_options"][0]["coverage_entries"]
    if entry["id"] == "cancer-hospital-daily"
)
assert "初次生效及復效均無等待期" in revision_four_cancer["conditions"][0]
assert "30 日" not in revision_four_cancer["conditions"][0]
assert parse_fubon_easy_combined_plan_table(
    {
        "product_id": "209391M12G00400",
        "file_name": "209391M12G00400-F.pdf",
        "document_type": "product_summary",
        "text": FUBON_EASY_TERMS,
    }
) is None

FUBON_EASY_REVISIONS_FIVE_TO_EIGHT = tuple(
    f"209391MZ9G00121A11Z1000000{revision}"
    for revision in range(5, 9)
)
FUBON_EASY_PLAN_ENTRY_COUNTS = [
    15,
    23,
    27,
    27,
    27,
    16,
    24,
    28,
    28,
    28,
    13,
    13,
]


def fubon_easy_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


fubon_easy_revised_schedules = {
    product_id: parse_fubon_easy_combined_plan_table(
        fubon_easy_document(product_id)
    )
    for product_id in FUBON_EASY_REVISIONS_FIVE_TO_EIGHT
}
assert all(fubon_easy_revised_schedules.values())
assert all(
    len(schedule["plan_options"]) == 12
    for schedule in fubon_easy_revised_schedules.values()
)
assert all(
    [len(plan["coverage_entries"]) for plan in schedule["plan_options"]]
    == FUBON_EASY_PLAN_ENTRY_COUNTS
    for schedule in fubon_easy_revised_schedules.values()
)
assert all(
    entry["amount"] > 0 and "附表一，第 14-16 頁" in entry["source_ref"]
    for schedule in fubon_easy_revised_schedules.values()
    for plan in schedule["plan_options"]
    for entry in plan["coverage_entries"]
)

easy_revision_five = fubon_easy_revised_schedules[
    "209391MZ9G00121A11Z10000005"
]
easy_revision_six = fubon_easy_revised_schedules[
    "209391MZ9G00121A11Z10000006"
]
easy_revision_seven = fubon_easy_revised_schedules[
    "209391MZ9G00121A11Z10000007"
]
easy_revision_eight = fubon_easy_revised_schedules[
    "209391MZ9G00121A11Z10000008"
]

assert easy_revision_five["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
    "disability_terminology": "失能",
    "cancer_classification": "original-two-tier",
    "missing_person_return_repayment_scope": "death-benefit-only",
    "funeral_benefit_cap_reference": "contract-inception",
    "source_conflicts": [
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
    ],
}
assert easy_revision_six["version_characteristics"] == {
    "cancer_initial_waiting_days": 0,
    "cancer_reinstatement_waiting_days": 0,
    "day_hospital_explicit": True,
    "disability_schedule_revision": "104-revised-79-items",
    "disability_terminology": "失能",
    "cancer_classification": "2018-three-tier",
    "missing_person_return_repayment_scope": "death-benefit-only",
    "funeral_benefit_cap_reference": "contract-inception",
}
assert easy_revision_seven["version_characteristics"] == {
    **easy_revision_six["version_characteristics"],
    "disability_schedule_revision": "109-revised-80-items",
}
assert easy_revision_eight["version_characteristics"] == {
    **easy_revision_seven["version_characteristics"],
    "missing_person_return_repayment_scope": "refund-or-death-benefit",
    "funeral_benefit_cap_reference": "statutory-deduction",
}

easy_plan_three_v5 = {
    entry["id"]: entry
    for entry in easy_revision_five["plan_options"][2]["coverage_entries"]
}
assert easy_plan_three_v5["total-disability"]["name"] == "完全失能保險金"
assert easy_plan_three_v5["total-disability"]["amount"] == 500_000
assert easy_plan_three_v5["initial-carcinoma-in-situ"]["amount"] == 5_000
assert easy_plan_three_v5["initial-malignant-tumor"]["amount"] == 50_000
assert easy_plan_three_v5["major-burn"]["amount"] == 400_000
assert easy_plan_three_v5["accident-death"]["amount"] == 1_000_000

easy_plan_three_v6 = {
    entry["id"]: entry
    for entry in easy_revision_six["plan_options"][2]["coverage_entries"]
}
assert easy_plan_three_v6["initial-early-cancer"]["name"] == (
    "初次罹患癌症（初期）保險金"
)
assert easy_plan_three_v6["initial-early-cancer"]["amount"] == 5_000
assert easy_plan_three_v6["initial-other-cancer"]["name"] == (
    "初次罹患癌症（輕度或重度）保險金"
)
assert easy_plan_three_v6["initial-other-cancer"]["amount"] == 50_000

easy_plan_six_v8 = {
    entry["id"]: entry
    for entry in easy_revision_eight["plan_options"][5]["coverage_entries"]
}
assert easy_plan_six_v8["accident-medical-reimbursement"]["amount"] == 30_000
assert easy_plan_six_v8["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般限額", "amount": 30_000},
    {"label": "以全民健康保險身分接受治療", "amount": 40_500},
]

easy_plan_twelve_v8 = {
    entry["id"]: entry
    for entry in easy_revision_eight["plan_options"][11]["coverage_entries"]
}
assert easy_plan_twelve_v8["policy-death"]["amount"] == 2_000_000
assert easy_plan_twelve_v8["total-disability"]["amount"] == 3_000_000
assert easy_plan_twelve_v8["cancer-death"]["amount"] == 500_000
assert easy_plan_twelve_v8["accident-disability"]["amount"] == 3_000_000
assert easy_plan_twelve_v8["accident-disability"]["rate_max_percent"] == 90
assert any(
    "109 年修正版附表三，共 80 項失能程度" in condition
    for condition in easy_plan_twelve_v8["accident-disability"]["conditions"]
)

easy_v5_document = fubon_easy_document(
    "209391MZ9G00121A11Z10000005"
)
assert parse_fubon_easy_combined_plan_table(
    fubon_easy_document("209391MZ9G00121A11Z10000005", "F")
) is None
assert parse_fubon_easy_combined_plan_table(
    {
        **easy_v5_document,
        "document_type": "product_summary",
    }
) is None
assert parse_fubon_easy_combined_plan_table(
    {
        **easy_v5_document,
        "product_id": "unrelated-product",
        "file_name": "unrelated-product-A.pdf",
    }
) is None

easy_bad_article = {
    **easy_v5_document,
    "text": easy_v5_document["text"].replace(
        "【保險範圍：癌症保險金的給付】 第十七條",
        "【保險範圍：癌症保險金的給付】 第十六條",
        1,
    ),
}
assert parse_fubon_easy_combined_plan_table(easy_bad_article) is None

easy_bad_amount_text = easy_v5_document["text"]
easy_bad_amount_start = easy_bad_amount_text.index("附表一：")
easy_bad_amount = {
    **easy_v5_document,
    "text": (
        easy_bad_amount_text[:easy_bad_amount_start]
        + easy_bad_amount_text[easy_bad_amount_start:].replace(
            "重大燒燙傷保險金 20 萬",
            "重大燒燙傷保險金 21 萬",
            1,
        )
    ),
}
assert parse_fubon_easy_combined_plan_table(easy_bad_amount) is None

easy_missing_appendix = {
    **easy_v5_document,
    "text": easy_v5_document["text"].replace("附表一：", "附表甲："),
}
assert parse_fubon_easy_combined_plan_table(easy_missing_appendix) is None

easy_wrong_version = {
    **easy_v5_document,
    "text": fubon_easy_document(
        "209391MZ9G00121A11Z10000006"
    )["text"],
}
assert parse_fubon_easy_combined_plan_table(easy_wrong_version) is None

easy_bad_feature_document = fubon_easy_document(
    "209391MZ9G00121A11Z10000007"
)
easy_bad_feature = {
    **easy_bad_feature_document,
    "text": easy_bad_feature_document["text"].replace(
        "鼻未缺損",
        "鼻部未缺損",
    ),
}
assert parse_fubon_easy_combined_plan_table(easy_bad_feature) is None

easy_bad_day_hospital_document = fubon_easy_document(
    "209391MZ9G00121A11Z10000006"
)
easy_bad_day_hospital = {
    **easy_bad_day_hospital_document,
    "text": easy_bad_day_hospital_document["text"].replace(
        "包含精神衛生法第三十五條所稱之日間留院",
        "包含日間留院",
    ),
}
assert parse_fubon_easy_combined_plan_table(easy_bad_day_hospital) is None

easy_bad_waiting_period = {
    **easy_v5_document,
    "text": easy_v5_document["text"].replace(
        "自本契約生效日（或復效日)起",
        "自本契約生效日（或復效日持續有效三十日)後",
    ),
}
assert parse_fubon_easy_combined_plan_table(easy_bad_waiting_period) is None

FUBON_GOLDEN_COMPLETE_PRODUCT_IDS = (
    "209391MZ9D00421A11Z10000000",
    "209391MZ9D00421A11Z10000001",
    "209391MZ9D00421A11Z10000002",
    "209391MZ9D00421A11Z10000003",
    "209391MZ9D00421A11Z10000004",
)


def fubon_golden_complete_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


fubon_golden_complete_schedules = {
    product_id: parse_fubon_golden_complete_combined_plan_table(
        fubon_golden_complete_document(product_id)
    )
    for product_id in FUBON_GOLDEN_COMPLETE_PRODUCT_IDS
}
assert all(fubon_golden_complete_schedules.values())
assert all(
    [plan["label"] for plan in schedule["plan_options"]]
    == ["計畫一", "計畫二", "計畫三", "計畫四"]
    for schedule in fubon_golden_complete_schedules.values()
)
assert all(
    [len(plan["coverage_entries"]) for plan in schedule["plan_options"]]
    == [18, 19, 18, 19]
    for schedule in fubon_golden_complete_schedules.values()
)
golden_complete_plan_one = {
    entry["id"]: entry
    for entry in fubon_golden_complete_schedules[
        FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[0]
    ]["plan_options"][0]["coverage_entries"]
}
golden_complete_plan_two = {
    entry["id"]: entry
    for entry in fubon_golden_complete_schedules[
        FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[3]
    ]["plan_options"][1]["coverage_entries"]
}
assert "accident-medical-reimbursement" not in golden_complete_plan_one
assert golden_complete_plan_two["accident-medical-reimbursement"]["amount"] == 40_000
assert golden_complete_plan_two["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般情形", "amount": 40_000},
    {"label": "以全民健康保險身分治療", "amount": 54_000},
]
assert golden_complete_plan_one["cancer-death"]["amount"] == 200_000
assert golden_complete_plan_one["major-burn"]["amount"] == 400_000
assert golden_complete_plan_one["accident-death"]["amount"] == 1_000_000
assert golden_complete_plan_one["accident-disability"]["rate_min_percent"] == 5
assert golden_complete_plan_one["accident-disability"]["rate_max_percent"] == 100
assert golden_complete_plan_one["natural-disaster-accident-disability"][
    "rate_max_percent"
] == 90
assert golden_complete_plan_one["fracture-without-hospitalization"][
    "multiplier"
] == 0.5
assert all(
    schedule["version_characteristics"]["day_hospital_excluded"] is True
    for schedule in fubon_golden_complete_schedules.values()
)
assert all(
    fubon_golden_complete_schedules[product_id]["version_characteristics"][
        "disability_schedule_revision"
    ]
    == ("104-revised-79-items" if index < 3 else "109-revised-80-items")
    for index, product_id in enumerate(FUBON_GOLDEN_COMPLETE_PRODUCT_IDS)
)
assert (
    fubon_golden_complete_schedules[FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[0]][
        "version_characteristics"
    ]["disability_terminology"]
    == "殘廢"
)
assert all(
    fubon_golden_complete_schedules[product_id]["version_characteristics"][
        "disability_terminology"
    ]
    == "失能"
    for product_id in FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[1:]
)

golden_complete_base_document = fubon_golden_complete_document(
    FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[0]
)
golden_complete_base_text = golden_complete_base_document["text"]
golden_complete_normalized_base_text = normalize_terms_text(golden_complete_base_text)
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "document_type": "product_summary",
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "file_name": f"{FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[0]}-F.pdf",
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_normalized_base_text.replace(
            "MGC21070528", "MGC21080101"
        ),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_normalized_base_text.replace(
            "【保險範圍:癌症保險金的給付】 第十二條",
            "【保險範圍:癌症保險金的給付】 第十一條",
            1,
        ),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_normalized_base_text.replace("20 萬", "30 萬", 1),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_normalized_base_text.replace("附表一:", "附表甲:", 1),
    }
) is None

FUBON_GOLDEN_LOHAS_PRODUCT_IDS = (
    "209391MZ1G00421A11Z10000000",
    "209391MZ1G00421A11Z10000001",
    "209391MZ1G00421A11Z10000002",
    "209391MZ1G00421A11Z10000003",
    "209391MZ1G00421A11Z10000004",
    "209391MZ1G00421A11Z10000005",
)


def fubon_golden_lohas_document(product_id: str, suffix: str = "A") -> dict:
    file_name = f"{product_id}-{suffix}.pdf"
    return next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("file_name") == file_name
    )


fubon_golden_lohas_schedules = {
    product_id: parse_fubon_golden_lohas_combined_plan_table(
        fubon_golden_lohas_document(product_id)
    )
    for product_id in FUBON_GOLDEN_LOHAS_PRODUCT_IDS
}
assert all(fubon_golden_lohas_schedules.values())
assert all(
    [plan["label"] for plan in schedule["plan_options"]]
    == ["計畫一", "計畫二"]
    for schedule in fubon_golden_lohas_schedules.values()
)
assert all(
    [len(plan["coverage_entries"]) for plan in schedule["plan_options"]]
    == [24, 24]
    for schedule in fubon_golden_lohas_schedules.values()
)
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000000"
]["version_characteristics"]["disability_schedule_revision"] == (
    "104-revised-79-items"
)
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000001"
]["version_characteristics"]["disability_schedule_revision"] == (
    "104-revised-79-items"
)
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000000"
]["version_characteristics"]["disability_term"] == "殘廢"
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000001"
]["version_characteristics"]["disability_term"] == "殘廢"
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000002"
]["version_characteristics"]["disability_schedule_revision"] == (
    "104-revised-79-items"
)
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000002"
]["version_characteristics"]["disability_term"] == "失能"
assert all(
    fubon_golden_lohas_schedules[product_id]["version_characteristics"][
        "disability_schedule_revision"
    ]
    == "109-revised-80-items"
    for product_id in FUBON_GOLDEN_LOHAS_PRODUCT_IDS[3:]
)
golden_lohas_plan_one = {
    entry["id"]: entry
    for entry in fubon_golden_lohas_schedules[
        "209391MZ1G00421A11Z10000002"
    ]["plan_options"][0]["coverage_entries"]
}
golden_lohas_plan_two = {
    entry["id"]: entry
    for entry in fubon_golden_lohas_schedules[
        "209391MZ1G00421A11Z10000005"
    ]["plan_options"][1]["coverage_entries"]
}
assert golden_lohas_plan_one["policy-death"]["amount"] == 500_000
assert golden_lohas_plan_two["policy-death"]["amount"] == 1_000_000
assert golden_lohas_plan_one["major-disease"]["amount"] == 100_000
assert golden_lohas_plan_two["major-disease"]["amount"] == 200_000
assert golden_lohas_plan_one["mild-cancer"]["amount"] == 5_000
assert golden_lohas_plan_two["mild-cancer"]["amount"] == 10_000
assert golden_lohas_plan_one["hospital-daily"]["amount"] == 1_000
assert golden_lohas_plan_one["hospital-icu-daily"]["amount"] == 2_500
assert golden_lohas_plan_one["burn-center-hospital-daily"]["amount"] == 3_000
assert golden_lohas_plan_one["air-transport-accident-death"]["amount"] == 2_000_000
assert golden_lohas_plan_one["overseas-accident-death"]["amount"] == 1_000_000
assert golden_lohas_plan_one["accident-disability"]["rate_min_percent"] == 5
assert golden_lohas_plan_one["accident-disability"]["rate_max_percent"] == 100
assert "accident-medical-reimbursement" not in golden_lohas_plan_one
golden_lohas_original_plan_one = {
    entry["id"]: entry
    for entry in fubon_golden_lohas_schedules[
        "209391MZ1G00421A11Z10000000"
    ]["plan_options"][0]["coverage_entries"]
}
assert golden_lohas_original_plan_one["total-disability"]["name"] == "完全殘廢保險金"
assert golden_lohas_original_plan_one["accident-disability"]["name"] == "意外殘廢保險金"
assert golden_lohas_original_plan_one["accident-disability"]["amount"] == 1_000_000
assert fubon_golden_lohas_schedules[
    "209391MZ1G00421A11Z10000005"
]["version_characteristics"]["day_hospital_excluded"] is True
assert all(
    "附表一" in entry["source_ref"]
    for schedule in fubon_golden_lohas_schedules.values()
    for plan in schedule["plan_options"]
    for entry in plan["coverage_entries"]
)

golden_lohas_base_document = fubon_golden_lohas_document(
    "209391MZ1G00421A11Z10000000"
)
golden_lohas_base_text = golden_lohas_base_document["text"]
assert "富邦人壽金樂活傷害暨健康一年定期保險" in golden_lohas_base_text
assert "附表一：" in golden_lohas_base_text
assert "50 萬 100 萬" in golden_lohas_base_text
assert parse_fubon_golden_lohas_combined_plan_table(
    {
        **golden_lohas_base_document,
        "text": golden_lohas_base_text.replace(
            "富邦人壽金樂活傷害暨健康一年定期保險",
            "富邦人壽金樂活Plus傷害暨健康一年定期保險",
        ),
    }
) is None
assert parse_fubon_golden_lohas_combined_plan_table(
    {
        **golden_lohas_base_document,
        "text": golden_lohas_base_text.replace("附表一：", "附表甲：", 1),
    }
) is None
assert parse_fubon_golden_lohas_combined_plan_table(
    {
        **golden_lohas_base_document,
        "text": golden_lohas_base_text.replace(
            "50 萬 100 萬",
            "60 萬 100 萬",
            1,
        ),
    }
) is None
assert parse_fubon_golden_lohas_combined_plan_table(
    fubon_golden_lohas_document(
        "209391MZ1G00421A11Z10000002",
        suffix="F",
    )
) is None

FUBON_LOHAS_TABLE = " ".join(
    [
        "附表一: 計畫一 計畫二 計畫三 計畫四 計畫五 計畫六 計畫七 計畫八",
        "身故保險金或喪葬費用保險金 無 20萬 20萬 50萬 無 20萬 20萬 50萬",
        "完全殘廢保險金 無 20萬 20萬 50萬 無 20萬 20萬 50萬",
        "重大疾病保險金 無 20萬 20萬 50萬 無 20萬 20萬 50萬",
        "重大燒燙傷保險金 40萬 40萬 80萬 80萬 40萬 40萬 80萬 80萬",
        "一般意外身故保險金或喪葬費用保險金 100萬 100萬 200萬 200萬 100萬 100萬 200萬 200萬",
        "意外傷害醫療保險金 2萬 2萬 2萬 2萬 無 無 無 無",
        "意外傷害住院醫療保險金 500元/日",
        "意外傷害加護病房住院醫療保險金 500元/日",
        "意外傷害門診手術醫療保險金 1,000元/次",
        "一般住院醫療保險金 1,000元/日",
        "加護病房住院醫療保險金 2,000元/日",
        "燒燙傷中心住院醫療保險金 3,000元/日",
        "附表二",
    ]
)
FUBON_LOHAS_TERMS = " ".join(
    [
        "富邦人壽樂活人生傷害暨健康一年定期保險",
        "本契約保障內容分八個計畫別，各計畫別之給付內容詳附表一，由要保人擇一投保，於本契約有效期間內,本公司不受理其變更。",
        "疾病須於初次生效持續有效三十日後發生。",
        "重大疾病須持續有效九十日以後開始發生，但因意外傷害所致者,或本契約續保時,不受九十日等待期間之限制。",
        "【保險範圍:身故保險金或喪葬費用保險金的給付】 第十二條",
        "【保險範圍:完全殘廢保險金的給付】 第十三條",
        "【保險範圍:重大疾病保險金的給付】 第十七條 同時符合第十二條、第十三條或本條約定中之二項以上者",
        "【保險範圍:住院醫療保險金的給付】 第十八條 住院(含日間留院)診療",
        "同一保單年度同一次住院之一般住院醫療保險金實際給付住院日數,最高以三百六十五日為限",
        "同一保單年度同一次住院之加護病房保險金實際給付住院日數,最高以三十日為限",
        "每次事故給付日數最長以三十日為限",
        "本契約有效期間屆滿後出院者,本公司就再次住院部分不予給付保險金",
        "【保險範圍:重大燒燙傷保險金的給付】 第二十一條 自意外傷害事故發生之日起屆滿十五日仍生存",
        "【保險範圍:住院醫療保險金的給付】 第二十二條 同一次意外傷害給付日數不得超過三百六十五日",
        "【保險範圍:意外傷害門診手術醫療保險金的給付】 第二十三條 每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
        "【保險範圍:意外傷害醫療保險金的給付】 第二十四條 同一次傷害的給付總額不得超過二萬元，則每次意外傷害醫療保險金限額提高為二萬七仟元",
        "【保險範圍:意外身故保險金或喪葬費用保險金的給付】 第二十五條 同時符合二項以上大眾運輸工具意外傷害事故者",
        "【保險範圍:意外殘廢保險金的給付】 第二十六條 1-1-5 8-2-9",
        "【意外身故保險金及意外殘廢保險金給付的限制】 第二十七條",
        FUBON_LOHAS_TABLE,
    ]
)
fubon_lohas_schedule = parse_fubon_lohas_combined_plan_table(
    {
        "product_id": "209391MZ9G00221A11Z10000004",
        "file_name": "209391MZ9G00221A11Z10000004-A.pdf",
        "document_type": "policy_terms",
        "text": FUBON_LOHAS_TERMS,
    }
)
assert fubon_lohas_schedule is not None
assert fubon_lohas_schedule["selection_type"] == "plan"
assert [plan["label"] for plan in fubon_lohas_schedule["plan_options"]] == [
    "計畫一",
    "計畫二",
    "計畫三",
    "計畫四",
    "計畫五",
    "計畫六",
    "計畫七",
    "計畫八",
]
assert [len(plan["coverage_entries"]) for plan in fubon_lohas_schedule["plan_options"]] == [
    11,
    22,
    22,
    22,
    10,
    21,
    21,
    21,
]
lohas_plan_one = {
    entry["id"]: entry
    for entry in fubon_lohas_schedule["plan_options"][0]["coverage_entries"]
}
assert "policy-death" not in lohas_plan_one
assert lohas_plan_one["accident-medical-reimbursement"]["amount_tiers"] == [
    {"label": "一般限額", "amount": 20_000},
    {"label": "以全民健康保險身分接受治療", "amount": 27_000},
]
lohas_plan_four = {
    entry["id"]: entry
    for entry in fubon_lohas_schedule["plan_options"][3]["coverage_entries"]
}
assert lohas_plan_four["policy-death"]["amount"] == 500_000
assert lohas_plan_four["major-disease"]["amount"] == 500_000
assert lohas_plan_four["major-burn"]["amount"] == 800_000
assert any(
    "完全脫離被劫持狀況前仍延續本項保障" in condition
    for condition in lohas_plan_four["major-burn"]["conditions"]
)
assert lohas_plan_four["air-transport-accident-death"]["amount"] == 4_000_000
assert lohas_plan_four["hospital-daily"]["amount"] == 1_000
assert lohas_plan_four["hospital-icu-daily"]["amount"] == 2_000
assert lohas_plan_four["burn-center-hospital-daily"]["amount"] == 3_000
lohas_plan_five_ids = {
    entry["id"]
    for entry in fubon_lohas_schedule["plan_options"][4]["coverage_entries"]
}
assert "major-disease" not in lohas_plan_five_ids
assert "accident-medical-reimbursement" not in lohas_plan_five_ids
assert fubon_lohas_schedule["version_characteristics"] == {
    "disease_initial_waiting_days": 30,
    "major_disease_initial_waiting_days": 90,
    "major_disease_reinstatement_waiting_days": 90,
    "day_hospital_explicit": True,
    "post_expiry_readmission_excluded": True,
    "disability_schedule_revision": "104-revised-71-items",
    "disability_term": "殘廢",
}
assert all(
    entry["amount"] > 0 and "附表一" in entry["source_ref"]
    for plan in fubon_lohas_schedule["plan_options"]
    for entry in plan["coverage_entries"]
)
assert parse_fubon_lohas_combined_plan_table(
    {
        "product_id": "209391M12G00100",
        "file_name": "209391M12G00100-F.pdf",
        "document_type": "product_summary",
        "text": FUBON_LOHAS_TERMS,
    }
) is None

FUBON_LOHAS_REVISED_PRODUCT_IDS = (
    "209391MZ9G00221A11Z10000005",
    "209391MZ9G00221A11Z10000006",
    "209391MZ9G00221A11Z10000007",
)
fubon_lohas_fixture_documents = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
for product_id in FUBON_LOHAS_REVISED_PRODUCT_IDS:
    document = next(
        item
        for item in fubon_lohas_fixture_documents
        if item["product_id"] == product_id
        and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_lohas_combined_plan_table(document)
    assert schedule is not None
    assert schedule["version_characteristics"]["disability_term"] == "失能"
    assert len(schedule["plan_options"]) == 8
    assert [len(plan["coverage_entries"]) for plan in schedule["plan_options"]] == [
        11,
        22,
        22,
        22,
        10,
        21,
        21,
        21,
    ]
    revised_plan_two = {
        entry["id"]: entry
        for entry in schedule["plan_options"][1]["coverage_entries"]
    }
    assert revised_plan_two["total-disability"]["name"] == "完全失能保險金"
    assert revised_plan_two["accident-disability"]["name"] == "一般意外失能保險金"

TII_LIFE_116_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-116-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_IDS = (
    "252321R11A00301",
    "252321R11A00302",
    "252321R11A00303",
    "252321R11A00304",
)
ANTAI_CANCER_LIFETIME_RIDER_FILES = {
    "252321R11A00301": "252321R11A003-1-A.pdf",
    "252321R11A00302": "252321R11A003-2-A.pdf",
    "252321R11A00303": "252321R11A00303-A.pdf",
    "252321R11A00304": "252321R11A00304-A.pdf",
}
ANTAI_CANCER_LIFETIME_RIDER_TABLE_PAGES = {
    "252321R11A00301": 11,
    "252321R11A00302": 9,
    "252321R11A00303": 7,
    "252321R11A00304": 7,
}


def antai_cancer_lifetime_rider_document(
    product_id: str,
    document_type: str = "policy_terms",
) -> dict:
    return next(
        document
        for document in TII_LIFE_116_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("document_type") == document_type
    )


antai_cancer_lifetime_rider_schedules = {}
for antai_product_id in ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_IDS:
    antai_document = antai_cancer_lifetime_rider_document(antai_product_id)
    assert antai_document["file_name"] == ANTAI_CANCER_LIFETIME_RIDER_FILES[
        antai_product_id
    ]
    assert repair_antai_cancer_lifetime_rider_text(antai_document["text"]) == (
        antai_document["text"]
    )
    antai_schedule = parse_antai_cancer_lifetime_rider_unit_table(antai_document)
    assert antai_schedule is not None
    antai_cancer_lifetime_rider_schedules[antai_product_id] = antai_schedule
    integrated_parse = parse_plan_table_with_parser(antai_document)
    assert integrated_parse is not None
    assert integrated_parse[0] == "antai-cancer-lifetime-rider-unit-v1"
    assert integrated_parse[1] == antai_schedule

    assert antai_schedule["selection_type"] == "unit"
    assert antai_schedule["selection_label"] == "承保單位數"
    assert "A 類保單條款" in antai_schedule["selection_guidance"]
    assert "version_characteristics" not in antai_schedule
    antai_entries = {
        entry["id"]: entry for entry in antai_schedule["coverage_entries"]
    }
    assert len(antai_entries) == 9
    assert {
        entry_id: entry["amount"]
        for entry_id, entry in antai_entries.items()
    } == {
        "cancer-diagnosis": 50_000,
        "cancer-hospital-days-1-90": 1_200,
        "cancer-hospital-days-91-plus": 1_800,
        "cancer-discharge-recovery": 600,
        "cancer-surgery": 15_000,
        "cancer-outpatient": 500,
        "cancer-radiation": 500,
        "cancer-chemotherapy": 800,
        "cancer-palliative-care": 20_000,
    }
    assert antai_entries["cancer-diagnosis"]["amount_tiers"] == [
        {"label": "第 1 至 20 保單年度／一般癌症", "amount": 50_000},
        {
            "label": "第 1 至 20 保單年度／第一期前列腺癌或原位癌",
            "amount": 7_500,
        },
        {"label": "第 21 保單年度起／一般癌症", "amount": 75_000},
        {
            "label": "第 21 保單年度起／第一期前列腺癌或原位癌",
            "amount": 11_250,
        },
    ]
    assert antai_entries["cancer-surgery"]["amount_tiers"] == [
        {"label": "一般癌症", "amount": 15_000},
        {"label": "第一期前列腺癌或原位癌", "amount": 2_250},
    ]
    assert all(entry["source"] == "terms" for entry in antai_entries.values())
    assert all(
        f"第 {ANTAI_CANCER_LIFETIME_RIDER_TABLE_PAGES[antai_product_id]} 頁"
        in entry["source_ref"]
        for entry in antai_entries.values()
    )

    waiting_condition = (
        "生效日、復效日或增加承保單位數生效日起持續有效 90 日後，才開始癌症保障"
    )
    coverage_end_condition = (
        "保險年齡達 95 歲後第一個保單週年日午夜 12 時，附約效力終止"
    )
    assert all(
        waiting_condition in entry["conditions"]
        and coverage_end_condition in entry["conditions"]
        for entry in antai_entries.values()
    )
    readmission_condition = (
        "同一癌症或其併發症出院後 14 日內再次住院，視為同一次住院"
    )
    for entry_id in (
        "cancer-hospital-days-1-90",
        "cancer-hospital-days-91-plus",
        "cancer-discharge-recovery",
    ):
        assert readmission_condition in antai_entries[entry_id]["conditions"]
    assert "15%" in antai_entries["cancer-diagnosis"]["note"]
    assert "15%" in antai_entries["cancer-surgery"]["note"]
    assert any(
        "同一手術位置" in condition and "14 日內" in condition
        for condition in antai_entries["cancer-surgery"]["conditions"]
    )
    assert "化學治療限以血管注射進行" in antai_entries[
        "cancer-chemotherapy"
    ]["conditions"]
    palliative_conditions = antai_entries["cancer-palliative-care"]["conditions"]
    assert "限罹患確定日後第 1 至第 5 個周年日，共最多五次" in (
        palliative_conditions
    )
    assert "自罹患確定日起第 6 年起不給付" in palliative_conditions
    assert (
        "第一期前列腺癌、原位癌或惡性黑色素瘤以外之皮膚癌不給付"
        in palliative_conditions
    )

# The four revisions have the same benefits; only evidence page references differ.
antai_schedule_signatures = set()
for antai_schedule in antai_cancer_lifetime_rider_schedules.values():
    antai_schedule_signatures.add(
        json.dumps(
            {
                **antai_schedule,
                "coverage_entries": [
                    {
                        key: value
                        for key, value in entry.items()
                        if key != "source_ref"
                    }
                    for entry in antai_schedule["coverage_entries"]
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
assert len(antai_schedule_signatures) == 1

for antai_product_id in ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_IDS[:2]:
    antai_document = antai_cancer_lifetime_rider_document(antai_product_id)
    mojibake_document = {
        **antai_document,
        "text": antai_document["text"].encode("utf-8").decode("latin-1"),
    }
    assert parse_antai_cancer_lifetime_rider_unit_table(mojibake_document) == (
        antai_cancer_lifetime_rider_schedules[antai_product_id]
    )


def assert_antai_cancer_lifetime_rider_rejected(document: dict) -> None:
    assert parse_antai_cancer_lifetime_rider_unit_table(document) is None
    assert parse_plan_table_with_parser(document) is None


for antai_f_document in TII_LIFE_116_TEXT_FIXTURE:
    if (
        antai_f_document.get("product_id")
        in ANTAI_CANCER_LIFETIME_RIDER_PRODUCT_IDS
        and antai_f_document.get("document_type") == "product_summary"
    ):
        assert_antai_cancer_lifetime_rider_rejected(antai_f_document)

antai_revision_one = antai_cancer_lifetime_rider_document("252321R11A00301")
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_one,
        "file_name": "252321R11A003-1-F.pdf",
        "document_type": "product_summary",
    }
)
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_one,
        "file_name": "252321R11A00301-A.pdf",
    }
)
for wrong_product_id in (
    "252321R11A0030",
    "252321R11A00300",
    "252321R11A00305",
):
    assert_antai_cancer_lifetime_rider_rejected(
        {**antai_revision_one, "product_id": wrong_product_id}
    )

antai_revision_four = antai_cancer_lifetime_rider_document("252321R11A00304")
antai_revision_four_text = normalize_terms_text(antai_revision_four["text"])
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_four,
        "text": antai_revision_four_text.replace(
            "安泰人壽防癌終身健康保險附約",
            "安泰人壽健康保險附約",
            1,
        ),
    }
)
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_four,
        "text": antai_revision_four_text.replace(
            "【癌症住院醫療保險金的給付】",
            "",
            1,
        ),
    }
)
assert "癌症化學治療保險金 800 元/日" in antai_revision_four_text
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_four,
        "text": antai_revision_four_text.replace(
            "癌症化學治療保險金 800 元/日",
            "癌症化學治療保險金 900 元/日",
            1,
        ),
    }
)
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_four,
        "text": antai_revision_four_text.replace(
            "【罹患癌症保險金的給付】 第八條",
            "【罹患癌症保險金的給付】 第七條",
            1,
        ),
    }
)
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_four,
        "text": antai_revision_four_text.replace(
            "的百分之十五乘以",
            "的百分之十六乘以",
            1,
        ),
    }
)

required_restriction_signals = (
    "自本附約生效日(或自復效日、加保生效日)起且持續有效九十日以後",
    "於出院後十四日內再次住院時",
    "自接受前次外科切除手術治療當日起十四日內(含)之所有外科切除手術",
    "以血管注射進行的化學治療法",
    "第二、三、四、五個罹患確定日之周年日午夜十二時終了時仍生存者",
    "自罹患確定日起算之第六年(含) 以後之各周年日",
    "第一期前列腺癌、原位癌或惡性黑色素瘤以外之皮膚癌時",
    "保險年齡達九十五歲後之第一個保單週年日午夜十二時即行終止",
)
for restriction_signal in required_restriction_signals:
    assert restriction_signal in antai_revision_four_text
    assert_antai_cancer_lifetime_rider_rejected(
        {
            **antai_revision_four,
            "text": antai_revision_four_text.replace(restriction_signal, "", 1),
        }
    )

antai_revision_two = antai_cancer_lifetime_rider_document("252321R11A00302")
assert antai_revision_two["text"].count("94107") == 1
assert_antai_cancer_lifetime_rider_rejected(
    {
        **antai_revision_two,
        "text": antai_revision_two["text"].replace("94107", "", 1),
    }
)
for source_id, target_id in (
    ("252321R11A00301", "252321R11A00302"),
    ("252321R11A00302", "252321R11A00301"),
    ("252321R11A00303", "252321R11A00304"),
    ("252321R11A00304", "252321R11A00303"),
):
    source_document = antai_cancer_lifetime_rider_document(source_id)
    assert_antai_cancer_lifetime_rider_rejected(
        {
            **source_document,
            "product_id": target_id,
            "file_name": ANTAI_CANCER_LIFETIME_RIDER_FILES[target_id],
        }
    )


NEW_CANCER_LIFETIME_HEADINGS = " ".join(
    [
        "安泰人壽新防癌終身健康保險",
        "【保險範圍】 第九條",
        "【保險範圍(一)-『罹患癌症保險金』的給付】 第十條",
        "【保險範圍(二)-『癌症住院醫療保險金』的給付】 第十一條",
        "【保險範圍(三)-『癌症出院療養保險金』的給付】 第十二條",
        "【保險範圍(四)-『癌症門診醫療保險金』的給付】 第十三條",
        "【保險範圍(五)-『癌症手術醫療保險金』的給付】 第十四條",
        "【保險範圍(六)-『癌症放射線治療保險金』的給付】 第十五條",
        "【保險範圍(七)-『癌症化學治療保險金』的給付】 第十六條",
        "【保險範圍(八)-『骨髓或幹細胞移植保險金』的給付】 第十七條",
        "【保險範圍(九)-『完全殘廢保險金』的給付】 第十八條",
        "【保險範圍(十)-『身故保險金或喪葬費用保險金』的給付】 第十九條",
        "【保險範圍(十一)-『祝壽保險金』的給付】 第二十條",
    ]
).replace("『", "「").replace("』", "」")
NEW_CANCER_LIFETIME_CLAUSES = " ".join(
    [
        "自本契約生效日(或復效日)起且持續有效九十日以後",
        "於出院後十四日內再次住院時",
        "不論其每日門診次數為一次或多次，均以一日計",
        "不論其每日治療次數為一次或多次，均以一日計",
        "以注射方式接受化學治療，不論其每日接受化學治療次數為一次或多次，均以一日計",
        "本契約有效期間內『骨髓或幹細胞移植保險金』的給付以一次為限",
        "保險年齡達一百一十歲後之保單周年日",
        "扣除第十條至第十七條已給付之各項保險金累計數額後之餘額",
    ]
).replace("『", "「").replace("』", "」")
NEW_CANCER_LIFETIME_TABLE = " ".join(
    [
        "第 8 頁，共 10 頁",
        "附表一 各項保險金『每承保單位給付金額』",
        "繳費期間內 50,000 元 7,500 元 特定癌症",
        "繳費期間屆滿後 75,000 元 11,250 元 特定癌症",
        "第 1-90 日 1,200 元/日 癌症住院醫療保險金同一次住院第 91 日起 1,800 元/日",
        "癌症出院療養保險金 600 元/日",
        "癌症門診醫療保險金 500 元/日",
        "特定癌症惡性腫瘤切除 3,000 元/次",
        "癌症手術醫療保險金 惡性腫瘤切除 15,000 元/次",
        "癌症放射線治療保險金 500 元/日",
        "癌症化學治療保險金 1,200 元/日",
        "骨髓或幹細胞移植保險金 50,000 元",
        "完全殘廢保險金 每一承保單位新臺幣 100 萬元扣除已給付的各項保險金累計數額後之餘額",
        "身故保險金或喪葬費用保險金 每一承保單位新臺幣 100 萬元扣除已給付的各項保險金累計數額後之餘額",
        "祝壽保險金 每一承保單位新臺幣 100 萬元扣除已給付的各項保險金累計數額後之餘額",
        "每一承保單位之總給付金額以新臺幣 100 萬元為上限",
        "附表二 完全殘廢程度表",
    ]
).replace("『", "「").replace("』", "」")


def new_cancer_lifetime_document(
    product_id: str,
    *,
    revised_funeral_rule: bool = False,
    file_name: str | None = None,
    document_type: str = "policy_terms",
    text: str | None = None,
):
    funeral_clause = (
        "遺產及贈與稅法第十七條有關遺產稅喪葬費扣除額之半數"
        if revised_funeral_rule
        else "主管機關所訂定之喪葬費用額度上限"
    )
    return {
        "product_id": product_id,
        "file_name": file_name or f"{product_id}-A.pdf",
        "document_type": document_type,
        "text": text
        or f"{NEW_CANCER_LIFETIME_HEADINGS} {NEW_CANCER_LIFETIME_CLAUSES} {funeral_clause} {NEW_CANCER_LIFETIME_TABLE}",
    }


new_cancer_original = parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document("252321M12B00100")
)
assert new_cancer_original is not None
assert new_cancer_original["selection_type"] == "unit"
assert new_cancer_original["selection_label"] == "承保單位數"
assert new_cancer_original["version_characteristics"] == {
    "cancer_waiting_days": 90,
    "specific_cancer_rate_percent": 15,
    "per_unit_total_cap": 1_000_000,
    "funeral_benefit_rule": "pre-2010-fixed-funeral-cap",
    "minor_death_or_disability_refund_rule": False,
    "maturity_age": 110,
}
new_cancer_entries = {
    entry["id"]: entry for entry in new_cancer_original["coverage_entries"]
}
assert len(new_cancer_entries) == 14
assert new_cancer_entries["cancer-diagnosis"]["amount_tiers"] == [
    {"label": "繳費期間內／癌症疾病", "amount": 50_000},
    {"label": "繳費期間內／特定癌症", "amount": 7_500},
    {"label": "繳費期滿後／癌症疾病", "amount": 75_000},
    {"label": "繳費期滿後／特定癌症", "amount": 11_250},
]
assert new_cancer_entries["cancer-hospital-days-1-90"]["amount"] == 1_200
assert new_cancer_entries["cancer-hospital-days-91-plus"]["amount"] == 1_800
assert new_cancer_entries["cancer-discharge-recovery"]["amount"] == 600
assert new_cancer_entries["cancer-outpatient"]["amount"] == 500
assert new_cancer_entries["specific-cancer-surgery"]["amount"] == 3_000
assert new_cancer_entries["malignant-tumor-surgery"]["amount"] == 15_000
assert new_cancer_entries["cancer-radiation"]["amount"] == 500
assert new_cancer_entries["cancer-chemotherapy"]["amount"] == 1_200
assert new_cancer_entries["marrow-stem-cell-transplant"]["amount"] == 50_000
for entry_id in [
    "total-disability-remaining-pool",
    "death-funeral-remaining-pool",
    "maturity-remaining-pool",
]:
    assert new_cancer_entries[entry_id]["amount"] == 1_000_000
    assert new_cancer_entries[entry_id]["aggregation_rule"] == "cumulative_cap"
    assert "已給付" in new_cancer_entries[entry_id]["note"]
assert new_cancer_entries["lifetime-total-benefit-cap"]["amount"] == 1_000_000

new_cancer_revision_three = parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document("209321M12B00303", revised_funeral_rule=True)
)
assert new_cancer_revision_three is not None
assert new_cancer_revision_three["version_characteristics"]["funeral_benefit_rule"] == (
    "2010-estate-tax-half-deduction"
)
assert (
    new_cancer_revision_three["version_characteristics"][
        "minor_death_or_disability_refund_rule"
    ]
    is False
)
assert new_cancer_revision_three["version_characteristics"]["maturity_age"] == 110
revision_three_death = next(
    entry
    for entry in new_cancer_revision_three["coverage_entries"]
    if entry["id"] == "death-funeral-remaining-pool"
)
assert "同公司多張契約" in revision_three_death["conditions"][-1]

TII_LIFE_050_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
for fubon_new_cancer_product_id in [
    "209321M12B00304",
    "209321M12B00305",
    "209321M12B00306",
    "209321M12B00307",
]:
    fubon_new_cancer_terms = next(
        document
        for document in TII_LIFE_050_TEXT_FIXTURE
        if document.get("product_id") == fubon_new_cancer_product_id
        and document.get("file_name") == f"{fubon_new_cancer_product_id}-A.pdf"
    )
    fubon_new_cancer_schedule = parse_antai_fubon_new_cancer_lifetime_unit_table(
        fubon_new_cancer_terms
    )
    assert fubon_new_cancer_schedule is not None
    assert len(fubon_new_cancer_schedule["coverage_entries"]) == 14
    assert fubon_new_cancer_schedule["version_characteristics"] == {
        "cancer_waiting_days": 90,
        "specific_cancer_rate_percent": 15,
        "per_unit_total_cap": 1_000_000,
        "funeral_benefit_rule": "2010-estate-tax-half-deduction",
        "minor_death_or_disability_refund_rule": True,
        "maturity_age": 111,
    }
    fubon_new_cancer_entries = {
        entry["id"]: entry for entry in fubon_new_cancer_schedule["coverage_entries"]
    }
    assert fubon_new_cancer_entries["cancer-diagnosis"]["amount_tiers"] == [
        {"label": "繳費期間內／癌症疾病", "amount": 50_000},
        {"label": "繳費期間內／特定癌症", "amount": 7_500},
        {"label": "繳費期滿後／癌症疾病", "amount": 75_000},
        {"label": "繳費期滿後／特定癌症", "amount": 11_250},
    ]
    assert fubon_new_cancer_entries["cancer-hospital-days-1-90"]["amount"] == 1_200
    assert fubon_new_cancer_entries["cancer-hospital-days-91-plus"]["amount"] == 1_800
    assert fubon_new_cancer_entries["cancer-discharge-recovery"]["amount"] == 600
    assert fubon_new_cancer_entries["cancer-outpatient"]["amount"] == 500
    assert fubon_new_cancer_entries["specific-cancer-surgery"]["amount"] == 3_000
    assert fubon_new_cancer_entries["malignant-tumor-surgery"]["amount"] == 15_000
    assert fubon_new_cancer_entries["cancer-radiation"]["amount"] == 500
    assert fubon_new_cancer_entries["cancer-chemotherapy"]["amount"] == 1_200
    assert fubon_new_cancer_entries["marrow-stem-cell-transplant"]["amount"] == 50_000
    assert (
        fubon_new_cancer_entries["maturity-remaining-pool"]["conditions"][-1]
        == "保險年齡到達 111 歲時仍生存"
    )

assert parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document("unrelated-product")
) is None
assert parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document(
        "252321M12B00100",
        file_name="252321M12B00100-F.pdf",
        document_type="product_summary",
    )
) is None
assert parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document(
        "252321M12B00100",
        text=(
            f"{NEW_CANCER_LIFETIME_HEADINGS} {NEW_CANCER_LIFETIME_CLAUSES} "
            f"{NEW_CANCER_LIFETIME_TABLE.replace('1,200 元/日', '')}"
        ),
    )
) is None
assert parse_antai_fubon_new_cancer_lifetime_unit_table(
    new_cancer_lifetime_document(
        "209321M12B00303",
        revised_funeral_rule=False,
    )
) is None

ANTAI_NEW_CANCER_R11_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-116"
    / "252321R11A00200"
    / "252321R11A002-A.pdf"
)
antai_new_cancer_r11_reader = PdfReader(ANTAI_NEW_CANCER_R11_PATH, strict=False)
antai_new_cancer_r11_text = normalize_terms_text(
    "\n".join(page.extract_text() or "" for page in antai_new_cancer_r11_reader.pages)
)
antai_new_cancer_r11_document = {
    "product_id": "252321R11A00200",
    "file_name": "252321R11A002-A.pdf",
    "document_type": "policy_terms",
    "page_count": len(antai_new_cancer_r11_reader.pages),
    "pages_parsed": len(antai_new_cancer_r11_reader.pages),
    "text": antai_new_cancer_r11_text,
}
antai_new_cancer_r11 = parse_antai_new_cancer_lifetime_r11_unit_table(
    antai_new_cancer_r11_document
)
assert antai_new_cancer_r11 is not None
assert antai_new_cancer_r11["selection_type"] == "unit"
assert antai_new_cancer_r11["selection_label"] == "承保單位數"
assert antai_new_cancer_r11["version_characteristics"] == {
    "terms_revision": "90-approved-original",
    "cancer_observation_days": 30,
    "minor_cancer_rate_percent": 15,
    "hospital_days_tier_one_limit": 90,
    "same_cancer_readmission_days": 14,
    "hospice_anniversary_payments": 5,
    "hospice_excluded_for_minor_cancer": True,
    "post_death_last_hospitalization_date_basis": True,
    "post_death_diagnosis_only_if_no_cancer_hospitalization": True,
    "premium_period_diagnosis_amount": 50_000,
    "post_premium_period_diagnosis_amount": 75_000,
}
antai_new_cancer_r11_entries = {
    entry["id"]: entry for entry in antai_new_cancer_r11["coverage_entries"]
}
assert len(antai_new_cancer_r11_entries) == 10
assert antai_new_cancer_r11_entries["cancer-diagnosis"]["amount_tiers"] == [
    {"label": "繳費期間內一般癌症", "amount": 50_000},
    {"label": "繳費期間屆滿後一般癌症", "amount": 75_000},
    {"label": "繳費期間內第一期前列腺癌或原位癌", "amount": 7_500},
    {"label": "繳費期間屆滿後第一期前列腺癌或原位癌", "amount": 11_250},
]
assert antai_new_cancer_r11_entries["cancer-hospital-days-1-90"]["amount"] == 1_200
assert antai_new_cancer_r11_entries["cancer-hospital-days-91-plus"]["amount"] == 1_800
assert antai_new_cancer_r11_entries["cancer-discharge-recuperation"]["amount"] == 600
assert antai_new_cancer_r11_entries["cancer-surgery"]["amount_tiers"] == [
    {"label": "一般癌症手術", "amount": 15_000},
    {"label": "第一期前列腺癌或原位癌手術", "amount": 2_250},
]
assert antai_new_cancer_r11_entries["cancer-outpatient"]["amount"] == 500
assert antai_new_cancer_r11_entries["cancer-radiation"]["amount"] == 500
assert antai_new_cancer_r11_entries["cancer-chemotherapy"]["amount"] == 800
assert antai_new_cancer_r11_entries["cancer-hospice-anniversary"]["amount"] == 20_000
assert (
    "第一期前列腺癌或原位癌不給付"
    in antai_new_cancer_r11_entries["cancer-hospice-anniversary"]["conditions"][-1]
)
assert (
    parse_plan_table_with_parser(antai_new_cancer_r11_document)[0]
    == "antai-new-cancer-lifetime-r11-unit-v1"
)
antai_new_cancer_r11_partial = {
    **antai_new_cancer_r11_document,
    "page_count": 3,
    "pages_parsed": 3,
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in antai_new_cancer_r11_reader.pages[:3]
        )
    ),
}
antai_new_cancer_r11_completed = complete_strict_source_document(
    antai_new_cancer_r11_partial, ANTAI_NEW_CANCER_R11_PATH
)
assert antai_new_cancer_r11_completed["page_count"] == 10
assert parse_antai_new_cancer_lifetime_r11_unit_table(
    antai_new_cancer_r11_completed
) is not None
assert parse_antai_new_cancer_lifetime_r11_unit_table(
    {**antai_new_cancer_r11_document, "product_id": "unrelated-product"}
) is None
assert parse_antai_new_cancer_lifetime_r11_unit_table(
    {**antai_new_cancer_r11_document, "file_name": "252321R11A002-F.pdf"}
) is None
assert parse_antai_new_cancer_lifetime_r11_unit_table(
    {
        **antai_new_cancer_r11_document,
        "text": antai_new_cancer_r11_text.replace("800 元/日癌症安寧", "900 元/日癌症安寧"),
    }
) is None


ANTAI_SPECIFIC_MAJOR_DISEASE_PRODUCT_FILES = {
    "269211M12D02100": ("269211M12D021-A.pdf", "95-approved-original"),
    "269211M12D02101": ("269211M12D02101-A.pdf", "95-first-partial-change"),
    "269211M12D02102": ("269211M12D02102-A.pdf", "96-second-partial-change"),
    "269211M12D02103": ("269211M12D02103-A.pdf", "97-third-partial-change"),
}


def antai_specific_major_disease_document(product_id: str) -> dict:
    file_name, _terms_revision = ANTAI_SPECIFIC_MAJOR_DISEASE_PRODUCT_FILES[
        product_id
    ]
    path = (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-documents"
        / "tii-life-175"
        / product_id
        / file_name
    )
    reader = PdfReader(path, strict=False)
    return {
        "product_id": product_id,
        "file_name": file_name,
        "document_type": "policy_terms",
        "page_count": len(reader.pages),
        "pages_parsed": len(reader.pages),
        "text": normalize_terms_text(
            "\n".join(page.extract_text() or "" for page in reader.pages)
        ),
    }


antai_specific_major_disease_schedules = {}
for antai_product_id, (
    antai_file_name,
    antai_terms_revision,
) in ANTAI_SPECIFIC_MAJOR_DISEASE_PRODUCT_FILES.items():
    antai_document = antai_specific_major_disease_document(antai_product_id)
    assert antai_document["file_name"] == antai_file_name
    antai_schedule = parse_antai_specific_major_disease_health_unit_table(
        antai_document
    )
    assert antai_schedule is not None
    antai_specific_major_disease_schedules[antai_product_id] = antai_schedule
    integrated_parse = parse_plan_table_with_parser(antai_document)
    assert integrated_parse is not None
    assert integrated_parse[0] == "antai-specific-major-disease-health-unit-v1"
    assert integrated_parse[1] == antai_schedule
    assert antai_schedule["selection_type"] == "unit"
    assert antai_schedule["selection_label"] == "投保單位"
    assert "投保單位數" in antai_schedule["selection_guidance"]
    assert antai_schedule["version_characteristics"] == {
        "terms_revision": antai_terms_revision,
        "disease_waiting_days": 30,
        "cancer_initial_waiting_days": 90,
        "major_disease_waiting_days": 30,
        "initial_cancer_lifetime_limit_times": 1,
        "specific_cancer_lifetime_limit_times": 1,
        "myocardial_infarction_or_coronary_bypass_lifetime_limit_times": 1,
        "stroke_lifetime_limit_times": 1,
        "systemic_lupus_lifetime_limit_times": 1,
        "reconstruction_claim_days": 365,
        "same_reconstruction_item_lifetime_limit_times": 1,
        "claims_notification_days": 10,
        "claim_payment_days_after_complete_documents": 15,
    }
    antai_entries = {
        entry["id"]: entry for entry in antai_schedule["coverage_entries"]
    }
    assert set(antai_entries) == {
        "initial-cancer",
        "specific-cancer",
        "myocardial-infarction-or-coronary-bypass",
        "stroke",
        "systemic-lupus-erythematosus",
        "pregnancy-childbirth-death",
        "reconstruction-prosthetic-eye",
        "reconstruction-prosthetic-limb",
        "reconstruction-breast",
        "reconstruction-skin-graft",
    }
    assert antai_entries["initial-cancer"]["amount"] == 100_000
    assert antai_entries["specific-cancer"]["amount"] == 200_000
    assert (
        antai_entries["myocardial-infarction-or-coronary-bypass"]["amount"]
        == 200_000
    )
    assert antai_entries["stroke"]["amount"] == 200_000
    assert antai_entries["systemic-lupus-erythematosus"]["amount"] == 200_000
    assert antai_entries["pregnancy-childbirth-death"]["amount"] == 100_000
    assert antai_entries["reconstruction-prosthetic-eye"]["amount"] == 10_000
    assert antai_entries["reconstruction-prosthetic-limb"]["amount"] == 10_000
    assert antai_entries["reconstruction-breast"]["amount"] == 10_000
    assert antai_entries["reconstruction-skin-graft"]["amount"] == 10_000
    assert all(
        entry["basis"] == "per_unit"
        and entry["calculation_basis"] == "per_unit"
        and entry["source"] == "terms"
        and entry.get("conditions")
        for entry in antai_entries.values()
    )
    assert "第 91 日" in antai_entries["initial-cancer"]["conditions"][0]
    assert "365 日" in antai_entries["reconstruction-skin-graft"]["conditions"][1]

antai_specific_major_disease_signature = {
    json.dumps(
        [
            (entry["id"], entry["amount"])
            for entry in schedule["coverage_entries"]
        ],
        ensure_ascii=False,
    )
    for schedule in antai_specific_major_disease_schedules.values()
}
assert len(antai_specific_major_disease_signature) == 1
antai_specific_major_disease_partial = {
    **antai_specific_major_disease_document("269211M12D02103"),
    "page_count": 3,
    "pages_parsed": 3,
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in PdfReader(
                Path(__file__).resolve().parents[1]
                / "work"
                / "tii-documents"
                / "tii-life-175"
                / "269211M12D02103"
                / "269211M12D02103-A.pdf",
                strict=False,
            ).pages[:3]
        )
    ),
}
antai_specific_major_disease_completed = complete_strict_source_document(
    antai_specific_major_disease_partial,
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-175"
    / "269211M12D02103"
    / "269211M12D02103-A.pdf",
)
assert antai_specific_major_disease_completed["page_count"] == 7
assert parse_antai_specific_major_disease_health_unit_table(
    antai_specific_major_disease_completed
) == antai_specific_major_disease_schedules["269211M12D02103"]
antai_specific_major_disease_document_03 = antai_specific_major_disease_document(
    "269211M12D02103"
)
assert parse_antai_specific_major_disease_health_unit_table(
    {**antai_specific_major_disease_document_03, "product_id": "wrong-product"}
) is None
assert parse_antai_specific_major_disease_health_unit_table(
    {**antai_specific_major_disease_document_03, "file_name": "269211M12D02103-F.pdf"}
) is None
assert parse_antai_specific_major_disease_health_unit_table(
    {
        **antai_specific_major_disease_document_03,
        "text": antai_specific_major_disease_document_03["text"].replace(
            "初次罹患癌症保險金 100,000 元",
            "初次罹患癌症保險金 101,000 元",
            1,
        ),
    }
) is None


ANTAI_CANCER_MEDICAL_TERM_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-116"
    / "252321R11A00100"
    / "252321R11A001-A.pdf"
)
antai_cancer_medical_term_reader = PdfReader(
    ANTAI_CANCER_MEDICAL_TERM_PATH, strict=False
)
antai_cancer_medical_term_text = normalize_terms_text(
    "\n".join(
        page.extract_text() or "" for page in antai_cancer_medical_term_reader.pages
    )
)
antai_cancer_medical_term_document = {
    "product_id": "252321R11A00100",
    "file_name": "252321R11A001-A.pdf",
    "document_type": "policy_terms",
    "page_count": len(antai_cancer_medical_term_reader.pages),
    "pages_parsed": len(antai_cancer_medical_term_reader.pages),
    "text": antai_cancer_medical_term_text,
}
antai_cancer_medical_term_schedule = parse_antai_cancer_medical_term_family_unit(
    antai_cancer_medical_term_document
)
assert antai_cancer_medical_term_schedule is not None
assert (
    parse_plan_table_with_parser(antai_cancer_medical_term_document)[0]
    == "antai-cancer-medical-term-family-unit-v1"
)
assert antai_cancer_medical_term_schedule["selection_type"] == "plan_unit"
assert antai_cancer_medical_term_schedule["selection_label"] == (
    "家庭型別與被保險人角色 + 承保單位數"
)
assert antai_cancer_medical_term_schedule["version_characteristics"] == {
    "terms_revision": "87-third-revision",
    "cancer_waiting_days": 90,
    "cancer_includes_carcinoma_in_situ": True,
    "family_type_options": True,
    "child_entry_age_limit": 23,
    "newborn_child_covered_from_birth": True,
    "same_cancer_readmission_days": 90,
    "radiation_annual_days_limit": 60,
    "chemotherapy_annual_days_limit": 60,
    "post_death_presumed_cancer_start_days": 30,
    "premium_waiver_main_contract_death_or_disability": True,
}
assert [option["value"] for option in antai_cancer_medical_term_schedule["plan_options"]] == [
    "individual-main",
    "single-parent-main",
    "single-parent-child",
    "two-parent-main",
    "two-parent-spouse",
    "two-parent-child",
]
adult_entries = {
    entry["id"]: entry
    for entry in antai_cancer_medical_term_schedule["plan_options"][0][
        "coverage_entries"
    ]
}
child_entries = {
    entry["id"]: entry
    for entry in antai_cancer_medical_term_schedule["plan_options"][2][
        "coverage_entries"
    ]
}
assert set(adult_entries) == {
    "cancer-diagnosis",
    "cancer-hospital-days-1-90",
    "cancer-hospital-days-91-plus",
    "cancer-discharge-recuperation",
    "cancer-surgery",
    "cancer-outpatient",
    "cancer-radiation",
    "cancer-chemotherapy",
    "cancer-death",
}
assert adult_entries["cancer-diagnosis"]["amount"] == 15_000
assert adult_entries["cancer-hospital-days-1-90"]["amount"] == 1_200
assert adult_entries["cancer-hospital-days-91-plus"]["amount"] == 1_800
assert adult_entries["cancer-discharge-recuperation"]["amount"] == 600
assert adult_entries["cancer-surgery"]["amount"] == 15_000
assert adult_entries["cancer-outpatient"]["amount"] == 500
assert adult_entries["cancer-radiation"]["amount"] == 500
assert adult_entries["cancer-chemotherapy"]["amount"] == 800
assert adult_entries["cancer-death"]["amount"] == 100_000
assert child_entries["cancer-diagnosis"]["amount"] == 7_500
assert child_entries["cancer-hospital-days-1-90"]["amount"] == 600
assert child_entries["cancer-hospital-days-91-plus"]["amount"] == 900
assert child_entries["cancer-discharge-recuperation"]["amount"] == 300
assert child_entries["cancer-surgery"]["amount"] == 7_500
assert child_entries["cancer-outpatient"]["amount"] == 250
assert child_entries["cancer-radiation"]["amount"] == 250
assert child_entries["cancer-chemotherapy"]["amount"] == 400
assert child_entries["cancer-death"]["amount"] == 50_000
assert all(
    entry["basis"] in {"per_unit", "daily_per_unit"}
    and entry["source"] == "terms"
    and entry.get("conditions")
    for entry in adult_entries.values()
)
antai_cancer_medical_term_partial = {
    **antai_cancer_medical_term_document,
    "page_count": 3,
    "pages_parsed": 3,
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in antai_cancer_medical_term_reader.pages[:3]
        )
    ),
}
antai_cancer_medical_term_completed = complete_strict_source_document(
    antai_cancer_medical_term_partial, ANTAI_CANCER_MEDICAL_TERM_PATH
)
assert antai_cancer_medical_term_completed["page_count"] == 9
assert parse_antai_cancer_medical_term_family_unit(
    antai_cancer_medical_term_completed
) == antai_cancer_medical_term_schedule
assert parse_antai_cancer_medical_term_family_unit(
    {**antai_cancer_medical_term_document, "product_id": "wrong-product"}
) is None
assert parse_antai_cancer_medical_term_family_unit(
    {**antai_cancer_medical_term_document, "file_name": "252321R11A001-F.pdf"}
) is None
assert parse_antai_cancer_medical_term_family_unit(
    {**antai_cancer_medical_term_document, "page_count": 8}
) is None
assert parse_antai_cancer_medical_term_family_unit(
    {
        **antai_cancer_medical_term_document,
        "text": antai_cancer_medical_term_text.replace(
            "100,000 元 100,000 元 100,000 元",
            "101,000 元 101,000 元 101,000 元",
            1,
        ),
    }
) is None


TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PRODUCT_ID = "202321RZ1A13B21A11E10000000"
TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-008"
    / TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PRODUCT_ID
    / f"{TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PRODUCT_ID}-A.pdf"
)
taiwan_drug_anxin_reader = PdfReader(
    TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PATH, strict=False
)
taiwan_drug_anxin_document = {
    "product_id": TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PRODUCT_ID,
    "file_name": TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PATH.name,
    "document_type": "policy_terms",
    "page_count": len(taiwan_drug_anxin_reader.pages),
    "pages_parsed": len(taiwan_drug_anxin_reader.pages),
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in taiwan_drug_anxin_reader.pages)
    ),
}
taiwan_drug_anxin_schedule = parse_taiwan_drug_anxin_cancer_precision_plan_table(
    taiwan_drug_anxin_document
)
assert taiwan_drug_anxin_schedule is not None
assert (
    parse_plan_table_with_parser(taiwan_drug_anxin_document)[0]
    == "taiwan-life-drug-anxin-cancer-precision-plan-v1"
)
assert taiwan_drug_anxin_schedule["selection_type"] == "plan"
assert taiwan_drug_anxin_schedule["selection_label"] == "投保計劃別"
assert taiwan_drug_anxin_schedule["version_characteristics"] == {
    "terms_revision": "114-original",
    "cancer_waiting_days": 90,
    "non_guaranteed_renewal": True,
    "maximum_renewal_age": 75,
    "post_cancer_claim_window_years": 3,
    "cancer_includes_carcinoma_in_situ": True,
    "drug_table_item_count": 85,
    "health_promotion_renewal_discount_available": True,
}
assert [plan["label"] for plan in taiwan_drug_anxin_schedule["plan_options"]] == [
    "計劃一",
    "計劃二",
]
plan_1_entries = {
    entry["id"]: entry
    for entry in taiwan_drug_anxin_schedule["plan_options"][0]["coverage_entries"]
}
plan_2_entries = {
    entry["id"]: entry
    for entry in taiwan_drug_anxin_schedule["plan_options"][1]["coverage_entries"]
}
assert plan_1_entries["post-cancer-gene-test"]["amount"] == 100_000
assert plan_2_entries["post-cancer-gene-test"]["amount"] == 150_000
assert plan_1_entries["post-cancer-targeted-drug-cumulative-limit"]["amount"] == 3_000_000
assert plan_2_entries["post-cancer-targeted-drug-cumulative-limit"]["amount"] == 5_000_000
assert plan_1_entries["post-cancer-targeted-drug-cumulative-limit"]["amount_tiers"] == [
    {"label": "捷癌寧 Verzenio / 150mg", "amount": 1_030},
    {"label": "沛斯博 Besponsa / 1mg", "amount": 370_250},
    {"label": "寬利安 Qarziba / 20.25mg", "amount": 298_198},
    {"label": "銳癌寧 Retsevmo / 80mg", "amount": 3_502},
]
taiwan_drug_anxin_partial = {
    **taiwan_drug_anxin_document,
    "page_count": 4,
    "pages_parsed": 4,
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in taiwan_drug_anxin_reader.pages[:4])
    ),
}
taiwan_drug_anxin_completed = complete_strict_source_document(
    taiwan_drug_anxin_partial, TAIWAN_DRUG_ANXIN_CANCER_PRECISION_PATH
)
assert taiwan_drug_anxin_completed["page_count"] == 10
assert parse_taiwan_drug_anxin_cancer_precision_plan_table(
    taiwan_drug_anxin_completed
) == taiwan_drug_anxin_schedule
assert parse_taiwan_drug_anxin_cancer_precision_plan_table(
    {**taiwan_drug_anxin_document, "product_id": "wrong-product"}
) is None
assert parse_taiwan_drug_anxin_cancer_precision_plan_table(
    {**taiwan_drug_anxin_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_drug_anxin_cancer_precision_plan_table(
    {**taiwan_drug_anxin_document, "page_count": 9}
) is None
assert parse_taiwan_drug_anxin_cancer_precision_plan_table(
    {
        **taiwan_drug_anxin_document,
        "text": taiwan_drug_anxin_document["text"].replace("300 萬元 500 萬元", "301 萬元 500 萬元", 1),
    }
) is None


TAIWAN_TAIPEI_STUDENT_GROUP_PRODUCT_ID = "202316M12G78103"
TAIWAN_TAIPEI_STUDENT_GROUP_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-008"
    / TAIWAN_TAIPEI_STUDENT_GROUP_PRODUCT_ID
    / f"{TAIWAN_TAIPEI_STUDENT_GROUP_PRODUCT_ID}-A.pdf"
)
taiwan_taipei_student_group_reader = PdfReader(
    TAIWAN_TAIPEI_STUDENT_GROUP_PATH, strict=False
)
taiwan_taipei_student_group_document = {
    "product_id": TAIWAN_TAIPEI_STUDENT_GROUP_PRODUCT_ID,
    "file_name": TAIWAN_TAIPEI_STUDENT_GROUP_PATH.name,
    "document_type": "policy_terms",
    "page_count": len(taiwan_taipei_student_group_reader.pages),
    "pages_parsed": len(taiwan_taipei_student_group_reader.pages),
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in taiwan_taipei_student_group_reader.pages
        )
    ),
}
taiwan_taipei_student_group_schedule = (
    parse_taiwan_taipei_student_group_fixed_schedule(
        taiwan_taipei_student_group_document
    )
)
assert taiwan_taipei_student_group_schedule is not None
assert (
    parse_plan_table_with_parser(taiwan_taipei_student_group_document)[0]
    == "taiwan-life-taipei-student-group-fixed-schedule-v1"
)
assert (
    taiwan_taipei_student_group_schedule["selection_type"]
    == taiwan_taipei_student_group_schedule["input_mode"]
    == "fixed"
)
assert taiwan_taipei_student_group_schedule["selection_label"] == "固定學生團體保險給付"
assert taiwan_taipei_student_group_schedule["version_characteristics"] == {
    "terms_revision": "102-third-revision",
    "disease_death_amount": 1_000_000,
    "accidental_death_amount": 2_000_000,
    "disease_disability_levels": 6,
    "accident_disability_levels": 6,
    "disability_living_assistance_levels": "1-2",
    "disability_living_assistance_annual_payments": 4,
    "hospital_daily_days_limit": 90,
    "same_hospital_readmission_days": 14,
    "post_accident_benefit_days_limit": 180,
    "disease_death_disability_period_cap": 1_000_000,
    "accidental_death_period_cap": 2_000_000,
    "low_income_project_subsidy": True,
    "collective_food_poisoning_min_people": 5,
    "facial_reconstruction_labor_disability_item": 57,
}
taipei_entries = {
    entry["id"]: entry
    for entry in taiwan_taipei_student_group_schedule["coverage_entries"]
}
assert set(taipei_entries) == {
    "disease-death",
    "accidental-death",
    "disease-disability",
    "accident-disability",
    "disability-living-assistance-annual",
    "inpatient-medical-reimbursement-limit",
    "hospital-daily-allowance",
    "accident-outpatient-medical-limit",
    "major-surgery",
    "major-burn",
    "low-income-project-subsidy-limit",
    "collective-food-poisoning",
    "major-accident-or-fracture-inpatient-limit",
    "facial-reconstruction-limit",
}
assert taipei_entries["disease-death"]["amount"] == 1_000_000
assert taipei_entries["accidental-death"]["amount"] == 2_000_000
assert taipei_entries["disease-disability"]["amount_tiers"] == [
    {"label": "第一級", "amount": 600_000},
    {"label": "第二級", "amount": 500_000},
    {"label": "第三級", "amount": 400_000},
    {"label": "第四級", "amount": 300_000},
    {"label": "第五級", "amount": 200_000},
    {"label": "第六級", "amount": 100_000},
]
assert taipei_entries["accident-disability"]["amount_tiers"] == [
    {"label": "第一級", "amount": 1_000_000},
    {"label": "第二級", "amount": 800_000},
    {"label": "第三級", "amount": 600_000},
    {"label": "第四級", "amount": 400_000},
    {"label": "第五級", "amount": 200_000},
    {"label": "第六級", "amount": 100_000},
]
assert taipei_entries["disability-living-assistance-annual"]["amount_tiers"] == [
    {"label": "第一級殘廢每週年", "amount": 300_000},
    {"label": "第二級殘廢每週年", "amount": 250_000},
]
assert taipei_entries["inpatient-medical-reimbursement-limit"]["amount"] == 100_000
assert taipei_entries["hospital-daily-allowance"]["amount"] == 600
assert taipei_entries["accident-outpatient-medical-limit"]["amount"] == 30_000
assert taipei_entries["major-surgery"]["amount"] == 50_000
assert taipei_entries["major-burn"]["amount"] == 30_000
assert taipei_entries["low-income-project-subsidy-limit"]["amount"] == 500_000
assert taipei_entries["collective-food-poisoning"]["amount"] == 3_000
assert taipei_entries["major-accident-or-fracture-inpatient-limit"]["amount"] == 30_000
assert taipei_entries["facial-reconstruction-limit"]["amount"] == 30_000
taipei_partial = {
    **taiwan_taipei_student_group_document,
    "page_count": 3,
    "pages_parsed": 3,
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in taiwan_taipei_student_group_reader.pages[:3]
        )
    ),
}
taipei_completed = complete_strict_source_document(
    taipei_partial, TAIWAN_TAIPEI_STUDENT_GROUP_PATH
)
assert taipei_completed["page_count"] == 11
assert parse_taiwan_taipei_student_group_fixed_schedule(
    taipei_completed
) == taiwan_taipei_student_group_schedule
assert parse_taiwan_taipei_student_group_fixed_schedule(
    {**taiwan_taipei_student_group_document, "product_id": "wrong-product"}
) is None
assert parse_taiwan_taipei_student_group_fixed_schedule(
    {**taiwan_taipei_student_group_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_taipei_student_group_fixed_schedule(
    {**taiwan_taipei_student_group_document, "page_count": 10}
) is None
assert parse_taiwan_taipei_student_group_fixed_schedule(
    {
        **taiwan_taipei_student_group_document,
        "text": taiwan_taipei_student_group_document["text"].replace(
            "意外身故保險金」新台幣二百萬元",
            "意外身故保險金」新台幣二百一十萬元",
            1,
        ),
    }
) is None


CHAOYANG_XINGNONG_STUDENT_GROUP_PRODUCT_IDS = [
    "212217M11A01500",
    "212217M11A01501",
    "212217M11A01502",
]
CHAOYANG_XINGNONG_STUDENT_GROUP_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-067"
)


def chaoyang_xingnong_student_group_document(product_id: str) -> dict:
    pdf_path = (
        CHAOYANG_XINGNONG_STUDENT_GROUP_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(reader.pages),
        "pages_parsed": len(reader.pages),
        "text": normalize_terms_text(
            "\n".join(page.extract_text() or "" for page in reader.pages)
        ),
    }


chaoyang_xingnong_student_schedules = {}
for product_id in CHAOYANG_XINGNONG_STUDENT_GROUP_PRODUCT_IDS:
    document = chaoyang_xingnong_student_group_document(product_id)
    schedule = parse_chaoyang_xingnong_student_group_fixed_schedule(document)
    assert schedule is not None
    chaoyang_xingnong_student_schedules[product_id] = schedule
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "chaoyang-xingnong-student-group-fixed-schedule-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    assert schedule["selection_label"] == "固定學生團體保險給付"

assert chaoyang_xingnong_student_schedules["212217M11A01500"][
    "version_characteristics"
] == {
    "terms_revision": "88-original",
    "filing_date": "88.06.09",
    "filing_number": "台財保第882409589號",
    "revision_dates": ["93.12.29", "94.01.03"],
    "death_amount": 500_000,
    "disability_term": "殘廢",
    "disability_grade_count": 6,
    "disability_table_item_count": 28,
    "disability_living_assistance_grades": "1-2",
    "disability_living_assistance_annual_payments": 4,
    "inpatient_medical_limit": 50_000,
    "major_surgery_project_subsidy_limit": 120_000,
    "major_surgery_table_item_count": 25,
    "accident_outpatient_medical_limit": 5_000,
    "accident_outpatient_minimum_expense": 500,
    "same_hospital_readmission_days": 14,
    "major_surgery_claim_window_years": 1,
    "post_policy_claim_days_limit": 180,
    "death_disability_period_cap": 500_000,
}
assert chaoyang_xingnong_student_schedules["212217M11A01501"][
    "version_characteristics"
]["terms_revision"] == "93-first-revision"
assert chaoyang_xingnong_student_schedules["212217M11A01502"][
    "version_characteristics"
]["terms_revision"] == "94-second-revision"

chaoyang_xingnong_student_entries = {
    entry["id"]: entry
    for entry in chaoyang_xingnong_student_schedules["212217M11A01500"][
        "coverage_entries"
    ]
}
assert set(chaoyang_xingnong_student_entries) == {
    "death",
    "disability",
    "disability-living-assistance-annual",
    "inpatient-medical-reimbursement-limit",
    "major-surgery-project-subsidy-limit",
    "accident-outpatient-medical-limit",
}
assert chaoyang_xingnong_student_entries["death"]["amount"] == 500_000
assert chaoyang_xingnong_student_entries["disability"]["amount_tiers"] == [
    {"label": "第一級", "amount": 500_000},
    {"label": "第二級", "amount": 375_000},
    {"label": "第三級", "amount": 250_000},
    {"label": "第四級", "amount": 175_000},
    {"label": "第五級", "amount": 75_000},
    {"label": "第六級", "amount": 25_000},
]
assert chaoyang_xingnong_student_entries[
    "disability-living-assistance-annual"
]["amount_tiers"] == [
    {"label": "第一級第1年", "amount": 150_000},
    {"label": "第一級第2年", "amount": 200_000},
    {"label": "第一級第3年", "amount": 250_000},
    {"label": "第一級第4年", "amount": 300_000},
    {"label": "第二級第1年", "amount": 112_500},
    {"label": "第二級第2年", "amount": 150_000},
    {"label": "第二級第3年", "amount": 187_500},
    {"label": "第二級第4年", "amount": 225_000},
]
assert (
    chaoyang_xingnong_student_entries["inpatient-medical-reimbursement-limit"][
        "amount"
    ]
    == 50_000
)
assert (
    chaoyang_xingnong_student_entries["major-surgery-project-subsidy-limit"][
        "amount"
    ]
    == 120_000
)
assert (
    chaoyang_xingnong_student_entries["accident-outpatient-medical-limit"][
        "amount"
    ]
    == 5_000
)
assert "五百元" in " ".join(
    chaoyang_xingnong_student_entries["accident-outpatient-medical-limit"][
        "conditions"
    ]
)

chaoyang_xingnong_student_base = chaoyang_xingnong_student_group_document(
    "212217M11A01500"
)
chaoyang_xingnong_student_path = (
    CHAOYANG_XINGNONG_STUDENT_GROUP_ROOT
    / "212217M11A01500"
    / "212217M11A01500-A.pdf"
)
chaoyang_xingnong_student_reader = PdfReader(
    chaoyang_xingnong_student_path, strict=False
)
chaoyang_xingnong_student_partial = {
    **chaoyang_xingnong_student_base,
    "page_count": 2,
    "pages_parsed": 2,
    "text": normalize_terms_text(
        "\n".join(
            page.extract_text() or ""
            for page in chaoyang_xingnong_student_reader.pages[:2]
        )
    ),
}
chaoyang_xingnong_student_completed = complete_strict_source_document(
    chaoyang_xingnong_student_partial,
    chaoyang_xingnong_student_path,
)
assert chaoyang_xingnong_student_completed["page_count"] == 4
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    chaoyang_xingnong_student_completed
) == chaoyang_xingnong_student_schedules["212217M11A01500"]
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    {**chaoyang_xingnong_student_base, "product_id": "wrong-product"}
) is None
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    {**chaoyang_xingnong_student_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    {**chaoyang_xingnong_student_base, "document_type": "product_summary"}
) is None
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    {**chaoyang_xingnong_student_base, "page_count": 3}
) is None
assert parse_chaoyang_xingnong_student_group_fixed_schedule(
    {
        **chaoyang_xingnong_student_base,
        "text": chaoyang_xingnong_student_base["text"].replace(
            "身故保險金新台幣伍拾萬元",
            "身故保險金新台幣伍拾壹萬元",
            1,
        ),
    }
) is None


FUBON_FAMILY_GIFT_PRODUCT_ID = "209391M12G00700"
FUBON_FAMILY_GIFT_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-050"
    / FUBON_FAMILY_GIFT_PRODUCT_ID
    / f"{FUBON_FAMILY_GIFT_PRODUCT_ID}-A.pdf"
)
fubon_family_gift_reader = PdfReader(FUBON_FAMILY_GIFT_PATH, strict=False)
fubon_family_gift_document = {
    "product_id": FUBON_FAMILY_GIFT_PRODUCT_ID,
    "file_name": FUBON_FAMILY_GIFT_PATH.name,
    "document_type": "policy_terms",
    "page_count": len(fubon_family_gift_reader.pages),
    "pages_parsed": len(fubon_family_gift_reader.pages),
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in fubon_family_gift_reader.pages)
    ),
}
fubon_family_gift_schedule = parse_fubon_family_gift_accident_health_plan_table(
    fubon_family_gift_document
)
assert fubon_family_gift_schedule is not None
assert (
    parse_plan_table_with_parser(fubon_family_gift_document)[0]
    == "fubon-family-gift-accident-health-plan-v1"
)
assert fubon_family_gift_schedule["selection_type"] == "plan"
assert fubon_family_gift_schedule["selection_label"] == "投保計畫別"
assert fubon_family_gift_schedule["version_characteristics"] == {
    "terms_revision": "102-original",
    "plan_count": 5,
    "non_guaranteed_renewal": True,
    "maximum_renewal_age": 70,
    "cancer_waiting_days": 30,
    "cancer_classification": "original-two-tier",
    "general_hospital_days_limit": 60,
    "icu_days_limit": 7,
    "accident_treatment_window_days": 180,
    "accident_hospital_days_limit": 365,
    "major_burn_survival_days": 15,
    "disability_term": "殘廢",
    "disability_levels": 11,
    "disability_rate_min_percent": 5,
    "disability_rate_max_percent": 100,
    "same_hospital_readmission_days": 14,
    "short_term_rate_table": True,
}
assert [plan["label"] for plan in fubon_family_gift_schedule["plan_options"]] == [
    "計畫一",
    "計畫二",
    "計畫三",
    "計畫四",
    "計畫五",
]
fubon_plan_entries = [
    {entry["id"]: entry for entry in plan["coverage_entries"]}
    for plan in fubon_family_gift_schedule["plan_options"]
]
assert fubon_plan_entries[0]["life-death-or-funeral"]["amount"] == 2_000_000
assert fubon_plan_entries[1]["life-death-or-funeral"]["amount"] == 3_000_000
assert fubon_plan_entries[0]["first-carcinoma-in-situ"]["amount"] == 5_000
assert fubon_plan_entries[0]["first-malignant-cancer"]["amount"] == 50_000
assert fubon_plan_entries[0]["major-burn"]["amount"] == 1_200_000
assert fubon_plan_entries[1]["major-burn"]["amount"] == 1_600_000
assert fubon_plan_entries[0]["general-accidental-death"]["amount"] == 3_000_000
assert fubon_plan_entries[1]["general-accidental-death"]["amount"] == 4_000_000
assert fubon_plan_entries[2]["general-accidental-death"]["amount"] == 3_000_000
assert fubon_plan_entries[3]["general-accidental-death"]["amount"] == 5_000_000
assert fubon_plan_entries[4]["general-accidental-death"]["amount"] == 8_000_000
assert fubon_plan_entries[0]["air-transit-accidental-death-additional"]["amount"] == 6_000_000
assert fubon_plan_entries[1]["air-transit-accidental-death-additional"]["amount"] == 8_000_000
assert fubon_plan_entries[0]["general-accidental-disability"]["amount_tiers"][0] == {
    "label": "第1級 100%",
    "amount": 3_000_000,
}
assert fubon_plan_entries[0]["general-accidental-disability"]["amount_tiers"][-1] == {
    "label": "第11級 5%",
    "amount": 150_000,
}
assert fubon_plan_entries[1]["air-transit-accidental-disability-additional"]["amount_tiers"][0]["amount"] == 8_000_000
assert fubon_plan_entries[0]["general-hospital-daily"]["amount"] == 1_000
assert fubon_plan_entries[0]["icu-hospital-daily"]["amount"] == 1_000
assert "general-hospital-daily" not in fubon_plan_entries[2]
assert "life-death-or-funeral" not in fubon_plan_entries[2]
assert fubon_plan_entries[2]["accident-hospital-daily"]["amount"] == 500
assert fubon_plan_entries[3]["accident-icu-hospital-daily"]["amount"] == 500
assert fubon_plan_entries[4]["accident-outpatient-surgery"]["amount"] == 1_000
fubon_family_gift_partial = {
    **fubon_family_gift_document,
    "page_count": 2,
    "pages_parsed": 2,
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in fubon_family_gift_reader.pages[:2])
    ),
}
fubon_family_gift_completed = complete_strict_source_document(
    fubon_family_gift_partial, FUBON_FAMILY_GIFT_PATH
)
assert fubon_family_gift_completed["page_count"] == 21
assert parse_fubon_family_gift_accident_health_plan_table(
    fubon_family_gift_completed
) == fubon_family_gift_schedule
assert parse_fubon_family_gift_accident_health_plan_table(
    {**fubon_family_gift_document, "product_id": "wrong-product"}
) is None
assert parse_fubon_family_gift_accident_health_plan_table(
    {**fubon_family_gift_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_fubon_family_gift_accident_health_plan_table(
    {**fubon_family_gift_document, "page_count": 20}
) is None
assert parse_fubon_family_gift_accident_health_plan_table(
    {
        **fubon_family_gift_document,
        "text": fubon_family_gift_document["text"].replace(
            "一般意外身故保險金或喪葬費用保險金 300 萬 400 萬 300 萬 500 萬 800 萬",
            "一般意外身故保險金或喪葬費用保險金 300 萬 400 萬 300 萬 500 萬 900 萬",
            1,
        ),
    }
) is None


FUBON_FAMILY_GIFT_LATE_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_FAMILY_GIFT_LATE_PRODUCTS = {
    "209291M19G00301": (
        21,
        "103-first-revision",
        "MGH1030501",
        "original-two-tier",
        "原位癌",
        "殘廢",
    ),
    "209291MZ9G00221A11Z10000002": (
        23,
        "104-second-revision",
        "MGH1040804",
        "original-two-tier",
        "原位癌",
        "殘廢",
    ),
    "209291MZ9G00221A11Z10000003": (
        23,
        "107-third-revision",
        "MGH1070430",
        "original-two-tier",
        "原位癌",
        "殘廢",
    ),
    "209291MZ9G00221A11Z10000004": (
        23,
        "107-fourth-revision",
        "MGH1070914",
        "original-two-tier",
        "原位癌",
        "失能",
    ),
    "209291MZ9G00221A11Z10000005": (
        24,
        "108-fifth-revision",
        "MGH1080101",
        "2018-three-tier",
        "癌症初期",
        "失能",
    ),
    "209291MZ9G00221A11Z10000006": (
        24,
        "109-sixth-revision",
        "MGH1090101",
        "2018-three-tier",
        "癌症初期",
        "失能",
    ),
    "209291MZ9G00221A11Z10000007": (
        24,
        "109-seventh-revision",
        "MGH1090901",
        "2018-three-tier",
        "癌症初期",
        "失能",
    ),
}


def fubon_family_gift_late_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = FUBON_FAMILY_GIFT_LATE_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_pages,
    expected_revision,
    expected_code,
    expected_cancer_classification,
    expected_early_cancer_label,
    expected_disability_term,
) in FUBON_FAMILY_GIFT_LATE_PRODUCTS.items():
    document = fubon_family_gift_late_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_code in document["text"]
    schedule = parse_fubon_family_gift_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-family-gift-accident-health-plan-v1"
    assert integrated[1] == schedule
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["cancer_classification"] == expected_cancer_classification
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["plan_count"] == 5
    assert characteristics["maximum_renewal_age"] == 70
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
    ]
    late_entries = [
        {entry["id"]: entry for entry in plan["coverage_entries"]}
        for plan in schedule["plan_options"]
    ]
    assert late_entries[0]["total-disability"]["name"] == (
        f"完全{expected_disability_term}保險金"
    )
    assert (
        late_entries[0]["first-carcinoma-in-situ"]["name"]
        == f"初次罹患癌症保險金（{expected_early_cancer_label}）"
    )
    assert late_entries[0]["general-accidental-disability"]["name"] == (
        f"一般意外{expected_disability_term}保險金"
    )
    assert late_entries[0]["life-death-or-funeral"]["amount"] == 2_000_000
    assert late_entries[1]["life-death-or-funeral"]["amount"] == 3_000_000
    assert late_entries[0]["general-accidental-death"]["amount"] == 3_000_000
    assert late_entries[4]["general-accidental-death"]["amount"] == 8_000_000
    assert late_entries[0]["general-accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 3_000_000,
    }
    assert late_entries[0]["general-accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 150_000,
    }
    assert late_entries[2]["accident-hospital-daily"]["amount"] == 500
    assert late_entries[4]["accident-outpatient-surgery"]["amount"] == 1_000

    source_path = FUBON_FAMILY_GIFT_LATE_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_family_gift_accident_health_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_fubon_family_gift_accident_health_plan_table(
            fubon_family_gift_late_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_fubon_family_gift_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_family_gift_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


FUBON_WANAN_365_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_WANAN_365_PRODUCTS = {
    "209211MZ1A00921A11Z10000000": "108-original",
    "209211MZ1A00921A11Z10000001": "109-first-revision",
    "209211MZ1A00921A11Z10000002": "110-second-revision",
    "209211MZ1A00921A11Z10000003": "112-third-revision",
    "209211MZ1A00921A11Z10000004": "112-fourth-revision",
    "209211MZ1A00921A11Z10000005": "112-fifth-revision",
}


def fubon_wanan_365_document(product_id: str) -> dict:
    pdf_path = FUBON_WANAN_365_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, expected_revision in FUBON_WANAN_365_PRODUCTS.items():
    document = fubon_wanan_365_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 15
    schedule = parse_fubon_wanan_365_accident_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-wanan-365-accident-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 2
    assert characteristics["plan_a_face_amount"] == 1_000_000
    assert characteristics["plan_b_face_amount"] == 2_000_000
    assert characteristics["maximum_renewal_age"] == 75
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_rate_percent"] == 40
    assert characteristics["food_poisoning_annual_limit_times"] == 3
    assert characteristics["disability_term"] == "失能"
    assert characteristics["disability_schedule_item_count"] == 80
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["natural_disaster_disability_min_level"] == 2
    assert characteristics["natural_disaster_disability_max_level"] == 11
    assert [plan["label"] for plan in schedule["plan_options"]] == ["計畫A", "計畫B"]
    plan_a_entries = {
        entry["id"]: entry for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    plan_b_entries = {
        entry["id"]: entry for entry in schedule["plan_options"][1]["coverage_entries"]
    }
    expected_entry_ids = {
        "general-accidental-death-or-funeral",
        "mass-transit-accidental-death-or-funeral",
        "public-building-fire-accidental-death-or-funeral",
        "elevator-accidental-death-or-funeral",
        "overseas-accidental-death-or-funeral",
        "holiday-accidental-death-or-funeral",
        "carbon-monoxide-poisoning-death",
        "general-accidental-disability",
        "mass-transit-accidental-disability",
        "public-building-fire-accidental-disability",
        "elevator-accidental-disability",
        "overseas-accidental-disability",
        "holiday-accidental-disability",
        "carbon-monoxide-poisoning-disability",
        "natural-disaster-accidental-disability-levels-2-to-11",
        "disability-living-assistance-levels-1-to-3",
        "major-burn",
        "food-poisoning-hospitalization",
    }
    assert set(plan_a_entries) == expected_entry_ids
    assert set(plan_b_entries) == expected_entry_ids
    assert plan_a_entries["general-accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_b_entries["general-accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_a_entries["overseas-accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_b_entries["overseas-accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_a_entries["holiday-accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_b_entries["holiday-accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_a_entries["general-accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 1_000_000,
    }
    assert plan_b_entries["general-accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 2_000_000,
    }
    assert plan_a_entries[
        "natural-disaster-accidental-disability-levels-2-to-11"
    ]["amount_tiers"][0] == {"label": "第2級 90%", "amount": 900_000}
    assert plan_b_entries[
        "natural-disaster-accidental-disability-levels-2-to-11"
    ]["amount_tiers"][0] == {"label": "第2級 90%", "amount": 1_800_000}
    assert (
        plan_a_entries["disability-living-assistance-levels-1-to-3"]["amount"]
        == 500_000
    )
    assert (
        plan_b_entries["disability-living-assistance-levels-1-to-3"]["amount"]
        == 500_000
    )
    assert plan_a_entries["major-burn"]["amount"] == 400_000
    assert plan_b_entries["major-burn"]["amount"] == 800_000
    assert plan_a_entries["food-poisoning-hospitalization"]["amount"] == 2_500
    assert plan_b_entries["food-poisoning-hospitalization"]["amount"] == 2_500
    assert plan_a_entries["food-poisoning-hospitalization"]["rate_percent"] == 0.25
    assert plan_b_entries["food-poisoning-hospitalization"]["rate_percent"] == 0.125
    for entries in (plan_a_entries, plan_b_entries):
        for entry in entries.values():
            assert entry["source"] == "terms"
            assert entry.get("conditions")

wanan_source_path = (
    FUBON_WANAN_365_ROOT
    / "209211MZ1A00921A11Z10000000"
    / "209211MZ1A00921A11Z10000000-A.pdf"
)
wanan_reader = PdfReader(wanan_source_path, strict=False)
wanan_base = fubon_wanan_365_document("209211MZ1A00921A11Z10000000")
wanan_partial = {
    **wanan_base,
    "page_count": 2,
    "pages_parsed": 2,
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in wanan_reader.pages[:2])
    ),
}
wanan_completed = complete_strict_source_document(wanan_partial, wanan_source_path)
assert wanan_completed["page_count"] == wanan_completed["pages_parsed"] == 15
assert parse_fubon_wanan_365_accident_plan_table(
    wanan_completed
) == parse_fubon_wanan_365_accident_plan_table(wanan_base)
assert parse_fubon_wanan_365_accident_plan_table(
    {**wanan_base, "product_id": "wrong-product"}
) is None
assert parse_fubon_wanan_365_accident_plan_table(
    {**wanan_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_fubon_wanan_365_accident_plan_table(
    {**wanan_base, "document_type": "product_summary"}
) is None
assert parse_fubon_wanan_365_accident_plan_table({**wanan_base, "page_count": 14}) is None
assert parse_fubon_wanan_365_accident_plan_table(
    {
        **wanan_base,
        "text": wanan_base["text"].replace(
            "計畫A 之保險金額為新臺幣(下同) 100 萬元",
            "計畫A 之保險金額為新臺幣(下同) 110 萬元",
            1,
        ),
    }
) is None


TII_LIFE_158_TEXT_FIXTURE = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-158-text.json"
    ).read_text(encoding="utf-8")
)["documents"]
GLOBAL_WINTERTHUR_CANCER_PRODUCT_IDS = {
    "262321R11A00300",
    "262321R11A00301",
    "262321R11A00400",
    "262321R11A00401",
}


def global_winterthur_document(product_id: str, document_type: str) -> dict:
    return next(
        document
        for document in TII_LIFE_158_TEXT_FIXTURE
        if document.get("product_id") == product_id
        and document.get("document_type") == document_type
    )


global_winterthur_schedules = {}
for global_winterthur_product_id in sorted(GLOBAL_WINTERTHUR_CANCER_PRODUCT_IDS):
    global_winterthur_terms = global_winterthur_document(
        global_winterthur_product_id,
        "policy_terms",
    )
    parsed_with_id = parse_plan_table_with_parser(global_winterthur_terms)
    assert parsed_with_id is not None
    assert parsed_with_id[0] == "global-winterthur-cancer-annuity-face-amount-v1"
    global_winterthur_schedule = parsed_with_id[1]
    global_winterthur_schedules[global_winterthur_product_id] = global_winterthur_schedule
    assert global_winterthur_schedule["selection_type"] == "face_amount"
    assert global_winterthur_schedule["selection_label"] == "保險金額"
    global_winterthur_entries = {
        entry["id"]: entry for entry in global_winterthur_schedule["coverage_entries"]
    }
    assert len(global_winterthur_entries) == 7
    assert {
        entry_id: entry["rate_percent"]
        for entry_id, entry in global_winterthur_entries.items()
    } == {
        "initial-carcinoma-in-situ": 10,
        "initial-cancer": 100,
        "cancer-recovery-annuity-year-1": 90,
        "cancer-recovery-annuity-year-2": 80,
        "cancer-recovery-annuity-year-3": 70,
        "cancer-recovery-annuity-year-4": 60,
        "cancer-recovery-annuity-years-5-9": 20,
    }
    assert all(
        entry["calculation_basis"] == "percentage_of_base"
        and "附表一（保險金給付表），第 4 頁" in entry["source_ref"]
        for entry in global_winterthur_entries.values()
    )
    assert parse_global_winterthur_cancer_annuity_face_amount(
        global_winterthur_document(global_winterthur_product_id, "product_summary")
    ) is None

assert set(global_winterthur_schedules) == GLOBAL_WINTERTHUR_CANCER_PRODUCT_IDS
for traditional_product_id in ("262321R11A00300", "262321R11A00301"):
    traditional_characteristics = global_winterthur_schedules[traditional_product_id][
        "version_characteristics"
    ]
    assert traditional_characteristics["product_variant"] == "traditional"
    assert traditional_characteristics["maximum_renewal_age"] == 65
    assert not traditional_characteristics[
        "terminates_next_policy_month_after_initial_cancer"
    ]
for investment_product_id in ("262321R11A00400", "262321R11A00401"):
    investment_characteristics = global_winterthur_schedules[investment_product_id][
        "version_characteristics"
    ]
    assert investment_characteristics["product_variant"] == "investment-linked"
    assert investment_characteristics["maximum_renewal_age"] == 75

assert global_winterthur_schedules["262321R11A00401"]["version_characteristics"][
    "terminates_next_policy_month_after_initial_cancer"
]
assert global_winterthur_schedules["262321R11A00401"]["version_characteristics"][
    "post_death_actual_diagnosis_date_evidence_allowed"
]
assert not global_winterthur_schedules["262321R11A00400"]["version_characteristics"][
    "post_death_actual_diagnosis_date_evidence_allowed"
]

global_winterthur_base = global_winterthur_document("262321R11A00300", "policy_terms")
global_winterthur_base_text = global_winterthur_base["text"]
assert parse_global_winterthur_cancer_annuity_face_amount(
    {**global_winterthur_base, "product_id": "262321R11A99900"}
) is None

preserved_schedule = global_winterthur_schedules["262321R11A00300"]
preserved_candidate = {
    "parser_id": "global-winterthur-cancer-annuity-face-amount-v1",
    "source_file": "262321R11A003-A.pdf",
    "source_document_sha256": "source-sha",
    "schedule_sha256": "schedule-sha",
    "schedule": preserved_schedule,
}
preserved_review = {
    "product_id": "262321R11A00300",
    "decision": "approved",
    **{key: preserved_candidate[key] for key in (
        "parser_id",
        "source_file",
        "source_document_sha256",
        "schedule_sha256",
    )},
    "reviewed_by": "source reviewer",
    "reviewed_at": "2026-07-20T09:00:00+08:00",
    "review_note": "verified",
}
preserved_record = {
    "product_id": "262321R11A00300",
    "status": "verified_reference",
    "extractor_version": EXTRACTOR_VERSION,
    **{key: preserved_candidate[key] for key in (
        "parser_id",
        "source_file",
        "source_document_sha256",
        "schedule_sha256",
    )},
    "reviewed_by": "source reviewer",
    "reviewed_at": "2026-07-20T09:00:00+08:00",
    "review_note": "verified",
    **preserved_schedule,
}
_, preserved_records = approved_schedules(
    {
        "batch_id": "tii-life-158",
        "extractor_version": EXTRACTOR_VERSION,
        "proposals": [{
            "product_id": "262321R11A00300",
            "status": "proposed",
            "candidates": [preserved_candidate],
        }],
    },
    {"batch_id": "tii-life-158", "reviews": [preserved_review]},
    [preserved_record],
)
assert preserved_records == [preserved_record]

old_version_preserved_record = {
    **preserved_record,
    "extractor_version": "tii-plan-benefits-v-old",
}
_, upgraded_preserved_records = approved_schedules(
    {
        "batch_id": "tii-life-158",
        "extractor_version": EXTRACTOR_VERSION,
        "proposals": [{
            "product_id": "262321R11A00300",
            "status": "proposed",
            "candidates": [preserved_candidate],
        }],
    },
    {"batch_id": "tii-life-158", "reviews": [preserved_review]},
    [old_version_preserved_record],
)
assert upgraded_preserved_records == [preserved_record]

stale_candidate = {
    **preserved_candidate,
    "schedule_sha256": "new-unreviewed-schedule-sha",
}
stale_proposal_payload = {
    "batch_id": "tii-life-158",
    "extractor_version": EXTRACTOR_VERSION,
    "proposals": [{
        "product_id": "262321R11A00300",
        "status": "proposed",
        "candidates": [stale_candidate],
    }],
}
stale_schedules, stale_preserved_records = approved_schedules(
    stale_proposal_payload,
    {"batch_id": "tii-life-158", "reviews": [preserved_review]},
    [old_version_preserved_record],
)
assert stale_schedules == {}
assert stale_preserved_records == [old_version_preserved_record]

try:
    approved_schedules(
        stale_proposal_payload,
        {"batch_id": "tii-life-158", "reviews": [preserved_review]},
        [],
    )
except SystemExit as error:
    assert "stale or mismatched approval" in str(error)
else:
    raise AssertionError("unreviewed stale approval must fail closed")

assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "file_name": "262321R11A003-F.pdf",
        "document_type": "product_summary",
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": global_winterthur_base_text.replace(
            "環球瑞泰人壽防癌健康保險附約",
            "環球瑞泰人壽防癌健康保險",
            1,
        ),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": global_winterthur_base_text.replace("第九十一日", "第六十一日", 1),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": global_winterthur_base_text.replace(
            "【附表一】保險金給付表",
            "【附表甲】保險金給付表",
            1,
        ),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": global_winterthur_base_text.replace("10,000 元", "11,000 元", 1),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": global_winterthur_base_text.replace(
            "【初次罹患原位癌保險金 】 第十二條",
            "【初次罹患原位癌保險金 】 第十一條",
            1,
        ),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "text": (
            global_winterthur_base_text
            + " "
            + global_winterthur_base_text[global_winterthur_base_text.rfind("【附表一】") :]
        ),
    }
) is None
assert parse_global_winterthur_cancer_annuity_face_amount(
    {
        **global_winterthur_base,
        "product_id": "262321R11A00301",
        "file_name": "262321R11A00301-A.pdf",
    }
) is None


KGI_RITAI_CANCER_PRODUCT_IDS = {
    "205321R11A50600": "original",
    "205321R11A50601": "first-revision",
}


def kgi_ritai_cancer_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_026_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


kgi_ritai_schedules = {}
for kgi_ritai_product_id, expected_revision in KGI_RITAI_CANCER_PRODUCT_IDS.items():
    kgi_ritai_terms = kgi_ritai_cancer_document(kgi_ritai_product_id)
    parsed_with_id = parse_plan_table_with_parser(kgi_ritai_terms)
    assert parsed_with_id is not None
    assert parsed_with_id[0] == "kgi-china-life-ritai-cancer-annuity-face-amount-v1"
    kgi_ritai_schedule = parsed_with_id[1]
    kgi_ritai_schedules[kgi_ritai_product_id] = kgi_ritai_schedule
    assert kgi_ritai_schedule["selection_type"] == "face_amount"
    assert kgi_ritai_schedule["selection_label"] == "保險金額"
    assert kgi_ritai_schedule["version_characteristics"] == {
        "product_variant": "investment-linked",
        "revision": expected_revision,
        "cancer_initial_waiting_days": 90,
        "cancer_reinstatement_waiting_days": 90,
        "cancer_renewal_waiting_days": 0,
        "maximum_renewal_age": 75,
        "terminates_next_policy_month_after_initial_cancer": True,
        "post_death_actual_diagnosis_date_evidence_allowed": True,
        "annuity_anniversary_basis": "initial-cancer-benefit-payment-date",
    }
    kgi_ritai_entries = {
        entry["id"]: entry for entry in kgi_ritai_schedule["coverage_entries"]
    }
    assert len(kgi_ritai_entries) == 7
    assert {
        entry_id: entry["rate_percent"]
        for entry_id, entry in kgi_ritai_entries.items()
    } == {
        "initial-carcinoma-in-situ": 10,
        "initial-cancer": 100,
        "cancer-recovery-annuity-year-1": 90,
        "cancer-recovery-annuity-year-2": 80,
        "cancer-recovery-annuity-year-3": 70,
        "cancer-recovery-annuity-year-4": 60,
        "cancer-recovery-annuity-years-5-9": 20,
    }
    assert all(
        entry["calculation_basis"] == "percentage_of_base"
        and "附表一（保險金給付表），第 6 頁" in entry["source_ref"]
        for entry in kgi_ritai_entries.values()
    )
    assert parse_kgi_china_life_ritai_cancer_annuity_face_amount(
        kgi_ritai_cancer_document(kgi_ritai_product_id, "F")
    ) is None

kgi_ritai_base = kgi_ritai_cancer_document("205321R11A50600")
assert parse_kgi_china_life_ritai_cancer_annuity_face_amount(
    {**kgi_ritai_base, "product_id": "205321R11A99900"}
) is None
assert parse_kgi_china_life_ritai_cancer_annuity_face_amount(
    {
        **kgi_ritai_base,
        "text": kgi_ritai_base["text"].replace("新台幣10,000元", "新台幣11,000元", 1),
    }
) is None
assert parse_kgi_china_life_ritai_cancer_annuity_face_amount(
    {
        **kgi_ritai_base,
        "product_id": "205321R11A50601",
        "file_name": "205321R11A50601-A.pdf",
    }
) is None


FUBON_HSL_INPATIENT_PRODUCT_ID = "209311RZ1A02221A11Z10000001"
FUBON_HSL_INPATIENT_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-050"
    / FUBON_HSL_INPATIENT_PRODUCT_ID
    / f"{FUBON_HSL_INPATIENT_PRODUCT_ID}-A.pdf"
)
fubon_hsl_reader = PdfReader(FUBON_HSL_INPATIENT_PATH, strict=False)
fubon_hsl_document = {
    "product_id": FUBON_HSL_INPATIENT_PRODUCT_ID,
    "file_name": FUBON_HSL_INPATIENT_PATH.name,
    "document_type": "policy_terms",
    "page_count": len(fubon_hsl_reader.pages),
    "pages_parsed": len(fubon_hsl_reader.pages),
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in fubon_hsl_reader.pages)
    ),
}
fubon_hsl_schedule = parse_fubon_hsl_inpatient_unit_table(fubon_hsl_document)
assert fubon_hsl_schedule is not None
assert fubon_hsl_schedule["selection_type"] == "unit"
assert fubon_hsl_schedule["version_characteristics"] == {
    "terms_revision": "111-12-02-revision",
    "disease_waiting_days": 30,
    "day_hospital_excluded": True,
    "same_hospital_readmission_days": 14,
    "post_expiry_readmission_excluded": True,
    "non_nhi_payment_rate_percent": 65,
    "room_daily_days_limit": 365,
    "renewal_age_self_or_spouse": 75,
    "renewal_age_child": 23,
    "linked_non_deductible_medical_required": True,
    "newborn_metabolic_disease_exempt_waiting_period": True,
    "prosthetic_eye_limb_room_net_limit_multiplier": 10,
}
fubon_hsl_entries = {
    entry["id"]: entry for entry in fubon_hsl_schedule["coverage_entries"]
}
assert len(fubon_hsl_entries) == 3
assert fubon_hsl_entries["daily-room-expense-reimbursement"]["amount"] == 150
assert fubon_hsl_entries["daily-room-expense-reimbursement"]["amount_tiers"] == [
    {"label": "每日病房費用自負額", "amount": 110},
    {"label": "每日病房費用限額", "amount": 150},
]
assert fubon_hsl_entries["inpatient-medical-expense-reimbursement"]["amount"] == 12_800
assert fubon_hsl_entries["inpatient-medical-expense-reimbursement"]["amount_tiers"] == [
    {"label": "住院醫療費用自負額", "amount": 8_818},
    {"label": "住院醫療費用限額", "amount": 12_800},
]
assert fubon_hsl_entries["prosthetic-eye-limb-sub-limit"]["amount"] == 400
assert (
    parse_plan_table_with_parser(fubon_hsl_document)[0]
    == "fubon-hsl-inpatient-unit-v1"
)
fubon_hsl_partial = {
    **fubon_hsl_document,
    "page_count": 4,
    "pages_parsed": 4,
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in fubon_hsl_reader.pages[:4])
    ),
}
fubon_hsl_completed = complete_strict_source_document(
    fubon_hsl_partial, FUBON_HSL_INPATIENT_PATH
)
assert fubon_hsl_completed["page_count"] == 7
assert parse_fubon_hsl_inpatient_unit_table(fubon_hsl_completed) == fubon_hsl_schedule
assert parse_fubon_hsl_inpatient_unit_table(
    {**fubon_hsl_document, "product_id": "wrong-product-id"}
) is None
assert parse_fubon_hsl_inpatient_unit_table(
    {**fubon_hsl_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_fubon_hsl_inpatient_unit_table(
    {**fubon_hsl_document, "page_count": 6}
) is None
assert parse_fubon_hsl_inpatient_unit_table(
    {
        **fubon_hsl_document,
        "text": fubon_hsl_document["text"].replace("每次12,800元", "每次12,900元", 1),
    }
) is None

FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID = "209311RZ1A02221A11Z10000000"
FUBON_HSL_INPATIENT_ORIGINAL_PATH = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-documents"
    / "tii-life-050"
    / FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID
    / f"{FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID}-A.pdf"
)
fubon_hsl_original_reader = PdfReader(
    FUBON_HSL_INPATIENT_ORIGINAL_PATH, strict=False
)
fubon_hsl_original_document = {
    "product_id": FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID,
    "file_name": FUBON_HSL_INPATIENT_ORIGINAL_PATH.name,
    "document_type": "policy_terms",
    "page_count": len(fubon_hsl_original_reader.pages),
    "pages_parsed": len(fubon_hsl_original_reader.pages),
    "text": normalize_terms_text(
        "\n".join(page.extract_text() or "" for page in fubon_hsl_original_reader.pages)
    ),
}
fubon_hsl_original_schedule = parse_fubon_hsl_inpatient_unit_table(
    fubon_hsl_original_document
)
assert fubon_hsl_original_schedule is not None
assert (
    parse_plan_table_with_parser(fubon_hsl_original_document)[0]
    == "fubon-hsl-inpatient-unit-v1"
)
assert fubon_hsl_original_schedule["version_characteristics"] == {
    **fubon_hsl_schedule["version_characteristics"],
    "terms_revision": "109-12-04-original",
}
assert fubon_hsl_original_schedule["coverage_entries"] == fubon_hsl_schedule[
    "coverage_entries"
]
fubon_hsl_original_summary_path = FUBON_HSL_INPATIENT_ORIGINAL_PATH.with_name(
    f"{FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID}-F.pdf"
)
fubon_hsl_original_summary_reader = PdfReader(
    fubon_hsl_original_summary_path, strict=False
)
assert parse_fubon_hsl_inpatient_unit_table(
    {
        "product_id": FUBON_HSL_INPATIENT_ORIGINAL_PRODUCT_ID,
        "file_name": fubon_hsl_original_summary_path.name,
        "document_type": "product_summary",
        "page_count": len(fubon_hsl_original_summary_reader.pages),
        "pages_parsed": len(fubon_hsl_original_summary_reader.pages),
        "text": normalize_terms_text(
            "\n".join(
                page.extract_text() or ""
                for page in fubon_hsl_original_summary_reader.pages
            )
        ),
    }
) is None
assert parse_fubon_hsl_inpatient_unit_table(
    {
        **fubon_hsl_original_document,
        "text": fubon_hsl_original_document["text"].replace(
            "109.12.04 富壽商精字第1090005302 號函備查",
            "109.12.05 富壽商精字第1090005302 號函備查",
            1,
        ),
    }
) is None


FUBON_INPATIENT_TARGET_PRODUCT_IDS = (
    "209311R11A00310",
    "209311RZ1A00721A11Z10000011",
    "209311RZ1A00721A11Z10000012",
    "209311RZ1A00721A11Z10000013",
)
FUBON_INPATIENT_PDF_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-050"
)


def fubon_inpatient_pdf_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = FUBON_INPATIENT_PDF_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


def assert_fubon_inpatient_rejected(document: dict) -> None:
    assert parse_fubon_inpatient_medical_unit_table(document) is None
    assert parse_plan_table_with_parser(document) is None


fubon_inpatient_documents = {
    product_id: fubon_inpatient_pdf_document(product_id)
    for product_id in FUBON_INPATIENT_TARGET_PRODUCT_IDS
}
fubon_inpatient_schedules = {}
expected_fubon_inpatient_amounts = {
    "hospital-room-limit": 110,
    "intensive-care-limit": 220,
    "burn-center-limit": 330,
    "inpatient-medical-limit": 8_800,
    "hospital-surgery-base": 5_500,
    "home-recovery-limit": 66,
    "surgery-recovery-base": 1_650,
    "hospital-daily-option": 143,
}
expected_fubon_version_signals = {
    FUBON_INPATIENT_TARGET_PRODUCT_IDS[0]: "因投保年齡的錯誤,而致短繳保險費者,應補足其差額",
    FUBON_INPATIENT_TARGET_PRODUCT_IDS[1]: "真實投保年齡較本公司保險費率表所載最高年齡為大者,本附約無效",
    FUBON_INPATIENT_TARGET_PRODUCT_IDS[2]: "得徵詢其他醫師之醫學專業意見",
    FUBON_INPATIENT_TARGET_PRODUCT_IDS[3]: "基於保戶服務,本公司於保險契約停止效力後至得申請復效之期限屆滿前三個月",
}

for product_id, document in fubon_inpatient_documents.items():
    assert document["page_count"] == document["pages_parsed"] == 10
    schedule = parse_fubon_inpatient_medical_unit_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-inpatient-medical-unit-v1"
    assert integrated[1] == schedule
    fubon_inpatient_schedules[product_id] = schedule

    assert schedule["selection_type"] == schedule["input_mode"] == "unit"
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 8
    assert set(entries) == set(expected_fubon_inpatient_amounts)
    for entry_id, amount in expected_fubon_inpatient_amounts.items():
        assert entries[entry_id]["amount"] == amount
        assert entries[entry_id]["source"] == "terms"
        assert "附表一" in entries[entry_id]["source_ref"]
    assert entries["inpatient-medical-limit"]["amount_tiers"][-1] == {
        "label": "住院 181 至 365 日",
        "amount": 44_000,
    }
    assert entries["hospital-surgery-base"]["rate_min_percent"] == 10
    assert entries["hospital-surgery-base"]["rate_max_percent"] == 500
    assert entries["home-recovery-limit"]["rate_min_percent"] == 60
    assert entries["hospital-daily-option"]["amount_tiers"] == [
        {"label": "住院第 1 至 30 日", "amount": 143},
        {"label": "住院第 31 日起", "amount": 286},
    ]
    assert entries["hospital-daily-option"]["aggregation_rule"] == "choose_one"

    source_path = (
        FUBON_INPATIENT_PDF_ROOT / product_id / f"{product_id}-A.pdf"
    )
    reader = PdfReader(source_path)
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in reader.pages[:6])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 10
    assert parse_fubon_inpatient_medical_unit_table(completed_document) == schedule

    missing_source = complete_strict_source_document(
        indexed_document,
        source_path.with_name("missing-A.pdf"),
    )
    assert missing_source is indexed_document
    assert_fubon_inpatient_rejected(missing_source)
    assert_fubon_inpatient_rejected(fubon_inpatient_pdf_document(product_id, "F"))

    dense_text = "".join(document["text"].split())
    version_signal = expected_fubon_version_signals[product_id]
    assert version_signal in dense_text
    assert_fubon_inpatient_rejected(
        {**document, "text": dense_text.replace(version_signal, "", 1)}
    )

fubon_inpatient_base = fubon_inpatient_documents[FUBON_INPATIENT_TARGET_PRODUCT_IDS[0]]
fubon_inpatient_base_dense = "".join(fubon_inpatient_base["text"].split())

assert_fubon_inpatient_rejected(
    {**fubon_inpatient_base, "product_id": "wrong-product-id"}
)
assert_fubon_inpatient_rejected(
    {**fubon_inpatient_base, "file_name": "wrong-file-A.pdf"}
)
assert_fubon_inpatient_rejected(
    {
        **fubon_inpatient_base,
        "product_id": "wrong-product-id",
        "file_name": "wrong-file-A.pdf",
    }
)
assert_fubon_inpatient_rejected(
    {**fubon_inpatient_base, "document_type": "product_summary"}
)
assert_fubon_inpatient_rejected({**fubon_inpatient_base, "page_count": 9})
assert_fubon_inpatient_rejected({**fubon_inpatient_base, "pages_parsed": 9})

base_source_path = (
    FUBON_INPATIENT_PDF_ROOT
    / FUBON_INPATIENT_TARGET_PRODUCT_IDS[0]
    / f"{FUBON_INPATIENT_TARGET_PRODUCT_IDS[0]}-A.pdf"
)
first_nine_pages = normalize_terms_text(
    "\n".join(
        (page.extract_text() or "") for page in PdfReader(base_source_path).pages[:9]
    )
)
assert_fubon_inpatient_rejected({**fubon_inpatient_base, "text": first_nine_pages})
assert_fubon_inpatient_rejected(
    {
        **fubon_inpatient_base,
        "text": fubon_inpatient_documents[FUBON_INPATIENT_TARGET_PRODUCT_IDS[1]][
            "text"
        ],
    }
)


def reject_fubon_inpatient_dense_replacement(old: str, new: str) -> None:
    assert old in fubon_inpatient_base_dense
    assert_fubon_inpatient_rejected(
        {
            **fubon_inpatient_base,
            "text": fubon_inpatient_base_dense.replace(old, new, 1),
        }
    )


reject_fubon_inpatient_dense_replacement("附表一(1)住院醫療保險金", "附表甲(1)住院醫療保險金")
reject_fubon_inpatient_dense_replacement(
    "附表二:手術項目給付比率表", "附表乙:手術項目給付比率表"
)
reject_fubon_inpatient_dense_replacement(
    "每日病房費用保險金每日110元", "每日病房費用保險金每日111元"
)
reject_fubon_inpatient_dense_replacement(
    "剖腹探查術、結腸切開術65%", "剖腹探查術、結腸切開術66%"
)
reject_fubon_inpatient_dense_replacement("超過的天數加倍給付", "")
reject_fubon_inpatient_dense_replacement("實際支付之各項費用之六十五%給付", "")


TII_LIFE_050_PRODUCT_IDS = (
    "209391M11G00100",
    "209391MZ1G00121A11Z10000001",
    "209391MZ1G00121A11Z10000002",
    "209391MZ1G00121A11Z10000003",
    "209391MZ1G00121A11Z10000004",
    "209391MZ1G00121A11Z10000005",
)
TII_LIFE_050_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-050"
)


def tii_life_050_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_050_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


def assert_tii_life_050_rejected(document: dict) -> None:
    assert parse_fubon_new_lohas_combined_plan_table(document) is None
    assert parse_plan_table_with_parser(document) is None


tii_life_050_documents = {
    product_id: tii_life_050_document(product_id)
    for product_id in TII_LIFE_050_PRODUCT_IDS
}
tii_life_050_schedules = {}
expected_schedule_revisions = {
    "209391M11G00100": "original-75-items",
    "209391MZ1G00121A11Z10000001": "104-revised-79-items",
    "209391MZ1G00121A11Z10000002": "104-revised-79-items",
    "209391MZ1G00121A11Z10000003": "109-revised-80-items",
    "209391MZ1G00121A11Z10000004": "109-revised-80-items",
    "209391MZ1G00121A11Z10000005": "109-revised-80-items",
}
expected_disability_terms = {
    "209391M11G00100": "殘廢",
    "209391MZ1G00121A11Z10000001": "殘廢",
    "209391MZ1G00121A11Z10000002": "失能",
    "209391MZ1G00121A11Z10000003": "失能",
    "209391MZ1G00121A11Z10000004": "失能",
    "209391MZ1G00121A11Z10000005": "失能",
}
expected_amounts = {
    "policy-death": (500_000, 1_000_000, 2_000_000, 3_000_000),
    "total-disability": (500_000, 1_000_000, 2_000_000, 3_000_000),
    "major-illness": (100_000, 200_000, 400_000, 600_000),
    "low-invasive-cancer": (5_000, 10_000, 20_000, 30_000),
    "major-burn": (400_000, 400_000, 400_000, 800_000),
    "accident-death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "overseas-accident-death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "air-transport-accident-death": (2_000_000, 2_000_000, 2_000_000, 4_000_000),
    "surface-transport-accident-death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "public-building-fire-accident-death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "elevator-accident-death": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "accident-disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "overseas-accident-disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "air-transport-accident-disability": (2_000_000, 2_000_000, 2_000_000, 4_000_000),
    "surface-transport-accident-disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "public-building-fire-accident-disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "elevator-accident-disability": (1_000_000, 1_000_000, 1_000_000, 2_000_000),
    "accident-hospital-daily": (500, 500, 500, 1_000),
    "fracture-without-hospitalization": (500, 500, 500, 1_000),
    "accident-icu-daily": (500, 500, 500, 1_000),
    "accident-outpatient-surgery": (500, 500, 500, 1_000),
    "hospital-daily": (1_000, 1_000, 1_000, 2_000),
    "hospital-icu-daily": (2_500, 2_500, 2_500, 5_000),
    "burn-center-hospital-daily": (2_500, 2_500, 2_500, 5_000),
}

for product_id, document in tii_life_050_documents.items():
    assert document["page_count"] == document["pages_parsed"]
    assert document["page_count"] == (24 if product_id == "209391M11G00100" else 25)
    schedule = parse_fubon_new_lohas_combined_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-lohas-combined-plan-v1"
    assert integrated[1] == schedule
    tii_life_050_schedules[product_id] = schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "保障計畫"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["disability_schedule_revision"] == expected_schedule_revisions[product_id]
    assert characteristics["disability_term"] == expected_disability_terms[product_id]
    assert characteristics["major_disease_initial_waiting_days"] == 90
    assert characteristics["major_disease_reinstatement_waiting_days"] == 90
    assert characteristics["mild_cancer_initial_waiting_days"] == 90
    assert characteristics["mild_cancer_reinstatement_waiting_days"] == 90
    assert characteristics["maximum_renewal_age"] == 75
    assert "document_code" not in characteristics
    assert "table_sha256" not in characteristics
    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert len(entries) == len(plan["coverage_entries"]) == 24
        assert set(entries) == set(expected_amounts)
        for entry_id, amounts in expected_amounts.items():
            assert entries[entry_id]["amount"] == amounts[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert "附表一" in entries[entry_id]["source_ref"]
            assert entries[entry_id].get("conditions")
        assert entries["fracture-without-hospitalization"]["multiplier"] == 0.5
        assert entries["accident-disability"]["rate_min_percent"] == 5
        assert entries["accident-disability"]["rate_max_percent"] == 100
        assert "附表二" in entries["total-disability"]["source_ref"]
        assert "附表四" in entries["major-burn"]["source_ref"]
        assert "附表三" in entries["accident-disability"]["source_ref"]

    source_path = (
        TII_LIFE_050_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:20])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"]
    assert completed_document["page_count"] == document["page_count"]
    assert parse_fubon_new_lohas_combined_plan_table(completed_document) == schedule

    missing_source = complete_strict_source_document(
        indexed_document,
        source_path.with_name("missing-A.pdf"),
    )
    assert missing_source is indexed_document
    assert parse_fubon_new_lohas_combined_plan_table(missing_source) is None

base_document = tii_life_050_documents["209391MZ1G00121A11Z10000002"]
base_text = base_document["text"]


def reject_text_replacement(old: str, new: str) -> None:
    assert old in base_text
    assert_tii_life_050_rejected(
        {**base_document, "text": base_text.replace(old, new, 1)}
    )


assert_tii_life_050_rejected({**base_document, "product_id": "wrong-product-id"})
assert_tii_life_050_rejected({**base_document, "file_name": "wrong-file-A.pdf"})
assert_tii_life_050_rejected(
    {**base_document, "product_id": "wrong-product-id", "file_name": "wrong-file-A.pdf"}
)
assert_tii_life_050_rejected({**base_document, "document_type": "product_summary"})
assert_tii_life_050_rejected({**base_document, "page_count": 24})
assert_tii_life_050_rejected({**base_document, "pages_parsed": 20})
for product_id in TII_LIFE_050_PRODUCT_IDS:
    assert_tii_life_050_rejected(tii_life_050_document(product_id, "F"))

reject_text_replacement(
    "富邦人壽新樂活人生傷害暨健康一年定期保險",
    "富邦人壽新樂活Plus傷害暨健康一年定期保險",
)
reject_text_replacement("MGA11070914", "MGA11070915")
reject_text_replacement("107.09.14 依 107.06.07 金管保壽字第 10704158370 號函修正", "107.09.15 版本文字已變更")
reject_text_replacement("MGA11070914 25/25 商品代號:MGA1", "MGA11070914 25/24 商品代號:MGA1")
reject_text_replacement("附表二:完全失能程度表", "附表乙:完全失能程度表")
reject_text_replacement("附表五:短期費率表", "附表戊:短期費率表")
for required_limit in (
    "本契約最高可續保至被保險人保險年齡七十五歲時之該保險期間屆滿",
    "本公司給付重大傷病保險金之責任,以一次為限",
    "本公司給付低侵襲性癌症保險金之責任,以一次為限",
    "同一次住院之一般住院醫療保險金實際給付住院日數,最高以三百六十五日為限",
    "於出院後十四日內再次住院時,其各種保險金給付,均視為一次住院",
    "不包含全民健康保險法第五十一條所稱之日間住院及精神衛生法第三十五條所稱之日間留院",
    "自意外傷害事故發生之日起屆滿十五日仍生存者",
    "如係不完全骨折,按完全骨折日數二分之一給付",
    "骨骼龜裂者按完全骨折日數四分之一給付",
    "每次意外傷害得申領之意外傷害門診手術醫療保險金以一次為限",
    "同時符合二項以上大眾運輸工具意外傷害事故者,本公司之保險責任以給付最高一項為限",
    "本公司之給付總金額合計最高以依第二十五條約定計算所應給付之保險金額為限",
):
    reject_text_replacement(required_limit, required_limit[:-1] + "異")

appendix_two_index = base_text.rfind("附表二:完全失能程度表")
appendix_one_index = base_text.rfind("附表一", 0, appendix_two_index)
assert appendix_one_index >= 0
assert_tii_life_050_rejected(
    {
        **base_document,
        "text": base_text[:appendix_one_index]
        + "附表甲"
        + base_text[appendix_one_index + len("附表一") :],
    }
)
appendix_four_index = base_text.rfind("附表四")
assert appendix_four_index >= 0
assert_tii_life_050_rejected(
    {
        **base_document,
        "text": base_text[:appendix_four_index]
        + "附表丁"
        + base_text[appendix_four_index + len("附表四") :],
    }
)
table_amount_index = base_text.find(
    "50 萬 100 萬 200 萬 300 萬", appendix_one_index
)
assert table_amount_index >= 0
assert_tii_life_050_rejected(
    {
        **base_document,
        "text": base_text[:table_amount_index]
        + "60 萬 100 萬 200 萬 300 萬"
        + base_text[table_amount_index + len("50 萬 100 萬 200 萬 300 萬") :],
    }
)
assert_tii_life_050_rejected(
    {
        **base_document,
        "text": tii_life_050_documents[TII_LIFE_050_PRODUCT_IDS[1]]["text"],
    }
)

FUBON_STATUTORY_INFECTIOUS_PRODUCT_IDS = (
    "209311MZ1B01021A11Z10000000",
    "209311MZ1B01021A11Z10000001",
)
statutory_expected = {
    "death": (500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000),
    "statutory-infectious-death": (750_000, 1_500_000, 2_250_000, 3_000_000, 3_750_000),
    "hospital-daily": (500, 1_000, 1_500, 2_000, 2_500),
    "statutory-infectious-hospital-daily": (1_000, 2_000, 3_000, 4_000, 5_000),
    "icu-daily": (500, 1_000, 1_500, 2_000, 2_500),
    "home-recovery-daily": (250, 500, 750, 1_000, 1_250),
    "statutory-infectious-diagnosis": (5_000, 10_000, 15_000, 20_000, 25_000),
}
for product_id in FUBON_STATUTORY_INFECTIOUS_PRODUCT_IDS:
    document = tii_life_050_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 9
    schedule = parse_fubon_statutory_infectious_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-statutory-infectious-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "保障計畫"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["statutory_infectious_waiting_days"] == 14
    assert characteristics["maximum_renewal_age"] == 75
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["statutory_death_rate_percent"] == 150
    assert characteristics["statutory_hospital_daily_rate_percent"] == 200
    assert characteristics["statutory_infectious_diagnosis_limit"] == "once_per_policy"
    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert len(entries) == len(plan["coverage_entries"]) == 7
        assert set(entries) == set(statutory_expected)
        for entry_id, amounts in statutory_expected.items():
            assert entries[entry_id]["amount"] == amounts[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert entries[entry_id].get("conditions")
        assert entries["statutory-infectious-death"]["rate_percent"] == 150
        assert entries["statutory-infectious-hospital-daily"]["rate_percent"] == 200

    source_path = TII_LIFE_050_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:4])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 9
    assert parse_fubon_statutory_infectious_plan_table(completed_document) == schedule
    assert parse_fubon_statutory_infectious_plan_table(tii_life_050_document(product_id, "F")) is None

statutory_base = tii_life_050_document(FUBON_STATUTORY_INFECTIOUS_PRODUCT_IDS[0])
assert parse_fubon_statutory_infectious_plan_table(
    {**statutory_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_fubon_statutory_infectious_plan_table(
    {**statutory_base, "document_type": "product_summary"}
) is None
assert parse_fubon_statutory_infectious_plan_table(
    {**statutory_base, "text": statutory_base["text"].replace("50 萬 100 萬 150 萬 200 萬 250 萬", "60 萬 100 萬 150 萬 200 萬 250 萬", 1)}
) is None

TII_LIFE_080_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-080"
)
FARGLORY_KANGFU_MEDICAL_PRODUCT_IDS = (
    "216311RZ1A19421A11Z10000001",
    "216311RZ1A19421A11Z10000002",
    "216311RZ1A19421A11Z10000003",
)


def tii_life_080_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_080_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


farglory_expected = {
    "hospital-daily": (500, 1_000, 1_500, 2_000),
    "hospital-auxiliary-daily": (500, 500, 500, 500),
    "hospital-consolation": (3_500, 7_000, 10_500, 14_000),
    "inpatient-medical-limit": (200_000, 300_000, 400_000, 500_000),
    "surgery-limit": (150_000, 200_000, 250_000, 300_000),
}
expected_kangfu_revisions = {
    "216311RZ1A19421A11Z10000001": ("107-revised", False, 6),
    "216311RZ1A19421A11Z10000002": ("109-revised", False, 7),
    "216311RZ1A19421A11Z10000003": ("111-revised", True, 7),
}
for product_id in FARGLORY_KANGFU_MEDICAL_PRODUCT_IDS:
    document = tii_life_080_document(product_id)
    expected_revision, expected_notice, expected_pages = expected_kangfu_revisions[product_id]
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_farglory_kangfu_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "farglory-kangfu-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計劃別"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計劃一",
        "計劃二",
        "計劃三",
        "計劃四",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["disease_initial_waiting_days"] == 0
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["nhi_uncovered_payment_rate_percent"] == 65
    assert characteristics["hospital_auxiliary_daily_fixed_amount"] == 500
    assert characteristics["hospital_consolation_daily_multiplier"] == 7
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["insured_notice_revision"] is expected_notice
    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert len(entries) == len(plan["coverage_entries"]) == 5
        assert set(entries) == set(farglory_expected)
        for entry_id, amounts in farglory_expected.items():
            assert entries[entry_id]["amount"] == amounts[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert entries[entry_id].get("conditions")
        assert entries["hospital-consolation"]["multiplier"] == 7
        assert entries["inpatient-medical-limit"]["amount_role"] == "limit"
        assert entries["surgery-limit"]["amount_role"] == "limit"

    source_path = TII_LIFE_080_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == expected_pages
    assert parse_farglory_kangfu_medical_plan_table(completed_document) == schedule
    assert parse_farglory_kangfu_medical_plan_table(tii_life_080_document(product_id, "F")) is None

farglory_base = tii_life_080_document(FARGLORY_KANGFU_MEDICAL_PRODUCT_IDS[0])
assert parse_farglory_kangfu_medical_plan_table(
    {**farglory_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_farglory_kangfu_medical_plan_table(
    {**farglory_base, "document_type": "product_summary"}
) is None
assert parse_farglory_kangfu_medical_plan_table(
    {**farglory_base, "text": farglory_base["text"].replace("住院日額 500 1,000 1,500 2,000", "住院日額 600 1,000 1,500 2,000", 1)}
) is None

TII_LIFE_164_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-164"
)
GLOBAL_E_ROAD_PEACE_OVERSEAS_ILLNESS_PRODUCT_IDS = (
    "264311AZ1AETS21A11Z10000000",
    "264311AZ1AETS21A11Z10000001",
    "264311AZ1AETS21A11Z10000002",
    "264311AZ1AETS21A11Z10000003",
)


def tii_life_164_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_164_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


expected_global_e_road_revisions = {
    "264311AZ1AETS21A11Z10000000": ("original", False, False),
    "264311AZ1AETS21A11Z10000001": ("107-first-revision", False, False),
    "264311AZ1AETS21A11Z10000002": ("108-second-revision", False, False),
    "264311AZ1AETS21A11Z10000003": ("109-third-revision", True, True),
}
for product_id in GLOBAL_E_ROAD_PEACE_OVERSEAS_ILLNESS_PRODUCT_IDS:
    document = tii_life_164_document(product_id)
    expected_revision, expected_regulatory_revision, expected_medical_opinion = (
        expected_global_e_road_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == 4
    schedule = parse_global_e_road_peace_overseas_illness_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "global-e-road-peace-overseas-illness-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "海外突發疾病醫療保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["overseas_illness_lookback_days"] == 180
    assert characteristics["inpatient_claim_days_limit"] == 180
    assert characteristics["outpatient_limit_rate_percent"] == 0.5
    assert characteristics["emergency_limit_rate_percent"] == 1
    assert characteristics["non_nhi_payment_rate_percent"] == 100
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["day_hospital_excluded"] is True
    assert (
        characteristics["claims_exchange_rate_basis"]
        == "taiwan-bank-reference-rate-on-claim-date"
    )
    assert characteristics["regulatory_revision"] is expected_regulatory_revision
    assert characteristics["claims_medical_opinion_revision"] is expected_medical_opinion

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "overseas-illness-inpatient-medical-limit",
        "overseas-illness-outpatient-medical-limit",
        "overseas-illness-emergency-medical-limit",
        "non-nhi-payment-rate",
        "unearned-premium-refund",
    }
    assert entries["overseas-illness-inpatient-medical-limit"]["rate_percent"] == 100
    assert entries["overseas-illness-outpatient-medical-limit"]["rate_percent"] == 0.5
    assert entries["overseas-illness-emergency-medical-limit"]["rate_percent"] == 1
    assert entries["non-nhi-payment-rate"]["rate_percent"] == 100
    assert entries["unearned-premium-refund"]["multiplier"] == 1
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_164_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 4
    assert parse_global_e_road_peace_overseas_illness_face_amount(completed_document) == schedule
    assert parse_global_e_road_peace_overseas_illness_face_amount(
        tii_life_164_document(product_id, "F")
    ) is None

global_e_road_base = tii_life_164_document(GLOBAL_E_ROAD_PEACE_OVERSEAS_ILLNESS_PRODUCT_IDS[0])
assert parse_global_e_road_peace_overseas_illness_face_amount(
    {**global_e_road_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_global_e_road_peace_overseas_illness_face_amount(
    {**global_e_road_base, "product_id": "264311AZ1AETS21A11Z10999999"}
) is None
assert parse_global_e_road_peace_overseas_illness_face_amount(
    {
        **global_e_road_base,
        "text": global_e_road_base["text"].replace(
            "0.5%",
            "0.6%",
            1,
        ),
    }
) is None

GLOBAL_NCCU_STUDENT_GROUP_PRODUCT_IDS = (
    "264396MZ9GY3221A11Z10000000",
    "264396MZ9GY3221A11Z10000001",
    "264396MZ9GY3221A11Z10000002",
)
expected_global_nccu_revisions = {
    "264396MZ9GY3221A11Z10000000": ("original", 19, False),
    "264396MZ9GY3221A11Z10000001": ("104-first-revision", 22, True),
    "264396MZ9GY3221A11Z10000002": ("107-second-revision", 22, True),
}
for product_id in GLOBAL_NCCU_STUDENT_GROUP_PRODUCT_IDS:
    document = tii_life_164_document(product_id)
    expected_revision, expected_pages, expected_regulatory_revision = (
        expected_global_nccu_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_global_nccu_student_group_fixed_schedule(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "global-nccu-student-group-fixed-schedule-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    assert schedule["selection_label"] == "固定保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fixed_face_amount"] == 1_000_000
    assert characteristics["disability_levels"] == 11
    assert characteristics["disability_living_assistance_levels"] == "1-3"
    assert characteristics["disability_living_assistance_annual_payments"] == 4
    assert characteristics["major_burn_rate_percent"] == 25
    assert characteristics["hospital_daily_days_limit"] == 90
    assert characteristics["fracture_daily_amount"] == 350
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["non_nhi_payment_rate_percent"] == 75
    assert characteristics["post_expiry_accident_days_limit"] == 180
    assert characteristics["death_disability_annual_cap"] == 1_000_000
    assert characteristics["specific_accidental_death_excluded_from_cap"] is True
    assert characteristics["regulatory_revision"] is expected_regulatory_revision

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "fixed-face-amount",
        "death-benefit",
        "specific-accidental-death-additional",
        "disability-benefit",
        "disability-living-assistance-annual",
        "major-burn",
        "hospital-daily-general",
        "hospital-daily-icu",
        "hospital-daily-burn-ward",
        "hospital-daily-cancer",
        "fracture-no-hospital-daily",
        "inpatient-routine-expense-limit",
        "surgery-expense-limit",
        "inpatient-medical-expense-limit",
        "accident-outpatient-limit",
        "major-illness-benefit",
        "campus-group-food-poisoning",
        "first-cancer-benefit",
        "death-disability-annual-cap",
    }
    assert entries["fixed-face-amount"]["amount"] == 1_000_000
    assert entries["death-benefit"]["amount"] == 1_000_000
    assert entries["specific-accidental-death-additional"]["amount"] == 1_000_000
    assert entries["specific-accidental-death-additional"]["aggregation_rule"] == "conditional_additive"
    assert entries["disability-benefit"]["rate_min_percent"] == 5
    assert entries["disability-benefit"]["rate_max_percent"] == 100
    assert entries["disability-benefit"]["amount_tiers"][0]["amount"] == 1_000_000
    assert entries["disability-benefit"]["amount_tiers"][-1]["amount"] == 50_000
    assert entries["disability-living-assistance-annual"]["amount_tiers"][0]["amount"] == 250_000
    assert entries["disability-living-assistance-annual"]["amount_tiers"][2]["amount"] == 200_000
    assert entries["major-burn"]["amount"] == 250_000
    assert entries["major-burn"]["rate_percent"] == 25
    assert entries["hospital-daily-general"]["amount"] == 750
    assert entries["hospital-daily-icu"]["amount"] == 1_500
    assert entries["hospital-daily-burn-ward"]["amount"] == 1_500
    assert entries["hospital-daily-cancer"]["amount"] == 1_500
    assert entries["fracture-no-hospital-daily"]["amount"] == 350
    assert entries["inpatient-routine-expense-limit"]["amount_tiers"] == [
        {"label": "一般住院每日", "amount": 500},
        {"label": "加護/燒燙傷/癌症住院每日", "amount": 1_500},
    ]
    assert entries["surgery-expense-limit"]["amount_tiers"] == [
        {"label": "一般手術", "amount": 10_000},
        {"label": "重大手術", "amount": 50_000},
    ]
    assert entries["inpatient-medical-expense-limit"]["amount"] == 20_000
    assert entries["accident-outpatient-limit"]["amount"] == 5_000
    assert entries["major-illness-benefit"]["amount"] == 50_000
    assert entries["campus-group-food-poisoning"]["amount"] == 1_000
    assert entries["first-cancer-benefit"]["amount_tiers"] == [
        {"label": "原位癌", "amount": 30_000},
        {"label": "原位癌以外之癌症", "amount": 150_000},
    ]
    assert entries["death-disability-annual-cap"]["amount"] == 1_000_000
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_164_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == expected_pages
    assert parse_global_nccu_student_group_fixed_schedule(completed_document) == schedule
    assert parse_global_nccu_student_group_fixed_schedule(
        tii_life_164_document(product_id, "F")
    ) is None

global_nccu_base = tii_life_164_document(GLOBAL_NCCU_STUDENT_GROUP_PRODUCT_IDS[0])
assert parse_global_nccu_student_group_fixed_schedule(
    {**global_nccu_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_global_nccu_student_group_fixed_schedule(
    {**global_nccu_base, "product_id": "264396MZ9GY3221A11Z10999999"}
) is None
assert parse_global_nccu_student_group_fixed_schedule(
    {
        **global_nccu_base,
        "text": global_nccu_base["text"].replace("新臺幣壹佰萬元", "新臺幣貳佰萬元", 1),
    }
) is None

TII_LIFE_152_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-152"
)
YUANTA_XIANGYOUXIN_MEDICAL_PRODUCT_IDS = (
    "261311RZ1AJR021A11Z10000000",
    "261311RZ1AJR021A11Z10000001",
    "261311RZ1AJR021A11Z10000002",
)


def tii_life_152_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_152_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


YUANTA_ANXIN100_CRITICAL_PRODUCT_ID = "261391MZ9GRJ023A11Z10000000"
yuanta_anxin100_document = tii_life_152_document(YUANTA_ANXIN100_CRITICAL_PRODUCT_ID)
yuanta_anxin100_schedule = parse_yuanta_anxin100_critical_illness_face_amount(
    yuanta_anxin100_document
)
assert yuanta_anxin100_schedule is not None
assert parse_plan_table_with_parser(yuanta_anxin100_document) == (
    "yuanta-anxin100-critical-illness-face-amount-v1",
    yuanta_anxin100_schedule,
)
assert yuanta_anxin100_schedule["selection_type"] == "face_amount"
assert yuanta_anxin100_schedule["selection_label"] == "保險金額"
assert yuanta_anxin100_schedule["version_characteristics"] == {
    "terms_revision": "108-original",
    "filing_date": "108.10.01",
    "filing_number": "元壽字第1080002530號",
    "disease_waiting_days": 30,
    "cancer_waiting_days": 90,
    "premium_total_multiplier": 1.09,
    "specified_critical_rate_percent": 50,
    "public_transport_accident_death_rate_percent": 100,
    "maturity_age": 100,
    "disability_terminology": "完全失能",
    "premium_waiver_disability_levels": "2-6",
    "excluded_critical_illness_item_count": 8,
}
yuanta_anxin100_entries = {
    entry["id"]: entry for entry in yuanta_anxin100_schedule["coverage_entries"]
}
assert set(yuanta_anxin100_entries) == {
    "death-or-funeral",
    "total-disability",
    "public-transport-accident-death",
    "critical-illness",
    "specified-critical-illness-additional",
    "disability-premium-waiver",
    "maturity-age-100",
}
assert yuanta_anxin100_entries["death-or-funeral"]["calculation_basis"] == "greater_of"
assert yuanta_anxin100_entries["total-disability"]["calculation_basis"] == "greater_of"
assert yuanta_anxin100_entries["critical-illness"]["calculation_basis"] == "greater_of"
assert yuanta_anxin100_entries["maturity-age-100"]["calculation_basis"] == "greater_of"
assert yuanta_anxin100_entries["specified-critical-illness-additional"]["rate_percent"] == 50
assert yuanta_anxin100_entries["public-transport-accident-death"]["rate_percent"] == 100
assert yuanta_anxin100_entries["disability-premium-waiver"]["amount_role"] == "reference"
assert any(
    "重大傷病但證明文件" in condition
    for condition in yuanta_anxin100_entries["critical-illness"]["conditions"]
)
assert parse_yuanta_anxin100_critical_illness_face_amount(
    tii_life_152_document(YUANTA_ANXIN100_CRITICAL_PRODUCT_ID, "F")
) is None
assert parse_yuanta_anxin100_critical_illness_face_amount(
    {**yuanta_anxin100_document, "product_id": "wrong-product"}
) is None
assert parse_yuanta_anxin100_critical_illness_face_amount(
    {
        **yuanta_anxin100_document,
        "text": yuanta_anxin100_document["text"].replace("一點零九倍", "一點零八倍"),
    }
) is None
yuanta_anxin100_indexed = {
    **yuanta_anxin100_document,
    "page_count": 1,
    "pages_parsed": 1,
    "text": yuanta_anxin100_document["text"].split("2 七、")[0],
}
yuanta_anxin100_completed = complete_strict_source_document(
    yuanta_anxin100_indexed,
    TII_LIFE_152_ROOT
    / YUANTA_ANXIN100_CRITICAL_PRODUCT_ID
    / f"{YUANTA_ANXIN100_CRITICAL_PRODUCT_ID}-A.pdf",
)
assert yuanta_anxin100_completed["page_count"] == 15
assert parse_yuanta_anxin100_critical_illness_face_amount(
    yuanta_anxin100_completed
) is not None


YUANTA_ZHEN_ANXIN_RETURN_CANCER_PRODUCT_IDS = (
    "261121MZ2GC2022A11Z10000004",
    "261121MZ2GC2022A11Z10000005",
)
TII_LIFE_153_ROOT = Path("work/tii-documents/tii-life-153")
TII_LIFE_153_TEXT_PATH = Path("work/tii-document-text/tii-life-153-text.json")


def tii_life_153_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_153_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    page_texts = [page.extract_text() or "" for page in PdfReader(pdf_path).pages]
    return {
        "batch_id": "tii-life-153",
        "product_id": product_id,
        "product_name": "元大人壽真安心保本防癌保險",
        "file_name": f"{product_id}-{suffix}.pdf",
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


def tii_life_153_ocr_document(product_id: str, suffix: str = "A") -> dict:
    document_type = "policy_terms" if suffix == "A" else "product_summary"
    documents = json.loads(TII_LIFE_153_TEXT_PATH.read_text(encoding="utf-8"))[
        "documents"
    ]
    document = next(
        item
        for item in documents
        if item.get("product_id") == product_id
        and item.get("document_type") == document_type
    )
    return {
        **document,
        "batch_id": "tii-life-153",
        "text": normalize_terms_text(document["text"]),
    }


expected_zhen_anxin_revisions = {
    "261121MZ2GC2022A11Z10000004": "fourth-partial-revision",
    "261121MZ2GC2022A11Z10000005": "fifth-regulatory-revision",
}
for product_id in YUANTA_ZHEN_ANXIN_RETURN_CANCER_PRODUCT_IDS:
    document = tii_life_153_document(product_id)
    schedule = parse_yuanta_zhen_anxin_return_cancer_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-zhen-anxin-return-cancer-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_zhen_anxin_revisions[product_id]
    assert characteristics["cancer_waiting_days"] == 90
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["accident_hospital_daily_rate_percent"] == 0.1
    assert characteristics["fracture_unhospitalized_daily_rate_percent"] == 0.05
    assert characteristics["low_invasive_cancer_rate_percent"] == 10
    assert characteristics["initial_cancer_low_invasive_offset"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-or-funeral-benefit",
        "accidental-death-benefit",
        "mass-transit-accidental-death-benefit",
        "total-disability-benefit",
        "accidental-first-degree-disability-benefit",
        "mass-transit-accidental-first-degree-disability-benefit",
        "accidental-disability-benefit",
        "accident-hospital-daily-benefit",
        "fracture-unhospitalized-benefit",
        "low-invasive-cancer-benefit",
        "initial-cancer-benefit",
        "maturity-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["low-invasive-cancer-benefit"]["rate_percent"] == 10
    assert entries["initial-cancer-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["unit_key"] == "annual_premium_total"
    assert parse_yuanta_zhen_anxin_return_cancer_face_amount(
        tii_life_153_document(product_id, "F")
    ) is None

    source_path = TII_LIFE_153_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = document["text"].split("第三條")[0]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 8
    assert parse_yuanta_zhen_anxin_return_cancer_face_amount(completed_document) == schedule

assert parse_yuanta_zhen_anxin_return_cancer_face_amount(
    {**tii_life_153_document(YUANTA_ZHEN_ANXIN_RETURN_CANCER_PRODUCT_IDS[0]), "product_id": "wrong-product"}
) is None


YUANTA_ZHENAI_BABY_RETURN_PRODUCT_ID = "261111M19GJB005"
yuanta_zhenai_baby_document = tii_life_153_ocr_document(
    YUANTA_ZHENAI_BABY_RETURN_PRODUCT_ID
)
yuanta_zhenai_baby_schedule = parse_yuanta_zhenai_baby_return_life_face_amount(
    yuanta_zhenai_baby_document
)
assert yuanta_zhenai_baby_schedule is not None
yuanta_zhenai_baby_integrated = parse_plan_table_with_parser(
    yuanta_zhenai_baby_document
)
assert yuanta_zhenai_baby_integrated is not None
assert yuanta_zhenai_baby_integrated[0] == (
    "yuanta-zhenai-baby-return-life-face-amount-v1"
)
assert yuanta_zhenai_baby_integrated[1] == yuanta_zhenai_baby_schedule
assert yuanta_zhenai_baby_schedule["selection_type"] == "face_amount"
assert yuanta_zhenai_baby_schedule["input_mode"] == "face_amount"
assert yuanta_zhenai_baby_schedule["selection_label"] == "保險金額"
assert yuanta_zhenai_baby_schedule["version_characteristics"] == {
    "product_family": "yuanta-zhenai-baby-return-life",
    "terms_revision": "fifth-partial-revision",
    "approval_filing_number": "金管保二字第09702091920號",
    "company_name_change_filing_number": "金管保壽字第10302008450號",
    "face_amount_required": True,
    "multiple_insured_supported": True,
    "unborn_child_policy": True,
    "insurance_benefit_basis": "policy_face_amount",
    "specific_major_disability_category_count": 18,
    "specific_major_disability_rate_percent": 50,
    "specific_major_disability_per_category_limit_times": 1,
    "specific_major_disability_cumulative_cap_percent": 100,
    "cerebral_palsy_rate_percent": 20,
    "cerebral_palsy_lifetime_limit_times": 1,
    "major_burn_rate_percent": 20,
    "accident_claim_days": 180,
    "major_burn_definition_body_surface_percent": 20,
    "survival_benefit_start_policy_anniversary": 7,
    "survival_benefit_end_policy_anniversary": 12,
    "survival_benefit_payment_count": 6,
    "survival_benefit_formula": "annual_premium_calculated_by_current_face_amount",
    "survival_benefit_single_survivor_limit": True,
    "death_refund_formula": "paid_premium_calculated_by_face_amount_at_death",
    "fetal_condition_known_exclusion": True,
    "non_participating_policy": True,
}
yuanta_zhenai_baby_entries = {
    entry["id"]: entry
    for entry in yuanta_zhenai_baby_schedule["coverage_entries"]
}
assert set(yuanta_zhenai_baby_entries) == {
    "specific-major-disability-benefit",
    "cerebral-palsy-benefit",
    "major-burn-benefit",
    "survival-benefit",
    "all-insured-death-premium-refund",
}
assert (
    yuanta_zhenai_baby_entries["specific-major-disability-benefit"]["rate_percent"]
    == 50
)
assert yuanta_zhenai_baby_entries["cerebral-palsy-benefit"]["rate_percent"] == 20
assert yuanta_zhenai_baby_entries["major-burn-benefit"]["rate_percent"] == 20
assert yuanta_zhenai_baby_entries["survival-benefit"]["unit_key"] == (
    "annual_premium_by_current_face_amount"
)
assert (
    yuanta_zhenai_baby_entries["all-insured-death-premium-refund"][
        "calculation_basis"
    ]
    == "unknown"
)
assert parse_yuanta_zhenai_baby_return_life_face_amount(
    tii_life_153_ocr_document(YUANTA_ZHENAI_BABY_RETURN_PRODUCT_ID, "F")
) is None
assert parse_yuanta_zhenai_baby_return_life_face_amount(
    {**yuanta_zhenai_baby_document, "product_id": "261111M12G00104"}
) is None
assert parse_yuanta_zhenai_baby_return_life_face_amount(
    {**yuanta_zhenai_baby_document, "page_count": 14, "pages_parsed": 14}
) is None
assert parse_yuanta_zhenai_baby_return_life_face_amount(
    {
        **yuanta_zhenai_baby_document,
        "text": yuanta_zhenai_baby_document["text"].replace(
            "每一類給付以一次為限",
            "每一類給付以二次為限",
            1,
        ),
    }
) is None


YUANTA_YUANMAN225_PRODUCT_ID = "261121MA1AYE022A11Z10000002"
yuanta_yuanman225_document = tii_life_153_document(YUANTA_YUANMAN225_PRODUCT_ID)
yuanta_yuanman225_schedule = parse_yuanta_yuanman225_interest_endowment_formula(
    yuanta_yuanman225_document
)
assert yuanta_yuanman225_schedule is not None
yuanta_yuanman225_integrated = parse_plan_table_with_parser(
    yuanta_yuanman225_document
)
assert yuanta_yuanman225_integrated is not None
assert yuanta_yuanman225_integrated[0] == (
    "yuanta-yuanman225-interest-endowment-formula-v1"
)
assert yuanta_yuanman225_integrated[1] == yuanta_yuanman225_schedule
assert yuanta_yuanman225_schedule["selection_type"] == "face_amount"
assert yuanta_yuanman225_schedule["input_mode"] == "face_amount"
assert yuanta_yuanman225_schedule["selection_label"] == "當年度保險金額"
assert yuanta_yuanman225_schedule["version_characteristics"] == {
    "product_family": "yuanta-yuanman225-interest-endowment",
    "terms_revision": "second-partial-revision",
    "filing_date": "104.05.18",
    "filing_number": "元壽字第10400661號",
    "regulatory_revision_date": "104.08.04",
    "regulatory_revision_number": "金管保壽字第10402049830號",
    "policy_period_years": 25,
    "expected_interest_rate_percent": 1.5,
    "declared_rate_frequency": "monthly",
    "value_sharing_bonus_available": True,
    "value_sharing_formula": "positive_difference_between_declared_rate_and_expected_rate_times_policy_reserve",
    "annual_insured_amount_formula": "face_amount_plus_cumulative_paid_up_addition",
    "death_benefit_formula": "greater_of_policy_reserve_or_annual_premium_total_times_1_01",
    "total_disability_benefit_formula": "greater_of_policy_reserve_or_annual_premium_total_times_1_01",
    "maturity_benefit_formula": "annual_insured_amount_times_1_6_on_25th_policy_anniversary",
    "maturity_policy_anniversary": 25,
    "maturity_multiplier": 1.6,
    "premium_multiplier": 1.01,
    "policy_reserve_required": True,
    "annual_premium_total_required": True,
    "accumulated_paid_up_additions_required": True,
    "stored_interest_before_age_16": True,
    "minor_death_refund_rule": True,
    "funeral_benefit_limit_rule": True,
    "full_disability_table_item_count": 7,
    "non_participating_policy": True,
}
yuanta_yuanman225_entries = {
    entry["id"]: entry
    for entry in yuanta_yuanman225_schedule["coverage_entries"]
}
assert set(yuanta_yuanman225_entries) == {
    "value-sharing-paid-up-addition",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "maturity-benefit",
}
assert yuanta_yuanman225_entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
assert yuanta_yuanman225_entries["total-disability-benefit"]["unit_key"] == (
    "greater_of_policy_reserve_premium_total_1_01"
)
assert yuanta_yuanman225_entries["maturity-benefit"]["rate_percent"] == 160
assert yuanta_yuanman225_entries["value-sharing-paid-up-addition"]["amount_role"] == (
    "reference"
)
yuanta_yuanman225_source_path = (
    TII_LIFE_153_ROOT
    / YUANTA_YUANMAN225_PRODUCT_ID
    / f"{YUANTA_YUANMAN225_PRODUCT_ID}-A.pdf"
)
yuanta_yuanman225_indexed = {
    key: value
    for key, value in yuanta_yuanman225_document.items()
    if key not in {"page_count", "pages_parsed"}
}
yuanta_yuanman225_indexed["text"] = yuanta_yuanman225_indexed["text"].split(
    "第一條"
)[0]
yuanta_yuanman225_completed = complete_strict_source_document(
    yuanta_yuanman225_indexed, yuanta_yuanman225_source_path
)
assert yuanta_yuanman225_completed["page_count"] == 3
assert (
    parse_yuanta_yuanman225_interest_endowment_formula(yuanta_yuanman225_completed)
    == yuanta_yuanman225_schedule
)
assert parse_yuanta_yuanman225_interest_endowment_formula(
    {**yuanta_yuanman225_document, "product_id": "261121MA1AYE022A11Z10000001"}
) is None
assert parse_yuanta_yuanman225_interest_endowment_formula(
    tii_life_153_document(YUANTA_YUANMAN225_PRODUCT_ID, "F")
) is None
assert parse_yuanta_yuanman225_interest_endowment_formula(
    {**yuanta_yuanman225_document, "page_count": 2, "pages_parsed": 2}
) is None
assert parse_yuanta_yuanman225_interest_endowment_formula(
    {
        **yuanta_yuanman225_document,
        "text": yuanta_yuanman225_document["text"].replace(
            "一點零一倍",
            "一點零二倍",
        ),
    }
) is None


YUANTA_MEINIANDUOLI_USD_PRODUCTS = {
    "261121MA1AFU023B11Z10000000": {
        "terms_revision": "original",
        "disability_term": "殘廢",
        "page_count": 5,
        "has_article_2_definition": False,
    },
    "261121MA1AFU023B11Z10000001": {
        "terms_revision": "first-partial-revision",
        "disability_term": "失能",
        "page_count": 5,
        "has_article_2_definition": False,
    },
    "261121MA1AFU023B11Z10000002": {
        "terms_revision": "second-partial-revision",
        "disability_term": "失能",
        "page_count": 5,
        "has_article_2_definition": False,
    },
    "261121MA1AFU023B11Z10000003": {
        "terms_revision": "third-partial-revision",
        "disability_term": "失能",
        "page_count": 5,
        "has_article_2_definition": True,
    },
    "261121MA1AFU023B11Z10000004": {
        "terms_revision": "fourth-partial-revision",
        "disability_term": "失能",
        "page_count": 6,
        "has_article_2_definition": True,
    },
}
for product_id, expected in YUANTA_MEINIANDUOLI_USD_PRODUCTS.items():
    document = tii_life_153_document(product_id)
    schedule = parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == (
        "yuanta-meinianduoli-usd-incremental-return-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["product_family"] == (
        "yuanta-meinianduoli-usd-incremental-return-whole-life"
    )
    assert characteristics["terms_revision"] == expected["terms_revision"]
    assert characteristics["currency"] == "USD"
    assert characteristics["expected_interest_rate_percent"] == 2.5
    assert characteristics["premium_multiplier"] == 1.06
    assert characteristics["survival_benefit_during_payment_rate_percent"] == 1.8
    assert characteristics["survival_benefit_after_paid_up_annual_rate_percent"] == 15
    assert characteristics["maturity_age"] == 111
    assert characteristics["disability_term"] == expected["disability_term"]
    assert characteristics["foreign_currency_policy"] is True
    assert characteristics["minor_death_refund_rule"] is True
    assert characteristics.get("benefit_amount_definition_in_article_2", False) == (
        expected["has_article_2_definition"]
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "survival-benefit-during-payment",
        "survival-benefit-after-paid-up",
        "maturity-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["multiplier"] == 1.06
    assert entries["survival-benefit-during-payment"]["rate_percent"] == 1.8
    assert entries["survival-benefit-after-paid-up"]["rate_percent"] == 15
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert entries["value-sharing-bonus"]["amount_role"] == "reference"

    source_path = TII_LIFE_153_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = indexed_document["text"].split("第十六條")[0]
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected["page_count"]
    assert (
        parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
            completed_document
        )
        == schedule
    )
    assert parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
        tii_life_153_document(product_id, "F")
    ) is None
    assert parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
        {**document, "page_count": expected["page_count"] + 1}
    ) is None
    assert parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
        {**document, "file_name": f"{product_id}-F.pdf"}
    ) is None

first_meinianduoli_document = tii_life_153_document(
    "261121MA1AFU023B11Z10000000"
)
assert parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
    {**first_meinianduoli_document, "product_id": "261121MA1AFU023B11Z10000001"}
) is None
assert parse_yuanta_meinianduoli_usd_incremental_return_whole_life_formula(
    {
        **first_meinianduoli_document,
        "text": first_meinianduoli_document["text"].replace(
            "預定利率 (2.5%)",
            "預定利率 (9.9%)",
            1,
        ),
    }
) is None


yuanta_xiangyouxin_expected = {
    "hospital-daily": (500, 1_000, 1_500, 2_000, 2_500, 3_000),
    "inpatient-medical-limit": (150_000, 200_000, 250_000, 300_000, 350_000, 400_000),
    "surgery-limit": (150_000, 200_000, 250_000, 300_000, 350_000, 400_000),
    "pre-admission-outpatient-limit": (1_000, 1_000, 1_000, 2_000, 2_000, 2_000),
    "post-discharge-outpatient-limit": (3_000, 3_000, 3_000, 6_000, 6_000, 6_000),
}
expected_yuanta_xiangyouxin_revisions = {
    "261311RZ1AJR021A11Z10000000": ("original", False),
    "261311RZ1AJR021A11Z10000001": ("108-revised", False),
    "261311RZ1AJR021A11Z10000002": ("109-revised", True),
}
for product_id in YUANTA_XIANGYOUXIN_MEDICAL_PRODUCT_IDS:
    document = tii_life_152_document(product_id)
    expected_revision, expected_medical_opinion_revision = expected_yuanta_xiangyouxin_revisions[
        product_id
    ]
    assert document["page_count"] == document["pages_parsed"] == 13
    schedule = parse_yuanta_xiangyouxin_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-xiangyouxin-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計劃別"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計劃一",
        "計劃二",
        "計劃三",
        "計劃四",
        "計劃五",
        "計劃六",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["renewal_disease_waiting_days"] == 0
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["nhi_uncovered_payment_rate_percent"] == 65
    assert characteristics["inpatient_medical_limit_after_60_days_multiplier"] == 2
    assert characteristics["outpatient_pre_admission_days"] == 7
    assert characteristics["outpatient_post_discharge_days"] == 30
    assert characteristics["maximum_renewal_age_primary_or_spouse"] == 84
    assert characteristics["maximum_renewal_age_child"] == 23
    assert characteristics["terms_revision"] == expected_revision
    assert (
        characteristics["claims_review_medical_opinion_revision"]
        is expected_medical_opinion_revision
    )
    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert len(entries) == len(plan["coverage_entries"]) == 5
        assert set(entries) == set(yuanta_xiangyouxin_expected)
        for entry_id, amounts in yuanta_xiangyouxin_expected.items():
            assert entries[entry_id]["amount"] == amounts[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert entries[entry_id].get("conditions")
        assert entries["inpatient-medical-limit"]["amount_tiers"][1]["amount"] == (
            entries["inpatient-medical-limit"]["amount"] * 2
        )
        assert entries["inpatient-medical-limit"]["amount_role"] == "limit"
        assert entries["surgery-limit"]["limit_scope"] == "per_surgery"

    source_path = TII_LIFE_152_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 13
    assert parse_yuanta_xiangyouxin_medical_plan_table(completed_document) == schedule
    assert parse_yuanta_xiangyouxin_medical_plan_table(tii_life_152_document(product_id, "F")) is None

yuanta_xiangyouxin_base = tii_life_152_document(YUANTA_XIANGYOUXIN_MEDICAL_PRODUCT_IDS[0])
assert parse_yuanta_xiangyouxin_medical_plan_table(
    {**yuanta_xiangyouxin_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_xiangyouxin_medical_plan_table(
    {**yuanta_xiangyouxin_base, "document_type": "product_summary"}
) is None
assert parse_yuanta_xiangyouxin_medical_plan_table(
    {
        **yuanta_xiangyouxin_base,
        "text": yuanta_xiangyouxin_base["text"].replace(
            "500 1,000 1,500 2,000 2,500 3,000",
            "600 1,000 1,500 2,000 2,500 3,000",
            1,
        ),
    }
) is None

YUANTA_XIANGAN_MEDICAL_PRODUCT_ID = "261311RZ1ANR021A11Z10000003"
yuanta_xiangan_expected = {
    "room-daily-limit": (1_000, 1_500, 2_000, 2_500, 3_000, 4_000),
    "inpatient-medical-limit": (125_000, 150_000, 175_000, 200_000, 225_000, 275_000),
    "surgery-limit": (80_000, 100_000, 120_000, 140_000, 160_000, 200_000),
    "pre-admission-outpatient-limit": (1_000, 1_000, 2_000, 2_000, 2_000, 2_000),
    "post-discharge-outpatient-limit": (3_000, 3_000, 6_000, 6_000, 6_000, 6_000),
    "supplement-limit": (2_000, 3_000, 4_000, 5_000, 6_000, 8_000),
}
yuanta_xiangan_document = tii_life_152_document(YUANTA_XIANGAN_MEDICAL_PRODUCT_ID)
assert yuanta_xiangan_document["page_count"] == yuanta_xiangan_document["pages_parsed"] == 8
yuanta_xiangan_schedule = parse_yuanta_xiangan_medical_plan_table(yuanta_xiangan_document)
assert yuanta_xiangan_schedule is not None
yuanta_xiangan_integrated = parse_plan_table_with_parser(yuanta_xiangan_document)
assert yuanta_xiangan_integrated is not None
assert yuanta_xiangan_integrated[0] == "yuanta-xiangan-medical-plan-v1"
assert yuanta_xiangan_integrated[1] == yuanta_xiangan_schedule
assert yuanta_xiangan_schedule["selection_type"] == yuanta_xiangan_schedule["input_mode"] == "plan"
assert yuanta_xiangan_schedule["selection_label"] == "投保計劃別"
assert [plan["label"] for plan in yuanta_xiangan_schedule["plan_options"]] == [
    "計劃一",
    "計劃二",
    "計劃三",
    "計劃四",
    "計劃五",
    "計劃六",
]
yuanta_xiangan_characteristics = yuanta_xiangan_schedule["version_characteristics"]
assert yuanta_xiangan_characteristics["terms_revision"] == "109-third-revision"
assert yuanta_xiangan_characteristics["plan_count"] == 6
assert yuanta_xiangan_characteristics["disease_initial_waiting_days"] == 30
assert yuanta_xiangan_characteristics["day_hospital_excluded"] is True
assert yuanta_xiangan_characteristics["icu_room_limit_multiplier"] == 3
assert yuanta_xiangan_characteristics["icu_room_limit_days"] == 15
assert yuanta_xiangan_characteristics["inpatient_medical_limit_after_60_days_multiplier"] == 2
assert yuanta_xiangan_characteristics["pre_admission_outpatient_days"] == 7
assert yuanta_xiangan_characteristics["post_discharge_outpatient_days"] == 30
assert yuanta_xiangan_characteristics["same_hospital_readmission_days"] == 14
assert yuanta_xiangan_characteristics["post_expiry_readmission_excluded"] is True
assert yuanta_xiangan_characteristics["non_nhi_payment_rate_percent"] == 65
assert yuanta_xiangan_characteristics["surgery_table_min_percent"] == 10
assert yuanta_xiangan_characteristics["surgery_table_max_percent"] == 300
assert yuanta_xiangan_characteristics["newborn_metabolic_disease_revision"] is True
assert yuanta_xiangan_characteristics["claims_review_medical_opinion_revision"] is True
for plan_index, plan in enumerate(yuanta_xiangan_schedule["plan_options"]):
    entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
    assert set(entries) == set(yuanta_xiangan_expected)
    for entry_id, values in yuanta_xiangan_expected.items():
        assert entries[entry_id]["amount"] == values[plan_index]
        assert entries[entry_id]["source"] == "terms"
        assert entries[entry_id].get("conditions")
    assert entries["room-daily-limit"]["amount_tiers"][1]["amount"] == (
        entries["room-daily-limit"]["amount"] * 3
    )
    assert entries["inpatient-medical-limit"]["amount_tiers"][1]["amount"] == (
        entries["inpatient-medical-limit"]["amount"] * 2
    )
    assert entries["surgery-limit"]["rate_min_percent"] == 10
    assert entries["surgery-limit"]["rate_max_percent"] == 300

source_path = TII_LIFE_152_ROOT / YUANTA_XIANGAN_MEDICAL_PRODUCT_ID / f"{YUANTA_XIANGAN_MEDICAL_PRODUCT_ID}-A.pdf"
indexed_document = {
    key: value
    for key, value in yuanta_xiangan_document.items()
    if key not in {"page_count", "pages_parsed"}
}
indexed_document["text"] = normalize_terms_text(
    "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
)
completed_document = complete_strict_source_document(indexed_document, source_path)
assert completed_document["page_count"] == completed_document["pages_parsed"] == 8
assert parse_yuanta_xiangan_medical_plan_table(completed_document) == yuanta_xiangan_schedule
assert parse_yuanta_xiangan_medical_plan_table(
    tii_life_152_document(YUANTA_XIANGAN_MEDICAL_PRODUCT_ID, "F")
) is None
assert parse_yuanta_xiangan_medical_plan_table(
    {**yuanta_xiangan_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_xiangan_medical_plan_table(
    {**yuanta_xiangan_document, "product_id": "261311RZ1ANR021A11Z10999999"}
) is None
assert parse_yuanta_xiangan_medical_plan_table(
    {
        **yuanta_xiangan_document,
        "text": yuanta_xiangan_document["text"].replace(
            "125,000 150,000 175,000 200,000 225,000 275,000",
            "126,000 150,000 175,000 200,000 225,000 275,000",
            1,
        ),
    }
) is None

YUANTA_YUANQI_SHIZU_PRODUCT_IDS = (
    "261311RZ1AYR021A11Z10000000",
    "261311RZ1AYR021A11Z10000001",
)
expected_yuanta_yuanqi_shizu_revisions = {
    "261311RZ1AYR021A11Z10000000": ("original", False),
    "261311RZ1AYR021A11Z10000001": ("111-revised", True),
}
yuanta_yuanqi_expected_amounts = {
    "hospital-daily": (1_000, 1_500, 2_000, 2_500, 3_000),
    "medical-device-subsidy": (10_000, 15_000, 20_000, 25_000, 30_000),
    "special-procedure": (3_000, 3_000, 3_000, 3_000, 3_000),
    "daily-room-limit": (1_000, 1_500, 2_000, 2_500, 3_000),
    "inpatient-medical-limit": (75_000, 100_000, 125_000, 150_000, 175_000),
    "pre-admission-outpatient-limit": (1_000, 1_000, 1_000, 1_000, 1_000),
    "post-discharge-outpatient-limit": (3_000, 3_000, 3_000, 3_000, 3_000),
    "inpatient-surgery-limit": (60_000, 60_000, 80_000, 80_000, 80_000),
    "outpatient-surgery-limit": (30_000, 30_000, 40_000, 40_000, 40_000),
}
for product_id in YUANTA_YUANQI_SHIZU_PRODUCT_IDS:
    document = tii_life_152_document(product_id)
    expected_revision, expected_notice = expected_yuanta_yuanqi_shizu_revisions[
        product_id
    ]
    assert document["page_count"] == document["pages_parsed"] == 14
    schedule = parse_yuanta_yuanqi_shizu_hospital_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-yuanqi-shizu-hospital-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計劃別"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計劃一",
        "計劃二",
        "計劃三",
        "計劃四",
        "計劃五",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 5
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["renewal_disease_waiting_days"] == 0
    assert characteristics["cancer_screening_min_age"] == 30
    assert characteristics["hospital_daily_days_limit"] == 365
    assert characteristics["mental_hospital_days_limit"] == 90
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["non_nhi_payment_rate_percent"] == 65
    assert characteristics["medical_device_heart_stent_annual_limit"] == 2
    assert characteristics["special_procedure_annual_limit"] == 2
    assert characteristics["surgery_table_min_percent"] == 3
    assert characteristics["surgery_table_max_percent"] == 300
    assert characteristics["insured_notice_revision"] is expected_notice

    for plan_index, plan in enumerate(schedule["plan_options"]):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert set(entries) == {
            "cancer-screening-reward",
            *yuanta_yuanqi_expected_amounts.keys(),
        }
        assert entries["cancer-screening-reward"]["rate_percent"] == 2
        assert entries["cancer-screening-reward"]["unit_key"] == "annual_premium"
        for entry_id, values in yuanta_yuanqi_expected_amounts.items():
            assert entries[entry_id]["amount"] == values[plan_index]
            assert entries[entry_id]["source"] == "terms"
            assert entries[entry_id].get("conditions")
        assert entries["inpatient-surgery-limit"]["rate_min_percent"] == 3
        assert entries["inpatient-surgery-limit"]["rate_max_percent"] == 300
        assert entries["outpatient-surgery-limit"]["rate_min_percent"] == 3
        assert entries["outpatient-surgery-limit"]["rate_max_percent"] == 300
    assert parse_yuanta_yuanqi_shizu_hospital_medical_plan_table(
        tii_life_152_document(product_id, "F")
    ) is None

yuanta_yuanqi_base = tii_life_152_document(YUANTA_YUANQI_SHIZU_PRODUCT_IDS[0])
assert parse_yuanta_yuanqi_shizu_hospital_medical_plan_table(
    {**yuanta_yuanqi_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_yuanqi_shizu_hospital_medical_plan_table(
    {**yuanta_yuanqi_base, "product_id": "261311RZ1AYR021A11Z10999999"}
) is None
assert parse_yuanta_yuanqi_shizu_hospital_medical_plan_table(
    {
        **yuanta_yuanqi_base,
        "text": yuanta_yuanqi_base["text"].replace("75,000 100,000 125,000 150,000 175,000", "76,000 100,000 125,000 150,000 175,000", 1),
    }
) is None

YUANTA_GROUP_HOSPITAL_MEDICAL_PRODUCT_IDS = (
    "261313MZ1AGHE21A11Z10000000",
    "261313MZ1AGHE21A11Z10000001",
    "261313MZ1AGHE21A11Z10000002",
)
expected_yuanta_group_hospital_revisions = {
    "261313MZ1AGHE21A11Z10000000": ("original", False, "original", 15),
    "261313MZ1AGHE21A11Z10000001": ("111-revised", True, "original", 14),
    "261313MZ1AGHE21A11Z10000002": ("113-revised", True, "113-day-care", 16),
}
yuanta_group_hospital_expected_entries = {
    "daily-room-limit",
    "inpatient-medical-limit",
    "surgery-fee-limit",
    "pre-post-outpatient-limit",
    "hospital-daily",
}
for product_id in YUANTA_GROUP_HOSPITAL_MEDICAL_PRODUCT_IDS:
    document = tii_life_152_document(product_id)
    expected_revision, expected_notice, expected_day_hospital_revision, expected_pages = (
        expected_yuanta_group_hospital_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_yuanta_group_hospital_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-group-hospital-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計劃別"
    assert len(schedule["plan_options"]) == 21
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 21
    assert characteristics["disease_initial_waiting_days"] == 0
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["day_hospital_definition_revision"] == expected_day_hospital_revision
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["non_nhi_payment_rate_percent"] == 65
    assert characteristics["inpatient_medical_limit_daily_multiplier"] == 40
    assert characteristics["surgery_limit_daily_multiplier"] == 40
    assert characteristics["insured_notice_revision"] is expected_notice
    for plan_index, plan in enumerate(schedule["plan_options"]):
        daily_amount = 500 + plan_index * 100
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert set(entries) == yuanta_group_hospital_expected_entries
        assert entries["daily-room-limit"]["amount"] == daily_amount
        assert entries["pre-post-outpatient-limit"]["amount"] == daily_amount
        assert entries["hospital-daily"]["amount"] == daily_amount
        assert entries["inpatient-medical-limit"]["amount"] == daily_amount * 40
        assert entries["surgery-fee-limit"]["amount"] == daily_amount * 40
        assert entries["surgery-fee-limit"]["rate_min_percent"] == 10
        assert entries["surgery-fee-limit"]["rate_max_percent"] == 200
        assert all(entry["source"] == "terms" for entry in entries.values())
    assert parse_yuanta_group_hospital_medical_plan_table(
        tii_life_152_document(product_id, "F")
    ) is None

yuanta_group_hospital_base = tii_life_152_document(YUANTA_GROUP_HOSPITAL_MEDICAL_PRODUCT_IDS[0])
assert parse_yuanta_group_hospital_medical_plan_table(
    {**yuanta_group_hospital_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_group_hospital_medical_plan_table(
    {**yuanta_group_hospital_base, "product_id": "261313MZ1AGHE21A11Z10999999"}
) is None
assert parse_yuanta_group_hospital_medical_plan_table(
    {
        **yuanta_group_hospital_base,
        "text": yuanta_group_hospital_base["text"].replace(
            "每次住院醫療費用保險金給付限額 20,000",
            "每次住院醫療費用保險金給付限額 21,000",
            1,
        ),
    }
) is None

YUANTA_HEALTH_LIFE_EARLY_PRODUCT_IDS = (
    "261311MZ1GA2023A11Z10000000",
    "261311MZ1GA2023A11Z10000001",
)
expected_yuanta_health_life_early_revisions = {
    "261311MZ1GA2023A11Z10000000": ("original", False),
    "261311MZ1GA2023A11Z10000001": ("105-revised", True),
}
yuanta_health_life_early_expected_entries = {
    "daily-amount-base",
    "hospital-daily-first-30-days",
    "hospital-daily-after-30-days",
    "intensive-care-daily",
    "pre-post-outpatient-daily",
    "discharge-recuperation-daily",
    "surgery-medical",
    "child-specific-disease",
    "child-fracture",
    "child-food-poisoning",
    "severe-burn",
    "moderate-burn",
    "burn-unit-daily",
    "burn-outpatient-daily",
    "severe-burn-rehab-monthly",
    "moderate-burn-rehab-monthly",
    "death-funeral-reference-base",
    "maturity-reference-base",
    "premium-waiver",
    "medical-benefits-lifetime-cap",
}
for product_id in YUANTA_HEALTH_LIFE_EARLY_PRODUCT_IDS:
    document = tii_life_152_document(product_id)
    expected_revision, expected_regulatory_revision = (
        expected_yuanta_health_life_early_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == 11
    schedule = parse_yuanta_health_life_early_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-health-life-early-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["daily_amount_face_amount_rate_percent"] == 1
    assert characteristics["hospital_daily_days_limit"] == 365
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["cumulative_medical_cap_daily_multiplier"] == 3800
    assert characteristics["surgery_min_daily_multiplier"] == 2
    assert characteristics["surgery_max_daily_multiplier"] == 60
    assert characteristics["child_benefit_max_age"] == 14
    assert characteristics["severe_burn_daily_multiplier"] == 250
    assert characteristics["moderate_burn_daily_multiplier"] == 100
    assert characteristics["maturity_age"] == 111
    assert characteristics["regulatory_revision"] is expected_regulatory_revision
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == yuanta_health_life_early_expected_entries
    assert entries["daily-amount-base"]["rate_percent"] == 1
    assert entries["hospital-daily-first-30-days"]["rate_percent"] == 1
    assert entries["hospital-daily-after-30-days"]["rate_percent"] == 2
    assert entries["intensive-care-daily"]["rate_percent"] == 2
    assert entries["pre-post-outpatient-daily"]["rate_percent"] == 0.25
    assert entries["discharge-recuperation-daily"]["rate_percent"] == 0.5
    assert entries["surgery-medical"]["multiplier"] == 60
    assert entries["surgery-medical"]["rate_min_percent"] == 2
    assert entries["surgery-medical"]["rate_max_percent"] == 60
    assert entries["child-specific-disease"]["rate_percent"] == 15
    assert entries["child-fracture"]["multiplier"] == 60
    assert entries["child-food-poisoning"]["rate_percent"] == 3
    assert entries["severe-burn"]["rate_percent"] == 250
    assert entries["moderate-burn"]["rate_percent"] == 100
    assert entries["burn-unit-daily"]["rate_percent"] == 3
    assert entries["burn-outpatient-daily"]["rate_percent"] == 0.5
    assert entries["severe-burn-rehab-monthly"]["rate_percent"] == 10
    assert entries["moderate-burn-rehab-monthly"]["rate_percent"] == 5
    assert entries["death-funeral-reference-base"]["rate_percent"] == 106
    assert entries["maturity-reference-base"]["rate_percent"] == 106
    assert entries["premium-waiver"]["multiplier"] == 1
    assert entries["medical-benefits-lifetime-cap"]["multiplier"] == 3800
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_152_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 11
    assert parse_yuanta_health_life_early_face_amount(completed_document) == schedule
    assert parse_yuanta_health_life_early_face_amount(
        tii_life_152_document(product_id, "F")
    ) is None

yuanta_health_life_early_base = tii_life_152_document(YUANTA_HEALTH_LIFE_EARLY_PRODUCT_IDS[0])
assert parse_yuanta_health_life_early_face_amount(
    {**yuanta_health_life_early_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_health_life_early_face_amount(
    {**yuanta_health_life_early_base, "product_id": "261311MZ1GA2023A11Z10999999"}
) is None
assert parse_yuanta_health_life_early_face_amount(
    {
        **yuanta_health_life_early_base,
        "text": yuanta_health_life_early_base["text"].replace(
            "住院給付日額」係指本契約之保險金額乘以百分之一",
            "住院給付日額」係指本契約之保險金額乘以百分之二",
            1,
        ),
    }
) is None

YUANTA_NEW_ACCOUNT_MEDICAL_PRODUCT_IDS = (
    "261311MZ1GA1023A11Z10000009",
    "261311MZ1GA1023A11Z10000010",
)
expected_yuanta_new_account_revisions = {
    "261311MZ1GA1023A11Z10000009": ("108-revised", False),
    "261311MZ1GA1023A11Z10000010": ("108-10-revised", True),
}
yuanta_new_account_common_entries = {
    "hospital-daily-first-30-days",
    "hospital-daily-after-30-days",
    "intensive-care-daily",
    "burn-unit-daily",
    "pre-post-outpatient-daily",
    "discharge-recuperation-daily",
    "surgery-medical",
    "cancer-major-disease-care-daily",
    "radiotherapy-chemotherapy-daily",
    "child-specific-disease",
    "child-fracture",
    "child-food-poisoning",
    "total-disability-care-annual",
    "death-funeral-reference-base",
    "total-disability-reference-base",
    "medical-benefits-lifetime-cap",
}
yuanta_new_account_type_b_entries = {
    "cancer-diagnosis",
    "breast-reconstruction",
    "major-disease-diagnosis",
}
for product_id in YUANTA_NEW_ACCOUNT_MEDICAL_PRODUCT_IDS:
    document = tii_life_152_document(product_id)
    expected_revision, expected_medical_opinion_revision = (
        expected_yuanta_new_account_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == 11
    schedule = parse_yuanta_new_account_medical_type_daily(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-new-account-medical-type-daily-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保型別與住院給付日額"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "甲型（輸入住院給付日額）",
        "乙型（輸入住院給付日額）",
    ]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["cancer_initial_waiting_days"] == 30
    assert characteristics["major_disease_initial_waiting_days"] == 30
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["face_amount_daily_multiplier"] == 500
    assert characteristics["medical_lifetime_cap_daily_multiplier"] == 1500
    assert characteristics["medical_opinion_revision"] is expected_medical_opinion_revision

    type_a_entries = {
        entry["id"]: entry
        for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    type_b_entries = {
        entry["id"]: entry
        for entry in schedule["plan_options"][1]["coverage_entries"]
    }
    assert set(type_a_entries) == yuanta_new_account_common_entries
    assert set(type_b_entries) == (
        yuanta_new_account_common_entries | yuanta_new_account_type_b_entries
    )
    assert type_a_entries["hospital-daily-first-30-days"]["rate_percent"] == 100
    assert type_a_entries["hospital-daily-after-30-days"]["rate_percent"] == 200
    assert type_a_entries["intensive-care-daily"]["rate_percent"] == 200
    assert type_a_entries["burn-unit-daily"]["rate_percent"] == 300
    assert type_a_entries["pre-post-outpatient-daily"]["rate_percent"] == 25
    assert type_a_entries["discharge-recuperation-daily"]["rate_percent"] == 50
    assert type_a_entries["surgery-medical"]["multiplier"] == 8
    assert type_a_entries["child-specific-disease"]["multiplier"] == 15
    assert type_a_entries["child-fracture"]["multiplier"] == 60
    assert type_a_entries["child-food-poisoning"]["multiplier"] == 3
    assert type_a_entries["total-disability-care-annual"]["multiplier"] == 25
    assert type_a_entries["death-funeral-reference-base"]["multiplier"] == 500
    assert type_a_entries["medical-benefits-lifetime-cap"]["multiplier"] == 1500
    assert type_b_entries["cancer-diagnosis"]["multiplier"] == 100
    assert type_b_entries["breast-reconstruction"]["multiplier"] == 50
    assert type_b_entries["major-disease-diagnosis"]["multiplier"] == 150
    for entry in type_b_entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_152_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 11
    assert parse_yuanta_new_account_medical_type_daily(completed_document) == schedule
    assert parse_yuanta_new_account_medical_type_daily(
        tii_life_152_document(product_id, "F")
    ) is None

yuanta_new_account_base = tii_life_152_document(YUANTA_NEW_ACCOUNT_MEDICAL_PRODUCT_IDS[0])
assert parse_yuanta_new_account_medical_type_daily(
    {**yuanta_new_account_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_yuanta_new_account_medical_type_daily(
    {**yuanta_new_account_base, "document_type": "product_summary"}
) is None
assert parse_yuanta_new_account_medical_type_daily(
    {
        **yuanta_new_account_base,
        "text": yuanta_new_account_base["text"].replace(
            "住院給付日額」的二倍乘以實際住加護病房的日數",
            "住院給付日額」的一倍乘以實際住加護病房的日數",
            1,
        ),
    }
) is None

FUBON_GOLDEN_HEALTH_PRODUCT_IDS = (
    "209311MZ1B00823A11Z10000000",
    "209311MZ1B00823A11Z10000001",
)


def fubon_golden_health_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_050_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


expected_fubon_golden_health_revisions = {
    "209311MZ1B00823A11Z10000000": ("original", False),
    "209311MZ1B00823A11Z10000001": ("109-revised", True),
}
for product_id in FUBON_GOLDEN_HEALTH_PRODUCT_IDS:
    document = fubon_golden_health_document(product_id)
    expected_revision, expected_medical_opinion_revision = (
        expected_fubon_golden_health_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == 31
    schedule = parse_fubon_golden_health_whole_life_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-golden-health-whole-life-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["medical_opinion_revision"] is expected_medical_opinion_revision
    assert characteristics["disease_initial_waiting_days"] == 30
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["non_nhi_payment_rate_percent"] == 75
    assert characteristics["icu_daily_multiplier"] == 1.5
    assert characteristics["icu_daily_multiplier_days_limit"] == 7
    assert characteristics["hospital_daily_days_limit"] == 365
    assert characteristics["chronic_or_mental_annual_days_limit"] == 32
    assert characteristics["outpatient_medical_annual_days_limit"] == 20

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "hospital-daily",
        "daily-room-board-limit",
        "inpatient-medical-surgery-limit",
        "outpatient-surgery-limit",
        "outpatient-medical-limit",
        "medical-lifetime-cap",
        "death-benefit-reference-base",
        "maturity-benefit-reference-base",
    }
    assert entries["hospital-daily"]["amount"] == 5_000
    assert entries["hospital-daily"]["multiplier"] == 1.5
    assert entries["daily-room-board-limit"]["amount"] == 5_000
    assert entries["inpatient-medical-surgery-limit"]["amount"] == 500_000
    assert entries["inpatient-medical-surgery-limit"]["amount_tiers"][0]["amount"] == 500_000
    assert entries["inpatient-medical-surgery-limit"]["amount_tiers"][1]["amount"] == 750_000
    assert entries["outpatient-surgery-limit"]["amount"] == 100_000
    assert entries["outpatient-medical-limit"]["amount"] == 10_000
    assert entries["medical-lifetime-cap"]["amount"] == 3_000_000
    assert entries["death-benefit-reference-base"]["amount"] == 300_000
    assert entries["maturity-benefit-reference-base"]["amount"] == 3_000_000
    assert entries["death-benefit-reference-base"]["amount_role"] == "reference"
    assert entries["maturity-benefit-reference-base"]["amount_role"] == "reference"
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions") or entry["id"] == "medical-lifetime-cap"

    source_path = TII_LIFE_050_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:5])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 31
    assert parse_fubon_golden_health_whole_life_table(completed_document) == schedule
    assert parse_fubon_golden_health_whole_life_table(fubon_golden_health_document(product_id, "F")) is None

fubon_golden_health_base = fubon_golden_health_document(FUBON_GOLDEN_HEALTH_PRODUCT_IDS[0])
assert parse_fubon_golden_health_whole_life_table(
    {**fubon_golden_health_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_fubon_golden_health_whole_life_table(
    {**fubon_golden_health_base, "document_type": "product_summary"}
) is None
assert parse_fubon_golden_health_whole_life_table(
    {
        **fubon_golden_health_base,
        "text": fubon_golden_health_base["text"].replace("5,000/日", "6,000/日", 1),
    }
) is None

TII_LIFE_008_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-008"
)
TAIWAN_FISHERMEN_GROUP_MEDICAL_PRODUCT_IDS = (
    "202313MZ1A96721A11Z10000000",
    "202313MZ1A96721A11Z10000001",
)


def tii_life_008_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = TII_LIFE_008_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


TAIWAN_GROUP_INPATIENT_LIMIT_PLAN_PRODUCT_IDS = (
    "202313MZ1A32821A11Z10000013",
    "202313MZ1A32821A11Z10000014",
)
expected_taiwan_group_inpatient_limit_plan_revisions = {
    "202313MZ1A32821A11Z10000013": ("113-thirteenth-revision", 6, False),
    "202313MZ1A32821A11Z10000014": ("113-fourteenth-revision", 7, True),
}
expected_taiwan_group_inpatient_limit_amounts = [
    (60_000, 600),
    (80_000, 1_200),
    (100_000, 1_800),
    (120_000, 2_400),
    (140_000, 3_000),
    (200_000, 4_800),
    (30_000, 900),
    (70_000, 1_000),
    (50_000, 500),
    (80_000, 800),
    (100_000, 1_000),
]
for product_id in TAIWAN_GROUP_INPATIENT_LIMIT_PLAN_PRODUCT_IDS:
    document = tii_life_008_document(product_id)
    expected_revision, expected_pages, expected_day_hospital_revision = (
        expected_taiwan_group_inpatient_limit_plan_revisions[product_id]
    )
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_taiwan_group_inpatient_limit_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-life-group-inpatient-limit-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "保險計畫"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 11
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["day_hospital_excluded"] is True
    assert characteristics["outpatient_surgery_included"] is True
    assert characteristics["nhi_paid_excluded"] is True
    assert characteristics["daily_option_policy_face_page_days_limit"] is True
    assert characteristics["day_hospital_definition_revision"] is expected_day_hospital_revision
    assert len(schedule["plan_options"]) == 11
    assert [plan["label"] for plan in schedule["plan_options"]] == [
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
    ]
    for plan, (expected_limit, expected_daily) in zip(
        schedule["plan_options"], expected_taiwan_group_inpatient_limit_amounts
    ):
        entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
        assert set(entries) == {
            "inpatient-medical-limit",
            "hospital-daily-conversion",
        }
        assert entries["inpatient-medical-limit"]["amount"] == expected_limit
        assert entries["inpatient-medical-limit"]["calculation_basis"] == "reimbursement_with_cap"
        assert entries["inpatient-medical-limit"]["aggregation_rule"] == "choose_one"
        assert entries["hospital-daily-conversion"]["amount"] == expected_daily
        assert entries["hospital-daily-conversion"]["calculation_basis"] == "per_day"
        assert entries["hospital-daily-conversion"]["aggregation_rule"] == "choose_one"
        for entry in entries.values():
            assert entry["source"] == "terms"
            assert entry.get("conditions")

    source_path = TII_LIFE_008_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == expected_pages
    assert parse_taiwan_group_inpatient_limit_plan_table(completed_document) == schedule
    assert parse_taiwan_group_inpatient_limit_plan_table(
        tii_life_008_document(product_id, "F")
    ) is None

taiwan_group_inpatient_limit_base = tii_life_008_document(
    TAIWAN_GROUP_INPATIENT_LIMIT_PLAN_PRODUCT_IDS[0]
)
assert parse_taiwan_group_inpatient_limit_plan_table(
    {**taiwan_group_inpatient_limit_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_group_inpatient_limit_plan_table(
    {**taiwan_group_inpatient_limit_base, "product_id": "202313MZ1A32821A11Z10999999"}
) is None
assert parse_taiwan_group_inpatient_limit_plan_table(
    {
        **taiwan_group_inpatient_limit_base,
        "text": taiwan_group_inpatient_limit_base["text"].replace("20 萬元", "21 萬元", 1),
    }
) is None

taiwan_shishizai_inpatient_document = tii_life_008_document(
    "202311RZ1A04A21A11Z10000000"
)
taiwan_shishizai_inpatient_schedule = parse_taiwan_shishizai_inpatient_plan_table(
    taiwan_shishizai_inpatient_document
)
assert taiwan_shishizai_inpatient_schedule is not None
assert (
    parse_plan_table_with_parser(taiwan_shishizai_inpatient_document)[0]
    == "taiwan-life-shishizai-inpatient-plan-v1"
)
assert taiwan_shishizai_inpatient_schedule["selection_type"] == "plan"
assert taiwan_shishizai_inpatient_schedule["selection_label"] == "投保計劃別"
assert taiwan_shishizai_inpatient_schedule["version_characteristics"] == {
    "filing_date": "112.08.18",
    "filing_number": "台壽字第1122320128號",
    "disease_waiting_days": 30,
    "guaranteed_renewal": True,
    "non_guaranteed_renewal_rate": True,
    "day_hospital_excluded": True,
    "hospital_days_limit": 365,
    "mental_disease_annual_days_limit": 30,
    "icu_or_burn_room_multiplier": 2,
    "outpatient_surgery_annual_count_limit": 6,
    "specified_procedure_annual_count_limit": 6,
    "pre_hospital_outpatient_days": 7,
    "post_discharge_outpatient_days": 14,
    "non_nhi_payment_percent": 65,
    "special_procedure_item_count": 93,
}
assert [plan["label"] for plan in taiwan_shishizai_inpatient_schedule["plan_options"]] == [
    "計劃一",
    "計劃二",
    "計劃三",
    "計劃四",
    "計劃五",
]
expected_shishizai_amounts = [
    (1_000, 100_000, 30_000, 600, 500_000),
    (1_500, 150_000, 40_000, 900, 750_000),
    (2_000, 200_000, 50_000, 1_200, 1_000_000),
    (2_500, 250_000, 60_000, 1_500, 1_250_000),
    (3_000, 350_000, 70_000, 1_800, 1_500_000),
]
for plan, expected in zip(
    taiwan_shishizai_inpatient_schedule["plan_options"], expected_shishizai_amounts
):
    entries = {entry["id"]: entry for entry in plan["coverage_entries"]}
    assert set(entries) == {
        "hospital-room-expense",
        "inpatient-medical-expense",
        "outpatient-surgery-expense",
        "specified-procedure-expense",
        "pre-post-outpatient-expense",
        "hospital-cash-alternative-daily",
        "major-hospital-comfort",
        "annual-total-limit",
    }
    room_daily, inpatient_limit, outpatient_or_procedure, pre_post, annual_total = expected
    assert entries["hospital-room-expense"]["amount"] == room_daily
    assert entries["inpatient-medical-expense"]["amount"] == inpatient_limit
    assert entries["outpatient-surgery-expense"]["amount"] == outpatient_or_procedure
    assert entries["specified-procedure-expense"]["amount"] == outpatient_or_procedure
    assert entries["pre-post-outpatient-expense"]["amount"] == pre_post
    assert entries["hospital-cash-alternative-daily"]["amount"] == room_daily
    assert entries["major-hospital-comfort"]["amount"] == 6_000
    assert entries["annual-total-limit"]["amount"] == annual_total
    assert entries["hospital-cash-alternative-daily"]["aggregation_rule"] == "choose_one"
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

shishizai_source_path = (
    TII_LIFE_008_ROOT
    / "202311RZ1A04A21A11Z10000000"
    / "202311RZ1A04A21A11Z10000000-A.pdf"
)
shishizai_indexed_document = {
    key: value
    for key, value in taiwan_shishizai_inpatient_document.items()
    if key not in {"page_count", "pages_parsed"}
}
shishizai_indexed_document["text"] = normalize_terms_text(
    "\n".join((page.extract_text() or "") for page in PdfReader(shishizai_source_path).pages[:2])
)
shishizai_completed_document = complete_strict_source_document(
    shishizai_indexed_document, shishizai_source_path
)
assert shishizai_completed_document["page_count"] == 9
assert parse_taiwan_shishizai_inpatient_plan_table(
    shishizai_completed_document
) == taiwan_shishizai_inpatient_schedule
assert parse_taiwan_shishizai_inpatient_plan_table(
    tii_life_008_document("202311RZ1A04A21A11Z10000000", "F")
) is None
assert parse_taiwan_shishizai_inpatient_plan_table(
    {**taiwan_shishizai_inpatient_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_shishizai_inpatient_plan_table(
    {
        **taiwan_shishizai_inpatient_document,
        "text": taiwan_shishizai_inpatient_document["text"].replace(
            "350,000", "360,000", 1
        ),
    }
) is None

taiwan_gold_group_inpatient_document = tii_life_008_document(
    "202313MZ1A31B21A11Z10000000"
)
taiwan_gold_group_inpatient_schedule = parse_taiwan_gold_group_inpatient_limit_plan_table(
    taiwan_gold_group_inpatient_document
)
assert taiwan_gold_group_inpatient_schedule is not None
assert (
    parse_plan_table_with_parser(taiwan_gold_group_inpatient_document)[0]
    == "taiwan-life-gold-group-inpatient-limit-plan-v1"
)
assert taiwan_gold_group_inpatient_schedule["selection_type"] == "plan"
assert taiwan_gold_group_inpatient_schedule["selection_label"] == "投保計劃別"
assert taiwan_gold_group_inpatient_schedule["version_characteristics"] == {
    "terms_revision": "114-original",
    "plan_count": 11,
    "same_hospital_readmission_days": 14,
    "post_expiry_readmission_excluded": True,
    "day_hospital_excluded": True,
    "outpatient_surgery_included": True,
    "nhi_paid_excluded": True,
    "non_nhi_payment_rate_percent": 100,
    "hospital_medical_icu_limit_multiplier": 2,
    "hospital_daily_icu_multiplier": 2,
    "hospital_daily_days_limit": 31,
    "icu_daily_days_limit": 31,
    "medical_expense_or_daily_choose_one": True,
    "conversion_right_after_months": 6,
    "experience_dividend_formula": True,
}
assert [plan["label"] for plan in taiwan_gold_group_inpatient_schedule["plan_options"]] == [
    "計劃A",
    "計劃B",
    "計劃C",
    "計劃D",
    "計劃E",
    "計劃F",
    "計劃G",
    "計劃H",
    "計劃I",
    "計劃J",
    "計劃K",
]
taiwan_gold_plan_entries = [
    {entry["id"]: entry for entry in plan["coverage_entries"]}
    for plan in taiwan_gold_group_inpatient_schedule["plan_options"]
]
assert taiwan_gold_plan_entries[0]["inpatient-medical-expense-limit"]["amount"] == 60_000
assert taiwan_gold_plan_entries[0]["inpatient-medical-expense-limit"]["amount_tiers"] == [
    {"label": "一般住院限額", "amount": 60_000},
    {"label": "曾住進加護病房限額", "amount": 120_000},
]
assert taiwan_gold_plan_entries[0]["hospital-daily-compensation"]["amount"] == 600
assert taiwan_gold_plan_entries[0]["hospital-daily-compensation"]["amount_tiers"] == [
    {"label": "一般住院日額", "amount": 600},
    {"label": "加護病房日額", "amount": 1_200},
]
assert taiwan_gold_plan_entries[0]["outpatient-surgery-expense-limit"]["amount"] == 60_000
assert taiwan_gold_plan_entries[5]["inpatient-medical-expense-limit"]["amount"] == 200_000
assert taiwan_gold_plan_entries[5]["hospital-daily-compensation"]["amount"] == 4_800
assert taiwan_gold_plan_entries[6]["inpatient-medical-expense-limit"]["amount"] == 30_000
assert taiwan_gold_plan_entries[6]["hospital-daily-compensation"]["amount"] == 900
assert taiwan_gold_plan_entries[10]["outpatient-surgery-expense-limit"]["amount"] == 100_000
assert all(len(entries) == 3 for entries in taiwan_gold_plan_entries)
taiwan_gold_group_partial = {
    key: value
    for key, value in taiwan_gold_group_inpatient_document.items()
    if key not in {"page_count", "pages_parsed"}
}
taiwan_gold_group_source = (
    TII_LIFE_008_ROOT
    / "202313MZ1A31B21A11Z10000000"
    / "202313MZ1A31B21A11Z10000000-A.pdf"
)
taiwan_gold_group_partial["text"] = normalize_terms_text(
    "\n".join(
        page.extract_text() or ""
        for page in PdfReader(taiwan_gold_group_source).pages[:2]
    )
)
taiwan_gold_group_completed = complete_strict_source_document(
    taiwan_gold_group_partial, taiwan_gold_group_source
)
assert taiwan_gold_group_completed["page_count"] == 7
assert (
    parse_taiwan_gold_group_inpatient_limit_plan_table(taiwan_gold_group_completed)
    == taiwan_gold_group_inpatient_schedule
)
assert parse_taiwan_gold_group_inpatient_limit_plan_table(
    tii_life_008_document("202313MZ1A31B21A11Z10000000", "F")
) is None
assert parse_taiwan_gold_group_inpatient_limit_plan_table(
    {**taiwan_gold_group_inpatient_document, "product_id": "wrong-product-id"}
) is None
assert parse_taiwan_gold_group_inpatient_limit_plan_table(
    {**taiwan_gold_group_inpatient_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_gold_group_inpatient_limit_plan_table(
    {**taiwan_gold_group_inpatient_document, "page_count": 6}
) is None
assert parse_taiwan_gold_group_inpatient_limit_plan_table(
    {
        **taiwan_gold_group_inpatient_document,
        "text": taiwan_gold_group_inpatient_document["text"].replace("6萬元", "9萬元", 1),
    }
) is None

expected_taiwan_fishermen_group_revisions = {
    "202313MZ1A96721A11Z10000000": ("original", False),
    "202313MZ1A96721A11Z10000001": ("112-revised", True),
}
for product_id in TAIWAN_FISHERMEN_GROUP_MEDICAL_PRODUCT_IDS:
    document = tii_life_008_document(product_id)
    expected_revision, expected_notice = expected_taiwan_fishermen_group_revisions[
        product_id
    ]
    assert document["page_count"] == document["pages_parsed"] == 6
    schedule = parse_taiwan_fishermen_group_medical_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-life-fishermen-group-medical-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "計畫別"
    assert [plan["label"] for plan in schedule["plan_options"]] == ["計畫A"]
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["insured_notice_revision"] is expected_notice
    assert characteristics["nhi_uncovered_payment_rate_percent"] == 100
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["post_expiry_readmission_excluded"] is True
    assert characteristics["annual_hospital_daily_days_limit"] == 31
    assert characteristics["same_accident_deductible"] == 3_000

    entries = {
        entry["id"]: entry
        for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    assert set(entries) == {
        "annual-medical-reimbursement-limit",
        "hospital-daily-compensation",
        "same-accident-deductible",
    }
    assert entries["annual-medical-reimbursement-limit"]["amount"] == 320_000
    assert entries["annual-medical-reimbursement-limit"]["amount_role"] == "limit"
    assert entries["annual-medical-reimbursement-limit"]["limit_scope"] == "annual"
    assert entries["hospital-daily-compensation"]["amount"] == 1_500
    assert entries["hospital-daily-compensation"]["calculation_basis"] == "per_day"
    assert entries["same-accident-deductible"]["amount"] == 3_000
    assert entries["same-accident-deductible"]["amount_role"] == "reference"
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_008_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 6
    assert parse_taiwan_fishermen_group_medical_plan_table(completed_document) == schedule
    assert parse_taiwan_fishermen_group_medical_plan_table(tii_life_008_document(product_id, "F")) is None

taiwan_fishermen_base = tii_life_008_document(
    TAIWAN_FISHERMEN_GROUP_MEDICAL_PRODUCT_IDS[0]
)
assert parse_taiwan_fishermen_group_medical_plan_table(
    {**taiwan_fishermen_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_fishermen_group_medical_plan_table(
    {**taiwan_fishermen_base, "document_type": "product_summary"}
) is None
assert parse_taiwan_fishermen_group_medical_plan_table(
    {
        **taiwan_fishermen_base,
        "text": taiwan_fishermen_base["text"].replace("32萬元", "33萬元", 1),
    }
) is None

TAIWAN_GROUP_LONG_TERM_CARE_SERVICE_PRODUCT_IDS = (
    "202363MZ1A84321A12Z10000000",
    "202363MZ1A84321A12Z10000001",
)
expected_taiwan_group_ltc_revisions = {
    "202363MZ1A84321A12Z10000000": ("original", False),
    "202363MZ1A84321A12Z10000001": ("112-revised", True),
}
for product_id in TAIWAN_GROUP_LONG_TERM_CARE_SERVICE_PRODUCT_IDS:
    document = tii_life_008_document(product_id)
    expected_revision, expected_privacy_revision = expected_taiwan_group_ltc_revisions[
        product_id
    ]
    assert document["page_count"] == document["pages_parsed"] == 10
    schedule = parse_taiwan_group_long_term_care_service_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-group-long-term-care-service-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["long_term_care_plan_months"] == 24
    assert characteristics["lump_sum_face_amount_multiplier"] == 6
    assert characteristics["monthly_service_face_amount_multiplier"] == 1
    assert characteristics["unclaimed_balance_interest_rate_percent"] == 0.25
    assert characteristics["service_area_limited"] is True
    assert characteristics["adl_impairment_min_items"] == 3
    assert characteristics["adl_assessment_months"] == 3
    assert characteristics["cdr_min_score"] == 2
    assert characteristics["service_fee_revision_notice_months"] == 3
    assert characteristics["service_fee_revision_limit_per_year"] == 1
    assert characteristics["privacy_revision"] is expected_privacy_revision

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "long-term-care-lump-sum",
        "monthly-care-service-limit",
        "unclaimed-care-balance",
        "basic-care-service-hourly-fee",
        "health-promotion-service-hourly-fee",
        "dementia-care-service-hourly-fee",
        "cancer-care-service-hourly-fee",
        "complex-care-hourly-surcharge",
        "holiday-service-fee-multiplier",
        "service-failure-compensation-rate",
    }
    assert entries["long-term-care-lump-sum"]["multiplier"] == 6
    assert entries["monthly-care-service-limit"]["rate_percent"] == 100
    assert entries["unclaimed-care-balance"]["multiplier"] == 24
    assert entries["basic-care-service-hourly-fee"]["amount"] == 400
    assert entries["health-promotion-service-hourly-fee"]["amount"] == 500
    assert entries["dementia-care-service-hourly-fee"]["amount"] == 550
    assert entries["cancer-care-service-hourly-fee"]["amount"] == 500
    assert entries["complex-care-hourly-surcharge"]["amount"] == 100
    assert entries["holiday-service-fee-multiplier"]["multiplier"] == 2
    assert entries["service-failure-compensation-rate"]["rate_percent"] == 110
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_008_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 10
    assert parse_taiwan_group_long_term_care_service_face_amount(
        completed_document
    ) == schedule
    assert parse_taiwan_group_long_term_care_service_face_amount(
        tii_life_008_document(product_id, "F")
    ) is None

taiwan_group_ltc_base = tii_life_008_document(
    TAIWAN_GROUP_LONG_TERM_CARE_SERVICE_PRODUCT_IDS[0]
)
assert parse_taiwan_group_long_term_care_service_face_amount(
    {**taiwan_group_ltc_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_group_long_term_care_service_face_amount(
    {**taiwan_group_ltc_base, "document_type": "product_summary"}
) is None
assert parse_taiwan_group_long_term_care_service_face_amount(
    {
        **taiwan_group_ltc_base,
        "text": taiwan_group_ltc_base["text"].replace("每小時 400元", "每小時 450元", 1),
    }
) is None

TAIWAN_YIQIJIANZHI_SPECIFIC_DISEASE_PRODUCT_IDS = (
    "202391MZ1A41B22A11E10000000",
    "202391MZ1A41B22A11E10000001",
)
expected_taiwan_yiqijianzhi_revisions = {
    "202391MZ1A41B22A11E10000000": "original",
    "202391MZ1A41B22A11E10000001": "first-revision",
}
for product_id in TAIWAN_YIQIJIANZHI_SPECIFIC_DISEASE_PRODUCT_IDS:
    document = tii_life_008_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 7
    schedule = parse_taiwan_yiqijianzhi_specific_disease_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-life-yiqijianzhi-specific-disease-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_taiwan_yiqijianzhi_revisions[product_id]
    assert characteristics["specific_disease_waiting_days"] == 30
    assert characteristics["accident_exempt_waiting_period"] is True
    assert characteristics["maximum_coverage_age"] == 89
    assert characteristics["no_claim_premium_refund_rate_percent"] == 102
    assert characteristics["health_promotion_discount_rate_percent"] == 2
    assert characteristics["installment_min_annual_amount"] == 36_000
    assert (
        characteristics["source_terms_sha256"]
        == "8167e1d1d5a12114bf2cd7ea401b3c3b60eb311269bd0d0c8df7642af221d6cb"
    )

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "specific-disease-face-amount",
        "specific-disease-no-claim-premium-addition",
        "no-claim-premium-refund",
        "health-promotion-renewal-premium-discount",
        "installment-minimum-annual-payment",
    }
    assert entries["specific-disease-face-amount"]["rate_percent"] == 100
    assert entries["specific-disease-face-amount"]["aggregation_rule"] == "choose_one"
    assert entries["specific-disease-no-claim-premium-addition"]["rate_percent"] == 102
    assert entries["specific-disease-no-claim-premium-addition"]["unit_key"] == "annual_premium_total"
    assert entries["no-claim-premium-refund"]["rate_percent"] == 102
    assert entries["no-claim-premium-refund"]["unit_key"] == "annual_premium_total"
    assert entries["health-promotion-renewal-premium-discount"]["rate_percent"] == 2
    assert entries["health-promotion-renewal-premium-discount"]["amount_role"] == "reference"
    assert entries["installment-minimum-annual-payment"]["amount"] == 36_000
    for entry in entries.values():
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = TII_LIFE_008_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:2])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 7
    assert parse_taiwan_yiqijianzhi_specific_disease_face_amount(completed_document) == schedule
    assert parse_taiwan_yiqijianzhi_specific_disease_face_amount(
        tii_life_008_document(product_id, "F")
    ) is None

taiwan_yiqijianzhi_base = tii_life_008_document(
    TAIWAN_YIQIJIANZHI_SPECIFIC_DISEASE_PRODUCT_IDS[0]
)
assert parse_taiwan_yiqijianzhi_specific_disease_face_amount(
    {**taiwan_yiqijianzhi_base, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_taiwan_yiqijianzhi_specific_disease_face_amount(
    {**taiwan_yiqijianzhi_base, "document_type": "product_summary"}
) is None
assert parse_taiwan_yiqijianzhi_specific_disease_face_amount(
    {
        **taiwan_yiqijianzhi_base,
        "text": taiwan_yiqijianzhi_base["text"].replace("台壽字第 1152320021 號函備查", "台壽字第 1152320022 號函備查", 1),
    }
) is None

CHAOYANG_XINGNONG_GROUP_INPATIENT_PRODUCT_ID = "212317R11A00800"
CHAOYANG_XINGNONG_GROUP_INPATIENT_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-068"
)


def chaoyang_xingnong_group_inpatient_document() -> dict:
    product_id = CHAOYANG_XINGNONG_GROUP_INPATIENT_PRODUCT_ID
    pdf_path = (
        CHAOYANG_XINGNONG_GROUP_INPATIENT_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


chaoyang_xingnong_document = chaoyang_xingnong_group_inpatient_document()
chaoyang_xingnong_schedule = parse_chaoyang_xingnong_group_inpatient_unit_table(
    chaoyang_xingnong_document
)
assert chaoyang_xingnong_schedule is not None
integrated_chaoyang_xingnong = parse_plan_table_with_parser(chaoyang_xingnong_document)
assert integrated_chaoyang_xingnong is not None
assert integrated_chaoyang_xingnong[0] == "chaoyang-xingnong-group-inpatient-unit-v1"
assert integrated_chaoyang_xingnong[1] == chaoyang_xingnong_schedule
assert chaoyang_xingnong_schedule["selection_type"] == "unit"
assert chaoyang_xingnong_schedule["selection_label"] == "投保單位數"
assert chaoyang_xingnong_schedule["version_characteristics"] == {
    "terms_revision": "87-08-15-revision",
    "filing_date": "83.06.03",
    "filing_number": "台財保第831481668號",
    "revision_date": "87.08.15",
    "revision_number": "台財保第872441034號",
    "disease_waiting_days": 30,
    "room_board_days_limit": 120,
    "icu_days_limit": 10,
    "same_accident_readmission_days": 90,
    "social_insurance_unclaimed_payment_rate_percent": 70,
    "surgery_table_min_percent": 2.5,
    "surgery_table_max_percent": 100,
    "experience_dividend": True,
}
chaoyang_xingnong_entries = {
    entry["id"]: entry for entry in chaoyang_xingnong_schedule["coverage_entries"]
}
assert set(chaoyang_xingnong_entries) == {
    "room-board-daily",
    "icu-daily",
    "inpatient-medical-expense",
    "surgery-expense-base",
    "home-recovery-daily",
}
assert chaoyang_xingnong_entries["room-board-daily"]["amount"] == 100
assert chaoyang_xingnong_entries["room-board-daily"]["limit_scope"] == "per_day"
assert chaoyang_xingnong_entries["icu-daily"]["amount"] == 300
assert chaoyang_xingnong_entries["inpatient-medical-expense"]["amount"] == 1_000
assert chaoyang_xingnong_entries["surgery-expense-base"]["amount"] == 1_000
assert chaoyang_xingnong_entries["surgery-expense-base"]["rate_min_percent"] == 2.5
assert chaoyang_xingnong_entries["surgery-expense-base"]["rate_max_percent"] == 100
assert chaoyang_xingnong_entries["home-recovery-daily"]["amount"] == 50
assert chaoyang_xingnong_entries["home-recovery-daily"]["multiplier"] == 0.5
assert all(
    "70%" in " ".join(entry.get("conditions", []))
    for entry in chaoyang_xingnong_entries.values()
)

chaoyang_xingnong_source_path = (
    CHAOYANG_XINGNONG_GROUP_INPATIENT_ROOT
    / CHAOYANG_XINGNONG_GROUP_INPATIENT_PRODUCT_ID
    / f"{CHAOYANG_XINGNONG_GROUP_INPATIENT_PRODUCT_ID}-A.pdf"
)
chaoyang_xingnong_indexed_document = {
    key: value
    for key, value in chaoyang_xingnong_document.items()
    if key not in {"page_count", "pages_parsed"}
}
chaoyang_xingnong_indexed_document["text"] = normalize_terms_text(
    "\n".join(
        page.extract_text() or ""
        for page in PdfReader(chaoyang_xingnong_source_path).pages[:2]
    )
)
chaoyang_xingnong_completed_document = complete_strict_source_document(
    chaoyang_xingnong_indexed_document,
    chaoyang_xingnong_source_path,
)
assert chaoyang_xingnong_completed_document["page_count"] == 6
assert (
    parse_chaoyang_xingnong_group_inpatient_unit_table(
        chaoyang_xingnong_completed_document
    )
    == chaoyang_xingnong_schedule
)
assert parse_chaoyang_xingnong_group_inpatient_unit_table(
    {**chaoyang_xingnong_document, "file_name": "wrong-file-A.pdf"}
) is None
assert parse_chaoyang_xingnong_group_inpatient_unit_table(
    {**chaoyang_xingnong_document, "document_type": "product_summary"}
) is None
assert parse_chaoyang_xingnong_group_inpatient_unit_table(
    {
        **chaoyang_xingnong_document,
        "text": chaoyang_xingnong_document["text"].replace("每日病房及膳食費用保險金 100 元", "每日病房及膳食費用保險金 200 元", 1),
    }
) is None

truncated_fixture = json.loads(
    (
        Path(__file__).resolve().parents[1]
        / "work"
        / "tii-document-text"
        / "tii-life-050-text.json"
    ).read_text(encoding="utf-8")
)
truncated_documents = (
    truncated_fixture.get("documents", [])
    if isinstance(truncated_fixture, dict)
    else truncated_fixture
)
for document in truncated_documents:
    if document.get("product_id") in TII_LIFE_050_PRODUCT_IDS:
        assert_tii_life_050_rejected(document)


PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-013"
)
CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-025"
)
PRUDENTIAL_CHINA_LIFE_ACCIDENT_ACCOUNT_PRODUCTS = {
    "203211R31A00102": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 16, False),
    "203211R31A00104": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211R31A00105": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 16, False),
    "203211R31A00106": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211R31A00107": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211R31A00108": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211RZ1A00321A11Z10000009": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 18, False),
    "203211RZ1A00321A11Z10000010": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 18, False),
    "203211RZ1A00321A11Z10000011": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 18, False),
    "203211RZ1A00321A11Z10000012": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 18, False),
    "203211RZ1A00321A11Z10000013": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 22, False),
    "203211RZ1A00321A11Z10000014": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211RZ1A00321A11Z10000015": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211RZ1A00321A11Z10000016": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "203211RZ1A00321A11Z10000017": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, False),
    "205211R11A54600": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 22, True),
    "205211R11A54601": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 22, True),
    "205211R11A54602": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 22, True),
    "205211R11A54603": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 23, True),
    "205211RZ1A00121A11Z10000005": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000006": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 23, True),
    "205211RZ1A00121A11Z10000007": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000008": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000009": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000010": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000011": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 24, True),
    "205211RZ1A00121A11Z10000012": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 20, False),
}


def accident_account_document(product_id: str) -> dict:
    root, _, _ = PRUDENTIAL_CHINA_LIFE_ACCIDENT_ACCOUNT_PRODUCTS[product_id]
    pdf_path = root / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


ACCIDENT_ACCOUNT_BASE_IDS = {
    "accidental-death-or-funeral",
    "accidental-disability",
    "injury-medical-reimbursement-limit",
    "accident-pre-post-outpatient",
    "accident-hospital-daily",
    "fracture-without-hospitalization",
    "accident-inpatient-surgery",
    "accident-icu-daily",
}
for product_id, (root, expected_pages, expected_major_burn) in (
    PRUDENTIAL_CHINA_LIFE_ACCIDENT_ACCOUNT_PRODUCTS.items()
):
    document = accident_account_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_prudential_china_life_accident_account_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-china-life-accident-account-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["non_nhi_payment_rate_percent"] == 70
    assert characteristics["hospital_daily_days_limit"] == 120
    assert characteristics["surgery_base_daily_multiplier"] == 20
    assert characteristics["surgery_per_hospitalization_daily_multiplier_limit"] == 60
    assert characteristics["major_burn_rider_included"] is expected_major_burn
    assert characteristics["surgery_table_max_percent"] == 300
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    expected_ids = set(ACCIDENT_ACCOUNT_BASE_IDS)
    if expected_major_burn:
        expected_ids.add("major-burn")
    assert set(entries) == expected_ids
    assert len(entries) == (9 if expected_major_burn else 8)
    assert entries["accidental-death-or-funeral"]["rate_percent"] == 100
    assert entries["accidental-disability"]["rate_min_percent"] >= 5
    assert entries["accidental-disability"]["rate_max_percent"] == 100
    assert entries["injury-medical-reimbursement-limit"].get("amount") is None
    assert (
        entries["injury-medical-reimbursement-limit"]["calculation_basis"]
        == "reimbursement_with_cap"
    )
    assert entries["accident-inpatient-surgery"]["multiplier"] == 20
    assert entries["fracture-without-hospitalization"]["multiplier"] == 0.5
    if expected_major_burn:
        assert entries["major-burn"]["rate_percent"] == 35

    source_path = root / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_prudential_china_life_accident_account_face_amount(completed_document)
        == schedule
    )
    assert (
        parse_prudential_china_life_accident_account_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_prudential_china_life_accident_account_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_prudential_china_life_accident_account_face_amount(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


ONE_THREE_FIVE_ACCIDENT_PRODUCTS = {
    "203211M11A00201": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 22, 75, "殘廢"),
    "203211M11A00202": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 75, "殘廢"),
    "203211M11A00203": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 11, 75, "殘廢"),
    "203211M11A00204": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 16, 75, "殘廢"),
    "203211M11A00205": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 16, 75, "殘廢"),
    "203211M11A00206": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 15, 75, "殘廢"),
    "203211MZ1A00221A11Z10000007": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 12, 79, "殘廢"),
    "203211MZ1A00221A11Z10000008": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 79, "殘廢"),
    "203211MZ1A00221A11Z10000009": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 79, "失能"),
    "203211MZ1A00221A11Z10000010": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 80, "失能"),
    "203211MZ1A00221A11Z10000011": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 80, "失能"),
    "203211MZ1A00221A11Z10000012": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 17, 80, "失能"),
    "205211M11A00200": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 14, 75, "殘廢"),
    "205211M11A00201": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 14, 75, "殘廢"),
    "205211M11A00202": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 18, 75, "殘廢"),
    "205211MZ1A00421A11Z10000003": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 18, 79, "殘廢"),
    "205211MZ1A00421A11Z10000004": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 18, 79, "殘廢"),
    "205211MZ1A00421A11Z10000005": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 18, 79, "失能"),
    "205211MZ1A00421A11Z10000006": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 18, 80, "失能"),
    "205211MZ1A00421A11Z10000007": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 14, 80, "失能"),
    "205211MZ1A00421A11Z10000008": (CHINA_LIFE_ACCIDENT_ACCOUNT_ROOT, 14, 80, "失能"),
}


def one_three_five_accident_document(product_id: str) -> dict:
    root, _, _, _ = ONE_THREE_FIVE_ACCIDENT_PRODUCTS[product_id]
    pdf_path = root / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (root, expected_pages, expected_disability_items, expected_term) in (
    ONE_THREE_FIVE_ACCIDENT_PRODUCTS.items()
):
    document = one_three_five_accident_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_prudential_china_life_one_three_five_accident_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-china-life-one-three-five-accident-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["disability_term"] == expected_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["domestic_general_multiplier"] == 1
    assert characteristics["overseas_general_multiplier"] == 3
    assert characteristics["flight_multiplier"] == 5
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "domestic-general-accidental-death-or-funeral",
        "overseas-general-accidental-death-or-funeral",
        "flight-accidental-death-or-funeral",
        "domestic-general-accidental-disability",
        "overseas-general-accidental-disability",
        "flight-accidental-disability",
    }
    assert entries["domestic-general-accidental-death-or-funeral"]["rate_percent"] == 100
    assert entries["overseas-general-accidental-death-or-funeral"]["rate_percent"] == 300
    assert entries["flight-accidental-death-or-funeral"]["rate_percent"] == 500
    assert entries["domestic-general-accidental-disability"]["multiplier"] == 1
    assert entries["overseas-general-accidental-disability"]["multiplier"] == 3
    assert entries["flight-accidental-disability"]["multiplier"] == 5
    for entry in entries.values():
        assert entry["basis"] == "face_amount"
        assert entry["calculation_basis"] == "percentage_of_base"
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = root / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_prudential_china_life_one_three_five_accident_face_amount(
            completed_document
        )
        == schedule
    )
    assert (
        parse_prudential_china_life_one_three_five_accident_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_prudential_china_life_one_three_five_accident_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_prudential_china_life_one_three_five_accident_face_amount(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


PRUDENTIAL_GROUP_SPECIFIC_ACCIDENT_PRODUCTS = {
    "203213AZ1A00421A11Z10000000": "109-original",
    "203213AZ1A00421A11Z10000001": "110-first-revision",
    "203213AZ1A00421A11Z10000002": "110-second-revision",
}


def prudential_group_specific_accident_document(product_id: str) -> dict:
    pdf_path = PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, expected_revision in PRUDENTIAL_GROUP_SPECIFIC_ACCIDENT_PRODUCTS.items():
    document = prudential_group_specific_accident_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 11
    schedule = parse_prudential_group_specific_accident_rider_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-group-specific-accident-rider-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["disability_term"] == "失能"
    assert characteristics["disability_schedule_item_count"] == 80
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["general_specific_multiplier"] == 1
    assert characteristics["flight_multiplier"] == 2

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "general-specific-accidental-death-or-funeral",
        "flight-accidental-death-or-funeral",
        "general-specific-accidental-disability",
        "flight-accidental-disability",
    }
    assert (
        entries["general-specific-accidental-death-or-funeral"]["rate_percent"]
        == 100
    )
    assert entries["flight-accidental-death-or-funeral"]["rate_percent"] == 200
    assert entries["general-specific-accidental-disability"]["multiplier"] == 1
    assert entries["flight-accidental-disability"]["multiplier"] == 2
    assert (
        entries["general-specific-accidental-disability"]["rate_min_percent"]
        == 5
    )
    assert (
        entries["flight-accidental-disability"]["rate_max_percent"]
        == 100
    )
    for entry in entries.values():
        assert entry["basis"] == "face_amount"
        assert entry["calculation_basis"] == "percentage_of_base"
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT / product_id / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 11
    assert (
        parse_prudential_group_specific_accident_rider_face_amount(
            completed_document
        )
        == schedule
    )
    assert (
        parse_prudential_group_specific_accident_rider_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_prudential_group_specific_accident_rider_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_prudential_group_specific_accident_rider_face_amount(
            {**document, "page_count": 10}
        )
        is None
    )


FIRE_MASS_TRANSIT_ACCIDENT_PRODUCTS = {
    "203211R11A00200": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 12, 75, "殘廢"),
    "203211R11A00201": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 12, 75, "殘廢"),
    "203211R11A00202": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 12, 75, "殘廢"),
    "203211R11A00203": (PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT, 12, 75, "殘廢"),
    "203211RZ1A00221A11Z10000004": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        79,
        "殘廢",
    ),
    "203211RZ1A00221A11Z10000005": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        79,
        "殘廢",
    ),
    "203211RZ1A00221A11Z10000006": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        79,
        "失能",
    ),
    "203211RZ1A00221A11Z10000007": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        80,
        "失能",
    ),
    "203211RZ1A00221A11Z10000008": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        80,
        "失能",
    ),
    "203211RZ1A00221A11Z10000009": (
        PRUDENTIAL_ACCIDENT_ACCOUNT_ROOT,
        13,
        80,
        "失能",
    ),
}


def fire_mass_transit_accident_document(product_id: str) -> dict:
    root, _, _, _ = FIRE_MASS_TRANSIT_ACCIDENT_PRODUCTS[product_id]
    pdf_path = root / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    root,
    expected_pages,
    expected_disability_items,
    expected_disability_term,
) in (
    FIRE_MASS_TRANSIT_ACCIDENT_PRODUCTS.items()
):
    document = fire_mass_transit_accident_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_prudential_fire_mass_transit_accident_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "prudential-fire-mass-transit-accident-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["fire_accident_multiplier"] == 1
    assert characteristics["land_water_mass_transit_multiplier"] == 4
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "fire-accidental-death-or-funeral",
        "land-water-mass-transit-accidental-death-or-funeral",
        "fire-accidental-disability",
        "land-water-mass-transit-accidental-disability",
    }
    assert entries["fire-accidental-death-or-funeral"]["rate_percent"] == 100
    assert (
        entries["land-water-mass-transit-accidental-death-or-funeral"][
            "rate_percent"
        ]
        == 400
    )
    assert entries["fire-accidental-disability"]["multiplier"] == 1
    assert entries["land-water-mass-transit-accidental-disability"]["multiplier"] == 4
    assert expected_disability_term in entries["fire-accidental-disability"]["name"]
    assert (
        expected_disability_term
        in entries["land-water-mass-transit-accidental-disability"]["name"]
    )
    for entry in entries.values():
        assert entry["basis"] == "face_amount"
        assert entry["calculation_basis"] == "percentage_of_base"
        assert entry["source"] == "terms"
        assert entry.get("conditions")

    source_path = root / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join((page.extract_text() or "") for page in PdfReader(source_path).pages[:3])
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_prudential_fire_mass_transit_accident_face_amount(completed_document)
        == schedule
    )
    assert (
        parse_prudential_fire_mass_transit_accident_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_prudential_fire_mass_transit_accident_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_prudential_fire_mass_transit_accident_face_amount(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


ANXIN_456_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
ANXIN_456_PRODUCTS = {
    "209291M12G00800": (19, "102-original", 30, "殘廢", 75),
    "209291M12G00801": (19, "103-first-revision", 30, "殘廢", 75),
    "209291MZ2G00221A11Z10000002": (20, "104-second-revision", 30, "殘廢", 75),
    "209291MZ2G00221A11Z10000003": (20, "105-third-revision", 30, "殘廢", 75),
    "209291MZ2G00221A11Z10000004": (20, "107-fourth-revision", 0, "殘廢", 75),
    "209291MZ2G00221A11Z10000005": (20, "107-fifth-revision", 0, "失能", 79),
    "209291MZ2G00221A11Z10000006": (20, "108-sixth-revision", 0, "失能", 79),
    "209291MZ2G00221A11Z10000007": (21, "109-seventh-revision", 0, "失能", 80),
    "209291MZ2G00221A11Z10000008": (20, "109-eighth-revision", 0, "失能", 80),
    "209291MZ2G00221A11Z10000009": (20, "111-ninth-revision", 0, "失能", 80),
}


def anxin_456_document(product_id: str) -> dict:
    pdf_path = ANXIN_456_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_pages,
    expected_revision,
    expected_cancer_waiting_days,
    expected_disability_term,
    expected_disability_items,
) in ANXIN_456_PRODUCTS.items():
    document = anxin_456_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_fubon_anxin_456_accident_health_fixed_schedule(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-anxin-456-accident-health-fixed-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fixed_schedule"] is True
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["cancer_waiting_days"] == expected_cancer_waiting_days
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["accident_hospital_days_limit"] == 90
    assert characteristics["accident_icu_days_limit"] == 30
    assert characteristics["burn_center_days_limit"] == 30
    assert characteristics["fracture_daily_rate_percent"] == 50
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_lifetime_limit_times"] == 1
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == 13
    assert entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert entries["total-disability"]["amount"] == 1_000_000
    assert entries["total-disability"]["name"] == f"完全{expected_disability_term}保險金"
    assert entries["cancer-death"]["amount"] == 300_000
    assert entries["major-burn"]["amount"] == 500_000
    assert entries["accidental-death-or-funeral"]["amount"] == 2_000_000
    assert entries["accidental-disability"]["amount"] == 2_000_000
    assert entries["accidental-disability"]["name"] == f"意外{expected_disability_term}保險金"
    assert entries["accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 2_000_000,
    }
    assert entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 100_000,
    }
    assert entries["cancer-surgery"]["amount"] == 30_000
    assert entries["cancer-hospital-daily"]["amount"] == 1_000
    assert entries["cancer-radiation-daily"]["amount"] == 1_000
    assert entries["accident-hospital-daily"]["amount"] == 1_000
    assert entries["fracture-unhospitalized-medical"]["amount"] == 500
    assert entries["accident-icu-hospital-daily"]["amount"] == 1_000
    assert entries["burn-center-medical-daily"]["amount"] == 2_000
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

    source_path = ANXIN_456_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_anxin_456_accident_health_fixed_schedule(completed_document)
        == schedule
    )
    assert (
        parse_fubon_anxin_456_accident_health_fixed_schedule(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_anxin_456_accident_health_fixed_schedule(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_anxin_456_accident_health_fixed_schedule(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


NEW_SHOUHU_JINNANG_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
NEW_SHOUHU_JINNANG_PRODUCTS = {
    "209291M12G00200": (21, "102-original", 30, 75),
    "209291M19G00101": (21, "103-first-revision", 30, 75),
    "209291MZ2G00121A11Z10000002": (22, "104-second-revision", 30, 79),
    "209291MZ2G00121A11Z10000003": (22, "105-third-revision", 30, 79),
    "209291MZ2G00121A11Z10000004": (22, "107-fourth-revision", 0, 79),
}


def new_shouhu_jinnang_document(product_id: str) -> dict:
    pdf_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_cancer_waiting_days,
        expected_disability_items,
    ),
) in NEW_SHOUHU_JINNANG_PRODUCTS.items():
    document = new_shouhu_jinnang_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_fubon_new_shouhu_jinnang_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-shouhu-jinnang-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 10
    assert characteristics["plan_1_2_maximum_renewal_age"] == 70
    assert characteristics["plan_3_4_maximum_renewal_age"] == 20
    assert characteristics["plan_5_10_maximum_renewal_age"] == 65
    assert characteristics["cancer_waiting_days"] == expected_cancer_waiting_days
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["accident_hospital_days_limit"] == 90
    assert characteristics["accident_outpatient_surgery_limit_times"] == 1
    assert characteristics["accident_reimbursement_non_nhi_rate_percent"] == 65
    assert characteristics["fracture_daily_rate_percent"] == 50
    assert characteristics["disability_term"] == "殘廢"
    assert (
        characteristics["disability_schedule_item_count"]
        == expected_disability_items
    )
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert [plan["label"] for plan in schedule["plan_options"]] == [
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
    ]
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert len(plan_1_entries) == 3
    assert plan_1_entries["general-accidental-death"]["amount"] == 1_000_000
    assert plan_1_entries["general-accidental-disability"]["amount"] == 1_000_000
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 1_000_000,
    }
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert plan_1_entries["accident-medical-reimbursement"]["amount"] == 20_000
    assert plan_1_entries["accident-medical-reimbursement"]["amount_role"] == "limit"
    assert (
        plan_1_entries["accident-medical-reimbursement"]["calculation_basis"]
        == "reimbursement_with_cap"
    )

    plan_7_entries = {
        entry["id"]: entry for entry in plans["plan-7"]["coverage_entries"]
    }
    assert len(plan_7_entries) == 25
    assert plan_7_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_7_entries["total-disability"]["amount"] == 1_000_000
    assert plan_7_entries["general-accidental-death"]["amount"] == 3_000_000
    assert (
        plan_7_entries["mass-transit-accidental-death-additional"]["amount"]
        == 5_000_000
    )
    assert (
        plan_7_entries["land-transit-accidental-death-additional"]["amount"]
        == 3_000_000
    )
    assert (
        plan_7_entries[
            "public-building-fire-first-level-disability-additional"
        ]["amount"]
        == 3_000_000
    )
    assert (
        plan_7_entries["mass-transit-accidental-disability-additional"][
            "amount_tiers"
        ][0]["amount"]
        == 5_000_000
    )
    assert plan_7_entries["accident-hospital-daily"]["amount"] == 2_000
    assert plan_7_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_7_entries["accident-medical-reimbursement"]["amount"] == 30_000
    assert plan_7_entries["accident-outpatient-surgery"]["amount"] == 1_000
    assert plan_7_entries["general-hospital-daily"]["amount"] == 2_000
    assert plan_7_entries["post-discharge-convalescence-daily"]["amount"] == 1_500
    assert plan_7_entries["icu-hospital-daily"]["amount"] == 4_000
    assert plan_7_entries["burn-center-hospital-daily"]["amount"] == 6_000
    assert plan_7_entries["cancer-hospital-daily"]["amount"] == 2_000
    assert (
        plan_7_entries["cancer-post-discharge-convalescence-daily"]["amount"]
        == 2_000
    )
    assert plan_7_entries["cancer-surgery"]["amount"] == 20_000
    assert plan_7_entries["cancer-radiation-daily"]["amount"] == 1_000
    assert plan_7_entries["cancer-chemotherapy-daily"]["amount"] == 1_000
    assert all(entry["source"] == "terms" for entry in plan_7_entries.values())
    assert all(entry.get("conditions") for entry in plan_7_entries.values())

    plan_8_entries = {
        entry["id"]: entry for entry in plans["plan-8"]["coverage_entries"]
    }
    assert plan_8_entries["burn-center-hospital-daily"]["amount"] == 4_500
    assert plan_8_entries["post-discharge-convalescence-daily"]["amount"] == 1_000
    assert plan_8_entries["cancer-hospital-daily"]["amount"] == 1_500

    plan_10_entries = {
        entry["id"]: entry for entry in plans["plan-10"]["coverage_entries"]
    }
    assert len(plan_10_entries) == 17
    assert "mass-transit-accidental-death-additional" not in plan_10_entries
    assert "land-transit-first-level-disability-additional" not in plan_10_entries
    assert plan_10_entries["general-accidental-death"]["amount"] == 500_000
    assert plan_10_entries["general-accidental-disability"]["amount"] == 500_000
    assert plan_10_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_10_entries["cancer-post-discharge-convalescence-daily"]["amount"] == 500

    source_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_new_shouhu_jinnang_accident_health_plan_table(
            completed_document
        )
        == schedule
    )
    assert (
        parse_fubon_new_shouhu_jinnang_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "意外傷害醫療保險金 2 萬 4 萬 3 萬 6 萬 3 萬 3 萬",
                    "意外傷害醫療保險金 2 萬 4 萬 3 萬 6 萬 3 萬 4 萬",
                    1,
                ),
            }
        )
        is None
    )


NEW_SHOUHU_JINNANG_LATE_PRODUCTS = {
    "209291MZ2G00121A11Z10000005": (
        22,
        "107-fifth-revision",
        "FBH1070914",
        79,
    ),
    "209291MZ2G00121A11Z10000007": (
        22,
        "109-seventh-revision",
        "FBH1090101",
        80,
    ),
    "209291MZ2G00121A11Z10000008": (
        22,
        "109-eighth-revision",
        "FBH1090901",
        80,
    ),
    "209291MZ2G00121A11Z10000009": (
        22,
        "110-ninth-revision",
        "FBH1101201",
        80,
    ),
    "209291MZ2G00121A11Z10000010": (
        22,
        "111-tenth-revision",
        "FBH1111202",
        80,
    ),
}


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_fubon_code,
        expected_disability_items,
    ),
) in NEW_SHOUHU_JINNANG_LATE_PRODUCTS.items():
    document = new_shouhu_jinnang_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    assert "日間留院" in document["text"]
    assert "完全失能保險金" in document["text"]
    assert parse_fubon_new_shouhu_jinnang_accident_health_plan_table(document) is None
    schedule = parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-shouhu-jinnang-late-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 4
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["cancer_waiting_days"] == 0
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["accident_hospital_days_limit"] == 90
    assert characteristics["accident_outpatient_surgery_limit_times"] == 1
    assert characteristics["accident_reimbursement_non_nhi_rate_percent"] == 65
    assert characteristics["fracture_daily_rate_percent"] == 50
    assert characteristics["disability_term"] == "失能"
    assert characteristics["day_hospital_explicit"] is True
    assert (
        characteristics["disability_schedule_item_count"]
        == expected_disability_items
    )
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫七",
        "計畫八",
        "計畫九",
        "計畫十",
    ]
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert set(plans) == {"plan-7", "plan-8", "plan-9", "plan-10"}

    plan_7_entries = {
        entry["id"]: entry for entry in plans["plan-7"]["coverage_entries"]
    }
    assert len(plan_7_entries) == 25
    assert plan_7_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_7_entries["total-disability"]["amount"] == 1_000_000
    assert plan_7_entries["total-disability"]["name"] == "完全失能保險金"
    assert plan_7_entries["general-accidental-death"]["amount"] == 3_000_000
    assert (
        plan_7_entries["mass-transit-accidental-death-additional"]["amount"]
        == 5_000_000
    )
    assert (
        plan_7_entries["land-transit-accidental-death-additional"]["amount"]
        == 3_000_000
    )
    assert (
        plan_7_entries["general-accidental-disability"]["amount_tiers"][0][
            "amount"
        ]
        == 3_000_000
    )
    assert (
        plan_7_entries["mass-transit-accidental-disability-additional"][
            "amount_tiers"
        ][0]["amount"]
        == 5_000_000
    )
    assert (
        plan_7_entries["public-building-fire-first-level-disability-additional"][
            "amount"
        ]
        == 3_000_000
    )
    assert plan_7_entries["accident-hospital-daily"]["amount"] == 2_000
    assert plan_7_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_7_entries["accident-medical-reimbursement"]["amount"] == 30_000
    assert plan_7_entries["accident-outpatient-surgery"]["amount"] == 1_000
    assert plan_7_entries["general-hospital-daily"]["amount"] == 2_000
    assert plan_7_entries["post-discharge-convalescence-daily"]["amount"] == 1_500
    assert plan_7_entries["icu-hospital-daily"]["amount"] == 4_000
    assert plan_7_entries["burn-center-hospital-daily"]["amount"] == 6_000
    assert plan_7_entries["cancer-hospital-daily"]["amount"] == 2_000
    assert (
        plan_7_entries["cancer-post-discharge-convalescence-daily"]["amount"]
        == 2_000
    )
    assert plan_7_entries["cancer-surgery"]["amount"] == 20_000
    assert plan_7_entries["cancer-radiation-daily"]["amount"] == 1_000
    assert plan_7_entries["cancer-chemotherapy-daily"]["amount"] == 1_000
    assert "失能" in json.dumps(plan_7_entries, ensure_ascii=False)
    assert "殘廢" not in json.dumps(plan_7_entries, ensure_ascii=False)
    assert all(entry["source"] == "terms" for entry in plan_7_entries.values())
    assert all(entry.get("conditions") for entry in plan_7_entries.values())

    plan_8_entries = {
        entry["id"]: entry for entry in plans["plan-8"]["coverage_entries"]
    }
    assert plan_8_entries["burn-center-hospital-daily"]["amount"] == 4_500
    assert plan_8_entries["general-hospital-daily"]["amount"] == 1_500
    assert plan_8_entries["cancer-hospital-daily"]["amount"] == 1_500

    plan_10_entries = {
        entry["id"]: entry for entry in plans["plan-10"]["coverage_entries"]
    }
    assert len(plan_10_entries) == 17
    assert "mass-transit-accidental-death-additional" not in plan_10_entries
    assert "land-transit-first-level-disability-additional" not in plan_10_entries
    assert plan_10_entries["general-accidental-death"]["amount"] == 500_000
    assert plan_10_entries["general-accidental-disability"]["amount"] == 500_000
    assert plan_10_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_10_entries["cancer-post-discharge-convalescence-daily"]["amount"] == 500

    source_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
            completed_document
        )
        == schedule
    )
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "癌症化學治療保險金 1,000 元/日",
                    "癌症化學治療保險金 2,000 元/日",
                    1,
                ),
            }
        )
        is None
    )


FUBON_COMPREHENSIVE_ACCIDENT_PRODUCTS = {
    "209211MZ1A01421A11Z10000000": (
        17,
        "113-original",
        "NAF1_51130329",
        "shiquan-ruyi",
        5,
        25,
        75,
        2,
        1,
    ),
    "209211MZ1A01421A11Z10000001": (
        17,
        "113-first-revision",
        "NAF1_51130923",
        "shiquan-ruyi",
        5,
        25,
        75,
        2,
        1,
    ),
    "209211MZ1A01421A11Z10000002": (
        17,
        "114-second-revision",
        "NAF1_51140101",
        "shiquan-ruyi",
        5,
        25,
        75,
        2,
        1,
    ),
    "209211MZ1A01522A11Z10000000": (
        17,
        "114-original",
        "NAG1_31140331",
        "yiwai-wuyou",
        3,
        21,
        70,
        0,
        3,
    ),
}


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_source_code,
        expected_family,
        expected_plan_count,
        expected_entry_count,
        expected_max_age,
        expected_guaranteed_years,
        expected_policy_years,
    ),
) in FUBON_COMPREHENSIVE_ACCIDENT_PRODUCTS.items():
    document = new_shouhu_jinnang_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_source_code in document["text"]
    assert "本契約分為" in document["text"]
    assert "意外傷害住院生活補助保險金" in document["text"]
    assert "失能程度與保險金給付表" in document["text"]
    schedule = parse_fubon_comprehensive_accident_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-comprehensive-accident-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fubon_product_family"] == expected_family
    assert characteristics["plan_count"] == expected_plan_count
    assert characteristics["maximum_renewal_age"] == expected_max_age
    assert characteristics["guaranteed_renewal_years"] == expected_guaranteed_years
    assert characteristics["policy_period_years"] == expected_policy_years
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["hospital_days_limit"] == 90
    assert characteristics["icu_days_limit"] == 30
    assert characteristics["nursing_days_limit"] == 90
    assert characteristics["burn_center_days_limit"] == 30
    assert characteristics["hospital_living_supplement_days_limit"] == 15
    assert characteristics["food_poisoning_lifetime_limit_times"] == 3
    assert characteristics["disability_living_supplement_lifetime_limit_times"] == 1
    assert characteristics["burn_lifetime_limit_times"] == 1
    assert characteristics["head_trauma_lifetime_limit_times"] == 1
    assert characteristics["fracture_unhospitalized_rate_percent"] == 50
    assert characteristics["disability_term"] == "失能"
    assert characteristics["disability_schedule_item_count"] == 80
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert len(plans) == expected_plan_count
    assert all(
        len(plan["coverage_entries"]) == expected_entry_count
        for plan in plans.values()
    )

    if expected_family == "shiquan-ruyi":
        assert [plan["label"] for plan in schedule["plan_options"]] == [
            "計劃 1",
            "計劃 2",
            "計劃 3",
            "計劃 4",
            "計劃 5",
        ]
        plan_1_entries = {
            entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
        }
        assert plan_1_entries["general-accidental-death"]["amount"] == 1_000_000
        assert (
            plan_1_entries["mass-transit-accidental-death-additional"]["amount"]
            == 3_000_000
        )
        assert (
            plan_1_entries[
                "public-building-fire-accidental-death-additional"
            ]["amount"]
            == 1_000_000
        )
        assert (
            plan_1_entries["natural-disaster-accidental-disability-additional"][
                "rate_max_percent"
            ]
            == 90
        )
        assert (
            plan_1_entries["natural-disaster-accidental-disability-additional"][
                "amount_tiers"
            ][0]["amount"]
            == 900_000
        )
        assert (
            plan_1_entries["accidental-disability-living-supplement"]["amount"]
            == 1_000_000
        )
        assert plan_1_entries["serious-third-degree-burn"]["amount"] == 1_000_000
        assert plan_1_entries["food-poisoning"]["amount"] == 2_000
        assert plan_1_entries["serious-head-trauma"]["amount"] == 500_000
        assert plan_1_entries["accident-hospital-daily"]["amount"] == 500
        assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == 250
        assert plan_1_entries["fracture-unhospitalized-medical"]["rate_percent"] == 50
        assert plan_1_entries["accident-icu-daily"]["amount"] == 1_000
        assert plan_1_entries["accident-nursing-daily"]["amount"] == 500
        assert plan_1_entries["accident-burn-center-daily"]["amount"] == 2_000
        assert plan_1_entries["accident-inpatient-surgery"]["amount"] == 1_500
        assert (
            plan_1_entries["accident-hospital-living-supplement"]["amount"]
            == 12_500
        )
        assert (
            plan_1_entries["accident-hospital-living-supplement"][
                "calculation_basis"
            ]
            == "tiered_or_stepped"
        )

        plan_5_entries = {
            entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
        }
        assert plan_5_entries["general-accidental-death"]["amount"] == 10_000_000
        assert (
            plan_5_entries["mass-transit-accidental-death-additional"]["amount"]
            == 6_000_000
        )
        assert plan_5_entries["accident-hospital-daily"]["amount"] == 3_000
        assert (
            plan_5_entries["accident-hospital-living-supplement"]["amount"]
            == 113_000
        )
    else:
        assert characteristics["same_day_icu_or_burn_center_choose_one"] is True
        assert characteristics["occupational_class_by_plan"] == {
            "plan-1": "第一類至第四類",
            "plan-2": "第一類至第四類",
            "plan-3": "第一類至第三類",
        }
        assert [plan["label"] for plan in schedule["plan_options"]] == [
            "計劃 1",
            "計劃 2",
            "計劃 3",
        ]
        plan_1_entries = {
            entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
        }
        assert plan_1_entries["general-accidental-death"]["amount"] == 2_000_000
        assert (
            plan_1_entries["motor-vehicle-accidental-death-additional"]["amount"]
            == 2_000_000
        )
        assert (
            plan_1_entries["holiday-accidental-death-additional"]["amount"]
            == 1_000_000
        )
        assert plan_1_entries["accident-hospital-daily"]["amount"] == 1_000
        assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == 500
        assert (
            plan_1_entries["accident-hospital-living-supplement"]["amount"]
            == 10_000
        )
        assert "擇一給付" in " ".join(
            plan_1_entries["accident-icu-daily"]["conditions"]
        )

        plan_3_entries = {
            entry["id"]: entry for entry in plans["plan-3"]["coverage_entries"]
        }
        assert plan_3_entries["general-accidental-death"]["amount"] == 4_000_000
        assert (
            plan_3_entries["holiday-accidental-death-additional"]["amount"]
            == 2_000_000
        )
        assert plan_3_entries["serious-head-trauma"]["amount"] == 1_000_000
        assert plan_3_entries["accident-inpatient-surgery"]["amount"] == 5_000

    first_plan_entries = {
        entry["id"]: entry for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    assert all(entry["source"] == "terms" for entry in first_plan_entries.values())
    assert all(entry.get("conditions") for entry in first_plan_entries.values())

    source_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert parse_fubon_comprehensive_accident_plan_table(completed_document) == schedule
    assert (
        parse_fubon_comprehensive_accident_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_comprehensive_accident_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_comprehensive_accident_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_comprehensive_accident_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    expected_source_code,
                    "BROKEN_SOURCE_CODE",
                ),
            }
        )
        is None
    )


FUBON_NEW_MILLION_HEART_PRODUCTS = {
    "209291MZ1G00321A11Z10000004": (
        22,
        "107-fourth-revision",
        "FBD1070914",
        79,
    ),
    "209291MZ1G00321A11Z10000005": (
        22,
        "109-fifth-revision",
        "FBD1090101",
        80,
    ),
    "209291MZ1G00321A11Z10000006": (
        22,
        "109-sixth-revision",
        "FBD1090901",
        80,
    ),
    "209291MZ1G00321A11Z10000007": (
        22,
        "111-seventh-revision",
        "FBD1111202",
        80,
    ),
}


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_fubon_code,
        expected_disability_items,
    ),
) in FUBON_NEW_MILLION_HEART_PRODUCTS.items():
    document = new_shouhu_jinnang_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    assert "新放百萬心" in document["text"]
    assert "本契約保障內容分八個計畫別" in document["text"]
    assert "日間留院" in document["text"]
    schedule = parse_fubon_new_million_heart_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-million-heart-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 8
    assert characteristics["non_guaranteed_renewal"] is True
    assert characteristics["maximum_renewal_age"] == 60
    assert characteristics["day_hospital_explicit"] is True
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["general_hospital_days_limit"] == 90
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["major_burn_rate_percent"] == 10
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_lifetime_limit_times"] == 1
    assert characteristics["disability_term"] == "失能"
    assert (
        characteristics["disability_schedule_item_count"]
        == expected_disability_items
    )
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
    ]
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert set(plans) == {
        "plan-1",
        "plan-2",
        "plan-3",
        "plan-4",
        "plan-5",
        "plan-6",
        "plan-7",
        "plan-8",
    }
    assert all(len(plan["coverage_entries"]) == 15 for plan in plans.values())

    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["total-disability"]["amount"] == 1_000_000
    assert plan_1_entries["general-accidental-death"]["amount"] == 1_000_000
    assert plan_1_entries["land-transit-accidental-death"]["amount"] == 1_000_000
    assert (
        plan_1_entries["public-building-fire-accidental-death"]["amount"]
        == 1_000_000
    )
    assert plan_1_entries["elevator-accidental-death"]["amount"] == 1_000_000
    assert plan_1_entries["general-accidental-disability"]["amount"] == 1_000_000
    assert (
        plan_1_entries["general-accidental-disability"]["amount_tiers"][0][
            "amount"
        ]
        == 1_000_000
    )
    assert (
        plan_1_entries["general-accidental-disability"]["amount_tiers"][-1][
            "amount"
        ]
        == 50_000
    )
    assert (
        plan_1_entries["land-transit-first-level-disability"]["amount"]
        == 1_000_000
    )
    assert (
        plan_1_entries["public-building-fire-first-level-disability"]["amount"]
        == 1_000_000
    )
    assert (
        plan_1_entries["elevator-first-level-disability"]["amount"]
        == 1_000_000
    )
    assert plan_1_entries["major-burn"]["amount"] == 100_000
    assert plan_1_entries["major-burn"]["rate_percent"] == 10
    assert plan_1_entries["hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == 500
    assert plan_1_entries["outpatient-surgery"]["amount"] == 1_000
    assert plan_1_entries["specific-treatment"]["amount"] == 1_000
    assert (
        plan_1_entries["land-transit-accidental-death"]["aggregation_rule"]
        == "conditional_additive"
    )
    assert (
        plan_1_entries["general-accidental-disability"]["calculation_basis"]
        == "table_multiplier"
    )
    assert plan_1_entries["hospital-daily"]["calculation_basis"] == "per_day"
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    plan_4_entries = {
        entry["id"]: entry for entry in plans["plan-4"]["coverage_entries"]
    }
    assert plan_4_entries["general-accidental-death"]["amount"] == 5_000_000
    assert plan_4_entries["major-burn"]["amount"] == 500_000
    assert plan_4_entries["hospital-daily"]["amount"] == 1_000
    assert plan_4_entries["fracture-unhospitalized-medical"]["amount"] == 500

    plan_5_entries = {
        entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
    }
    assert plan_5_entries["general-accidental-death"]["amount"] == 1_000_000
    assert plan_5_entries["hospital-daily"]["amount"] == 2_000
    assert plan_5_entries["fracture-unhospitalized-medical"]["amount"] == 1_000

    plan_8_entries = {
        entry["id"]: entry for entry in plans["plan-8"]["coverage_entries"]
    }
    assert plan_8_entries["general-accidental-death"]["amount"] == 5_000_000
    assert plan_8_entries["major-burn"]["amount"] == 500_000
    assert plan_8_entries["hospital-daily"]["amount"] == 2_000
    assert plan_8_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_8_entries["outpatient-surgery"]["amount"] == 2_000
    assert plan_8_entries["specific-treatment"]["amount"] == 2_000

    source_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_new_million_heart_accident_health_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_fubon_new_million_heart_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_new_million_heart_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_new_million_heart_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_new_million_heart_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "住院醫療日額保險金 1,000 元/日",
                    "住院醫療日額保險金 9,000 元/日",
                    1,
                ),
            }
        )
        is None
    )


FUBON_MILLION_HEART_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_MILLION_HEART_PRODUCTS = {
    "209291M12G00100": (
        16,
        "102-original",
        "FBE1020401",
        75,
        "殘廢",
        False,
    ),
    "209291M11G00201": (
        16,
        "103-first-revision",
        "FBE1030501",
        75,
        "殘廢",
        True,
    ),
    "209291MZ1G00221A11Z10000002": (
        18,
        "104-second-revision",
        "FBE1040804",
        79,
        "殘廢",
        True,
    ),
    "209291MZ1G00221A11Z10000003": (
        18,
        "107-third-revision",
        "FBE1070914",
        79,
        "失能",
        True,
    ),
    "209291MZ1G00221A11Z10000004": (
        18,
        "109-fourth-revision",
        "FBE1090101",
        80,
        "失能",
        True,
    ),
    "209291MZ1G00221A11Z10000005": (
        18,
        "109-fifth-revision",
        "FBE1090901",
        80,
        "失能",
        True,
    ),
    "209291MZ1G00221A11Z10000006": (
        18,
        "111-sixth-revision",
        "FBE1111202",
        80,
        "失能",
        True,
    ),
}


def fubon_million_heart_document(product_id: str) -> dict:
    pdf_path = FUBON_MILLION_HEART_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_fubon_code,
        expected_disability_items,
        expected_disability_term,
        expected_day_hospital_explicit,
    ),
) in FUBON_MILLION_HEART_PRODUCTS.items():
    document = fubon_million_heart_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    assert "富邦人壽放百萬心傷害暨健康一年定期保險" in document["text"]
    assert "富邦人壽新放百萬心傷害暨健康一年定期保險" not in document["text"]
    assert "本契約保障內容分十個計畫別" in document["text"]
    assert ("日間留院" in document["text"]) is expected_day_hospital_explicit
    assert "重大燒燙傷" not in document["text"]
    assert "門診手術" not in document["text"]
    assert "特定處置" not in document["text"]
    assert parse_fubon_new_million_heart_accident_health_plan_table(document) is None
    schedule = parse_fubon_million_heart_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-million-heart-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    characteristics = schedule["version_characteristics"]
    assert characteristics == {
        "terms_revision": expected_revision,
        "plan_count": 10,
        "non_guaranteed_renewal": True,
        "maximum_renewal_age": 50,
        "day_hospital_explicit": expected_day_hospital_explicit,
        "same_hospital_readmission_days": 14,
        "hospital_daily_days_limit_per_policy_year_same_hospitalization": 30,
        "accident_claim_days": 180,
        "death_disability_same_accident_cap": True,
        "disability_term": expected_disability_term,
        "total_disability_schedule_item_count": 7,
        "disability_schedule_item_count": expected_disability_items,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "short_term_rate_table": True,
    }
    assert [plan["label"] for plan in schedule["plan_options"]] == [
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
    ]

    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert set(plans) == {
        "plan-1",
        "plan-2",
        "plan-3",
        "plan-4",
        "plan-5",
        "plan-6",
        "plan-7",
        "plan-8",
        "plan-9",
        "plan-10",
    }
    assert all(len(plan["coverage_entries"]) == 5 for plan in plans.values())
    all_entries_json = json.dumps(schedule["plan_options"], ensure_ascii=False)
    assert "重大燒燙傷" not in all_entries_json
    assert "門診手術" not in all_entries_json
    assert "特定處置" not in all_entries_json

    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["total-disability"]["amount"] == 1_000_000
    assert plan_1_entries["hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["hospital-daily"]["calculation_basis"] == "per_day"
    assert plan_1_entries["accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["accidental-disability"]["amount"] == 1_000_000
    assert (
        plan_1_entries["accidental-disability"]["calculation_basis"]
        == "table_multiplier"
    )
    assert plan_1_entries["accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 1_000_000,
    }
    assert plan_1_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert plan_1_entries["accidental-disability"]["aggregation_rule"] == "cumulative_cap"

    plan_5_entries = {
        entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
    }
    assert plan_5_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_5_entries["total-disability"]["amount"] == 1_000_000
    assert plan_5_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_5_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }

    plan_6_entries = {
        entry["id"]: entry for entry in plans["plan-6"]["coverage_entries"]
    }
    assert plan_6_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_6_entries["total-disability"]["amount"] == 2_000_000
    assert plan_6_entries["accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_6_entries["hospital-daily"]["amount"] == 1_000

    plan_10_entries = {
        entry["id"]: entry for entry in plans["plan-10"]["coverage_entries"]
    }
    assert plan_10_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_10_entries["total-disability"]["amount"] == 2_000_000
    assert plan_10_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_10_entries["accidental-disability"]["amount"] == 5_000_000
    assert plan_10_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    source_path = FUBON_MILLION_HEART_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_million_heart_accident_health_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_fubon_million_heart_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_million_heart_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_million_heart_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_million_heart_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "住院醫療日額保險金 1,000 元/日",
                    "住院醫療日額保險金 9,000 元/日",
                    1,
                ),
            }
        )
        is None
    )


FUBON_VISION_LIFE_PRODUCTS = {
    "209291M12G00600": (
        20,
        "102-original",
        "FBJ1020401",
        75,
        "殘廢",
        30,
        False,
    ),
    "209291M12G00601": (
        20,
        "103-first-revision",
        "FBJ1030501",
        75,
        "殘廢",
        30,
        True,
    ),
    "209291MZ2G00421A11Z10000002": (
        21,
        "104-second-revision",
        "FBJ1040804",
        79,
        "殘廢",
        30,
        True,
    ),
    "209291MZ2G00421A11Z10000003": (
        21,
        "107-third-revision",
        "FBJ1070430",
        79,
        "殘廢",
        0,
        True,
    ),
    "209291MZ2G00421A11Z10000004": (
        21,
        "107-fourth-revision",
        "FBJ1070914",
        79,
        "失能",
        0,
        True,
    ),
    "209291MZ2G00421A11Z10000005": (
        21,
        "108-fifth-revision",
        "FBJ1080101",
        79,
        "失能",
        0,
        True,
    ),
    "209291MZ2G00421A11Z10000006": (
        21,
        "109-sixth-revision",
        "FBJ1090101",
        80,
        "失能",
        0,
        True,
    ),
    "209291MZ2G00421A11Z10000007": (
        21,
        "109-seventh-revision",
        "FBJ1090901",
        80,
        "失能",
        0,
        True,
    ),
    "209291MZ2G00421A11Z10000008": (
        21,
        "111-eighth-revision",
        "FBJ1111202",
        80,
        "失能",
        0,
        True,
    ),
}


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_fubon_code,
        expected_disability_items,
        expected_disability_term,
        expected_cancer_waiting_days,
        expected_day_hospital_excluded,
    ),
) in FUBON_VISION_LIFE_PRODUCTS.items():
    document = new_shouhu_jinnang_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    assert "本契約保障內容分三個計畫別" in document["text"]
    assert "本契約最高可續保至被保險人保險年齡五十五歲" in document["text"]
    assert f"完全{expected_disability_term}保險金" in document["text"]
    assert parse_fubon_new_shouhu_jinnang_accident_health_plan_table(document) is None
    assert (
        parse_fubon_new_shouhu_jinnang_late_accident_health_plan_table(document)
        is None
    )
    schedule = parse_fubon_vision_life_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-vision-life-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 3
    assert characteristics["non_guaranteed_renewal"] is True
    assert characteristics["maximum_renewal_age"] == 55
    assert characteristics["cancer_waiting_days"] == expected_cancer_waiting_days
    assert characteristics["day_hospital_excluded"] is expected_day_hospital_excluded
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["accident_hospital_days_limit"] == 90
    assert characteristics["accident_icu_days_limit"] == 30
    assert characteristics["burn_center_days_limit"] == 30
    assert characteristics["accident_outpatient_surgery_limit_times"] == 1
    assert characteristics["fracture_daily_rate_percent"] == 50
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_lifetime_limit_times"] == 1
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["mass_transit_additional_benefit"] is True
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
    ]

    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert len(plan_1_entries) == 15
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 500_000
    assert plan_1_entries["total-disability"]["amount"] == 500_000
    assert plan_1_entries["general-accidental-death"]["amount"] == 1_000_000
    assert (
        plan_1_entries["mass-transit-accidental-death-additional"]["amount"]
        == 1_000_000
    )
    assert (
        plan_1_entries["mass-transit-accidental-death-additional"][
            "aggregation_rule"
        ]
        == "conditional_additive"
    )
    assert plan_1_entries["general-accidental-disability"]["amount"] == 1_000_000
    assert (
        plan_1_entries["general-accidental-disability"]["calculation_basis"]
        == "table_multiplier"
    )
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][0][
        "amount"
    ] == 1_000_000
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][-1][
        "amount"
    ] == 50_000
    assert (
        plan_1_entries["mass-transit-accidental-disability-additional"][
            "amount_tiers"
        ][0]["amount"]
        == 1_000_000
    )
    assert plan_1_entries["major-burn"]["amount"] == 250_000
    assert plan_1_entries["major-burn"]["aggregation_rule"] == "separate"
    assert plan_1_entries["accident-hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == 500
    assert plan_1_entries["fracture-unhospitalized-medical"]["rate_percent"] == 50
    assert plan_1_entries["fracture-unhospitalized-medical"]["amount_role"] == "reference"
    assert (
        plan_1_entries["fracture-unhospitalized-medical"]["calculation_basis"]
        == "percentage_of_base"
    )
    assert plan_1_entries["accident-icu-hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["accident-burn-center-hospital-daily"]["amount"] == 2_000
    assert plan_1_entries["accident-outpatient-surgery"]["amount"] == 1_000
    assert plan_1_entries["cancer-hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["cancer-surgery"]["amount"] == 20_000
    assert plan_1_entries["cancer-radiation-daily"]["amount"] == 1_000

    plan_2_entries = {
        entry["id"]: entry for entry in plans["plan-2"]["coverage_entries"]
    }
    assert plan_2_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_2_entries["fracture-unhospitalized-medical"]["amount"] == 750
    assert plan_2_entries["cancer-surgery"]["amount"] == 30_000

    plan_3_entries = {
        entry["id"]: entry for entry in plans["plan-3"]["coverage_entries"]
    }
    assert len(plan_3_entries) == 15
    assert plan_3_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_3_entries["total-disability"]["amount"] == 2_000_000
    assert plan_3_entries["general-accidental-death"]["amount"] == 4_000_000
    assert (
        plan_3_entries["mass-transit-accidental-death-additional"]["amount"]
        == 4_000_000
    )
    assert (
        plan_3_entries["mass-transit-accidental-death-additional"][
            "aggregation_rule"
        ]
        == "conditional_additive"
    )
    assert plan_3_entries["general-accidental-disability"]["amount"] == 4_000_000
    assert (
        plan_3_entries["mass-transit-accidental-disability-additional"][
            "amount_tiers"
        ][-1]["amount"]
        == 200_000
    )
    assert plan_3_entries["major-burn"]["amount"] == 1_000_000
    assert plan_3_entries["accident-hospital-daily"]["amount"] == 2_000
    assert plan_3_entries["fracture-unhospitalized-medical"]["amount"] == 1_000
    assert plan_3_entries["accident-icu-hospital-daily"]["amount"] == 2_000
    assert plan_3_entries["accident-burn-center-hospital-daily"]["amount"] == 4_000
    assert plan_3_entries["accident-outpatient-surgery"]["amount"] == 2_000
    assert plan_3_entries["cancer-hospital-daily"]["amount"] == 2_000
    assert plan_3_entries["cancer-surgery"]["amount"] == 50_000
    assert plan_3_entries["cancer-radiation-daily"]["amount"] == 2_000
    plan_3_json = json.dumps(plan_3_entries, ensure_ascii=False)
    assert expected_disability_term in plan_3_json
    if expected_disability_term == "失能":
        assert "殘廢" not in plan_3_json
    else:
        assert "失能" not in plan_3_json
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    source_path = NEW_SHOUHU_JINNANG_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert parse_fubon_vision_life_accident_health_plan_table(
        completed_document
    ) == schedule
    assert (
        parse_fubon_vision_life_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_vision_life_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_vision_life_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_vision_life_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "重大燒燙傷保險金 25 萬 50 萬 100 萬",
                    "重大燒燙傷保險金 25 萬 50 萬 200 萬",
                    1,
                ),
            }
        )
        is None
    )


FUBON_XIANGANBAO_ACCIDENT_MEDICAL_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_XIANGANBAO_ACCIDENT_MEDICAL_PRODUCTS = {
    "209211AZ1A00421A11Z10000000": "113-original",
    "209211AZ1A00421A11Z10000001": "113-first-revision",
    "209211AZ1A00421A11Z10000002": "113-second-revision",
}


def fubon_xianganbao_accident_medical_document(
    product_id: str, suffix: str = "A"
) -> dict:
    pdf_path = (
        FUBON_XIANGANBAO_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    expected_revision,
) in FUBON_XIANGANBAO_ACCIDENT_MEDICAL_PRODUCTS.items():
    document = fubon_xianganbao_accident_medical_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 3
    assert "TMR1130715" in document["text"]
    assert "富邦人壽享安寶意外傷害醫療保險給付附加條款" in document["text"]
    assert "意外傷害脫臼開放性復位術保險金" in document["text"]
    assert "意外傷害醫療保險金" in document["text"]

    schedule = parse_fubon_xianganbao_accident_medical_rider_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert (
        integrated[0]
        == "fubon-xianganbao-accident-medical-rider-face-amount-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "本附加條款保險金額"
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "fubon_code": "TMR1130715",
        "accident_claim_days": 180,
        "overseas_medical_treatment_days_limit": 14,
        "non_nhi_payment_rate_percent": 75,
        "medical_icu_burn_center_limit_rate_percent": 150,
        "medical_reimbursement_nhi_excess_only": True,
        "duplicate_reimbursement_excluded": True,
        "dislocation_base_amount": 150_000,
        "dislocation_table_item_count": 8,
        "dislocation_rate_min_percent": 10,
        "dislocation_rate_max_percent": 30,
    }

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "accident-dislocation-open-reduction",
        "accident-medical-reimbursement-limit",
        "accident-medical-icu-burn-center-limit",
    }
    dislocation = entries["accident-dislocation-open-reduction"]
    assert dislocation["amount"] == 15_000
    assert dislocation["calculation_basis"] == "tiered_or_stepped"
    assert dislocation["aggregation_rule"] == "highest"
    assert dislocation["amount_tiers"][0] == {
        "label": "髖關節 30%",
        "amount": 45_000,
    }
    assert dislocation["amount_tiers"][-1] == {
        "label": "其他關節 10%",
        "amount": 15_000,
    }

    medical = entries["accident-medical-reimbursement-limit"]
    assert medical["basis"] == "face_amount"
    assert medical["calculation_basis"] == "percentage_of_base"
    assert medical["amount_role"] == "limit"
    assert medical["limit_scope"] == "per_injury"
    assert medical["rate_percent"] == 100
    assert medical["aggregation_rule"] == "choose_one"
    assert "百分之七十五" in " ".join(medical["conditions"])

    icu_burn = entries["accident-medical-icu-burn-center-limit"]
    assert icu_burn["basis"] == "face_amount"
    assert icu_burn["calculation_basis"] == "percentage_of_base"
    assert icu_burn["rate_percent"] == 150
    assert icu_burn["aggregation_rule"] == "choose_one"
    assert "燒燙傷中心" in " ".join(icu_burn["conditions"])
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

    source_path = (
        FUBON_XIANGANBAO_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:2]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 3
    assert (
        parse_fubon_xianganbao_accident_medical_rider_face_amount(
            completed_document
        )
        == schedule
    )
    assert (
        parse_fubon_xianganbao_accident_medical_rider_face_amount(
            fubon_xianganbao_accident_medical_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_fubon_xianganbao_accident_medical_rider_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_xianganbao_accident_medical_rider_face_amount(
            {**document, "page_count": 2}
        )
        is None
    )
    assert (
        parse_fubon_xianganbao_accident_medical_rider_face_amount(
            {
                **document,
                "text": document["text"].replace("百分之七十五", "百分之八十五", 1),
            }
        )
        is None
    )


YUANTA_NEW_ACCIDENT_MEDICAL_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-151"
)
YUANTA_NEW_ACCIDENT_MEDICAL_PRODUCTS = {
    "261211RZ1AQR021A11Z10000000": ("108-original", "QR-上市日期:108.05.31"),
    "261211RZ1AQR021A11Z10000001": ("109-first-revision", "QR-2020.01"),
    "261211RZ1AQR021A11Z10000002": ("110-second-revision", "QR-2021.12"),
    "261211RZ1AQR021A11Z10000003": ("112-third-revision", "QR-2023.01"),
}


def yuanta_new_accident_medical_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = (
        YUANTA_NEW_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    (expected_revision, expected_yuanta_code),
) in YUANTA_NEW_ACCIDENT_MEDICAL_PRODUCTS.items():
    document = yuanta_new_accident_medical_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 2
    assert expected_yuanta_code in document["text"]
    assert "元大人壽新意外傷害醫療保險附約" in document["text"]
    assert "每次實支實付傷害醫療保險金限額" in document["text"]

    schedule = parse_yuanta_new_accident_medical_rider_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-new-accident-medical-rider-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "每次實支實付傷害醫療保險金限額"
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "yuanta_code": expected_yuanta_code,
        "accident_claim_days": 180,
        "non_nhi_payment_rate_percent": 65,
        "medical_reimbursement_nhi_excess_only": True,
        "policy_recorded_limit_label": "每次實支實付傷害醫療保險金限額",
    }

    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {"accident-medical-reimbursement-limit"}
    medical = entries["accident-medical-reimbursement-limit"]
    assert medical["basis"] == "face_amount"
    assert medical["calculation_basis"] == "percentage_of_base"
    assert medical["amount_role"] == "limit"
    assert medical["limit_scope"] == "per_injury"
    assert medical["rate_percent"] == 100
    assert "百分之六十五" in " ".join(medical["conditions"])
    assert medical["source"] == "terms"

    source_path = (
        YUANTA_NEW_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        (PdfReader(source_path, strict=False).pages[0].extract_text() or "")
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 2
    assert (
        parse_yuanta_new_accident_medical_rider_face_amount(completed_document)
        == schedule
    )
    assert (
        parse_yuanta_new_accident_medical_rider_face_amount(
            yuanta_new_accident_medical_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_yuanta_new_accident_medical_rider_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_yuanta_new_accident_medical_rider_face_amount(
            {**document, "page_count": 1}
        )
        is None
    )
    assert (
        parse_yuanta_new_accident_medical_rider_face_amount(
            {
                **document,
                "text": document["text"].replace("百分之六十五", "百分之七十五", 1),
            }
        )
        is None
    )


YUANTA_PERSONAL_ACCIDENT_PRODUCTS = {
    "261211RZ1APR021A11Z10000013": (
        "105-thirteenth-revision",
        "元壽字第 1050000730 號函備查",
    ),
    "261211RZ1APR021A11Z10000014": (
        "106-fourteenth-revision",
        "金管保財字第 10502502801 號令修正",
    ),
}


def yuanta_life_151_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = (
        YUANTA_NEW_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms" if suffix == "A" else "product_summary",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (expected_revision, expected_filing_signal) in (
    YUANTA_PERSONAL_ACCIDENT_PRODUCTS.items()
):
    document = yuanta_life_151_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 5
    assert "元大人壽人身傷害保險附約" in document["text"]
    assert expected_filing_signal in document["text"]

    schedule = parse_yuanta_personal_accident_rider_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-personal-accident-rider-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "filing_signal": expected_filing_signal,
        "accident_claim_days": 180,
        "maximum_renewal_age": 75,
        "child_maximum_renewal_age": 23,
        "minor_death_premium_refund_before_age": 15,
        "funeral_benefit_limit_rule": True,
        "death_benefit_rate_percent": 100,
        "disability_term": "殘廢",
        "disability_schedule_item_count": 115,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "major_burn_rate_percent": 25,
        "major_burn_lifetime_limit_times": 1,
        "death_disability_same_accident_cap": True,
    }
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "accidental-death-or-funeral",
        "accidental-disability",
        "major-burn",
    }
    assert entries["accidental-death-or-funeral"]["rate_percent"] == 100
    assert entries["accidental-death-or-funeral"]["basis"] == "face_amount"
    assert entries["accidental-disability"]["rate_min_percent"] == 5
    assert entries["accidental-disability"]["rate_max_percent"] == 100
    assert entries["accidental-disability"]["aggregation_rule"] == "cumulative_cap"
    assert entries["major-burn"]["rate_percent"] == 25
    assert entries["major-burn"]["limit_scope"] == "lifetime"

    source_path = (
        YUANTA_NEW_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        (PdfReader(source_path, strict=False).pages[0].extract_text() or "")
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 5
    assert parse_yuanta_personal_accident_rider_face_amount(completed_document) == (
        schedule
    )
    assert (
        parse_yuanta_personal_accident_rider_face_amount(
            yuanta_life_151_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_yuanta_personal_accident_rider_face_amount(
            {**document, "page_count": 4}
        )
        is None
    )
    assert (
        parse_yuanta_personal_accident_rider_face_amount(
            {
                **document,
                "text": document["text"].replace(
                    "保險金額百分之二十五給付重大燒燙傷保險金",
                    "保險金額百分之三十五給付重大燒燙傷保險金",
                    1,
                ),
            }
        )
        is None
    )


YUANTA_FUNXINYOU_ACCIDENT_MEDICAL_PRODUCTS = {
    "261221AZ1ATAM21A11Z10000003": ("third-revision", "本契約"),
    "261221AZ1ATAM21A11Z10000004": ("fourth-revision", "主契約"),
}


for product_id, (expected_revision, expected_contract_reference) in (
    YUANTA_FUNXINYOU_ACCIDENT_MEDICAL_PRODUCTS.items()
):
    document = yuanta_life_151_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 1
    assert "元大人壽Fun 心遊傷害醫療保險給付附加條款" in document["text"]
    assert f"遭受{expected_contract_reference}第二條約定的意外傷害事故" in document["text"]

    schedule = parse_yuanta_funxinyou_accident_medical_addendum_limit(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "yuanta-funxinyou-accident-medical-addendum-limit-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "每次實支實付傷害醫療保險金限額"
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "contract_reference": expected_contract_reference,
        "accident_claim_days": 180,
        "non_nhi_payment_rate_percent": 65,
        "medical_reimbursement_nhi_excess_only": True,
        "policy_recorded_limit_label": "每次實支實付傷害醫療保險金限額",
        "beneficiary_self_only": True,
    }
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "accident-medical-reimbursement-limit",
        "non-nhi-medical-reimbursement",
    }
    assert entries["accident-medical-reimbursement-limit"]["basis"] == (
        "policy_recorded_limit"
    )
    assert entries["accident-medical-reimbursement-limit"]["rate_percent"] == 100
    assert entries["accident-medical-reimbursement-limit"]["limit_scope"] == (
        "per_injury"
    )
    assert entries["non-nhi-medical-reimbursement"]["rate_percent"] == 65
    assert entries["non-nhi-medical-reimbursement"]["calculation_basis"] == (
        "percentage_of_actual_expense_with_cap"
    )

    source_path = (
        YUANTA_NEW_ACCIDENT_MEDICAL_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = ""
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 1
    assert (
        parse_yuanta_funxinyou_accident_medical_addendum_limit(completed_document)
        == schedule
    )
    assert (
        parse_yuanta_funxinyou_accident_medical_addendum_limit(
            yuanta_life_151_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_yuanta_funxinyou_accident_medical_addendum_limit(
            {**document, "page_count": 2}
        )
        is None
    )
    assert (
        parse_yuanta_funxinyou_accident_medical_addendum_limit(
            {
                **document,
                "text": document["text"].replace(
                    "本公司依被保險人實際支付之各項費用之65%給付",
                    "本公司依被保險人實際支付之各項費用之75%給付",
                    1,
                ),
            }
        )
        is None
    )


FUBON_NEW_PINGAN_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_NEW_PINGAN_PRODUCTS = {
    "209291MZ1A00321A11Z10000002": (
        14,
        "107-second-revision",
        "FBB1070914",
        79,
    ),
    "209291MZ1A00321A11Z10000003": (
        14,
        "109-third-revision",
        "FBB1090101",
        80,
    ),
    "209291MZ1A00321A11Z10000004": (
        14,
        "109-fourth-revision",
        "FBB1090901",
        80,
    ),
    "209291MZ1A00321A11Z10000005": (
        14,
        "111-fifth-revision",
        "FBB1111202",
        80,
    ),
}


def fubon_new_pingan_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = FUBON_NEW_PINGAN_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_fubon_code,
        expected_disability_items,
    ),
) in FUBON_NEW_PINGAN_PRODUCTS.items():
    document = fubon_new_pingan_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    assert "富邦人壽新平安傷害一年定期保險" in document["text"]
    assert "本契約保障內容分八個計畫別" in document["text"]
    compact_document_text = compact_table_text(compact_whitespace(document["text"]))
    assert "意外傷害醫療保險金5萬-" in compact_document_text
    assert "意外傷害住院醫療保險金-1500元/日" in compact_document_text
    assert parse_fubon_666_accident_health_plan_table(document) is None
    schedule = parse_fubon_new_pingan_accident_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-pingan-accident-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "plan_count": 8,
        "non_guaranteed_renewal": True,
        "maximum_renewal_age": 65,
        "accident_claim_days": 180,
        "accident_medical_limit": 50_000,
        "accident_medical_daily_formula_per_10000_inpatient_only": 70,
        "accident_medical_daily_formula_per_10000_inpatient_split": 40,
        "accident_medical_daily_formula_per_10000_outpatient_split": 20,
        "accident_medical_daily_formula_days_limit": 90,
        "accident_hospital_daily_amount": 1_500,
        "accident_hospital_days_limit": 90,
        "fracture_daily_rate_percent": 50,
        "death_disability_same_accident_cap": True,
        "disability_term": "失能",
        "disability_schedule_item_count": expected_disability_items,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "short_term_rate_table": True,
    }
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
    ]
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert all(
        len(plans[plan_key]["coverage_entries"]) == 5
        for plan_key in ("plan-1", "plan-2", "plan-3", "plan-4")
    )
    assert all(
        len(plans[plan_key]["coverage_entries"]) == 4
        for plan_key in ("plan-5", "plan-6", "plan-7", "plan-8")
    )
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert plan_1_entries["accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["accidental-disability"]["amount"] == 1_000_000
    assert plan_1_entries["accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 1_000_000,
    }
    assert plan_1_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert plan_1_entries["accident-medical-reimbursement"]["amount"] == 50_000
    assert (
        plan_1_entries["accident-medical-reimbursement"]["calculation_basis"]
        == "reimbursement_with_cap"
    )
    assert plan_1_entries["accident-medical-daily-option-a"]["amount"] == 350
    assert plan_1_entries["accident-medical-daily-option-b"]["amount"] == 200
    assert plan_1_entries["accident-medical-daily-option-b"]["amount_tiers"] == [
        {"label": "住院每日", "amount": 200},
        {"label": "門診每日", "amount": 100},
    ]
    assert (
        plan_1_entries["accident-medical-daily-option-a"]["aggregation_rule"]
        == "choose_one"
    )

    plan_4_entries = {
        entry["id"]: entry for entry in plans["plan-4"]["coverage_entries"]
    }
    assert plan_4_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_4_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }

    plan_5_entries = {
        entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
    }
    assert "accident-medical-reimbursement" not in plan_5_entries
    assert plan_5_entries["accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_5_entries["accident-hospital-daily"]["amount"] == 1_500
    assert plan_5_entries["accident-hospital-daily"]["calculation_basis"] == "per_day"
    assert plan_5_entries["fracture-unhospitalized-daily"]["amount"] == 750
    assert (
        plan_5_entries["fracture-unhospitalized-daily"]["calculation_basis"]
        == "percentage_of_base"
    )
    assert plan_5_entries["fracture-unhospitalized-daily"]["rate_percent"] == 50

    plan_8_entries = {
        entry["id"]: entry for entry in plans["plan-8"]["coverage_entries"]
    }
    assert plan_8_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_8_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }
    assert plan_8_entries["accident-hospital-daily"]["amount"] == 1_500
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    source_path = FUBON_NEW_PINGAN_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert parse_fubon_new_pingan_accident_plan_table(completed_document) == schedule
    assert parse_fubon_new_pingan_accident_plan_table(
        fubon_new_pingan_document(product_id, "F")
    ) is None
    assert (
        parse_fubon_new_pingan_accident_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_new_pingan_accident_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_new_pingan_accident_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "每壹萬元換算住院每日柒拾元",
                    "每壹萬元換算住院每日捌拾元",
                    1,
                ),
            }
        )
        is None
    )


FUBON_666_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_666_PRODUCTS = {
    "209291M12A00100": (16, "102-original", "CTBC1020401", "殘廢", 75),
    "209291MZ2A00121A11Z10000001": (17, "104-first-revision", "CTBC1040804", "殘廢", 79),
    "209291MZ2A00121A11Z10000002": (17, "105-second-revision", "CTBC1050901", "殘廢", 79),
    "209291MZ2A00121A11Z10000003": (17, "107-third-revision", "CTBC1070914", "失能", 79),
    "209291MZ2A00121A11Z10000004": (18, "109-fourth-revision", "CTBC1090101", "失能", 80),
    "209291MZ2A00121A11Z10000005": (18, "109-fifth-revision", "CTBC1090901", "失能", 80),
    "209291MZ2A00121A11Z10000006": (18, "110-sixth-revision", "CTBC1100701", "失能", 80),
    "209291MZ2A00121A11Z10000007": (18, "111-seventh-revision", "CTBC1111202", "失能", 80),
}


def fubon_666_document(product_id: str) -> dict:
    pdf_path = FUBON_666_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for (
    product_id,
    (
        expected_pages,
        expected_revision,
        expected_ctbc_code,
        expected_disability_term,
        expected_disability_items,
    ),
) in FUBON_666_PRODUCTS.items():
    document = fubon_666_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_ctbc_code in document["text"]
    schedule = parse_fubon_666_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-666-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 2
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["accident_hospital_days_limit"] == 90
    assert characteristics["fracture_daily_rate_percent"] == 50
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert characteristics["mass_transit_additional_benefit"] is True
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
    ]

    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert len(plan_1_entries) == 8
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["total-disability"]["amount"] == 1_000_000
    assert plan_1_entries["total-disability"]["name"] == (
        f"完全{expected_disability_term}保險金"
    )
    assert (
        plan_1_entries["general-accidental-death-or-funeral"]["amount"]
        == 2_500_000
    )
    assert (
        plan_1_entries["mass-transit-accidental-death-or-funeral"]["amount"]
        == 2_500_000
    )
    assert (
        plan_1_entries["mass-transit-accidental-death-or-funeral"][
            "aggregation_rule"
        ]
        == "conditional_additive"
    )
    assert plan_1_entries["general-accidental-disability"]["amount"] == 2_500_000
    assert plan_1_entries["general-accidental-disability"]["name"] == (
        f"一般意外{expected_disability_term}保險金"
    )
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 2_500_000,
    }
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 125_000,
    }
    assert (
        plan_1_entries["mass-transit-accidental-disability"]["amount_tiers"][-1][
            "amount"
        ]
        == 125_000
    )
    assert plan_1_entries["mass-transit-accidental-disability"]["name"] == (
        f"大眾運輸工具意外{expected_disability_term}保險金"
    )
    assert plan_1_entries["accident-hospital-daily"]["amount"] == 2_500
    assert plan_1_entries["fracture-unhospitalized-daily"]["amount"] == 1_250
    assert plan_1_entries["fracture-unhospitalized-daily"]["rate_percent"] == 50

    plan_2_entries = {
        entry["id"]: entry for entry in plans["plan-2"]["coverage_entries"]
    }
    assert len(plan_2_entries) == 6
    assert "life-death-or-funeral" not in plan_2_entries
    assert "total-disability" not in plan_2_entries
    assert (
        plan_2_entries["general-accidental-death-or-funeral"]["amount"]
        == 2_500_000
    )
    assert (
        plan_2_entries["mass-transit-accidental-death-or-funeral"]["amount"]
        == 2_500_000
    )
    assert plan_2_entries["general-accidental-disability"]["amount"] == 2_500_000
    assert plan_2_entries["accident-hospital-daily"]["amount"] == 2_000
    assert plan_2_entries["fracture-unhospitalized-daily"]["amount"] == 1_000
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry["source"] == "terms" for entry in plan_2_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_2_entries.values())

    source_path = FUBON_666_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert parse_fubon_666_accident_health_plan_table(completed_document) == schedule
    assert (
        parse_fubon_666_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_666_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_666_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_666_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "意外傷害住院醫療保險金 2,500 元/日 2,000 元/日",
                    "意外傷害住院醫療保險金 2,500 元/日 2,500 元/日",
                    1,
                ),
            }
        )
        is None
    )


FUBON_MILLION_NEW_LIFE_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_MILLION_NEW_LIFE_PRODUCTS = {
    "209291M12G00400": (17, "102-original", "FBA1020401", "殘廢", 75),
    "209291M11G00101": (17, "103-first-revision", "FBA1030501", "殘廢", 75),
    "209291MZ1G00121A11Z10000002": (
        18,
        "104-second-revision",
        "FBA1040804",
        "殘廢",
        79,
    ),
    "209291MZ1G00121A11Z10000003": (
        18,
        "105-third-revision",
        "FBA1050727",
        "殘廢",
        79,
    ),
    "209291MZ1G00121A11Z10000004": (
        18,
        "107-fourth-revision",
        "FBA1070914",
        "失能",
        79,
    ),
    "209291MZ1G00121A11Z10000005": (
        18,
        "109-fifth-revision",
        "FBA1090101",
        "失能",
        80,
    ),
    "209291MZ1G00121A11Z10000006": (
        18,
        "109-sixth-revision",
        "FBA1090901",
        "失能",
        80,
    ),
    "209291MZ1G00121A11Z10000007": (
        18,
        "111-seventh-revision",
        "FBA1111202",
        "失能",
        80,
    ),
}


def fubon_million_new_life_document(product_id: str, suffix: str = "A") -> dict:
    pdf_path = FUBON_MILLION_NEW_LIFE_ROOT / product_id / f"{product_id}-{suffix}.pdf"
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_pages,
    expected_revision,
    expected_fubon_code,
    expected_disability_term,
    expected_disability_items,
) in FUBON_MILLION_NEW_LIFE_PRODUCTS.items():
    document = fubon_million_new_life_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    schedule = parse_fubon_million_new_life_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-million-new-life-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
    ]

    characteristics = schedule["version_characteristics"]
    assert characteristics == {
        "terms_revision": expected_revision,
        "plan_count": 5,
        "non_guaranteed_renewal": True,
        "maximum_renewal_age": 50,
        "day_hospital_explicit": True,
        "same_hospital_readmission_days": 14,
        "hospital_daily_days_limit_per_policy_year_same_hospitalization": 30,
        "accident_claim_days": 180,
        "accident_medical_limit": 30_000,
        "accident_medical_daily_formula_per_10000_inpatient_only": 70,
        "accident_medical_daily_formula_per_10000_inpatient_split": 40,
        "accident_medical_daily_formula_per_10000_outpatient_split": 20,
        "accident_medical_daily_formula_days_limit": 90,
        "death_disability_same_accident_cap": True,
        "disability_term": expected_disability_term,
        "total_disability_schedule_item_count": 7,
        "disability_schedule_item_count": expected_disability_items,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "short_term_rate_table": True,
    }

    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert all(len(plan["coverage_entries"]) == 8 for plan in plans.values())
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    plan_5_entries = {
        entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["total-disability"]["amount"] == 1_000_000
    assert plan_1_entries["hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["hospital-daily"]["calculation_basis"] == "per_day"
    assert plan_1_entries["accidental-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["accidental-disability"]["amount"] == 1_000_000
    assert plan_1_entries["accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 1_000_000,
    }
    assert plan_1_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert plan_1_entries["accident-medical-reimbursement"]["amount"] == 30_000
    assert (
        plan_1_entries["accident-medical-reimbursement"]["calculation_basis"]
        == "reimbursement_with_cap"
    )
    assert plan_1_entries["accident-medical-daily-option-a"]["amount"] == 210
    assert plan_1_entries["accident-medical-daily-option-b"]["amount"] == 120
    assert plan_1_entries["accident-medical-daily-option-b"]["amount_tiers"] == [
        {"label": "住院每日", "amount": 120},
        {"label": "門診每日", "amount": 60},
    ]
    assert (
        plan_1_entries["accident-medical-daily-option-a"]["aggregation_rule"]
        == "choose_one"
    )
    assert (
        plan_1_entries["accident-medical-daily-option-b"]["aggregation_rule"]
        == "choose_one"
    )
    assert plan_5_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_5_entries["accidental-disability"]["amount"] == 5_000_000
    assert plan_5_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }
    plan_1_json = json.dumps(plan_1_entries, ensure_ascii=False)
    assert expected_disability_term in plan_1_json
    if expected_disability_term == "失能":
        assert "殘廢" not in plan_1_json
    else:
        assert "失能" not in plan_1_json
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    source_path = (
        FUBON_MILLION_NEW_LIFE_ROOT / product_id / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_million_new_life_accident_health_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_fubon_million_new_life_accident_health_plan_table(
            fubon_million_new_life_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_fubon_million_new_life_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_million_new_life_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_million_new_life_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "每壹萬元換算住院每日柒拾元",
                    "每壹萬元換算住院每日捌拾元",
                    1,
                ),
            }
        )
        is None
    )


TAIWAN_QIANWAN_CHUXING_A_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-007"
)
TAIWAN_QIANWAN_CHUXING_A_PRODUCTS = {
    "202211MZ2A89622A11Z10000000": (
        "台灣人壽千萬出行 A 型定期傷害保險",
        "110-original",
        "none",
        "none",
        "original-filing",
        "",
    ),
    "202211MZ2A89622A11Z10000001": (
        "台灣人壽千萬出行 A 型定期傷害保險",
        "112-first-partial-revision",
        "112-02-09",
        "金管保壽字第1110152342號",
        "111-12-08-regulatory-amendment",
        "中華民國 112 年 2 月 9 日依 111 年 12 月 8 日金管保壽字第 1110152342 號函修正",
    ),
    "202211MZ2A89622A11Z10000002": (
        "台灣人壽新千萬出行 A 型定期傷害保險",
        "112-second-partial-revision",
        "112-03-01",
        "台壽字第1122320055號",
        "company-filing-amendment",
        "中華民國 112 年 3 月 1 日台壽字第 1122320055 號函備查修正",
    ),
}


def taiwan_qianwan_chuxing_a_document(
    product_id: str,
    suffix: str = "A",
    *,
    document_type: str = "policy_terms",
) -> dict:
    pdf_path = (
        TAIWAN_QIANWAN_CHUXING_A_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": document_type,
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_title,
    expected_revision,
    expected_revision_date,
    expected_revision_number,
    expected_revision_basis,
    expected_revision_signal,
) in TAIWAN_QIANWAN_CHUXING_A_PRODUCTS.items():
    document = taiwan_qianwan_chuxing_a_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 16
    assert expected_title in document["text"]
    assert "台壽字第 1102320135 號函備查" in document["text"]
    if expected_revision_signal:
        assert expected_revision_signal in document["text"]
    schedule = parse_taiwan_qianwan_chuxing_a_accident_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-qianwan-chuxing-a-accident-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    assert "保險單面頁" in schedule["selection_guidance"]
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "filing_date": "110-10-29",
        "filing_number": "台壽字第1102320135號",
        "revision_date": expected_revision_date,
        "revision_number": expected_revision_number,
        "revision_basis": expected_revision_basis,
        "maximum_coverage_age": 85,
        "death_benefit_premium_total_rate_percent": 106,
        "accident_claim_days": 180,
        "air_or_train_mass_transit_accidental_death_multiplier": 20,
        "water_or_nontrain_land_mass_transit_accidental_death_multiplier": 10,
        "automobile_passenger_accidental_death_multiplier": 5,
        "other_accidental_death_multiplier": 1,
        "major_burn_rate_percent": 20,
        "major_burn_lifetime_limit_times": 1,
        "disability_term": "失能",
        "disability_schedule_item_count": 80,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "installment_death_benefit_available": True,
    }
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-or-funeral-greater-of",
        "air-or-train-mass-transit-accidental-death",
        "water-or-nontrain-land-mass-transit-accidental-death",
        "automobile-passenger-accidental-death",
        "other-accidental-death",
        "accidental-disability",
        "major-burn",
    }
    assert entries["death-or-funeral-greater-of"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-greater-of"]["rate_percent"] == 106
    assert entries["death-or-funeral-greater-of"]["basis"] == "policy_recorded_limit"
    assert "amount" not in entries["death-or-funeral-greater-of"]
    assert (
        entries["air-or-train-mass-transit-accidental-death"]["multiplier"]
        == 20
    )
    assert (
        entries["water-or-nontrain-land-mass-transit-accidental-death"][
            "multiplier"
        ]
        == 10
    )
    assert entries["automobile-passenger-accidental-death"]["multiplier"] == 5
    assert entries["other-accidental-death"]["multiplier"] == 1
    assert entries["other-accidental-death"]["basis"] == "face_amount"
    assert entries["accidental-disability"]["rate_min_percent"] == 5
    assert entries["accidental-disability"]["rate_max_percent"] == 100
    assert entries["accidental-disability"]["aggregation_rule"] == "cumulative_cap"
    assert entries["major-burn"]["rate_percent"] == 20
    assert entries["major-burn"]["limit_scope"] == "lifetime"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

    source_path = (
        TAIWAN_QIANWAN_CHUXING_A_ROOT / product_id / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:2]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 16
    assert (
        parse_taiwan_qianwan_chuxing_a_accident_face_amount(completed_document)
        == schedule
    )
    assert (
        parse_taiwan_qianwan_chuxing_a_accident_face_amount(
            taiwan_qianwan_chuxing_a_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_a_accident_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_a_accident_face_amount(
            {**document, "page_count": 15}
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_a_accident_face_amount(
            {
                **document,
                "text": document["text"].replace(
                    "本公司另按保險金額的 20 倍給付",
                    "本公司另按保險金額的 30 倍給付",
                    1,
                ),
            }
        )
        is None
    )


TAIWAN_QIANWAN_CHUXING_B_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-009"
)
TAIWAN_QIANWAN_CHUXING_B_PRODUCTS = {
    "202121MZ2A89922A11Z10000000": (
        "台灣人壽千萬出行 B 型定期養老保險",
        "110-original",
        "none",
        "none",
        "original-filing",
        "",
    ),
    "202121MZ2A89922A11Z10000002": (
        "台灣人壽新千萬出行 B 型定期養老保險",
        "112-second-partial-revision",
        "112-03-01",
        "台壽字第1122320056號",
        "company-filing-amendment",
        "中華民國 112 年 3 月 1 日台壽字第 1122320056 號函備查修正",
    ),
}


def taiwan_qianwan_chuxing_b_document(
    product_id: str,
    suffix: str = "A",
    *,
    document_type: str = "policy_terms",
) -> dict:
    pdf_path = (
        TAIWAN_QIANWAN_CHUXING_B_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": document_type,
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_title,
    expected_revision,
    expected_revision_date,
    expected_revision_number,
    expected_revision_basis,
    expected_revision_signal,
) in TAIWAN_QIANWAN_CHUXING_B_PRODUCTS.items():
    document = taiwan_qianwan_chuxing_b_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == 16
    assert expected_title in document["text"]
    assert "台壽字第 1102320136 號函備查" in document["text"]
    if expected_revision_signal:
        assert expected_revision_signal in document["text"]
    schedule = parse_taiwan_qianwan_chuxing_b_endowment_face_amount(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-qianwan-chuxing-b-endowment-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "保險金額"
    assert "滿期取大值" in schedule["selection_guidance"]
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "filing_date": "110-10-29",
        "filing_number": "台壽字第1102320136號",
        "revision_date": expected_revision_date,
        "revision_number": expected_revision_number,
        "revision_basis": expected_revision_basis,
        "maximum_coverage_age": 85,
        "maturity_age": 85,
        "death_benefit_premium_total_rate_percent": 106,
        "maturity_benefit_premium_total_rate_percent": 106,
        "accident_claim_days": 180,
        "air_or_train_mass_transit_accidental_death_multiplier": 20,
        "water_or_nontrain_land_mass_transit_accidental_death_multiplier": 10,
        "automobile_passenger_accidental_death_multiplier": 5,
        "other_accidental_death_multiplier": 1,
        "major_burn_rate_percent": 20,
        "major_burn_lifetime_limit_times": 1,
        "disability_term": "失能",
        "disability_schedule_item_count": 80,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "installment_death_benefit_available": True,
    }
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-or-funeral-greater-of",
        "air-or-train-mass-transit-accidental-death",
        "water-or-nontrain-land-mass-transit-accidental-death",
        "automobile-passenger-accidental-death",
        "other-accidental-death",
        "accidental-disability",
        "major-burn",
        "maturity-benefit-greater-of",
    }
    assert entries["death-or-funeral-greater-of"]["calculation_basis"] == "greater_of"
    assert entries["death-or-funeral-greater-of"]["rate_percent"] == 106
    assert entries["death-or-funeral-greater-of"]["basis"] == "policy_recorded_limit"
    assert entries["maturity-benefit-greater-of"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit-greater-of"]["rate_percent"] == 106
    assert entries["maturity-benefit-greater-of"]["basis"] == "policy_recorded_limit"
    assert entries["maturity-benefit-greater-of"]["limit_scope"] == "per_policy"
    assert "amount" not in entries["maturity-benefit-greater-of"]
    assert (
        entries["air-or-train-mass-transit-accidental-death"]["multiplier"]
        == 20
    )
    assert (
        entries["water-or-nontrain-land-mass-transit-accidental-death"][
            "multiplier"
        ]
        == 10
    )
    assert entries["automobile-passenger-accidental-death"]["multiplier"] == 5
    assert entries["other-accidental-death"]["multiplier"] == 1
    assert entries["accidental-disability"]["rate_min_percent"] == 5
    assert entries["accidental-disability"]["rate_max_percent"] == 100
    assert entries["major-burn"]["rate_percent"] == 20
    assert entries["major-burn"]["limit_scope"] == "lifetime"
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

    source_path = (
        TAIWAN_QIANWAN_CHUXING_B_ROOT / product_id / f"{product_id}-A.pdf"
    )
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:2]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == 16
    assert (
        parse_taiwan_qianwan_chuxing_b_endowment_face_amount(completed_document)
        == schedule
    )
    assert (
        parse_taiwan_qianwan_chuxing_b_endowment_face_amount(
            taiwan_qianwan_chuxing_b_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_b_endowment_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_b_endowment_face_amount(
            {**document, "page_count": 15}
        )
        is None
    )
    assert (
        parse_taiwan_qianwan_chuxing_b_endowment_face_amount(
            {
                **document,
                "text": document["text"].replace(
                    "保險年齡 85 歲屆滿之年繳應繳保險費總和的 1.06 倍",
                    "保險年齡 85 歲屆滿之年繳應繳保險費總和的 1.10 倍",
                    1,
                ),
            }
        )
        is None
    )


FUBON_ANXIN_FINANCIAL_LIFE_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
FUBON_ANXIN_FINANCIAL_LIFE_PRODUCTS = {
    "209291M12G00300": (18, "102-original", "FBF1020401", "殘廢", 75, 30, 30, False, True),
    "209291M19G00201": (18, "103-first-revision", "FBF1030501", "殘廢", 75, 30, 30, True, True),
    "209291MZ9G00121A11Z10000002": (19, "104-second-revision", "FBF1040804", "殘廢", 79, 30, 30, True, True),
    "209291MZ9G00121A11Z10000003": (
        19,
        "104-third-record-shared-second-source",
        "FBF1040804",
        "殘廢",
        79,
        30,
        30,
        True,
        True,
    ),
    "209291MZ9G00121A11Z10000005": (
        19,
        "107-fifth-revision",
        "FBF1070914",
        "失能",
        79,
        0,
        0,
        True,
        False,
    ),
    "209291MZ9G00121A11Z10000006": (
        20,
        "109-sixth-revision",
        "FBF1090101",
        "失能",
        80,
        0,
        0,
        True,
        False,
    ),
    "209291MZ9G00121A11Z10000007": (
        19,
        "109-seventh-revision",
        "FBF1090901",
        "失能",
        80,
        0,
        0,
        True,
        False,
    ),
    "209291MZ9G00121A11Z10000008": (
        19,
        "111-eighth-revision",
        "FBF1111202",
        "失能",
        80,
        0,
        0,
        True,
        False,
    ),
}


def fubon_anxin_financial_life_document(
    product_id: str,
    suffix: str = "A",
) -> dict:
    pdf_path = (
        FUBON_ANXIN_FINANCIAL_LIFE_ROOT
        / product_id
        / f"{product_id}-{suffix}.pdf"
    )
    if not pdf_path.is_file() and suffix == "A":
        pdf_path = next((FUBON_ANXIN_FINANCIAL_LIFE_ROOT / product_id).glob("*-A.pdf"))
    reader = PdfReader(pdf_path, strict=False)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (
    expected_pages,
    expected_revision,
    expected_fubon_code,
    expected_disability_term,
    expected_disability_items,
    expected_cancer_waiting_days,
    expected_major_disease_waiting_days,
    expected_day_hospital_explicit,
    expected_legacy_cancer_split,
) in FUBON_ANXIN_FINANCIAL_LIFE_PRODUCTS.items():
    document = fubon_anxin_financial_life_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    assert expected_fubon_code in document["text"]
    schedule = parse_fubon_anxin_financial_life_accident_health_plan_table(
        document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-anxin-financial-life-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
    ]
    assert schedule["version_characteristics"] == {
        "terms_revision": expected_revision,
        "plan_count": 5,
        "non_guaranteed_renewal": True,
        "plan_1_3_maximum_renewal_age": 65,
        "plan_4_5_maximum_renewal_age": 70,
        "cancer_waiting_days": expected_cancer_waiting_days,
        "major_disease_waiting_days": expected_major_disease_waiting_days,
        "day_hospital_explicit": expected_day_hospital_explicit,
        "same_hospital_readmission_days": 14,
        "hospital_daily_days_limit_per_policy_year_same_hospitalization": 30,
        "icu_days_limit_per_policy_year_same_hospitalization": 30,
        "burn_center_days_limit_per_policy_year_same_hospitalization": 30,
        "accident_claim_days": 180,
        "mild_cancer_lifetime_limit_times": 1,
        "disability_term": expected_disability_term,
        "total_disability_schedule_item_count": 7,
        "disability_schedule_item_count": expected_disability_items,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "short_term_rate_table": True,
    }
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    expected_entry_counts = [2, 6, 8, 7, 7] if expected_legacy_cancer_split else [
        2,
        5,
        7,
        7,
        7,
    ]
    assert [len(plans[key]["coverage_entries"]) for key in plans] == expected_entry_counts
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    plan_2_entries = {
        entry["id"]: entry for entry in plans["plan-2"]["coverage_entries"]
    }
    plan_3_entries = {
        entry["id"]: entry for entry in plans["plan-3"]["coverage_entries"]
    }
    plan_4_entries = {
        entry["id"]: entry for entry in plans["plan-4"]["coverage_entries"]
    }
    plan_5_entries = {
        entry["id"]: entry for entry in plans["plan-5"]["coverage_entries"]
    }
    assert plan_1_entries["accidental-death-or-funeral"]["amount"] == 5_000_000
    assert plan_1_entries["accidental-disability"]["amount"] == 5_000_000
    assert plan_1_entries["accidental-disability"]["name"] == (
        f"意外{expected_disability_term}保險金"
    )
    assert plan_1_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 250_000,
    }
    assert plan_2_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_2_entries["major-disease"]["amount"] == 2_000_000
    if expected_legacy_cancer_split:
        assert plan_2_entries["major-disease"]["name"] == "特定重大疾病保險金"
        assert plan_2_entries["carcinoma-in-situ"]["amount"] == 2_000
        assert plan_2_entries["carcinoma-in-situ"]["limit_scope"] == "lifetime"
        assert plan_2_entries["carcinoma-in-situ"]["aggregation_rule"] == "cumulative_cap"
        assert plan_2_entries["malignant-cancer"]["amount"] == 2_000_000
        assert "mild-cancer" not in plan_2_entries
    else:
        assert plan_2_entries["major-disease"]["name"] == "重大疾病保險金"
        assert plan_2_entries["mild-cancer"]["amount"] == 2_000
        assert plan_2_entries["mild-cancer"]["limit_scope"] == "lifetime"
        assert plan_2_entries["mild-cancer"]["aggregation_rule"] == "cumulative_cap"
    assert plan_2_entries["general-hospital-daily"]["amount"] == 1_500
    assert plan_3_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_3_entries["major-disease"]["amount"] == 1_000_000
    if expected_legacy_cancer_split:
        assert plan_3_entries["carcinoma-in-situ"]["amount"] == 1_000
        assert plan_3_entries["malignant-cancer"]["amount"] == 1_000_000
    else:
        assert plan_3_entries["mild-cancer"]["amount"] == 1_000
    assert plan_3_entries["accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_3_entries["general-hospital-daily"]["amount"] == 1_500
    assert plan_4_entries["life-death-or-funeral"]["amount"] == 3_000_000
    assert plan_4_entries["accidental-disability"]["amount"] == 3_000_000
    assert plan_4_entries["general-hospital-daily"]["amount"] == 1_000
    assert plan_4_entries["icu-hospital-daily"]["amount"] == 2_000
    assert plan_4_entries["burn-center-hospital-daily"]["amount"] == 3_000
    assert plan_5_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_5_entries["accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_5_entries["general-hospital-daily"]["amount"] == 500
    assert plan_5_entries["icu-hospital-daily"]["amount"] == 1_000
    assert plan_5_entries["burn-center-hospital-daily"]["amount"] == 1_500
    assert all(entry["source"] == "terms" for entry in plan_3_entries.values())
    assert all(entry.get("conditions") for entry in plan_3_entries.values())

    source_path = (
        FUBON_ANXIN_FINANCIAL_LIFE_ROOT / product_id / f"{product_id}-A.pdf"
    )
    if not source_path.is_file():
        source_path = next((FUBON_ANXIN_FINANCIAL_LIFE_ROOT / product_id).glob("*-A.pdf"))
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_anxin_financial_life_accident_health_plan_table(
            completed_document
        )
        == schedule
    )
    assert (
        parse_fubon_anxin_financial_life_accident_health_plan_table(
            fubon_anxin_financial_life_document(product_id, "F")
        )
        is None
    )
    assert (
        parse_fubon_anxin_financial_life_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_anxin_financial_life_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_anxin_financial_life_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    expected_fubon_code,
                    "FBF9999999",
                ),
            }
        )
        is None
    )


TIANTIAN_ANXIN_500_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-049"
)
TIANTIAN_ANXIN_500_PRODUCTS = {
    "209291MZ2G00321A11Z10000004": (21, "107-fourth-revision"),
    "209291MZ2G00321A11Z10000005": (21, "108-fifth-revision"),
    "209291MZ2G00321A11Z10000006": (22, "109-sixth-revision"),
    "209291MZ2G00321A11Z10000007": (22, "109-seventh-revision"),
    "209291MZ2G00321A11Z10000008": (22, "111-eighth-revision"),
}


def tiantian_anxin_500_document(product_id: str) -> dict:
    pdf_path = TIANTIAN_ANXIN_500_ROOT / product_id / f"{product_id}-A.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [page.extract_text() or "" for page in reader.pages]
    return {
        "product_id": product_id,
        "file_name": pdf_path.name,
        "document_type": "policy_terms",
        "page_count": len(page_texts),
        "pages_parsed": len(page_texts),
        "text": normalize_terms_text("\n".join(page_texts)),
    }


for product_id, (expected_pages, expected_revision) in TIANTIAN_ANXIN_500_PRODUCTS.items():
    document = tiantian_anxin_500_document(product_id)
    assert document["page_count"] == document["pages_parsed"] == expected_pages
    schedule = parse_fubon_tiantian_anxin_500_accident_health_plan_table(document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-tiantian-anxin-500-accident-health-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 4
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["cancer_waiting_days"] == 0
    assert characteristics["general_hospital_days_limit"] == 90
    assert characteristics["icu_days_limit"] == 30
    assert characteristics["burn_center_hospital_days_limit"] == 30
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["fracture_claim_days"] == 180
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_lifetime_limit_times"] == 1
    assert characteristics["disability_schedule_item_count"] == 79
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
    ]
    assert len(plans["plan-1"]["coverage_entries"]) == 2
    assert len(plans["plan-2"]["coverage_entries"]) == 2
    assert len(plans["plan-3"]["coverage_entries"]) == 2
    assert len(plans["plan-4"]["coverage_entries"]) == 13
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    assert plan_1_entries["accidental-death-or-funeral"]["amount"] == 3_000_000
    assert plan_1_entries["accidental-disability"]["amount"] == 3_000_000
    assert plan_1_entries["accidental-disability"]["amount_tiers"][0] == {
        "label": "第1級 100%",
        "amount": 3_000_000,
    }
    assert plan_1_entries["accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 150_000,
    }
    plan_4_entries = {
        entry["id"]: entry for entry in plans["plan-4"]["coverage_entries"]
    }
    assert plan_4_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_4_entries["total-disability"]["amount"] == 1_000_000
    assert plan_4_entries["cancer-death"]["amount"] == 300_000
    assert plan_4_entries["cancer-surgery"]["amount"] == 30_000
    assert plan_4_entries["cancer-hospital-daily"]["amount"] == 1_000
    assert plan_4_entries["cancer-radiation-daily"]["amount"] == 1_000
    assert plan_4_entries["fracture-unhospitalized-daily"]["amount"] == 500
    assert plan_4_entries["general-hospital-daily"]["amount"] == 1_000
    assert plan_4_entries["icu-hospital-daily"]["amount"] == 2_000
    assert plan_4_entries["burn-center-hospital-daily"]["amount"] == 3_000
    assert plan_4_entries["major-burn"]["amount"] == 500_000
    assert plan_4_entries["accidental-death-or-funeral"]["amount"] == 2_000_000
    assert plan_4_entries["accidental-disability"]["amount"] == 2_000_000
    assert all(entry["source"] == "terms" for entry in plan_4_entries.values())
    assert all(entry.get("conditions") for entry in plan_4_entries.values())

    source_path = TIANTIAN_ANXIN_500_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_tiantian_anxin_500_accident_health_plan_table(completed_document)
        == schedule
    )
    assert (
        parse_fubon_tiantian_anxin_500_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_tiantian_anxin_500_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_tiantian_anxin_500_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )


FUBON_LEGACY_INJURY_TEXT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-document-text"
    / "tii-life-049-text.json"
)
fubon_legacy_injury_documents = json.loads(
    FUBON_LEGACY_INJURY_TEXT.read_text(encoding="utf-8")
)["documents"]
fubon_legacy_expected_parsers = {
    "209291M11A00300": "fubon-new-pingan-accident-legacy-plan-v1",
    "209291MZ1A00321A11Z10000001": "fubon-new-pingan-accident-legacy-plan-v1",
    "209291M12G00500": "fubon-tiantian-anxin-500-accident-health-legacy-plan-v1",
    "209291M19G00401": "fubon-tiantian-anxin-500-accident-health-legacy-plan-v1",
    "209291MZ2G00321A11Z10000002": "fubon-tiantian-anxin-500-accident-health-legacy-plan-v1",
    "209291MZ2G00321A11Z10000003": "fubon-tiantian-anxin-500-accident-health-legacy-plan-v1",
    "209291MZ1G00321A11Z10000002": "fubon-new-million-heart-accident-health-legacy-plan-v1",
    "209291MZ1G00321A11Z10000003": "fubon-new-million-heart-accident-health-legacy-plan-v1",
    "209291MZ2G00121A11Z10000006": "fubon-new-shouhu-jinnang-late-accident-health-legacy-plan-v1",
    "209291MZ9G00121A11Z10000004": "fubon-anxin-financial-life-accident-health-plan-v1",
}
for product_id, expected_parser_id in fubon_legacy_expected_parsers.items():
    document = next(
        item
        for item in fubon_legacy_injury_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    parsed = parse_plan_table_with_parser(document)
    assert parsed is not None
    parser_id, schedule = parsed
    assert parser_id == expected_parser_id
    assert schedule["selection_type"] == "plan"
    assert schedule["plan_options"]


FUBON_TRADITIONAL_LIFE_TEXT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-document-text"
    / "tii-life-051-text.json"
)
fubon_traditional_life_documents = json.loads(
    FUBON_TRADITIONAL_LIFE_TEXT.read_text(encoding="utf-8")
)["documents"]
FUBON_HAOZHOUQUAN_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-051"
)
FUBON_HAOZHOUQUAN_PRODUCTS = {
    "209191M12G00200": ("102-original", 17, "殘廢", 75),
    "209191M19G00101": ("103-first-revision", 17, "殘廢", 75),
    "209131MZ9G00121A11Z10000002": ("104-second-revision", 18, "殘廢", 79),
    "209131MZ9G00121A11Z10000003": ("105-third-revision", 18, "殘廢", 79),
    "209131MZ9G00121A11Z10000004": ("107-fourth-revision", 18, "失能", 79),
    "209131MZ9G00121A11Z10000006": ("109-sixth-revision", 18, "失能", 80),
    "209131MZ9G00121A11Z10000007": ("111-seventh-revision", 18, "失能", 80),
}

FUBON_GOLDEN_LUCK_UNIVERSAL_PRODUCT_ID = "209131MB1A00323A11Z10000005"
fubon_golden_luck_universal_document = next(
    item
    for item in fubon_traditional_life_documents
    if item["product_id"] == FUBON_GOLDEN_LUCK_UNIVERSAL_PRODUCT_ID
    and item["document_type"] == "policy_terms"
)
fubon_golden_luck_universal_schedule = (
    parse_fubon_golden_luck_universal_whole_life_formula(
        fubon_golden_luck_universal_document
    )
)
assert fubon_golden_luck_universal_schedule is not None
fubon_golden_luck_universal_integrated = parse_plan_table_with_parser(
    fubon_golden_luck_universal_document
)
assert fubon_golden_luck_universal_integrated is not None
assert fubon_golden_luck_universal_integrated[0] == (
    "fubon-golden-luck-universal-whole-life-formula-v1"
)
assert fubon_golden_luck_universal_integrated[1] == (
    fubon_golden_luck_universal_schedule
)
assert fubon_golden_luck_universal_schedule["selection_type"] == "face_amount"
assert fubon_golden_luck_universal_schedule["input_mode"] == "face_amount"
assert fubon_golden_luck_universal_schedule["selection_label"] == "保險金額"
assert fubon_golden_luck_universal_schedule["version_characteristics"] == {
    "product_family": "fubon-golden-luck-universal-whole-life",
    "terms_revision": "fifth-partial-revision",
    "fubon_code": "UWA21100701",
    "product_code": "UWA2",
    "filing_date": "106.02.24",
    "filing_number": "富壽商精字第1050004386號",
    "revision_events": [
        "107.09.14-金管保壽字第10704158370號",
        "109.01.01-金管保壽字第10804904941號",
        "109.01.01-金管保壽字第10804933330號",
        "109.07.01-富壽商精字第1090002112號",
        "109.09.01-富壽商精字第1090003802號",
        "110.07.01-富壽商精字第1100001193號",
    ],
    "universal_life_policy": True,
    "non_participating_policy": True,
    "declared_rate_frequency": "annual_policy_year_declared_month",
    "declared_rate_non_negative": True,
    "policy_value_reserve_formula": "premiums_minus_premium_fee_minus_monthly_insurance_cost_minus_reductions_plus_declared_rate_daily_simple_interest",
    "insurance_cost_deduction_frequency": "monthly",
    "premium_fee_table_required": True,
    "surrender_charge_table_required": True,
    "death_benefit_formula": "greater_of_face_amount_policy_reserve_paid_premium_total",
    "total_disability_benefit_formula": "greater_of_face_amount_policy_reserve_paid_premium_total",
    "maturity_benefit_formula": "greater_of_face_amount_policy_reserve_paid_premium_total",
    "maturity_age": 110,
    "policy_face_amount_required": True,
    "policy_reserve_required": True,
    "paid_premium_total_required": True,
    "basic_premium_supported": True,
    "flexible_additional_premium_supported": True,
    "premium_payment_ratio_schedule_required": True,
    "installment_benefit_available": True,
    "installment_period_options": [10, 20],
    "installment_interest_rate_source": "company_announced_rate_on_installment_start_date",
    "minimum_specified_insurance_amount": 200_000,
    "minimum_annual_installment_amount": 20_000,
    "guardianship_funeral_benefit_rule": True,
    "funeral_benefit_limit_rule": True,
    "disability_schedule_item_count": 7,
}
fubon_golden_luck_universal_entries = {
    entry["id"]: entry
    for entry in fubon_golden_luck_universal_schedule["coverage_entries"]
}
assert set(fubon_golden_luck_universal_entries) == {
    "policy-value-reserve-reference",
    "death-or-funeral-benefit",
    "total-disability-benefit",
    "installment-periodic-benefit",
    "maturity-benefit",
}
assert fubon_golden_luck_universal_entries["death-or-funeral-benefit"][
    "calculation_basis"
] == "greater_of"
assert fubon_golden_luck_universal_entries["total-disability-benefit"][
    "unit_key"
] == "greater_of_face_amount_policy_reserve_paid_premium_total"
assert fubon_golden_luck_universal_entries["installment-periodic-benefit"][
    "amount_role"
] == "reference"
assert fubon_golden_luck_universal_entries["maturity-benefit"]["rate_percent"] == 100
fubon_golden_luck_universal_source_path = (
    FUBON_HAOZHOUQUAN_ROOT
    / FUBON_GOLDEN_LUCK_UNIVERSAL_PRODUCT_ID
    / f"{FUBON_GOLDEN_LUCK_UNIVERSAL_PRODUCT_ID}-A.pdf"
)
fubon_golden_luck_universal_indexed = {
    key: value
    for key, value in fubon_golden_luck_universal_document.items()
    if key not in {"page_count", "pages_parsed"}
}
fubon_golden_luck_universal_indexed["text"] = (
    fubon_golden_luck_universal_indexed["text"].split("【保險契約的構成】")[0]
)
fubon_golden_luck_universal_completed = complete_strict_source_document(
    fubon_golden_luck_universal_indexed,
    fubon_golden_luck_universal_source_path,
)
assert fubon_golden_luck_universal_completed["page_count"] == 10
assert (
    parse_fubon_golden_luck_universal_whole_life_formula(
        fubon_golden_luck_universal_completed
    )
    == fubon_golden_luck_universal_schedule
)
assert parse_fubon_golden_luck_universal_whole_life_formula(
    {**fubon_golden_luck_universal_document, "product_id": "209131MB1A00323A11Z10000004"}
) is None
assert parse_fubon_golden_luck_universal_whole_life_formula(
    {**fubon_golden_luck_universal_document, "document_type": "product_summary"}
) is None
assert parse_fubon_golden_luck_universal_whole_life_formula(
    {**fubon_golden_luck_universal_document, "page_count": 9, "pages_parsed": 9}
) is None
assert parse_fubon_golden_luck_universal_whole_life_formula(
    {
        **fubon_golden_luck_universal_document,
        "text": fubon_golden_luck_universal_document["text"].replace(
            "三者之最大值",
            "二者之最大值",
        ),
    }
) is None

FUBON_HEALTH_LIMIT_UP_PRODUCTS = {
    "209191M12G00400": ("103-original", 16, 30, "殘廢", 75),
    "209191MZ2G00221A11Z10000001": ("104-first-revision", 17, 30, "殘廢", 79),
    "209191MZ2G00221A11Z10000002": ("107-second-revision", 17, 0, "殘廢", 79),
    "209191MZ2G00221A11Z10000004": ("108-fourth-revision", 17, 0, "失能", 79),
    "209191MZ2G00221A11Z10000005": ("109-fifth-revision", 17, 0, "失能", 79),
}
FUBON_NEW_MILLION_HEART_LEGACY_PRODUCTS = {
    "209191M12G00300": ("102-original", 21, "FBD1020712", 75),
    "209191M11G00101": ("103-first-revision", 21, "FBD1030501", 75),
}
ANTAI_TRADITIONAL_LIFE_TEXT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-document-text"
    / "tii-life-117-text.json"
)
antai_traditional_life_documents = json.loads(
    ANTAI_TRADITIONAL_LIFE_TEXT.read_text(encoding="utf-8")
)["documents"]

for (
    product_id,
    (
        expected_revision,
        expected_pages,
        expected_disability_term,
        expected_disability_items,
    ),
) in FUBON_HAOZHOUQUAN_PRODUCTS.items():
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_haozhouquan_accident_health_plan_table(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 3
    assert characteristics["non_guaranteed_renewal"] is True
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["general_hospital_days_limit"] == 90
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 100
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
    ]
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    assert set(plans) == {"plan-1", "plan-2", "plan-3"}
    assert all(len(plan["coverage_entries"]) == 7 for plan in schedule["plan_options"])

    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    plan_2_entries = {
        entry["id"]: entry for entry in plans["plan-2"]["coverage_entries"]
    }
    plan_3_entries = {
        entry["id"]: entry for entry in plans["plan-3"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_2_entries["life-death-or-funeral"]["amount"] == 2_000_000
    assert plan_3_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert (
        plan_1_entries["total-disability"]["name"]
        == f"完全{expected_disability_term}保險金"
    )
    assert plan_2_entries["mass-transit-accidental-death-additional"]["amount"] == 6_000_000
    assert (
        plan_2_entries["mass-transit-accidental-disability-additional"][
            "amount_tiers"
        ][0]["amount"]
        == 6_000_000
    )
    assert (
        plan_2_entries["general-accidental-disability"]["amount_tiers"][-1]
        == {"label": "第11級 5%", "amount": 100_000}
    )
    assert plan_1_entries["general-hospital-daily"]["amount"] == 1_000
    assert plan_2_entries["general-hospital-daily"]["amount"] == 2_000
    assert plan_3_entries["general-hospital-daily"]["amount"] == 2_000
    assert all(entry["source"] == "terms" for entry in plan_1_entries.values())
    assert all(entry.get("conditions") for entry in plan_1_entries.values())

    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-haozhouquan-accident-health-plan-v1"
    assert integrated[1] == schedule

    source_path = FUBON_HAOZHOUQUAN_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert parse_fubon_haozhouquan_accident_health_plan_table(completed_document) == schedule
    assert (
        parse_fubon_haozhouquan_accident_health_plan_table(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_haozhouquan_accident_health_plan_table(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_haozhouquan_accident_health_plan_table(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_haozhouquan_accident_health_plan_table(
            {
                **document,
                "text": document["text"].replace(
                    "2,000 元/日",
                    "3,000 元/日",
                ),
            }
        )
        is None
    )

for (
    product_id,
    (
        expected_revision,
        expected_pages,
        expected_cancer_waiting_days,
        expected_disability_term,
        expected_disability_items,
    ),
) in FUBON_HEALTH_LIMIT_UP_PRODUCTS.items():
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_health_limit_up_accident_health_fixed_schedule(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    assert schedule["selection_label"] == "附表一固定保險金額"
    assert "unit_fields" not in schedule
    assert "plan_options" not in schedule
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["fixed_terms_amount"] is True
    assert characteristics["non_guaranteed_renewal"] is True
    assert characteristics["maximum_renewal_age"] == 65
    assert characteristics["cancer_waiting_days"] == expected_cancer_waiting_days
    assert characteristics["general_hospital_days_limit"] == 90
    assert characteristics["icu_days_limit"] == 30
    assert characteristics["burn_center_hospital_days_limit"] == 30
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["disability_term"] == expected_disability_term
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["disability_rate_min_percent"] == 5
    assert characteristics["disability_rate_max_percent"] == 90
    assert characteristics["short_term_rate_table"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == 9
    assert entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert entries["total-disability"]["amount"] == 1_000_000
    assert entries["disease-or-accidental-disability"]["amount"] == 1_000_000
    assert entries["disease-or-accidental-disability"]["amount_tiers"][0] == {
        "label": "第2級 90%",
        "amount": 900_000,
    }
    assert entries["disease-or-accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert entries["general-hospital-daily"]["amount"] == 1_500
    assert entries["icu-hospital-daily"]["amount"] == 3_000
    assert entries["burn-center-hospital-daily"]["amount"] == 4_500
    assert entries["cancer-surgery"]["amount"] == 30_000
    assert entries["cancer-hospital-daily"]["amount"] == 1_000
    assert entries["cancer-radiation-daily"]["amount"] == 1_000
    assert all(entry["source"] == "terms" for entry in entries.values())
    assert all(entry.get("conditions") for entry in entries.values())

    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-health-limit-up-accident-health-fixed-v1"
    assert integrated[1] == schedule

    source_path = FUBON_HAOZHOUQUAN_ROOT / product_id / f"{product_id}-A.pdf"
    indexed_document = {
        key: value
        for key, value in document.items()
        if key not in {"page_count", "pages_parsed"}
    }
    indexed_document["text"] = normalize_terms_text(
        "\n".join(
            (page.extract_text() or "") for page in PdfReader(source_path).pages[:3]
        )
    )
    completed_document = complete_strict_source_document(indexed_document, source_path)
    assert completed_document["page_count"] == expected_pages
    assert (
        parse_fubon_health_limit_up_accident_health_fixed_schedule(completed_document)
        == schedule
    )
    assert (
        parse_fubon_health_limit_up_accident_health_fixed_schedule(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )
    assert (
        parse_fubon_health_limit_up_accident_health_fixed_schedule(
            {**document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_fubon_health_limit_up_accident_health_fixed_schedule(
            {**document, "page_count": expected_pages - 1}
        )
        is None
    )
    assert (
        parse_fubon_health_limit_up_accident_health_fixed_schedule(
            {
                **document,
                "text": document["text"].replace("1,500 元/日", "1,600 元/日"),
            }
        )
        is None
    )

for (
    product_id,
    (
        expected_revision,
        expected_pages,
        expected_fubon_code,
        expected_disability_items,
    ),
) in FUBON_NEW_MILLION_HEART_LEGACY_PRODUCTS.items():
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    assert expected_fubon_code in document["text"]
    assert "新放百萬心" in document["text"]
    schedule = parse_fubon_new_million_heart_accident_health_legacy_plan_table(document)
    assert schedule is not None
    assert parse_fubon_new_million_heart_accident_health_plan_table(document) is None
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-new-million-heart-accident-health-legacy-plan-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["plan_count"] == 8
    assert characteristics["non_guaranteed_renewal"] is True
    assert characteristics["maximum_renewal_age"] == 60
    assert characteristics["day_hospital_explicit"] is True
    assert characteristics["same_hospital_readmission_days"] == 14
    assert characteristics["general_hospital_days_limit"] == 90
    assert characteristics["accident_claim_days"] == 180
    assert characteristics["major_burn_rate_percent"] == 10
    assert characteristics["major_burn_survival_days"] == 15
    assert characteristics["major_burn_lifetime_limit_times"] == 1
    assert characteristics["disability_term"] == "殘廢"
    assert characteristics["disability_schedule_item_count"] == expected_disability_items
    assert characteristics["legacy_readable_validation"] is True
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
        "計畫四",
        "計畫五",
        "計畫六",
        "計畫七",
        "計畫八",
    ]
    assert all(len(plan["coverage_entries"]) == 15 for plan in schedule["plan_options"])
    plan_1_entries = {
        entry["id"]: entry for entry in schedule["plan_options"][0]["coverage_entries"]
    }
    assert plan_1_entries["total-disability"]["name"] == "完全殘廢保險金"
    assert (
        plan_1_entries["general-accidental-disability"]["name"]
        == "一般意外殘廢保險金"
    )
    assert plan_1_entries["hospital-daily"]["amount"] == 1_000
    assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == 500

for (
    product_id,
    expected_revision,
    expected_disability_count,
    expected_accident_daily,
    expected_fracture_reference,
) in (
    ("209191M12G00100", "102-second-revision", 75, 1_000, 500),
    ("209191M12G00101", "102-first-revision", 75, 1_000, 500),
    ("209191MZ2G00121A11Z10000003", "104-third-revision", 79, 1_000, 500),
    ("209191MZ2G00121A11Z10000004", "105-fourth-revision", 79, 1_000, 500),
    ("209191MZ2G00121A11Z10000005", "107-fifth-revision", 79, 1_000, 500),
    ("209191MZ2G00121A11Z10000006", "109-sixth-revision", 79, 1_000, 500),
    ("209191MZ9G00121A11Z10000001", "110-first-revision", 79, 1_005, 1_005),
    ("209191MZ9G00121A11Z10000002", "110-second-revision", 79, 1_005, 1_005),
    ("209191MZ9G00121A11Z10000003", "110-third-revision", 79, 1_005, 1_005),
):
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_xinfu_life_accident_health_plan_table(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["version_characteristics"]["terms_revision"] == expected_revision
    assert schedule["version_characteristics"]["disability_schedule_item_count"] == expected_disability_count
    expected_total_disability_term = (
        "完全失能"
        if product_id
        in {
            "209191MZ2G00121A11Z10000005",
            "209191MZ2G00121A11Z10000006",
        }
        else "完全殘廢"
    )
    expected_disability_term = (
        "失能"
        if product_id
        in {
            "209191MZ2G00121A11Z10000005",
            "209191MZ2G00121A11Z10000006",
        }
        else "殘廢"
    )
    assert (
        schedule["version_characteristics"]["total_disability_term"]
        == expected_total_disability_term
    )
    assert schedule["version_characteristics"]["disability_term"] == expected_disability_term
    assert [plan["label"] for plan in schedule["plan_options"]] == [
        "計畫一",
        "計畫二",
        "計畫三",
    ]
    assert all(len(plan["coverage_entries"]) == 28 for plan in schedule["plan_options"])
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    plan_3_entries = {
        entry["id"]: entry for entry in plans["plan-3"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 500_000
    assert (
        plan_1_entries["total-disability"]["name"]
        == f"{expected_total_disability_term}保險金"
    )
    assert (
        plan_1_entries["general-accidental-disability"]["name"]
        == f"一般意外{expected_disability_term}保險金"
    )
    assert plan_1_entries["cancer-surgery"]["amount"] == 10_000
    assert plan_1_entries["accident-hospital-daily"]["amount"] == expected_accident_daily
    assert plan_1_entries["accident-icu-hospital-daily"]["amount"] == expected_accident_daily
    assert plan_1_entries["fracture-unhospitalized-medical"]["amount"] == expected_fracture_reference
    assert plan_1_entries["general-accidental-disability"]["amount_tiers"][-1] == {
        "label": "第11級 5%",
        "amount": 50_000,
    }
    assert plan_3_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_3_entries["cancer-death"]["amount"] == 300_000
    assert plan_3_entries["air-transit-accidental-death-additional"]["amount"] == 4_000_000
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-xinfu-life-accident-health-plan-v1"

FUBON_GOLDEN_GUARD_PRODUCTS = (
    ("209131MZ9G00521A11Z10000000", "108-original", "MGB21080304"),
    ("209131MZ9G00521A11Z10000001", "109-first-revision", "MGB21090101"),
)
fubon_golden_guard_schedules = {}
for product_id, expected_revision, expected_code in FUBON_GOLDEN_GUARD_PRODUCTS:
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    assert expected_code in normalize_terms_text(document["text"])
    schedule = parse_fubon_golden_guard_accident_health_plan_table(document)
    assert schedule is not None
    fubon_golden_guard_schedules[product_id] = schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "投保計畫別"
    assert [plan["label"] for plan in schedule["plan_options"]] == ["計畫一", "計畫二"]
    assert [len(plan["coverage_entries"]) for plan in schedule["plan_options"]] == [20, 20]
    characteristics = schedule["version_characteristics"]
    assert characteristics == {
        "terms_revision": expected_revision,
        "plan_count": 2,
        "guaranteed_renewal": True,
        "maximum_renewal_age": 75,
        "cancer_waiting_days": 30,
        "cancer_classification": "2018-three-tier",
        "cancer_discharge_recovery_days_limit": 21,
        "cancer_radiation_days_limit_per_policy_year": 60,
        "cancer_chemotherapy_days_limit_per_policy_year": 60,
        "accident_claim_days": 180,
        "major_burn_survival_days": 15,
        "disability_term": "失能",
        "disability_schedule_item_count": 80,
        "disability_rate_min_percent": 5,
        "disability_rate_max_percent": 100,
        "short_term_rate_table": True,
    }
    plans = {plan["value"]: plan for plan in schedule["plan_options"]}
    plan_1_entries = {
        entry["id"]: entry for entry in plans["plan-1"]["coverage_entries"]
    }
    plan_2_entries = {
        entry["id"]: entry for entry in plans["plan-2"]["coverage_entries"]
    }
    assert plan_1_entries["life-death-or-funeral"]["amount"] == 500_000
    assert plan_2_entries["life-death-or-funeral"]["amount"] == 1_000_000
    assert plan_1_entries["one-to-three-disability"]["amount_tiers"] == [
        {"label": "第1級 100%", "amount": 500_000},
        {"label": "第2級 90%", "amount": 450_000},
        {"label": "第3級 80%", "amount": 400_000},
    ]
    assert plan_2_entries["one-to-three-disability"]["amount_tiers"] == [
        {"label": "第1級 100%", "amount": 1_000_000},
        {"label": "第2級 90%", "amount": 900_000},
        {"label": "第3級 80%", "amount": 800_000},
    ]
    assert plan_2_entries["general-accidental-death"]["amount"] == 1_000_000
    assert (
        plan_2_entries["air-transit-accidental-death-additional"]["amount"]
        == 2_000_000
    )
    assert plan_2_entries["major-burn"]["amount"] == 400_000
    assert plan_2_entries["cancer-surgery"]["amount"] == 30_000
    assert plan_2_entries["cancer-hospital-daily"]["amount"] == 1_000
    assert plan_2_entries["cancer-discharge-recovery-daily"]["limit_scope"] == "per_day"
    assert plan_2_entries["cancer-radiation-daily"]["amount"] == 1_000
    assert plan_2_entries["cancer-chemotherapy-daily"]["amount"] == 1_000
    assert (
        plan_2_entries["general-accidental-disability"]["amount_tiers"][-1]
        == {"label": "第11級 5%", "amount": 50_000}
    )
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-golden-guard-accident-health-plan-v1"

    source_path = FUBON_HAOZHOUQUAN_ROOT / product_id / f"{product_id}-A.pdf"
    completed_document = complete_strict_source_document(document, source_path)
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 20
    assert parse_fubon_golden_guard_accident_health_plan_table(completed_document) == (
        schedule
    )

fubon_golden_guard_summary = next(
    item
    for item in fubon_traditional_life_documents
    if item["product_id"] == "209131MZ9G00521A11Z10000001"
    and item["document_type"] == "product_summary"
)
assert parse_fubon_golden_guard_accident_health_plan_table(fubon_golden_guard_summary) is None
assert parse_plan_table_with_parser(fubon_golden_guard_summary) is None
fubon_golden_guard_revision = next(
    item
    for item in fubon_traditional_life_documents
    if item["product_id"] == "209131MZ9G00521A11Z10000001"
    and item["document_type"] == "policy_terms"
)
assert parse_fubon_golden_guard_accident_health_plan_table(
    {**fubon_golden_guard_revision, "product_id": "209131MZ9G00521A11Z10000002"}
) is None
assert parse_fubon_golden_guard_accident_health_plan_table(
    {
        **fubon_golden_guard_revision,
        "file_name": "209131MZ9G00521A11Z10000001-F.pdf",
    }
) is None
guard_text = normalize_terms_text(fubon_golden_guard_revision["text"])
assert "身故保險金或喪葬費用保險金 50 萬 100 萬" in guard_text
assert "重大燒燙傷保險金 40 萬" in guard_text
assert parse_fubon_golden_guard_accident_health_plan_table(
    {
        **fubon_golden_guard_revision,
        "text": guard_text.replace(
            "身故保險金或喪葬費用保險金 50 萬 100 萬",
            "身故保險金或喪葬費用保險金 60 萬 100 萬",
            1,
        ),
    }
) is None
assert parse_fubon_golden_guard_accident_health_plan_table(
    {
        **fubon_golden_guard_revision,
        "text": guard_text.replace("重大燒燙傷保險金 40 萬", "重大燒燙傷保險金 45 萬", 1),
    }
) is None

for product_id, expected_revision, expected_total_disability_term, expected_hospital_total_limit in (
    ("252197M12B00100", "83-original", "完全殘廢", 450_000),
    ("252197M12B00201", "95-first-revision", "完全殘廢", 450_000),
    ("209197M12B00105", "99-fifth-revision", "完全殘廢", None),
    ("209197M12B00106", "100-sixth-revision", "完全殘廢", None),
    ("209193M11B00107", "101-seventh-revision", "完全殘廢", None),
    ("209197M12B00107", "101-seventh-revision", "完全殘廢", None),
    ("209193MZ1B00121A11Z10000008", "eighth-revision", "完全失能", None),
    ("209193MZ1B00121A11Z10000009", "ninth-revision", "完全失能", None),
    ("209193MZ1B00121A11Z10000010", "tenth-revision", "完全失能", None),
    ("209193MZ1B00121A11Z10000011", "eleventh-revision", "完全失能", None),
    ("209193MZ1B00121A11Z10000012", "twelfth-revision", "完全失能", None),
    ("209193MZ1B00121A11Z10000013", "thirteenth-revision", "完全失能", None),
    ("252197M12B00202", "100-second-revision", "完全殘廢", None),
    ("252197M12B00203", "101-third-revision", "完全殘廢", None),
):
    document = next(
        item
        for item in fubon_traditional_life_documents + antai_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_tzu_chi_marrow_group_life_medical_table(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == f"身故/{expected_total_disability_term}保險金額"
    assert schedule["version_characteristics"]["terms_revision"] == expected_revision
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    expected_entry_count = 7 if expected_hospital_total_limit else 6
    assert len(entries) == len(schedule["coverage_entries"]) == expected_entry_count
    assert entries["life-death-face-amount"]["rate_percent"] == 100
    assert entries["life-death-face-amount"]["unit_key"] == "face_amount"
    assert (
        entries["total-disability-face-amount"]["name"]
        == f"{expected_total_disability_term}保險金"
    )
    assert entries["hospital-room-daily-limit"]["amount"] == 2_000
    assert entries["hospital-surgery-fee-base"]["amount"] == 43_200
    assert entries["hospital-surgery-fee-base"]["rate_max_percent"] == 220
    assert entries["hospital-miscellaneous-limit"]["amount"] == 68_000
    if expected_hospital_total_limit:
        assert (
            schedule["version_characteristics"]["hospital_total_limit"]
            == expected_hospital_total_limit
        )
        assert entries["hospitalization-total-limit"]["amount"] == expected_hospital_total_limit
    else:
        assert "hospital_total_limit" not in schedule["version_characteristics"]
        assert "hospitalization-total-limit" not in entries
    assert entries["hospital-allowance-without-original-receipt"]["amount"] == 2_000
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-tzu-chi-marrow-group-life-medical-face-amount-v1"


for product_id, expected_revision, expected_supervision_wording in (
    (
        "209131MZ1A01813A12Z10000000",
        "105-original",
        "mental-disability-or-cognitive-defect",
    ),
    (
        "209131MZ1A01823A12Z10000001",
        "106-first-partial-revision",
        "mental-disability-or-cognitive-defect",
    ),
    (
        "209131MZ1A01823A12Z10000002",
        "107-second-partial-revision",
        "adult-guardianship-not-revoked",
    ),
):
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_changanbao_life_service_face_amount(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    version = schedule["version_characteristics"]
    assert version["terms_revision"] == expected_revision
    assert version["service_plan_count"] == 7
    assert version["service_unavailable_compensation"] == 5_000
    assert version["supervision_wording"] == expected_supervision_wording
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 6
    service_entry = entries["life-funeral-service-plan-table"]
    assert service_entry["amount"] == 210_000
    assert service_entry["calculation_basis"] == "tiered_or_stepped"
    assert [tier["amount"] for tier in service_entry["amount_tiers"]] == [
        210_000,
        670_000,
        630_000,
        622_000,
        582_000,
        575_000,
        535_000,
    ]
    assert "福田妙國" in service_entry["amount_tiers"][1]["label"]
    assert entries["death-first-policy-year-annual-face-amount-reference"]["rate_percent"] == 20
    assert entries["death-second-policy-year-annual-face-amount-reference"]["rate_percent"] == 40
    assert entries["death-after-third-year-cash-benefit"]["rate_percent"] == 100
    assert entries["maturity-age-110-benefit"]["rate_percent"] == 100
    assert entries["service-unavailable-compensation"]["amount"] == 5_000
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-changanbao-life-service-face-amount-v1"
    assert (
        parse_fubon_changanbao_life_service_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )


for product_id, expected_revision, expected_code, expected_revision_number in (
    (
        "209131MZ1A02523A12Z10000000",
        "108-original",
        "XMB1080701",
        "none",
    ),
    (
        "209131MZ1A02523A12Z10000002",
        "109-second-partial-revision",
        "XMB1090901",
        "金管保壽字第1090423012號",
    ),
):
    document = next(
        item
        for item in fubon_traditional_life_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_fubon_yongai_life_service_face_amount(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    version = schedule["version_characteristics"]
    assert version["terms_revision"] == expected_revision
    assert version["fubon_code"] == expected_code
    assert version["revision_number"] == expected_revision_number
    assert version["service_provider"] == "龍巖股份有限公司"
    assert version["life_service_from_policy_year"] == 3
    assert version["service_scope_taiwan_main_island"] is True
    assert version["life_service_not_cash_convertible"] is True
    assert version["service_unavailable_compensation"] == 5_000
    assert version["service_shortfall_compensation_rate_percent"] == 110
    assert version["maturity_age"] == 110
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 8
    assert entries["life-funeral-service"]["rate_percent"] == 100
    assert entries["life-funeral-service"]["amount_role"] == "reference"
    assert entries["death-first-two-policy-years-greater-of"]["calculation_basis"] == "greater_of"
    assert entries["death-first-policy-year-annual-face-amount-reference"]["rate_percent"] == 20
    assert entries["death-second-policy-year-annual-face-amount-reference"]["rate_percent"] == 40
    assert entries["death-after-third-year-service-exception"]["rate_percent"] == 100
    assert entries["maturity-age-110-benefit"]["rate_percent"] == 100
    assert entries["service-unavailable-compensation"]["amount"] == 5_000
    assert entries["service-shortfall-price-difference-compensation"]["rate_percent"] == 110
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "fubon-yongai-life-service-face-amount-v1"
    assert (
        parse_fubon_yongai_life_service_face_amount(
            {**document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )


for product_id, expected_revision, expected_service_amount in (
    ("202131RZ2A81523A12Z10000000", "original", 210_000),
    ("202131RZ2A81523A12Z10000001", "first-partial-revision", 210_000),
    ("202131RZ2A81523A12Z10000002", "second-partial-revision", 210_000),
    ("202131RZ2A81523A12Z10000003", "third-partial-revision", 240_000),
    ("202131RZ2A81523A12Z10000004", "fourth-partial-revision", 240_000),
    ("202131RZ2A81523A12Z10000005", "fifth-partial-revision", 240_000),
):
    document = next(
        item
        for item in TII_LIFE_009_TEXT_FIXTURE
        if item["product_id"] == product_id
        and item["document_type"] == "policy_terms"
    )
    schedule = parse_taiwan_funeral_service_rider_fixed(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "fixed"
    version = schedule["version_characteristics"]
    assert version["terms_revision"] == expected_revision
    assert version["service_provider"] == "龍巖股份有限公司"
    assert version["service_option_count"] == 2
    assert version["service_amount"] == expected_service_amount
    assert version["funeral_service_from_policy_year"] == 4
    assert version["cash_conversion_allowed"] is False
    assert version["non_attributable_unavailable_cash_rate_percent"] == 100
    assert version["attributable_unavailable_cash_rate_percent"] == 110
    assert version["first_three_policy_year_death_premium_multiplier"] == 1.06
    assert version["accidental_death_amount"] == 100_000
    assert version["accidental_death_max_age"] == 85
    assert version["accident_claim_days"] == 180
    assert version["maturity_age"] == 111
    assert version["funeral_benefit_limit_rule"] is True
    assert version["fixed_terms_amount"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 6
    assert entries["funeral-service-benefit"]["amount"] == expected_service_amount
    assert entries["funeral-service-benefit"]["amount_role"] == "reference"
    assert entries["funeral-service-benefit"]["calculation_basis"] == "fixed_amount"
    assert entries["death-first-three-policy-years"]["rate_percent"] == 106
    assert (
        entries["death-first-three-policy-years"]["unit_key"]
        == "annual_premium_total"
    )
    assert (
        entries["death-after-fourth-policy-year-service-exception"]["amount"]
        == expected_service_amount
    )
    assert (
        entries["service-unavailable-company-fault-cash-benefit"]["amount"]
        == expected_service_amount * 11 // 10
    )
    assert entries["accidental-death-before-85"]["amount"] == 100_000
    assert (
        entries["accidental-death-before-85"]["aggregation_rule"]
        == "conditional_additive"
    )
    assert entries["maturity-age-111-benefit"]["amount"] == expected_service_amount
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-funeral-service-rider-fixed-v1"
    assert (
        parse_taiwan_funeral_service_rider_fixed(
            {
                **document,
                "file_name": f"{product_id}-F.pdf",
                "document_type": "product_summary",
            }
        )
        is None
    )


for product_id, expected_revision, expected_supervision in (
    ("202131MZ1A62623A12Z10000000", "original", "mental-disorder"),
    (
        "202131MZ1A62623A12Z10000001",
        "first-regulatory-revision",
        "guardianship",
    ),
):
    document = next(
        item
        for item in TII_LIFE_009_TEXT_FIXTURE
        if item["product_id"] == product_id
        and item["document_type"] == "policy_terms"
    )
    schedule = parse_taiwan_funeral_service_whole_life_early_plan(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "保險金額對應投保方案"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["service_provider"] == "龍巖股份有限公司"
    assert characteristics["service_plan_count"] == 19
    assert characteristics["funeral_service_amount"] == 210_000
    assert characteristics["tower_plan_count"] == 18
    assert characteristics["funeral_service_from_policy_year"] == 3
    assert characteristics["cash_conversion_allowed"] is False
    assert characteristics["non_attributable_unavailable_cash_rate_percent"] == 100
    assert characteristics["attributable_unavailable_cash_rate_percent"] == 110
    assert characteristics["first_policy_year_face_amount_rate_percent"] == 20
    assert characteristics["second_policy_year_face_amount_rate_percent"] == 40
    assert characteristics["maturity_age"] == 111
    assert characteristics["plan_price_includes_funeral_service"] is True
    assert characteristics["service_scope_taiwan_main_island"] is True
    assert characteristics["service_plan_amounts_fixed_from_table"] is True
    assert characteristics["death_cash_uses_policy_reserve_floor"] is True
    assert characteristics["funeral_benefit_limit_rule"] is True
    assert characteristics["supervision_wording"] == expected_supervision
    plans = schedule["plan_options"]
    assert len(plans) == 19
    assert plans[0]["value"] == "plan-1"
    assert plans[0]["label"] == "方案一：殯葬服務"
    assert plans[1]["label"] == "方案二：殯葬服務 + 塔位 1"
    assert plans[-1]["label"] == "方案十九：殯葬服務 + 塔位 18"
    assert [plan["coverage_entries"][0]["amount"] for plan in plans] == [
        210_000,
        1_218_000,
        1_118_000,
        848_000,
        788_000,
        670_000,
        630_000,
        622_000,
        582_000,
        575_000,
        535_000,
        425_000,
        405_000,
        396_000,
        376_000,
        380_000,
        360_000,
        375_000,
        355_000,
    ]
    plan_one_entries = {entry["id"]: entry for entry in plans[0]["coverage_entries"]}
    assert len(plan_one_entries) == len(plans[0]["coverage_entries"]) == 7
    assert (
        plan_one_entries["funeral-service-or-bone-tower-plan-benefit"]["amount"]
        == 210_000
    )
    assert plan_one_entries["death-first-policy-year"]["amount"] == 42_000
    assert plan_one_entries["death-first-policy-year"]["rate_percent"] == 20
    assert (
        plan_one_entries["death-first-policy-year"]["calculation_basis"]
        == "greater_of"
    )
    assert (
        plan_one_entries["death-first-policy-year"]["unit_key"]
        == "face_amount_or_policy_reserve"
    )
    assert plan_one_entries["death-second-policy-year"]["amount"] == 84_000
    assert plan_one_entries["death-second-policy-year"]["rate_percent"] == 40
    assert (
        plan_one_entries["death-after-third-policy-year-service-exception"][
            "amount"
        ]
        == 210_000
    )
    assert plan_one_entries["non-attributable-unavailable-cash"]["amount"] == 210_000
    assert plan_one_entries["company-fault-unavailable-cash"]["amount"] == 231_000
    assert plan_one_entries["maturity-age-111-benefit"]["amount"] == 210_000
    plan_two_entries = {entry["id"]: entry for entry in plans[1]["coverage_entries"]}
    assert plan_two_entries["death-first-policy-year"]["amount"] == 243_600
    assert plan_two_entries["death-second-policy-year"]["amount"] == 487_200
    assert plan_two_entries["company-fault-unavailable-cash"]["amount"] == 1_339_800
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-funeral-service-whole-life-early-plan-v1"
    assert (
        parse_taiwan_funeral_service_whole_life_early_plan(
            {
                **document,
                "file_name": f"{product_id}-F.pdf",
                "document_type": "product_summary",
            }
        )
        is None
    )
    assert (
        parse_taiwan_funeral_service_whole_life_early_plan(
            {**document, "product_id": "not-this-product"}
        )
        is None
    )


for product_id, expected_revision in (
    ("202131MZ1A58413A12Z10000000", "original"),
    ("202131MZ1A58423A12Z10000001", "first-partial-revision"),
    ("202131MZ1A58423A12Z10000002", "second-partial-revision"),
    ("202131MZ1A58423A12Z10000003", "third-partial-revision"),
):
    document = next(
        item
        for item in TII_LIFE_009_TEXT_FIXTURE
        if item["product_id"] == product_id
        and item["document_type"] == "policy_terms"
    )
    schedule = parse_taiwan_funeral_service_whole_life_early_tower_plan(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    assert schedule["selection_label"] == "骨灰塔位指定選項"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["service_provider"] == "龍巖股份有限公司"
    assert characteristics["funeral_service_option_count"] == 2
    assert characteristics["funeral_service_amount"] == 193_200
    assert characteristics["tower_table_row_count"] == 9
    assert characteristics["tower_option_count"] == 18
    assert characteristics["tower_table_revision"] == "early-two-layer"
    assert characteristics["funeral_service_from_policy_year"] == 3
    assert characteristics["cash_conversion_allowed_for_disability_or_maturity"] is True
    assert characteristics["cash_conversion_allowed_for_death_exceptions"] is True
    assert characteristics["non_attributable_unavailable_cash_rate_percent"] == 100
    assert characteristics["attributable_unavailable_cash_rate_percent"] == 110
    assert characteristics["maturity_age"] == 111
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["premium_waiver_disability_grade_min"] == 2
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["plan_price_includes_funeral_service"] is True
    assert characteristics["plan_price_deducted_from_life_cash_benefits"] is True
    assert characteristics["service_scope_taiwan_main_island"] is True
    assert characteristics["service_plan_amounts_fixed_from_table"] is True
    assert characteristics["premium_total_wording"] == "premium_total"
    assert characteristics["disability_terminology"] == "完全殘廢"
    plans = schedule["plan_options"]
    assert len(plans) == 18
    assert plans[0]["value"] == "tower-1-low-high"
    assert plans[0]["label"].endswith("高低層別")
    assert plans[1]["value"] == "tower-1-middle"
    assert plans[1]["label"].endswith("中層別")
    assert plans[-1]["value"] == "tower-9-middle"
    assert [plan["coverage_entries"][0]["amount"] for plan in plans] == [
        1_016_200,
        1_106_200,
        719_200,
        773_200,
        576_200,
        612_200,
        530_200,
        566_200,
        489_200,
        525_200,
        370_200,
        388_200,
        344_200,
        362_200,
        329_200,
        347_200,
        324_200,
        342_200,
    ]
    entries = {entry["id"]: entry for entry in plans[0]["coverage_entries"]}
    assert len(entries) == len(plans[0]["coverage_entries"]) == 11
    assert entries["funeral-service-or-bone-tower-plan-benefit"]["amount"] == 1_016_200
    assert (
        entries["death-after-third-policy-year-cash-balance"]["unit_key"]
        == "face_amount_or_reserve_or_premium_total_minus_plan_price"
    )
    assert entries["death-cash-conversion-exception"]["amount"] == 1_016_200
    assert (
        entries["total-disability-first-two-policy-years"]["name"]
        == "第一至第二保單年度完全殘廢保險金"
    )
    assert "完全失能" not in entries["total-disability-first-two-policy-years"]["name"]
    assert (
        entries["premium-waiver-disability-grade-two-to-six"]["name"]
        == "第二至第六級殘廢豁免保險費"
    )
    assert (
        entries["company-fault-funeral-service-unavailable-cash"]["amount"]
        == 212_520
    )
    assert entries["company-fault-bone-tower-unavailable-cash"]["amount"] == 905_300
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-funeral-service-whole-life-early-tower-v1"
    assert (
        parse_taiwan_funeral_service_whole_life_early_tower_plan(
            {
                **document,
                "file_name": f"{product_id}-F.pdf",
                "document_type": "product_summary",
            }
        )
        is None
    )


for product_id, expected_revision, expected_service_amount, expected_premium_wording in (
    ("202131MZ1A58423A12Z10000005", "fifth-partial-revision", 210_000, "premium_total"),
    ("202131MZ1A58423A12Z10000006", "sixth-partial-revision", 210_000, "annual_premium_total"),
    ("202131MZ1A58423A12Z10000008", "eighth-partial-revision", 210_000, "annual_premium_total"),
    ("202131MZ1A58423A12Z10000009", "ninth-partial-revision", 210_000, "annual_premium_total"),
    ("202131MZ1A58423A12Z10000010", "tenth-partial-revision", 240_000, "annual_premium_total"),
    ("202131MZ1A58423A12Z10000011", "eleventh-partial-revision", 240_000, "annual_premium_total"),
):
    document = next(
        item
        for item in TII_LIFE_009_TEXT_FIXTURE
        if item["product_id"] == product_id
        and item["document_type"] == "policy_terms"
    )
    schedule = parse_taiwan_funeral_service_whole_life_plan(document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "plan"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["service_provider"] == "龍巖股份有限公司"
    assert characteristics["service_plan_count"] == 11
    assert characteristics["funeral_service_amount"] == expected_service_amount
    assert characteristics["tower_plan_count"] == 10
    assert characteristics["funeral_service_from_policy_year"] == 3
    assert characteristics["cash_conversion_allowed_for_disability_or_maturity"] is True
    assert characteristics["cash_conversion_allowed_for_death_exceptions"] is True
    assert characteristics["non_attributable_unavailable_cash_rate_percent"] == 100
    assert characteristics["attributable_unavailable_cash_rate_percent"] == 110
    assert characteristics["maturity_age"] == 111
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["premium_waiver_disability_grade_min"] == 2
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["plan_price_includes_funeral_service"] is True
    assert characteristics["plan_price_deducted_from_life_cash_benefits"] is True
    assert characteristics["service_scope_taiwan_main_island"] is True
    assert characteristics["service_plan_amounts_fixed_from_table"] is True
    assert characteristics["premium_total_wording"] == expected_premium_wording
    plans = schedule["plan_options"]
    assert len(plans) == 11
    assert plans[0]["value"] == "plan-1"
    assert plans[0]["label"] == "方案一：殯葬服務"
    assert plans[0]["coverage_entries"][0]["amount"] == expected_service_amount
    assert [plan["coverage_entries"][0]["amount"] for plan in plans] == (
        [
            210_000,
            1_274_000,
            1_162_000,
            669_000,
            624_000,
            647_000,
            602_000,
            583_000,
            543_000,
            393_000,
            373_000,
        ]
        if expected_service_amount == 210_000
        else [
            240_000,
            1_304_000,
            1_192_000,
            699_000,
            654_000,
            677_000,
            632_000,
            613_000,
            573_000,
            423_000,
            403_000,
        ]
    )
    plan_one_entries = {entry["id"]: entry for entry in plans[0]["coverage_entries"]}
    assert len(plan_one_entries) == len(plans[0]["coverage_entries"]) == 10
    assert (
        plan_one_entries["funeral-service-or-bone-tower-plan-benefit"]["amount_role"]
        == "reference"
    )
    assert (
        plan_one_entries["death-first-two-policy-years"]["calculation_basis"]
        == "greater_of"
    )
    assert (
        plan_one_entries["death-after-third-policy-year-cash-balance"]["unit_key"]
        == "face_amount_or_reserve_or_premium_total_minus_plan_price"
    )
    assert (
        plan_one_entries["death-cash-conversion-exception"]["amount"]
        == expected_service_amount
    )
    assert (
        plan_one_entries["company-fault-funeral-service-unavailable-cash"]["amount"]
        == expected_service_amount * 11 // 10
    )
    assert (
        plan_one_entries["premium-waiver-disability-grade-two-to-six"][
            "calculation_basis"
        ]
        == "unknown"
    )
    plan_two_entries = {entry["id"]: entry for entry in plans[1]["coverage_entries"]}
    assert len(plan_two_entries) == len(plans[1]["coverage_entries"]) == 11
    assert (
        plan_two_entries["company-fault-bone-tower-unavailable-cash"]["amount"]
        == 1_064_000 * 11 // 10
    )
    integrated = parse_plan_table_with_parser(document)
    assert integrated is not None
    assert integrated[0] == "taiwan-funeral-service-whole-life-plan-v1"
    assert (
        parse_taiwan_funeral_service_whole_life_plan(
            {
                **document,
                "file_name": f"{product_id}-F.pdf",
                "document_type": "product_summary",
            }
        )
        is None
    )


CHINA_LIFE_JINHAOYI_TEXT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-document-text"
    / "tii-life-025-text.json"
)
china_life_jinhaoyi_documents = json.loads(
    CHINA_LIFE_JINHAOYI_TEXT.read_text(encoding="utf-8")
)["documents"]
for product_id in (
    "205291M12A00104",
    "205291M12A00105",
    "205291M12A00106",
):
    document = next(
        item
        for item in china_life_jinhaoyi_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    schedule = parse_china_life_jinhaoyi_face_amount(document)
    assert schedule is not None
    assert schedule["selection_type"] == "face_amount"
    assert schedule["input_mode"] == "face_amount"
    assert schedule["version_characteristics"]["disability_schedule_item_count"] == 69
    assert len(china_life_jinhaoyi_disability_percentages(document["text"])) == 69
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == 12
    assert entries["major-burn"]["rate_percent"] == 30
    assert entries["aviation-accidental-death-face-amount"]["rate_percent"] == 300
    assert entries["accidental-disability-rate-table"]["rate_min_percent"] == 5
    assert entries["accidental-disability-rate-table"]["rate_max_percent"] == 90
    assert entries["maturity-premium-formula"]["calculation_basis"] == "unknown"
    assert (
        parse_china_life_jinhaoyi_face_amount(
            {**document, "document_type": "product_summary"}
        )
        is None
    )


CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_TEXT = (
    Path(__file__).resolve().parents[1]
    / "work"
    / "tii-document-text"
    / "tii-life-027-text.json"
)
CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT = (
    Path(__file__).resolve().parents[1] / "work" / "tii-documents" / "tii-life-027"
)
china_life_foreign_currency_interest_documents = json.loads(
    CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_TEXT.read_text(encoding="utf-8")
)["documents"]
china_life_xinhaoyi_expected = {
    "205191M12A00100": ("100-original", False, "none"),
    "205191M12A00101": (
        "100-first-partial-revision",
        True,
        "中壽商發字第1000328001號",
    ),
}
for product_id, (
    expected_revision,
    expected_injury_surrender_refund,
    expected_revision_number,
) in china_life_xinhaoyi_expected.items():
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_xinhaoyi_face_amount(completed_document)
    assert schedule is not None
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    version = schedule["version_characteristics"]
    assert version["terms_revision"] == expected_revision
    assert version["revision_number"] == expected_revision_number
    assert version["special_multiplier_payment_period"] == 1.1
    assert version["special_multiplier_after_payment_period"] == 0.6
    assert version["paid_premium_interest_rate_percent"] == 2.5
    assert version["land_or_water_traffic_multiplier"] == 3
    assert version["aviation_multiplier"] == 5
    assert version["survival_rate_percent"] == 50
    assert version["maturity_rate_percent"] == 60
    assert version["maturity_age"] == 91
    assert (
        version["nonaccident_injury_surrender_value_refund"]
        is expected_injury_surrender_refund
    )
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert len(entries) == len(schedule["coverage_entries"]) == 14
    assert entries["land-water-traffic-accidental-death-face-amount"]["rate_percent"] == 300
    assert entries["aviation-accidental-death-face-amount"]["rate_percent"] == 500
    assert entries["land-water-total-disability-face-amount"]["rate_percent"] == 300
    assert entries["aviation-total-disability-face-amount"]["rate_percent"] == 500
    assert entries["land-water-disability-rate-table"]["rate_min_percent"] == 15
    assert entries["land-water-disability-rate-table"]["rate_max_percent"] == 270
    assert entries["aviation-disability-rate-table"]["rate_min_percent"] == 25
    assert entries["aviation-disability-rate-table"]["rate_max_percent"] == 450
    assert entries["major-burn"]["rate_percent"] == 30
    assert entries["survival-benefit-paid-premium-formula"]["rate_percent"] == 50
    assert entries["maturity-age-91-benefit"]["rate_percent"] == 60
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert integrated[0] == "china-life-xinhaoyi-face-amount-v1"
    assert (
        parse_china_life_xinhaoyi_face_amount(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_xinhaoyi_face_amount(
            {**completed_document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )

china_life_foreign_currency_interest_expected = {
    "205121MA1A01023B11Z10000000": ("meishi-usd-106-original", "USD", [4], 2.2),
    "205121MA1A01123J11Z10000000": ("minwang-cny-107-original", "CNY", [4, 6], 2),
}
for product_id, (
    expected_revision,
    expected_currency,
    expected_payment_periods,
    expected_survival_rate,
) in china_life_foreign_currency_interest_expected.items():
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_foreign_currency_interest_whole_life_formula(
        completed_document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert (
        integrated[0]
        == "china-life-foreign-currency-interest-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["currency"] == expected_currency
    assert characteristics["payment_period_options"] == expected_payment_periods
    assert characteristics["survival_rate_percent"] == expected_survival_rate
    assert characteristics["maturity_age"] == 110
    assert characteristics["foreign_currency_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "survival-benefit",
        "maturity-benefit",
        "minor-premium-refund-with-interest",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["survival-benefit"]["rate_percent"] == expected_survival_rate
    assert entries["maturity-benefit"]["calculation_basis"] == "unknown"
    assert (
        parse_china_life_foreign_currency_interest_whole_life_formula(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_foreign_currency_interest_whole_life_formula(
            {**completed_document, "product_id": "wrong-product"}
        )
        is None
    )


china_life_dameiwang_expected = {
    "205131MA1A05623B11Z10000000": ("dameiwang-usd-111-original", 0),
    "205131MA1A05623B11Z10000001": (
        "dameiwang-usd-112-first-regulatory-revision",
        1,
    ),
    "205131MA1A05623B11Z10000002": (
        "dameiwang-usd-112-second-regulatory-revision",
        2,
    ),
}
for product_id, (expected_revision, expected_revision_count) in (
    china_life_dameiwang_expected.items()
):
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_dameiwang_usd_periodic_whole_life_formula(
        completed_document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert (
        integrated[0]
        == "china-life-dameiwang-usd-periodic-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert len(characteristics["revision_events"]) == expected_revision_count
    assert characteristics["expected_interest_rate_percent"] == 1
    assert characteristics["premium_multiplier"] == 1.03
    assert characteristics["terminal_illness_advance_available"] is True
    assert characteristics["terminal_illness_advance_rate_percent"] == 90
    assert characteristics["terminal_illness_advance_cap_amount"] == 1_000_000
    assert characteristics["installment_period_options"] == [5, 10, 15, 20, 25]
    assert characteristics["maturity_age"] == 110
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "terminal-illness-advance-benefit",
        "installment-periodic-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert entries["terminal-illness-advance-benefit"]["rate_percent"] == 90
    assert (
        "100 萬美元"
        in " ".join(entries["terminal-illness-advance-benefit"]["conditions"])
    )
    assert (
        parse_china_life_dameiwang_usd_periodic_whole_life_formula(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_dameiwang_usd_periodic_whole_life_formula(
            {**completed_document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )


china_life_meilifeng_expected = {
    "205131MA4B02423B11Z10000000": ("meilifeng-usd-109-original", 0),
    "205131MA4B02423B11Z10000001": (
        "meilifeng-usd-112-first-regulatory-revision",
        1,
    ),
    "205131MA4B02423B11Z10000002": (
        "meilifeng-usd-112-second-regulatory-revision",
        2,
    ),
}
for product_id, (expected_revision, expected_revision_count) in (
    china_life_meilifeng_expected.items()
):
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_meilifeng_usd_periodic_whole_life_formula(
        completed_document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert (
        integrated[0]
        == "china-life-meilifeng-usd-periodic-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert len(characteristics["revision_events"]) == expected_revision_count
    assert characteristics["expected_interest_rate_by_payment_period_percent"] == {
        "4": 1.5,
        "6": 1.75,
        "10": 1.75,
        "20": 1.75,
    }
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["premium_waiver_disability_grade_min"] == 2
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["installment_period_options"] == [5, 10, 15, 20, 25]
    assert characteristics["installment_minimum_specified_insurance_amount"] == 5_000
    assert characteristics["installment_minimum_annual_amount"] == 1_000
    assert characteristics["maturity_age"] == 110
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "premium-waiver-disability-grade-2-to-6",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert (
        entries["premium-waiver-disability-grade-2-to-6"]["calculation_basis"]
        == "unknown"
    )
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert (
        "5,000 美元"
        in " ".join(entries["installment-periodic-benefit"]["conditions"])
    )
    assert (
        parse_china_life_meilifeng_usd_periodic_whole_life_formula(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_meilifeng_usd_periodic_whole_life_formula(
            {**completed_document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )


china_life_meilexiangtui_expected = {
    "205121MA4B01723B11Z10000000": (
        "meilexiangtui-usd-112-original",
        "中國人壽",
        None,
    ),
    "205121MA4B01723B11Z10000001": (
        "meilexiangtui-usd-112-first-regulatory-revision",
        "中國人壽",
        None,
    ),
    "205121MA4B01723B11Z10000002": (
        "meilexiangtui-usd-113-kgi-second-partial-revision",
        "凱基人壽",
        "金管保壽字第1120432605號",
    ),
}
for product_id, (expected_revision, expected_company, expected_approval) in (
    china_life_meilexiangtui_expected.items()
):
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_meilexiangtui_usd_survival_whole_life_formula(
        completed_document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert (
        integrated[0]
        == "china-life-meilexiangtui-usd-survival-whole-life-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["latest_company_name"] == expected_company
    assert characteristics["approval_number"] == expected_approval
    assert characteristics["expected_interest_rate_percent"] == 2.25
    assert characteristics["survival_rate_percent"] == 1.85
    assert characteristics["premium_waiver_available"] is True
    assert characteristics["premium_waiver_disability_grade_min"] == 2
    assert characteristics["premium_waiver_disability_grade_max"] == 6
    assert characteristics["installment_period_options"] == [5, 10, 15, 20, 25]
    assert characteristics["maturity_age"] == 110
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "survival-benefit",
        "premium-waiver-disability-grade-2-to-6",
        "maturity-benefit",
        "installment-periodic-benefit",
    }
    assert entries["death-or-funeral-benefit"]["calculation_basis"] == "greater_of"
    assert entries["total-disability-benefit"]["calculation_basis"] == "greater_of"
    assert entries["survival-benefit"]["rate_percent"] == 1.85
    assert (
        entries["premium-waiver-disability-grade-2-to-6"]["calculation_basis"]
        == "unknown"
    )
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert (
        parse_china_life_meilexiangtui_usd_survival_whole_life_formula(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_meilexiangtui_usd_survival_whole_life_formula(
            {**completed_document, "file_name": "wrong-file-A.pdf"}
        )
        is None
    )


china_life_foreign_currency_interest_endowment_expected = {
    "205121M21A00200": (
        "hongmeili-usd-101-original",
        "USD",
        "美元",
        "中壽商發字第1010116002號",
    ),
    "205121M21A00301": (
        "hongaoli-aud-102-first-partial-revision",
        "AUD",
        "澳幣",
        "中壽商一字第1020101007號",
    ),
}
for product_id, (
    expected_revision,
    expected_currency,
    expected_currency_label,
    expected_filing_number,
) in china_life_foreign_currency_interest_endowment_expected.items():
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_foreign_currency_interest_endowment_formula(
        completed_document
    )
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert (
        integrated[0]
        == "china-life-foreign-currency-interest-endowment-formula-v1"
    )
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["currency"] == expected_currency
    assert characteristics["currency_label"] == expected_currency_label
    assert characteristics["filing_number"] == expected_filing_number
    assert characteristics["expected_interest_rate_percent"] == 2.5
    assert characteristics["maturity_benefit_formula"] == "face_amount"
    assert characteristics["foreign_currency_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "value-sharing-bonus",
        "death-or-funeral-benefit",
        "total-disability-benefit",
        "maturity-benefit",
        "minor-premium-refund-with-interest",
    }
    assert entries["death-or-funeral-benefit"]["rate_percent"] == 100
    assert entries["death-or-funeral-benefit"]["basis"] == "face_amount"
    assert entries["total-disability-benefit"]["rate_percent"] == 100
    assert entries["maturity-benefit"]["rate_percent"] == 100
    assert (
        entries["minor-premium-refund-with-interest"]["calculation_basis"]
        == "percentage_of_base"
    )
    assert (
        "2.5% 年利率"
        in " ".join(entries["minor-premium-refund-with-interest"]["conditions"])
    )
    assert (
        parse_china_life_foreign_currency_interest_endowment_formula(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_foreign_currency_interest_endowment_formula(
            {**completed_document, "product_id": "wrong-product"}
        )
        is None
    )


china_life_group_endowment_expected = {
    "205127M11A00100": ("97-original", None),
    "205127M11A00101": ("98-first-partial-revision", "98.08.01"),
}
for product_id, (expected_revision, expected_revision_date) in (
    china_life_group_endowment_expected.items()
):
    document = next(
        item
        for item in china_life_foreign_currency_interest_documents
        if item["product_id"] == product_id and item["document_type"] == "policy_terms"
    )
    source_path = (
        CHINA_LIFE_FOREIGN_CURRENCY_INTEREST_WHOLE_LIFE_ROOT
        / product_id
        / f"{product_id}-A.pdf"
    )
    completed_document = complete_strict_source_document(document, source_path)
    schedule = parse_china_life_group_endowment_face_amount(completed_document)
    assert schedule is not None
    integrated = parse_plan_table_with_parser(completed_document)
    assert integrated is not None
    assert integrated[0] == "china-life-group-endowment-face-amount-v1"
    assert integrated[1] == schedule
    assert schedule["selection_type"] == schedule["input_mode"] == "face_amount"
    assert schedule["selection_label"] == "每位被保險人保險金額"
    characteristics = schedule["version_characteristics"]
    assert characteristics["terms_revision"] == expected_revision
    assert characteristics["revision_date"] == expected_revision_date
    assert characteristics["product_family"] == "china-life-group-endowment"
    assert characteristics["group_policy"] is True
    assert characteristics["payment_period_options"] == [6, 10]
    assert characteristics["death_benefit_formula"] == "face_amount"
    assert characteristics["total_disability_benefit_formula"] == "face_amount"
    assert characteristics["maturity_benefit_formula"] == "face_amount"
    assert characteristics["full_disability_table_item_count"] == 7
    assert characteristics["surrender_value_table_available"] is True
    assert characteristics["surrender_value_table_unit_amount"] == 10_000
    assert characteristics["no_premium_loan"] is True
    assert characteristics["non_participating_policy"] is True
    entries = {entry["id"]: entry for entry in schedule["coverage_entries"]}
    assert set(entries) == {
        "death-benefit",
        "total-disability-benefit",
        "maturity-benefit",
    }
    assert all(entry["basis"] == "face_amount" for entry in entries.values())
    assert all(entry["rate_percent"] == 100 for entry in entries.values())
    assert all(entry["unit_key"] == "face_amount" for entry in entries.values())
    assert entries["death-benefit"]["limit_scope"] == "per_policy"
    assert entries["total-disability-benefit"]["limit_scope"] == "per_policy"
    assert entries["maturity-benefit"]["limit_scope"] == "per_policy"
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 10
    assert (
        parse_china_life_group_endowment_face_amount(
            {**completed_document, "document_type": "product_summary"}
        )
        is None
    )
    assert (
        parse_china_life_group_endowment_face_amount(
            {**completed_document, "product_id": "wrong-product"}
        )
        is None
    )


with TemporaryDirectory() as temp_dir:
    documents_dir = Path(temp_dir)
    product_id = "medical-plan-product"
    source_dir = documents_dir / "tii-life-test" / product_id
    source_dir.mkdir(parents=True)
    (source_dir / "terms-a.pdf").write_bytes(b"first-pdf")
    document = {
        "product_id": product_id,
        "file_name": "terms-a.pdf",
        "text": f"{HEADINGS} {TABLE}",
    }
    payload = build_proposal_payload(
        batch_id="tii-life-test",
        documents=[document],
        public_product_ids={product_id},
        documents_dir=documents_dir,
    )
    assert payload["proposed_count"] == 1
    proposal = payload["proposals"][0]
    assert proposal["status"] == "proposed"
    assert proposal["candidates"][0]["source_document_sha256"]

    (source_dir / "terms-b.pdf").write_bytes(b"second-pdf")
    second_document = {
        **document,
        "file_name": "terms-b.pdf",
        "text": f"{HEADINGS} {TABLE.replace('1,500,000', '1,600,000')}",
    }
    conflict_payload = build_proposal_payload(
        batch_id="tii-life-test",
        documents=[document, second_document],
        public_product_ids={product_id},
        documents_dir=documents_dir,
    )
    conflict = conflict_payload["proposals"][0]
    assert conflict["status"] == "manual_review_required"
    assert "multiple_matching_source_documents" in conflict["review_reasons"]
    assert "conflicting_extracted_schedules" in conflict["review_reasons"]

print("tii plan benefit parser tests: ok")
