from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from extract_tii_plan_benefits import (
    EXTRACTOR_VERSION,
    approved_schedules,
    complete_strict_source_document,
    build_proposal_payload,
    normalize_terms_text,
    parse_antai_cancer_lifetime_rider_unit_table,
    parse_antai_fubon_new_cancer_lifetime_unit_table,
    parse_annual_inpatient_account_unit_table,
    parse_fubon_cancer_unit_table,
    parse_fubon_cardio_device_unit_table,
    parse_fubon_child_combined_plan_table,
    parse_fubon_easy_combined_plan_table,
    parse_fubon_golden_lohas_combined_plan_table,
    parse_fubon_new_lohas_combined_plan_table,
    parse_fubon_golden_complete_combined_plan_table,
    parse_fubon_inpatient_medical_unit_table,
    parse_fubon_little_tycoon_plan_table,
    parse_fubon_lohas_combined_plan_table,
    parse_fubon_new_complete_combined_plan_table,
    parse_fubon_protect_combined_plan_table,
    parse_group_inpatient_limit_unit_table,
    parse_group_plan_inpatient_limit_table,
    parse_group_cancer_fixed_unit_table,
    parse_global_winterthur_cancer_annuity_face_amount,
    parse_kgi_china_life_cancer_account_unit_table,
    parse_kgi_china_life_cancer_five_year_unit_table,
    parse_prudential_cancer_account_unit_table,
    parse_prudential_cancer_five_year_unit_table,
    parse_prudential_china_daily_hospital_face_amount,
    parse_prudential_china_medical_endowment_plan_unit,
    parse_ritai_dual_unit_inpatient_table,
    parse_plan_table_with_parser,
    parse_three_plan_medical_table,
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


assert EXTRACTOR_VERSION == "tii-plan-benefits-v30"
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
    == ("104-revised-79-items" if index < 2 else "109-revised-80-items")
    for index, product_id in enumerate(FUBON_GOLDEN_COMPLETE_PRODUCT_IDS)
)

golden_complete_base_document = fubon_golden_complete_document(
    FUBON_GOLDEN_COMPLETE_PRODUCT_IDS[0]
)
golden_complete_base_text = golden_complete_base_document["text"]
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
        "text": golden_complete_base_text.replace(
            "MGC21070914", "MGC21080101"
        ),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_base_text.replace(
            "【保險範圍：癌症保險金的給付】 第十二條",
            "【保險範圍：癌症保險金的給付】 第十一條",
            1,
        ),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_base_text.replace("20 萬", "30 萬", 1),
    }
) is None
assert parse_fubon_golden_complete_combined_plan_table(
    {
        **golden_complete_base_document,
        "text": golden_complete_base_text.replace("附表一：", "附表甲：", 1),
    }
) is None

FUBON_GOLDEN_LOHAS_PRODUCT_IDS = (
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
    "209391MZ1G00421A11Z10000002"
]["version_characteristics"]["disability_schedule_revision"] == (
    "104-revised-79-items"
)
assert all(
    fubon_golden_lohas_schedules[product_id]["version_characteristics"][
        "disability_schedule_revision"
    ]
    == "109-revised-80-items"
    for product_id in FUBON_GOLDEN_LOHAS_PRODUCT_IDS[1:]
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
    "209391MZ1G00421A11Z10000002"
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
revision_three_death = next(
    entry
    for entry in new_cancer_revision_three["coverage_entries"]
    if entry["id"] == "death-funeral-remaining-pool"
)
assert "同公司多張契約" in revision_three_death["conditions"][-1]

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
    "extractor_version": "tii-plan-benefits-v-old",
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
    [preserved_record],
)
assert stale_schedules == {}
assert stale_preserved_records == [preserved_record]

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
    TII_LIFE_050_PRODUCT_IDS[0]: "104-revised-79-items",
    TII_LIFE_050_PRODUCT_IDS[1]: "109-revised-80-items",
    TII_LIFE_050_PRODUCT_IDS[2]: "109-revised-80-items",
    TII_LIFE_050_PRODUCT_IDS[3]: "109-revised-80-items",
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
    assert document["page_count"] == document["pages_parsed"] == 25
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
    assert completed_document["page_count"] == completed_document["pages_parsed"] == 25
    assert parse_fubon_new_lohas_combined_plan_table(completed_document) == schedule

    missing_source = complete_strict_source_document(
        indexed_document,
        source_path.with_name("missing-A.pdf"),
    )
    assert missing_source is indexed_document
    assert parse_fubon_new_lohas_combined_plan_table(missing_source) is None

base_document = tii_life_050_documents[TII_LIFE_050_PRODUCT_IDS[0]]
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
