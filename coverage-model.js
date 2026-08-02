(function initPolicyCoverageModel(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.PolicyCoverageModel = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPolicyCoverageModel() {
  "use strict";

  const MAX_MONEY_AMOUNT = 999999999999;
  const MAX_MONEY_DECIMAL_PLACES = 4;
  const MAX_UNIT_COUNT = 9999;
  const MAX_RATE = 10;
  const MAX_INSURED_AGE = 130;

  const SELECTION_MODES = {
    face_amount: { label: "契約保險金額", fields: ["face_amount"] },
    face_amount_plan: { label: "基本保額與保險型態", fields: ["face_amount", "plan_name"] },
    account_value: { label: "保單帳戶價值", fields: ["account_value"] },
    paid_premium_factor_plan: { label: "已繳保費公式與保險型態", fields: ["plan_name"] },
    plan: { label: "計畫別", fields: ["plan_name"] },
    unit: { label: "投保單位數", fields: ["unit_count"] },
    multi_unit: { label: "多組投保單位數", fields: ["unit_counts"] },
    plan_unit: { label: "計畫別與投保單位數", fields: ["plan_name", "unit_count"] },
    policy_state: { label: "保單狀態", fields: [] },
    fixed: { label: "條款固定給付", fields: [] },
    unknown: { label: "條款待整理", fields: [] },
  };

  const STRUCTURE_STATUSES = {
    calculated: {
      label: "已整理可計算",
      short_label: "已可計算",
      description: "條款給付項目、金額或可計算公式已完成結構化，可納入保障整理。",
    },
    needs_user_input: {
      label: "需補保單資料",
      short_label: "需補資料",
      description: "條款已有給付公式，但需要補保額、單位、計畫別或保單現況後才能計算。",
    },
    pending_structure: {
      label: "條款待整理",
      short_label: "待整理",
      description: "已有官方條款或摘要，但尚未把給付表與金額完整結構化；不代表沒有保障。",
    },
    source_pending: {
      label: "來源待補",
      short_label: "來源待補",
      description: "目前只有商品清單或索引，尚未取得可解析的官方條款內容。",
    },
    confirmed_no_amount: {
      label: "條款未列固定金額",
      short_label: "無固定金額",
      description: "已確認條款不提供可直接計算的固定金額，需依實際費用、公司試算或事故狀態判斷。",
    },
  };

  const USER_INPUT_VALUE_STATES = new Set([
    "needs_face_amount",
    "needs_unit_count",
    "needs_plan",
    "needs_policy_state",
    "needs_account_value",
    "needs_annuity_factor",
    "needs_insurer_confirmation",
  ]);

  const CALCULATED_VALUE_STATES = new Set([
    "calculated",
    "daily_rate",
    "benefit_limit",
    "account_value_return",
    "policy_state_value",
    "value_sharing_bonus",
    "value_added_account_credit",
    "greater_of",
    "premium_waiver_effect",
    "aggregate_cap",
    "policy_state_daily_rate",
    "policy_state_multiplier",
    "policy_state_percentage",
    "policy_state_limit",
    "tiered_values",
    "conditional_amount",
    "death_or_funeral_amount",
  ]);

  const CALCULATION_BASES = {
    fixed_amount: "固定給付",
    percentage_of_base: "依基準額比例",
    plan_schedule_lookup: "依計畫附表",
    per_unit: "每單位",
    per_unit_per_day: "每單位／每日",
    per_day: "每日給付",
    reimbursement_with_cap: "實際支出限額內",
    percentage_of_actual_expense_with_cap: "實際支出比例限額內",
    reimbursement_with_total_and_daily_room_cap:
      "實際支出受每次事故總限額及每日病房上限約束",
    reimbursement_with_schedule_and_major_cap:
      "實際支出依手術表與重大手術限額給付",
    reimbursement_with_greater_of_daily_cap:
      "實際支出依固定或每日累計較高限額給付",
    table_multiplier: "依條款倍數表",
    tiered_or_stepped: "依級距或階梯表",
    additional_benefit: "額外給付",
    account_value: "保單帳戶價值",
    account_value_annuity_factor: "保單帳戶價值換算年金",
    annuity_amount_or_lump_sum: "年金金額或低額年金一次給付",
    maturity_policy_account_value: "滿期時保單帳戶價值",
    policy_state_amount: "保單或保險公司列示金額",
    sum_policy_state_amounts: "保單列示金額合計",
    death_or_funeral_greater_of: "身故或喪葬費用條件式給付",
    death_or_funeral_face_amount: "身故保額或喪葬費用限額",
    death_or_funeral_percentage_of_face_amount:
      "身故保額比例或喪葬費用限額",
    death_or_funeral_multiplier_of_face_amount:
      "身故保額倍數或喪葬費用限額",
    death_or_funeral_percentage_of_policy_state_amount:
      "保費總和比例身故給付或喪葬費用限額",
    death_or_funeral_fixed_amount: "固定身故金額或喪葬費用限額",
    target_premium_count_value_addition: "依目標保險費累積繳費次數計算加值",
    installment_premium_value_addition: "依分期保險費繳別與累積次數計算加值",
    policy_year_average_target_premium_account_value_addition:
      "依保單年度與目標保險費帳戶平均值計算加值",
    policy_year_average_basic_premium_account_value_addition:
      "依保單年度與基本保費帳戶平均值計算加值",
    policy_value_component: "條款指定保單價值部分",
    policy_value_plus_general_insurance_amount: "保單價值部分加一般身故／完全殘廢保額",
    policy_value_plus_general_and_accidental_insurance_amount:
      "保單價值部分加一般及意外身故／完全殘廢保額",
    protected_amount_plus_policy_account_value:
      "條款保障額加給付評價日保單帳戶價值",
    net_premium_factor_plus_additional_premium:
      "淨主保費乘條款比例加淨增額保費",
    face_amount_plus_account_value_minus_paid_annuity_and_offsets:
      "風險額加期滿帳戶價值扣已領年金及欠款",
    net_amount_at_risk_plus_policy_account_value: "淨危險保額加保單帳戶價值",
    paid_premium_factor_account_value_formula: "已繳保費基礎加保單帳戶價值公式",
    annuity_face_amount_schedule: "年金投保金額換算給付",
    single_premium_minus_paid_annuity_total:
      "躉繳保費扣除累計已領年金",
    reserve_minus_policy_loan_and_interest:
      "保單價值準備金扣除借款及利息",
    policy_year_tiered_premium_or_face_amount: "依保單年度切換保費總和或保額比例",
    policy_year_greater_of_face_reserve_premium_with_offset:
      "依保單年度取保額、準備金或保費倍數較高值並扣除既往給付",
    death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset:
      "身故／喪葬費用依保單年度取較高值並扣除既往給付",
    maturity_greater_of_face_and_premium_with_offset:
      "滿期取保額或保費倍數較高值並扣除既往給付",
    death_or_funeral_greater_of_per_unit_floor_and_paid_premium_net:
      "身故取每單位最低額與已繳保費淨額較高者",
    aggregate_cap: "累計給付總限額",
    greater_of: "取較高值",
    waiver: "保費豁免",
    unknown: "計算方式尚待整理",
  };

  const POLICY_STATE_FIELDS = {
    policy_account_value: {
      label: "保單帳戶價值",
      type: "money",
      unit: "元",
      guidance: "請填保單帳戶價值通知、保單明細或保險公司試算列示的金額。",
    },
    benefit_valuation_policy_account_value: {
      label: "給付評價日保單帳戶價值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填受益人備齊申請文件送達保險公司後，條款指定之次一或第一個資產評價日的保單帳戶價值；目前保單明細僅能作估算，不能代替實際給付評價日金額。",
    },
    benefit_valuation_basic_premium_policy_account_value: {
      label: "給付評價日基本保費保單帳戶價值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司依本版本條款在給付評價日列示的「基本保費保單帳戶價值」；不得填入增額保費或其他保費帳戶價值。",
    },
    annuity_start_policy_account_value: {
      label: "年金開始日保單帳戶價值",
      type: "money",
      unit: "元",
      guidance:
        "請填年金給付開始日前一個資產評價日，或保險公司年金通知所列的保單帳戶價值；不可用目前帳戶價值代替未來年金開始日的金額。",
    },
    maturity_policy_account_value: {
      label: "滿期時保單帳戶價值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填滿期時由保險公司依投資標的、評價日與匯率列示的保單帳戶價值；不可用目前帳戶價值推定未來滿期金。",
    },
    maturity_basic_premium_policy_account_value: {
      label: "滿期時基本保費保單帳戶價值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填滿期時由保險公司依本版本條款列示的「基本保費保單帳戶價值」；不得把其他保費帳戶價值一併計入。",
    },
    policy_value_component: {
      label: "事故時保單價值部分",
      type: "money",
      unit: "元",
      guidance:
        "請依事故時點填入條款所稱的保單價值或保單帳戶價值；投資保險費運用起始日前後的名稱與評價日可能不同。",
    },
    policy_values_converted_to_twd: {
      label: "保單價值金額已換算為新臺幣",
      type: "boolean",
      guidance:
        "請先依保險公司列示的評價日與匯率確認金額均為新臺幣，再勾選此項；未確認時系統不會把外幣帳戶數字與新臺幣保額相加。",
    },
    general_death_disability_insurance_amount: {
      label: "一般身故及完全殘廢保險金額",
      type: "money",
      unit: "元",
      guidance: "請依保單首頁、批註或最近通知所記載的一般身故及完全殘廢保險金額填寫。",
    },
    accidental_death_disability_insurance_amount: {
      label: "意外傷害身故及完全殘廢保險金額",
      type: "money",
      unit: "元",
      guidance: "請依保單首頁、批註或最近通知所記載的意外傷害身故及完全殘廢保險金額填寫。",
    },
    annuity_payment_amount: {
      label: "年金給付金額",
      type: "money",
      unit: "元",
      guidance: "若保單或保險公司試算已列示年金金額，可填入後納入保障整理。",
    },
    annuity_payment_year: {
      label: "目前年金給付年度",
      type: "integer",
      max: 130,
      unit: "年",
      guidance: "第一個年金給付年度請填 1；增額型會依條款按年金給付年度套用增額比例。",
    },
    single_premium_amount: {
      label: "躉繳保險費",
      type: "money",
      unit: "元",
      guidance: "請依保單首頁或繳費收據填入本契約的躉繳保險費，不要加計非保證紅利。",
    },
    annuity_paid_total_amount: {
      label: "累計已領年金總額",
      type: "non_negative_money",
      unit: "元",
      guidance: "尚未領取請填 0；其餘請依保單或入帳紀錄加總截至計算日實際已領年金，不要用換算係數自行截尾。",
    },
    current_policy_amount: {
      label: "當年度保險金額",
      type: "money",
      unit: "元",
      guidance: "請依保單首頁、批註或年度通知列示的當年度保險金額填寫。",
    },
    current_benefit_amount_status: {
      label: "目前保障金額依據",
      type: "choice",
      options: [
        {
          value: "formula_confirmed_current",
          label: "已確認仍可依保費公式計算",
        },
        {
          value: "current_amount_provided",
          label: "保單已調整，改填目前保障總額",
        },
        {
          value: "unknown",
          label: "不確定是否曾調整",
        },
      ],
      guidance:
        "後續繳費、部分終止、年齡級距或契約變更可能使保障金額重算。只有確認公式仍適用時才選第一項；否則請依最新保單明細填入目前身故／完全失能保障總額。",
    },
    current_death_disability_benefit_amount: {
      label: "目前身故／完全失能保障總額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司在最新保單明細、批註或試算中列示的目前身故／完全失能保障總額，須包含條款計入的保單帳戶價值；不要自行用保費或目前帳戶價值回推。",
    },
    basic_face_amount: {
      label: "基本保額",
      type: "money",
      unit: "元",
      guidance: "請依保單首頁、批註或最近一次契約變更通知列示的目前基本保額填寫。",
    },
    insurance_deduction_amount: {
      label: "目前保險金扣除額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依最近一期保單明細或向保險公司確認目前保險金扣除額；若保單明確列示為 0，請輸入 0。部分提領與後續繳費可能改變此金額，不宜自行回推。",
    },
    current_threshold_face_amount: {
      label: "目前門檻保額",
      type: "money",
      unit: "元",
      guidance:
        "請依保單明細或向保險公司確認目前門檻保額；門檻保額是在投保、繳費或部分提領時重算，不可用目前年齡與目前帳戶價值自行回推。",
    },
    risk_amount_source: {
      label: "危險保額取得方式",
      type: "choice",
      options: [
        {
          value: "insurer_statement",
          label: "直接填保險公司目前列示金額",
        },
        {
          value: "recalculate_from_history",
          label: "依最近一次重算紀錄換算",
        },
      ],
      guidance:
        "建議優先使用最近保單明細或保險公司試算列示的危險保額；只有拿不到時，才依最近一次繳費或變更紀錄換算。",
    },
    risk_calculation_actual_age: {
      label: "最近一次重算時實際年齡",
      type: "integer",
      allow_zero: true,
      unit: "歲",
      max: MAX_INSURED_AGE,
      guidance:
        "請填最近一次重算危險保額當時的足歲，不是事故發生時年齡。",
    },
    risk_calculation_insurance_age: {
      label: "最近一次重算時保險年齡",
      type: "integer",
      allow_zero: true,
      unit: "歲",
      max: MAX_INSURED_AGE,
      guidance:
        "請填最近一次重算危險保額當時的保險年齡；係數依這個年齡選擇，不是事故日年齡。",
    },
    insured_age_accuracy_status: {
      label: "投保年齡是否正確",
      type: "choice",
      options: [
        {
          value: "confirmed_accurate",
          label: "已確認投保年齡正確",
        },
        {
          value: "error_or_uncertain",
          label: "發現錯誤或尚未確認",
        },
      ],
      guidance:
        "投保年齡錯誤可能按原扣繳與應扣繳保險成本比例調整危險保額；此時請改填保險公司確認後的目前危險保額。",
    },
    risk_calculation_stage: {
      label: "最近一次危險保額重算時點",
      type: "choice",
      options: [
        {
          value: "before_second_premium",
          label: "首期繳費後，尚未繳交第二期",
        },
        {
          value: "age15_recalculation",
          label: "滿 15 足歲時重算，之後尚未再繳費",
        },
        {
          value: "subsequent_regular_premium",
          label: "第二期以後定期定額繳費",
        },
        {
          value: "subsequent_nonregular_premium",
          label: "第二期以後非定期定額繳費",
        },
      ],
      guidance:
        "請依最近一次會改變危險保額的投保、滿 15 足歲或繳費紀錄選擇；若之後又繳費，應選最近一次繳費方式。",
    },
    risk_calculation_policy_account_value: {
      label: "危險保額重算時保單帳戶價值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "定期定額請填最近一次保單週月日的帳戶價值；非定期定額請填該次繳費時的帳戶價值。這不是理賠文件送達後的給付評價日帳戶價值。",
    },
    risk_calculation_net_premium_amount: {
      label: "該次繳費扣除保費費用後金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填最近一次第二期以後保險費扣除保費費用後的淨額；定期定額與非定期定額都以保險公司列示金額為準。",
    },
    risk_amount_effective_status: {
      label: "最近一次危險保額重算是否已生效",
      type: "choice",
      options: [
        {
          value: "current_formula_effective",
          label: "已確認重算結果生效",
        },
        {
          value: "decrease_pending_next_monthiversary",
          label: "降低結果尚待下個保單週月日生效",
        },
        {
          value: "uncertain",
          label: "不確定，改填保險公司目前列示危險保額",
        },
      ],
      guidance:
        "條款約定危險保額降低時可能延至下一保單週月日生效；若尚未生效或不確定，須填保險公司目前列示的危險保額。",
    },
    insurer_confirmed_current_risk_amount: {
      label: "保險公司目前列示危險保額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請使用最近保單明細或保險公司試算列示的當前危險保額；發現投保年齡錯誤、重算降低尚未生效或歷史不完整時也應使用此金額。",
    },
    maturity_interest_amount: {
      label: "保險公司列示之祝壽金利息",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司依條款指定活期存款利率、收款日至給付日前一日逐日計算的利息；若尚無利息則填 0。",
    },
    policy_effect_status_at_event: {
      label: "給付時點契約狀態",
      type: "choice",
      options: [
        { value: "active", label: "契約有效" },
        { value: "suspended_or_lapsed", label: "停效或失效" },
        { value: "terminated_or_uncertain", label: "已終止或狀態不確定" },
      ],
      guidance:
        "請依事故日、滿期日或保險公司通知確認契約狀態；只有契約有效時可直接依本條款公式試算。",
    },
    claim_time_status: {
      label: "申請是否超過條款時效",
      type: "choice",
      options: [
        { value: "within_claim_period", label: "未超過條款時效" },
        { value: "time_barred", label: "已超過條款時效" },
      ],
      guidance:
        "請依事故日、申請日及保險公司確認結果選擇；超過條款時效時，本商品改按指定評價日帳戶價值處理。",
    },
    benefit_exclusion_status: {
      label: "除外責任確認狀態",
      type: "choice",
      options: [
        { value: "none_confirmed", label: "已確認不適用除外責任" },
        { value: "confirmed_applies", label: "已確認適用除外責任" },
        { value: "may_apply", label: "可能適用或尚未確認" },
      ],
      guidance:
        "請依保險公司理賠判定選擇；已確認適用且條款明定返還帳戶價值時，系統會改按該返還方式試算。",
    },
    total_disability_qualification_status: {
      label: "全殘資格確認狀態",
      type: "choice",
      options: [
        {
          value: "confirmed_first_level_item",
          label: "已確認符合條款第一級七項之一",
        },
        { value: "not_confirmed", label: "尚未確認或不符合" },
      ],
      guidance:
        "請依診斷書及保險公司理賠認定選擇；未確認符合本版全殘定義前，不直接換算全殘保險金。",
    },
    investment_allocation_status: {
      label: "保險費投入狀態",
      type: "choice",
      options: [
        { value: "allocated", label: "已投入投資標的" },
        { value: "awaiting_allocation", label: "已收取但尚未投入" },
      ],
      guidance:
        "請依給付評價時點的保單明細選擇；若尚未投入，系統會再要求輸入扣除費用後的淨保險費。",
    },
    unallocated_net_premium_amount: {
      label: "已收取尚未投入之淨保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司已收取但尚未投入投資標的、且已扣除條款費用後的金額；若已全部投入則不需填寫。",
    },
    net_primary_premium_amount: {
      label: "尚未投入之淨主保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司列示填入尚未投入投資標的、已扣除條款費用後的實繳、基本或目標保險費；不同版本名稱不同，不可直接填原始繳費金額。",
    },
    net_additional_premium_amount: {
      label: "尚未投入之淨增額保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司列示填入尚未投入投資標的、已扣除條款費用後的增額或額外保險費；若本版本沒有此類保費或確認為 0，請輸入 0。",
    },
    exclusion_account_value_return_amount: {
      label: "除外責任帳戶價值返還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司依除外責任、申請文件送達日、資產評價日、匯率及適用欠款計算後列示的帳戶價值返還額。",
    },
    unpaid_policy_charge_amount: {
      label: "其他未償款項及尚未扣除費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填條款允許自給付金抵銷的其他未償款項，以及尚未收取的保險成本與行政費用合計；若保險公司確認為 0，請輸入 0。",
    },
    unpaid_monthly_deduction_amount: {
      label: "寬限期間欠繳的每月扣除額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司確認在寬限期間尚未繳付、依條款可自本次給付扣除的每月扣除額合計；不要加入其他費用，確認沒有時填 0。",
    },
    remittance_fee_amount: {
      label: "本次給付匯款相關費用",
      type: "non_negative_money",
      unit: "契約幣別",
      guidance:
        "外幣保單請依保險公司本次給付所列匯款相關費用填寫；若確認不收取，請輸入 0。",
    },
    death_benefit_status: {
      label: "身故給付適用狀態",
      type: "choice",
      options: [
        { value: "standard_death", label: "一般身故保險金" },
        { value: "funeral_limited", label: "適用喪葬費用保險金限制" },
      ],
      guidance:
        "請依本版本條款及被保險人法律狀態選擇；不同版本可能以受監護宣告或條款所列心智狀態為判斷基準。",
    },
    death_age_band_status: {
      label: "身故事故日年齡區間",
      type: "choice",
      options: [
        { value: "standard", label: "已適用一般身故給付" },
        { value: "under_15_refund", label: "實際年齡未滿 15 足歲" },
        {
          value: "age_15_before_age_16_anniversary",
          label: "已滿 15 足歲、未到保險年齡 16 歲保單週年日",
        },
      ],
      guidance:
        "請依事故日實際年齡與保單週年日選擇；不同區間適用一般身故給付、退還所繳保險費或所繳保險費身故給付。",
    },
    minor_death_benefit_status: {
      label: "未成年身故給付生效狀態",
      type: "choice",
      options: [
        { value: "effective", label: "身故給付已生效" },
        { value: "not_effective", label: "未滿 15 足歲，身故給付尚未生效" },
      ],
      guidance:
        "僅依該版本條款與事故日年齡選擇；條款約定未滿 15 足歲身故給付不生效時，系統會將此項給付列為 0。",
    },
    remaining_funeral_benefit_limit: {
      label: "本保單可用喪葬費用剩餘額度",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在適用喪葬費用限制時使用。請填法定總額扣除要保時間在先之其他保單應理賠金額後，本保單尚可使用的額度；必要時向保險公司確認。",
    },
    funeral_excess_premium_refund_amount: {
      label: "喪葬限額超額部分保費退還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在身故給付改為喪葬費用保險金，且因法定額度有超額不賠部分時填寫；請依保險公司列示的實際退還保費輸入，確認沒有時填 0。",
    },
    funeral_excess_insurance_cost_refund_status: {
      label: "喪葬超額保險成本返還",
      type: "choice",
      options: [
        {
          value: "confirmed_none",
          label: "保險公司確認返還額為 0",
        },
        {
          value: "confirmed_amount",
          label: "保險公司已提供返還額",
        },
        {
          value: "unknown",
          label: "尚未確認",
        },
      ],
      guidance:
        "危險保額受喪葬上限截限時，條款另約定按比例返還超額部分已繳或已扣保險成本；請依保險公司理賠試算填寫。",
    },
    funeral_excess_insurance_cost_refund_amount: {
      label: "喪葬超額保險成本返還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司就超過喪葬費用上限部分按比例計算的保險成本返還額。",
    },
    event_before_policy_maturity_status: {
      label: "事故是否發生於滿期日前",
      type: "choice",
      options: [
        { value: "before_maturity", label: "確認在滿期日前" },
        {
          value: "at_or_after_maturity",
          label: "在滿期日或之後",
        },
        { value: "uncertain", label: "尚未確認" },
      ],
      guidance:
        "部分版本明定身故或全殘事故須發生於滿期日前；若接近保險年齡 100 歲滿期日，請以保單與保險公司認定為準。",
    },
    unexpired_premium_refund_amount: {
      label: "未到期保險成本／未滿期保險費返還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保單、保險證或保險公司在事故日按日數比例計算的未到期保險成本或未滿期保險費返還額填寫；若保險公司確認為 0，請輸入 0。",
    },
    critical_specified_benefit_claim_status: {
      label: "重大疾病／特定傷病理賠資格",
      type: "choice",
      options: [
        {
          value: "eligible_first_claim",
          label: "已確認為契約有效期間內首次符合條款且尚未領取",
        },
        {
          value: "already_paid",
          label: "本附約已領取過這筆保險金",
        },
      ],
      guidance:
        "只有已依事故原因、等待期、完整醫學定義、首次診斷與契約狀態確認符合時，才選擇第一項；尚未確認時請先查閱診斷文件或向保險公司確認。",
    },
    china_account_specific_illness_claim_status: {
      label: "特定傷病理賠資格",
      type: "choice",
      options: [
        {
          value: "eligible_first_claim",
          label: "已確認為附約有效期間內首次符合條款且尚未領取",
        },
        {
          value: "already_paid",
          label: "本附約已領取過特定傷病保險金",
        },
      ],
      guidance:
        "請先確認完整醫學定義、癌症九十日或其他疾病三十日等待期、事故原因及續保狀態；條款確認符合後才選擇第一項。",
    },
    nanshan_specific_illness_event_status: {
      label: "這次要查看的條款情境",
      type: "choice",
      options: [
        {
          value: "eligible_after_waiting_period",
          label: "等待期後首次符合特定傷病",
        },
        {
          value: "eligible_accident_waiting_exempt",
          label: "意外所致且符合等待期例外",
        },
        {
          value: "disease_within_initial_waiting_period",
          label: "生效前或生效後 30 日內因疾病罹患",
        },
        {
          value: "disease_within_increase_waiting_period",
          label: "增加保額責任開始前因疾病罹患",
        },
        {
          value: "qualifying_waiver_within_payment_period",
          label: "繳費期間內符合本版本失能／殘廢豁免等級",
        },
        {
          value: "termination_with_unexpired_premium",
          label: "附約終止且有未到期保費可退",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
        {
          value: "benefit_already_paid",
          label: "特定傷病保險金已給付，附約已終止",
        },
      ],
      guidance:
        "請依診斷日、事故原因、保單生效／復效／增加保額日期、繳費期間及本版本失能或殘廢附表選擇。系統只會顯示該情境真正需要的金額欄位；不確定時請選「尚未確認」。",
    },
    farglory_yongkang_event_status: {
      label: "這次要查看的特定傷病情境",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "eligible_after_waiting_during_payment_period",
          label: "等待期後首次符合，仍在繳費期間",
        },
        {
          value: "eligible_after_waiting_after_payment_period",
          label: "等待期後首次符合，已過繳費期間",
        },
        {
          value: "eligible_accident_exempt_during_payment_period",
          label: "意外所致等待期例外，仍在繳費期間",
        },
        {
          value: "eligible_accident_exempt_after_payment_period",
          label: "意外所致等待期例外，已過繳費期間",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病發生時尚未滿 30 日等待期",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
        {
          value: "benefit_already_paid",
          label: "特定傷病保險金已給付，附約已終止",
        },
      ],
      guidance:
        "請依診斷日、事故原因、附約生效／復效日及繳費期間選擇。意外等待期例外只適用各版本特定傷病表第 6、7、10 項；事故仍在繳費期間時，另填保險公司核定的未到期保費返還額。",
    },
    farglory_specific_illness_life_event_status: {
      label: "這次要查看的保險事故",
      type: "choice",
      max_length: 72,
      options: [
        {
          value: "specific_illness_after_waiting_during_payment_period",
          label: "等待期後首次符合特定傷病，仍在繳費期間",
        },
        {
          value: "specific_illness_after_waiting_after_payment_period",
          label: "等待期後首次符合特定傷病，已過繳費期間",
        },
        {
          value: "specific_illness_accident_exempt_during_payment_period",
          label: "意外所致等待期例外，仍在繳費期間",
        },
        {
          value: "specific_illness_accident_exempt_after_payment_period",
          label: "意外所致等待期例外，已過繳費期間",
        },
        {
          value: "death_during_payment_period",
          label: "身故，仍在繳費期間",
        },
        {
          value: "death_after_payment_period",
          label: "身故，已過繳費期間",
        },
        {
          value: "total_disability_during_payment_period",
          label: "符合附表一完全殘廢，仍在繳費期間",
        },
        {
          value: "total_disability_after_payment_period",
          label: "符合附表一完全殘廢，已過繳費期間",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病發生時尚未滿 30 日等待期",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
        {
          value: "primary_benefit_already_paid",
          label: "任一主給付已領取，附約已終止",
        },
      ],
      guidance:
        "請依診斷日、事故原因、附約生效／復效日及繳費期間選擇。三項主給付互斥；身故時系統會再詢問一般身故或喪葬限額，繳費期間內則另填保險公司核定的未到期保費。",
    },
    increased_face_amount_premium_paid_total: {
      label: "增加保險金額部分已繳保費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在增加保額責任開始前因疾病罹患特定傷病時填寫；請依保單批註、繳費紀錄或保險公司列示的增加保額部分已繳保費輸入，不要填整張附約保費。",
    },
    post_event_insurance_cost_refund_amount: {
      label: "事故後已收取的保險成本返還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險事故發生後保險公司仍收取、依本版本條款須併同保險金返還的保險成本；若保險公司確認為 0，請輸入 0。",
    },
    post_event_insurance_cost_refund_status: {
      label: "事故後是否仍扣取保險成本",
      type: "choice",
      options: [
        { value: "none", label: "沒有，或保險公司確認為 0" },
        { value: "charged_after_event", label: "有，需輸入返還額" },
      ],
      guidance:
        "只有事故後因通知或文件送達時間差仍扣取保險成本時才選擇「有」；不確定時請先向保險公司確認。",
    },
    delayed_notice_policy_fee_refund_amount: {
      label: "事故後應退還的每月保單費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填事故發生後因通知或文件送達時間差而仍被扣除、依條款應無息退還的每月保單費用；若保險公司確認沒有此項退費，請輸入 0。",
    },
    policy_reserve_value: {
      label: "保單價值準備金",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填事故日或條款指定評價日的保單價值準備金。",
    },
    policy_loan_and_interest_amount: {
      label: "保單借款及應付利息",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填事故日或年金給付開始日尚未清償的保單借款本金與應付利息合計；若保險公司確認沒有借款，請輸入 0。",
    },
    previous_policy_reserve_value: {
      label: "前一保單年度末保單價值準備金",
      type: "money",
      unit: "元",
      guidance: "增值回饋分享金通常需用前一保單年度末的保單價值準備金計算。",
    },
    premium_total_amount: {
      label: "應繳保險費總和",
      type: "money",
      unit: "元",
      guidance: "請依條款所稱已繳、應繳或年繳應繳保險費總和填寫。",
    },
    cumulative_surgery_benefit_paid_amount: {
      label: "累計已領及本次應領手術醫療保險金",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司理賠紀錄填入第十一條至第十二條累計已領及本次應領的手術醫療保險金總額；尚未領取且本次無手術給付時填 0。",
    },
    cumulative_medical_benefit_paid_amount: {
      label: "事故前累計已領醫療保險金",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司理賠紀錄，填入本次事故前已列入條款終身給付上限的醫療保險金累計總額；尚未領取請填 0。",
    },
    current_eligible_hospital_benefit_total_amount: {
      label: "本次可列入健康增值的住院給付合計",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請先加總本次依該商品條款可申領、且明列可納入健康增值計算的住院相關保險金；不符合健康增值條件時可填 0。",
    },
    health_increment_rate_percent: {
      label: "未住院間隔適用的健康增值比率",
      type: "choice",
      options: [
        { value: "0", label: "未滿 24 個月（0%）" },
        { value: "20", label: "24 個月至未滿 48 個月（20%）" },
        { value: "40", label: "48 個月至未滿 72 個月（40%）" },
        { value: "60", label: "72 個月至未滿 96 個月（60%）" },
        { value: "80", label: "96 個月以上（80%）" },
      ],
      guidance:
        "依本次入院日往前，從契約生效日、前次出院日、復效日或增加單位日額生效日中最接近者起算；請按條款選擇間隔級距。",
    },
    cumulative_medical_benefit_paid_multiplier: {
      label: "事故前累計已占用醫療給付倍數",
      type: "number",
      allow_zero: true,
      max: 1500,
      step: "0.5",
      unit: "倍",
      guidance:
        "請依保險公司理賠紀錄，填入本次事故前已列入終身給付上限的累計倍數；尚未領取請填 0。此欄不能用歷史給付金額直接換算，因保單日額調整後仍須依條款以倍數扣除。",
    },
    current_articles_11_to_14_benefit_total_amount: {
      label: "本次第 11 至 14 條保險金合計",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請先將本次可申領的手術醫療、住院手術療養、重大手術慰問及意外創傷縫合處置保險金加總；不適用的項目以 0 計。",
    },
    policy_year: {
      label: "目前保單年度",
      type: "integer",
      max: 130,
      unit: "年",
      guidance: "第一保單年度請填 1；請依保單週年日與最近一期保單明細確認。",
    },
    standard_annual_premium_amount: {
      label: "標準體年繳保險費",
      type: "money",
      unit: "元",
      guidance:
        "請依保單面頁或保險公司列示的標準體年繳保險費填寫，不要以實際扣款金額或折扣後保費代替。",
    },
    premium_payment_period_years: {
      label: "繳費年期",
      type: "integer",
      max: 100,
      unit: "年",
      guidance: "請依保單面頁所載繳費年期填寫，例如 10 年期請填 10。",
    },
    prior_long_term_care_benefit_amount: {
      label: "已領長期照顧保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "未曾領取請填 0；曾領取時請依理賠通知所列金額填寫。",
    },
    long_term_care_qualification_type: {
      label: "長期照顧狀態判定類型",
      type: "choice",
      options: [
        { value: "adl", label: "生理功能障礙（ADL）" },
        { value: "cognitive", label: "認知功能障礙（CDR）" },
      ],
      guidance: "請依診斷書或理賠文件選擇本次判定所依據的類型。",
    },
    adl_impairment_count: {
      label: "ADL 障礙項目數",
      type: "integer",
      allow_zero: true,
      max: 6,
      unit: "項",
      guidance: "依進食、移位、如廁、沐浴、平地行動與更衣六項，填入符合條款障礙定義的項目數。",
    },
    cdr_score: {
      label: "臨床失智量表（CDR）",
      type: "choice",
      options: [
        { value: "0", label: "0" },
        { value: "0.5", label: "0.5" },
        { value: "1", label: "1" },
        { value: "2", label: "2" },
        { value: "3", label: "3" },
      ],
      guidance: "請依醫師診斷或理賠文件填寫，不要自行評估。",
    },
    impairment_duration_months: {
      label: "狀態持續月數",
      type: "integer",
      allow_zero: true,
      max: 1200,
      unit: "月",
      guidance: "請依診斷或理賠文件填入已持續月數；未滿一個月可填 0。",
    },
    long_term_care_permanence_status: {
      label: "是否屬終身無法治癒",
      type: "choice",
      options: [
        { value: "permanent", label: "醫師確認終身無法治癒" },
        { value: "not_permanent", label: "未確認為終身無法治癒" },
      ],
      guidance: "只有醫師已明確確認終身無法治癒時才選第一項。",
    },
    long_term_care_medical_confirmation_status: {
      label: "是否已有條款要求的醫療確認",
      type: "choice",
      options: [
        { value: "confirmed", label: "已有醫師／專科醫師文件確認" },
        { value: "not_confirmed", label: "尚未確認" },
      ],
      guidance: "請依診斷書或理賠文件確認；尚未取得文件時請選尚未確認。",
    },
    cognitive_icd_diagnosis_status: {
      label: "認知障礙是否符合條款診斷",
      type: "choice",
      options: [
        { value: "confirmed", label: "診斷符合條款所列 ICD 範圍" },
        { value: "not_confirmed", label: "尚未確認或不符合" },
      ],
      guidance: "僅認知功能障礙路徑需要；請以專科醫師診斷或理賠文件為準。",
    },
    long_term_care_previous_claim_status: {
      label: "本契約是否已領過長期照顧保險金",
      type: "choice",
      options: [
        { value: "not_claimed", label: "尚未領取" },
        { value: "already_claimed", label: "已領取" },
      ],
      guidance: "本項給付終身一次；請依過往理賠通知確認。",
    },
    premium_payment_period_status: {
      label: "事故時是否仍在繳費期間",
      type: "choice",
      options: [
        { value: "within_payment_period", label: "仍在繳費期間" },
        { value: "payment_period_ended", label: "繳費期間已屆滿" },
        { value: "reduced_paid_up", label: "已辦理減額繳清" },
      ],
      guidance: "保費豁免只適用於條款所定繳費期間內，請依事故日與保單年期確認。",
    },
    old_age_long_term_care_age_status: {
      label: "長期照顧狀態發生時是否已滿 60 歲",
      type: "choice",
      options: [
        { value: "age_60_plus", label: "已滿 60 歲" },
        { value: "under_60", label: "未滿 60 歲" },
      ],
      guidance:
        "老年長期照顧／看護給付限保險年齡 60 歲後符合條款狀態時適用。",
    },
    paid_premium_total: {
      label: "截至評價日已繳保險費總額",
      type: "money",
      unit: "元",
      guidance: "請依保單或保險公司試算資料，輸入截至評價日已實際繳納的保險費總額。",
    },
    aia_tongtong_prior_cap_benefit_paid_amount: {
      label: "事故前已領取且應扣除的保險金總額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依友邦人壽通通友保終身保險的理賠紀錄，填入事故前已領取、依條款應自身故或祝壽給付扣除的保險金；尚未領取請填 0。",
    },
    cumulative_paid_target_premium_total: {
      label: "累積所繳目標保險費總和",
      type: "money",
      unit: "元",
      guidance: "請依本期保險費入帳後的保單明細，填入截至本期累積已繳的目標保險費總和。",
    },
    target_premium_cumulative_count: {
      label: "本期入帳後累積繳費次數",
      type: "integer",
      max: MAX_UNIT_COUNT,
      unit: "次",
      guidance: "請依條款口徑填寫：年繳每次計 12 次，月繳每次計 1 次；填入本期保險費入帳後的累積次數。",
    },
    target_premium_new_count: {
      label: "本期新增繳費次數",
      type: "integer",
      max: 12,
      unit: "次",
      guidance: "年繳通常輸入 12，月繳通常輸入 1；若保單明細另有列示，請以保險公司資料為準。",
    },
    value_addition_qualification_status: {
      label: "加值給付金資格",
      type: "choice",
      options: [
        { value: "eligible", label: "仍具加值給付資格" },
        { value: "ineligible", label: "已喪失加值給付資格" },
      ],
      guidance:
        "若曾調整目標保險費，或部分提領後次日保單帳戶價值低於累積所繳目標保險費總和，條款可能使資格喪失；不確定時請向保險公司確認。",
    },
    installment_premium_frequency: {
      label: "分期保險費繳別",
      type: "choice",
      options: [
        { value: "annual", label: "年繳" },
        { value: "monthly", label: "月繳" },
      ],
      guidance: "請依保單首頁或最近一次繳費通知選擇目前分期保險費繳別。",
    },
    previous_installment_premium_cumulative_count: {
      label: "前期累積分期繳費次數",
      type: "integer",
      allow_zero: true,
      max: MAX_UNIT_COUNT,
      unit: "次",
      guidance: "請依前一期保單明細所列的分期保險費累積繳費次數填寫；首次繳費可填 0。",
    },
    current_installment_premium_cumulative_count: {
      label: "當期累積分期繳費次數",
      type: "integer",
      max: MAX_UNIT_COUNT,
      unit: "次",
      guidance: "請依本期保險費入帳後的保單明細填寫累積繳費次數。",
    },
    previous_installment_premium_average_amount: {
      label: "前期累積所繳分期保險費平均值",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依保單明細或保險公司列示的前期累積所繳分期保險費平均值填寫，不要自行以目前保費倒推。",
    },
    average_target_premium_account_value: {
      label: "前 12 個保單週月日目標保險費帳戶價值平均值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司明細填入本次保單週年日前 12 個保單週月日之目標保險費帳戶價值平均值；不是整張保單帳戶價值。",
    },
    average_basic_premium_account_value: {
      label: "前 12 個保單足月日基本保費帳戶價值平均值",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依保險公司明細填入本次保單週年日前 12 個保單足月日之基本保費帳戶價值平均值；不是整張保單帳戶價值。",
    },
    partial_termination_amount_total: {
      label: "累計部分終止金額",
      type: "non_negative_money",
      unit: "元",
      guidance: "若沒有部分終止或部分提領，請輸入 0；條款會用已繳保費總額扣除此金額。",
    },
    specified_percent_or_multiplier: {
      label: "要保書指定百分比或倍數",
      type: "number",
      unit: "倍 / %",
      max: MAX_RATE * 100,
      step: "0.01",
      guidance: "請照保單數字輸入，例如 1.3 或 130，並在下一欄明確選擇單位；系統不會自行猜測是倍數或百分比。",
    },
    specified_factor_unit: {
      label: "指定係數單位",
      type: "choice",
      options: [
        { value: "multiplier", label: "倍數" },
        { value: "percent", label: "百分比" },
      ],
      guidance:
        "請依保單要保書確認係數單位；條款未提供單位不明時的推定或換算規則。",
    },
    contract_currency: {
      label: "契約約定幣別",
      type: "text",
      max_length: 20,
      guidance: "請依保單首頁或保單明細填寫，例如 USD、美元或澳幣。",
    },
    insured_age_at_event: {
      label: "事故時被保險人年齡",
      type: "integer",
      allow_zero: true,
      unit: "歲",
      max: MAX_INSURED_AGE,
      guidance: "請填事故發生時的足歲；部分投資型壽險未滿 15 足歲時只返還保單帳戶價值。",
    },
    insured_insurance_age_at_event: {
      label: "事故時保險年齡",
      type: "integer",
      allow_zero: true,
      unit: "歲",
      max: MAX_INSURED_AGE,
      guidance:
        "請依保單明細填寫保險年齡；保險年齡可能比實際足歲多一歲，會影響危險保額係數。",
    },
    insured_age_at_issue: {
      label: "投保時被保險人年齡",
      type: "integer",
      allow_zero: true,
      unit: "歲",
      max: MAX_INSURED_AGE,
      guidance: "請依保單首頁填寫投保年齡；舊版商品會以投保年齡與目前保單年度查附表保額倍數。",
    },
    premium_amount: {
      label: "保險費金額",
      type: "money",
      unit: "元",
      guidance: "保費折減、折抵或比例計算項目需填入對應期間的保險費。",
    },
    remaining_premium_amount: {
      label: "未到期保險費合計",
      type: "money",
      unit: "元",
      guidance: "保險費豁免不是現金給付；可填入未到期保費合計來估算保障效果。",
    },
    fubon_premium_waiver_eligibility_status: {
      label: "工作能力豁免資格",
      type: "choice",
      options: [
        {
          value: "eligible_after_180_days",
          label: "已持續超過 180 日且確認符合",
        },
        {
          value: "under_180_days",
          label: "尚未持續超過 180 日",
        },
        { value: "not_eligible", label: "確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "須因疾病或意外不能從事一切工作、不能由工作取得報酬，且狀況持續超過 180 日仍未治癒，才選擇已確認符合。",
    },
    fubon_premium_waiver_collected_refund_amount: {
      label: "180 日內已收保費返還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司核定、從工作能力喪失診斷日起 180 日內已到期且已收取的主契約與附約保費返還總額。",
    },
    fubon_premium_waiver_current_refund_status: {
      label: "事故當期未到期保費返還資格",
      type: "choice",
      options: [
        {
          value: "eligible_no_prior_waiver",
          label: "符合且應繳日前無其他既有豁免",
        },
        {
          value: "prior_waiver_already_effective",
          label: "應繳日前其他契約已先符合豁免",
        },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "第 13 次以後版本才有本項；若主契約或附約在當期應繳日前已先符合自身豁免條件，條款不返還該部分未到期保費。",
    },
    fubon_premium_waiver_overlap_status: {
      label: "主附約是否發生重疊豁免",
      type: "choice",
      options: [
        {
          value: "eligible_overlapping_waiver",
          label: "豁免期間另有契約符合自身豁免",
        },
        { value: "no_overlapping_waiver", label: "沒有重疊豁免" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "第 13 次以後版本才有本項；符合時，其他契約自身應豁免的續期保費由保險公司逐期退還。",
    },
    fubon_premium_waiver_overlap_refund_amount: {
      label: "重疊豁免逐期退還保費合計",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司已核定或本次要整理期間內逐期退還的主契約及其他附約保費合計；本條款不是貼現一次給付。",
    },
    fubon_parent_child_waiver_event_status: {
      label: "親子型保費豁免資格",
      type: "choice",
      options: [
        { value: "eligible_parent_death", label: "父或母身故，已確認符合" },
        {
          value: "eligible_parent_impairment",
          label: "父或母符合附表失能／殘廢，已確認符合",
        },
        { value: "not_parent_policyholder", label: "主約要保人不是被保險人的父或母" },
        {
          value: "no_covered_death_or_impairment",
          label: "沒有身故或附表所列失能／殘廢",
        },
        { value: "confirmed_not_eligible", label: "保險公司確認不符合" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "本附約以主約要保人為被保險人，且該要保人須是主約被保險人的父或母；事故須為身故或符合該版附表的失能／殘廢程度。",
    },
    fubon_parent_child_waiver_overlap_status: {
      label: "親子型保費豁免重疊狀態",
      type: "choice",
      options: [
        { value: "eligible_both", label: "自身契約與其他豁免附約皆重疊" },
        {
          value: "eligible_own_contract_only",
          label: "僅主約或其他附約符合自身豁免",
        },
        {
          value: "eligible_other_waiver_only",
          label: "僅另一豁免保費附約同時符合",
        },
        { value: "no_overlap", label: "沒有重疊豁免" },
        { value: "event_not_eligible", label: "親子型豁免事故本身不符合" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "僅新版條款有多重豁免協調；請依事故當期主約、附約及其他豁免附約的實際核定結果選擇。",
    },
    fubon_parent_child_contract_own_waiver_refund_amount: {
      label: "主約／附約自身豁免逐期退還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司核定、在親子型豁免期間由主約或其他附約自身豁免所逐期退還的續期保費合計。",
    },
    fubon_parent_child_other_waiver_balance_refund_amount: {
      label: "其他豁免附約重疊差額退還額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司核定、兩份豁免附約同時生效後，合計豁免額扣除實際免繳保費的差額。",
    },
    overlapping_waiver_settlement_amount: {
      label: "重疊豁免一次給付確認金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在主契約或其他附約另有豁免保障、且本附約條款改以貼現方式一次給付時使用；請填保險公司依剩餘日數、未來年度保費與預定利率確認的金額。",
    },
    waived_premium_termination_settlement_amount: {
      label: "豁免後契約終止貼現給付確認金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在已發生保費豁免後，條款約定因主契約被保險人事故或相關契約終止，將尚未豁免保費貼現一次給付時使用；請填保險公司確認的金額。",
    },
    cancer_hospital_daily_amount: {
      label: "保單記載癌症住院醫療日額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書、保險證、被保險人名冊、批註或最近契約變更通知所載的癌症住院醫療保險金日額。",
    },
    cancer_surgery_benefit_amount: {
      label: "保單記載癌症手術保險金額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書、保險證、被保險人名冊、批註或最近契約變更通知所載的癌症手術治療保險金額。",
    },
    cancer_death_benefit_amount: {
      label: "保單記載癌症死亡保險金額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書、保險證、被保險人名冊、批註或最近契約變更通知所載的癌症死亡保險金額。",
    },
    cancer_recovery_daily_amount: {
      label: "保單記載癌症出院後療養日額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書、保險證、被保險人名冊、批註或最近契約變更通知所載的癌症出院後療養保險金日額。",
    },
    cancer_radiation_daily_amount: {
      label: "保單記載癌症放射線治療日額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書、保險證、被保險人名冊、批註或最近契約變更通知所載的癌症放射線醫療保險金日額。",
    },
    fubon_group_one_year_cancer_event_status: {
      label: "這次要查看的癌症保障情境",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "eligible_cancer_death",
          label: "符合條款且因癌症或相關治療身故",
        },
        {
          value: "eligible_cancer_treatment",
          label: "符合條款的癌症住院或治療",
        },
        {
          value: "diagnosed_within_applicable_waiting_period",
          label: "責任開始日前確診，查看退費",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
      ],
      guidance:
        "請依診斷日、附約生效或復效日、身故原因及這個 productId 版本選擇。早期版本復效後仍有 30 日等待期，後期版本自復效日起恢復保障。",
    },
    fubon_group_one_year_cancer_waiting_refund_amount: {
      label: "責任開始日前確診應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在責任開始日前確診時填寫；請輸入保險公司依本附約繳費紀錄列示的無息退還金額，不要自行用保額推估。",
    },
    hospital_daily_amount: {
      label: "保單記載住院日額",
      type: "money",
      unit: "元",
      guidance: "請填保單首頁、批註或計畫表列示的住院保險金日額。",
    },
    fubon_anxin_hospital_event_status: {
      label: "本次住院事故資格",
      type: "choice",
      options: [
        {
          value: "eligible_disease_after_waiting",
          label: "疾病且已超過 30 日等待期",
        },
        { value: "eligible_accident", label: "有效期間內的意外傷害" },
        {
          value: "disease_waiting_not_met",
          label: "疾病仍在等待期內",
        },
        {
          value: "day_hospital_or_day_stay",
          label: "日間住院或日間留院",
        },
        {
          value: "post_expiry_readmission",
          label: "契約屆滿後的再次住院",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "請依事故原因、疾病發生日、附約生效或復效日及這個 product ID 的條款版本選擇；日間住院與契約屆滿後再住院的處理會依版本判定。",
    },
    fubon_anxin_health_increment_rate_percent: {
      label: "健康增值資格",
      type: "choice",
      options: [
        { value: "0", label: "距前次理賠出院未超過 24 個月（0%）" },
        { value: "20", label: "距前次理賠出院超過 24 個月（20%）" },
      ],
      guidance:
        "依本次入院日與前次醫療理賠事故出院日判斷；只要申請任何理賠，健康增值期間即重新起算。",
    },
    fubon_anxin_highest_surgery_rate_percent: {
      label: "同一次住院手術附表最高比例",
      type: "rate",
      unit: "%",
      min: 10,
      max: 500,
      guidance:
        "同一次住院有兩次以上手術時，輸入各手術附表比例中的最高值；只有一次手術時，與本次手術給付比例相同。",
    },
    global_fixed_icu_daily_amount: {
      label: "保單記載加護病房日額",
      type: "money",
      unit: "元",
      guidance:
        "僅適用未在條款列出計畫金額的早期版本；請填保單首頁、保險證或批註列示的每日加護病房保險金。",
    },
    global_fixed_burn_daily_amount: {
      label: "保單記載燒燙傷病房日額",
      type: "money",
      unit: "元",
      guidance:
        "僅適用未在條款列出計畫金額的早期版本；請填保單首頁、保險證或批註列示的每日燒燙傷病房保險金。",
    },
    global_fixed_surgery_base_amount: {
      label: "保單記載手術保險金基準額",
      type: "money",
      unit: "元",
      guidance:
        "僅適用未在條款列出計畫金額的早期版本；請填保單首頁、保險證或批註列示的手術醫療保險金基準額，再依手術附表輸入給付比例。",
    },
    global_fixed_hospital_event_status: {
      label: "本次住院事故資格",
      type: "choice",
      options: [
        {
          value: "eligible_disease_after_waiting",
          label: "疾病且已超過 30 日等待期",
        },
        { value: "eligible_accident", label: "有效期間內的意外傷害" },
        {
          value: "eligible_newborn_screening_exception",
          label: "零歲投保的新生兒篩檢例外",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病仍在等待期內",
        },
        {
          value: "day_hospital_or_day_stay",
          label: "日間住院、日間留院或日間照護",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "請依診斷書、事故日期與這個 product ID 對應的條款版本選擇；日間住院是否排除及新生兒篩檢例外會依版本判定。",
    },
    global_health_event_status: {
      label: "這次住院或醫療事故資格",
      type: "choice",
      options: [
        { value: "eligible_disease_after_waiting", label: "疾病且已超過 30 日等待期" },
        { value: "eligible_accident", label: "有效期間內的意外傷害" },
        { value: "eligible_newborn_screening_exception", label: "零歲投保的新生兒篩檢例外" },
        { value: "disease_waiting_not_met", label: "疾病仍在等待期內" },
        { value: "day_hospital_or_day_stay", label: "日間住院、日間留院或日間照護" },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance: "請依事故原因、疾病發生日、附約生效或復效日與本 product ID 條款版本選擇。",
    },
    global_health_surgery_schedule_multiplier: {
      label: "本次手術附表給付比例",
      type: "rate",
      unit: "%",
      min: 5,
      max: 300,
      step: "1",
      guidance: "請查本 product ID 手術附表輸入 5% 至 300%；例如 250% 請輸入 250。",
    },
    global_health_same_stay_surgery_paid_amount: {
      label: "同一住院或事故已領手術保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "尚未領取請填 0；有多次手術時填同一住院或事故已給付金額，以套用三倍累計上限。",
    },
    global_health_bonus_factor_percent: {
      label: "健康增值後給付比例",
      type: "choice",
      options: [
        { value: "100", label: "100%（無增值）" },
        { value: "120", label: "120%" },
        { value: "130", label: "130%" },
        { value: "140", label: "140%" },
        { value: "150", label: "150%（上限）" },
      ],
      guidance: "連續兩年未申請理賠為 120%，之後每一保單週年增加 10%，最高 150%；理賠後回到 100%。",
    },
    global_health_work_inability_status: {
      label: "喪失工作能力狀態",
      type: "choice",
      options: [
        { value: "persisting_180_days", label: "已持續 180 日且仍持續" },
        { value: "not_persisting_180_days", label: "未持續滿 180 日" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance: "依診斷證明與保險公司認定，判斷是否符合條款連續 180 日喪失工作能力。",
    },
    global_health_premiums_paid_within_180_days: {
      label: "診斷後前 180 日已繳本附約保費",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填診斷日起前 180 日內已到期並實際繳交的本附約保費；沒有請填 0。",
    },
    taiwan_inpatient_daily_event_status: {
      label: "本次住院事故狀態",
      type: "choice",
      options: [
        {
          value: "eligible_disease_after_waiting_period",
          label: "疾病於生效或復效滿 30 日後發生",
        },
        {
          value: "eligible_accident",
          label: "有效期間內因意外傷害住院",
        },
        {
          value: "disease_within_waiting_period",
          label: "疾病於生效後 30 日內發生",
        },
        {
          value: "day_hospital_or_day_care",
          label: "日間住院、日間留院或日間照護",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認是否符合條款",
        },
      ],
      guidance:
        "請依疾病發生日、事故原因、附約生效或復效日及住院證明選擇；早期版本未明列日間住院排除時，仍須由保險公司確認。",
    },
    inpatient_nursing_daily_amount: {
      label: "保單記載住院看護日額",
      type: "money",
      unit: "元",
      guidance:
        "請填保單首頁、被保險人名冊、批註或最近契約變更通知所載的住院看護保險金日額。",
    },
    discharge_recuperation_daily_amount: {
      label: "保單記載出院後療養日額",
      type: "money",
      unit: "元",
      guidance:
        "請填保單首頁、被保險人名冊、批註或最近契約變更通知所載的出院後療養保險金日額。",
    },
    surgery_fixed_amount: {
      label: "保單記載外科手術保險金定額",
      type: "money",
      unit: "元",
      guidance:
        "請填被保險人名冊、批註或最近契約變更通知所載的外科手術保險金定額；系統會再乘手術附表比例。",
    },
    surgery_nursing_fixed_amount: {
      label: "保單記載外科手術看護保險金",
      type: "money",
      unit: "元",
      guidance:
        "請填被保險人名冊、批註或最近契約變更通知所載的外科手術看護保險金；系統會再乘手術附表比例。",
    },
    surgery_fee_benefit_limit: {
      label: "保單記載手術費用保險金限額",
      type: "money",
      unit: "元",
      guidance:
        "請填保單首頁、被保險人名冊、批註或計畫表列示的每次手術費用保險金限額；系統會再乘本次手術附表比例。",
    },
    inpatient_medical_benefit_limit: {
      label: "保單記載住院醫療費用保險金限額",
      type: "money",
      unit: "元",
      guidance:
        "請填保單首頁、被保險人名冊、批註或計畫表列示的每次住院醫療費用保險金限額。",
    },
    hospitalization_total_benefit_limit: {
      label: "保單記載每次住院總限額",
      type: "money",
      unit: "元",
      guidance:
        "僅舊版條款需要；請填保單首頁、被保險人名冊、批註或附表列示的每次住院及出院後門診各項保險金總限額。",
    },
    china_group_hospital_medical_total_limit: {
      label: "保單記載住院醫療保險金總限額",
      type: "money",
      unit: "元／每次事故",
      guidance:
        "請填本 productId 對應保單、被保險人名冊、批註或保險公司資料列示的住院醫療保險金總限額。",
    },
    china_group_hospital_medical_actual_expense: {
      label: "本次事故實際自付醫療費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依醫療費用收據及明細單，填入本次符合條款範圍的實際自付醫療費用總額。",
    },
    china_group_hospital_room_meal_expense: {
      label: "其中病房及膳食費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "住院事故請填實際自付醫療費用中屬於病房及膳食費的金額；不得高於本次實際自付醫療費用總額。",
    },
    china_group_hospital_medical_event_type: {
      label: "本次醫療事故類型",
      type: "choice",
      options: [
        { value: "inpatient", label: "住院治療" },
        { value: "outpatient_surgery", label: "未住院的當日外科手術" },
        {
          value: "emergency_observation",
          label: "急診暫留床或治療超過六小時",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "較後版本才包含未住院當日外科手術與特定急診暫留；請依本 productId 條款、診斷證明及收據選擇。",
    },
    nanshan_new_group_daily_room_limit: {
      label: "要保書每日住院費限額",
      type: "money",
      unit: "元／日",
      guidance:
        "請填本 productId 對應要保書、被保險人名冊或批註所列的每日住院費保險金限額。",
    },
    nanshan_new_group_misc_limit: {
      label: "要保書醫院各項雜費限額",
      type: "money",
      unit: "元／同一次住院",
      guidance:
        "此限額由住院雜費、意外事故急診醫療費及住院前後門診費共用。",
    },
    nanshan_new_group_physician_daily_limit: {
      label: "要保書每日醫師診查費限額",
      type: "money",
      unit: "元／日或次",
      guidance:
        "請填要保書列示的每日醫師診查費限額；住院前後門診每次也使用此限額。",
    },
    nanshan_new_group_surgery_base_limit: {
      label: "要保書外科手術費限額",
      type: "money",
      unit: "元",
      guidance:
        "請填要保書列示的外科手術費保險金限額，系統會再依附表百分率換算。",
    },
    nanshan_new_group_surgery_schedule_rate: {
      label: "附表手術最高補償百分率",
      type: "choice",
      options: [
        3, 5, 7, 8, 10, 12, 13, 15, 18, 19, 20, 25, 30, 32, 35, 38,
        40, 45, 50, 55, 60, 63, 65, 75, 85,
      ].map((rate) => ({ value: String(rate), label: `${rate}%` })).concat([
        { value: "400", label: "附表 100%（條款提高為 400%）" },
      ]),
      guidance:
        "依本 productId 條款附表選擇手術百分率；未列手術或骨折、脫臼加成須由保險公司確認。",
    },
    fubon_group_hospital_daily_room_limit: {
      label: "每日病房費限額",
      type: "money",
      unit: "元／日",
      guidance: "依這個 productId 的保險金表輸入每日病房費用限額。",
    },
    fubon_group_hospital_ordinary_surgery_limit: {
      label: "普通手術費限額",
      type: "money",
      unit: "元",
      guidance: "依保險金表輸入普通手術費用限額。",
    },
    fubon_group_hospital_major_surgery_limit: {
      label: "重大手術費限額",
      type: "money",
      unit: "元",
      guidance: "依保險金表輸入重大手術費用限額。",
    },
    fubon_group_hospital_misc_limit: {
      label: "每次住院醫院雜費限額",
      type: "money",
      unit: "元／次住院",
      guidance: "依保險金表輸入每次住院醫院雜費限額。",
    },
    fubon_group_hospital_misc_daily_limit: {
      label: "雜費每日限額或日額替代金額",
      type: "non_negative_money",
      unit: "元／日",
      guidance: "依保險金表輸入每日金額；表內未列時可輸入 0。",
    },
    fubon_group_hospital_deductible: {
      label: "每次住院自負額",
      type: "non_negative_money",
      unit: "元／次住院",
      guidance: "依保險金表輸入每次住院自負額；沒有自負額時輸入 0。",
    },
    fubon_group_hospital_max_days: {
      label: "每次住院最高日數",
      type: "integer",
      max: 365,
      unit: "日",
      guidance: "依保險金表輸入這個計畫每次住院的最高日數。",
    },
    fubon_group_hospital_room_class: {
      label: "病房等級",
      type: "choice",
      options: [
        { value: "ordinary", label: "普通病房" },
        { value: "first_class", label: "一等病房" },
        { value: "private", label: "單人病房" },
        { value: "deluxe", label: "特等病房" },
      ],
      guidance: "依保險金表所列病房等級選擇。",
    },
    fubon_group_hospital_claim_mode: {
      label: "本次理賠方式",
      type: "choice",
      options: [
        { value: "reimbursement", label: "實支實付" },
        { value: "daily_cash", label: "住院醫療日額" },
        {
          value: "daily_cash_not_available",
          label: "此計畫不提供日額替代",
        },
        { value: "uncertain", label: "尚待確認" },
      ],
      guidance: "早期條款提供實支實付與日額二擇一；社保負額型不提供日額替代。",
    },
    fubon_new_group_hospital_event_claim_status: {
      label: "本次住院資格與申領方式",
      type: "choice",
      max_length: 64,
      options: [
        { value: "reimbursement_disease_after_waiting", label: "疾病已過等待期，申領實支實付" },
        { value: "reimbursement_injury", label: "意外傷害，申領實支實付" },
        { value: "reimbursement_newborn_screening_exception", label: "新生兒篩檢例外，申領實支實付" },
        { value: "daily_cash_disease_after_waiting", label: "疾病已過等待期，改領住院日額" },
        { value: "daily_cash_injury", label: "意外傷害，改領住院日額" },
        { value: "daily_cash_newborn_screening_exception", label: "新生兒篩檢例外，改領住院日額" },
        { value: "day_hospital_or_day_care", label: "日間住院、留院或照護" },
        { value: "post_expiry_readmission", label: "契約屆滿後再次住院" },
        { value: "disease_waiting_not_met", label: "疾病仍在 30 日等待期" },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "請依事故原因、附約生效或復效日、本次申領方式與這個 productId 的條款版本選擇；新生兒篩檢、日間住院及屆滿後再住院的處理會依版本判定。",
    },
    fubon_new_inpatient_daily_event_status: {
      label: "本次住院資格",
      type: "choice",
      max_length: 64,
      options: [
        { value: "eligible_disease_after_waiting", label: "疾病已過 30 日等待期" },
        { value: "eligible_accident", label: "意外傷害住院" },
        { value: "eligible_newborn_screening_exception", label: "符合本版新生兒篩檢例外" },
        { value: "day_hospital_or_day_stay", label: "日間住院或日間留院" },
        { value: "post_expiry_readmission", label: "附約屆滿後再次住院" },
        { value: "disease_waiting_not_met", label: "疾病仍在 30 日等待期" },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "請依事故原因、生效或復效日、住院型態與這個 productId 的條款版本選擇；新生兒篩檢、日間住院及屆滿後再住院會依版本判定。",
    },
    fubon_new_group_hospital_room_daily_limit: {
      label: "每日病房及膳食費用限額",
      type: "money",
      unit: "元／日",
      guidance: "請填這個 productId 保險單、名冊或批註所載的每日病房及膳食費用保險金限額。",
    },
    fubon_new_group_hospital_medical_limit: {
      label: "每次住院醫療費用限額",
      type: "money",
      unit: "元／次住院",
      guidance: "請填保險單所載每次住院醫療費用保險金限額；條款列舉的急診與住院前後門診也共用此限額。",
    },
    fubon_new_group_hospital_surgery_limit: {
      label: "每次外科手術費用限額",
      type: "money",
      unit: "元",
      guidance: "請填保險單所載每次外科手術費用保險金限額，系統會再乘手術附表百分率。",
    },
    fubon_new_group_hospital_max_days: {
      label: "病房及日額最高給付日數",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance: "請填保險單所載同一次住院病房費用及住院日額補償的最高給付日數。",
    },
    fubon_new_group_hospital_icu_daily_limit: {
      label: "每日加護病房費用限額",
      type: "money",
      unit: "元／日",
      guidance: "僅在保單有特別約定時，填入每日加護病房費用保險金限額。",
    },
    fubon_new_group_hospital_icu_max_days: {
      label: "加護病房最高給付日數",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance: "請填保險單所載同一次住院加護病房費用最高給付日數。",
    },
    fubon_new_group_hospital_burn_daily_limit: {
      label: "每日燒燙傷中心費用限額",
      type: "money",
      unit: "元／日",
      guidance: "僅在保單有特別約定時，填入每日燒燙傷中心費用保險金限額。",
    },
    fubon_new_group_hospital_burn_max_days: {
      label: "燒燙傷中心最高給付日數",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance: "請填保險單所載同一次住院燒燙傷中心費用最高給付日數。",
    },
    fubon_new_group_hospital_special_agreement_status: {
      label: "特殊病房特別約定",
      type: "choice",
      options: [
        { value: "both_included", label: "加護及燒燙傷中心都有約定" },
        { value: "icu_only", label: "只有加護病房約定" },
        { value: "burn_only", label: "只有燒燙傷中心約定" },
        { value: "neither_included", label: "兩項都沒有約定" },
      ],
      guidance: "請依保險單或批註確認；條款要求要保人與保險公司另有特別約定才可申領。",
    },
    mercantile_group_new_hospital_event_claim_status: {
      label: "本次住院申領方式與條款狀態",
      type: "choice",
      max_length: 64,
      options: [
        { value: "reimbursement", label: "提供收據正本，申領實支實付" },
        { value: "daily_cash", label: "無收據正本，改領住院日額" },
        { value: "day_hospital_or_day_care", label: "日間住院、留院或照護" },
        { value: "post_expiry_readmission", label: "契約屆滿後再次住院" },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "同一次住院只能在三項實支實付給付與住院日額之間擇一；日間住院及契約屆滿後再住院須依這個 product ID 的版本判斷。",
    },
    mercantile_group_new_hospital_room_daily_limit: {
      label: "每日病房費用保險金限額",
      type: "money",
      unit: "元／日",
      guidance:
        "僅適用未附數值限額表的早期版本；請從保險單、保險證、被保險人名冊或批註抄錄每日病房費用保險金限額。",
    },
    mercantile_group_new_hospital_medical_limit: {
      label: "每次住院醫療費用保險金基本限額",
      type: "money",
      unit: "元／次住院",
      guidance:
        "僅適用未附數值限額表的早期版本；請抄錄住院三十日內的基本限額。住院超過三十日時，系統會依條款按日比例換算，最高一百二十日。",
    },
    mercantile_group_new_hospital_surgery_base_limit: {
      label: "每次手術費用保險金基準限額",
      type: "money",
      unit: "元／次手術",
      guidance:
        "僅適用未附數值限額表的早期版本；請抄錄每次手術基準限額，系統會再乘本次手術在附表中的給付百分比。",
    },
    mercantile_group_daily_event_status: {
      label: "本次住院是否符合條款",
      type: "choice",
      max_length: 64,
      options: [
        { value: "eligible_inpatient", label: "符合條款的住院" },
        { value: "day_hospital_or_day_care", label: "日間住院或日間照護" },
        { value: "post_expiry_readmission", label: "契約屆滿後再次住院" },
        { value: "confirmed_not_eligible", label: "已確認不符合" },
        { value: "uncertain", label: "仍需保險公司確認" },
      ],
      guidance:
        "請依本次住院與這個 product ID 的條款版本選擇；系統會區分舊版尚待確認與新版明確排除的情形。",
    },
    mercantile_group_daily_max_hospital_days: {
      label: "最高住院給付日數",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance:
        "條款未固定這個數字，請從投保申請書、保險單、保險證或批註抄錄最高住院給付日數。",
    },
    mercantile_group_daily_surgery_option_status: {
      label: "手術醫療保險金是否納入",
      type: "choice",
      options: [
        { value: "included", label: "保單有納入" },
        { value: "not_included", label: "保單未納入" },
      ],
      guidance:
        "條款載明未選擇時本項條文刪除，請依投保資料或保險單確認。",
    },
    mercantile_group_daily_discharge_option_status: {
      label: "出院療養保險金是否納入",
      type: "choice",
      options: [
        { value: "included", label: "保單有納入" },
        { value: "not_included", label: "保單未納入" },
      ],
      guidance:
        "條款載明未選擇時本項條文刪除，請依投保資料或保險單確認。",
    },
    hospitalization_day_limit_per_stay: {
      label: "每次住院給付日數上限",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance:
        "請填保單首頁、批註、被保險人名冊或最近契約變更通知所載的每次住院最高給付日數。",
    },
    cathay_group_quanyi_daily_room_limit: {
      label: "保單記載每日病房費用限額",
      type: "money",
      unit: "元／日",
      guidance:
        "請填國泰人壽保單、被保險人名冊或書面約定所載的每日病房費用保險金限額。",
    },
    cathay_group_quanyi_max_hospital_days: {
      label: "保單記載最高給付日數",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance:
        "請填國泰人壽保單、被保險人名冊或書面約定所載的每日病房費用最高給付日數。",
    },
    cathay_group_quanyi_inpatient_medical_limit: {
      label: "保單記載每次住院醫療費用限額",
      type: "money",
      unit: "元／次住院",
      guidance:
        "請填國泰人壽保單、被保險人名冊或書面約定所載的每次住院醫療費用保險金限額。",
    },
    cathay_group_quanyi_nhi_status: {
      label: "本次醫療費用的健保給付狀態",
      type: "choice",
      options: [
        { value: "nhi_covered", label: "已由全民健康保險給付" },
        {
          value: "not_nhi_covered",
          label: "未以健保身分就醫或費用未經健保給付",
        },
      ],
      guidance:
        "未以健保身分就醫、非健保醫院治療或費用未經健保給付時，條款按符合項目的實際費用 65% 計算，仍受保單記載限額約束。",
    },
    cathay_group_quanyi_event_status: {
      label: "本次事故是否符合計畫的承保條件",
      type: "choice",
      options: [
        { value: "eligible_injury", label: "有效期間內的意外傷害" },
        {
          value: "eligible_disease_after_waiting",
          label: "疾病已符合所選計畫等待期",
        },
        {
          value: "eligible_newborn_screening_exception",
          label: "計畫 A 的新生兒篩檢疾病例外",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病尚未符合所選計畫等待期",
        },
        {
          value: "day_hospital_or_day_stay",
          label: "日間住院、日間留院或日間照護",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "資料不足，尚待確認" },
      ],
      guidance:
        "請依保單計畫、事故日期、疾病等待期及診斷資料選擇；不同 product ID 的新生兒篩檢例外範圍可能不同。",
    },
    cathay_group_warm_event_status: {
      label: "本次住院是否符合溫情附約條件",
      type: "choice",
      options: [
        {
          value: "eligible_disease_waiting_met",
          label: "疾病已符合 30 日等待期",
        },
        { value: "eligible_accident", label: "有效期間內的意外傷害" },
        {
          value: "eligible_newborn_screening_exception",
          label: "零歲投保的新生兒篩檢疾病例外",
        },
        {
          value: "day_hospital_or_day_stay",
          label: "日間住院、日間留院或日間照護",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病尚未符合 30 日等待期",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "資料不足，尚待確認" },
      ],
      guidance:
        "請依事故日期、疾病等待期、診斷及該 product ID 版本選擇；新生兒篩檢例外範圍會隨版本變更。",
    },
    cathay_group_warm_benefit_choice: {
      label: "本次住院申請的給付型別",
      type: "choice",
      options: [
        { value: "reimbursement", label: "實支實付型" },
        { value: "daily_cash", label: "住院日額型" },
      ],
      guidance:
        "同一次住院只能在每日病房費用與住院醫療費用的實支實付型，或住院日額型之間擇一。",
    },
    cathay_group_warm_nhi_status: {
      label: "本次醫療費用的健保給付狀態",
      type: "choice",
      options: [
        { value: "nhi_covered", label: "已由全民健康保險給付" },
        {
          value: "not_nhi_covered",
          label: "未以健保身分就醫或費用未經健保給付",
        },
      ],
      guidance:
        "未以健保身分就醫、非健保醫院住院或費用未經健保給付時，符合項目的實際費用按 65% 計算，仍受計畫限額約束。",
    },
    cathay_group_warm_icu_limit_rate: {
      label: "本次住院醫療費用限額倍率",
      type: "choice",
      options: [
        { value: "100", label: "一般住院：100%" },
        { value: "200", label: "曾入住加護病房：200%" },
      ],
      guidance:
        "只要本次住院期間曾入住加護病房，住院醫療費用保險金限額提高為計畫表金額的 2 倍。",
    },
    farglory_anjia_event_status: {
      label: "本次住院是否符合甲型附約條件",
      type: "choice",
      options: [
        {
          value: "eligible_disease_waiting_met",
          label: "疾病已符合 30 日等待期",
        },
        { value: "eligible_accident", label: "有效期間內的意外傷害" },
        {
          value: "eligible_newborn_screening_exception",
          label: "零歲投保的新生兒篩檢疾病例外",
        },
        {
          value: "day_hospital_or_day_care",
          label: "日間住院、日間留院或日間照護",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病尚未符合 30 日等待期",
        },
        { value: "confirmed_not_eligible", label: "已確認不符合條款" },
        { value: "uncertain", label: "資料不足，尚待確認" },
      ],
      guidance:
        "請依本 product ID 條款、事故日期、診斷書與住院證明選擇；新生兒篩檢與日間照護規則會依版本判斷。",
    },
    farglory_anjia_daily_room_limit: {
      label: "投保計畫每日住院病房限額",
      type: "money",
      unit: "元／日",
      guidance:
        "請從保險證、被保險人名冊、要保書或批註抄錄每日住院病房費用保險金限額；條款本身沒有列出金額表。",
    },
    farglory_anjia_daily_physician_limit: {
      label: "投保計畫每日醫師診查限額",
      type: "money",
      unit: "元／日",
      guidance:
        "請從保險證、被保險人名冊、要保書或批註抄錄每日醫師診查費用保險金限額。",
    },
    farglory_anjia_inpatient_medical_limit: {
      label: "投保計畫每次住院醫療限額",
      type: "money",
      unit: "元／次住院",
      guidance:
        "請從保險證、被保險人名冊、要保書或批註抄錄住院醫療費用保險金限額。",
    },
    farglory_anjia_surgery_base_limit: {
      label: "投保計畫外科手術基準限額",
      type: "money",
      unit: "元／次手術",
      guidance:
        "請從保險證、被保險人名冊、要保書或批註抄錄外科手術費用保險金給付限額；系統會再乘本次手術附表比例。",
    },
    farglory_anjia_hospital_day_limit: {
      label: "投保計畫每次住院給付日數上限",
      type: "integer",
      max: 9999,
      unit: "日",
      guidance:
        "請從保險證、被保險人名冊、要保書或批註抄錄每次住院最高給付日數；一般病房與加護病房日數合計不得超過此數。",
    },
    reimbursement_limit: {
      label: "保單記載實支實付限額",
      type: "money",
      unit: "元",
      guidance: "請填保單首頁、批註或計畫表列示的每次/每年實支實付限額。",
    },
    medical_claim_receipt_status: {
      label: "本次是否能提供醫療費用收據正本",
      type: "choice",
      options: [
        { value: "original_receipt", label: "可以提供收據正本" },
        {
          value: "no_original_receipt_daily_cash",
          label: "無法提供，依條款改領日額與門診給付",
        },
      ],
      guidance:
        "請依本次申請文件選擇；選擇無收據替代方式時，同一次事故不再計算手術與住院醫療實支實付保險金。",
    },
    overseas_medical_region_factor_percent: {
      label: "海外就醫地區",
      type: "choice",
      options: [
        { value: "300", label: "美國或加拿大（限額 300%）" },
        { value: "150", label: "歐洲、澳洲、紐西蘭或日本（限額 150%）" },
        { value: "100", label: "其他海外地區（限額 100%）" },
      ],
      guidance:
        "請依本次海外就醫地點選擇；返國後在台灣接受的醫療不在本附約海外醫療給付範圍內。",
    },
    injury_medical_rider_status: {
      label: "是否有傷害醫療附加保障",
      type: "choice",
      options: [
        { value: "included", label: "保單有記載此項保障" },
        { value: "not_included", label: "保單未附加此項保障" },
      ],
      guidance: "請查看保單首頁、批註或保障明細，確認是否有傷害醫療或實支實付傷害醫療保障。",
    },
    prior_same_insurer_major_burn_claim_status: {
      label: "同公司重大燒燙傷保險金過去給付狀態",
      type: "choice",
      options: [
        { value: "not_paid", label: "過去未曾給付" },
        { value: "paid", label: "過去已曾給付" },
      ],
      guidance:
        "本項條款約定同一被保險人在同一保險公司的重大燒燙傷保險金以一次為限；請依理賠紀錄選擇。",
    },
    same_insurer_other_major_burn_benefit_amount: {
      label: "同公司其他保單本次重大燒燙傷條款金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請加總同一被保險人在同一保險公司其他契（附）約，依各自條款對本次重大燒燙傷算出的金額；沒有其他保單請輸入 0。若加總超過跨契約上限，實際分配仍須由保險公司確認。",
    },
    injury_medical_expense: {
      label: "本次傷害醫療實際自付費用",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據與條款可列入範圍，填入扣除全民健康保險給付後的實際自付費用；沒有可填 0。",
    },
    prior_disability_benefit_paid_amount: {
      label: "本保單過去已領失能／殘廢保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填本保單過去已領或依條款視同已領的失能／殘廢保險金合計；尚未領取請填 0。",
    },
    disability_support_claim_status: {
      label: "要查看的給付情境",
      type: "choice",
      options: [
        { value: "monthly_entitlement", label: "一至六級殘廢扶助月給付" },
        { value: "death_during_payment", label: "給付期間身故的未支領餘額" },
      ],
      guidance: "先選擇要試算每月扶助金，或給付期間身故後由保險公司折現的一次給付。",
    },
    disability_grade: {
      label: "本次／合併後殘廢等級",
      type: "choice",
      options: [
        { value: "1", label: "第 1 級" },
        { value: "2", label: "第 2 級" },
        { value: "3", label: "第 3 級" },
        { value: "4", label: "第 4 級" },
        { value: "5", label: "第 5 級" },
        { value: "6", label: "第 6 級" },
      ],
      guidance: "請依本商品版本附表及保險公司的事故認定，選擇本次事故或與既往殘廢合併後的等級。",
    },
    disability_status_after_180_days: {
      label: "殘廢確定滿 180 日後狀態",
      type: "choice",
      options: [
        { value: "persisting", label: "殘廢狀態仍持續存在" },
        { value: "not_persisting", label: "殘廢狀態未持續存在" },
        { value: "uncertain", label: "尚待醫療或理賠確認" },
      ],
      guidance: "條款要求自確定殘廢日起 180 日後狀態仍持續存在；尚未確認時不會直接估成可領。",
    },
    other_disability_support_monthly_amount: {
      label: "同一保險公司其他同類月給付",
      type: "non_negative_money",
      unit: "元／月",
      guidance: "請填同一被保險人在同一保險公司其他可申請的一至六級殘廢扶助保險金月給付合計；沒有請填 0，用來套用每月合計 10 萬元上限。",
    },
    prior_disability_status: {
      label: "是否有可合併計算的既往殘廢",
      type: "choice",
      options: [
        { value: "none", label: "沒有" },
        { value: "exists", label: "有，需套用扣除與最低保障規則" },
      ],
      guidance: "若以前的殘廢會與本次殘廢合併成較嚴重等級，請選擇「有」。",
    },
    insurer_approved_remaining_disability_support_months: {
      label: "保險公司核定的剩餘給付月數",
      type: "integer",
      allow_zero: true,
      max: 100,
      unit: "個月",
      guidance: "有既往殘廢時，條款涉及視同已給付及不得低於單獨請領的併合判定；請填保險公司核定後的剩餘月數，不由系統自行判級。",
    },
    discounted_unpaid_disability_support_amount: {
      label: "保險公司列示的未支領餘額折現金額",
      type: "non_negative_money",
      unit: "元",
      guidance: "條款只指定以預定利率 2% 計算現值；請填保險公司依剩餘期數與給付日正式列示的一次給付金額，未發生請勿選此情境。",
    },
    discounted_cancer_living_support_balance_amount: {
      label: "癌症生活扶助未支領餘額貼現金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在生活扶助給付期間身故或達條款約定年齡時填寫；請輸入保險公司依該保單版本貼現率正式列示的金額，其他情況請填 0。",
    },
    same_accident_prior_disability_benefit_paid_amount: {
      label: "同一事故先前已領失能／殘廢保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "只有同一意外事故先失能／殘廢、後續再身故時需要扣除；尚未領取請填 0。",
    },
    prior_same_injury_medical_benefit_paid_amount: {
      label: "同一次傷害先前已領醫療保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填同一次傷害在本次申請前已領的傷害醫療保險金；尚未領取請填 0。",
    },
    hospitalization_days: {
      label: "本次住院日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請依診斷書、住院證明或理賠文件填寫條款可計入的住院日數；沒有此項事故可填 0。",
    },
    china_new_lohas_eligible_hospital_daily_days: {
      label: "本次可計入住院日額天數",
      type: "integer",
      allow_zero: true,
      max: 365,
      unit: "日",
      guidance:
        "請依這個 product ID 的條款與理賠文件填寫。早期 ANHRL／BNHRL 版本於醫院持續治療達六小時（含）以上可計一日；CNHRL 以後版本只填實際住院日數，沒有可填 0。",
    },
    general_ward_days: {
      label: "本次一般病房日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance:
        "請填本次住院中實際住一般病房的日數；與加護病房日數合計不得超過本次住院日數，沒有可填 0。",
    },
    intensive_care_days: {
      label: "本次加護病房日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請依住院證明或理賠文件填寫本次實際住進加護病房的日數；沒有可填 0。",
    },
    burn_unit_days: {
      label: "本次燒燙傷病房日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請依住院證明或理賠文件填寫本次實際住進燒燙傷病房的日數；沒有可填 0。",
    },
    home_recuperation_days: {
      label: "本次居家療養可計日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance:
        "請填保險公司依本次加護病房或燒燙傷病房治療日數核定的居家療養日數；同一日不得重複計入，沒有可填 0。",
    },
    hongtai_group_fixed_event_status: {
      label: "本次住院事故資格",
      type: "choice",
      options: [
        {
          value: "eligible_disease_after_waiting",
          label: "疾病且已超過等待期",
        },
        {
          value: "eligible_nonoccupational_accident",
          label: "非職業傷害的意外事故",
        },
        {
          value: "eligible_occupational_injury",
          label: "條款所稱職業傷害",
        },
        {
          value: "eligible_newborn_screening_exception",
          label: "零歲投保的新生兒篩檢例外",
        },
        {
          value: "disease_waiting_not_met",
          label: "疾病仍在等待期內",
        },
        {
          value: "confirmed_not_eligible",
          label: "已確認不符合條款",
        },
        { value: "uncertain", label: "尚待保險公司確認" },
      ],
      guidance:
        "請依診斷書、事故原因及這個 product ID 的條款選擇；職業傷害會使四項每日醫療保險金提高為 1.5 倍，手術給付不適用此加成。",
    },
    hongtai_group_fixed_surgery_addendum_status: {
      label: "是否附加手術醫療條款",
      type: "choice",
      options: [
        { value: "attached", label: "保單已附加" },
        { value: "not_attached", label: "保單未附加" },
      ],
      guidance:
        "請查看保單、保險證或批註是否附加住院／門診手術醫療條款；未確認前請勿用其他版本手術表代算。",
    },
    hospital_transfer_count: {
      label: "本次符合條款的住院轉診次數",
      type: "integer",
      allow_zero: true,
      max: 1,
      unit: "次",
      guidance:
        "同一住院期間若同日由前一醫院出院並轉入後一醫院，請填 1；沒有符合的轉診請填 0。",
    },
    intensive_care_or_burn_unit_days: {
      label: "本次加護病房或燒燙傷中心可計入日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance:
        "請填符合該商品條款的加護病房或燒燙傷中心日數；同一日同時符合兩者時只計一次，沒有可填 0。",
    },
    cancer_hospitalization_days: {
      label: "本次癌症住院日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "僅填符合條款癌症定義的本次住院日數；不是癌症住院可填 0。",
    },
    taiwan_new_cancer_home_recovery_claim_count: {
      label: "本保險年度本次要計算的在家療養給付次數",
      type: "integer",
      allow_zero: true,
      max: 3,
      unit: "次",
      guidance:
        "請填本保險年度中符合連續住院六日以上、出院在家療養條件的次數；條款每年度最多三次。",
    },
    taiwan_new_cancer_health_event_status: {
      label: "這次要查看的新防癌保障情境",
      type: "choice",
      max_length: 64,
      options: [
        { value: "eligible_cancer_hospitalization", label: "符合條款的癌症住院" },
        { value: "eligible_home_recovery", label: "癌症住院六日以上後在家療養" },
        { value: "eligible_cancer_death", label: "首次罹患癌症並因癌身故" },
        {
          value: "diagnosed_within_initial_waiting_period",
          label: "生效後九十日內首次確診，查看退費",
        },
        {
          value: "eligible_non_cancer_death_refund",
          label: "非因癌症身故，查看當年度保費退還",
        },
        { value: "not_eligible_or_uncertain", label: "尚未確認符合，或沒有本次事故" },
      ],
      guidance:
        "請依診斷日、住院原因、身故原因與這個 productId 版本選擇；第 1 至 7 次修訂另有復效日起十日等待期。",
    },
    taiwan_new_cancer_policy_form: {
      label: "保險單形式",
      type: "choice",
      options: [
        { value: "individual", label: "個人保險單" },
        { value: "family", label: "家庭保險單" },
      ],
      guidance:
        "僅在查看非癌身故退還金時依保單面頁選擇；家庭保險單依條款退還當年度已繳保費總額的半數。",
    },
    current_policy_year_paid_premium_amount: {
      label: "當年度已繳保險費總額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依繳費紀錄或保險公司列示金額輸入本保險單當年度已繳保費總額，不要用投保單位自行推估。",
    },
    taiwan_new_cancer_waiting_refund_amount: {
      label: "等待期間內確診應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在生效日起九十日內首次確診時填寫；請輸入保單繳費紀錄或保險公司核算的已收保險費。",
    },
    taiwan_cancer_insurance_event_status: {
      label: "這次要查看的防癌保障情境",
      type: "choice",
      max_length: 64,
      options: [
        { value: "eligible_cancer_hospitalization", label: "符合條款的癌症住院" },
        {
          value: "eligible_posthumous_cancer_diagnosis",
          label: "身故後解剖證明罹癌，追溯住院給付",
        },
        {
          value: "diagnosed_within_initial_waiting_period",
          label: "生效後九十日內確診，查看退費",
        },
        {
          value: "precontract_unaware_cancer_premium_refund",
          label: "投保前已罹癌但當時不知情，查看退費",
        },
        { value: "not_eligible_or_uncertain", label: "尚未確認符合，或沒有本次事故" },
      ],
      guidance:
        "請依診斷、住院、身故後解剖結果與這個 productId 版本選擇；第 0 至 7 次修訂另有復效日起十日等待期。",
    },
    taiwan_cancer_waiting_refund_amount: {
      label: "等待期間內確診應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在生效日起九十日內確診時填寫；請依繳費紀錄或保險公司核算金額輸入。",
    },
    taiwan_cancer_precontract_refund_amount: {
      label: "投保前未知癌症應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在投保前已曾診斷癌症、醫師未告知且當事人不知情時填寫；請依繳費紀錄或保險公司核算金額輸入。",
    },
    prudential_youhuo_event_status: {
      label: "這次要查看的優活保障情境",
      type: "choice",
      max_length: 64,
      options: [
        { value: "eligible_medical_benefit", label: "符合條款的住院或手術醫療" },
        {
          value: "eligible_newborn_screening_exception",
          label: "零歲投保的新生兒篩檢疾病例外",
        },
        {
          value: "eligible_initial_critical_or_specific_illness",
          label: "初次符合重大疾病或特定傷病",
        },
        {
          value: "initial_30_day_sickness_death_refund",
          label: "生效後三十日內疾病身故，查看退費",
        },
        {
          value: "death_unexpired_premium_refund",
          label: "身故終止，查看未到期保費退還",
        },
        { value: "disease_waiting_not_met", label: "一般疾病仍在三十日等待期內" },
        {
          value: "major_disease_waiting_not_met",
          label: "重大疾病或特定傷病仍在等待期內",
        },
        { value: "not_eligible_or_uncertain", label: "尚未確認符合，或沒有本次事故" },
      ],
      guidance:
        "請依診斷、住院、手術、生效或復效日及 exact product ID 條款版本選擇；各版疾病定義與等待期不同。",
    },
    prudential_youhuo_bonus_factor_percent: {
      label: "理賠加值資格",
      type: "choice",
      options: [
        { value: "100", label: "不符合或尚未確認：按原金額 100%" },
        {
          value: "130",
          label: "連續三個保單年度無約定事故且符合條款：按 130%",
        },
      ],
      guidance:
        "僅住院、加護、住院或門診手術、手術看護及舊版緊急轉送適用；不確定時先向保險公司確認。",
    },
    prudential_youhuo_surgery_rate_percent: {
      label: "本次住院手術附表總比率",
      type: "rate",
      min: 1,
      max: 490,
      step: "1",
      unit: "%",
      guidance:
        "請查 exact product ID 手術附表並依同次住院合併規則輸入；舊版最高 300%，第 8 版起最高 490%。",
    },
    prudential_youhuo_initial_sickness_death_refund_amount: {
      label: "生效後三十日內疾病身故應退還的已收保費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在生效後三十日內因疾病身故時填寫；請依繳費紀錄或保險公司核算金額輸入。",
    },
    cancer_benefit_category: {
      label: "本次癌症給付類型",
      type: "choice",
      options: [
        {
          value: "reduced_benefit_cancer",
          label: "條款列示按較低比例給付的初期癌症／原位癌等",
        },
        {
          value: "full_benefit_hospice_excluded",
          label: "診斷與治療全額，但不符合安寧照護癌別條件",
        },
        {
          value: "full_benefit_cancer",
          label: "其他全額給付且符合安寧照護癌別條件的癌症",
        },
      ],
      guidance: "請依這個商品版本條款對癌症類型的定義選擇；不同版本對初期癌症及皮膚癌的分類可能不同。",
    },
    farglory_new_cancer_99_event_status: {
      label: "這次要查看的癌症保障情境",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "eligible_reduced_diagnosis",
          label: "首次符合較低給付癌症定義",
        },
        {
          value: "eligible_full_diagnosis",
          label: "首次符合全額給付癌症定義",
        },
        {
          value: "eligible_cancer_treatment",
          label: "符合條款的癌症住院或治療",
        },
        {
          value: "diagnosed_within_applicable_waiting_period",
          label: "適用等待期內確診，查看退費",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
      ],
      guidance:
        "請先依診斷日、保單生效／復效日與該 productId 版本的癌症定義選擇。舊版復效後仍有 90 日等待期，後期版本復效日起即恢復保障。",
    },
    farglory_new_cancer_99_cumulative_paid_amount: {
      label: "事故前已占用癌症醫療給付上限的累計金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依遠雄人壽理賠紀錄，填入本次事故前第 11 至 20 條已給付、會占用終身上限的累計金額；尚未領取請填 0。",
    },
    farglory_new_cancer_99_waiting_refund_amount: {
      label: "等待期內確診應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在適用等待期內確診時填寫；請輸入保單繳費紀錄或保險公司列示的本附約已收全部保險費，不要自行用單位數推估。",
    },
    china_new_kangjian_97_event_status: {
      label: "這次要查看的新康健防癌保障情境",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "eligible_in_situ_diagnosis",
          label: "首次符合原位癌定義",
        },
        {
          value: "eligible_full_diagnosis",
          label: "首次符合完整癌症定義",
        },
        {
          value: "eligible_specified_cancer_diagnosis",
          label: "首次符合條款列示的特定癌症",
        },
        {
          value: "eligible_cancer_treatment",
          label: "符合條款的癌症住院或治療",
        },
        {
          value: "eligible_cancer_death",
          label: "因癌症身故",
        },
        {
          value: "eligible_terminal_death_advance",
          label: "符合癌症身故保險金提前給付",
        },
        {
          value: "diagnosed_within_applicable_waiting_period",
          label: "適用等待期內確診，查看退費",
        },
        {
          value: "eligible_non_cancer_death_refund",
          label: "非因癌症身故，查看未到期保費退還",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "尚未確認符合，或沒有本次事故",
        },
      ],
      guidance:
        "請依診斷日、保單生效或復效日、身故原因與這個 productId 版本選擇。早期版本復效後仍有 90 日等待期，後期版本復效日起即恢復保障。",
    },
    china_new_kangjian_97_cumulative_paid_amount: {
      label: "事故前已占用終身給付上限的累計金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依凱基人壽（原中國人壽）理賠紀錄，填入本次事故前已給付且會占用本商品終身累積總給付上限的金額；尚未領取請填 0。",
    },
    china_new_kangjian_97_waiting_refund_amount: {
      label: "等待期內確診應退還的已收保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在適用等待期內確診時填寫；請輸入保單繳費紀錄或保險公司列示的本契約已收保險費，不要自行用投保單位推估。",
    },
    china_new_kangjian_97_unexpired_premium_refund_amount: {
      label: "非因癌症身故應退還的未到期保險費",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅在被保險人非因癌症身故時填寫；請以保險公司依繳別及身故日核算的未到期保險費為準。",
    },
    china_new_kangjian_97_bone_marrow_transplant_count: {
      label: "本次符合的癌症骨髓移植次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "請依本次實際接受且符合條款的骨髓移植次數填寫；條款未明列終身一次上限，不要自行限制為 1。",
    },
    china_new_kangjian_97_prosthetic_limb_count: {
      label: "本次符合的義肢裝設肢數",
      type: "integer",
      allow_zero: true,
      max: 4,
      unit: "肢",
      guidance:
        "每一肢終身限給付一次，四肢合計最多 4；請扣除過去已領取的肢數後填入本次可給付肢數。",
    },
    china_new_kangjian_97_denture_count: {
      label: "本保單年度符合的義齒裝設次數",
      type: "integer",
      allow_zero: true,
      max: 1,
      unit: "次",
      guidance:
        "同一保單年度最多給付一次；本年度符合且尚未領取請填 1，否則填 0。",
    },
    prior_cancer_diagnosis_benefit_paid_amount: {
      label: "本次事故前已領罹患癌症保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填同一保單在本次確診前已領取的罹患癌症保險金總額；尚未領取請填 0。",
    },
    cancer_surgery_count: {
      label: "本次可計入癌症手術次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance: "請依條款的同一癌症、手術位置及間隔日數規則填入可計入的手術次數；沒有可填 0。",
    },
    inpatient_surgery_count: {
      label: "本次可計入住院手術次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "請依條款的手術位置、同一手術及保單年度限制，填入本次實際可給付的住院手術次數；沒有可填 0。",
    },
    specific_surgery_count: {
      label: "本次符合特定手術的次數",
      type: "integer",
      allow_zero: true,
      max: 1,
      unit: "次",
      guidance:
        "請依本商品版本的特定手術附表確認；本次符合請填 1，不符合或未施作請填 0。",
    },
    outpatient_surgery_count: {
      label: "本次可計入門診手術次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "請依條款與手術證明填入本次實際可給付的門診手術次數；沒有可填 0。",
    },
    cancer_bone_marrow_transplant_count: {
      label: "本次符合的癌症骨髓移植次數",
      type: "integer",
      allow_zero: true,
      max: 1,
      unit: "次",
      guidance:
        "本項終身限給付一次；本次符合且過去未領取請填 1，否則填 0。",
    },
    cancer_inpatient_surgery_hospitalization_count: {
      label: "本年度可計入癌症住院手術的住院次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "請依條款的每次住院期間定義，填入本年度因癌症或其併發症住院並接受手術的可給付住院次數；同一次住院期間只計一次，沒有可填 0。",
    },
    cancer_post_discharge_outpatient_visit_count: {
      label: "本年度可計入癌症出院後門診次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "請填同一保單年度內，因癌症住院出院後依醫師囑咐繼續治療的可給付門診次數；系統會依條款最多計入 70 次，沒有可填 0。",
    },
    cancer_outpatient_treatment_days: {
      label: "本次癌症門診治療日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請填符合條款的實際門診治療日數；同日多次門診仍依條款以一日計，沒有可填 0。",
    },
    cancer_radiation_treatment_days: {
      label: "本次癌症放射線治療日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請填符合條款的實際放射線治療日數；同日多次治療仍依條款以一日計，沒有可填 0。",
    },
    cancer_chemotherapy_treatment_days: {
      label: "本次癌症化學治療日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請填符合條款的實際化學治療日數；同日多次治療仍依條款以一日計，沒有可填 0。",
    },
    cancer_radiochemotherapy_treatment_count: {
      label: "本次可計入放射線／化學治療次數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "次",
      guidance:
        "同一天接受放射線與化學治療或多次治療只計 1 次；口服化療每張處方只計 1 次，不按處方天數重複計算。",
    },
    cancer_breast_reconstruction_side_count: {
      label: "本次符合的義乳重建側數",
      type: "integer",
      allow_zero: true,
      max: 2,
      unit: "側",
      guidance:
        "請填本次接受且過去未就同側領取的義乳重建側數，最多 2 側；沒有可填 0。",
    },
    cancer_prosthetic_limb_count: {
      label: "本次符合的癌症義肢裝設次數",
      type: "integer",
      allow_zero: true,
      max: 1,
      unit: "次",
      guidance:
        "本項終身限給付一次；本次符合且過去未領取請填 1，否則填 0。",
    },
    cancer_hospice_anniversary_count: {
      label: "符合癌症安寧照護給付的周年次數",
      type: "integer",
      allow_zero: true,
      max: 5,
      unit: "次",
      guidance: "請填罹患確定日後仍生存且符合條款的第 1 至第 5 個周年次數；尚未到周年或不符合可填 0。",
    },
    cancer_living_support_anniversary_count: {
      label: "已符合癌症生活扶助給付的周年次數",
      type: "integer",
      allow_zero: true,
      max: 5,
      unit: "次",
      guidance:
        "請依診斷確定日後已符合條款的保單周年次數填 0 至 5；尚未到周年或改以未支領餘額貼現給付時填 0。",
    },
    home_care_eligible_days: {
      label: "本次符合居家療養給付日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請依本次出院及條款資格填入可計入居家療養看護給付的日數；不符合可填 0。",
    },
    inpatient_medical_expense_days: {
      label: "本次符合住院醫療雜費給付日數",
      type: "integer",
      allow_zero: true,
      max: 3650,
      unit: "日",
      guidance: "請填本次住院中符合條款列舉醫療費用的日數；沒有可填 0。",
    },
    outpatient_visit_count: {
      label: "本次可計入門診次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance: "請依條款期間與每日次數限制，填入本次可計入的實際門診次數；沒有可填 0。",
    },
    post_discharge_outpatient_visit_count: {
      label: "出院後可計入門診次數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "次",
      guidance:
        "僅適用以實際門診次數計算的舊版條款；請填出院後二週內、經醫師囑咐繼續治療且符合條款的門診次數，沒有可填 0。",
    },
    post_discharge_outpatient_day_count: {
      label: "出院後可計入門診日數",
      type: "integer",
      allow_zero: true,
      max: 1000,
      unit: "日",
      guidance:
        "適用以實際門診日數計算的版本；請填出院後二週內、經醫師囑咐繼續治療的門診日數，同日多次只計一日，沒有可填 0。",
    },
    inpatient_medical_expense: {
      label: "本次住院醫療實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據與條款可列入範圍填寫本次住院醫療實際支出；沒有可填 0。",
    },
    day_hospital_medical_expense: {
      label: "本次日間住院醫療實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依日間住院收據及本版本條款可列入範圍填寫實際支出；沒有可填 0。",
    },
    day_hospital_days: {
      label: "本次日間住院日數",
      type: "integer",
      allow_zero: true,
      max: 365,
      unit: "日",
      guidance:
        "請依診斷書或住院證明填寫本次日間住院日數；沒有可填 0。",
    },
    day_hospital_daily_cash_amount: {
      label: "保單列示的日間住院每日替代日額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "公開條款未列固定日額；請依實際保單、保險證或保險公司理賠試算所列每日金額填寫。",
    },
    hospital_medical_claim_mode: {
      label: "本次住院型態與其他實支實付保險告知狀態",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "inpatient",
          label: "一般住院",
        },
        {
          value: "day_hospital_no_other_or_notified",
          label: "日間住院，沒有其他同類保險或投保時已告知",
        },
        {
          value: "day_hospital_unnotified_other_reimbursement",
          label: "日間住院，投保時未告知其他同類實支實付保險",
        },
      ],
      guidance:
        "新版條款對日間住院另有處理方式；若屬日間住院，請依要保文件、保單及保險公司確認當時是否已告知其他同類實支實付保險。",
    },
    reimbursement_or_daily_cash_choice: {
      label: "本次住院申領方式",
      type: "choice",
      options: [
        { value: "reimbursement", label: "實支實付型" },
        { value: "daily_cash", label: "日額給付型" },
      ],
      guidance:
        "條款約定同一次住院只能擇一申領；請依本次理賠選擇實支實付型或日額給付型。",
    },
    prudential_new_hospital_event_status: {
      label: "本次醫療是否符合住院條件",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "eligible_formal_hospitalization",
          label: "經醫師診斷並正式住院治療",
        },
        {
          value: "eligible_six_hour_continuous_treatment",
          label: "在醫院持續治療達六小時以上",
        },
        {
          value: "day_hospital_or_day_care",
          label: "日間住院或日間照護",
        },
        {
          value: "confirmed_not_eligible",
          label: "已確認不符合條款住院條件",
        },
        {
          value: "not_eligible_or_uncertain",
          label: "資料不足，尚待保險公司確認",
        },
      ],
      guidance:
        "請依診斷書、住院證明及這個 product ID 對應條款選擇；新版已刪除六小時持續治療並明文排除日間住院時，系統會判定不符合。",
    },
    hospital_room_expense: {
      label: "本次符合條款的病房費用總額",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據填寫條款可列入的一般病房、膳食、護理及診察等費用總額；沒有可填 0。",
    },
    intensive_care_room_expense: {
      label: "本次符合條款的加護病房費用總額",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據填寫條款可列入的加護病房實際費用總額；沒有可填 0。",
    },
    burn_unit_room_expense: {
      label: "本次符合條款的燒燙傷中心費用總額",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據填寫條款可列入的燒燙傷中心實際費用總額；沒有可填 0。",
    },
    physician_examination_expense: {
      label: "本次符合條款的醫師診查費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依醫療費用收據填寫住院期間符合條款的醫師診查費總額；沒有可填 0。",
    },
    surgery_medical_expense: {
      label: "本次符合條款的外科手術費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請依醫療費用收據填寫本次住院或門診手術符合條款的實際費用；同次多項或同一部位手術仍須依條款附表分別確認。",
    },
    inpatient_surgery_expense: {
      label: "本次住院手術實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據填寫條款可列入的本次住院手術費用；同次多項手術請依條款分別計算。",
    },
    outpatient_surgery_expense: {
      label: "本次門診手術實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據與條款可列入範圍填寫本次門診手術實際支出；沒有可填 0。",
    },
    outpatient_medical_expense: {
      label: "本次住院前後門診實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請加總本次住院前七日及出院後十四日內，因同一疾病或傷害且符合條款的門診費用；沒有可填 0。",
    },
    outpatient_surgery_medical_expense: {
      label: "本次門診手術其他醫療實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填門診手術當日除手術費外、符合條款住院醫療費用項目的實際支出；沒有可填 0。",
    },
    special_procedure_expense: {
      label: "本次特定處置實際費用",
      type: "non_negative_money",
      unit: "元",
      guidance: "請依收據與條款可列入範圍填寫本次特定處置實際支出；沒有可填 0。",
    },
    national_health_insurance_payment_status: {
      label: "本次費用是否經條款所稱社會保險／健保給付",
      type: "choice",
      options: [
        { value: "covered", label: "已經條款所稱社會保險／健保給付" },
        { value: "not_covered", label: "未經條款所稱社會保險／健保給付" },
      ],
      guidance: "請依該商品版本條款、醫療收據及理賠文件確認；舊版可能使用社會保險用語，未經給付時可能套用較低比例。",
    },
    bank_taiwan_legacy_reimbursement_eligibility_status: {
      label: "本次是否同時符合條款所稱社會保險身分及收據正本要件",
      type: "choice",
      max_length: 64,
      options: [
        {
          value: "social_insurance_and_original_receipt",
          label: "同時符合社會保險身分及收據正本要件",
        },
        {
          value: "missing_social_insurance_or_original_receipt",
          label: "任一要件不符合，應改選日額型",
        },
        { value: "uncertain", label: "尚待確認" },
      ],
      guidance:
        "最早版實支實付型須同時符合條款所稱社會保險身分與醫療費用收據正本；任一不符時請改選日額型。",
    },
    prudential_new_hospital_social_insurance_factor_60_percent: {
      label: "本次費用是否經舊版條款所稱社會保險分攤",
      type: "choice",
      options: [
        {
          value: "100",
          label: "有社會保險分攤：按各項原限額 100%",
        },
        {
          value: "60",
          label: "無社會保險分攤：各項限額降為 60%",
        },
      ],
      guidance:
        "僅適用最早版本。請依醫療收據與理賠文件選擇；這個比例調整的是各項條款限額，不是把實際費用先乘比例。",
    },
    prudential_new_hospital_nhi_factor_65_percent: {
      label: "本次費用是否經全民健康保險分攤",
      type: "choice",
      options: [
        {
          value: "100",
          label: "有全民健康保險分攤：按各項原限額 100%",
        },
        {
          value: "65",
          label: "無全民健康保險分攤：各項限額降為 65%",
        },
      ],
      guidance:
        "請依醫療收據與理賠文件選擇；這個比例調整的是各項條款限額，不是把實際費用先乘比例。",
    },
    annual_medical_benefit_paid_amount: {
      label: "本保單年度已領醫療保險金",
      type: "non_negative_money",
      unit: "元",
      guidance: "請填本保單年度在本次事故前已領取的醫療保險金總額；尚未領取請填 0。",
    },
    surgery_benefit_rate_percent: {
      label: "本次手術給付比例",
      type: "rate",
      unit: "%",
      guidance: "請依條款手術附表找到本次手術項目的給付比例，例如附表列 17.5% 就輸入 17.5。",
    },
    surgery_total_benefit_rate_percent: {
      label: "本次住院手術合計給付比例",
      type: "rate",
      unit: "%",
      guidance:
        "請依同一次住院內各項手術的條款附表比例合計後輸入；同一手術位置只取較高項，且本商品每次住院合計最高 500%。",
    },
    surgery_benefit_multiplier: {
      label: "本次手術附表給付倍數",
      type: "integer",
      max: 1200,
      unit: "倍",
      guidance:
        "請依這個商品版本的手術附表輸入本次手術項目所列整數倍數；附表未列且需與保險公司協議比照者，請先向保險公司確認後再填。",
    },
    taiwan_yongjian_surgery_multiplier: {
      label: "本次手術附表給付倍數",
      type: "integer",
      max: 50,
      unit: "倍",
      guidance:
        "請依這個 product ID 的永健住院醫療手術附表輸入 1 至 50 倍；附表未列者須先依全民健保支付點數確認，少於 1 倍不給付。",
    },
    taiwan_wenxin_no_claim_factor_percent: {
      label: "溫心附約無理賠增額資格",
      type: "choice",
      options: [
        {
          value: "100",
          label: "未符合前三個保單年度無理賠：按原金額 100%",
        },
        {
          value: "130",
          label: "前三個保單年度（含）無理賠且持續有效：按 130%",
        },
      ],
      guidance:
        "請依理賠事故日前三個保單年度是否曾發生本附約理賠事故選擇；不確定時請先向保險公司確認。",
    },
    taiwan_wenxin_icu_status: {
      label: "本次住院是否住進加護病房",
      type: "choice",
      options: [
        { value: "not_admitted", label: "未住進加護病房" },
        { value: "admitted", label: "有住進加護病房" },
      ],
      guidance:
        "溫心附約的住院醫療費用限額在住進加護病房時提高為二倍；請依住院證明或理賠文件選擇。",
    },
    surgery_benefit_multiplier_decimal: {
      label: "本次手術附表給付倍數",
      type: "number",
      max: 1200,
      step: 0.01,
      unit: "倍",
      guidance:
        "請依這個 product ID 對應條款的手術附表輸入倍數；可輸入 0.25、0.5、0.75 等小數，不可套用其他版本的附表。",
    },
    minor_paid_premium_interest_refund_amount: {
      label: "未滿 16 歲身故的保費加息返還金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "僅未滿 16 歲身故時使用；請填保險公司按條款已繳保費與年利率 2.25% 計算後正式列示的返還金額。",
    },
    terminal_illness_advance_amount: {
      label: "末期疾病提前給付金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填保險公司依末期疾病診斷、事故原因及身故給付路徑核定的提前給付金額。",
    },
    surgery_care_setting: {
      label: "本次手術是否住院",
      type: "choice",
      options: [
        { value: "inpatient", label: "住院期間接受手術" },
        { value: "outpatient", label: "門診或未住院手術" },
      ],
      guidance:
        "請依住院證明與手術紀錄選擇；手術醫療保險金可涵蓋醫院或診所手術，住院手術療養保險金只適用住院手術。",
    },
    wound_suture_benefit_rate_percent: {
      label: "意外創傷縫合給付比例",
      type: "choice",
      options: [
        { value: "50", label: "傷口 10 公分以下（含）：50%" },
        { value: "100", label: "傷口超過 10 公分：100%" },
      ],
      guidance:
        "同一次意外只取接受縫合處置的最大傷口，依本商品附表選擇 50% 或 100%。",
    },
    no_claim_bonus_rate_percent: {
      label: "無理賠紀錄增額比例",
      type: "choice",
      options: [
        { value: "0", label: "未滿 3 年：不適用" },
        { value: "20", label: "3 年以上、未滿 4 年：20%" },
        { value: "30", label: "4 年以上、未滿 5 年：30%" },
        { value: "40", label: "5 年以上、未滿 6 年：40%" },
        { value: "50", label: "6 年以上：50%" },
      ],
      guidance:
        "請依本次事故日前的無理賠紀錄期間選擇；若保險公司認定期間未滿 3 年，選擇不適用。",
    },
    disability_benefit_rate_percent: {
      label: "本次失能／殘廢給付比例",
      type: "rate",
      unit: "%",
      guidance: "請依這個商品版本的失能或殘廢程度給付表，選擇本次事故對應的給付比例。",
    },
    cash_surrender_value: {
      label: "解約金／現金價值",
      type: "money",
      unit: "元",
      guidance: "請填保險公司列示的事故日或條款指定日解約金、保單現金價值。",
    },
    installment_periodic_amount: {
      label: "分期定期保險金",
      type: "money",
      unit: "元",
      guidance: "若保險金指定分期給付，請填保險公司換算後的每期或年度給付金額。",
    },
    unpaid_annuity_balance: {
      label: "未支領年金餘額",
      type: "money",
      unit: "元",
      guidance: "請填保證期間內尚未支領、或保險公司貼現換算後的年金餘額。",
    },
    successor_discounted_annuity_amount: {
      label: "身故受益人後續身故之折現一次給付",
      type: "non_negative_money",
      unit: "元",
      guidance: "僅在身故受益人於續領餘額期間內身故時使用；請填保險公司依剩餘期數與條款預定利率列示的折現金額，未發生或不適用請填 0。",
    },
    excess_annuity_reserve_return_amount: {
      label: "超額年金準備金返還金額",
      type: "non_negative_money",
      unit: "元",
      guidance:
        "請填年金給付開始時，保險公司因年領年金超過條款上限而正式列示返還的超額保單價值準備金；若沒有超額返還，請輸入 0。",
    },
    policy_dividend_amount: {
      label: "保單紅利／非保證給付估算",
      type: "non_negative_money",
      unit: "元",
      guidance: "紅利或非保證給付需以保險公司通知或使用者估算值填入。",
    },
    declared_interest_rate_percent: {
      label: "宣告利率",
      type: "rate",
      unit: "%",
      guidance: "請填該保單年度適用的宣告利率百分比。",
    },
    scheduled_interest_rate_percent: {
      label: "預定利率",
      type: "rate",
      unit: "%",
      guidance: "請填條款或保單所列的預定利率百分比。",
    },
  };

  const AMOUNT_ROLES = {
    payout: "給付金額",
    base: "計算基準",
    limit: "最高限額",
    reference: "條款參考值",
    premium_waiver: "保費豁免",
    unknown: "金額角色尚待整理",
  };

  const LIMIT_SCOPES = {
    per_policy: "本保單",
    cross_policy: "跨保單合計",
    per_event: "每次事故",
    per_injury: "每次傷害",
    per_item: "每項",
    per_surgery: "每次手術",
    per_procedure: "每次處置",
    per_visit: "每次門診",
    per_day: "每日",
    per_month: "每月",
    per_hospitalization: "每次住院",
    annual: "每保單年度",
    lifetime: "保險期間累計",
    unknown: "適用範圍尚待整理",
  };

  const AGGREGATION_RULES = {
    separate: "分開呈現",
    conditional_additive: "符合條款時可併計",
    choose_one: "擇一給付",
    highest: "取較高給付",
    cumulative_cap: "受累計上限限制",
    unknown: "是否併計尚待條款確認",
  };

  const RESULT_KINDS = {
    cash_payout: "現金給付",
    non_cash_effect: "非現金保障效果",
    payment_method: "給付方式",
    reference: "條款參考資訊",
  };

  const AMOUNT_STAGES = {
    gross_contract_benefit: "條款保障毛額",
    non_cash_estimate: "非現金保障效果估值",
    insurer_quoted_amount: "保險公司列示金額",
    not_applicable: "不適用",
  };

  const LEGACY_BASIS_MAP = {
    per_unit: "per_unit",
    daily_per_unit: "per_unit_per_day",
    daily_total: "per_day",
    annual_limit: "reimbursement_with_cap",
    benefit_base: "percentage_of_base",
    per_injury_limit: "reimbursement_with_cap",
    additional_benefit: "additional_benefit",
  };

  const COVERAGE_BUCKETS = [
    {
      id: "life",
      group: "personal",
      label: "壽險",
      summary: "身故、完全失能、壽險主約或投資型壽險。",
      categories: ["傳統型壽險", "投資型壽險"],
      keywords: ["壽險", "身故", "死亡", "完全失能", "生死合險", "定期壽", "終身壽"],
    },
    {
      id: "medical",
      group: "personal",
      label: "醫療險",
      summary: "住院、手術、實支實付、日額、門診或健康醫療。",
      categories: ["健康保險"],
      keywords: ["醫療", "健康", "住院", "手術", "實支", "日額", "門診", "病房", "雜費"],
    },
    {
      id: "accident",
      group: "personal",
      label: "意外險",
      summary: "傷害、意外、平安、燒燙傷、骨折或意外失能。",
      categories: ["傷害保險"],
      keywords: ["傷害", "意外", "平安", "燒燙傷", "骨折", "意外失能", "旅行平安"],
    },
    {
      id: "cancer",
      group: "personal",
      label: "癌症險",
      summary: "癌症、惡性腫瘤、防癌或癌症醫療給付。",
      categories: [],
      keywords: ["癌", "癌症", "防癌", "抗癌", "惡性腫瘤", "原位癌", "初期癌"],
    },
    {
      id: "critical",
      group: "personal",
      label: "重大疾病險",
      summary: "重大疾病、重大傷病、特定傷病或一次金保障。",
      categories: [],
      keywords: ["重大疾病", "重大傷病", "特定傷病", "心肌梗塞", "腦中風", "癱瘓", "洗腎"],
    },
    {
      id: "longterm",
      group: "personal",
      label: "長照險",
      summary: "長期照顧、失智、認知功能障礙或長期看護。",
      categories: [],
      keywords: ["長期照顧", "長照", "長期看護", "失智", "認知功能障礙", "照護", "扶助"],
    },
    {
      id: "annuity",
      group: "personal",
      label: "年金／退休",
      summary: "年金、退休、生存金或長期現金流安排。",
      categories: ["傳統型年金", "投資型年金"],
      keywords: ["年金", "退休", "生存金", "養老", "即期年金", "利率變動型年金"],
    },
    {
      id: "auto",
      group: "property",
      label: "汽車險",
      summary: "車體、竊盜、第三人責任、乘客或駕駛人保障。",
      categories: ["汽車保險"],
      keywords: ["汽車", "機車", "車體", "竊盜", "第三人責任", "駕駛人", "乘客責任"],
    },
    {
      id: "fire",
      group: "property",
      label: "住宅／火災險",
      summary: "住宅、商業火災、地震、颱風洪水或財物損失保障。",
      categories: ["火災保險"],
      keywords: ["住宅", "火災", "地震", "颱風", "洪水", "財物", "建築物", "動產"],
    },
    {
      id: "marine",
      group: "property",
      label: "海上／運輸險",
      summary: "船舶、貨物運輸、海運或相關責任保障。",
      categories: ["海上保險"],
      keywords: ["海上", "船舶", "貨物運輸", "海運", "貨運", "航空貨物"],
    },
    {
      id: "property_other",
      group: "property",
      label: "其他產險",
      summary: "責任、工程、保證、信用、旅遊不便及其他財產風險。",
      categories: ["意外保險"],
      keywords: ["責任保險", "工程保險", "保證保險", "信用保險", "旅遊不便", "寵物保險", "農業保險"],
    },
  ];

  const OFFICIAL_CATEGORY_GROUPS = {
    personal: new Set(["健康保險", "傳統型壽險", "傳統型年金", "傷害保險", "投資型壽險", "投資型年金"]),
    property: new Set(["意外保險", "汽車保險", "海上保險", "火災保險"]),
  };

  function normalizeText(value) {
    return String(value ?? "").trim().toLowerCase();
  }

  function productVersionFamilyName(value) {
    return normalizeText(value)
      .replace(/\s*[（(][^()（）]*第[^()（）]*(?:次|版)[^()（）]*(?:變更|修訂|修正|改訂)[^()（）]*[)）]\s*$/u, "")
      .trim();
  }

  function normalizeInteger(value, max) {
    if (value === "" || value === null || value === undefined) return null;
    const number = Number(String(value).replaceAll(",", ""));
    if (!Number.isSafeInteger(number) || number <= 0 || number > max) return null;
    return number;
  }

  function normalizeNonNegativeInteger(value, max) {
    if (value === "" || value === null || value === undefined) return null;
    const number = Number(String(value).replaceAll(",", ""));
    if (!Number.isSafeInteger(number) || number < 0 || number > max) return null;
    return number;
  }

  function normalizeUnitCount(value) {
    return normalizeInteger(value, MAX_UNIT_COUNT);
  }

  function normalizeMoneyAmount(value) {
    return normalizeInteger(value, MAX_MONEY_AMOUNT);
  }

  function normalizeNonNegativeMoneyAmount(value) {
    return normalizeNonNegativeInteger(value, MAX_MONEY_AMOUNT);
  }

  function moneyDecimalPlaces(item) {
    const value = Number(
      item?.version_characteristics?.money_decimal_places,
    );
    return Number.isSafeInteger(value) &&
      value >= 0 &&
      value <= MAX_MONEY_DECIMAL_PLACES
      ? value
      : 0;
  }

  function fixedPointMoney(value, decimalPlaces, allowZero = false) {
    if (value === "" || value === null || value === undefined) {
      return null;
    }
    const places = Number(decimalPlaces);
    if (
      !Number.isSafeInteger(places) ||
      places < 0 ||
      places > MAX_MONEY_DECIMAL_PLACES
    ) {
      return null;
    }
    const text = String(value).trim().replaceAll(",", "");
    const matched = text.match(/^(\d+)(?:\.(\d+))?$/u);
    if (!matched || (matched[2] || "").length > places) return null;
    const scale = 10 ** places;
    const fraction = (matched[2] || "").padEnd(places, "0");
    const scaled =
      BigInt(matched[1]) * BigInt(scale) +
      BigInt(fraction || "0");
    if (
      (!allowZero && scaled === 0n) ||
      scaled > BigInt(MAX_MONEY_AMOUNT) * BigInt(scale) ||
      scaled > BigInt(Number.MAX_SAFE_INTEGER)
    ) {
      return null;
    }
    return {
      decimal_places: places,
      scale,
      scaled: Number(scaled),
      value: Number(scaled) / scale,
    };
  }

  function normalizeDecimalMoneyAmount(
    value,
    decimalPlaces = MAX_MONEY_DECIMAL_PLACES,
    allowZero = false,
  ) {
    return fixedPointMoney(value, decimalPlaces, allowZero)?.value ?? null;
  }

  function normalizeContractCurrencyCode(value) {
    const code = String(value ?? "").trim().toUpperCase();
    return /^[A-Z]{3}$/u.test(code) ? code : "";
  }

  function normalizeNumberValue(
    value,
    max = MAX_RATE * 100,
    allowZero = false,
  ) {
    if (value === "" || value === null || value === undefined) return null;
    const number = Number(String(value).replaceAll(",", ""));
    return Number.isFinite(number) &&
      (allowZero ? number >= 0 : number > 0) &&
      number <= max
      ? number
      : null;
  }

  function normalizePolicyText(value, maxLength = 20) {
    const text = String(value ?? "").trim();
    if (!text || text.length > maxLength || /[\u0000-\u001f\u007f]/u.test(text)) return "";
    return /^[a-z]{3}$/iu.test(text) ? text.toUpperCase() : text;
  }

  function normalizePolicyChoice(value, field) {
    const normalized = normalizePolicyText(value, field?.max_length || 40);
    const matchedOption = field?.options?.find(
      (option) =>
        normalizeText(option.value) === normalizeText(normalized),
    );
    return matchedOption ? matchedOption.value : "";
  }

  function normalizeRate(value, percentValue) {
    const candidate = percentValue !== undefined && percentValue !== null ? Number(percentValue) / 100 : Number(value);
    return Number.isFinite(candidate) && candidate > 0 && candidate <= MAX_RATE ? candidate : null;
  }

  function safeIntegerProduct(left, right) {
    const result = Number(left) * Number(right);
    return Number.isSafeInteger(result) && result > 0 ? result : null;
  }

  function safeFloorRatio(amount, numerator, denominator = 100) {
    if (
      !Number.isSafeInteger(amount) ||
      amount < 0 ||
      !Number.isSafeInteger(numerator) ||
      numerator < 0 ||
      !Number.isSafeInteger(denominator) ||
      denominator <= 0
    ) {
      return null;
    }
    const value =
      (BigInt(amount) * BigInt(numerator)) / BigInt(denominator);
    return value <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(value) : null;
  }

  function safeExactRatio(amount, numerator, denominator = 100) {
    if (
      !Number.isSafeInteger(amount) ||
      amount < 0 ||
      !Number.isSafeInteger(numerator) ||
      numerator < 0 ||
      !Number.isSafeInteger(denominator) ||
      denominator <= 0
    ) {
      return { status: "invalid", value: null };
    }
    const dividend = BigInt(amount) * BigInt(numerator);
    const divisor = BigInt(denominator);
    if (dividend % divisor !== 0n) {
      return { status: "fractional", value: null };
    }
    const value = dividend / divisor;
    return value <= BigInt(Number.MAX_SAFE_INTEGER)
      ? { status: "exact", value: Number(value) }
      : { status: "overflow", value: null };
  }

  function safeIntegerSum(...values) {
    if (
      values.some(
        (value) => !Number.isSafeInteger(value) || value < 0,
      )
    ) {
      return null;
    }
    const total = values.reduce((sum, value) => sum + value, 0);
    return Number.isSafeInteger(total) ? total : null;
  }

  function canonicalSelectionMode(value) {
    const mode = normalizeText(value).replace(/[\s/+]+/g, "_");
    if (!mode) return "";
    if (["face_amount", "amount", "sum_insured", "insured_amount", "保額", "保險金額"].includes(mode)) return "face_amount";
    if (["face_amount_plan", "face_amount_policy_type", "basic_amount_policy_type", "基本保額與保險型態"].includes(mode)) return "face_amount_plan";
    if (["account_value", "policy_account_value", "保單帳戶價值", "帳戶價值"].includes(mode)) return "account_value";
    if (["paid_premium_factor_plan", "paid_premium_factor", "paid_premium_policy_type", "已繳保費公式與保險型態"].includes(mode)) return "paid_premium_factor_plan";
    if (["multi_unit", "multiple_units", "多組單位", "多單位"].includes(mode)) return "multi_unit";
    if (["plan_unit", "plan_and_unit", "計畫_單位", "計畫與單位"].includes(mode)) return "plan_unit";
    if (mode.includes("plan") || mode.includes("方案") || mode.includes("計畫")) return "plan";
    if (mode.includes("unit") || mode.includes("單位")) return "unit";
    if (["policy_state", "policy_status", "policy_recorded", "保單狀態", "保單資料", "保單記載"].includes(mode)) return "policy_state";
    if (["fixed", "none", "no_input", "固定", "免輸入"].includes(mode)) return "fixed";
    if (["unknown", "unsupported", "pending", "待整理", "未知"].includes(mode)) return "unknown";
    return "";
  }

  function canonicalCalculationBasis(value) {
    const basis = normalizeText(value);
    if (CALCULATION_BASES[basis]) return basis;
    return LEGACY_BASIS_MAP[basis] || "unknown";
  }

  function defaultAmountRole(basis) {
    if (basis === "aggregate_cap") return "limit";
    if (basis === "waiver") return "premium_waiver";
    if (basis === "percentage_of_base") return "base";
    if (
      [
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
        "reimbursement_with_total_and_daily_room_cap",
        "reimbursement_with_schedule_and_major_cap",
        "reimbursement_with_greater_of_daily_cap",
      ].includes(basis)
    ) return "limit";
    if (["table_multiplier", "tiered_or_stepped", "account_value_annuity_factor", "unknown"].includes(basis)) return "reference";
    return "payout";
  }

  function defaultLimitScope(basis, legacyBasis) {
    if (["per_day", "per_unit_per_day"].includes(basis)) return "per_day";
    if (legacyBasis === "annual_limit") return "annual";
    if (legacyBasis === "per_injury_limit") return "per_injury";
    if (
      [
        "fixed_amount",
        "percentage_of_base",
        "additional_benefit",
        "account_value",
        "account_value_annuity_factor",
        "annuity_amount_or_lump_sum",
        "maturity_policy_account_value",
        "policy_state_amount",
        "sum_policy_state_amounts",
        "death_or_funeral_greater_of",
        "death_or_funeral_fixed_amount",
        "policy_value_component",
        "policy_value_plus_general_insurance_amount",
        "policy_value_plus_general_and_accidental_insurance_amount",
        "protected_amount_plus_policy_account_value",
        "net_premium_factor_plus_additional_premium",
        "face_amount_plus_account_value_minus_paid_annuity_and_offsets",
        "paid_premium_factor_account_value_formula",
        "annuity_face_amount_schedule",
        "single_premium_minus_paid_annuity_total",
        "reserve_minus_policy_loan_and_interest",
        "aggregate_cap",
        "greater_of",
        "waiver",
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
        "reimbursement_with_total_and_daily_room_cap",
        "reimbursement_with_schedule_and_major_cap",
        "reimbursement_with_greater_of_daily_cap",
      ].includes(basis)
    ) return "per_event";
    return "unknown";
  }

  function normalizeEligibilityRule(rule) {
    if (!rule || typeof rule !== "object") return null;
    if (String(rule.type || "").trim() !== "long_term_care_state") return null;
    const fieldKey = (value, fallback = "") => {
      const key = String(value || fallback).trim();
      return POLICY_STATE_FIELDS[key] ? key : "";
    };
    const normalized = {
      type: "long_term_care_state",
      qualification_type_key: fieldKey(
        rule.qualification_type_key,
        "long_term_care_qualification_type",
      ),
      adl_impairment_count_key: fieldKey(
        rule.adl_impairment_count_key,
        "adl_impairment_count",
      ),
      adl_minimum:
        Number.isSafeInteger(Number(rule.adl_minimum)) &&
        Number(rule.adl_minimum) > 0
          ? Number(rule.adl_minimum)
          : 3,
      cdr_score_key: fieldKey(rule.cdr_score_key, "cdr_score"),
      cdr_minimum:
        Number.isFinite(Number(rule.cdr_minimum)) &&
        Number(rule.cdr_minimum) > 0
          ? Number(rule.cdr_minimum)
          : 2,
      duration_months_key: fieldKey(
        rule.duration_months_key,
        "impairment_duration_months",
      ),
      minimum_duration_months:
        Number.isSafeInteger(Number(rule.minimum_duration_months)) &&
        Number(rule.minimum_duration_months) > 0
          ? Number(rule.minimum_duration_months)
          : 3,
      permanence_status_key: fieldKey(
        rule.permanence_status_key,
        "long_term_care_permanence_status",
      ),
      permanent_value: String(
        rule.permanent_value || "permanent",
      ).trim(),
      medical_confirmation_status_key: fieldKey(
        rule.medical_confirmation_status_key,
        "long_term_care_medical_confirmation_status",
      ),
      confirmed_value: String(
        rule.confirmed_value || "confirmed",
      ).trim(),
      previous_claim_status_key: fieldKey(
        rule.previous_claim_status_key,
        "long_term_care_previous_claim_status",
      ),
      not_claimed_value: String(
        rule.not_claimed_value || "not_claimed",
      ).trim(),
      cognitive_diagnosis_status_key: fieldKey(
        rule.cognitive_diagnosis_status_key,
        "cognitive_icd_diagnosis_status",
      ),
      cognitive_confirmed_value: String(
        rule.cognitive_confirmed_value || "confirmed",
      ).trim(),
      payment_period_status_key: fieldKey(
        rule.payment_period_status_key,
      ),
      eligible_payment_period_value: String(
        rule.eligible_payment_period_value || "within_payment_period",
      ).trim(),
    };
    return [
      normalized.qualification_type_key,
      normalized.adl_impairment_count_key,
      normalized.cdr_score_key,
      normalized.duration_months_key,
      normalized.permanence_status_key,
      normalized.permanent_value,
      normalized.medical_confirmation_status_key,
      normalized.confirmed_value,
      normalized.previous_claim_status_key,
      normalized.not_claimed_value,
      normalized.cognitive_diagnosis_status_key,
      normalized.cognitive_confirmed_value,
      normalized.eligible_payment_period_value,
    ].every(Boolean)
      ? normalized
      : null;
  }

  function normalizeCoverageEntry(entry, index) {
    const source = entry || {};
    const legacyBasis = normalizeText(source.basis);
    const calculationBasis = canonicalCalculationBasis(source.calculation_basis || legacyBasis);
    const amountRole = AMOUNT_ROLES[source.amount_role] ? source.amount_role : defaultAmountRole(calculationBasis);
    const limitScope = LIMIT_SCOPES[source.limit_scope]
      ? source.limit_scope
      : defaultLimitScope(calculationBasis, legacyBasis);
    const aggregationRule = AGGREGATION_RULES[source.aggregation_rule] ? source.aggregation_rule : "separate";
    const conditions = Array.isArray(source.conditions)
      ? source.conditions.map((value) => String(value || "").trim()).filter(Boolean)
      : String(source.conditions || "").trim()
        ? [String(source.conditions).trim()]
        : [];
    const amountTiers = Array.isArray(source.amount_tiers)
      ? source.amount_tiers
          .map((tier) => ({
            label: String(tier?.label || "").trim(),
            amount: normalizeMoneyAmount(tier?.amount),
            multiplier:
              Number.isFinite(Number(tier?.multiplier)) &&
              Number(tier.multiplier) > 0
                ? Number(tier.multiplier)
                : null,
            min_quantity: normalizeInteger(
              tier?.min_quantity,
              100_000,
            ),
            max_quantity:
              tier?.max_quantity === null ||
              tier?.max_quantity === undefined
                ? null
                : normalizeInteger(tier.max_quantity, 100_000),
          }))
          .filter(
            (tier) =>
              tier.label &&
              (tier.amount || tier.multiplier),
          )
      : [];
    return {
      id: String(source.id || `coverage-${index + 1}`),
      name: String(source.name || "").trim(),
      amount: normalizeMoneyAmount(source.amount),
      basis: legacyBasis || calculationBasis,
      calculation_basis: calculationBasis,
      amount_role: amountRole,
      limit_scope: limitScope,
      aggregation_rule: aggregationRule,
      benefit_group_id: String(source.benefit_group_id || "").trim(),
      event_key: String(source.event_key || "").trim(),
      event_label: String(source.event_label || "").trim(),
      conditional_event_key: String(
        source.conditional_event_key || "",
      ).trim(),
      conditional_event_label: String(
        source.conditional_event_label || "",
      ).trim(),
      applies_to_entry_ids: Array.isArray(source.applies_to_entry_ids)
        ? [
            ...new Set(
              source.applies_to_entry_ids
                .map((entryId) => String(entryId || "").trim())
                .filter(Boolean),
            ),
          ]
        : [],
      rate: normalizeRate(source.rate, source.rate_percent),
      limit_rate: normalizeRate(source.limit_rate, source.limit_rate_percent),
      limit_rate_state_key: POLICY_STATE_FIELDS[
        source.limit_rate_state_key
      ]
        ? String(source.limit_rate_state_key)
        : "",
      secondary_limit_rate_state_key: POLICY_STATE_FIELDS[
        source.secondary_limit_rate_state_key
      ]
        ? String(source.secondary_limit_rate_state_key)
        : "",
      secondary_limit_state_key: POLICY_STATE_FIELDS[
        source.secondary_limit_state_key
      ]
        ? String(source.secondary_limit_state_key)
        : "",
      rate_min: normalizeRate(source.rate_min, source.rate_min_percent),
      rate_max: normalizeRate(source.rate_max, source.rate_max_percent),
      rate_threshold: normalizeRate(
        source.rate_threshold,
        source.rate_threshold_percent,
      ),
      rate_state_key: POLICY_STATE_FIELDS[source.rate_state_key]
        ? String(source.rate_state_key)
        : "",
      multiplier: Number.isFinite(Number(source.multiplier)) && Number(source.multiplier) > 0 ? Number(source.multiplier) : null,
      minimum_multiplier:
        Number.isFinite(Number(source.minimum_multiplier)) &&
        Number(source.minimum_multiplier) > 0
          ? Number(source.minimum_multiplier)
          : null,
      maximum_multiplier:
        Number.isFinite(Number(source.maximum_multiplier)) &&
        Number(source.maximum_multiplier) > 0
          ? Number(source.maximum_multiplier)
          : null,
      multiplier_state_key: POLICY_STATE_FIELDS[
        source.multiplier_state_key
      ]
        ? String(source.multiplier_state_key)
        : "",
      unit_key: String(source.unit_key || "").trim(),
      quantity_state_key: POLICY_STATE_FIELDS[source.quantity_state_key]
        ? String(source.quantity_state_key)
        : "",
      quantity_cap:
        Number.isSafeInteger(Number(source.quantity_cap)) &&
        Number(source.quantity_cap) > 0
          ? Number(source.quantity_cap)
          : null,
      quantity_cap_state_key: POLICY_STATE_FIELDS[
        source.quantity_cap_state_key
      ]
        ? String(source.quantity_cap_state_key)
        : "",
      limit_proration_threshold:
        Number.isSafeInteger(Number(source.limit_proration_threshold)) &&
        Number(source.limit_proration_threshold) > 0
          ? Number(source.limit_proration_threshold)
          : null,
      expense_state_key: POLICY_STATE_FIELDS[source.expense_state_key]
        ? String(source.expense_state_key)
        : "",
      rate_condition_state_key: POLICY_STATE_FIELDS[source.rate_condition_state_key]
        ? String(source.rate_condition_state_key)
        : "",
      rate_condition_value: String(source.rate_condition_value || "").trim(),
      tier_selection_state_key: POLICY_STATE_FIELDS[
        source.tier_selection_state_key
      ]
        ? String(source.tier_selection_state_key)
        : "",
      eligibility_state_key: POLICY_STATE_FIELDS[
        source.eligibility_state_key
      ]
        ? String(source.eligibility_state_key)
        : "",
      ineligible_values: Array.isArray(source.ineligible_values)
        ? [
            ...new Set(
              source.ineligible_values
                .map((value) => String(value || "").trim())
                .filter(Boolean),
            ),
          ]
        : [],
      uncertain_values: Array.isArray(source.uncertain_values)
        ? [
            ...new Set(
              source.uncertain_values
                .map((value) => String(value || "").trim())
                .filter(Boolean),
            ),
          ]
        : [],
      exclusion_state_key: POLICY_STATE_FIELDS[source.exclusion_state_key]
        ? String(source.exclusion_state_key)
        : "",
      exclusion_values: Array.isArray(source.exclusion_values)
        ? [
            ...new Set(
              source.exclusion_values
                .map((value) => String(value || "").trim())
                .filter(Boolean),
            ),
          ]
        : [],
      cumulative_paid_state_key: POLICY_STATE_FIELDS[source.cumulative_paid_state_key]
        ? String(source.cumulative_paid_state_key)
        : "",
      cumulative_paid_multiplier_state_key: POLICY_STATE_FIELDS[
        source.cumulative_paid_multiplier_state_key
      ]
        ? String(source.cumulative_paid_multiplier_state_key)
        : "",
      aggregate_limit_entry_id: String(source.aggregate_limit_entry_id || "").trim(),
      policy_state_keys: Array.isArray(source.policy_state_keys)
        ? [
            ...new Set(
              source.policy_state_keys
                .map((key) => String(key || "").trim())
                .filter((key) => POLICY_STATE_FIELDS[key]),
            ),
          ]
        : [],
      currency_state_key: String(source.currency_state_key || "").trim(),
      minor_account_value_return_age:
        Number.isSafeInteger(Number(source.minor_account_value_return_age)) &&
        Number(source.minor_account_value_return_age) > 0 &&
        Number(source.minor_account_value_return_age) <= MAX_INSURED_AGE
          ? Number(source.minor_account_value_return_age)
          : null,
      minor_unallocated_net_premium_return:
        source.minor_unallocated_net_premium_return === true
          ? true
          : source.minor_unallocated_net_premium_return === false
            ? false
            : null,
      funeral_limit_plan_options: Array.isArray(
        source.funeral_limit_plan_options,
      )
        ? [
            ...new Set(
              source.funeral_limit_plan_options
                .map((value) => String(value || "").trim())
                .filter(Boolean),
            ),
          ]
        : [],
      annuity_payment_pattern: ["level", "increasing"].includes(
        String(source.annuity_payment_pattern || "").trim(),
      )
        ? String(source.annuity_payment_pattern).trim()
        : "",
      annuity_growth_rate: normalizeRate(
        source.annuity_growth_rate,
        source.annuity_growth_rate_percent,
      ),
      annuity_guarantee_years:
        Number.isSafeInteger(Number(source.annuity_guarantee_years)) &&
        Number(source.annuity_guarantee_years) > 0 &&
        Number(source.annuity_guarantee_years) <= 100
          ? Number(source.annuity_guarantee_years)
          : null,
      minimum_annual_annuity_amount: normalizeMoneyAmount(
        source.minimum_annual_annuity_amount,
      ),
      maximum_annual_annuity_amount: normalizeMoneyAmount(
        source.maximum_annual_annuity_amount,
      ),
      policy_year_cutoff:
        Number.isSafeInteger(Number(source.policy_year_cutoff)) &&
        Number(source.policy_year_cutoff) > 0 &&
        Number(source.policy_year_cutoff) <= 130
          ? Number(source.policy_year_cutoff)
          : null,
      result_kind: RESULT_KINDS[source.result_kind]
        ? source.result_kind
        : amountRole === "payout"
          ? "cash_payout"
          : amountRole === "premium_waiver"
            ? "non_cash_effect"
            : "reference",
      amount_stage: AMOUNT_STAGES[source.amount_stage]
        ? source.amount_stage
        : amountRole === "payout"
          ? "gross_contract_benefit"
          : amountRole === "premium_waiver"
            ? "non_cash_estimate"
            : "not_applicable",
      eligibility_rule: normalizeEligibilityRule(source.eligibility_rule),
      amount_tiers: amountTiers,
      source: source.source === "user" ? "user" : "terms",
      note: String(source.note || "").trim(),
      conditions,
      source_ref: String(source.source_ref || "").trim(),
    };
  }

  function normalizeCoverageEntries(entries) {
    if (!Array.isArray(entries)) return [];
    return entries
      .filter((entry) => entry?.source !== "user")
      .map(normalizeCoverageEntry)
      .filter((entry) => entry.name || entry.amount);
  }

  function allStructuredCoverageEntries(item) {
    const entries = normalizeCoverageEntries(item?.coverage_entries || item?.benefit_rules);
    for (const option of normalizePlanOptions(item)) entries.push(...option.coverage_entries);
    return entries;
  }

  function normalizePlanOptions(item) {
    const rawOptions = item?.plan_options || item?.benefit_schedule?.plans || [];
    if (!Array.isArray(rawOptions)) return [];
    const options = rawOptions
      .map((option) => {
        const source = typeof option === "string" ? { value: option, label: option } : option || {};
        const value = String(source.value || source.id || source.code || source.name || source.label || "").trim();
        const label = String(source.label || source.name || value).trim();
        return {
          value,
          label,
          coverage_entries: normalizeCoverageEntries(source.coverage_entries || source.benefits),
        };
      })
      .filter((option) => option.value && option.label);
    return [...new Map(options.map((option) => [option.value, option])).values()];
  }

  function normalizeUnitFields(item) {
    if (!Array.isArray(item?.unit_fields)) return [];
    const fields = item.unit_fields
      .map((field) => ({
        key: String(field?.key || "").trim(),
        label: String(field?.label || "").trim(),
      }))
      .filter((field) => field.key && field.label);
    return [...new Map(fields.map((field) => [field.key, field])).values()];
  }

  function entryPolicyStateText(entry) {
    return normalizeText(
      [
        entry?.id,
        entry?.name,
        entry?.basis,
        entry?.calculation_basis,
        entry?.note,
        ...(entry?.conditions || []),
      ].join(" "),
    );
  }

  function hasAnyTerm(text, terms) {
    return terms.some((term) => text.includes(normalizeText(term)));
  }

  function isUnpaidAnnuityBalanceEntry(entry, text = entryPolicyStateText(entry)) {
    const id = normalizeText(entry?.id);
    const unitKey = normalizeText(entry?.unit_key);
    return (
      unitKey === "unpaid_annuity_balance" ||
      id.includes("unpaid-annuity-balance") ||
      id.includes("unpaid_annuity_balance") ||
      hasAnyTerm(text, ["未支領之年金餘額", "未支領年金餘額"])
    );
  }

  function isValueSharingBonusEntry(entry, text = entryPolicyStateText(entry)) {
    if (isUnpaidAnnuityBalanceEntry(entry, text)) return false;
    const id = normalizeText(entry?.id);
    const basis = normalizeText(entry?.basis);
    if (
      entry?.rate_state_key === "no_claim_bonus_rate_percent" ||
      id.includes("no-claim-record") ||
      normalizeText(entry?.unit_key) ===
        "current_articles_11_to_14_benefit_total_amount"
    ) {
      return false;
    }
    return (
      basis === "value_sharing_bonus" ||
      id.includes("value-sharing") ||
      id.includes("bonus") ||
      hasAnyTerm(text, ["增值回饋分享金", "增值回饋金", "回饋分享金"])
    );
  }

  function uniquePolicyStateFields(keys) {
    return [...new Set(keys)].filter((key) => POLICY_STATE_FIELDS[key]);
  }

  function policyStateFieldKeysForEntry(entry, selection = null) {
    const normalizedEntry = normalizeCoverageEntry(entry, 0);
    const text = entryPolicyStateText(normalizedEntry);
    const unitKey = normalizeText(normalizedEntry.unit_key);
    const keys = [];
    const add = (...fieldKeys) => keys.push(...fieldKeys);
    const insuredAgeForRequirements = selection
      ? policyStateInteger(selection, "insured_age_at_event")
      : null;
    const minorAccountValueReturnSelected =
      Boolean(normalizedEntry.minor_account_value_return_age) &&
      insuredAgeForRequirements !== null &&
      insuredAgeForRequirements <
        normalizedEntry.minor_account_value_return_age;
    const isShinkongJinhaoyi = [
      "shinkong-jinhaoyi-variable-universal-life",
      "shinkong-jinmanyi-variable-universal-life",
    ].includes(
      selection?.version_characteristics?.product_family,
    );
    const riskCalculationStage = selection
      ? policyStateChoice(selection, "risk_calculation_stage")
      : "";
    const riskAmountSource = selection
      ? policyStateChoice(selection, "risk_amount_source")
      : "";
    const ageAccuracyStatus = selection
      ? policyStateChoice(selection, "insured_age_accuracy_status")
      : "";
    const subsequentPremiumRiskCalculation = [
      "subsequent_regular_premium",
      "subsequent_nonregular_premium",
    ].includes(riskCalculationStage);
    const riskAmountEffectiveStatus = selection
      ? policyStateChoice(selection, "risk_amount_effective_status")
      : "";
    const shinkongRiskAgeThreshold = Number(
      selection?.version_characteristics
        ?.risk_amount_actual_age_threshold,
    );
    const shinkongRiskFormulaNotRequired =
      isShinkongJinhaoyi &&
      (
        (
          selection &&
          policyStateChoice(selection, "claim_time_status") ===
            "time_barred"
        ) ||
        (
          insuredAgeForRequirements !== null &&
          Number.isSafeInteger(shinkongRiskAgeThreshold) &&
          shinkongRiskAgeThreshold === 15 &&
          insuredAgeForRequirements < shinkongRiskAgeThreshold
        )
      );
    const shinkongAccountValueOnlySelected =
      isShinkongJinhaoyi &&
      (
        (
          selection &&
          policyStateChoice(selection, "claim_time_status") ===
            "time_barred"
        ) ||
        (
          normalizedEntry.id === "death-benefit" &&
          minorAccountValueReturnSelected
        )
      );
    const paidPremiumFactorAccountValueOnlySelected =
      normalizedEntry.calculation_basis ===
        "paid_premium_factor_account_value_formula" &&
      Boolean(selection) &&
      (
        policyStateChoice(selection, "claim_time_status") ===
          "time_barred" ||
        minorAccountValueReturnSelected
      );
    const protectedAmountAccountValueOnlySelected =
      normalizedEntry.calculation_basis ===
        "protected_amount_plus_policy_account_value" &&
      Boolean(selection) &&
      (
        (
          policyStateChoice(selection, "claim_time_status") ===
            "time_barred" &&
          selection?.version_characteristics
            ?.claim_time_bar_account_value_return === true
        ) ||
        policyStateChoice(selection, "benefit_exclusion_status") ===
          "confirmed_applies"
      );
    const currentBenefitAmountStatusForRequirements =
      selection
        ? policyStateChoice(
            selection,
            "current_benefit_amount_status",
          )
        : "";
    const eligibilityValueForRequirements =
      selection && normalizedEntry.eligibility_state_key
        ? policyStateChoice(
            selection,
            normalizedEntry.eligibility_state_key,
          )
        : "";
    const exclusionValueForRequirements =
      selection && normalizedEntry.exclusion_state_key
        ? policyStateChoice(
            selection,
            normalizedEntry.exclusion_state_key,
          )
        : "";
    const entryEligibilitySuppressesAmountRequirements =
      Boolean(selection) &&
      eligibilityValueForRequirements &&
      [
        ...normalizedEntry.ineligible_values,
        ...normalizedEntry.uncertain_values,
      ].includes(eligibilityValueForRequirements);
    const entryExclusionSuppressesAmountRequirements =
      Boolean(selection) &&
      exclusionValueForRequirements &&
      normalizedEntry.exclusion_values.includes(
        exclusionValueForRequirements,
      );
    const entryStateSuppressesAmountRequirements =
      entryEligibilitySuppressesAmountRequirements ||
      entryExclusionSuppressesAmountRequirements;
    if (
      normalizedEntry.calculation_basis ===
      "reimbursement_with_total_and_daily_room_cap"
    ) {
      add(normalizedEntry.eligibility_state_key);
      if (normalizedEntry.eligibility_state_key && !eligibilityValueForRequirements) {
        return uniquePolicyStateFields(keys);
      }
      if (entryStateSuppressesAmountRequirements) {
        return uniquePolicyStateFields(keys);
      }
      add(normalizedEntry.unit_key, normalizedEntry.expense_state_key);
      if (
        !normalizedEntry.eligibility_state_key ||
        eligibilityValueForRequirements === "inpatient"
      ) {
        add(
          normalizedEntry.quantity_state_key,
          ...normalizedEntry.policy_state_keys,
        );
      }
      return uniquePolicyStateFields(keys);
    }
    const shinkongRiskHistoryKeys = [
      "risk_calculation_actual_age",
      "risk_calculation_insurance_age",
      "insured_age_accuracy_status",
      "risk_calculation_stage",
      "risk_calculation_policy_account_value",
      "risk_calculation_net_premium_amount",
      "risk_amount_effective_status",
    ];
    const entryPolicyStateKeys = normalizedEntry.policy_state_keys.filter(
      (key) =>
        !entryStateSuppressesAmountRequirements &&
        !(
          minorAccountValueReturnSelected &&
          key === "death_benefit_status"
        ) &&
        (
          key !== "unexpired_premium_refund_amount" ||
          unexpiredInsuranceCostRefundApplies(
            selection,
            normalizedEntry,
            selectedPolicyType(selection),
          )
        ) &&
        !(
          selection &&
          ["risk_calculation_policy_account_value", "risk_calculation_net_premium_amount"].includes(key) &&
          !subsequentPremiumRiskCalculation
        ) &&
        !(
          selection &&
          key === "insurer_confirmed_current_risk_amount" &&
          riskAmountSource !== "insurer_statement" &&
          !(
            riskAmountSource === "recalculate_from_history" &&
            (
              [
                "decrease_pending_next_monthiversary",
                "uncertain",
              ].includes(riskAmountEffectiveStatus) ||
              ageAccuracyStatus === "error_or_uncertain"
            )
          )
        ) &&
        !(
          selection &&
          shinkongRiskHistoryKeys.includes(key) &&
          riskAmountSource !== "recalculate_from_history"
        ) &&
        !(
          shinkongRiskFormulaNotRequired &&
          [
            "risk_amount_source",
            "risk_calculation_actual_age",
            "risk_calculation_insurance_age",
            "insured_age_accuracy_status",
            "risk_calculation_stage",
            "risk_calculation_policy_account_value",
            "risk_calculation_net_premium_amount",
            "risk_amount_effective_status",
            "insurer_confirmed_current_risk_amount",
          ].includes(key)
        ) &&
        !(
          shinkongAccountValueOnlySelected &&
          [
            "benefit_exclusion_status",
            "post_event_insurance_cost_refund_status",
            "post_event_insurance_cost_refund_amount",
            "death_benefit_status",
            "remaining_funeral_benefit_limit",
            "funeral_excess_insurance_cost_refund_status",
            "funeral_excess_insurance_cost_refund_amount",
          ].includes(key)
        ) &&
        !(
          paidPremiumFactorAccountValueOnlySelected &&
          [
            "current_benefit_amount_status",
            "current_death_disability_benefit_amount",
            "total_disability_qualification_status",
            "death_benefit_status",
            "remaining_funeral_benefit_limit",
            "funeral_excess_insurance_cost_refund_status",
            "funeral_excess_insurance_cost_refund_amount",
          ].includes(key)
        ) &&
        !(
          paidPremiumFactorAccountValueOnlySelected &&
          policyStateChoice(selection, "claim_time_status") ===
            "time_barred" &&
          key === "benefit_exclusion_status"
        ) &&
        !(
          protectedAmountAccountValueOnlySelected &&
          [
            "insured_age_accuracy_status",
            "total_disability_qualification_status",
            "death_benefit_status",
            "remaining_funeral_benefit_limit",
            "funeral_excess_insurance_cost_refund_status",
            "funeral_excess_insurance_cost_refund_amount",
          ].includes(key)
        ) &&
        !(
          protectedAmountAccountValueOnlySelected &&
          policyStateChoice(selection, "claim_time_status") ===
            "time_barred" &&
          key === "benefit_exclusion_status"
        ) &&
        !(
          protectedAmountAccountValueOnlySelected &&
          policyStateChoice(selection, "benefit_exclusion_status") ===
            "confirmed_applies" &&
          key === "claim_time_status"
        ) &&
        !(
          key === "current_death_disability_benefit_amount" &&
          currentBenefitAmountStatusForRequirements !==
            "current_amount_provided"
        ),
    );

    const selectedPolicyYear = selection
      ? policyStateInteger(selection, "policy_year")
      : null;
    if (
      [
        "policy_year_average_target_premium_account_value_addition",
        "policy_year_average_basic_premium_account_value_addition",
      ].includes(normalizedEntry.calculation_basis) &&
      (selectedPolicyYear === null || selectedPolicyYear < 6)
    ) {
      add("policy_effect_status_at_event", "policy_year");
    } else if (
      normalizedEntry.calculation_basis ===
        "policy_year_tiered_premium_or_face_amount" &&
      selectedPolicyYear !== null &&
      normalizedEntry.policy_year_cutoff &&
      selectedPolicyYear > normalizedEntry.policy_year_cutoff
    ) {
      add("policy_year");
    } else {
      add(...entryPolicyStateKeys);
    }
    add(
      normalizedEntry.quantity_state_key,
      normalizedEntry.quantity_cap_state_key,
      normalizedEntry.expense_state_key,
      normalizedEntry.rate_state_key,
      normalizedEntry.limit_rate_state_key,
      normalizedEntry.secondary_limit_rate_state_key,
      normalizedEntry.secondary_limit_state_key,
      normalizedEntry.multiplier_state_key,
      normalizedEntry.rate_condition_state_key,
      normalizedEntry.tier_selection_state_key,
      normalizedEntry.eligibility_state_key,
      entryEligibilitySuppressesAmountRequirements
        ? ""
        : normalizedEntry.exclusion_state_key,
      normalizedEntry.cumulative_paid_state_key,
      normalizedEntry.cumulative_paid_multiplier_state_key,
    );
    const eligibilityRule = normalizedEntry.eligibility_rule;
    if (eligibilityRule?.type === "long_term_care_state") {
      add(
        eligibilityRule.qualification_type_key,
        eligibilityRule.duration_months_key,
        eligibilityRule.permanence_status_key,
        eligibilityRule.medical_confirmation_status_key,
        eligibilityRule.previous_claim_status_key,
      );
      const qualificationType = selection
        ? policyStateChoice(
            selection,
            eligibilityRule.qualification_type_key,
          )
        : "";
      if (!qualificationType || qualificationType === "adl") {
        add(eligibilityRule.adl_impairment_count_key);
      }
      if (!qualificationType || qualificationType === "cognitive") {
        add(
          eligibilityRule.cdr_score_key,
          eligibilityRule.cognitive_diagnosis_status_key,
        );
      }
      if (eligibilityRule.payment_period_status_key) {
        add(eligibilityRule.payment_period_status_key);
      }
    }
    const isChubbDisabilitySupportMonthlyEntry =
      selection?.version_characteristics?.product_family ===
        "chubb-disability-support-addendum" &&
      normalizedEntry.id === "chubb-disability-support-monthly";
    if (isChubbDisabilitySupportMonthlyEntry) {
      add(
        "disability_support_claim_status",
        "policy_effect_status_at_event",
        "insured_age_at_event",
        "disability_grade",
        "disability_status_after_180_days",
        "other_disability_support_monthly_amount",
        "prior_disability_status",
      );
      if (
        policyStateChoice(selection, "prior_disability_status") === "exists"
      ) {
        add(
          "insurer_approved_remaining_disability_support_months",
        );
      }
    }
    if (normalizedEntry.calculation_basis === "account_value" || normalizedEntry.basis === "policy_account_value") {
      add("policy_account_value");
    }
    if (normalizedEntry.calculation_basis === "policy_value_component") {
      add("policy_value_component", "policy_values_converted_to_twd");
    }
    if (normalizedEntry.calculation_basis === "maturity_policy_account_value") {
      add(
        normalizedEntry.policy_state_keys.find(
          (key) =>
            key.includes("maturity") &&
            key.includes("policy_account_value"),
        ) || "maturity_policy_account_value",
      );
      if (
        normalizedEntry.policy_state_keys.includes(
          "policy_values_converted_to_twd",
        )
      ) {
        add("policy_values_converted_to_twd");
      }
    }
    if (normalizedEntry.calculation_basis === "policy_value_plus_general_insurance_amount") {
      add(
        "policy_value_component",
        "general_death_disability_insurance_amount",
        "policy_values_converted_to_twd",
      );
    }
    if (
      normalizedEntry.calculation_basis ===
      "policy_value_plus_general_and_accidental_insurance_amount"
    ) {
      add(
        "policy_value_component",
        "general_death_disability_insurance_amount",
        "accidental_death_disability_insurance_amount",
        "policy_values_converted_to_twd",
      );
    }
    if (
      normalizedEntry.calculation_basis ===
      "protected_amount_plus_policy_account_value"
    ) {
      add(
        normalizedEntry.policy_state_keys.find(
          (key) =>
            key.includes("benefit_valuation") &&
            key.includes("policy_account_value"),
        ) || "benefit_valuation_policy_account_value",
      );
      if (
        normalizedEntry.policy_state_keys.includes(
          "policy_values_converted_to_twd",
        )
      ) {
        add("policy_values_converted_to_twd");
      }
      if (
        policyStateChoice(selection, "investment_allocation_status") ===
        "awaiting_allocation"
      ) {
        add("unallocated_net_premium_amount");
      }
      if (
        !minorAccountValueReturnSelected &&
        policyStateChoice(selection, "death_benefit_status") ===
        "funeral_limited"
      ) {
        add("remaining_funeral_benefit_limit");
      }
    }
    if (normalizedEntry.calculation_basis === "net_amount_at_risk_plus_policy_account_value") {
      add(
        ...(entryPolicyStateKeys.length
          ? entryPolicyStateKeys
          : ["policy_account_value"]),
      );
      if (policyTypeUsesFuneralLimit(normalizedEntry, selection)) {
        add("death_benefit_status", "remaining_funeral_benefit_limit");
      }
    }
    if (normalizedEntry.calculation_basis === "paid_premium_factor_account_value_formula") {
      const formulaAccountValueKey =
        normalizedEntry.policy_state_keys.find((key) =>
          key.includes("policy_account_value"),
        ) || "policy_account_value";
      add(formulaAccountValueKey);
      const requiresCurrentBenefitAmountStatus =
        normalizedEntry.policy_state_keys.includes(
          "current_benefit_amount_status",
        );
      const currentBenefitAmountStatus = selection
        ? policyStateChoice(selection, "current_benefit_amount_status")
        : "";
      if (!paidPremiumFactorAccountValueOnlySelected) {
        if (
          currentBenefitAmountStatus ===
          "current_amount_provided"
        ) {
          add("current_death_disability_benefit_amount");
        } else if (
          !requiresCurrentBenefitAmountStatus ||
          currentBenefitAmountStatus ===
            "formula_confirmed_current"
        ) {
          add(
            "paid_premium_total",
            "partial_termination_amount_total",
            "specified_percent_or_multiplier",
          );
          if (
            selection?.version_characteristics
              ?.specified_factor_unit_required === true &&
            !selection?.version_characteristics
              ?.specified_factor_unit_fixed
          ) {
            add("specified_factor_unit");
          }
        }
      }
    }
    if (normalizedEntry.currency_state_key) add(normalizedEntry.currency_state_key);
    if (normalizedEntry.minor_account_value_return_age) add("insured_age_at_event");
    if (normalizedEntry.calculation_basis === "account_value_annuity_factor") {
      add("policy_account_value", "annuity_payment_amount");
    }
    if (
      normalizedEntry.calculation_basis ===
      "annuity_amount_or_lump_sum"
    ) {
      add(
        "annuity_payment_amount",
        "annuity_start_policy_account_value",
      );
    }
    if (
      normalizedEntry.calculation_basis === "annuity_face_amount_schedule" &&
      normalizedEntry.annuity_payment_pattern === "increasing"
    ) {
      add("annuity_payment_year");
    }
    if (
      normalizedEntry.calculation_basis ===
      "single_premium_minus_paid_annuity_total"
    ) {
      add(
        "single_premium_amount",
        "annuity_paid_total_amount",
      );
    }
    if (
      normalizedEntry.calculation_basis ===
      "reserve_minus_policy_loan_and_interest"
    ) {
      add(
        "policy_reserve_value",
        "policy_loan_and_interest_amount",
      );
    }
    if (
      !entryStateSuppressesAmountRequirements &&
      (
        normalizedEntry.calculation_basis ===
          "death_or_funeral_greater_of" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_greater_of_per_unit_floor_and_paid_premium_net" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_face_amount" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_percentage_of_face_amount" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_multiplier_of_face_amount" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_percentage_of_policy_state_amount" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_fixed_amount" ||
        normalizedEntry.calculation_basis ===
          "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset"
      )
    ) {
      add("death_benefit_status", "remaining_funeral_benefit_limit");
    }
    if (
      isUnpaidAnnuityBalanceEntry(normalizedEntry, text) &&
      normalizedEntry.calculation_basis !==
        "single_premium_minus_paid_annuity_total"
    ) {
      add("unpaid_annuity_balance");
    }
    if (isValueSharingBonusEntry(normalizedEntry, text)) {
      add("previous_policy_reserve_value", "declared_interest_rate_percent", "scheduled_interest_rate_percent");
    }
    if (unitKey === "current_policy_amount" || unitKey.includes("current_policy_amount")) {
      add("current_policy_amount");
    }
    if (normalizedEntry.calculation_basis === "greater_of" || hasAnyTerm(text, ["取最大值", "取其大", "較高給付"])) {
      if (hasAnyTerm(text, ["當年度保險金額", "當時之保險金額", "當時保險金額", "保險金額"])) add("current_policy_amount");
      if (hasAnyTerm(text, ["保單價值準備金"])) add("policy_reserve_value");
      if (hasAnyTerm(text, ["保費總和", "保險費總和", "應繳保險費"])) add("premium_total_amount");
      if (hasAnyTerm(text, ["解約金", "現金價值"])) add("cash_surrender_value");
    }
    if (
      ["reimbursement_with_cap", "percentage_of_actual_expense_with_cap"].includes(normalizedEntry.calculation_basis) &&
      (normalizedEntry.basis === "policy_recorded_limit" || hasAnyTerm(text, ["保單所記載", "實支實付限額", "約定限額"]))
    ) {
      add(
        POLICY_STATE_FIELDS[unitKey] &&
          ["money", "non_negative_money"].includes(
            POLICY_STATE_FIELDS[unitKey].type,
          )
          ? unitKey
          : "reimbursement_limit",
      );
    }
    if (
      normalizedEntry.calculation_basis === "percentage_of_base" &&
      POLICY_STATE_FIELDS[unitKey] &&
      ["money", "non_negative_money"].includes(
        POLICY_STATE_FIELDS[unitKey].type,
      )
    ) {
      add(unitKey);
    }
    if (
      !normalizedEntry.amount &&
      (
        normalizedEntry.basis === "hospital_daily_amount" ||
        (
          normalizedEntry.calculation_basis === "unknown" &&
          hasAnyTerm(text, ["住院保險金日額", "住院日額"])
        )
      )
    ) {
      add("hospital_daily_amount");
    }
    if (hasAnyTerm(text, ["解約金", "現金價值"])) add("cash_surrender_value");
    if (hasAnyTerm(text, ["保單紅利", "紅利"])) add("policy_dividend_amount");
    if (hasAnyTerm(text, ["保險費折減", "保費折減", "保險費折扣", "保費折扣", "保險費折抵"])) add("premium_amount");
    if (
      normalizedEntry.calculation_basis === "waiver" ||
      hasAnyTerm(text, ["豁免保險費", "豁免基本保險費", "保險費豁免", "免繳保險費"])
    ) {
      add("remaining_premium_amount");
    }
    if (hasAnyTerm(text, ["分期定期保險金"]) && !normalizedEntry.amount) add("installment_periodic_amount");
    if (
      hasAnyTerm(text, ["未支領之年金餘額", "未支領年金餘額"]) &&
      normalizedEntry.calculation_basis !==
        "single_premium_minus_paid_annuity_total"
    ) {
      add("unpaid_annuity_balance");
    }
    if (
      hasAnyTerm(text, ["保單價值準備金"]) &&
      !isValueSharingBonusEntry(normalizedEntry, text) &&
      normalizedEntry.calculation_basis !== "greater_of" &&
      ![
        "policy_value_component",
        "policy_value_plus_general_insurance_amount",
        "policy_value_plus_general_and_accidental_insurance_amount",
      ].includes(normalizedEntry.calculation_basis)
    ) {
      add("policy_reserve_value");
    }

    return uniquePolicyStateFields(keys);
  }

  function policyStateFieldsForEntry(entry) {
    return policyStateFieldKeysForEntry(entry).map((key) => ({ key, ...POLICY_STATE_FIELDS[key] }));
  }

  function policyStateFieldForItem(key, item) {
    const field = { key, ...POLICY_STATE_FIELDS[key] };
    if (
      key === "contract_currency" &&
      item?.version_characteristics?.contract_currency_code_format ===
        "iso_4217_alpha3"
    ) {
      return {
        ...field,
        max_length: 3,
        pattern: "^[A-Za-z]{3}$",
        guidance:
          "請填保單首頁記載的 ISO 三碼幣別，例如 USD、AUD 或 CNY；下方所有金額都必須使用同一幣別。",
      };
    }
    if (
      key === "risk_calculation_stage" &&
      [
        "shinkong-jinhaoyi-variable-universal-life",
        "shinkong-jinmanyi-variable-universal-life",
      ].includes(item?.version_characteristics?.product_family) &&
      item?.version_characteristics?.age15_recalculation_applies !== true
    ) {
      return {
        ...field,
        options: field.options.filter(
          (option) => option.value !== "age15_recalculation",
        ),
      };
    }
    if (key === "prudential_youhuo_surgery_rate_percent") {
      const version = item?.version_characteristics || {};
      const min = Number(version.surgery_schedule_rate_min_percent);
      const max = Number(version.surgery_schedule_rate_max_percent);
      return {
        ...field,
        min: Number.isFinite(min) && min > 0 ? min : field.min,
        max: Number.isFinite(max) && max > 0 ? max : field.max,
        guidance:
          Number.isFinite(min) && Number.isFinite(max)
            ? `請查 exact product ID 手術附表輸入 ${min}% 至 ${max}%；同次住院須先依條款合併。`
            : field.guidance,
      };
    }
    if (key !== "disability_benefit_rate_percent") return field;
    const rates = Array.isArray(
      item?.version_characteristics?.disability_rate_options_percent,
    )
      ? item.version_characteristics.disability_rate_options_percent
          .map(Number)
          .filter(
            (rate) =>
              Number.isFinite(rate) &&
              rate > 0 &&
              rate <= MAX_RATE * 100,
          )
      : [];
    const uniqueRates = [...new Set(rates)].sort((left, right) => right - left);
    if (!uniqueRates.length) return field;
    return {
      ...field,
      type: "choice",
      options: uniqueRates.map((rate) => ({
        value: String(rate),
        label: `${rate}%`,
      })),
    };
  }

  function policyStateRequirements(item) {
    const entries = effectiveCoverageEntries(item);
    const deathBenefitStatus = policyStateChoice(item, "death_benefit_status");
    const funeralRefundStatus = policyStateChoice(
      item,
      "funeral_excess_insurance_cost_refund_status",
    );
    const policyType = selectedPolicyType(item);
    const isAllianzAge111 =
      item?.version_characteristics?.product_family ===
      "allianz-age111-variable-universal-life-face-amount";
    const isAllianzWorldview =
      item?.version_characteristics?.product_family ===
      "allianz-worldview-foreign-currency-variable-universal-life";
    const isAllianzNewExcellence =
      item?.version_characteristics?.product_family ===
      "allianz-new-excellence-variable-universal-life";
    const isGlobalExcellence =
      item?.version_characteristics?.product_family ===
      "global-excellence-variable-universal-life";
    const isGlobalNewExcellence =
      item?.version_characteristics?.product_family ===
      "global-new-excellence-variable-universal-life";
    const postEventInsuranceCostRefundStatus = policyStateChoice(
      item,
      "post_event_insurance_cost_refund_status",
    );
    const formulaKeys = [];
    if (
      item?.version_characteristics?.insured_age_accuracy_status_required ===
      true
    ) {
      formulaKeys.push("insured_age_accuracy_status");
    }
    if (isAllianzAge111 && policyType.includes("甲")) {
      formulaKeys.push("insurance_deduction_amount");
    }
    if (isAllianzAge111 && policyType.includes("丙")) {
      formulaKeys.push("insurance_deduction_amount", "insured_age_at_event");
    }
    if (isAllianzAge111 && policyType.includes("丁")) {
      formulaKeys.push("insured_age_at_event");
    }
    if (isAllianzAge111 && policyType.includes("戊")) {
      formulaKeys.push(
        "insurance_deduction_amount",
        "insured_age_at_event",
        "paid_premium_total",
        "partial_termination_amount_total",
      );
    }
    if (isAllianzWorldview || isAllianzNewExcellence) {
      const semanticPhase = String(
        item?.version_characteristics?.semantic_phase || "",
      );
      if (
        semanticPhase === "legacy-annual-insurance-amount-abc" &&
        isPolicyTypeA(policyType)
      ) {
        formulaKeys.push("insured_age_at_issue", "policy_year");
      }
      if (
        semanticPhase !== "legacy-annual-insurance-amount-abc" &&
        (isPolicyTypeA(policyType) || isPolicyTypeB(policyType))
      ) {
        formulaKeys.push("insured_age_at_event");
      }
    }
    if (
      isGlobalExcellence &&
      item?.version_characteristics?.minimum_rate_formula_variant !==
        "fixed_110_percent"
    ) {
      formulaKeys.push("insured_age_at_event");
    }
    if (isGlobalNewExcellence) {
      const semanticPhase = String(
        item?.version_characteristics?.semantic_phase || "",
      );
      if (semanticPhase === "premium_three_way_ab") {
        formulaKeys.push(
          "paid_premium_total",
          "partial_termination_amount_total",
        );
      } else if (
        semanticPhase === "four_type_age_bands_minor15_130_115_101" ||
        (
          semanticPhase === "four_type_age_bands_130_115_101" &&
          (isPolicyTypeA(policyType) || isPolicyTypeB(policyType))
        )
      ) {
        formulaKeys.push("insured_age_at_event");
      }
    }
    if (policyTypeRequiresInsuranceDeduction(item, policyType)) {
      formulaKeys.push("insurance_deduction_amount");
    }
    const declaredPolicyInputKeys = Array.isArray(
      item?.version_characteristics?.required_policy_inputs,
    )
      ? item.version_characteristics.required_policy_inputs
      : [];
    const keys = uniquePolicyStateFields(
      [
        ...declaredPolicyInputKeys,
        ...entries
          .flatMap((entry) => {
            const normalizedEntry = normalizeCoverageEntry(entry, 0);
            const keys = policyStateFieldKeysForEntry(entry, item);
            const eligibilityKey =
              normalizedEntry.eligibility_state_key;
            const eligibilityValue = eligibilityKey
              ? policyStateChoice(item, eligibilityKey)
              : "";
            if (eligibilityKey && !eligibilityValue) {
              return [eligibilityKey];
            }
            if (
              eligibilityKey &&
              [
                ...normalizedEntry.ineligible_values,
                ...normalizedEntry.uncertain_values,
              ].includes(eligibilityValue)
            ) {
              return [eligibilityKey];
            }
            const exclusionKey = normalizedEntry.exclusion_state_key;
            const exclusionValue = exclusionKey
              ? policyStateChoice(item, exclusionKey)
              : "";
            if (
              exclusionKey &&
              (
                !exclusionValue ||
                normalizedEntry.exclusion_values.includes(exclusionValue)
              )
            ) {
              return [exclusionKey];
            }
            return keys;
          })
          .filter(
            (key) =>
              (
                key !== "remaining_funeral_benefit_limit" ||
                deathBenefitStatus === "funeral_limited"
              ) &&
              (
                ![
                  "funeral_excess_insurance_cost_refund_status",
                  "funeral_excess_insurance_cost_refund_amount",
                ].includes(key) ||
                (
                  deathBenefitStatus === "funeral_limited" &&
                  (
                    key !==
                      "funeral_excess_insurance_cost_refund_amount" ||
                    funeralRefundStatus === "confirmed_amount"
                  )
                )
              ) &&
              (
                key !== "post_event_insurance_cost_refund_amount" ||
                postEventInsuranceCostRefundStatus ===
                  "charged_after_event"
              ),
          ),
        ...formulaKeys,
      ],
    );
    const orderedKeys = [
      ...keys.filter((key) => POLICY_STATE_FIELDS[key]?.type !== "boolean"),
      ...keys.filter((key) => POLICY_STATE_FIELDS[key]?.type === "boolean"),
    ];
    return {
      fields: orderedKeys.map((key) => policyStateFieldForItem(key, item)),
    };
  }

  function declaredSelectionMode(item) {
    const explicit = canonicalSelectionMode(item?.selection_type || item?.input_mode || item?.quantity_mode);
    if (!explicit) return "";
    if (explicit === "unknown") return explicit;
    const hasReviewedPlanOptions = normalizePlanOptions(item).length > 0;
    const isTermsDeclared = normalizeText(item?.selection_source) === "terms";
    if (hasReviewedPlanOptions || isTermsDeclared) return explicit;
    return "";
  }

  function selectionMode(item) {
    const declared = declaredSelectionMode(item);
    if (declared) return declared;
    return "unknown";
  }

  function selectionRequirements(item) {
    const mode = selectionMode(item);
    return {
      mode,
      label: String(item?.selection_label || "").trim() || SELECTION_MODES[mode].label,
      face_amount_label:
        String(item?.face_amount_label || "").trim() ||
        (mode === "face_amount_plan" ? "基本保額" : "契約保險金額"),
      guidance: String(item?.selection_guidance || "").trim(),
      fields: [...SELECTION_MODES[mode].fields],
      plan_options: normalizePlanOptions(item),
      unit_fields: normalizeUnitFields(item),
      is_verified: Boolean(declaredSelectionMode(item)) && mode !== "unknown",
    };
  }

  function effectiveCoverageEntries(item) {
    const options = normalizePlanOptions(item);
    const selectedPlan = options.find((option) => option.value === item?.plan_name || option.label === item?.plan_name);
    if (selectedPlan?.coverage_entries?.length) return selectedPlan.coverage_entries;
    return normalizeCoverageEntries(item?.coverage_entries || item?.benefit_rules);
  }

  function policyState(selection) {
    return selection?.policy_state && typeof selection.policy_state === "object" ? selection.policy_state : {};
  }

  function policyStateMoney(selection, key) {
    return normalizeMoneyAmount(policyState(selection)[key]);
  }

  function policyStateNonNegativeMoney(selection, key) {
    return normalizeNonNegativeMoneyAmount(policyState(selection)[key]);
  }

  function policyStateNumber(selection, key) {
    const field = POLICY_STATE_FIELDS[key] || {};
    return normalizeNumberValue(
      policyState(selection)[key],
      field.max || MAX_RATE * 100,
      field.allow_zero === true,
    );
  }

  function policyStateInteger(selection, key) {
    const field = POLICY_STATE_FIELDS[key] || {};
    return field.allow_zero
      ? normalizeNonNegativeInteger(
          policyState(selection)[key],
          field.max || MAX_INSURED_AGE,
        )
      : normalizeInteger(
          policyState(selection)[key],
          field.max || MAX_INSURED_AGE,
        );
  }

  function policyStateText(selection, key) {
    const field = POLICY_STATE_FIELDS[key] || {};
    return normalizePolicyText(policyState(selection)[key], field.max_length || 20);
  }

  function policyStateChoice(selection, key) {
    const field = POLICY_STATE_FIELDS[key] || {};
    return normalizePolicyChoice(policyState(selection)[key], field);
  }

  function policyStateAmount(selection, key) {
    return POLICY_STATE_FIELDS[key]?.type === "non_negative_money"
      ? policyStateNonNegativeMoney(selection, key)
      : policyStateMoney(selection, key);
  }

  function policyStateBoolean(selection, key) {
    return policyState(selection)[key] === true;
  }

  function policyStateRate(selection, key) {
    const rawValue = policyState(selection)[key];
    if (rawValue === "" || rawValue === null || rawValue === undefined) return null;
    const value = Number(String(rawValue).replaceAll(",", ""));
    if (!Number.isFinite(value) || value < 0 || value / 100 > MAX_RATE) return null;
    return value / 100;
  }

  function selectedAccountValue(selection) {
    return normalizeMoneyAmount(selection?.account_value) || policyStateMoney(selection, "policy_account_value");
  }

  function annualPremiumTotalAmount(selection, policyYear = null) {
    const annualPremium = policyStateMoney(
      selection,
      "standard_annual_premium_amount",
    );
    const paymentPeriodYears = policyStateInteger(
      selection,
      "premium_payment_period_years",
    );
    const countedYears =
      policyYear === null
        ? paymentPeriodYears
        : Math.min(policyYear, paymentPeriodYears || 0);
    if (!annualPremium || !paymentPeriodYears || !countedYears) return null;
    return safeIntegerProduct(annualPremium, countedYears);
  }

  function selectedPolicyType(selection) {
    return normalizeText(selection?.policy_type || selection?.plan_name || policyState(selection).policy_type);
  }

  function policyTypeUsesFuneralLimit(entry, selection) {
    const policyType = selectedPolicyType(selection);
    return Boolean(
      policyType &&
        entry.funeral_limit_plan_options.some(
          (option) => normalizeText(option) === policyType,
        ),
    );
  }

  function policyTypeRequiresInsuranceDeduction(selection, policyType) {
    if (!policyType) return false;
    const options =
      selection?.version_characteristics
        ?.insurance_deduction_amount_policy_type_options;
    return Boolean(
      Array.isArray(options) &&
        options.some(
          (option) => normalizeText(option) === normalizeText(policyType),
        ),
    );
  }

  function isPolicyTypeA(policyType) {
    return policyType.includes("甲") || /^A(?:型)?$/i.test(policyType);
  }

  function isPolicyTypeB(policyType) {
    return policyType.includes("乙") || /^B(?:型)?$/i.test(policyType);
  }

  function isPolicyTypeC(policyType) {
    return policyType.includes("丙") || /^C(?:型)?$/i.test(policyType);
  }

  function isPolicyTypeD(policyType) {
    return policyType.includes("丁") || /^D(?:型)?$/i.test(policyType);
  }

  function unexpiredInsuranceCostRefundApplies(selection, entry, policyType) {
    const rule = normalizeText(
      selection?.version_characteristics
        ?.unexpired_insurance_cost_refund_rule,
    );
    if (!rule || rule === "always") return true;
    if (rule === "minor_death_only") {
      const insuredAge = policyStateInteger(
        selection,
        "insured_age_at_event",
      );
      const minorReturnAge = Number(
        entry?.minor_account_value_return_age,
      );
      return (
        Number.isSafeInteger(insuredAge) &&
        Number.isSafeInteger(minorReturnAge) &&
        insuredAge < minorReturnAge
      );
    }
    if (
      rule !==
      "type_a_when_account_value_exceeds_face_amount_type_b_always"
    ) {
      return true;
    }
    if (isPolicyTypeB(policyType)) return true;
    if (!isPolicyTypeA(policyType)) return true;

    const accountValueStateKey =
      entry?.policy_state_keys?.find((key) =>
        key.includes("policy_account_value"),
      ) || "policy_account_value";
    const accountValue = policyStateNonNegativeMoney(
      selection,
      accountValueStateKey,
    );
    const faceAmount = normalizeMoneyAmount(selection?.face_amount);
    return accountValue === null || !faceAmount || accountValue > faceAmount;
  }

  function thresholdFactorForAge(selection, insuredAge) {
    if (insuredAge === null) return null;
    const schedule = selection?.version_characteristics?.threshold_factor_schedule;
    if (!Array.isArray(schedule)) return null;
    const bracket = schedule.find((item) => {
      const minAge = Number(item?.min_age);
      const maxAge = Number(item?.max_age);
      return (
        Number.isSafeInteger(minAge) &&
        Number.isSafeInteger(maxAge) &&
        insuredAge >= minAge &&
        insuredAge <= maxAge
      );
    });
    const factor = Number(bracket?.factor);
    return Number.isFinite(factor) && factor >= 0 && factor <= MAX_RATE ? factor : null;
  }

  function missingPolicyStateFields(selection, keys) {
    return uniquePolicyStateFields(keys).filter((key) => {
      const field = POLICY_STATE_FIELDS[key];
      if (field?.type === "rate") return policyStateRate(selection, key) === null;
      if (field?.type === "number") return policyStateNumber(selection, key) === null;
      if (field?.type === "integer") return policyStateInteger(selection, key) === null;
      if (field?.type === "text") return !policyStateText(selection, key);
      if (field?.type === "choice") return !policyStateChoice(selection, key);
      if (field?.type === "boolean") return !policyStateBoolean(selection, key);
      if (field?.type === "non_negative_money") return policyStateNonNegativeMoney(selection, key) === null;
      return policyStateMoney(selection, key) === null;
    });
  }

  function needsPolicyStateResult(result, selection, keys) {
    const required = missingPolicyStateFields(selection, keys);
    return { ...result, state: "needs_policy_state", required_fields: required.length ? required : uniquePolicyStateFields(keys) };
  }

  function entryConditionResult(entry, selection, result) {
    if (
      [
        "taiwan_new_cancer_health_event_status",
        "taiwan_cancer_insurance_event_status",
      ].includes(entry.exclusion_state_key)
    ) {
      const selectedValue = policyStateChoice(
        selection,
        entry.exclusion_state_key,
      );
      if (!selectedValue) {
        return needsPolicyStateResult(
          result,
          selection,
          [entry.exclusion_state_key],
        );
      }
      if (selectedValue === "not_eligible_or_uncertain") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            entry.exclusion_state_key ===
            "taiwan_cancer_insurance_event_status"
              ? "taiwan_cancer_insurance_event_eligibility_uncertain"
              : "taiwan_new_cancer_event_eligibility_uncertain",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
      if (entry.exclusion_values.includes(selectedValue)) {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
    }
    if (entry.eligibility_state_key) {
      const selectedValue = policyStateChoice(
        selection,
        entry.eligibility_state_key,
      );
      if (!selectedValue) {
        return needsPolicyStateResult(
          result,
          selection,
          [entry.eligibility_state_key],
        );
      }
      if (entry.uncertain_values.includes(selectedValue)) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "claim_eligibility_uncertain",
          eligibility_state_key: entry.eligibility_state_key,
          eligibility_value: selectedValue,
        };
      }
      if (entry.ineligible_values.includes(selectedValue)) {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          eligibility_state_key: entry.eligibility_state_key,
          eligibility_value: selectedValue,
        };
      }
    }
    if (entry.minimum_multiplier && entry.multiplier_state_key) {
      const field = POLICY_STATE_FIELDS[entry.multiplier_state_key] || {};
      const selectedMultiplier =
        field.type === "rate"
          ? policyStateRate(selection, entry.multiplier_state_key)
          : field.type === "number"
            ? policyStateNumber(selection, entry.multiplier_state_key)
            : policyStateInteger(selection, entry.multiplier_state_key);
      if (selectedMultiplier === null) {
        return needsPolicyStateResult(result, selection, [
          entry.multiplier_state_key,
        ]);
      }
      if (selectedMultiplier < entry.minimum_multiplier) {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          multiplier_state_key: entry.multiplier_state_key,
          multiplier: selectedMultiplier,
          minimum_multiplier: entry.minimum_multiplier,
        };
      }
    }
    if (entry.maximum_multiplier && entry.multiplier_state_key) {
      const field = POLICY_STATE_FIELDS[entry.multiplier_state_key] || {};
      const selectedMultiplier =
        field.type === "rate"
          ? policyStateRate(selection, entry.multiplier_state_key)
          : field.type === "number"
            ? policyStateNumber(selection, entry.multiplier_state_key)
            : policyStateInteger(selection, entry.multiplier_state_key);
      if (selectedMultiplier === null) {
        return needsPolicyStateResult(result, selection, [
          entry.multiplier_state_key,
        ]);
      }
      if (selectedMultiplier > entry.maximum_multiplier) {
        return needsPolicyStateResult(result, selection, [
          entry.multiplier_state_key,
        ]);
      }
    }
    if (entry.exclusion_state_key) {
      const selectedValue = policyStateChoice(
        selection,
        entry.exclusion_state_key,
      );
      if (!selectedValue) {
        return needsPolicyStateResult(
          result,
          selection,
          [entry.exclusion_state_key],
        );
      }
      if (
        entry.exclusion_state_key ===
          "taiwan_inpatient_daily_event_status" &&
        selectedValue === "not_eligible_or_uncertain"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "inpatient_event_eligibility_uncertain",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
      if (
        entry.exclusion_state_key ===
          "fubon_group_one_year_cancer_event_status" &&
        selectedValue === "not_eligible_or_uncertain"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "fubon_group_cancer_event_eligibility_uncertain",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
      if (
        entry.exclusion_state_key ===
          "taiwan_inpatient_daily_event_status" &&
        selectedValue === "day_hospital_or_day_care"
      ) {
        if (
          selection?.version_characteristics
            ?.day_hospital_excluded === true
        ) {
          return {
            ...result,
            value: 0,
            state: "not_eligible",
            exclusion_state_key: entry.exclusion_state_key,
            exclusion_value: selectedValue,
          };
        }
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "day_hospital_not_explicitly_resolved",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
      if (entry.exclusion_values.includes(selectedValue)) {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          exclusion_state_key: entry.exclusion_state_key,
          exclusion_value: selectedValue,
        };
      }
    }
    if (entry.rate_condition_state_key) {
      const selectedValue = policyStateChoice(
        selection,
        entry.rate_condition_state_key,
      );
      if (!selectedValue) {
        return needsPolicyStateResult(
          result,
          selection,
          [entry.rate_condition_state_key],
        );
      }
    }
    return null;
  }

  function entryConditionalRate(entry, selection) {
    if (!entry.rate_condition_state_key) return 1;
    const selectedValue = policyStateChoice(
      selection,
      entry.rate_condition_state_key,
    );
    return selectedValue === entry.rate_condition_value
      ? entry.rate
      : 1;
  }

  function adjustedEntryPayout(entry, selection, grossValue) {
    const appliedRate = entryConditionalRate(entry, selection);
    const rateAdjustedValue = Math.trunc(grossValue * appliedRate);
    if (!Number.isSafeInteger(rateAdjustedValue)) {
      return { state: "amount_overflow" };
    }
    if (!entry.cumulative_paid_state_key) {
      return {
        value: rateAdjustedValue,
        gross_value: grossValue,
        rate_adjusted_value: rateAdjustedValue,
        applied_rate: appliedRate,
        cumulative_paid_amount: null,
      };
    }
    const paidAmount = policyStateNonNegativeMoney(
      selection,
      entry.cumulative_paid_state_key,
    );
    if (paidAmount === null) {
      return {
        state: "needs_policy_state",
        required_fields: [entry.cumulative_paid_state_key],
      };
    }
    if (entry.aggregate_limit_entry_id) {
      const aggregateEntry = effectiveCoverageEntries(selection).find(
        (candidate) =>
          candidate.id === entry.aggregate_limit_entry_id,
      );
      const aggregateAmount = normalizeMoneyAmount(
        aggregateEntry?.amount,
      );
      const aggregateUnits = normalizeUnitCount(
        aggregateEntry?.unit_key
          ? selection.unit_counts?.[aggregateEntry.unit_key]
          : selection.unit_count,
      );
      const aggregateLimit =
        aggregateEntry?.calculation_basis === "per_unit"
          ? aggregateAmount && aggregateUnits
            ? safeIntegerProduct(aggregateAmount, aggregateUnits)
            : null
          : aggregateAmount;
      if (!aggregateLimit) {
        return {
          state:
            aggregateEntry?.calculation_basis === "per_unit"
              ? "needs_unit_count"
              : "needs_rate_table",
        };
      }
      const remainingAggregateLimit = Math.max(
        0,
        aggregateLimit - paidAmount,
      );
      return {
        value: Math.min(
          rateAdjustedValue,
          remainingAggregateLimit,
        ),
        gross_value: grossValue,
        rate_adjusted_value: rateAdjustedValue,
        applied_rate: appliedRate,
        cumulative_paid_amount: paidAmount,
        aggregate_limit: aggregateLimit,
        remaining_aggregate_limit: remainingAggregateLimit,
      };
    }
    return {
      value: Math.max(0, rateAdjustedValue - paidAmount),
      gross_value: grossValue,
      rate_adjusted_value: rateAdjustedValue,
      applied_rate: appliedRate,
      cumulative_paid_amount: paidAmount,
    };
  }

  function eligibilityResult(entry, selection, result) {
    const rule = entry?.eligibility_rule;
    if (rule?.type !== "long_term_care_state") return null;
    const qualificationType = policyStateChoice(
      selection,
      rule.qualification_type_key,
    );
    const durationMonths = policyStateInteger(
      selection,
      rule.duration_months_key,
    );
    const permanenceStatus = policyStateChoice(
      selection,
      rule.permanence_status_key,
    );
    const medicalConfirmationStatus = policyStateChoice(
      selection,
      rule.medical_confirmation_status_key,
    );
    const previousClaimStatus = policyStateChoice(
      selection,
      rule.previous_claim_status_key,
    );
    const cognitiveDiagnosisStatus =
      qualificationType === "cognitive"
        ? policyStateChoice(
            selection,
            rule.cognitive_diagnosis_status_key,
          )
        : "";
    const paymentPeriodStatus = rule.payment_period_status_key
      ? policyStateChoice(selection, rule.payment_period_status_key)
      : "";
    const routeField =
      qualificationType === "adl"
        ? rule.adl_impairment_count_key
        : qualificationType === "cognitive"
          ? rule.cdr_score_key
          : "";
    const requiredFields = [
      rule.qualification_type_key,
      ...(routeField ? [routeField] : []),
      rule.duration_months_key,
      rule.permanence_status_key,
      rule.medical_confirmation_status_key,
      rule.previous_claim_status_key,
      ...(qualificationType === "cognitive"
        ? [rule.cognitive_diagnosis_status_key]
        : []),
      ...(rule.payment_period_status_key
        ? [rule.payment_period_status_key]
        : []),
    ];
    if (
      !qualificationType ||
      durationMonths === null ||
      !permanenceStatus ||
      !medicalConfirmationStatus ||
      !previousClaimStatus ||
      (qualificationType === "cognitive" &&
        !cognitiveDiagnosisStatus) ||
      (rule.payment_period_status_key && !paymentPeriodStatus)
    ) {
      return needsPolicyStateResult(result, selection, requiredFields);
    }

    let qualificationValue = null;
    let qualificationMinimum = null;
    if (qualificationType === "adl") {
      qualificationValue = policyStateInteger(
        selection,
        rule.adl_impairment_count_key,
      );
      qualificationMinimum = rule.adl_minimum;
    } else if (qualificationType === "cognitive") {
      const cdrValue = policyStateChoice(
        selection,
        rule.cdr_score_key,
      );
      qualificationValue = cdrValue ? Number(cdrValue) : null;
      qualificationMinimum = rule.cdr_minimum;
    }
    if (qualificationValue === null) {
      return needsPolicyStateResult(result, selection, requiredFields);
    }

    const qualificationMet =
      qualificationValue >= qualificationMinimum;
    const durationMet =
      durationMonths >= rule.minimum_duration_months ||
      permanenceStatus === rule.permanent_value;
    const paymentPeriodMet =
      !rule.payment_period_status_key ||
      paymentPeriodStatus === rule.eligible_payment_period_value;
    const medicalConfirmationMet =
      medicalConfirmationStatus === rule.confirmed_value;
    const previousClaimMet =
      previousClaimStatus === rule.not_claimed_value;
    const cognitiveDiagnosisMet =
      qualificationType !== "cognitive" ||
      cognitiveDiagnosisStatus === rule.cognitive_confirmed_value;
    if (
      !qualificationMet ||
      !durationMet ||
      !medicalConfirmationMet ||
      !previousClaimMet ||
      !cognitiveDiagnosisMet ||
      !paymentPeriodMet
    ) {
      return {
        ...result,
        value: null,
        reference_amount: null,
        state: "not_eligible",
        eligibility: {
          type: rule.type,
          qualification_type: qualificationType,
          qualification_value: qualificationValue,
          qualification_minimum: qualificationMinimum,
          qualification_met: qualificationMet,
          duration_months: durationMonths,
          minimum_duration_months: rule.minimum_duration_months,
          duration_met: durationMet,
          permanence_status: permanenceStatus,
          medical_confirmation_status:
            medicalConfirmationStatus,
          medical_confirmation_met: medicalConfirmationMet,
          previous_claim_status: previousClaimStatus,
          previous_claim_met: previousClaimMet,
          cognitive_diagnosis_status:
            cognitiveDiagnosisStatus || undefined,
          cognitive_diagnosis_met: cognitiveDiagnosisMet,
          payment_period_status: paymentPeriodStatus || undefined,
          payment_period_met: paymentPeriodMet,
        },
      };
    }
    return null;
  }

  function policyStateBaseForEntry(entry, selection) {
    const text = entryPolicyStateText(entry);
    const unitKey = normalizeText(entry?.unit_key);
    if (hasAnyTerm(text, ["保險費折減", "保費折減", "保險費折扣", "保費折扣", "保險費折抵"])) {
      return { key: "premium_amount", value: policyStateMoney(selection, "premium_amount") };
    }
    if (entry?.basis === "hospital_daily_amount" || hasAnyTerm(text, ["住院保險金日額", "住院日額"])) {
      return { key: "hospital_daily_amount", value: policyStateMoney(selection, "hospital_daily_amount") };
    }
    if (hasAnyTerm(text, ["保單帳戶價值"])) {
      return { key: "policy_account_value", value: selectedAccountValue(selection) };
    }
    if (hasAnyTerm(text, ["保單價值準備金"])) {
      return { key: "policy_reserve_value", value: policyStateMoney(selection, "policy_reserve_value") };
    }
    if (
      unitKey === "current_policy_amount" ||
      unitKey.includes("current_policy_amount") ||
      hasAnyTerm(text, ["當年度保險金額", "當時之保險金額", "當時保險金額"])
    ) {
      return { key: "current_policy_amount", value: policyStateMoney(selection, "current_policy_amount") };
    }
    if (hasAnyTerm(text, ["解約金", "現金價值"])) {
      return { key: "cash_surrender_value", value: policyStateMoney(selection, "cash_surrender_value") };
    }
    if (
      POLICY_STATE_FIELDS[unitKey] &&
      ["money", "non_negative_money"].includes(
        POLICY_STATE_FIELDS[unitKey].type,
      )
    ) {
      return {
        key: unitKey,
        value: policyStateAmount(selection, unitKey),
      };
    }
    return { key: "", value: null };
  }

  function firstPolicyStateAmount(selection, keys) {
    for (const key of keys) {
      const value = policyStateMoney(selection, key);
      if (value) return { key, value };
    }
    return { key: "", value: null };
  }

  function allianzPolicyTypeCoverageValue(
    normalizedEntry,
    item,
    result,
  ) {
    const productFamily = String(
      item?.version_characteristics?.product_family || "",
    );
    const requiresContractCurrency =
      productFamily ===
      "allianz-worldview-foreign-currency-variable-universal-life";
    const exactRatioRequired =
      productFamily ===
        "allianz-new-excellence-variable-universal-life" &&
      item?.version_characteristics
        ?.fractional_formula_requires_insurer_confirmation === true;
    const decimalPlaces = moneyDecimalPlaces(item);
    const scale = 10 ** decimalPlaces;
    const currencyLabel = requiresContractCurrency
      ? normalizeContractCurrencyCode(
          policyState(item).contract_currency,
        )
      : "元";
    if (requiresContractCurrency && !currencyLabel) {
      return needsPolicyStateResult(result, item, [
        "contract_currency",
      ]);
    }

    const monetaryKeys = new Set([
      "value",
      "reference_amount",
      "gross_value_before_offsets",
      "gross_value_before_loan_offset",
      "gross_insurance_amount",
      "annual_insurance_amount",
      "face_amount",
      "account_value",
      "raw_account_value",
      "adjusted_account_value",
      "net_amount_at_risk",
      "protected_amount",
      "insurance_deduction_amount",
      "post_event_insurance_cost_refund_amount",
      "policy_loan_and_interest_amount",
      "unpaid_policy_charge_amount",
      "unpaid_monthly_deduction_amount",
    ]);
    const finish = (payload) => {
      const output = {
        ...result,
        ...payload,
        currency_label: currencyLabel,
        money_decimal_places: decimalPlaces,
      };
      for (const key of monetaryKeys) {
        if (Number.isSafeInteger(output[key])) {
          output[key] = output[key] / scale;
        }
      }
      return output;
    };
    const stateMoney = (key, allowZero = true) =>
      fixedPointMoney(
        policyState(item)[key],
        decimalPlaces,
        allowZero,
      )?.scaled ?? null;

    const accountValueStateKey =
      normalizedEntry.policy_state_keys.find((key) =>
        key.includes("policy_account_value"),
      ) || "policy_account_value";
    const rawAccountValue = stateMoney(accountValueStateKey);
    if (rawAccountValue === null) {
      return {
        ...result,
        state: "needs_account_value",
        required_fields: [accountValueStateKey],
        currency_label: currencyLabel,
      };
    }

    const requiresContractStatus =
      normalizedEntry.policy_state_keys.includes(
        "policy_effect_status_at_event",
      );
    const contractStatus = requiresContractStatus
      ? policyStateChoice(item, "policy_effect_status_at_event")
      : "active";
    if (requiresContractStatus && !contractStatus) {
      return needsPolicyStateResult(result, item, [
        "policy_effect_status_at_event",
      ]);
    }
    if (contractStatus !== "active") {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "contract_not_confirmed_active",
        policy_effect_status_at_event: contractStatus,
        currency_label: currencyLabel,
      };
    }

    const claimTimeStatusRequired =
      normalizedEntry.policy_state_keys.includes("claim_time_status");
    const claimTimeStatus = claimTimeStatusRequired
      ? policyStateChoice(item, "claim_time_status")
      : "within_claim_period";
    if (claimTimeStatusRequired && !claimTimeStatus) {
      return needsPolicyStateResult(result, item, [
        "claim_time_status",
      ]);
    }
    const exclusionStatusRequired =
      normalizedEntry.policy_state_keys.includes(
        "benefit_exclusion_status",
      );
    const exclusionStatus = exclusionStatusRequired
      ? policyStateChoice(item, "benefit_exclusion_status")
      : "none_confirmed";
    if (exclusionStatusRequired && !exclusionStatus) {
      return needsPolicyStateResult(result, item, [
        "benefit_exclusion_status",
      ]);
    }
    if (exclusionStatus !== "none_confirmed") {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "benefit_exclusion_requires_review",
        benefit_exclusion_status: exclusionStatus,
        currency_label: currencyLabel,
      };
    }
    const disabilityQualificationRequired =
      normalizedEntry.policy_state_keys.includes(
        "total_disability_qualification_status",
      );
    const disabilityQualificationStatus =
      disabilityQualificationRequired
        ? policyStateChoice(
            item,
            "total_disability_qualification_status",
          )
        : "confirmed_first_level_item";
    if (
      disabilityQualificationRequired &&
      !disabilityQualificationStatus
    ) {
      return needsPolicyStateResult(result, item, [
        "total_disability_qualification_status",
      ]);
    }
    if (
      disabilityQualificationStatus !==
      "confirmed_first_level_item"
    ) {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "total_disability_not_confirmed",
        total_disability_qualification_status:
          disabilityQualificationStatus,
        currency_label: currencyLabel,
      };
    }

    const refundStatusRequired =
      normalizedEntry.policy_state_keys.includes(
        "post_event_insurance_cost_refund_status",
      );
    const refundStatus = refundStatusRequired
      ? policyStateChoice(
          item,
          "post_event_insurance_cost_refund_status",
        )
      : "";
    if (refundStatusRequired && !refundStatus) {
      return needsPolicyStateResult(result, item, [
        "post_event_insurance_cost_refund_status",
      ]);
    }
    const refundAmountRequired =
      normalizedEntry.policy_state_keys.includes(
        "post_event_insurance_cost_refund_amount",
      ) && refundStatus === "charged_after_event";
    const refundAmount = refundAmountRequired
      ? stateMoney("post_event_insurance_cost_refund_amount")
      : 0;
    const loanAmount =
      normalizedEntry.policy_state_keys.includes(
        "policy_loan_and_interest_amount",
      )
        ? stateMoney("policy_loan_and_interest_amount")
        : 0;
    const unpaidAmount =
      normalizedEntry.policy_state_keys.includes(
        "unpaid_monthly_deduction_amount",
      )
        ? stateMoney("unpaid_monthly_deduction_amount")
        : 0;
    const missingOffsetFields = [
      ...(refundAmountRequired && refundAmount === null
        ? ["post_event_insurance_cost_refund_amount"]
        : []),
      ...(loanAmount === null
        ? ["policy_loan_and_interest_amount"]
        : []),
      ...(unpaidAmount === null
        ? ["unpaid_monthly_deduction_amount"]
        : []),
    ];
    if (missingOffsetFields.length) {
      return needsPolicyStateResult(
        result,
        item,
        missingOffsetFields,
      );
    }
    const formulaAccountValue = safeIntegerSum(
      rawAccountValue,
      refundAmount,
    );
    if (formulaAccountValue === null) {
      return { ...result, state: "amount_overflow" };
    }

    const totalOffsets = safeIntegerSum(loanAmount, unpaidAmount);
    if (totalOffsets === null) {
      return { ...result, state: "amount_overflow" };
    }
    if (claimTimeStatus === "time_barred") {
      if (totalOffsets > formulaAccountValue) {
        return finish({
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: formulaAccountValue,
          policy_loan_and_interest_amount: loanAmount,
          unpaid_policy_charge_amount: unpaidAmount,
          unpaid_monthly_deduction_amount: unpaidAmount,
          claim_time_status: claimTimeStatus,
        });
      }
      return finish({
        value: formulaAccountValue - totalOffsets,
        reference_amount: formulaAccountValue,
        state: "account_value_return",
        formula_type: "time_barred_account_value_return",
        account_value: formulaAccountValue,
        raw_account_value: rawAccountValue,
        adjusted_account_value: formulaAccountValue,
        post_event_insurance_cost_refund_amount: refundAmount,
        post_event_insurance_cost_refund_status: refundStatus,
        policy_loan_and_interest_amount: loanAmount,
        unpaid_policy_charge_amount: unpaidAmount,
        unpaid_monthly_deduction_amount: unpaidAmount,
        gross_value_before_loan_offset: formulaAccountValue,
        policy_effect_status_at_event: contractStatus,
        policy_state_key: accountValueStateKey,
        claim_time_status: claimTimeStatus,
        benefit_exclusion_status: exclusionStatus,
        product_family: productFamily,
      });
    }
    const minorReturnAge =
      normalizedEntry.minor_account_value_return_age;
    let insuredAge = null;
    if (minorReturnAge) {
      insuredAge = policyStateInteger(item, "insured_age_at_event");
      if (insuredAge === null) {
        return needsPolicyStateResult(result, item, [
          "insured_age_at_event",
        ]);
      }
      if (insuredAge < minorReturnAge) {
        if (totalOffsets > formulaAccountValue) {
          return finish({
            state: "needs_insurer_confirmation",
            confirmation_reason: "offsets_exceed_gross_benefit",
            gross_value_before_offsets: formulaAccountValue,
            policy_loan_and_interest_amount: loanAmount,
            unpaid_policy_charge_amount: unpaidAmount,
            unpaid_monthly_deduction_amount: unpaidAmount,
          });
        }
        return finish({
          value: formulaAccountValue - totalOffsets,
          reference_amount: formulaAccountValue,
          state: "account_value_return",
          formula_type: "minor_account_value_return",
          account_value: formulaAccountValue,
          raw_account_value: rawAccountValue,
          adjusted_account_value: formulaAccountValue,
          post_event_insurance_cost_refund_amount: refundAmount,
          post_event_insurance_cost_refund_status: refundStatus,
          policy_loan_and_interest_amount: loanAmount,
          unpaid_policy_charge_amount: unpaidAmount,
          unpaid_monthly_deduction_amount: unpaidAmount,
          gross_value_before_loan_offset: formulaAccountValue,
          policy_effect_status_at_event: contractStatus,
          policy_state_key: accountValueStateKey,
          insured_age_at_event: insuredAge,
          product_family: productFamily,
        });
      }
    }

    const policyType = selectedPolicyType(item);
    if (!policyType) {
      return {
        ...result,
        state: "needs_plan",
        required_fields: ["plan_name"],
        currency_label: currencyLabel,
      };
    }
    const faceAmount = fixedPointMoney(
      item.face_amount,
      decimalPlaces,
    )?.scaled ?? null;
    if (faceAmount === null) {
      return {
        ...result,
        state: "needs_face_amount",
        currency_label: currencyLabel,
      };
    }

    const insuranceDeductionRequired =
      policyTypeRequiresInsuranceDeduction(item, policyType);
    const insuranceDeductionAmount =
      insuranceDeductionRequired
        ? stateMoney("insurance_deduction_amount")
        : 0;
    if (insuranceDeductionAmount === null) {
      return needsPolicyStateResult(result, item, [
        "insurance_deduction_amount",
      ]);
    }

    const semanticPhase = String(
      item?.version_characteristics?.semantic_phase || "",
    );
    let annualInsuranceAmount = null;
    let thresholdFactor = null;
    let grossInsuranceAmount = null;
    if (semanticPhase === "legacy-annual-insurance-amount-abc") {
      if (isPolicyTypeA(policyType)) {
        const issueAge = policyStateInteger(
          item,
          "insured_age_at_issue",
        );
        const policyYear = policyStateInteger(item, "policy_year");
        if (issueAge === null || policyYear === null) {
          return needsPolicyStateResult(result, item, [
            "insured_age_at_issue",
            "policy_year",
          ]);
        }
        if (issueAge < 14) {
          return {
            ...result,
            state: "outside_terms_formula_age_range",
            insured_age_at_issue: issueAge,
            minimum_formula_age: 14,
            currency_label: currencyLabel,
          };
        }
        const growthYears = Math.min(
          Math.max(policyYear - 1, 0),
          Math.max(60 - issueAge, 0),
        );
        const annualInsuranceAmountPercent = 100 + growthYears * 5;
        const annualRatio = exactRatioRequired
          ? safeExactRatio(faceAmount, annualInsuranceAmountPercent)
          : {
              status: "exact",
              value: safeFloorRatio(
                faceAmount,
                annualInsuranceAmountPercent,
              ),
            };
        if (annualRatio.status === "fractional") {
          const annualNetNumerator =
            BigInt(faceAmount) * BigInt(annualInsuranceAmountPercent) -
            BigInt(insuranceDeductionAmount) * 100n;
          const accountValueNumerator =
            BigInt(formulaAccountValue) * 100n;
          if (annualNetNumerator <= accountValueNumerator) {
            grossInsuranceAmount = formulaAccountValue;
          } else {
            return finish({
              state: "needs_insurer_confirmation",
              confirmation_reason:
                "fractional_policy_amount_rounding_undefined",
              rounding_component: "annual_insurance_amount",
              face_amount: faceAmount,
              annual_insurance_amount_factor_percent:
                annualInsuranceAmountPercent,
            });
          }
        } else if (annualRatio.value === null) {
          return { ...result, state: "amount_overflow" };
        } else {
          annualInsuranceAmount = annualRatio.value;
          grossInsuranceAmount = Math.max(
            annualInsuranceAmount - insuranceDeductionAmount,
            formulaAccountValue,
          );
        }
      } else if (isPolicyTypeB(policyType)) {
        grossInsuranceAmount = safeIntegerSum(
          faceAmount,
          formulaAccountValue,
        );
      } else if (isPolicyTypeC(policyType)) {
        grossInsuranceAmount = Math.max(
          faceAmount - insuranceDeductionAmount,
          formulaAccountValue,
        );
      }
    } else {
      if (isPolicyTypeA(policyType) || isPolicyTypeB(policyType)) {
        if (insuredAge === null) {
          insuredAge = policyStateInteger(
            item,
            "insured_age_at_event",
          );
        }
        if (insuredAge === null) {
          return needsPolicyStateResult(result, item, [
            "insured_age_at_event",
          ]);
        }
        thresholdFactor = thresholdFactorForAge(item, insuredAge);
        if (thresholdFactor === null) {
          return needsPolicyStateResult(result, item, [
            "insured_age_at_event",
          ]);
        }
      }
      const thresholdPercent =
        thresholdFactor === null
          ? null
          : Math.round(thresholdFactor * 100);
      const multiplierRatio =
        thresholdPercent === null
          ? null
          : exactRatioRequired
            ? safeExactRatio(formulaAccountValue, thresholdPercent)
            : {
                status: "exact",
                value: safeFloorRatio(
                  formulaAccountValue,
                  thresholdPercent,
                ),
              };
      if (
        multiplierRatio &&
        multiplierRatio.status !== "fractional" &&
        multiplierRatio.value === null
      ) {
        return { ...result, state: "amount_overflow" };
      }
      const accountValueTimesMultiplier =
        multiplierRatio?.value ?? null;
      const resolveFractionalMultiplier = (integerCandidate) => {
        if (multiplierRatio?.status !== "fractional") {
          return {
            state: "resolved",
            value: Math.max(
              integerCandidate,
              accountValueTimesMultiplier,
            ),
          };
        }
        const integerCandidateNumerator =
          BigInt(integerCandidate) * 100n;
        const multiplierNumerator =
          BigInt(formulaAccountValue) * BigInt(thresholdPercent);
        return integerCandidateNumerator > multiplierNumerator
          ? { state: "resolved", value: integerCandidate }
          : { state: "fractional", value: null };
      };
      if (isPolicyTypeA(policyType)) {
        const resolved = resolveFractionalMultiplier(
          faceAmount - insuranceDeductionAmount,
        );
        if (resolved.state === "fractional") {
          return finish({
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "fractional_policy_amount_rounding_undefined",
            rounding_component: "policy_account_value_multiplier",
            account_value: formulaAccountValue,
            threshold_factor: thresholdFactor,
          });
        }
        grossInsuranceAmount = resolved.value;
      } else if (isPolicyTypeB(policyType)) {
        const accountPlusFace = safeIntegerSum(
          faceAmount,
          formulaAccountValue,
        );
        if (accountPlusFace === null) {
          return { ...result, state: "amount_overflow" };
        }
        const resolved = resolveFractionalMultiplier(
          accountPlusFace,
        );
        if (resolved.state === "fractional") {
          return finish({
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "fractional_policy_amount_rounding_undefined",
            rounding_component: "policy_account_value_multiplier",
            account_value: formulaAccountValue,
            threshold_factor: thresholdFactor,
          });
        }
        grossInsuranceAmount = resolved.value;
      } else if (isPolicyTypeC(policyType)) {
        grossInsuranceAmount = safeIntegerSum(
          faceAmount,
          formulaAccountValue,
        );
      } else if (isPolicyTypeD(policyType)) {
        grossInsuranceAmount = Math.max(
          faceAmount - insuranceDeductionAmount,
          formulaAccountValue,
        );
      }
    }
    if (grossInsuranceAmount === null) {
      return {
        ...result,
        state: "needs_plan",
        required_fields: ["plan_name"],
        currency_label: currencyLabel,
      };
    }
    if (totalOffsets > grossInsuranceAmount) {
      return finish({
        state: "needs_insurer_confirmation",
        confirmation_reason: "offsets_exceed_gross_benefit",
        gross_value_before_offsets: grossInsuranceAmount,
        policy_loan_and_interest_amount: loanAmount,
        unpaid_policy_charge_amount: unpaidAmount,
        unpaid_monthly_deduction_amount: unpaidAmount,
      });
    }

    const netAmountAtRisk = Math.max(
      grossInsuranceAmount - formulaAccountValue,
      0,
    );
    return finish({
      value: grossInsuranceAmount - totalOffsets,
      reference_amount: grossInsuranceAmount,
      state: "calculated",
      face_amount: faceAmount,
      face_amount_label:
        String(item?.face_amount_label || "").trim() || "基本保額",
      account_value: formulaAccountValue,
      raw_account_value: rawAccountValue,
      adjusted_account_value: formulaAccountValue,
      net_amount_at_risk: netAmountAtRisk,
      protected_amount: netAmountAtRisk,
      gross_insurance_amount: grossInsuranceAmount,
      annual_insurance_amount: annualInsuranceAmount,
      policy_type: policyType,
      post_event_insurance_cost_refund_amount: refundAmount,
      post_event_insurance_cost_refund_status: refundStatus,
      policy_loan_and_interest_amount: loanAmount,
      unpaid_policy_charge_amount: unpaidAmount,
      unpaid_monthly_deduction_amount: unpaidAmount,
      policy_effect_status_at_event: contractStatus,
      claim_time_status: claimTimeStatus,
      benefit_exclusion_status: exclusionStatus,
      total_disability_qualification_status:
        disabilityQualificationStatus,
      gross_value_before_loan_offset: grossInsuranceAmount,
      formula_type: policyType.replace("型", ""),
      insurance_deduction_amount: insuranceDeductionAmount,
      threshold_factor: thresholdFactor,
      insured_age_at_event: insuredAge,
      policy_state_key: accountValueStateKey,
      semantic_phase: semanticPhase,
      product_family: productFamily,
    });
  }

  function shinkongJinhaoyiCoverageValue(
    normalizedEntry,
    item,
    result,
  ) {
    const productFamily = String(
      item?.version_characteristics?.product_family || "",
    );
    const hasStateKey = (key) =>
      normalizedEntry.policy_state_keys.includes(key);
    const accountValueStateKey =
      normalizedEntry.policy_state_keys.find((key) =>
        key.includes("benefit_valuation_policy_account_value"),
      ) || "benefit_valuation_policy_account_value";
    const rawAccountValue = policyStateNonNegativeMoney(
      item,
      accountValueStateKey,
    );
    const contractStatus = policyStateChoice(
      item,
      "policy_effect_status_at_event",
    );
    const claimTimeStatus = policyStateChoice(item, "claim_time_status");
    const loanAmount = policyStateNonNegativeMoney(
      item,
      "policy_loan_and_interest_amount",
    );
    const unpaidChargeAmount = policyStateNonNegativeMoney(
      item,
      "unpaid_policy_charge_amount",
    );
    if (
      rawAccountValue === null ||
      !contractStatus ||
      !claimTimeStatus ||
      loanAmount === null ||
      unpaidChargeAmount === null
    ) {
      return needsPolicyStateResult(result, item, [
        accountValueStateKey,
        "policy_effect_status_at_event",
        "policy_loan_and_interest_amount",
        "unpaid_policy_charge_amount",
        "claim_time_status",
      ]);
    }
    if (contractStatus !== "active") {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "contract_not_confirmed_active",
        policy_effect_status_at_event: contractStatus,
      };
    }

    const boundaryStatus = hasStateKey(
      "event_before_policy_maturity_status",
    )
      ? policyStateChoice(
          item,
          "event_before_policy_maturity_status",
        )
      : "before_maturity";
    if (
      hasStateKey("event_before_policy_maturity_status") &&
      !boundaryStatus
    ) {
      return needsPolicyStateResult(result, item, [
        "event_before_policy_maturity_status",
      ]);
    }
    if (boundaryStatus !== "before_maturity") {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason:
          "event_not_confirmed_before_policy_maturity",
        event_before_policy_maturity_status: boundaryStatus,
      };
    }

    let disabilityQualificationStatus = "";
    if (hasStateKey("total_disability_qualification_status")) {
      disabilityQualificationStatus = policyStateChoice(
        item,
        "total_disability_qualification_status",
      );
      if (!disabilityQualificationStatus) {
        return needsPolicyStateResult(result, item, [
          "total_disability_qualification_status",
        ]);
      }
      if (
        disabilityQualificationStatus !==
        "confirmed_first_level_item"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "total_disability_not_confirmed",
          total_disability_qualification_status:
            disabilityQualificationStatus,
        };
      }
    }

    const totalOffsets = safeIntegerSum(
      loanAmount,
      unpaidChargeAmount,
    );
    if (totalOffsets === null) {
      return { ...result, state: "amount_overflow" };
    }
    const accountValueOnlyResult = (
      formulaType,
      insuredAge = null,
    ) => {
      if (totalOffsets > rawAccountValue) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: rawAccountValue,
          policy_loan_and_interest_amount: loanAmount,
          unpaid_policy_charge_amount: unpaidChargeAmount,
        };
      }
      return {
        ...result,
        value: rawAccountValue - totalOffsets,
        reference_amount: rawAccountValue,
        state: "account_value_return",
        formula_type: formulaType,
        account_value: rawAccountValue,
        raw_account_value: rawAccountValue,
        adjusted_account_value: rawAccountValue,
        post_event_insurance_cost_refund_status: "not_applied",
        post_event_insurance_cost_refund_amount: 0,
        policy_loan_and_interest_amount: loanAmount,
        unpaid_policy_charge_amount: unpaidChargeAmount,
        gross_value_before_offsets: rawAccountValue,
        policy_effect_status_at_event: contractStatus,
        claim_time_status: claimTimeStatus,
        event_before_policy_maturity_status: boundaryStatus,
        policy_state_key: accountValueStateKey,
        insured_age_at_event: insuredAge,
        product_family: productFamily,
      };
    };
    if (claimTimeStatus === "time_barred") {
      return accountValueOnlyResult(
        "time_barred_account_value_return",
      );
    }

    const actualAge = hasStateKey("insured_age_at_event")
      ? policyStateInteger(item, "insured_age_at_event")
      : null;
    const actualAgeThreshold = Number(
      item?.version_characteristics
        ?.risk_amount_actual_age_threshold,
    );
    if (!Number.isSafeInteger(actualAgeThreshold)) {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "risk_amount_age_threshold_missing",
      };
    }
    if (
      hasStateKey("insured_age_at_event") &&
      actualAge === null
    ) {
      return needsPolicyStateResult(result, item, [
        "insured_age_at_event",
      ]);
    }
    const isMinorUnderAge15 =
      actualAgeThreshold === 15 &&
      actualAge !== null &&
      actualAge < 15;
    if (
      isMinorUnderAge15 &&
      normalizedEntry.id === "death-benefit"
    ) {
      return accountValueOnlyResult(
        "minor_account_value_return",
        actualAge,
      );
    }

    const exclusionStatus = policyStateChoice(
      item,
      "benefit_exclusion_status",
    );
    if (!exclusionStatus) {
      return needsPolicyStateResult(result, item, [
        "benefit_exclusion_status",
      ]);
    }
    if (exclusionStatus !== "none_confirmed") {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "benefit_exclusion_requires_review",
        benefit_exclusion_status: exclusionStatus,
      };
    }
    const refundStatus = policyStateChoice(
      item,
      "post_event_insurance_cost_refund_status",
    );
    if (!refundStatus) {
      return needsPolicyStateResult(result, item, [
        "post_event_insurance_cost_refund_status",
      ]);
    }
    const refundAmountRequired =
      refundStatus === "charged_after_event";
    const refundAmount = refundAmountRequired
      ? policyStateNonNegativeMoney(
          item,
          "post_event_insurance_cost_refund_amount",
        )
      : 0;
    if (refundAmount === null) {
      return needsPolicyStateResult(result, item, [
        "post_event_insurance_cost_refund_amount",
      ]);
    }
    const formulaAccountValue = safeIntegerSum(
      rawAccountValue,
      refundAmount,
    );
    if (formulaAccountValue === null) {
      return { ...result, state: "amount_overflow" };
    }

    const faceAmount = normalizeMoneyAmount(item?.face_amount);
    if (!faceAmount) {
      return { ...result, state: "needs_face_amount" };
    }
    let riskAmount = isMinorUnderAge15 ? 0 : null;
    let riskAmountSource = isMinorUnderAge15
      ? "minor_zero_risk"
      : policyStateChoice(item, "risk_amount_source");
    let riskCalculationActualAge = null;
    let riskCalculationInsuranceAge = null;
    let riskCalculationStage = "";
    let riskCalculationAccountValue = null;
    let riskCalculationNetPremiumAmount = null;
    let flexibleInsuranceAmount = null;
    let coefficient = null;
    let effectiveStatus = "";
    let ageAccuracyStatus = "";

    if (!isMinorUnderAge15 && !riskAmountSource) {
      return needsPolicyStateResult(result, item, [
        "risk_amount_source",
      ]);
    }
    if (riskAmountSource === "insurer_statement") {
      riskAmount = policyStateNonNegativeMoney(
        item,
        "insurer_confirmed_current_risk_amount",
      );
      if (riskAmount === null) {
        return needsPolicyStateResult(result, item, [
          "insurer_confirmed_current_risk_amount",
        ]);
      }
    } else if (riskAmountSource === "recalculate_from_history") {
      ageAccuracyStatus = policyStateChoice(
        item,
        "insured_age_accuracy_status",
      );
      if (!ageAccuracyStatus) {
        return needsPolicyStateResult(result, item, [
          "insured_age_accuracy_status",
        ]);
      }
      if (ageAccuracyStatus !== "confirmed_accurate") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "insured_age_error_requires_adjusted_risk_amount",
          required_fields: [
            "insurer_confirmed_current_risk_amount",
          ],
        };
      }
      riskCalculationActualAge = policyStateInteger(
        item,
        "risk_calculation_actual_age",
      );
      riskCalculationInsuranceAge = policyStateInteger(
        item,
        "risk_calculation_insurance_age",
      );
      riskCalculationStage = policyStateChoice(
        item,
        "risk_calculation_stage",
      );
      effectiveStatus = policyStateChoice(
        item,
        "risk_amount_effective_status",
      );
      if (
        riskCalculationActualAge === null ||
        riskCalculationInsuranceAge === null ||
        !riskCalculationStage ||
        !effectiveStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "risk_calculation_actual_age",
          "risk_calculation_insurance_age",
          "risk_calculation_stage",
          "risk_amount_effective_status",
        ]);
      }
      if (effectiveStatus !== "current_formula_effective") {
        riskAmount = policyStateNonNegativeMoney(
          item,
          "insurer_confirmed_current_risk_amount",
        );
        if (riskAmount === null) {
          return needsPolicyStateResult(result, item, [
            "insurer_confirmed_current_risk_amount",
          ]);
        }
      } else if (riskCalculationActualAge < actualAgeThreshold) {
        if (
          actualAgeThreshold === 15 &&
          actualAge !== null &&
          actualAge >= 15
        ) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "age15_risk_recalculation_history_missing",
          };
        }
        riskAmount = actualAgeThreshold === 15 ? 0 : faceAmount;
      } else if (
        [
          "before_second_premium",
          "age15_recalculation",
        ].includes(riskCalculationStage)
      ) {
        if (
          riskCalculationStage === "age15_recalculation" &&
          item?.version_characteristics
            ?.age15_recalculation_applies !== true
        ) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "age15_recalculation_not_in_this_version",
          };
        }
        riskAmount = faceAmount;
        flexibleInsuranceAmount = faceAmount;
      } else if (
        [
          "subsequent_regular_premium",
          "subsequent_nonregular_premium",
        ].includes(riskCalculationStage)
      ) {
        riskCalculationAccountValue =
          policyStateNonNegativeMoney(
            item,
            "risk_calculation_policy_account_value",
          );
        riskCalculationNetPremiumAmount =
          policyStateNonNegativeMoney(
            item,
            "risk_calculation_net_premium_amount",
          );
        if (
          riskCalculationAccountValue === null ||
          riskCalculationNetPremiumAmount === null
        ) {
          return needsPolicyStateResult(result, item, [
            "risk_calculation_policy_account_value",
            "risk_calculation_net_premium_amount",
          ]);
        }
        const coefficientSchedule =
          item?.version_characteristics
            ?.risk_coefficient_schedule;
        const bracket = Array.isArray(coefficientSchedule)
          ? coefficientSchedule.find(
              (candidate) =>
                riskCalculationInsuranceAge >=
                  Number(candidate?.min_insurance_age) &&
                riskCalculationInsuranceAge <=
                  Number(candidate?.max_insurance_age),
            )
          : null;
        coefficient = Number(bracket?.factor);
        if (
          !Number.isFinite(coefficient) ||
          coefficient <= 0 ||
          coefficient > 1
        ) {
          return {
            ...result,
            state: "outside_terms_formula_age_range",
            risk_calculation_insurance_age:
              riskCalculationInsuranceAge,
          };
        }
        const coefficientNumerator = Math.round(coefficient * 100);
        const coefficientBase = safeIntegerSum(
          riskCalculationAccountValue,
          riskCalculationNetPremiumAmount,
        );
        if (coefficientBase === null) {
          return { ...result, state: "amount_overflow" };
        }
        const exactFlexibleAmount = safeExactRatio(
          coefficientBase,
          coefficientNumerator,
        );
        if (exactFlexibleAmount.status === "overflow") {
          return { ...result, state: "amount_overflow" };
        }
        const flexibleDoesNotExceedFace =
          BigInt(coefficientBase) *
            BigInt(coefficientNumerator) <=
          BigInt(faceAmount) * 100n;
        if (exactFlexibleAmount.status === "fractional") {
          if (!flexibleDoesNotExceedFace) {
            return {
              ...result,
              state: "needs_insurer_confirmation",
              confirmation_reason:
                "fractional_policy_amount_rounding_undefined",
              coefficient,
              coefficient_base: coefficientBase,
              face_amount: faceAmount,
            };
          }
          riskAmount = faceAmount;
        } else if (exactFlexibleAmount.status === "exact") {
          flexibleInsuranceAmount = exactFlexibleAmount.value;
          riskAmount = Math.max(
            faceAmount,
            flexibleInsuranceAmount,
          );
        } else {
          return { ...result, state: "amount_overflow" };
        }
      } else {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "risk_calculation_stage_invalid",
          risk_calculation_stage: riskCalculationStage,
        };
      }
    }
    if (riskAmount === null) {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "risk_amount_source_invalid",
      };
    }

    let payableRiskAmount = riskAmount;
    let deathBenefitStatus = "";
    let funeralBenefitLimit = null;
    let funeralExcessRefundStatus = "";
    let funeralExcessRefundAmount = 0;
    if (normalizedEntry.id === "death-benefit") {
      deathBenefitStatus = policyStateChoice(
        item,
        "death_benefit_status",
      );
      if (!deathBenefitStatus) {
        return needsPolicyStateResult(result, item, [
          "death_benefit_status",
        ]);
      }
      if (deathBenefitStatus === "funeral_limited") {
        funeralBenefitLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (funeralBenefitLimit === null) {
          return needsPolicyStateResult(result, item, [
            "remaining_funeral_benefit_limit",
          ]);
        }
        payableRiskAmount = Math.min(
          riskAmount,
          funeralBenefitLimit,
        );
        if (payableRiskAmount < riskAmount) {
          funeralExcessRefundStatus = policyStateChoice(
            item,
            "funeral_excess_insurance_cost_refund_status",
          );
          if (!funeralExcessRefundStatus) {
            return needsPolicyStateResult(result, item, [
              "funeral_excess_insurance_cost_refund_status",
            ]);
          }
          if (funeralExcessRefundStatus === "unknown") {
            return {
              ...result,
              state: "needs_insurer_confirmation",
              confirmation_reason:
                "funeral_excess_insurance_cost_refund_unknown",
            };
          }
          if (funeralExcessRefundStatus === "confirmed_amount") {
            funeralExcessRefundAmount =
              policyStateNonNegativeMoney(
                item,
                "funeral_excess_insurance_cost_refund_amount",
              );
            if (funeralExcessRefundAmount === null) {
              return needsPolicyStateResult(result, item, [
                "funeral_excess_insurance_cost_refund_amount",
              ]);
            }
          }
        }
      }
    }
    const grossValueBeforeOffsets = safeIntegerSum(
      payableRiskAmount,
      formulaAccountValue,
      funeralExcessRefundAmount,
    );
    if (grossValueBeforeOffsets === null) {
      return { ...result, state: "amount_overflow" };
    }
    if (totalOffsets > grossValueBeforeOffsets) {
      return {
        ...result,
        state: "needs_insurer_confirmation",
        confirmation_reason: "offsets_exceed_gross_benefit",
        gross_value_before_offsets: grossValueBeforeOffsets,
        policy_loan_and_interest_amount: loanAmount,
        unpaid_policy_charge_amount: unpaidChargeAmount,
      };
    }
    const value = grossValueBeforeOffsets - totalOffsets;
    return {
      ...result,
      value,
      reference_amount: grossValueBeforeOffsets,
      state:
        normalizedEntry.id === "death-benefit"
          ? "death_or_funeral_amount"
          : "calculated",
      formula_type:
        deathBenefitStatus === "funeral_limited"
          ? "funeral_limited"
          : "risk_amount_plus_policy_account_value",
      risk_amount: riskAmount,
      risk_amount_source: riskAmountSource,
      payable_risk_amount: payableRiskAmount,
      flexible_insurance_amount: flexibleInsuranceAmount,
      face_amount: faceAmount,
      face_amount_label:
        String(item?.face_amount_label || "").trim() ||
        "保險金額",
      account_value: formulaAccountValue,
      raw_account_value: rawAccountValue,
      adjusted_account_value: formulaAccountValue,
      post_event_insurance_cost_refund_status: refundStatus,
      post_event_insurance_cost_refund_amount: refundAmount,
      funeral_excess_insurance_cost_refund_status:
        funeralExcessRefundStatus,
      funeral_excess_insurance_cost_refund_amount:
        funeralExcessRefundAmount,
      policy_loan_and_interest_amount: loanAmount,
      unpaid_policy_charge_amount: unpaidChargeAmount,
      gross_value_before_offsets: grossValueBeforeOffsets,
      policy_effect_status_at_event: contractStatus,
      claim_time_status: claimTimeStatus,
      benefit_exclusion_status: exclusionStatus,
      event_before_policy_maturity_status: boundaryStatus,
      total_disability_qualification_status:
        disabilityQualificationStatus,
      death_benefit_status: deathBenefitStatus,
      funeral_benefit_limit: funeralBenefitLimit,
      insured_age_at_event: actualAge,
      risk_calculation_actual_age: riskCalculationActualAge,
      risk_calculation_insurance_age:
        riskCalculationInsuranceAge,
      insured_age_accuracy_status: ageAccuracyStatus,
      risk_calculation_stage: riskCalculationStage,
      risk_calculation_policy_account_value:
        riskCalculationAccountValue,
      risk_calculation_net_premium_amount:
        riskCalculationNetPremiumAmount,
      risk_amount_effective_status: effectiveStatus,
      risk_coefficient: coefficient,
      policy_state_key: accountValueStateKey,
      semantic_phase:
        item?.version_characteristics?.semantic_phase,
      product_family: productFamily,
    };
  }

  function coverageValue(entry, selection) {
    const normalizedEntry = normalizeCoverageEntry(entry, 0);
    const item = selection || {};
    const amount = normalizedEntry.amount;
    const declaredMaximumUnits = Number(
      item?.version_characteristics?.maximum_units_per_insured,
    );
    const maximumUnits =
      Number.isSafeInteger(declaredMaximumUnits) && declaredMaximumUnits > 0
        ? Math.min(declaredMaximumUnits, MAX_UNIT_COUNT)
        : MAX_UNIT_COUNT;
    const units = normalizeInteger(
      normalizedEntry.unit_key ? item.unit_counts?.[normalizedEntry.unit_key] : item.unit_count,
      maximumUnits,
    );
    const faceAmount = normalizeMoneyAmount(item.face_amount);
    const accountValue = selectedAccountValue(item);
    const policyFieldKeys = policyStateFieldKeysForEntry(
      normalizedEntry,
      item,
    );
    const currencyStateKey = normalizedEntry.currency_state_key;
    const currencyLabel = currencyStateKey ? policyStateText(item, currencyStateKey) : "元";
    const result = {
      value: null,
      reference_amount: amount,
      state: amount ? "reference_only" : "missing_amount",
      calculation_basis: normalizedEntry.calculation_basis,
      amount_role: normalizedEntry.amount_role,
      result_kind: normalizedEntry.result_kind,
      amount_stage: normalizedEntry.amount_stage,
      limit_scope: normalizedEntry.limit_scope,
      required_fields: policyFieldKeys,
      currency_label: currencyLabel,
    };
    if (currencyStateKey && !currencyLabel) {
      return needsPolicyStateResult(result, item, policyFieldKeys);
    }
    const ineligibleResult = eligibilityResult(
      normalizedEntry,
      item,
      result,
    );
    if (ineligibleResult) return ineligibleResult;
    const conditionResult = entryConditionResult(
      normalizedEntry,
      item,
      result,
    );
    if (conditionResult) return conditionResult;
    if (
      normalizedEntry.calculation_basis ===
      "death_or_funeral_greater_of_per_unit_floor_and_paid_premium_net"
    ) {
      if (!amount || !units) {
        return { ...result, state: "needs_unit_count" };
      }
      const paidPremiumTotal = policyStateMoney(
        item,
        "paid_premium_total",
      );
      const priorBenefitPaid = policyStateNonNegativeMoney(
        item,
        "aia_tongtong_prior_cap_benefit_paid_amount",
      );
      const deathStatus = policyStateChoice(
        item,
        "death_benefit_status",
      );
      if (
        paidPremiumTotal === null ||
        priorBenefitPaid === null ||
        !deathStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "paid_premium_total",
          "aia_tongtong_prior_cap_benefit_paid_amount",
          "death_benefit_status",
        ]);
      }
      const unitFloor = safeIntegerProduct(amount, units);
      if (!Number.isSafeInteger(unitFloor)) {
        return { ...result, state: "amount_overflow" };
      }
      const premiumNet = Math.max(
        0,
        paidPremiumTotal - priorBenefitPaid,
      );
      const grossValue = Math.max(unitFloor, premiumNet);
      if (
        !Number.isSafeInteger(grossValue) ||
        grossValue > MAX_MONEY_AMOUNT
      ) {
        return { ...result, state: "amount_overflow" };
      }
      if (deathStatus === "funeral_limited") {
        const remainingLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (remainingLimit === null) {
          return needsPolicyStateResult(result, item, [
            "remaining_funeral_benefit_limit",
          ]);
        }
        return {
          ...result,
          value: Math.min(grossValue, remainingLimit),
          reference_amount: grossValue,
          state: "death_or_funeral_amount",
          formula_type:
            "greater_of_per_unit_floor_and_paid_premium_net_funeral_cap",
          unit_floor_amount: unitFloor,
          paid_premium_net_amount: premiumNet,
          gross_value_before_funeral_cap: grossValue,
          protected_amount: grossValue,
          capped_protected_amount: Math.min(
            grossValue,
            remainingLimit,
          ),
          funeral_benefit_limit: remainingLimit,
        };
      }
      return {
        ...result,
        value: grossValue,
        reference_amount: grossValue,
        state: "death_or_funeral_amount",
        formula_type:
          "greater_of_per_unit_floor_and_paid_premium_net",
        unit_floor_amount: unitFloor,
        paid_premium_net_amount: premiumNet,
        gross_value_before_funeral_cap: grossValue,
        protected_amount: grossValue,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "policy_year_tiered_premium_or_face_amount"
    ) {
      const policyYear = policyStateInteger(item, "policy_year");
      const cutoff = normalizedEntry.policy_year_cutoff;
      if (policyYear === null || !cutoff) {
        return needsPolicyStateResult(
          result,
          item,
          ["policy_year"],
        );
      }
      if (policyYear <= cutoff) {
        const requiredFields = [
          "policy_year",
          "standard_annual_premium_amount",
          "premium_payment_period_years",
        ];
        const annualPremiumTotal = annualPremiumTotalAmount(
          item,
          policyYear,
        );
        if (!annualPremiumTotal) {
          return needsPolicyStateResult(
            result,
            item,
            requiredFields,
          );
        }
        return {
          ...result,
          value: annualPremiumTotal,
          reference_amount: annualPremiumTotal,
          state: "calculated",
          formula_type: "early_policy_year_annual_premium_total",
          policy_year: policyYear,
          policy_year_cutoff: cutoff,
          annual_premium_total: annualPremiumTotal,
        };
      }
      if (!faceAmount) {
        return { ...result, state: "needs_face_amount" };
      }
      if (!normalizedEntry.rate) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "needs_rate_table",
        };
      }
      const value = Math.trunc(faceAmount * normalizedEntry.rate);
      return Number.isSafeInteger(value) && value > 0
        ? {
            ...result,
            value,
            reference_amount: faceAmount,
            state: "calculated",
            formula_type: "later_policy_year_face_amount_rate",
            policy_year: policyYear,
            policy_year_cutoff: cutoff,
            face_amount: faceAmount,
            rate: normalizedEntry.rate,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      [
        "policy_year_greater_of_face_reserve_premium_with_offset",
        "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset",
      ].includes(normalizedEntry.calculation_basis)
    ) {
      const requiredFields = [
        "policy_year",
        "standard_annual_premium_amount",
        "premium_payment_period_years",
        "policy_reserve_value",
        "prior_long_term_care_benefit_amount",
      ];
      const policyYear = policyStateInteger(item, "policy_year");
      const reserveValue = policyStateNonNegativeMoney(
        item,
        "policy_reserve_value",
      );
      const priorLongTermCareAmount = policyStateNonNegativeMoney(
        item,
        "prior_long_term_care_benefit_amount",
      );
      const annualPremiumTotal = annualPremiumTotalAmount(
        item,
        policyYear,
      );
      const cutoff = normalizedEntry.policy_year_cutoff;
      if (
        policyYear === null ||
        reserveValue === null ||
        priorLongTermCareAmount === null ||
        !annualPremiumTotal ||
        !cutoff
      ) {
        return needsPolicyStateResult(
          result,
          item,
          requiredFields,
        );
      }
      if (!normalizedEntry.rate) {
        return {
          ...result,
          reference_amount: annualPremiumTotal,
          state: "needs_rate_table",
        };
      }
      const premiumCandidate = Math.trunc(
        annualPremiumTotal * normalizedEntry.rate,
      );
      const candidates =
        policyYear <= cutoff
          ? [
              {
                key: "annual_premium_total_times_rate",
                value: premiumCandidate,
                base_value: annualPremiumTotal,
                rate: normalizedEntry.rate,
              },
              {
                key: "policy_reserve_value",
                value: reserveValue,
              },
            ]
          : [
              {
                key: "face_amount_minus_prior_long_term_care",
                value: faceAmount
                  ? Math.max(
                      faceAmount - priorLongTermCareAmount,
                      0,
                    )
                  : null,
              },
              {
                key: "policy_reserve_value",
                value: reserveValue,
              },
              {
                key: "annual_premium_total_times_rate_minus_prior_long_term_care",
                value: Math.max(
                  premiumCandidate - priorLongTermCareAmount,
                  0,
                ),
                base_value: annualPremiumTotal,
                rate: normalizedEntry.rate,
              },
            ];
      if (
        policyYear > cutoff &&
        (!faceAmount || candidates.some((candidate) => candidate.value === null))
      ) {
        return { ...result, state: "needs_face_amount" };
      }
      const grossValue = Math.max(
        ...candidates.map((candidate) => candidate.value),
      );
      if (
        !Number.isSafeInteger(grossValue) ||
        grossValue > MAX_MONEY_AMOUNT
      ) {
        return { ...result, state: "amount_overflow" };
      }
      const commonResult = {
        ...result,
        value: grossValue,
        reference_amount: grossValue,
        state: "greater_of",
        formula_type:
          policyYear <= cutoff
            ? "early_policy_year_greater_of"
            : "later_policy_year_greater_of_with_offset",
        policy_year: policyYear,
        policy_year_cutoff: cutoff,
        annual_premium_total: annualPremiumTotal,
        prior_long_term_care_benefit_amount:
          priorLongTermCareAmount,
        candidates,
      };
      if (
        normalizedEntry.calculation_basis !==
        "death_or_funeral_policy_year_greater_of_face_reserve_premium_with_offset"
      ) {
        return commonResult;
      }
      const deathStatus = policyStateChoice(
        item,
        "death_benefit_status",
      );
      if (!deathStatus) {
        return needsPolicyStateResult(result, item, [
          "death_benefit_status",
        ]);
      }
      if (deathStatus !== "funeral_limited") {
        return {
          ...commonResult,
          state: "death_or_funeral_amount",
          gross_value_before_funeral_cap: grossValue,
          protected_amount: grossValue,
        };
      }
      const remainingLimit = policyStateNonNegativeMoney(
        item,
        "remaining_funeral_benefit_limit",
      );
      if (remainingLimit === null) {
        return needsPolicyStateResult(result, item, [
          "remaining_funeral_benefit_limit",
        ]);
      }
      const cappedValue = Math.min(grossValue, remainingLimit);
      return {
        ...commonResult,
        value: cappedValue,
        reference_amount: grossValue,
        state: "death_or_funeral_amount",
        gross_value_before_funeral_cap: grossValue,
        protected_amount: grossValue,
        capped_protected_amount: cappedValue,
        funeral_benefit_limit: remainingLimit,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "maturity_greater_of_face_and_premium_with_offset"
    ) {
      const requiredFields = [
        "standard_annual_premium_amount",
        "premium_payment_period_years",
        "prior_long_term_care_benefit_amount",
      ];
      const annualPremiumTotal = annualPremiumTotalAmount(item);
      const priorLongTermCareAmount = policyStateNonNegativeMoney(
        item,
        "prior_long_term_care_benefit_amount",
      );
      if (
        !annualPremiumTotal ||
        priorLongTermCareAmount === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          requiredFields,
        );
      }
      if (!faceAmount) {
        return { ...result, state: "needs_face_amount" };
      }
      if (!normalizedEntry.rate) {
        return {
          ...result,
          reference_amount: annualPremiumTotal,
          state: "needs_rate_table",
        };
      }
      const candidates = [
        {
          key: "face_amount_minus_prior_long_term_care",
          value: Math.max(
            faceAmount - priorLongTermCareAmount,
            0,
          ),
        },
        {
          key: "annual_premium_total_times_rate_minus_prior_long_term_care",
          value: Math.max(
            Math.trunc(
              annualPremiumTotal * normalizedEntry.rate,
            ) - priorLongTermCareAmount,
            0,
          ),
          base_value: annualPremiumTotal,
          rate: normalizedEntry.rate,
        },
      ];
      const value = Math.max(
        ...candidates.map((candidate) => candidate.value),
      );
      return Number.isSafeInteger(value) &&
        value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: value,
            state: "greater_of",
            formula_type: "maturity_greater_of_with_offset",
            annual_premium_total: annualPremiumTotal,
            prior_long_term_care_benefit_amount:
              priorLongTermCareAmount,
            candidates,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "plan_schedule_lookup") {
      const options = normalizePlanOptions(item);
      const selectedPlan = options.find(
        (option) => option.value === item.plan_name || option.label === item.plan_name,
      );
      if (!selectedPlan) return { ...result, state: "needs_plan" };
    }
    if (normalizedEntry.calculation_basis === "annuity_face_amount_schedule") {
      if (!faceAmount) return { ...result, state: "needs_face_amount" };
      if (!normalizedEntry.rate) {
        return { ...result, reference_amount: faceAmount, state: "needs_rate_table" };
      }
      const paymentPattern = normalizedEntry.annuity_payment_pattern;
      const paymentYear =
        paymentPattern === "increasing"
          ? policyStateInteger(item, "annuity_payment_year")
          : 1;
      if (paymentPattern === "increasing" && paymentYear === null) {
        return needsPolicyStateResult(result, item, ["annuity_payment_year"]);
      }
      const guaranteeYears = normalizedEntry.annuity_guarantee_years || 0;
      const growthRate =
        paymentPattern === "increasing" ? normalizedEntry.annuity_growth_rate : 0;
      if (
        !["level", "increasing"].includes(paymentPattern) ||
        (paymentPattern === "increasing" && (!growthRate || !guaranteeYears))
      ) {
        return { ...result, reference_amount: faceAmount, state: "needs_rate_table" };
      }
      const growthYear =
        paymentPattern === "increasing"
          ? Math.min(Math.max(paymentYear - 1, 0), guaranteeYears)
          : 0;
      const growthMultiplier = 1 + growthRate * growthYear;
      const value = Math.trunc(faceAmount * normalizedEntry.rate * growthMultiplier);
      return value > 0 && Number.isSafeInteger(value)
        ? {
            ...result,
            value,
            reference_amount: faceAmount,
            state: "calculated",
            annuity_payment_pattern: paymentPattern,
            annuity_payment_year: paymentYear,
            annuity_guarantee_years: guaranteeYears,
            annuity_growth_rate: growthRate,
            annuity_frequency_rate: normalizedEntry.rate,
            annuity_growth_multiplier: growthMultiplier,
          }
        : { ...result, reference_amount: faceAmount, state: "amount_overflow" };
    }
    if (
      normalizedEntry.calculation_basis ===
      "single_premium_minus_paid_annuity_total"
    ) {
      const requiredFields = [
        "single_premium_amount",
        "annuity_paid_total_amount",
      ];
      const singlePremiumAmount = policyStateMoney(
        item,
        "single_premium_amount",
      );
      const paidAnnuityTotal = policyStateNonNegativeMoney(
        item,
        "annuity_paid_total_amount",
      );
      if (
        singlePremiumAmount === null ||
        paidAnnuityTotal === null
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      const value = Math.max(
        singlePremiumAmount - paidAnnuityTotal,
        0,
      );
      return Number.isSafeInteger(value) &&
        value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: singlePremiumAmount,
            state: "calculated_annuity_balance",
            single_premium_amount: singlePremiumAmount,
            paid_annuity_total: paidAnnuityTotal,
          }
        : {
            ...result,
            reference_amount: singlePremiumAmount,
            state: "amount_overflow",
          };
    }
    if (
      normalizedEntry.calculation_basis ===
      "reserve_minus_policy_loan_and_interest"
    ) {
      const requiredFields = [
        "policy_reserve_value",
        "policy_loan_and_interest_amount",
      ];
      const reserveValue = policyStateNonNegativeMoney(
        item,
        "policy_reserve_value",
      );
      const loanAndInterest = policyStateNonNegativeMoney(
        item,
        "policy_loan_and_interest_amount",
      );
      if (reserveValue === null || loanAndInterest === null) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      const value = Math.max(reserveValue - loanAndInterest, 0);
      return Number.isSafeInteger(value) && value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: reserveValue,
            state: "calculated",
            formula_type: "reserve_minus_policy_loan_and_interest",
            policy_reserve_value: reserveValue,
            policy_loan_and_interest_amount: loanAndInterest,
          }
        : {
            ...result,
            reference_amount: reserveValue,
            state: "amount_overflow",
          };
    }
    if (normalizedEntry.calculation_basis === "account_value") {
      return accountValue
        ? {
            ...result,
            value: accountValue,
            reference_amount: accountValue,
            state: "account_value_return",
            policy_state_key: "policy_account_value",
          }
        : { ...result, state: "needs_account_value", required_fields: ["policy_account_value"] };
    }
    if (normalizedEntry.calculation_basis === "policy_value_component") {
      const policyValueComponent = policyStateMoney(item, "policy_value_component");
      const requiresTwdConfirmation =
        normalizedEntry.policy_state_keys.includes(
          "policy_values_converted_to_twd",
        );
      const twdConfirmed = requiresTwdConfirmation
        ? policyStateBoolean(item, "policy_values_converted_to_twd")
        : true;
      return policyValueComponent && twdConfirmed
        ? {
            ...result,
            value: policyValueComponent,
            reference_amount: policyValueComponent,
            state: "policy_state_value",
            policy_state_key: "policy_value_component",
          }
        : needsPolicyStateResult(result, item, [
            "policy_value_component",
            ...(requiresTwdConfirmation
              ? ["policy_values_converted_to_twd"]
              : []),
          ]);
    }
    if (normalizedEntry.calculation_basis === "maturity_policy_account_value") {
      const maturityAccountValueStateKey =
        normalizedEntry.policy_state_keys.find(
          (key) =>
            key.includes("maturity") &&
            key.includes("policy_account_value"),
        ) || "maturity_policy_account_value";
      const maturityAccountValue = policyStateNonNegativeMoney(
        item,
        maturityAccountValueStateKey,
      );
      const twdConfirmed = policyStateBoolean(
        item,
        "policy_values_converted_to_twd",
      );
      const requiresTwdConfirmation =
        normalizedEntry.policy_state_keys.includes(
          "policy_values_converted_to_twd",
        );
      const appliesLoanOffset =
        normalizedEntry.policy_state_keys.includes(
          "policy_loan_and_interest_amount",
        );
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        );
      const appliesMaturityInterest =
        normalizedEntry.policy_state_keys.includes(
          "maturity_interest_amount",
        );
      const appliesRemittanceFee =
        normalizedEntry.policy_state_keys.includes(
          "remittance_fee_amount",
        );
      const requiresContractStatus =
        normalizedEntry.policy_state_keys.includes(
          "policy_effect_status_at_event",
        );
      const contractStatus = requiresContractStatus
        ? policyStateChoice(item, "policy_effect_status_at_event")
        : "active";
      if (requiresContractStatus && !contractStatus) {
        return needsPolicyStateResult(result, item, [
          "policy_effect_status_at_event",
        ]);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      const policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(
            item,
            "unpaid_policy_charge_amount",
          )
        : 0;
      const maturityInterestAmount = appliesMaturityInterest
        ? policyStateNonNegativeMoney(
            item,
            "maturity_interest_amount",
          )
        : 0;
      const remittanceFeeAmount = appliesRemittanceFee
        ? policyStateNonNegativeMoney(item, "remittance_fee_amount")
        : 0;
      if (
        maturityAccountValue === null ||
        (requiresTwdConfirmation && !twdConfirmed) ||
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null ||
        maturityInterestAmount === null ||
        remittanceFeeAmount === null
      ) {
        return needsPolicyStateResult(result, item, [
          maturityAccountValueStateKey,
          ...(requiresTwdConfirmation
            ? ["policy_values_converted_to_twd"]
            : []),
          ...(appliesLoanOffset
            ? ["policy_loan_and_interest_amount"]
            : []),
          ...(appliesPolicyChargeOffset
            ? ["unpaid_policy_charge_amount"]
            : []),
          ...(appliesMaturityInterest
            ? ["maturity_interest_amount"]
            : []),
          ...(appliesRemittanceFee
            ? ["remittance_fee_amount"]
            : []),
        ]);
      }
      const grossValueBeforeOffsets = safeIntegerSum(
        maturityAccountValue,
        maturityInterestAmount,
      );
      const totalOffsets = safeIntegerSum(
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
        remittanceFeeAmount,
      );
      if (grossValueBeforeOffsets === null || totalOffsets === null) {
        return { ...result, state: "amount_overflow" };
      }
      if (totalOffsets > grossValueBeforeOffsets) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeOffsets,
          policy_loan_and_interest_amount: policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
          remittance_fee_amount: remittanceFeeAmount,
        };
      }
      const value = grossValueBeforeOffsets - totalOffsets;
      return Number.isSafeInteger(value)
        ? {
            ...result,
            value,
            reference_amount: maturityAccountValue,
            state: "conditional_amount",
            policy_state_key: maturityAccountValueStateKey,
            gross_value_before_loan_offset: grossValueBeforeOffsets,
            gross_value_before_offsets: grossValueBeforeOffsets,
            maturity_policy_account_value: maturityAccountValue,
            [maturityAccountValueStateKey]: maturityAccountValue,
            maturity_interest_amount: maturityInterestAmount,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
            remittance_fee_amount: remittanceFeeAmount,
            policy_effect_status_at_event: contractStatus,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      normalizedEntry.calculation_basis ===
      "protected_amount_plus_policy_account_value"
    ) {
      if (!faceAmount) return { ...result, state: "needs_face_amount" };
      const contractStatus = policyStateChoice(
        item,
        "policy_effect_status_at_event",
      );
      if (!contractStatus) {
        return needsPolicyStateResult(result, item, [
          "policy_effect_status_at_event",
        ]);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      const requiresClaimTimeStatus =
        normalizedEntry.policy_state_keys.includes("claim_time_status");
      const requiresExclusionStatus =
        normalizedEntry.policy_state_keys.includes(
          "benefit_exclusion_status",
        );
      const requiresAgeAccuracyStatus =
        normalizedEntry.policy_state_keys.includes(
          "insured_age_accuracy_status",
        );
      const requiresDisabilityQualification =
        normalizedEntry.policy_state_keys.includes(
          "total_disability_qualification_status",
        );
      const claimTimeStatus = requiresClaimTimeStatus
        ? policyStateChoice(item, "claim_time_status")
        : "within_claim_period";
      const exclusionStatus = requiresExclusionStatus
        ? policyStateChoice(item, "benefit_exclusion_status")
        : "none_confirmed";
      if (
        requiresClaimTimeStatus &&
        !claimTimeStatus &&
        exclusionStatus !== "confirmed_applies"
      ) {
        return needsPolicyStateResult(result, item, ["claim_time_status"]);
      }
      const benefitAccountValueStateKey =
        normalizedEntry.policy_state_keys.find(
          (key) =>
            key.includes("benefit_valuation") &&
            key.includes("policy_account_value"),
        ) || "benefit_valuation_policy_account_value";
      const benefitAccountValue = policyStateNonNegativeMoney(
        item,
        benefitAccountValueStateKey,
      );
      const twdConfirmationRequired =
        normalizedEntry.policy_state_keys.includes(
          "policy_values_converted_to_twd",
        );
      const twdConfirmed = twdConfirmationRequired
        ? policyStateBoolean(item, "policy_values_converted_to_twd")
        : true;
      const allocationRequired = normalizedEntry.policy_state_keys.includes(
        "investment_allocation_status",
      );
      const allocationStatus = allocationRequired
        ? policyStateChoice(item, "investment_allocation_status")
        : "allocated";
      const appliesLoanOffset = normalizedEntry.policy_state_keys.includes(
        "policy_loan_and_interest_amount",
      );
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        );
      const postEventInsuranceCostStateKey =
        normalizedEntry.policy_state_keys.includes(
          "post_event_insurance_cost_refund_amount",
        )
          ? "post_event_insurance_cost_refund_amount"
          : normalizedEntry.policy_state_keys.includes(
                "unexpired_premium_refund_amount",
              )
            ? "unexpired_premium_refund_amount"
            : "";
      const includesPostEventInsuranceCostRefund =
        Boolean(postEventInsuranceCostStateKey);
      const policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(
            item,
            "unpaid_policy_charge_amount",
          )
        : 0;
      const postEventInsuranceCostRefundAmount =
        includesPostEventInsuranceCostRefund
          ? policyStateNonNegativeMoney(
              item,
              postEventInsuranceCostStateKey,
            )
          : 0;
      const pendingPremiumAmount =
        allocationStatus === "awaiting_allocation"
          ? policyStateNonNegativeMoney(
              item,
              "unallocated_net_premium_amount",
            )
          : 0;
      const requiredFields = [
        benefitAccountValueStateKey,
        ...(twdConfirmationRequired
          ? ["policy_values_converted_to_twd"]
          : []),
        ...(allocationRequired ? ["investment_allocation_status"] : []),
        ...(allocationStatus === "awaiting_allocation"
          ? ["unallocated_net_premium_amount"]
          : []),
        ...(includesPostEventInsuranceCostRefund
          ? [postEventInsuranceCostStateKey]
          : []),
        ...(appliesLoanOffset
          ? ["policy_loan_and_interest_amount"]
          : []),
        ...(appliesPolicyChargeOffset
          ? ["unpaid_policy_charge_amount"]
          : []),
      ];
      if (
        benefitAccountValue === null ||
        !twdConfirmed ||
        !allocationStatus ||
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null ||
        postEventInsuranceCostRefundAmount === null ||
        pendingPremiumAmount === null
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }

      const accountValueReturn = (
        formulaType,
        {
          include_unallocated_net_premium = false,
          ...extra
        } = {},
      ) => {
        const grossAccountValueReturn = safeIntegerSum(
          benefitAccountValue,
          include_unallocated_net_premium ? pendingPremiumAmount : 0,
        );
        const returnOffsets = safeIntegerSum(
          policyLoanAndInterestAmount,
          unpaidPolicyChargeAmount,
        );
        if (
          grossAccountValueReturn === null ||
          returnOffsets === null
        ) {
          return { ...result, state: "amount_overflow" };
        }
        if (returnOffsets > grossAccountValueReturn) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason: "offsets_exceed_account_value_return",
            benefit_valuation_policy_account_value: benefitAccountValue,
            unallocated_net_premium_amount:
              include_unallocated_net_premium
                ? pendingPremiumAmount
                : 0,
            policy_loan_and_interest_amount: policyLoanAndInterestAmount,
            unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
            ...extra,
          };
        }
        return {
          ...result,
          value: grossAccountValueReturn - returnOffsets,
          reference_amount: grossAccountValueReturn,
          state: "account_value_return",
          formula_type: formulaType,
          benefit_valuation_policy_account_value: benefitAccountValue,
          [benefitAccountValueStateKey]: benefitAccountValue,
          unallocated_net_premium_amount:
            include_unallocated_net_premium
              ? pendingPremiumAmount
              : 0,
          policy_loan_and_interest_amount: policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
          gross_value_before_offsets: grossAccountValueReturn,
          policy_effect_status_at_event: contractStatus,
          policy_state_key: benefitAccountValueStateKey,
          ...extra,
        };
      };
      if (claimTimeStatus === "time_barred") {
        if (
          item?.version_characteristics
            ?.claim_time_bar_account_value_return !== true
        ) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "claim_time_bar_return_not_stated",
            claim_time_status: claimTimeStatus,
          };
        }
        return accountValueReturn("claim_time_barred_account_value_return", {
          claim_time_status: claimTimeStatus,
        });
      }
      if (requiresExclusionStatus && !exclusionStatus) {
        return needsPolicyStateResult(result, item, [
          "benefit_exclusion_status",
        ]);
      }
      if (exclusionStatus === "confirmed_applies") {
        return accountValueReturn("exclusion_account_value_return", {
          include_unallocated_net_premium:
            item?.version_characteristics
              ?.unallocated_net_premium_return_on_exclusion === true,
          claim_time_status: claimTimeStatus,
          benefit_exclusion_status: exclusionStatus,
        });
      }
      if (exclusionStatus !== "none_confirmed") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "benefit_exclusion_may_apply",
          claim_time_status: claimTimeStatus,
          benefit_exclusion_status: exclusionStatus,
        };
      }
      const ageAccuracyStatus = requiresAgeAccuracyStatus
        ? policyStateChoice(item, "insured_age_accuracy_status")
        : "confirmed_accurate";
      if (requiresAgeAccuracyStatus && !ageAccuracyStatus) {
        return needsPolicyStateResult(result, item, [
          "insured_age_accuracy_status",
        ]);
      }
      if (ageAccuracyStatus !== "confirmed_accurate") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "insured_age_not_confirmed_accurate",
          insured_age_accuracy_status: ageAccuracyStatus,
        };
      }
      const disabilityQualificationStatus =
        requiresDisabilityQualification
          ? policyStateChoice(
              item,
              "total_disability_qualification_status",
            )
          : "confirmed_first_level_item";
      if (
        requiresDisabilityQualification &&
        !disabilityQualificationStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "total_disability_qualification_status",
        ]);
      }
      if (
        requiresDisabilityQualification &&
        disabilityQualificationStatus !== "confirmed_first_level_item"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "total_disability_not_confirmed",
          total_disability_qualification_status:
            disabilityQualificationStatus,
        };
      }

      const minorReturnAge = normalizedEntry.minor_account_value_return_age;
      const insuredAge = minorReturnAge
        ? policyStateInteger(item, "insured_age_at_event")
        : null;
      if (minorReturnAge && insuredAge === null) {
        return needsPolicyStateResult(result, item, [
          ...requiredFields,
          "insured_age_at_event",
        ]);
      }
      const minorAccountValueReturn =
        Boolean(minorReturnAge) && insuredAge < minorReturnAge;
      const includedPendingPremiumAmount =
        minorAccountValueReturn &&
        normalizedEntry.minor_unallocated_net_premium_return === false
          ? 0
          : pendingPremiumAmount;
      let protectedAmount = minorAccountValueReturn ? 0 : faceAmount;
      let remainingFuneralLimit = null;
      const deathStatusRequired =
        !minorAccountValueReturn &&
        normalizedEntry.policy_state_keys.includes(
          "death_benefit_status",
        );
      const deathStatus = deathStatusRequired
        ? policyStateChoice(item, "death_benefit_status")
        : "";
      if (deathStatusRequired && !deathStatus) {
        return needsPolicyStateResult(result, item, [
          ...requiredFields,
          "death_benefit_status",
        ]);
      }
      if (!minorAccountValueReturn && deathStatus === "funeral_limited") {
        remainingFuneralLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (remainingFuneralLimit === null) {
          return needsPolicyStateResult(result, item, [
            ...requiredFields,
            "death_benefit_status",
            "remaining_funeral_benefit_limit",
          ]);
        }
        protectedAmount = Math.min(protectedAmount, remainingFuneralLimit);
      }
      const requiresFuneralExcessRefund =
        normalizedEntry.policy_state_keys.includes(
          "funeral_excess_insurance_cost_refund_status",
        );
      let funeralExcessRefundStatus = "";
      let funeralExcessRefundAmount = 0;
      if (
        requiresFuneralExcessRefund &&
        deathStatus === "funeral_limited" &&
        protectedAmount < faceAmount
      ) {
        funeralExcessRefundStatus = policyStateChoice(
          item,
          "funeral_excess_insurance_cost_refund_status",
        );
        if (!funeralExcessRefundStatus) {
          return needsPolicyStateResult(result, item, [
            "funeral_excess_insurance_cost_refund_status",
          ]);
        }
        if (funeralExcessRefundStatus === "unknown") {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason:
              "funeral_excess_insurance_cost_refund_unknown",
          };
        }
        if (funeralExcessRefundStatus === "confirmed_amount") {
          funeralExcessRefundAmount = policyStateNonNegativeMoney(
            item,
            "funeral_excess_insurance_cost_refund_amount",
          );
          if (funeralExcessRefundAmount === null) {
            return needsPolicyStateResult(result, item, [
              "funeral_excess_insurance_cost_refund_amount",
            ]);
          }
        }
      }
      const grossValueBeforeOffsets = safeIntegerSum(
        protectedAmount,
        benefitAccountValue,
        includedPendingPremiumAmount,
        postEventInsuranceCostRefundAmount,
        funeralExcessRefundAmount,
      );
      const totalOffsets = safeIntegerSum(
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
      );
      if (grossValueBeforeOffsets === null || totalOffsets === null) {
        return { ...result, state: "amount_overflow" };
      }
      if (totalOffsets > grossValueBeforeOffsets) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeOffsets,
          policy_loan_and_interest_amount: policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        };
      }
      const value = grossValueBeforeOffsets - totalOffsets;
      return {
        ...result,
        value,
        reference_amount: grossValueBeforeOffsets,
        state: minorAccountValueReturn
          ? "account_value_return"
          : deathStatusRequired
            ? "death_or_funeral_amount"
            : "calculated",
        formula_type: minorAccountValueReturn
          ? "minor_account_value_return"
          : deathStatus === "funeral_limited"
            ? "funeral_cap_plus_account_value"
            : "protected_amount_plus_policy_account_value",
        product_family:
          item?.version_characteristics?.product_family || "",
        semantic_phase:
          item?.version_characteristics?.semantic_phase || "",
        face_amount: faceAmount,
        protected_amount: protectedAmount,
        benefit_valuation_policy_account_value: benefitAccountValue,
        [benefitAccountValueStateKey]: benefitAccountValue,
        unallocated_net_premium_amount:
          includedPendingPremiumAmount,
        unexpired_premium_refund_amount:
          postEventInsuranceCostRefundAmount,
        post_event_insurance_cost_refund_amount:
          postEventInsuranceCostStateKey ===
          "post_event_insurance_cost_refund_amount"
            ? postEventInsuranceCostRefundAmount
            : 0,
        investment_allocation_status: allocationStatus,
        policy_loan_and_interest_amount: policyLoanAndInterestAmount,
        unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        gross_value_before_offsets: grossValueBeforeOffsets,
        gross_value_before_funeral_cap: safeIntegerSum(
          faceAmount,
          benefitAccountValue,
          includedPendingPremiumAmount,
          postEventInsuranceCostRefundAmount,
        ),
        remaining_funeral_benefit_limit: remainingFuneralLimit,
        funeral_excess_insurance_cost_refund_status:
          funeralExcessRefundStatus,
        funeral_excess_insurance_cost_refund_amount:
          funeralExcessRefundAmount,
        insured_age_at_event: insuredAge,
        minor_account_value_return_age: minorReturnAge,
        policy_effect_status_at_event: contractStatus,
        claim_time_status: claimTimeStatus,
        benefit_exclusion_status: exclusionStatus,
        insured_age_accuracy_status: ageAccuracyStatus,
        total_disability_qualification_status:
          requiresDisabilityQualification
            ? disabilityQualificationStatus
            : undefined,
        policy_state_key: benefitAccountValueStateKey,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "net_premium_factor_plus_additional_premium"
    ) {
      const contractStatus = policyStateChoice(
        item,
        "policy_effect_status_at_event",
      );
      const primaryPremium = policyStateNonNegativeMoney(
        item,
        "net_primary_premium_amount",
      );
      const includesAdditionalPremium =
        normalizedEntry.policy_state_keys.includes(
          "net_additional_premium_amount",
        );
      const additionalPremium = includesAdditionalPremium
        ? policyStateNonNegativeMoney(
            item,
            "net_additional_premium_amount",
          )
        : 0;
      const appliesLoanOffset = normalizedEntry.policy_state_keys.includes(
        "policy_loan_and_interest_amount",
      );
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        );
      const policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(
            item,
            "unpaid_policy_charge_amount",
          )
        : 0;
      const requiredFields = [
        "policy_effect_status_at_event",
        "investment_allocation_status",
        "net_primary_premium_amount",
        ...(includesAdditionalPremium
          ? ["net_additional_premium_amount"]
          : []),
        ...(appliesLoanOffset
          ? ["policy_loan_and_interest_amount"]
          : []),
        ...(appliesPolicyChargeOffset
          ? ["unpaid_policy_charge_amount"]
          : []),
      ];
      if (
        !contractStatus ||
        primaryPremium === null ||
        additionalPremium === null ||
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null ||
        !normalizedEntry.rate
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      const factoredPremium = Math.trunc(
        primaryPremium * normalizedEntry.rate,
      );
      const grossValueBeforeOffsets = safeIntegerSum(
        factoredPremium,
        additionalPremium,
      );
      const totalOffsets = safeIntegerSum(
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
      );
      if (
        grossValueBeforeOffsets === null ||
        totalOffsets === null
      ) {
        return { ...result, state: "amount_overflow" };
      }
      if (totalOffsets > grossValueBeforeOffsets) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeOffsets,
          policy_loan_and_interest_amount:
            policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        };
      }
      return {
        ...result,
        value: grossValueBeforeOffsets - totalOffsets,
        reference_amount: grossValueBeforeOffsets,
        state: "calculated",
        formula_type:
          "net_premium_factor_plus_additional_premium",
        net_primary_premium_amount: primaryPremium,
        net_additional_premium_amount: additionalPremium,
        premium_factor: normalizedEntry.rate,
        policy_loan_and_interest_amount:
          policyLoanAndInterestAmount,
        unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        gross_value_before_offsets: grossValueBeforeOffsets,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "face_amount_plus_account_value_minus_paid_annuity_and_offsets"
    ) {
      if (!faceAmount) {
        return { ...result, state: "needs_face_amount" };
      }
      const contractStatus = policyStateChoice(
        item,
        "policy_effect_status_at_event",
      );
      const accountValue = policyStateNonNegativeMoney(
        item,
        "annuity_start_policy_account_value",
      );
      const paidAnnuityTotal = policyStateNonNegativeMoney(
        item,
        "annuity_paid_total_amount",
      );
      const twdConfirmed = policyStateBoolean(
        item,
        "policy_values_converted_to_twd",
      );
      const appliesLoanOffset = normalizedEntry.policy_state_keys.includes(
        "policy_loan_and_interest_amount",
      );
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        );
      const policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(
            item,
            "unpaid_policy_charge_amount",
          )
        : 0;
      const requiredFields = [
        "policy_effect_status_at_event",
        "annuity_start_policy_account_value",
        "annuity_paid_total_amount",
        "policy_values_converted_to_twd",
        ...(appliesLoanOffset
          ? ["policy_loan_and_interest_amount"]
          : []),
        ...(appliesPolicyChargeOffset
          ? ["unpaid_policy_charge_amount"]
          : []),
      ];
      if (
        !contractStatus ||
        accountValue === null ||
        paidAnnuityTotal === null ||
        !twdConfirmed ||
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      const grossValueBeforeOffsets = safeIntegerSum(
        faceAmount,
        accountValue,
      );
      const totalOffsets = safeIntegerSum(
        paidAnnuityTotal,
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
      );
      if (
        grossValueBeforeOffsets === null ||
        totalOffsets === null
      ) {
        return { ...result, state: "amount_overflow" };
      }
      if (totalOffsets > grossValueBeforeOffsets) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeOffsets,
          annuity_paid_total_amount: paidAnnuityTotal,
          policy_loan_and_interest_amount:
            policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        };
      }
      return {
        ...result,
        value: grossValueBeforeOffsets - totalOffsets,
        reference_amount: grossValueBeforeOffsets,
        state: "calculated",
        formula_type:
          "face_amount_plus_account_value_minus_paid_annuity_and_offsets",
        protected_amount: faceAmount,
        annuity_start_policy_account_value: accountValue,
        annuity_paid_total_amount: paidAnnuityTotal,
        policy_loan_and_interest_amount:
          policyLoanAndInterestAmount,
        unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
        gross_value_before_offsets: grossValueBeforeOffsets,
      };
    }
    if (
      normalizedEntry.calculation_basis === "policy_value_plus_general_insurance_amount" ||
      normalizedEntry.calculation_basis ===
        "policy_value_plus_general_and_accidental_insurance_amount"
    ) {
      const policyValueComponent = policyStateMoney(item, "policy_value_component");
      const generalInsuranceAmount = policyStateMoney(
        item,
        "general_death_disability_insurance_amount",
      );
      const includesAccidentalAmount =
        normalizedEntry.calculation_basis ===
        "policy_value_plus_general_and_accidental_insurance_amount";
      const accidentalInsuranceAmount = includesAccidentalAmount
        ? policyStateMoney(item, "accidental_death_disability_insurance_amount")
        : 0;
      const twdConfirmed = policyStateBoolean(
        item,
        "policy_values_converted_to_twd",
      );
      const requiredFields = [
        "policy_value_component",
        "general_death_disability_insurance_amount",
        ...(includesAccidentalAmount
          ? ["accidental_death_disability_insurance_amount"]
          : []),
        "policy_values_converted_to_twd",
      ];
      if (
        !policyValueComponent ||
        !generalInsuranceAmount ||
        (includesAccidentalAmount && !accidentalInsuranceAmount) ||
        !twdConfirmed
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      const value =
        policyValueComponent + generalInsuranceAmount + accidentalInsuranceAmount;
      return Number.isSafeInteger(value) && value > 0
        ? {
            ...result,
            value,
            reference_amount: value,
            state: "conditional_amount",
            policy_value_component: policyValueComponent,
            general_insurance_amount: generalInsuranceAmount,
            accidental_insurance_amount: accidentalInsuranceAmount || undefined,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "net_amount_at_risk_plus_policy_account_value") {
      const productFamily = String(
        item?.version_characteristics?.product_family || "",
      );
      if (
        [
          "allianz-worldview-foreign-currency-variable-universal-life",
          "allianz-new-excellence-variable-universal-life",
        ].includes(productFamily)
      ) {
        return allianzPolicyTypeCoverageValue(
          normalizedEntry,
          item,
          result,
        );
      }
      if (
        [
          "shinkong-jinhaoyi-variable-universal-life",
          "shinkong-jinmanyi-variable-universal-life",
        ].includes(productFamily)
      ) {
        return shinkongJinhaoyiCoverageValue(
          normalizedEntry,
          item,
          result,
        );
      }
      const accountValueStateKey =
        normalizedEntry.policy_state_keys.find((key) =>
          key.includes("policy_account_value"),
        ) || "policy_account_value";
      const netRiskAccountValue = policyStateNonNegativeMoney(
        item,
        accountValueStateKey,
      );
      const isKangjianJinzhun =
        productFamily ===
        "kangjian-jinzhun-variable-universal-life";
      const isGlobalNewExcellence =
        productFamily ===
        "global-new-excellence-variable-universal-life";
      const isAllianzWorldview =
        productFamily ===
        "allianz-worldview-foreign-currency-variable-universal-life";
      let formulaAccountValue = netRiskAccountValue;
      let delayedNoticePolicyFeeRefundAmount = 0;
      const postEventInsuranceCostRefundRequired =
        normalizedEntry.policy_state_keys.includes(
          "post_event_insurance_cost_refund_amount",
        );
      const postEventInsuranceCostRefundStatusRequired =
        normalizedEntry.policy_state_keys.includes(
          "post_event_insurance_cost_refund_status",
        );
      const postEventInsuranceCostRefundStatus =
        postEventInsuranceCostRefundStatusRequired
          ? policyStateChoice(
              item,
              "post_event_insurance_cost_refund_status",
            )
          : "";
      if (
        postEventInsuranceCostRefundStatusRequired &&
        !postEventInsuranceCostRefundStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "post_event_insurance_cost_refund_status",
        ]);
      }
      const postEventInsuranceCostRefundAmountRequired =
        postEventInsuranceCostRefundRequired &&
        (
          !postEventInsuranceCostRefundStatusRequired ||
          postEventInsuranceCostRefundStatus === "charged_after_event"
        );
      const postEventInsuranceCostRefundAmount =
        postEventInsuranceCostRefundAmountRequired
          ? policyStateNonNegativeMoney(
              item,
              "post_event_insurance_cost_refund_amount",
            )
          : 0;
      const appliesLoanOffset =
        normalizedEntry.policy_state_keys.includes(
          "policy_loan_and_interest_amount",
        ) || isGlobalNewExcellence;
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        ) ||
        normalizedEntry.policy_state_keys.includes(
          "unpaid_monthly_deduction_amount",
        );
      const unpaidPolicyChargeStateKey =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_monthly_deduction_amount",
        )
          ? "unpaid_monthly_deduction_amount"
          : "unpaid_policy_charge_amount";
      const requiresContractStatus =
        normalizedEntry.policy_state_keys.includes(
          "policy_effect_status_at_event",
        );
      const requiresClaimTimeStatus =
        normalizedEntry.policy_state_keys.includes(
          "claim_time_status",
        );
      const requiresExclusionStatus =
        normalizedEntry.policy_state_keys.includes(
          "benefit_exclusion_status",
        );
      const requiresDisabilityQualification =
        normalizedEntry.policy_state_keys.includes(
          "total_disability_qualification_status",
        );
      const requiresAgeAccuracyStatus =
        normalizedEntry.policy_state_keys.includes(
          "insured_age_accuracy_status",
        );
      const contractStatus = requiresContractStatus
        ? policyStateChoice(item, "policy_effect_status_at_event")
        : "active";
      const claimTimeStatus = requiresClaimTimeStatus
        ? policyStateChoice(item, "claim_time_status")
        : "within_claim_period";
      const ageAccuracyStatus = requiresAgeAccuracyStatus
        ? policyStateChoice(item, "insured_age_accuracy_status")
        : "confirmed_accurate";
      if (requiresContractStatus && !contractStatus) {
        return needsPolicyStateResult(result, item, [
          "policy_effect_status_at_event",
        ]);
      }
      if (requiresClaimTimeStatus && !claimTimeStatus) {
        return needsPolicyStateResult(result, item, [
          "claim_time_status",
        ]);
      }
      if (requiresAgeAccuracyStatus && !ageAccuracyStatus) {
        return needsPolicyStateResult(result, item, [
          "insured_age_accuracy_status",
        ]);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      if (ageAccuracyStatus !== "confirmed_accurate") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "insured_age_not_confirmed_accurate",
          insured_age_accuracy_status: ageAccuracyStatus,
        };
      }
      let policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(
            item,
            unpaidPolicyChargeStateKey,
          )
        : 0;
      if (
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null ||
        postEventInsuranceCostRefundAmount === null
      ) {
        return needsPolicyStateResult(result, item, [
          accountValueStateKey,
          ...(isKangjianJinzhun &&
          String(
            item?.version_characteristics?.semantic_phase || "",
          ) !== "legacy_greater_of_basic_or_account"
            ? ["insured_age_at_event"]
            : []),
          ...(appliesLoanOffset
            ? ["policy_loan_and_interest_amount"]
            : []),
          ...(appliesPolicyChargeOffset
            ? [unpaidPolicyChargeStateKey]
            : []),
          ...(postEventInsuranceCostRefundAmountRequired
            ? ["post_event_insurance_cost_refund_amount"]
            : []),
        ]);
      }
      let delayedRefundRule = "";
      let minorInsuredAge = null;
      if (isGlobalNewExcellence) {
        const newFamilyRequiredFields = [
          accountValueStateKey,
          "delayed_notice_policy_fee_refund_amount",
          "policy_loan_and_interest_amount",
        ];
        delayedNoticePolicyFeeRefundAmount =
          policyStateNonNegativeMoney(
            item,
            "delayed_notice_policy_fee_refund_amount",
          );
        if (
          netRiskAccountValue === null ||
          delayedNoticePolicyFeeRefundAmount === null ||
          policyLoanAndInterestAmount === null
        ) {
          return needsPolicyStateResult(
            result,
            item,
            newFamilyRequiredFields,
          );
        }
        delayedRefundRule = String(
          item?.version_characteristics
            ?.delayed_notice_policy_fee_refund_rule || "",
        );
        if (
          delayedRefundRule ===
          "restore_account_value_then_recalculate"
        ) {
          formulaAccountValue = safeIntegerSum(
            netRiskAccountValue,
            delayedNoticePolicyFeeRefundAmount,
          );
          if (formulaAccountValue === null) {
            return { ...result, state: "amount_overflow" };
          }
        }
      }
      if (postEventInsuranceCostRefundRequired) {
        formulaAccountValue = safeIntegerSum(
          formulaAccountValue,
          postEventInsuranceCostRefundAmount,
        );
        if (formulaAccountValue === null) {
          return { ...result, state: "amount_overflow" };
        }
      }
      if (formulaAccountValue === null) {
        return {
          ...result,
          state: "needs_account_value",
          required_fields: [accountValueStateKey],
        };
      }
      const eventAccountValueReturn = (
        formulaType,
        extra = {},
      ) => {
        const totalOffsets = safeIntegerSum(
          policyLoanAndInterestAmount,
          unpaidPolicyChargeAmount,
        );
        if (totalOffsets === null) {
          return { ...result, state: "amount_overflow" };
        }
        if (totalOffsets > formulaAccountValue) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason: "offsets_exceed_gross_benefit",
            gross_value_before_offsets: formulaAccountValue,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount:
              unpaidPolicyChargeAmount,
            ...extra,
          };
        }
        return {
          ...result,
          value: formulaAccountValue - totalOffsets,
          reference_amount: formulaAccountValue,
          state: "account_value_return",
          formula_type: formulaType,
          account_value: formulaAccountValue,
          policy_state_key: accountValueStateKey,
          policy_effect_status_at_event: contractStatus,
          claim_time_status: claimTimeStatus,
          policy_loan_and_interest_amount:
            policyLoanAndInterestAmount,
          unpaid_policy_charge_amount:
            unpaidPolicyChargeAmount,
          ...extra,
        };
      };
      if (claimTimeStatus === "time_barred") {
        if (
          item?.version_characteristics
            ?.account_value_return_on_time_bar === true
        ) {
          return eventAccountValueReturn(
            "time_barred_account_value_return",
          );
        }
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "claim_time_barred",
          claim_time_status: claimTimeStatus,
        };
      }
      const exclusionStatus = requiresExclusionStatus
        ? policyStateChoice(item, "benefit_exclusion_status")
        : "none_confirmed";
      if (requiresExclusionStatus && !exclusionStatus) {
        return needsPolicyStateResult(result, item, [
          "benefit_exclusion_status",
        ]);
      }
      if (exclusionStatus === "confirmed_applies") {
        if (
          item?.version_characteristics
            ?.account_value_return_on_exclusion === true
        ) {
          return eventAccountValueReturn(
            "exclusion_account_value_return",
            { benefit_exclusion_status: exclusionStatus },
          );
        }
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "benefit_exclusion_applies",
          benefit_exclusion_status: exclusionStatus,
        };
      }
      if (exclusionStatus !== "none_confirmed") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "benefit_exclusion_may_apply",
          benefit_exclusion_status: exclusionStatus,
        };
      }
      const disabilityQualificationStatus =
        requiresDisabilityQualification
          ? policyStateChoice(
              item,
              "total_disability_qualification_status",
            )
          : "confirmed_first_level_item";
      if (
        requiresDisabilityQualification &&
        !disabilityQualificationStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "total_disability_qualification_status",
        ]);
      }
      if (
        requiresDisabilityQualification &&
        disabilityQualificationStatus !==
          "confirmed_first_level_item"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "total_disability_not_confirmed",
          total_disability_qualification_status:
            disabilityQualificationStatus,
        };
      }
      const minorReturnAge = normalizedEntry.minor_account_value_return_age;
      if (minorReturnAge) {
        const insuredAge = policyStateInteger(item, "insured_age_at_event");
        minorInsuredAge = insuredAge;
        const minorRefundApplies =
          normalizedEntry.policy_state_keys.includes(
            "unexpired_premium_refund_amount",
          ) &&
          unexpiredInsuranceCostRefundApplies(
            item,
            normalizedEntry,
            selectedPolicyType(item),
          );
        const minorUnexpiredInsuranceCostRefundAmount =
          minorRefundApplies
            ? policyStateNonNegativeMoney(
                item,
                "unexpired_premium_refund_amount",
              )
            : 0;
        const minorFields = [
          "insured_age_at_event",
          accountValueStateKey,
          ...(minorRefundApplies
            ? ["unexpired_premium_refund_amount"]
            : []),
          ...(appliesLoanOffset
            ? ["policy_loan_and_interest_amount"]
            : []),
          ...(appliesPolicyChargeOffset
            ? [unpaidPolicyChargeStateKey]
            : []),
          ...(isGlobalNewExcellence
            ? [
                "delayed_notice_policy_fee_refund_amount",
                "policy_loan_and_interest_amount",
              ]
            : []),
          ...(currencyStateKey ? [currencyStateKey] : []),
        ];
        if (
          insuredAge === null ||
          formulaAccountValue === null ||
          minorUnexpiredInsuranceCostRefundAmount === null
        ) {
          return needsPolicyStateResult(result, item, minorFields);
        }
        if (insuredAge < minorReturnAge) {
          const minorGrossValue = safeIntegerSum(
            formulaAccountValue,
            minorUnexpiredInsuranceCostRefundAmount,
          );
          const minorOffsets = safeIntegerSum(
            policyLoanAndInterestAmount,
            unpaidPolicyChargeAmount,
          );
          if (
            minorGrossValue === null ||
            minorOffsets === null
          ) {
            return { ...result, state: "amount_overflow" };
          }
          if (minorOffsets > minorGrossValue) {
            return {
              ...result,
              state: "needs_insurer_confirmation",
              confirmation_reason:
                "offsets_exceed_gross_benefit",
              gross_value_before_offsets: minorGrossValue,
              policy_loan_and_interest_amount:
                policyLoanAndInterestAmount,
              unpaid_policy_charge_amount:
                unpaidPolicyChargeAmount,
            };
          }
          const minorValue = minorGrossValue - minorOffsets;
          return {
            ...result,
            value: minorValue,
            reference_amount: formulaAccountValue,
            state: "account_value_return",
            formula_type: "minor_account_value_return",
            account_value: formulaAccountValue,
            raw_account_value: netRiskAccountValue,
            adjusted_account_value: formulaAccountValue,
            delayed_notice_policy_fee_refund_amount:
              delayedNoticePolicyFeeRefundAmount,
            delayed_notice_policy_fee_refund_rule: delayedRefundRule,
            post_event_insurance_cost_refund_amount:
              postEventInsuranceCostRefundAmount,
            post_event_insurance_cost_refund_status:
              postEventInsuranceCostRefundStatus,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount:
              unpaidPolicyChargeAmount,
            unpaid_monthly_deduction_amount:
              unpaidPolicyChargeStateKey ===
              "unpaid_monthly_deduction_amount"
                ? unpaidPolicyChargeAmount
                : undefined,
            unexpired_insurance_cost_refund_amount:
              minorUnexpiredInsuranceCostRefundAmount,
            unexpired_insurance_cost_refund_applies:
              minorRefundApplies,
            gross_value_before_loan_offset: minorGrossValue,
            gross_value_before_offsets: minorGrossValue,
            minor_funeral_precedence_requires_insurer_confirmation:
              Boolean(
                item?.version_characteristics
                  ?.minor_funeral_precedence_rule ===
                  "insurer_confirmation_required_when_both_apply",
              ),
            policy_state_key: accountValueStateKey,
            insured_age_at_event: insuredAge,
            product_family: productFamily,
          };
        }
      }
      const policyType = selectedPolicyType(item);
      if (!faceAmount) return { ...result, state: "needs_face_amount" };
      if (netRiskAccountValue === null) {
        return {
          ...result,
          state: "needs_account_value",
          required_fields: [accountValueStateKey],
        };
      }
      if (!policyType) return { ...result, state: "needs_plan", required_fields: ["plan_name"] };

      let netAmountAtRisk = null;
      let unexpiredInsuranceCostRefundAmount = 0;
      let insuranceDeductionAmount = null;
      let thresholdFactor = null;
      let insuredAge = null;
      let paidPremiumTotal = null;
      let partialTerminationAmountTotal = null;
      const refundStateKey = normalizedEntry.policy_state_keys.includes(
        "unexpired_premium_refund_amount",
      )
        ? "unexpired_premium_refund_amount"
        : "";
      const refundApplies =
        Boolean(refundStateKey) &&
        unexpiredInsuranceCostRefundApplies(
          item,
          normalizedEntry,
          policyType,
        );
      if (refundApplies) {
        const recordedRefund = policyStateNonNegativeMoney(
          item,
          refundStateKey,
        );
        if (recordedRefund === null) {
          return needsPolicyStateResult(result, item, [refundStateKey]);
        }
        unexpiredInsuranceCostRefundAmount = recordedRefund;
      }
      const insuranceDeductionRequired =
        policyTypeRequiresInsuranceDeduction(item, policyType);
      const isAllianzAge111 =
        item?.version_characteristics?.product_family ===
        "allianz-age111-variable-universal-life-face-amount";
      const isGlobalExcellence =
        item?.version_characteristics?.product_family ===
        "global-excellence-variable-universal-life";
      if (isAllianzWorldview) {
        const semanticPhase = String(
          item?.version_characteristics?.semantic_phase || "",
        );
        if (insuranceDeductionRequired) {
          insuranceDeductionAmount = policyStateNonNegativeMoney(
            item,
            "insurance_deduction_amount",
          );
          if (insuranceDeductionAmount === null) {
            return needsPolicyStateResult(result, item, [
              "insurance_deduction_amount",
            ]);
          }
        }
        let grossInsuranceAmount = null;
        if (semanticPhase === "legacy-annual-insurance-amount-abc") {
          if (isPolicyTypeA(policyType)) {
            const issueAge = policyStateInteger(
              item,
              "insured_age_at_issue",
            );
            const policyYear = policyStateInteger(item, "policy_year");
            if (issueAge === null || policyYear === null) {
              return needsPolicyStateResult(result, item, [
                "insured_age_at_issue",
                "policy_year",
              ]);
            }
            if (issueAge < 14) {
              return {
                ...result,
                state: "outside_terms_formula_age_range",
                insured_age_at_issue: issueAge,
                minimum_formula_age: 14,
              };
            }
            const growthYears = Math.min(
              Math.max(policyYear - 1, 0),
              Math.max(60 - issueAge, 0),
            );
            const annualInsuranceAmount = safeFloorRatio(
              faceAmount,
              100 + growthYears * 5,
            );
            if (annualInsuranceAmount === null) {
              return { ...result, state: "amount_overflow" };
            }
            grossInsuranceAmount = Math.max(
              annualInsuranceAmount - insuranceDeductionAmount,
              formulaAccountValue,
            );
          } else if (isPolicyTypeB(policyType)) {
            grossInsuranceAmount = safeIntegerSum(
              faceAmount,
              formulaAccountValue,
            );
          } else if (isPolicyTypeC(policyType)) {
            grossInsuranceAmount = Math.max(
              faceAmount - insuranceDeductionAmount,
              formulaAccountValue,
            );
          }
        } else {
          if (isPolicyTypeA(policyType) || isPolicyTypeB(policyType)) {
            insuredAge = policyStateInteger(
              item,
              "insured_age_at_event",
            );
            if (insuredAge === null) {
              return needsPolicyStateResult(result, item, [
                "insured_age_at_event",
              ]);
            }
            thresholdFactor = thresholdFactorForAge(item, insuredAge);
            if (thresholdFactor === null) {
              return needsPolicyStateResult(result, item, [
                "insured_age_at_event",
              ]);
            }
          }
          const accountValueTimesMultiplier =
            thresholdFactor === null
              ? null
              : safeFloorRatio(
                  formulaAccountValue,
                  Math.round(thresholdFactor * 100),
                );
          if (
            thresholdFactor !== null &&
            accountValueTimesMultiplier === null
          ) {
            return { ...result, state: "amount_overflow" };
          }
          if (isPolicyTypeA(policyType)) {
            grossInsuranceAmount = Math.max(
              faceAmount - insuranceDeductionAmount,
              accountValueTimesMultiplier,
            );
          } else if (isPolicyTypeB(policyType)) {
            const accountPlusFace = safeIntegerSum(
              faceAmount,
              formulaAccountValue,
            );
            if (accountPlusFace === null) {
              return { ...result, state: "amount_overflow" };
            }
            grossInsuranceAmount = Math.max(
              accountPlusFace,
              accountValueTimesMultiplier,
            );
          } else if (isPolicyTypeC(policyType)) {
            grossInsuranceAmount = safeIntegerSum(
              faceAmount,
              formulaAccountValue,
            );
          } else if (isPolicyTypeD(policyType)) {
            grossInsuranceAmount = Math.max(
              faceAmount - insuranceDeductionAmount,
              formulaAccountValue,
            );
          }
        }
        if (grossInsuranceAmount !== null) {
          netAmountAtRisk = Math.max(
            grossInsuranceAmount - formulaAccountValue,
            0,
          );
        }
      } else if (isKangjianJinzhun) {
        const semanticPhase = String(
          item?.version_characteristics?.semantic_phase || "",
        );
        let grossInsuranceAmount = null;
        insuredAge = minorInsuredAge;
        if (semanticPhase === "legacy_greater_of_basic_or_account") {
          grossInsuranceAmount = Math.max(
            faceAmount,
            formulaAccountValue,
          );
        } else {
          if (insuredAge === null) {
            insuredAge = policyStateInteger(
              item,
              "insured_age_at_event",
            );
          }
          if (insuredAge === null) {
            return needsPolicyStateResult(result, item, [
              "insured_age_at_event",
            ]);
          }
          thresholdFactor = thresholdFactorForAge(
            item,
            insuredAge,
          );
          if (thresholdFactor === null) {
            return needsPolicyStateResult(result, item, [
              "insured_age_at_event",
            ]);
          }
          const minimumInsuranceAmount = safeFloorRatio(
            formulaAccountValue,
            Math.round(thresholdFactor * 100),
          );
          if (minimumInsuranceAmount === null) {
            return { ...result, state: "amount_overflow" };
          }
          grossInsuranceAmount = Math.max(
            faceAmount,
            minimumInsuranceAmount,
          );
        }
        netAmountAtRisk = Math.max(
          grossInsuranceAmount - formulaAccountValue,
          0,
        );
      } else if (isGlobalExcellence) {
        const formulaVariant = String(
          item?.version_characteristics?.minimum_rate_formula_variant || "",
        );
        if (formulaVariant === "fixed_110_percent") {
          thresholdFactor = 1.1;
        } else {
          insuredAge = policyStateInteger(item, "insured_age_at_event");
          if (insuredAge === null) {
            return needsPolicyStateResult(result, item, [
              "insured_age_at_event",
            ]);
          }
          const minimumFormulaAge = Number(
            item?.version_characteristics?.minimum_benefit_formula_age,
          );
          if (
            Number.isSafeInteger(minimumFormulaAge) &&
            minimumFormulaAge > 0 &&
            insuredAge < minimumFormulaAge
          ) {
            return {
              ...result,
              state: "outside_terms_formula_age_range",
              insured_age_at_event: insuredAge,
              minimum_formula_age: minimumFormulaAge,
            };
          }
          thresholdFactor = thresholdFactorForAge(item, insuredAge);
          if (thresholdFactor === null) {
            return needsPolicyStateResult(result, item, [
              "insured_age_at_event",
            ]);
          }
        }

        const minimumInsuranceAmount = safeFloorRatio(
          netRiskAccountValue,
          Math.round(thresholdFactor * 100),
        );
        if (minimumInsuranceAmount === null) {
          return { ...result, state: "amount_overflow" };
        }
        if (isPolicyTypeA(policyType)) {
          const grossInsuranceAmount = Math.max(
            faceAmount,
            minimumInsuranceAmount,
          );
          netAmountAtRisk = Math.max(
            grossInsuranceAmount - netRiskAccountValue,
            0,
          );
        } else if (isPolicyTypeB(policyType)) {
          const grossInsuranceAmount =
            formulaVariant === "fixed_110_percent"
              ? faceAmount + netRiskAccountValue
              : Math.max(
                  faceAmount + netRiskAccountValue,
                  minimumInsuranceAmount,
                );
          netAmountAtRisk = Math.max(
            grossInsuranceAmount - netRiskAccountValue,
            0,
          );
        }
      } else if (isGlobalNewExcellence) {
        const semanticPhase = String(
          item?.version_characteristics?.semantic_phase || "",
        );
        let grossInsuranceAmount = null;
        if (semanticPhase === "premium_three_way_ab") {
          const requiredFields = [
            "paid_premium_total",
            "partial_termination_amount_total",
          ];
          paidPremiumTotal = policyStateMoney(
            item,
            "paid_premium_total",
          );
          partialTerminationAmountTotal =
            policyStateNonNegativeMoney(
              item,
              "partial_termination_amount_total",
            );
          if (
            paidPremiumTotal === null ||
            partialTerminationAmountTotal === null
          ) {
            return needsPolicyStateResult(
              result,
              item,
              requiredFields,
            );
          }
          const paidPremiumTimes112 = safeFloorRatio(
            paidPremiumTotal,
            112,
          );
          const accountValueTimes110 = safeFloorRatio(
            formulaAccountValue,
            110,
          );
          const accountPlusFace = safeIntegerSum(
            formulaAccountValue,
            faceAmount,
          );
          if (
            paidPremiumTimes112 === null ||
            accountValueTimes110 === null ||
            accountPlusFace === null
          ) {
            return { ...result, state: "amount_overflow" };
          }
          const premiumCandidate = Math.max(
            paidPremiumTimes112 -
              partialTerminationAmountTotal,
            0,
          );
          if (isPolicyTypeA(policyType)) {
            grossInsuranceAmount = Math.max(
              accountValueTimes110,
              faceAmount,
              premiumCandidate,
            );
          } else if (isPolicyTypeB(policyType)) {
            grossInsuranceAmount = Math.max(
              accountPlusFace,
              premiumCandidate,
            );
          }
        } else {
          insuredAge = minorInsuredAge;
          if (
            isPolicyTypeA(policyType) ||
            isPolicyTypeB(policyType)
          ) {
            if (insuredAge === null) {
              insuredAge = policyStateInteger(
                item,
                "insured_age_at_event",
              );
            }
            if (insuredAge === null) {
              return needsPolicyStateResult(result, item, [
                "insured_age_at_event",
              ]);
            }
            thresholdFactor = thresholdFactorForAge(
              item,
              insuredAge,
            );
            if (thresholdFactor === null) {
              return needsPolicyStateResult(result, item, [
                "insured_age_at_event",
              ]);
            }
          }
          const accountPlusFace = safeIntegerSum(
            formulaAccountValue,
            faceAmount,
          );
          if (accountPlusFace === null) {
            return { ...result, state: "amount_overflow" };
          }
          if (isPolicyTypeA(policyType)) {
            const minimumInsuranceAmount = safeFloorRatio(
              formulaAccountValue,
              Math.round(thresholdFactor * 100),
            );
            if (minimumInsuranceAmount === null) {
              return { ...result, state: "amount_overflow" };
            }
            grossInsuranceAmount = Math.max(
              faceAmount,
              minimumInsuranceAmount,
            );
          } else if (isPolicyTypeB(policyType)) {
            const minimumInsuranceAmount = safeFloorRatio(
              formulaAccountValue,
              Math.round(thresholdFactor * 100),
            );
            if (minimumInsuranceAmount === null) {
              return { ...result, state: "amount_overflow" };
            }
            grossInsuranceAmount = Math.max(
              accountPlusFace,
              minimumInsuranceAmount,
            );
          } else if (isPolicyTypeC(policyType)) {
            grossInsuranceAmount = Math.max(
              faceAmount,
              formulaAccountValue,
            );
          } else if (isPolicyTypeD(policyType)) {
            grossInsuranceAmount = accountPlusFace;
          }
        }
        if (grossInsuranceAmount !== null) {
          netAmountAtRisk = Math.max(
            grossInsuranceAmount - formulaAccountValue,
            0,
          );
        }
      } else if (isAllianzAge111) {
        const requiredFields = ["policy_account_value"];
        if (["甲", "丙", "戊"].some((label) => policyType.includes(label))) {
          requiredFields.push("insurance_deduction_amount");
          insuranceDeductionAmount = policyStateNonNegativeMoney(
            item,
            "insurance_deduction_amount",
          );
        }
        if (["丙", "丁", "戊"].some((label) => policyType.includes(label))) {
          requiredFields.push("insured_age_at_event");
          insuredAge = policyStateInteger(item, "insured_age_at_event");
          thresholdFactor = thresholdFactorForAge(item, insuredAge);
        }
        if (policyType.includes("戊")) {
          requiredFields.push(
            "paid_premium_total",
            "partial_termination_amount_total",
          );
          paidPremiumTotal = policyStateMoney(item, "paid_premium_total");
          partialTerminationAmountTotal = policyStateNonNegativeMoney(
            item,
            "partial_termination_amount_total",
          );
        }
        const missingFields = missingPolicyStateFields(item, requiredFields);
        if (
          missingFields.length ||
          (["丙", "丁", "戊"].some((label) => policyType.includes(label)) &&
            thresholdFactor === null)
        ) {
          return needsPolicyStateResult(result, item, requiredFields);
        }

        if (policyType.includes("甲")) {
          netAmountAtRisk = Math.max(
            faceAmount - insuranceDeductionAmount - netRiskAccountValue,
            0,
          );
        } else if (policyType.includes("乙")) {
          netAmountAtRisk = faceAmount;
        } else if (policyType.includes("丙")) {
          netAmountAtRisk = Math.max(
            faceAmount - insuranceDeductionAmount - netRiskAccountValue,
            Math.trunc(netRiskAccountValue * thresholdFactor),
          );
        } else if (policyType.includes("丁")) {
          netAmountAtRisk = Math.max(
            faceAmount,
            Math.trunc(netRiskAccountValue * thresholdFactor),
          );
        } else if (policyType.includes("戊")) {
          netAmountAtRisk = Math.max(
            faceAmount - insuranceDeductionAmount - netRiskAccountValue,
            paidPremiumTotal -
              partialTerminationAmountTotal -
              netRiskAccountValue,
            Math.trunc(netRiskAccountValue * thresholdFactor),
          );
        }
      } else if (insuranceDeductionRequired) {
        insuranceDeductionAmount = policyStateNonNegativeMoney(
          item,
          "insurance_deduction_amount",
        );
        if (insuranceDeductionAmount === null) {
          return needsPolicyStateResult(result, item, [
            "insurance_deduction_amount",
          ]);
        }
        if (isPolicyTypeA(policyType) || isPolicyTypeC(policyType)) {
          netAmountAtRisk = Math.max(
            faceAmount - insuranceDeductionAmount - netRiskAccountValue,
            0,
          );
        }
      } else if (isPolicyTypeA(policyType)) {
        netAmountAtRisk = Math.max(faceAmount - netRiskAccountValue, 0);
      } else if (isPolicyTypeB(policyType)) {
        netAmountAtRisk = faceAmount;
      }
      if (netAmountAtRisk === null) return { ...result, state: "needs_plan", required_fields: ["plan_name"] };

      const directDelayedRefundAmount =
        isGlobalNewExcellence &&
        delayedRefundRule === "add_to_calculated_benefit"
          ? delayedNoticePolicyFeeRefundAmount
          : 0;
      const protectedAmount = safeIntegerSum(
        netAmountAtRisk,
        unexpiredInsuranceCostRefundAmount,
        directDelayedRefundAmount,
      );
      const grossValueBeforeLoanOffset = safeIntegerSum(
        protectedAmount,
        formulaAccountValue,
      );
      const totalOffsets = safeIntegerSum(
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
      );
      if (
        protectedAmount === null ||
        grossValueBeforeLoanOffset === null ||
        totalOffsets === null
      ) {
        return { ...result, state: "amount_overflow" };
      }
      if (totalOffsets > grossValueBeforeLoanOffset) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeLoanOffset,
          policy_loan_and_interest_amount:
            policyLoanAndInterestAmount,
          unpaid_policy_charge_amount:
            unpaidPolicyChargeAmount,
        };
      }
      const value = grossValueBeforeLoanOffset - totalOffsets;
      const funeralLimitApplies = policyTypeUsesFuneralLimit(
        normalizedEntry,
        item,
      );
      if (funeralLimitApplies) {
        const status = policyStateChoice(item, "death_benefit_status");
        if (!status) {
          return needsPolicyStateResult(result, item, [
            "death_benefit_status",
          ]);
        }
        if (status === "funeral_limited") {
          const remainingLimit = policyStateNonNegativeMoney(
            item,
            "remaining_funeral_benefit_limit",
          );
          if (remainingLimit === null) {
            return needsPolicyStateResult(result, item, [
              "remaining_funeral_benefit_limit",
            ]);
          }
          const cappedProtectedAmount = Math.min(
            protectedAmount,
            remainingLimit,
          );
          const requiresFuneralExcessRefund =
            normalizedEntry.policy_state_keys.includes(
              "funeral_excess_insurance_cost_refund_status",
            );
          let funeralExcessRefundStatus = "";
          let funeralExcessRefundAmount = 0;
          if (
            requiresFuneralExcessRefund &&
            cappedProtectedAmount < protectedAmount
          ) {
            funeralExcessRefundStatus = policyStateChoice(
              item,
              "funeral_excess_insurance_cost_refund_status",
            );
            if (!funeralExcessRefundStatus) {
              return needsPolicyStateResult(result, item, [
                "funeral_excess_insurance_cost_refund_status",
              ]);
            }
            if (funeralExcessRefundStatus === "unknown") {
              return {
                ...result,
                state: "needs_insurer_confirmation",
                confirmation_reason:
                  "funeral_excess_insurance_cost_refund_unknown",
              };
            }
            if (
              funeralExcessRefundStatus === "confirmed_amount"
            ) {
              funeralExcessRefundAmount =
                policyStateNonNegativeMoney(
                  item,
                  "funeral_excess_insurance_cost_refund_amount",
                );
              if (funeralExcessRefundAmount === null) {
                return needsPolicyStateResult(result, item, [
                  "funeral_excess_insurance_cost_refund_amount",
                ]);
              }
            }
          }
          const grossFuneralValue = safeIntegerSum(
            cappedProtectedAmount,
            formulaAccountValue,
            funeralExcessRefundAmount,
          );
          if (grossFuneralValue === null) {
            return { ...result, state: "amount_overflow" };
          }
          if (totalOffsets > grossFuneralValue) {
            return {
              ...result,
              state: "needs_insurer_confirmation",
              confirmation_reason:
                "offsets_exceed_gross_benefit",
              gross_value_before_offsets: grossFuneralValue,
              policy_loan_and_interest_amount:
                policyLoanAndInterestAmount,
              unpaid_policy_charge_amount:
                unpaidPolicyChargeAmount,
            };
          }
          const funeralValue = grossFuneralValue - totalOffsets;
          return Number.isSafeInteger(funeralValue) &&
            (funeralValue > 0 || isGlobalNewExcellence)
            ? {
                ...result,
                value: funeralValue,
                reference_amount: grossValueBeforeLoanOffset,
                state: "death_or_funeral_amount",
                formula_type: `${policyType.replace("型", "")}_funeral_limited`,
                gross_value_before_funeral_cap:
                  grossValueBeforeLoanOffset,
                gross_value_before_loan_offset: grossFuneralValue,
                protected_amount: protectedAmount,
                capped_protected_amount: cappedProtectedAmount,
                funeral_benefit_limit: remainingLimit,
                funeral_excess_insurance_cost_refund_status:
                  funeralExcessRefundStatus,
                funeral_excess_insurance_cost_refund_amount:
                  funeralExcessRefundAmount,
                net_amount_at_risk: netAmountAtRisk,
                unexpired_insurance_cost_refund_amount:
                  unexpiredInsuranceCostRefundAmount,
                unexpired_insurance_cost_refund_applies: refundApplies,
                face_amount: faceAmount,
                face_amount_label:
                  String(item?.face_amount_label || "").trim() || "基本保額",
                account_value: formulaAccountValue,
                raw_account_value: netRiskAccountValue,
                adjusted_account_value: formulaAccountValue,
                delayed_notice_policy_fee_refund_amount:
                  delayedNoticePolicyFeeRefundAmount,
                delayed_notice_policy_fee_refund_rule:
                  delayedRefundRule,
                policy_loan_and_interest_amount:
                  policyLoanAndInterestAmount,
                unpaid_policy_charge_amount:
                  unpaidPolicyChargeAmount,
                policy_effect_status_at_event:
                  contractStatus,
                claim_time_status: claimTimeStatus,
                benefit_exclusion_status: exclusionStatus,
                total_disability_qualification_status:
                  requiresDisabilityQualification
                    ? disabilityQualificationStatus
                    : undefined,
                policy_type: policyType,
                policy_state_key: accountValueStateKey,
                threshold_factor: thresholdFactor,
                insured_age_at_event: insuredAge,
                paid_premium_total: paidPremiumTotal,
                partial_termination_amount_total:
                  partialTerminationAmountTotal,
                minimum_rate_formula_variant:
                  item?.version_characteristics
                    ?.minimum_rate_formula_variant,
                semantic_phase:
                  item?.version_characteristics?.semantic_phase,
                product_family: productFamily,
              }
            : { ...result, state: "amount_overflow" };
        }
      }
      return Number.isSafeInteger(value) &&
        (value > 0 || isGlobalNewExcellence)
        ? {
            ...result,
            value,
            reference_amount: grossValueBeforeLoanOffset,
            state: funeralLimitApplies
              ? "death_or_funeral_amount"
              : "calculated",
            net_amount_at_risk: netAmountAtRisk,
            face_amount: faceAmount,
            face_amount_label:
              String(item?.face_amount_label || "").trim() || "基本保額",
            account_value: formulaAccountValue,
            raw_account_value: netRiskAccountValue,
            adjusted_account_value: formulaAccountValue,
            policy_type: policyType,
            unexpired_insurance_cost_refund_amount:
              unexpiredInsuranceCostRefundAmount,
            unexpired_insurance_cost_refund_applies: refundApplies,
            delayed_notice_policy_fee_refund_amount:
              delayedNoticePolicyFeeRefundAmount,
            delayed_notice_policy_fee_refund_rule: delayedRefundRule,
            post_event_insurance_cost_refund_amount:
              postEventInsuranceCostRefundAmount,
            post_event_insurance_cost_refund_status:
              postEventInsuranceCostRefundStatus,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount:
              unpaidPolicyChargeAmount,
            unpaid_monthly_deduction_amount:
              unpaidPolicyChargeStateKey ===
              "unpaid_monthly_deduction_amount"
                ? unpaidPolicyChargeAmount
                : undefined,
            policy_effect_status_at_event: contractStatus,
            claim_time_status: claimTimeStatus,
            benefit_exclusion_status: exclusionStatus,
            total_disability_qualification_status:
              requiresDisabilityQualification
                ? disabilityQualificationStatus
                : undefined,
            gross_value_before_loan_offset:
              grossValueBeforeLoanOffset,
            formula_type: funeralLimitApplies
              ? `${policyType.replace("型", "")}_standard_death`
              : policyType.replace("型", ""),
            insurance_deduction_amount: insuranceDeductionAmount,
            threshold_factor: thresholdFactor,
            insured_age_at_event: insuredAge,
            paid_premium_total: paidPremiumTotal,
            partial_termination_amount_total: partialTerminationAmountTotal,
            policy_state_key: accountValueStateKey,
            minimum_rate_formula_variant:
              item?.version_characteristics?.minimum_rate_formula_variant,
            semantic_phase:
              item?.version_characteristics?.semantic_phase,
            product_family: productFamily,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "paid_premium_factor_account_value_formula") {
      const accountValueStateKey =
        normalizedEntry.policy_state_keys.find((key) =>
          key.includes("policy_account_value"),
        ) || "policy_account_value";
      const formulaAccountValue = policyStateNonNegativeMoney(
        item,
        accountValueStateKey,
      );
      const requiresContractStatus =
        normalizedEntry.policy_state_keys.includes(
          "policy_effect_status_at_event",
        );
      const requiresClaimTimeStatus =
        normalizedEntry.policy_state_keys.includes(
          "claim_time_status",
        );
      const requiresExclusionStatus =
        normalizedEntry.policy_state_keys.includes(
          "benefit_exclusion_status",
        );
      const requiresDisabilityQualification =
        normalizedEntry.policy_state_keys.includes(
          "total_disability_qualification_status",
        );
      const requiresCurrentBenefitAmountStatus =
        normalizedEntry.policy_state_keys.includes(
          "current_benefit_amount_status",
        );
      const requiresAgeAccuracyStatus =
        normalizedEntry.policy_state_keys.includes(
          "insured_age_accuracy_status",
        );
      const contractStatus = requiresContractStatus
        ? policyStateChoice(item, "policy_effect_status_at_event")
        : "active";
      const claimTimeStatus = requiresClaimTimeStatus
        ? policyStateChoice(item, "claim_time_status")
        : "within_claim_period";
      const ageAccuracyStatus = requiresAgeAccuracyStatus
        ? policyStateChoice(item, "insured_age_accuracy_status")
        : "confirmed_accurate";
      const appliesLoanOffset = normalizedEntry.policy_state_keys.includes(
        "policy_loan_and_interest_amount",
      );
      const appliesPolicyChargeOffset =
        normalizedEntry.policy_state_keys.includes(
          "unpaid_policy_charge_amount",
        );
      const appliesRemittanceFee =
        normalizedEntry.policy_state_keys.includes(
          "remittance_fee_amount",
        );
      const policyLoanAndInterestAmount = appliesLoanOffset
        ? policyStateNonNegativeMoney(
            item,
            "policy_loan_and_interest_amount",
          )
        : 0;
      const unpaidPolicyChargeAmount = appliesPolicyChargeOffset
        ? policyStateNonNegativeMoney(item, "unpaid_policy_charge_amount")
        : 0;
      const remittanceFeeAmount = appliesRemittanceFee
        ? policyStateNonNegativeMoney(item, "remittance_fee_amount")
        : 0;
      const commonRequiredFields = [
        accountValueStateKey,
        ...(requiresContractStatus
          ? ["policy_effect_status_at_event"]
          : []),
        ...(requiresClaimTimeStatus ? ["claim_time_status"] : []),
        ...(requiresAgeAccuracyStatus
          ? ["insured_age_accuracy_status"]
          : []),
        ...(requiresCurrentBenefitAmountStatus
          ? ["current_benefit_amount_status"]
          : []),
        ...(appliesLoanOffset
          ? ["policy_loan_and_interest_amount"]
          : []),
        ...(appliesPolicyChargeOffset
          ? ["unpaid_policy_charge_amount"]
          : []),
        ...(appliesRemittanceFee ? ["remittance_fee_amount"] : []),
        ...(currencyStateKey ? [currencyStateKey] : []),
      ];
      if (
        formulaAccountValue === null ||
        (requiresContractStatus && !contractStatus) ||
        (requiresClaimTimeStatus && !claimTimeStatus) ||
        (requiresAgeAccuracyStatus && !ageAccuracyStatus) ||
        policyLoanAndInterestAmount === null ||
        unpaidPolicyChargeAmount === null ||
        remittanceFeeAmount === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          commonRequiredFields,
        );
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
        };
      }
      if (ageAccuracyStatus !== "confirmed_accurate") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "insured_age_not_confirmed_accurate",
          insured_age_accuracy_status: ageAccuracyStatus,
        };
      }
      const totalOffsets = safeIntegerSum(
        policyLoanAndInterestAmount,
        unpaidPolicyChargeAmount,
        remittanceFeeAmount,
      );
      if (totalOffsets === null) {
        return { ...result, state: "amount_overflow" };
      }
      const accountValueReturnResult = (
        formulaType,
        extra = {},
      ) => {
        if (totalOffsets > formulaAccountValue) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason: "offsets_exceed_gross_benefit",
            gross_value_before_offsets: formulaAccountValue,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
            remittance_fee_amount: remittanceFeeAmount,
            ...extra,
          };
        }
        return {
          ...result,
          value: formulaAccountValue - totalOffsets,
          reference_amount: formulaAccountValue,
          state: "account_value_return",
          formula_type: formulaType,
          account_value: formulaAccountValue,
          gross_value_before_offsets: formulaAccountValue,
          policy_loan_and_interest_amount:
            policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
          remittance_fee_amount: remittanceFeeAmount,
          policy_state_key: accountValueStateKey,
          policy_effect_status_at_event: contractStatus,
          claim_time_status: claimTimeStatus,
          ...extra,
        };
      };
      if (claimTimeStatus === "time_barred") {
        return accountValueReturnResult(
          "time_barred_account_value_return",
        );
      }
      const exclusionStatus = requiresExclusionStatus
        ? policyStateChoice(item, "benefit_exclusion_status")
        : "none_confirmed";
      if (requiresExclusionStatus && !exclusionStatus) {
        return needsPolicyStateResult(result, item, [
          "benefit_exclusion_status",
        ]);
      }
      if (
        exclusionStatus === "confirmed_applies" &&
        item?.version_characteristics
          ?.account_value_return_on_exclusion === true
      ) {
        return accountValueReturnResult(
          "exclusion_account_value_return",
          { benefit_exclusion_status: exclusionStatus },
        );
      }
      if (exclusionStatus !== "none_confirmed") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "benefit_exclusion_may_apply",
          benefit_exclusion_status: exclusionStatus,
        };
      }
      const disabilityQualificationStatus =
        requiresDisabilityQualification
          ? policyStateChoice(
              item,
              "total_disability_qualification_status",
            )
          : "confirmed_first_level_item";
      if (
        requiresDisabilityQualification &&
        !disabilityQualificationStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "total_disability_qualification_status",
        ]);
      }
      if (
        requiresDisabilityQualification &&
        disabilityQualificationStatus !==
          "confirmed_first_level_item"
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "total_disability_not_confirmed",
          total_disability_qualification_status:
            disabilityQualificationStatus,
        };
      }
      const minorReturnAge = normalizedEntry.minor_account_value_return_age;
      if (minorReturnAge) {
        const insuredAge = policyStateInteger(item, "insured_age_at_event");
        const minorFields = [
          "insured_age_at_event",
          ...commonRequiredFields,
        ];
        if (insuredAge === null) {
          return needsPolicyStateResult(result, item, minorFields);
        }
        if (insuredAge < minorReturnAge) {
          return accountValueReturnResult(
            "minor_account_value_return",
            { insured_age_at_event: insuredAge },
          );
        }
      }

      const currentBenefitAmountStatus =
        requiresCurrentBenefitAmountStatus
          ? policyStateChoice(
              item,
              "current_benefit_amount_status",
            )
          : "formula_confirmed_current";
      if (
        requiresCurrentBenefitAmountStatus &&
        !currentBenefitAmountStatus
      ) {
        return needsPolicyStateResult(result, item, [
          "current_benefit_amount_status",
        ]);
      }
      if (currentBenefitAmountStatus === "unknown") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "current_benefit_amount_basis_unknown",
          current_benefit_amount_status:
            currentBenefitAmountStatus,
        };
      }
      const usesCurrentBenefitAmount =
        currentBenefitAmountStatus ===
        "current_amount_provided";
      const currentBenefitAmount = usesCurrentBenefitAmount
        ? policyStateNonNegativeMoney(
            item,
            "current_death_disability_benefit_amount",
          )
        : null;
      if (
        usesCurrentBenefitAmount &&
        currentBenefitAmount === null
      ) {
        return needsPolicyStateResult(result, item, [
          "current_death_disability_benefit_amount",
        ]);
      }

      const paidPremiumTotal = policyStateMoney(item, "paid_premium_total");
      const partialTerminationTotal = policyStateNonNegativeMoney(item, "partial_termination_amount_total");
      const rawFactor = policyStateNumber(item, "specified_percent_or_multiplier");
      const fixedFactorUnit = String(
        item?.version_characteristics
          ?.specified_factor_unit_fixed || "",
      );
      const requiresFactorUnit =
        item?.version_characteristics
          ?.specified_factor_unit_required === true &&
        !fixedFactorUnit;
      const factorUnit = fixedFactorUnit || (requiresFactorUnit
        ? policyStateChoice(item, "specified_factor_unit")
        : "");
      const requiredFormulaFields = uniquePolicyStateFields([
        ...commonRequiredFields,
        "paid_premium_total",
        "partial_termination_amount_total",
        "specified_percent_or_multiplier",
        ...(requiresFactorUnit
          ? ["specified_factor_unit"]
          : []),
      ]);
      if (
        !usesCurrentBenefitAmount &&
        (
          !paidPremiumTotal ||
          partialTerminationTotal === null ||
          rawFactor === null ||
          (requiresFactorUnit && !factorUnit)
        )
      ) {
        return needsPolicyStateResult(result, item, requiredFormulaFields);
      }
      const policyType = String(item.plan_name || policyState(item).policy_type || item.policy_type || "").trim();
      if (!policyType) return { ...result, state: "needs_plan", required_fields: ["plan_name"] };

      const factor = usesCurrentBenefitAmount
        ? null
        : (
            factorUnit
              ? (
                  factorUnit === "percent"
                    ? rawFactor / 100
                    : factorUnit === "multiplier"
                      ? rawFactor
                      : Number.NaN
                )
              : (
                  rawFactor > MAX_RATE
                    ? rawFactor / 100
                    : rawFactor
                )
          );
      if (
        !usesCurrentBenefitAmount &&
        (
          !Number.isFinite(factor) ||
          factor <= 0 ||
          factor > MAX_RATE
        )
      ) {
        return needsPolicyStateResult(result, item, requiredFormulaFields);
      }

      if (
        !usesCurrentBenefitAmount &&
        partialTerminationTotal > paidPremiumTotal
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "partial_termination_exceeds_paid_premium",
          paid_premium_total: paidPremiumTotal,
          partial_termination_amount_total:
            partialTerminationTotal,
        };
      }
      const paidPremiumBasis = usesCurrentBenefitAmount
        ? null
        : paidPremiumTotal - partialTerminationTotal;
      const factorAmount = usesCurrentBenefitAmount
        ? null
        : paidPremiumBasis * factor;
      if (
        !usesCurrentBenefitAmount &&
        !Number.isSafeInteger(factorAmount)
      ) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "specified_factor_rounding_rule_missing",
          paid_premium_basis: paidPremiumBasis,
          specified_factor: factor,
          specified_factor_unit:
            factorUnit || "legacy_inferred",
          unrounded_factor_amount: factorAmount,
        };
      }
      let value = null;
      let formulaType = "";
      if (usesCurrentBenefitAmount) {
        value = currentBenefitAmount;
        formulaType = "current_recorded_benefit_amount";
      } else if (policyType.includes("甲")) {
        value = Math.max(factorAmount, formulaAccountValue);
        formulaType = "A";
      } else if (policyType.includes("乙")) {
        value = safeIntegerSum(factorAmount, formulaAccountValue);
        formulaType = "B";
      } else {
        return { ...result, state: "needs_plan", required_fields: ["plan_name"] };
      }
      if (!Number.isSafeInteger(value)) {
        return { ...result, state: "amount_overflow" };
      }
      const grossValueBeforeFuneralCap = value;
      let grossValueBeforeOffsets = value;
      let remainingFuneralLimit = null;
      let funeralExcessRefundStatus = "";
      let funeralExcessRefundAmount = 0;
      const requiresFuneralExcessRefund =
        normalizedEntry.policy_state_keys.includes(
          "funeral_excess_insurance_cost_refund_status",
        );
      let protectedAmount = Math.max(
        grossValueBeforeOffsets - formulaAccountValue,
        0,
      );
      const funeralLimitApplies = policyTypeUsesFuneralLimit(
        normalizedEntry,
        item,
      );
      if (funeralLimitApplies) {
        const deathStatus = policyStateChoice(
          item,
          "death_benefit_status",
        );
        if (!deathStatus) {
          return needsPolicyStateResult(result, item, [
            "death_benefit_status",
          ]);
        }
        if (deathStatus === "funeral_limited") {
          remainingFuneralLimit = policyStateNonNegativeMoney(
            item,
            "remaining_funeral_benefit_limit",
          );
          if (remainingFuneralLimit === null) {
            return needsPolicyStateResult(result, item, [
              "remaining_funeral_benefit_limit",
            ]);
          }
          protectedAmount = Math.min(
            protectedAmount,
            remainingFuneralLimit,
          );
          if (
            requiresFuneralExcessRefund &&
            protectedAmount <
            grossValueBeforeFuneralCap - formulaAccountValue
          ) {
            funeralExcessRefundStatus = policyStateChoice(
              item,
              "funeral_excess_insurance_cost_refund_status",
            );
            if (!funeralExcessRefundStatus) {
              return needsPolicyStateResult(result, item, [
                "funeral_excess_insurance_cost_refund_status",
              ]);
            }
            if (funeralExcessRefundStatus === "unknown") {
              return {
                ...result,
                state: "needs_insurer_confirmation",
                confirmation_reason:
                  "funeral_excess_insurance_cost_refund_unknown",
              };
            }
            if (
              funeralExcessRefundStatus === "confirmed_amount"
            ) {
              funeralExcessRefundAmount =
                policyStateNonNegativeMoney(
                  item,
                  "funeral_excess_insurance_cost_refund_amount",
                );
              if (funeralExcessRefundAmount === null) {
                return needsPolicyStateResult(result, item, [
                  "funeral_excess_insurance_cost_refund_amount",
                ]);
              }
            }
          }
          grossValueBeforeOffsets = safeIntegerSum(
            formulaAccountValue,
            protectedAmount,
            funeralExcessRefundAmount,
          );
          if (grossValueBeforeOffsets === null) {
            return { ...result, state: "amount_overflow" };
          }
        }
      }
      if (totalOffsets > grossValueBeforeOffsets) {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "offsets_exceed_gross_benefit",
          gross_value_before_offsets: grossValueBeforeOffsets,
          policy_loan_and_interest_amount: policyLoanAndInterestAmount,
          unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
          remittance_fee_amount: remittanceFeeAmount,
        };
      }
      value = grossValueBeforeOffsets - totalOffsets;
      return Number.isSafeInteger(value) && value >= 0
        ? {
            ...result,
            value,
            reference_amount: grossValueBeforeOffsets,
            state: funeralLimitApplies
              ? "death_or_funeral_amount"
              : "calculated",
            policy_state_key: "paid_premium_total",
            policy_type: policyType,
            formula_type: formulaType,
            paid_premium_basis: paidPremiumBasis,
            paid_premium_factor_amount: factorAmount,
            specified_factor: factor,
            specified_factor_unit:
              factorUnit || "legacy_inferred",
            account_value: formulaAccountValue,
            gross_value_before_offsets: grossValueBeforeOffsets,
            gross_value_before_funeral_cap:
              grossValueBeforeFuneralCap,
            protected_amount: Math.max(
              grossValueBeforeFuneralCap -
                formulaAccountValue,
              0,
            ),
            capped_protected_amount: protectedAmount,
            funeral_benefit_limit: remainingFuneralLimit,
            funeral_excess_insurance_cost_refund_status:
              funeralExcessRefundStatus,
            funeral_excess_insurance_cost_refund_amount:
              funeralExcessRefundAmount,
            policy_loan_and_interest_amount:
              policyLoanAndInterestAmount,
            unpaid_policy_charge_amount: unpaidPolicyChargeAmount,
            remittance_fee_amount: remittanceFeeAmount,
            policy_effect_status_at_event: contractStatus,
            claim_time_status: claimTimeStatus,
            benefit_exclusion_status: exclusionStatus,
            total_disability_qualification_status:
              requiresDisabilityQualification
                ? disabilityQualificationStatus
                : undefined,
            current_benefit_amount_status:
              currentBenefitAmountStatus,
            current_death_disability_benefit_amount:
              usesCurrentBenefitAmount
                ? currentBenefitAmount
                : undefined,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "account_value_annuity_factor") {
      const annuityAmount = policyStateMoney(item, "annuity_payment_amount");
      if (annuityAmount) {
        return {
          ...result,
          value: annuityAmount,
          reference_amount: accountValue || annuityAmount,
          state: "policy_state_value",
          policy_state_key: "annuity_payment_amount",
        };
      }
      return accountValue
        ? {
            ...result,
            reference_amount: accountValue,
            state: "needs_annuity_factor",
            required_fields: ["annuity_payment_amount"],
          }
        : { ...result, state: "needs_account_value", required_fields: ["policy_account_value", "annuity_payment_amount"] };
    }
    if (
      normalizedEntry.calculation_basis ===
      "annuity_amount_or_lump_sum"
    ) {
      const requiredFields = [
        "annuity_payment_amount",
        "annuity_start_policy_account_value",
      ];
      const annuityAmount = policyStateMoney(
        item,
        "annuity_payment_amount",
      );
      const annuityStartAccountValue = policyStateMoney(
        item,
        "annuity_start_policy_account_value",
      );
      if (!annuityAmount || !annuityStartAccountValue) {
        return needsPolicyStateResult(
          result,
          item,
          requiredFields,
        );
      }
      const minimumAnnualAnnuity =
        normalizedEntry.minimum_annual_annuity_amount;
      if (
        minimumAnnualAnnuity &&
        annuityAmount < minimumAnnualAnnuity
      ) {
        return {
          ...result,
          value: annuityStartAccountValue,
          reference_amount: annuityStartAccountValue,
          state: "account_value_return",
          policy_state_key: "annuity_start_policy_account_value",
          formula_type: "low_annual_annuity_lump_sum",
          annual_annuity_amount: annuityAmount,
          minimum_annual_annuity_amount: minimumAnnualAnnuity,
          maximum_annual_annuity_amount:
            normalizedEntry.maximum_annual_annuity_amount,
        };
      }
      return {
        ...result,
        value: annuityAmount,
        reference_amount: annuityAmount,
        state: "policy_state_value",
        policy_state_key: "annuity_payment_amount",
        formula_type: "insurer_quoted_annual_annuity",
        annual_annuity_amount: annuityAmount,
        annuity_start_policy_account_value:
          annuityStartAccountValue,
        minimum_annual_annuity_amount: minimumAnnualAnnuity,
        maximum_annual_annuity_amount:
          normalizedEntry.maximum_annual_annuity_amount,
      };
    }

    if (normalizedEntry.calculation_basis === "policy_state_amount") {
      const [policyStateKey] = normalizedEntry.policy_state_keys;
      const recordedAmount = policyStateKey
        ? policyStateAmount(item, policyStateKey)
        : null;
      if (recordedAmount === null) {
        return needsPolicyStateResult(
            result,
            item,
            normalizedEntry.policy_state_keys,
          );
      }
      const quantity = normalizedEntry.quantity_state_key
        ? policyStateInteger(item, normalizedEntry.quantity_state_key)
        : null;
      if (
        normalizedEntry.quantity_state_key &&
        quantity === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_state_key],
        );
      }
      const policyQuantityCap = normalizedEntry.quantity_cap_state_key
        ? policyStateInteger(
            item,
            normalizedEntry.quantity_cap_state_key,
          )
        : null;
      if (
        normalizedEntry.quantity_cap_state_key &&
        policyQuantityCap === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_cap_state_key],
        );
      }
      const eligibleQuantity =
        normalizedEntry.quantity_state_key
          ? Math.min(
              quantity,
              normalizedEntry.quantity_cap ||
                Number.MAX_SAFE_INTEGER,
              policyQuantityCap ||
                Number.MAX_SAFE_INTEGER,
            )
          : null;
      const quantityAdjustedValue =
        eligibleQuantity === null
          ? recordedAmount
          : eligibleQuantity === 0
            ? 0
            : safeIntegerProduct(
                recordedAmount,
                eligibleQuantity,
              );
      const appliedRate = normalizedEntry.rate_condition_state_key
        ? entryConditionalRate(normalizedEntry, item)
        : normalizedEntry.rate || 1;
      const value = Number.isSafeInteger(quantityAdjustedValue)
        ? Math.trunc(quantityAdjustedValue * appliedRate)
        : null;
      return Number.isSafeInteger(value)
        ? {
            ...result,
            value,
            reference_amount: recordedAmount,
            state: "policy_state_value",
            policy_state_key: policyStateKey,
            quantity_state_key:
              normalizedEntry.quantity_state_key || undefined,
            quantity:
              normalizedEntry.quantity_state_key
                ? quantity
                : undefined,
            eligible_quantity:
              normalizedEntry.quantity_state_key
                ? eligibleQuantity
                : undefined,
            quantity_cap:
              normalizedEntry.quantity_cap ||
              policyQuantityCap ||
              undefined,
            quantity_cap_state_key:
              normalizedEntry.quantity_cap_state_key ||
              undefined,
            unit_value:
              normalizedEntry.quantity_state_key
                ? recordedAmount
                : undefined,
            applied_rate: appliedRate,
            gross_value: value,
          }
        : { ...result, state: "amount_overflow" };
    }

    if (normalizedEntry.calculation_basis === "sum_policy_state_amounts") {
      const missingKeys = normalizedEntry.policy_state_keys.filter(
        (key) => policyStateAmount(item, key) === null,
      );
      if (missingKeys.length) {
        return needsPolicyStateResult(result, item, missingKeys);
      }
      const components = normalizedEntry.policy_state_keys.map((key) => ({
        key,
        value: policyStateAmount(item, key),
      }));
      const value = components.reduce(
        (sum, component) => sum + component.value,
        0,
      );
      return Number.isSafeInteger(value) && value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: value,
            state: "policy_state_value",
            components,
          }
        : { ...result, state: "amount_overflow" };
    }

    if (
      normalizedEntry.calculation_basis ===
      "target_premium_count_value_addition"
    ) {
      const requiredFields = normalizedEntry.policy_state_keys;
      const cumulativeCount = policyStateInteger(
        item,
        "target_premium_cumulative_count",
      );
      const newCount = policyStateInteger(
        item,
        "target_premium_new_count",
      );
      const cumulativePaidTotal = policyStateMoney(
        item,
        "cumulative_paid_target_premium_total",
      );
      const qualificationStatus = policyStateChoice(
        item,
        "value_addition_qualification_status",
      );
      if (
        cumulativeCount === null ||
        newCount === null ||
        cumulativePaidTotal === null ||
        !qualificationStatus ||
        newCount > cumulativeCount
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }

      if (qualificationStatus === "ineligible") {
        return {
          ...result,
          value: 0,
          reference_amount: cumulativePaidTotal,
          state: "value_added_account_credit",
          formula_type: "qualification_lost",
          cumulative_count: cumulativeCount,
          new_count: newCount,
          applicable_rate_sum: 0,
        };
      }

      const firstNewCount = cumulativeCount - newCount + 1;
      let applicableRateSum = 0;
      for (
        let paymentCount = firstNewCount;
        paymentCount <= cumulativeCount;
        paymentCount += 1
      ) {
        if (paymentCount >= 25 && paymentCount <= 60) {
          applicableRateSum += 0.1;
        } else if (paymentCount >= 61 && paymentCount <= 72) {
          applicableRateSum += 0.15;
        } else if (paymentCount >= 73 && paymentCount <= 84) {
          applicableRateSum += 0.3;
        }
      }
      const averageTargetPremium =
        cumulativePaidTotal / cumulativeCount;
      const value = Math.round(
        averageTargetPremium * applicableRateSum,
      );
      return Number.isSafeInteger(value) && value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: cumulativePaidTotal,
            state: "value_added_account_credit",
            formula_type: "target_premium_count_rate_sum",
            cumulative_count: cumulativeCount,
            new_count: newCount,
            first_new_count: firstNewCount,
            average_target_premium: averageTargetPremium,
            applicable_rate_sum: applicableRateSum,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      normalizedEntry.calculation_basis ===
      "installment_premium_value_addition"
    ) {
      const requiredFields = normalizedEntry.policy_state_keys;
      const frequency = policyStateChoice(
        item,
        "installment_premium_frequency",
      );
      const previousCount = policyStateInteger(
        item,
        "previous_installment_premium_cumulative_count",
      );
      const currentCount = policyStateInteger(
        item,
        "current_installment_premium_cumulative_count",
      );
      const previousAverage = policyStateNonNegativeMoney(
        item,
        "previous_installment_premium_average_amount",
      );
      const qualificationStatus = policyStateChoice(
        item,
        "value_addition_qualification_status",
      );
      if (
        !frequency ||
        previousCount === null ||
        currentCount === null ||
        previousAverage === null ||
        !qualificationStatus ||
        currentCount < previousCount
      ) {
        return needsPolicyStateResult(result, item, requiredFields);
      }
      if (qualificationStatus === "ineligible") {
        return {
          ...result,
          value: 0,
          reference_amount: previousAverage,
          state: "value_added_account_credit",
          formula_type: "qualification_lost",
          payment_frequency: frequency,
          previous_count: previousCount,
          current_count: currentCount,
          previous_average_installment_premium: previousAverage,
          applicable_rate_sum: 0,
        };
      }

      const rateForCount = (count) =>
        count >= 121 ? 0.02 : count >= 61 ? 0.01 : 0;
      let applicableRateSum = 0;
      let formulaType = "";
      if (frequency === "monthly") {
        applicableRateSum = rateForCount(currentCount);
        formulaType = "monthly_current_count_rate";
      } else if (previousCount < 61 && currentCount >= 61) {
        const onePercentCount = Math.min(currentCount, 120) - 60;
        const twoPercentCount = Math.max(currentCount - 120, 0);
        applicableRateSum =
          Math.max(onePercentCount, 0) * 0.01 +
          twoPercentCount * 0.02;
        formulaType = "annual_first_crossing_61";
      } else if (previousCount < 121 && currentCount >= 121) {
        applicableRateSum =
          Math.max(120 - previousCount, 0) * 0.01 +
          Math.max(currentCount - 120, 0) * 0.02;
        formulaType = "annual_first_crossing_121";
      } else {
        applicableRateSum =
          (currentCount - previousCount) * rateForCount(currentCount);
        formulaType = "annual_same_band";
      }
      const value = Math.round(previousAverage * applicableRateSum);
      return Number.isSafeInteger(value) && value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: previousAverage,
            state: "value_added_account_credit",
            formula_type: formulaType,
            payment_frequency: frequency,
            previous_count: previousCount,
            current_count: currentCount,
            previous_average_installment_premium: previousAverage,
            applicable_rate_sum: applicableRateSum,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      [
        "policy_year_average_target_premium_account_value_addition",
        "policy_year_average_basic_premium_account_value_addition",
      ].includes(normalizedEntry.calculation_basis)
    ) {
      const contractStatus = policyStateChoice(
        item,
        "policy_effect_status_at_event",
      );
      const policyYear = policyStateInteger(item, "policy_year");
      if (!contractStatus || policyYear === null) {
        return needsPolicyStateResult(result, item, [
          "policy_effect_status_at_event",
          "policy_year",
        ]);
      }
      if (contractStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
          policy_effect_status_at_event: contractStatus,
          policy_year: policyYear,
        };
      }
      if (policyYear < 6) {
        return {
          ...result,
          value: 0,
          reference_amount: 0,
          state: "value_added_account_credit",
          formula_type: "before_value_addition_start_year",
          policy_year: policyYear,
          applicable_rate: 0,
        };
      }
      const averageAccountValueStateKey =
        normalizedEntry.calculation_basis ===
        "policy_year_average_basic_premium_account_value_addition"
          ? "average_basic_premium_account_value"
          : "average_target_premium_account_value";
      const averageAccountValue = policyStateNonNegativeMoney(
        item,
        averageAccountValueStateKey,
      );
      if (averageAccountValue === null) {
        return needsPolicyStateResult(result, item, [
          averageAccountValueStateKey,
        ]);
      }
      const applicableRate =
        policyYear >= 16 ? 0.004 : policyYear >= 11 ? 0.003 : 0.002;
      const value = Math.round(averageAccountValue * applicableRate);
      return Number.isSafeInteger(value) && value <= MAX_MONEY_AMOUNT
        ? {
            ...result,
            value,
            reference_amount: averageAccountValue,
            state: "value_added_account_credit",
            formula_type: "policy_year_average_account_value_rate",
            policy_year: policyYear,
            [averageAccountValueStateKey]: averageAccountValue,
            applicable_rate: applicableRate,
          }
        : { ...result, state: "amount_overflow" };
    }

    const entryText = entryPolicyStateText(normalizedEntry);
    if (isValueSharingBonusEntry(normalizedEntry, entryText)) {
      const reserve = policyStateMoney(item, "previous_policy_reserve_value");
      const declaredRate = policyStateRate(item, "declared_interest_rate_percent");
      const scheduledRate = policyStateRate(item, "scheduled_interest_rate_percent");
      if (reserve && declaredRate !== null && scheduledRate !== null) {
        const rateSpread = Math.max(0, declaredRate - scheduledRate);
        return {
          ...result,
          value: Math.round(reserve * rateSpread),
          reference_amount: reserve,
          state: "value_sharing_bonus",
          rate_spread: rateSpread,
          declared_rate: declaredRate,
          scheduled_rate: scheduledRate,
        };
      }
      return needsPolicyStateResult(result, item, [
        "previous_policy_reserve_value",
        "declared_interest_rate_percent",
        "scheduled_interest_rate_percent",
      ]);
    }

    if (
      normalizedEntry.calculation_basis ===
      "death_or_funeral_fixed_amount"
    ) {
      if (!amount) {
        return { ...result, state: "missing_amount" };
      }
      const status = policyStateChoice(item, "death_benefit_status");
      if (!status) {
        return needsPolicyStateResult(result, item, [
          "death_benefit_status",
        ]);
      }
      if (status === "funeral_limited") {
        const remainingLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (remainingLimit === null) {
          return needsPolicyStateResult(result, item, [
            "remaining_funeral_benefit_limit",
          ]);
        }
        const cappedProtectedAmount = Math.min(amount, remainingLimit);
        return {
          ...result,
          value: cappedProtectedAmount,
          reference_amount: amount,
          state: "death_or_funeral_amount",
          formula_type: "fixed_amount_funeral_cap",
          gross_value_before_funeral_cap: amount,
          protected_amount: amount,
          capped_protected_amount: cappedProtectedAmount,
          funeral_benefit_limit: remainingLimit,
        };
      }
      return {
        ...result,
        value: amount,
        reference_amount: amount,
        state: "death_or_funeral_amount",
        formula_type: "fixed_amount_standard_death",
        gross_value_before_funeral_cap: amount,
        protected_amount: amount,
      };
    }

    if (
      normalizedEntry.calculation_basis ===
        "death_or_funeral_face_amount" ||
      normalizedEntry.calculation_basis ===
        "death_or_funeral_percentage_of_face_amount" ||
      normalizedEntry.calculation_basis ===
        "death_or_funeral_multiplier_of_face_amount"
    ) {
      if (!faceAmount) {
        return { ...result, state: "needs_face_amount" };
      }
      const isPercentage =
        normalizedEntry.calculation_basis ===
        "death_or_funeral_percentage_of_face_amount";
      const isMultiplier =
        normalizedEntry.calculation_basis ===
        "death_or_funeral_multiplier_of_face_amount";
      if (isPercentage && !normalizedEntry.rate) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "needs_rate_table",
        };
      }
      if (isMultiplier && !normalizedEntry.multiplier) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "needs_multiplier_table",
        };
      }
      const appliedFactor = isPercentage
        ? normalizedEntry.rate
        : isMultiplier
          ? normalizedEntry.multiplier
          : 1;
      const grossValue = Math.trunc(faceAmount * appliedFactor);
      if (!Number.isSafeInteger(grossValue)) {
        return { ...result, state: "amount_overflow" };
      }
      const status = policyStateChoice(item, "death_benefit_status");
      if (!status) {
        return needsPolicyStateResult(result, item, [
          "death_benefit_status",
        ]);
      }
      const adjustedPayout = adjustedEntryPayout(
        normalizedEntry,
        item,
        grossValue,
      );
      if (adjustedPayout.state === "needs_policy_state") {
        return {
          ...result,
          ...adjustedPayout,
        };
      }
      if (adjustedPayout.state === "amount_overflow") {
        return { ...result, state: "amount_overflow" };
      }
      const remainingSameAccidentAmount = adjustedPayout.value;
      if (status === "funeral_limited") {
        const remainingLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (remainingLimit === null) {
          return needsPolicyStateResult(result, item, [
            "remaining_funeral_benefit_limit",
          ]);
        }
        const cappedProtectedAmount = Math.min(
          remainingSameAccidentAmount,
          remainingLimit,
        );
        return {
          ...result,
          value: cappedProtectedAmount,
          reference_amount: faceAmount,
          state: "death_or_funeral_amount",
          formula_type: isPercentage
            ? "face_amount_percentage_funeral_cap"
            : isMultiplier
              ? "face_amount_multiplier_funeral_cap"
            : "face_amount_funeral_cap",
          gross_value_before_funeral_cap: grossValue,
          protected_amount: remainingSameAccidentAmount,
          capped_protected_amount: cappedProtectedAmount,
          funeral_benefit_limit: remainingLimit,
          face_amount: faceAmount,
          applied_rate: isPercentage
            ? normalizedEntry.rate
            : 1,
          applied_multiplier: isMultiplier
            ? normalizedEntry.multiplier
            : undefined,
          same_accident_prior_paid_amount:
            adjustedPayout.cumulative_paid_amount,
          remaining_same_accident_amount:
            remainingSameAccidentAmount,
        };
      }
      return {
        ...result,
        value: remainingSameAccidentAmount,
        reference_amount: faceAmount,
        state: "death_or_funeral_amount",
        formula_type: isPercentage
          ? "face_amount_percentage_standard_death"
          : isMultiplier
            ? "face_amount_multiplier_standard_death"
          : "face_amount_standard_death",
        gross_value_before_funeral_cap: grossValue,
        protected_amount: remainingSameAccidentAmount,
        face_amount: faceAmount,
        applied_rate: isPercentage
          ? normalizedEntry.rate
          : 1,
        applied_multiplier: isMultiplier
          ? normalizedEntry.multiplier
          : undefined,
        same_accident_prior_paid_amount:
          adjustedPayout.cumulative_paid_amount,
        remaining_same_accident_amount:
          remainingSameAccidentAmount,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "death_or_funeral_percentage_of_policy_state_amount"
    ) {
      const policyBase = policyStateBaseForEntry(
        normalizedEntry,
        item,
      );
      if (policyBase.value === null) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.unit_key, ...policyFieldKeys],
        );
      }
      if (!normalizedEntry.rate) {
        return {
          ...result,
          reference_amount: policyBase.value,
          state: "needs_rate_table",
        };
      }
      const grossValue = Math.trunc(
        policyBase.value * normalizedEntry.rate,
      );
      if (!Number.isSafeInteger(grossValue)) {
        return { ...result, state: "amount_overflow" };
      }
      const status = policyStateChoice(
        item,
        "death_benefit_status",
      );
      if (!status) {
        return needsPolicyStateResult(result, item, [
          "death_benefit_status",
        ]);
      }
      const adjustedPayout = adjustedEntryPayout(
        normalizedEntry,
        item,
        grossValue,
      );
      if (adjustedPayout.state === "needs_policy_state") {
        return {
          ...result,
          ...adjustedPayout,
        };
      }
      if (adjustedPayout.state === "amount_overflow") {
        return { ...result, state: "amount_overflow" };
      }
      const protectedAmount = adjustedPayout.value;
      if (status === "funeral_limited") {
        const remainingLimit = policyStateNonNegativeMoney(
          item,
          "remaining_funeral_benefit_limit",
        );
        if (remainingLimit === null) {
          return needsPolicyStateResult(result, item, [
            "remaining_funeral_benefit_limit",
          ]);
        }
        return {
          ...result,
          value: Math.min(protectedAmount, remainingLimit),
          reference_amount: policyBase.value,
          state: "death_or_funeral_amount",
          formula_type: "policy_state_percentage_funeral_cap",
          policy_state_key: policyBase.key,
          gross_value_before_funeral_cap: grossValue,
          protected_amount: protectedAmount,
          capped_protected_amount: Math.min(
            protectedAmount,
            remainingLimit,
          ),
          funeral_benefit_limit: remainingLimit,
          applied_rate: normalizedEntry.rate,
          cumulative_paid_amount:
            adjustedPayout.cumulative_paid_amount,
        };
      }
      return {
        ...result,
        value: protectedAmount,
        reference_amount: policyBase.value,
        state: "death_or_funeral_amount",
        formula_type: "policy_state_percentage_standard_death",
        policy_state_key: policyBase.key,
        gross_value_before_funeral_cap: grossValue,
        protected_amount: protectedAmount,
        applied_rate: normalizedEntry.rate,
        cumulative_paid_amount:
          adjustedPayout.cumulative_paid_amount,
      };
    }

    if (
      normalizedEntry.calculation_basis === "greater_of" ||
      normalizedEntry.calculation_basis === "death_or_funeral_greater_of"
    ) {
      if (normalizedEntry.policy_state_keys.length) {
        const offsetKeys = [
          "policy_loan_and_interest_amount",
          "unpaid_policy_charge_amount",
          "remittance_fee_amount",
        ].filter((key) =>
          normalizedEntry.policy_state_keys.includes(key),
        );
        const controlKeys = new Set([
          "policy_effect_status_at_event",
          "policy_values_converted_to_twd",
          "death_benefit_status",
          "remaining_funeral_benefit_limit",
          ...offsetKeys,
        ]);
        const candidateKeys = normalizedEntry.policy_state_keys.filter(
          (key) => !controlKeys.has(key),
        );
        const requiresContractStatus =
          normalizedEntry.policy_state_keys.includes(
            "policy_effect_status_at_event",
          );
        const contractStatus = requiresContractStatus
          ? policyStateChoice(item, "policy_effect_status_at_event")
          : "active";
        if (requiresContractStatus && !contractStatus) {
          return needsPolicyStateResult(result, item, [
            "policy_effect_status_at_event",
          ]);
        }
        if (contractStatus !== "active") {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason: "contract_not_confirmed_active",
            policy_effect_status_at_event: contractStatus,
          };
        }
        const missingOffsetKeys = offsetKeys.filter(
          (key) => policyStateNonNegativeMoney(item, key) === null,
        );
        if (missingOffsetKeys.length) {
          return needsPolicyStateResult(
            result,
            item,
            missingOffsetKeys,
          );
        }
        const offsetAmounts = Object.fromEntries(
          offsetKeys.map((key) => [
            key,
            policyStateNonNegativeMoney(item, key),
          ]),
        );
        const totalOffsets = safeIntegerSum(
          ...offsetKeys.map((key) => offsetAmounts[key]),
        );
        if (totalOffsets === null) {
          return { ...result, state: "amount_overflow" };
        }
        const minorReturnAge = normalizedEntry.minor_account_value_return_age;
        if (minorReturnAge) {
          const insuredAge = policyStateInteger(item, "insured_age_at_event");
          const accountValueForMinor = policyStateAmount(
            item,
            candidateKeys.find((key) =>
              key.includes("policy_account_value"),
            ) || "policy_account_value",
          );
          if (insuredAge === null || accountValueForMinor === null) {
            return needsPolicyStateResult(result, item, [
              "insured_age_at_event",
              candidateKeys.find((key) =>
                key.includes("policy_account_value"),
              ) || "policy_account_value",
              ...offsetKeys,
            ]);
          }
          if (insuredAge < minorReturnAge) {
            if (totalOffsets > accountValueForMinor) {
              return {
                ...result,
                state: "needs_insurer_confirmation",
                confirmation_reason: "offsets_exceed_gross_benefit",
                gross_value_before_offsets: accountValueForMinor,
                ...offsetAmounts,
              };
            }
            return {
              ...result,
              value: accountValueForMinor - totalOffsets,
              reference_amount: accountValueForMinor,
              state: "account_value_return",
              formula_type: "minor_account_value_return",
              account_value: accountValueForMinor,
              gross_value_before_offsets: accountValueForMinor,
              ...offsetAmounts,
              policy_state_key: "policy_account_value",
              insured_age_at_event: insuredAge,
              policy_effect_status_at_event: contractStatus,
            };
          }
        }

        const missingKeys = candidateKeys.filter(
          (key) => policyStateAmount(item, key) === null,
        );
        if (missingKeys.length) {
          return needsPolicyStateResult(result, item, missingKeys);
        }
        const candidates = candidateKeys.map((key) => ({
          key,
          value: policyStateAmount(item, key),
        }));
        const grossValue = Math.max(
          ...candidates.map((candidate) => candidate.value),
        );
        if (
          normalizedEntry.calculation_basis ===
          "death_or_funeral_greater_of"
        ) {
          const status = policyStateChoice(item, "death_benefit_status");
          if (!status) {
            return needsPolicyStateResult(result, item, [
              "death_benefit_status",
            ]);
          }
          if (status === "funeral_limited") {
            const remainingLimit = policyStateNonNegativeMoney(
              item,
              "remaining_funeral_benefit_limit",
            );
            if (remainingLimit === null) {
              return needsPolicyStateResult(result, item, [
                "remaining_funeral_benefit_limit",
              ]);
            }
            const accountValue =
              candidates.find((candidate) =>
                candidate.key.includes("policy_account_value"),
              )?.value ?? 0;
            const protectedAmount = Math.max(0, grossValue - accountValue);
            const cappedProtectedAmount = Math.min(
              protectedAmount,
              remainingLimit,
            );
            const grossValueBeforeOffsets =
              accountValue + cappedProtectedAmount;
            if (totalOffsets > grossValueBeforeOffsets) {
              return {
                ...result,
                state: "needs_insurer_confirmation",
                confirmation_reason: "offsets_exceed_gross_benefit",
                gross_value_before_offsets: grossValueBeforeOffsets,
                ...offsetAmounts,
              };
            }
            const value = grossValueBeforeOffsets - totalOffsets;
            return {
              ...result,
              value,
              reference_amount: value,
              state: "greater_of",
              formula_type: "funeral_cap_plus_account_value_return",
              candidates,
              gross_value_before_funeral_cap: grossValue,
              protected_amount: protectedAmount,
              capped_protected_amount: cappedProtectedAmount,
              funeral_benefit_limit: remainingLimit,
              account_value_return: accountValue,
              gross_value_before_offsets: grossValueBeforeOffsets,
              ...offsetAmounts,
              policy_effect_status_at_event: contractStatus,
            };
          }
        }
        if (totalOffsets > grossValue) {
          return {
            ...result,
            state: "needs_insurer_confirmation",
            confirmation_reason: "offsets_exceed_gross_benefit",
            gross_value_before_offsets: grossValue,
            ...offsetAmounts,
          };
        }
        const value = grossValue - totalOffsets;
        return {
          ...result,
          value,
          reference_amount: grossValue,
          state: "greater_of",
          candidates,
          gross_value_before_offsets: grossValue,
          ...offsetAmounts,
          policy_effect_status_at_event: contractStatus,
        };
      }

      const candidates = [];
      const currentPolicyAmount = policyStateMoney(item, "current_policy_amount");
      const reserveValue = policyStateMoney(item, "policy_reserve_value");
      const premiumTotal = policyStateMoney(item, "premium_total_amount");
      const surrenderValue = policyStateMoney(item, "cash_surrender_value");
      if (currentPolicyAmount) candidates.push({ key: "current_policy_amount", value: currentPolicyAmount });
      if (reserveValue) candidates.push({ key: "policy_reserve_value", value: reserveValue });
      if (premiumTotal && normalizedEntry.rate) {
        candidates.push({ key: "premium_total_amount", value: Math.trunc(premiumTotal * normalizedEntry.rate), base_value: premiumTotal, rate: normalizedEntry.rate });
      } else if (premiumTotal) {
        candidates.push({ key: "premium_total_amount", value: premiumTotal });
      }
      if (surrenderValue) candidates.push({ key: "cash_surrender_value", value: surrenderValue });
      if (candidates.length) {
        const value = Math.max(...candidates.map((candidate) => candidate.value));
        return { ...result, value, reference_amount: value, state: "greater_of", candidates };
      }
      return policyFieldKeys.length ? needsPolicyStateResult(result, item, policyFieldKeys) : result;
    }
    if (normalizedEntry.calculation_basis === "waiver") {
      const waivedPremium = policyStateMoney(item, "remaining_premium_amount");
      return waivedPremium
        ? {
            ...result,
            value: waivedPremium,
            reference_amount: waivedPremium,
            state: "premium_waiver_effect",
            policy_state_key: "remaining_premium_amount",
          }
        : needsPolicyStateResult(result, item, ["remaining_premium_amount"]);
    }
    if (normalizedEntry.calculation_basis === "aggregate_cap") {
      return amount
        ? { ...result, value: amount, reference_amount: amount, state: "aggregate_cap" }
        : result;
    }

    if (["per_unit", "per_unit_per_day"].includes(normalizedEntry.calculation_basis)) {
      if (!amount || !units) return { ...result, state: "needs_unit_count" };
      const unitValue = safeIntegerProduct(amount, units);
      const quantity = normalizedEntry.quantity_state_key
        ? policyStateInteger(item, normalizedEntry.quantity_state_key)
        : null;
      if (
        normalizedEntry.quantity_state_key &&
        quantity === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_state_key],
        );
      }
      const eligibleQuantity =
        normalizedEntry.quantity_state_key
          ? Math.min(
              quantity,
              normalizedEntry.quantity_cap ||
                Number.MAX_SAFE_INTEGER,
            )
          : null;
      const grossValue = normalizedEntry.quantity_state_key
        ? eligibleQuantity === 0
          ? 0
          : safeIntegerProduct(unitValue, eligibleQuantity)
        : unitValue;
      if (!Number.isSafeInteger(grossValue)) {
        return { ...result, state: "amount_overflow" };
      }
      const payout = adjustedEntryPayout(
        normalizedEntry,
        item,
        grossValue,
      );
      if (payout.state === "needs_policy_state") {
        return needsPolicyStateResult(
          result,
          item,
          payout.required_fields,
        );
      }
      return Number.isSafeInteger(payout.value)
        ? {
            ...result,
            ...payout,
            state:
              normalizedEntry.calculation_basis === "per_unit_per_day" &&
              !normalizedEntry.quantity_state_key
                ? "daily_rate"
                : "calculated",
            quantity,
            eligible_quantity: eligibleQuantity,
            quantity_cap:
              normalizedEntry.quantity_cap || undefined,
            unit_value: unitValue,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      normalizedEntry.calculation_basis === "percentage_of_base" &&
      item?.version_characteristics?.product_family ===
        "chubb-disability-support-addendum" &&
      normalizedEntry.id === "chubb-disability-support-monthly"
    ) {
      const version = item.version_characteristics;
      const policyType = selectedPolicyType(item);
      const requiresPolicyType =
        version.main_contract_amount_basis ===
        "main_contract_type_specific";
      if (
        requiresPolicyType &&
        !["investment", "non_investment"].includes(policyType)
      ) {
        return { ...result, state: "needs_plan" };
      }
      if (!faceAmount) {
        return { ...result, state: "needs_face_amount" };
      }
      const missingFields = missingPolicyStateFields(
        item,
        policyFieldKeys,
      );
      if (missingFields.length) {
        return needsPolicyStateResult(
          result,
          item,
          missingFields,
        );
      }
      const policyEffectStatus = policyStateChoice(
        item,
        "policy_effect_status_at_event",
      );
      if (policyEffectStatus !== "active") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason: "contract_not_confirmed_active",
        };
      }
      const statusAfterWaitingPeriod = policyStateChoice(
        item,
        "disability_status_after_180_days",
      );
      if (statusAfterWaitingPeriod === "uncertain") {
        return {
          ...result,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "disability_status_after_waiting_period_uncertain",
        };
      }
      const insuredAge = policyStateInteger(
        item,
        "insured_age_at_event",
      );
      if (
        insuredAge > Number(version.maximum_eligible_age || 75)
      ) {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          eligibility_reason: "insured_age_above_maximum",
          insured_age_at_event: insuredAge,
          maximum_eligible_age: Number(
            version.maximum_eligible_age || 75,
          ),
        };
      }
      if (statusAfterWaitingPeriod !== "persisting") {
        return {
          ...result,
          value: 0,
          state: "not_eligible",
          eligibility_reason:
            "disability_not_persisting_after_waiting_period",
          waiting_period_days: Number(
            version.eligibility_waiting_days || 180,
          ),
        };
      }
      const grade = policyStateChoice(item, "disability_grade");
      const gradePaymentMonths =
        version.grade_payment_months &&
        typeof version.grade_payment_months === "object"
          ? version.grade_payment_months
          : {};
      const paymentMonths = Number(gradePaymentMonths[grade]);
      const monthlyRate =
        normalizedEntry.rate ||
        Number(version.monthly_rate_percent || 0) / 100;
      const monthlyCap = normalizeMoneyAmount(
        version.combined_monthly_cap_amount,
      );
      const otherMonthlyAmount = policyStateNonNegativeMoney(
        item,
        "other_disability_support_monthly_amount",
      );
      if (
        !Number.isSafeInteger(paymentMonths) ||
        paymentMonths <= 0 ||
        !monthlyRate ||
        !monthlyCap ||
        otherMonthlyAmount === null
      ) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "needs_rate_table",
        };
      }
      const rawMonthlyAmount = faceAmount * monthlyRate;
      if (!Number.isSafeInteger(rawMonthlyAmount)) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "needs_insurer_confirmation",
          confirmation_reason:
            "fractional_monthly_amount_rounding_undefined",
          raw_monthly_amount: rawMonthlyAmount,
        };
      }
      const monthlyAmount = Math.min(rawMonthlyAmount, monthlyCap);
      const combinedMonthlyTotal =
        monthlyAmount + otherMonthlyAmount;
      const marginalMonthlyCapacity = Math.max(
        0,
        monthlyCap - otherMonthlyAmount,
      );
      const allocationState =
        combinedMonthlyTotal > monthlyCap
          ? "needs_insurer_confirmation"
          : "within_combined_cap";
      const scheduledNominalTotal =
        monthlyAmount * paymentMonths;
      if (
        !Number.isSafeInteger(rawMonthlyAmount) ||
        !Number.isSafeInteger(scheduledNominalTotal)
      ) {
        return {
          ...result,
          reference_amount: faceAmount,
          state: "amount_overflow",
        };
      }

      const priorDisabilityStatus = policyStateChoice(
        item,
        "prior_disability_status",
      );
      let payablePaymentMonths = paymentMonths;
      let payableNominalTotal = scheduledNominalTotal;
      if (priorDisabilityStatus === "exists") {
        payablePaymentMonths = policyStateInteger(
          item,
          "insurer_approved_remaining_disability_support_months",
        );
        if (
          payablePaymentMonths === null ||
          payablePaymentMonths > paymentMonths
        ) {
          return needsPolicyStateResult(result, item, [
            "insurer_approved_remaining_disability_support_months",
          ]);
        }
        payableNominalTotal =
          monthlyAmount * payablePaymentMonths;
        if (!Number.isSafeInteger(payableNominalTotal)) {
          return {
            ...result,
            reference_amount: faceAmount,
            state: "amount_overflow",
          };
        }
      }
      return {
        ...result,
        value: monthlyAmount,
        reference_amount: faceAmount,
        state: "calculated",
        formula_type: "disability_support_monthly_schedule",
        policy_type: policyType || "legacy_main_contract",
        face_amount: faceAmount,
        monthly_rate: monthlyRate,
        raw_monthly_amount: rawMonthlyAmount,
        combined_monthly_cap_amount: monthlyCap,
        other_disability_support_monthly_amount:
          otherMonthlyAmount,
        combined_monthly_total: combinedMonthlyTotal,
        marginal_monthly_capacity: marginalMonthlyCapacity,
        allocation_state: allocationState,
        disability_grade: grade,
        payment_months: paymentMonths,
        scheduled_nominal_total: scheduledNominalTotal,
        prior_disability_status: priorDisabilityStatus,
        payable_payment_months: payablePaymentMonths,
        payable_nominal_total: payableNominalTotal,
        waiting_period_days: Number(
          version.eligibility_waiting_days || 180,
        ),
        maximum_eligible_age: Number(
          version.maximum_eligible_age || 75,
        ),
      };
    }
    if (normalizedEntry.calculation_basis === "percentage_of_base") {
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      if (unitBased && amount && !units && !faceAmount) {
        return { ...result, state: "needs_unit_count" };
      }
      const unitBase = unitBased && amount && units ? safeIntegerProduct(amount, units) : null;
      const policyBase = policyStateBaseForEntry(normalizedEntry, item);
      const unitField = POLICY_STATE_FIELDS[
        normalizeText(normalizedEntry.unit_key)
      ];
      const explicitPolicyStateBase =
        unitField &&
        ["money", "non_negative_money"].includes(unitField.type);
      const base = explicitPolicyStateBase
        ? policyBase.value
        : faceAmount || unitBase || amount || policyBase.value;
      if (!base) {
        return policyFieldKeys.length ? needsPolicyStateResult(result, item, policyFieldKeys) : { ...result, state: "needs_face_amount" };
      }
      if (normalizedEntry.rate_state_key) {
        const rateField = policyStateFieldForItem(
          normalizedEntry.rate_state_key,
          item,
        );
        const selectedRate = String(
          policyState(item)[normalizedEntry.rate_state_key] ?? "",
        ).trim();
        if (
          rateField.type === "choice" &&
          !rateField.options.some(
            (option) => String(option.value) === selectedRate,
          )
        ) {
          return needsPolicyStateResult(
            result,
            item,
            [normalizedEntry.rate_state_key],
          );
        }
      }
      const appliedRate = normalizedEntry.rate_state_key
        ? policyStateRate(item, normalizedEntry.rate_state_key)
        : normalizedEntry.rate_condition_state_key
          ? 1
          : normalizedEntry.rate;
      if (
        normalizedEntry.rate_state_key &&
        appliedRate === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.rate_state_key],
        );
      }
      if (
        normalizedEntry.rate_state_key &&
        (
          (
            normalizedEntry.rate_min &&
            appliedRate < normalizedEntry.rate_min
          ) ||
          (
            normalizedEntry.rate_max &&
            appliedRate > normalizedEntry.rate_max
          )
        )
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.rate_state_key],
        );
      }
      if (appliedRate === 0) {
        return {
          ...result,
          value: 0,
          reference_amount: base,
          state: "not_eligible",
          applied_rate: 0,
        };
      }
      if (!appliedRate) return { ...result, reference_amount: base, state: "needs_rate_table" };
      const grossValue = Math.trunc(base * appliedRate);
      if (
        normalizedEntry.cumulative_paid_state_key &&
        normalizedEntry.aggregate_limit_entry_id
      ) {
        const otherBenefitAmount = policyStateNonNegativeMoney(
          item,
          normalizedEntry.cumulative_paid_state_key,
        );
        if (otherBenefitAmount === null) {
          return needsPolicyStateResult(result, item, [
            normalizedEntry.cumulative_paid_state_key,
          ]);
        }
        const aggregateLimitEntry = effectiveCoverageEntries(item).find(
          (candidate) =>
            candidate.id ===
            normalizedEntry.aggregate_limit_entry_id,
        );
        const aggregateLimit = normalizeMoneyAmount(
          aggregateLimitEntry?.amount,
        );
        if (!aggregateLimit) {
          return {
            ...result,
            reference_amount: base,
            state: "needs_rate_table",
          };
        }
        const combinedBenefitAmount = safeIntegerSum(
          grossValue,
          otherBenefitAmount,
        );
        if (combinedBenefitAmount === null) {
          return {
            ...result,
            reference_amount: base,
            state: "amount_overflow",
          };
        }
        const marginalCapacity = Math.max(
          0,
          aggregateLimit - otherBenefitAmount,
        );
        if (
          otherBenefitAmount > 0 &&
          combinedBenefitAmount > aggregateLimit
        ) {
          return {
            ...result,
            reference_amount: base,
            state: "needs_insurer_confirmation",
            confirmation_reason: "aggregate_cap_allocation_required",
            gross_value: grossValue,
            applied_rate: appliedRate,
            aggregate_limit: aggregateLimit,
            other_benefit_amount: otherBenefitAmount,
            combined_benefit_amount: combinedBenefitAmount,
            marginal_capacity: marginalCapacity,
          };
        }
        return {
          ...result,
          reference_amount: base,
          value: Math.min(grossValue, aggregateLimit),
          state: "calculated",
          applied_rate: appliedRate,
          gross_value: grossValue,
          aggregate_limit: aggregateLimit,
          other_benefit_amount: otherBenefitAmount,
          combined_benefit_amount: combinedBenefitAmount,
          marginal_capacity: marginalCapacity,
        };
      }
      const adjustedPayout = adjustedEntryPayout(
        normalizedEntry,
        item,
        grossValue,
      );
      if (adjustedPayout.state === "needs_policy_state") {
        return {
          ...result,
          reference_amount: base,
          ...adjustedPayout,
        };
      }
      if (adjustedPayout.state === "amount_overflow") {
        return {
          ...result,
          reference_amount: base,
          state: "amount_overflow",
        };
      }
      return {
        ...result,
        reference_amount: base,
        value: adjustedPayout.value,
        state: policyBase.value ? "policy_state_percentage" : "calculated",
        policy_state_key: policyBase.key || undefined,
        applied_rate:
          appliedRate * (adjustedPayout.applied_rate ?? 1),
        gross_value: adjustedPayout.gross_value,
        cumulative_paid_amount:
          adjustedPayout.cumulative_paid_amount,
      };
    }
    if (normalizedEntry.calculation_basis === "table_multiplier") {
      const policyBase = policyStateBaseForEntry(normalizedEntry, item);
      const unitBased = ["per_unit", "daily_per_unit"].includes(
        normalizedEntry.basis,
      );
      if (unitBased && !units) {
        return { ...result, state: "needs_unit_count" };
      }
      const unitBase = unitBased
        ? safeIntegerProduct(amount, units)
        : null;
      const base = faceAmount || unitBase || amount || policyBase.value;
      if (!base) {
        return policyFieldKeys.length ? needsPolicyStateResult(result, item, policyFieldKeys) : { ...result, state: "needs_face_amount" };
      }
      const selectedMultiplier = normalizedEntry.multiplier_state_key
        ? POLICY_STATE_FIELDS[
            normalizedEntry.multiplier_state_key
          ]?.type === "rate"
          ? policyStateRate(
              item,
              normalizedEntry.multiplier_state_key,
            )
          : POLICY_STATE_FIELDS[
                normalizedEntry.multiplier_state_key
              ]?.type === "number"
            ? policyStateNumber(
                item,
                normalizedEntry.multiplier_state_key,
              )
            : policyStateInteger(
                item,
                normalizedEntry.multiplier_state_key,
              )
        : normalizedEntry.multiplier;
      if (
        normalizedEntry.multiplier_state_key &&
        selectedMultiplier === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.multiplier_state_key,
        ]);
      }
      if (!selectedMultiplier) return { ...result, reference_amount: base, state: "needs_multiplier_table" };
      const paidMultiplier = normalizedEntry.cumulative_paid_multiplier_state_key
        ? policyStateNumber(
            item,
            normalizedEntry.cumulative_paid_multiplier_state_key,
          )
        : 0;
      if (
        normalizedEntry.cumulative_paid_multiplier_state_key &&
        paidMultiplier === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.cumulative_paid_multiplier_state_key,
        ]);
      }
      if (
        normalizedEntry.minimum_multiplier &&
        selectedMultiplier < normalizedEntry.minimum_multiplier
      ) {
        return {
          ...result,
          value: 0,
          reference_amount: base,
          state: "not_eligible",
          multiplier_state_key:
            normalizedEntry.multiplier_state_key || undefined,
          multiplier: selectedMultiplier,
          minimum_multiplier: normalizedEntry.minimum_multiplier,
        };
      }
      const appliedMultiplier = Math.max(
        0,
        selectedMultiplier - paidMultiplier,
      );
      const quantity = normalizedEntry.quantity_state_key
        ? policyStateInteger(item, normalizedEntry.quantity_state_key)
        : 1;
      if (
        normalizedEntry.quantity_state_key &&
        quantity === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.quantity_state_key,
        ]);
      }
      const policyQuantityCap = normalizedEntry.quantity_cap_state_key
        ? policyStateInteger(
            item,
            normalizedEntry.quantity_cap_state_key,
          )
        : null;
      if (
        normalizedEntry.quantity_cap_state_key &&
        policyQuantityCap === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.quantity_cap_state_key,
        ]);
      }
      const eligibleQuantity = normalizedEntry.quantity_state_key
        ? Math.min(
            quantity,
            normalizedEntry.quantity_cap ||
              Number.MAX_SAFE_INTEGER,
            policyQuantityCap || Number.MAX_SAFE_INTEGER,
          )
        : 1;
      const multipliedValue = Math.trunc(base * appliedMultiplier);
      const quantityAdjustedValue =
        Number.isSafeInteger(multipliedValue) && multipliedValue >= 0
          ? Math.trunc(multipliedValue * eligibleQuantity)
          : null;
      if (normalizedEntry.rate_state_key) {
        const rateField = policyStateFieldForItem(
          normalizedEntry.rate_state_key,
          item,
        );
        const selectedRate = String(
          policyState(item)[normalizedEntry.rate_state_key] ?? "",
        ).trim();
        if (
          rateField.type === "choice" &&
          !rateField.options.some(
            (option) => String(option.value) === selectedRate,
          )
        ) {
          return needsPolicyStateResult(result, item, [
            normalizedEntry.rate_state_key,
          ]);
        }
      }
      const appliedRate = normalizedEntry.rate_state_key
        ? policyStateRate(item, normalizedEntry.rate_state_key)
        : normalizedEntry.rate || 1;
      if (
        normalizedEntry.rate_state_key &&
        (
          appliedRate === null ||
          (
            normalizedEntry.rate_min &&
            appliedRate < normalizedEntry.rate_min
          ) ||
          (
            normalizedEntry.rate_max &&
            appliedRate > normalizedEntry.rate_max
          )
        )
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.rate_state_key,
        ]);
      }
      const grossValue = Number.isSafeInteger(quantityAdjustedValue)
        ? Math.trunc(quantityAdjustedValue * appliedRate)
        : null;
      if (!Number.isSafeInteger(grossValue)) {
        return { ...result, reference_amount: base, state: "amount_overflow" };
      }
      const payout = adjustedEntryPayout(
        normalizedEntry,
        item,
        grossValue,
      );
      if (payout.state === "needs_policy_state") {
        return needsPolicyStateResult(
          result,
          item,
          payout.required_fields,
        );
      }
      return Number.isSafeInteger(payout.value)
        ? {
            ...result,
            ...payout,
            reference_amount: base,
            state: normalizedEntry.multiplier_state_key
              ? "policy_state_multiplier"
              : policyBase.value
                ? "policy_state_percentage"
                : "calculated",
            policy_state_key:
              policyBase.key ||
              undefined,
            multiplier_state_key:
              normalizedEntry.multiplier_state_key || undefined,
            multiplier: selectedMultiplier,
            applied_multiplier: appliedMultiplier,
            cumulative_paid_multiplier:
              normalizedEntry.cumulative_paid_multiplier_state_key
                ? paidMultiplier
                : undefined,
            quantity_state_key:
              normalizedEntry.quantity_state_key || undefined,
            quantity:
              normalizedEntry.quantity_state_key
                ? quantity
                : undefined,
            eligible_quantity:
              normalizedEntry.quantity_state_key
                ? eligibleQuantity
                : undefined,
            quantity_cap:
              normalizedEntry.quantity_cap ||
              policyQuantityCap ||
              undefined,
            quantity_cap_state_key:
              normalizedEntry.quantity_cap_state_key || undefined,
            applied_rate: appliedRate,
          }
        : { ...result, reference_amount: base, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "tiered_or_stepped") {
      if (!normalizedEntry.amount_tiers.length) return result;
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      const policyDailyBased =
        normalizedEntry.basis === "hospital_daily_amount";
      const faceAmountBased =
        normalizedEntry.basis === "face_amount";
      const policyDailyAmount = policyDailyBased
        ? policyStateMoney(item, "hospital_daily_amount")
        : null;
      if (policyDailyBased && policyDailyAmount === null) {
        return needsPolicyStateResult(
          result,
          item,
          ["hospital_daily_amount"],
        );
      }
      const usesWenxinNoClaimFactor =
        normalizedEntry.rate_state_key ===
        "taiwan_wenxin_no_claim_factor_percent";
      const appliedRate = usesWenxinNoClaimFactor
        ? policyStateRate(item, normalizedEntry.rate_state_key)
        : 1;
      if (
        usesWenxinNoClaimFactor &&
        (
          appliedRate === null ||
          (
            normalizedEntry.rate_min &&
            appliedRate < normalizedEntry.rate_min
          ) ||
          (
            normalizedEntry.rate_max &&
            appliedRate > normalizedEntry.rate_max
          )
        )
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.rate_state_key,
        ]);
      }
      const tierReferenceAmount = (tier) => {
        let rawTierAmount = null;
        if (faceAmountBased) {
          if (!faceAmount || !tier.multiplier) return null;
          rawTierAmount = Math.trunc(
            faceAmount * tier.multiplier,
          );
        } else if (policyDailyBased) {
          rawTierAmount = Math.trunc(
            policyDailyAmount * tier.multiplier,
          );
        } else {
          rawTierAmount = unitBased
            ? safeIntegerProduct(tier.amount, units)
            : tier.amount;
        }
        if (!Number.isSafeInteger(rawTierAmount) || rawTierAmount <= 0) {
          return null;
        }
        const adjustedTierAmount = Math.trunc(
          rawTierAmount * appliedRate,
        );
        return Number.isSafeInteger(adjustedTierAmount) &&
          adjustedTierAmount > 0
          ? adjustedTierAmount
          : null;
      };
      if (normalizedEntry.tier_selection_state_key) {
        const selectedTierValue = policyStateInteger(
          item,
          normalizedEntry.tier_selection_state_key,
        );
        if (selectedTierValue === null) {
          return needsPolicyStateResult(
            result,
            item,
            [normalizedEntry.tier_selection_state_key],
          );
        }
        if (unitBased && !units) {
          return { ...result, state: "needs_unit_count" };
        }
        const selectedTier = normalizedEntry.amount_tiers.find(
          (tier) =>
            selectedTierValue >= tier.min_quantity &&
            (
              tier.max_quantity === null ||
              selectedTierValue <= tier.max_quantity
            ),
        );
        if (!selectedTier) {
          return { ...result, state: "needs_tier_table" };
        }
        const grossValue = tierReferenceAmount(selectedTier);
        if (!Number.isSafeInteger(grossValue)) {
          return { ...result, state: "amount_overflow" };
        }
        const payout = adjustedEntryPayout(
          normalizedEntry,
          item,
          grossValue,
        );
        if (payout.state === "needs_policy_state") {
          return needsPolicyStateResult(
            result,
            item,
            payout.required_fields,
          );
        }
        return Number.isSafeInteger(payout.value)
          ? {
              ...result,
              ...payout,
              state: "calculated",
              selected_tier: selectedTier,
              tier_selection_value: selectedTierValue,
              tier_selection_state_key:
                normalizedEntry.tier_selection_state_key,
              reference_amount: faceAmountBased
                ? faceAmount
                : grossValue,
              multiplier: selectedTier.multiplier,
              applied_rate: appliedRate,
            }
          : { ...result, state: "amount_overflow" };
      }
      const quantity = normalizedEntry.quantity_state_key
        ? policyStateInteger(item, normalizedEntry.quantity_state_key)
        : null;
      if (
        normalizedEntry.quantity_state_key &&
        quantity === null
      ) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_state_key],
        );
      }
      const hasQuantityBounds = normalizedEntry.amount_tiers.every(
        (tier) => tier.min_quantity,
      );
      if (
        normalizedEntry.quantity_state_key &&
        hasQuantityBounds
      ) {
        if (unitBased && !units) {
          return { ...result, state: "needs_unit_count" };
        }
        const tierValues = normalizedEntry.amount_tiers.map((tier) => {
          const upperBound =
            tier.max_quantity === null
              ? quantity
              : Math.min(quantity, tier.max_quantity);
          const tierQuantity = Math.max(
            0,
            upperBound - tier.min_quantity + 1,
          );
          const amountWithUnits = tierReferenceAmount(tier);
          const value =
            tierQuantity === 0
              ? 0
              : safeIntegerProduct(amountWithUnits, tierQuantity);
          return {
            ...tier,
            quantity: tierQuantity,
            reference_amount: amountWithUnits,
            value,
          };
        });
        if (
          tierValues.some(
            (tier) => !Number.isSafeInteger(tier.value),
          )
        ) {
          return { ...result, state: "amount_overflow", tier_values: tierValues };
        }
        const value = tierValues.reduce(
          (total, tier) => total + tier.value,
          0,
        );
        return Number.isSafeInteger(value)
          ? {
              ...result,
              value,
              state: "calculated",
              quantity,
              tier_values: tierValues,
              applied_rate: appliedRate,
            }
          : { ...result, state: "amount_overflow", tier_values: tierValues };
      }
      const tierValues = normalizedEntry.amount_tiers.map((tier) => ({
        label: tier.label,
        reference_amount: tierReferenceAmount(tier),
        value:
          policyDailyBased ||
          (unitBased && units)
            ? tierReferenceAmount(tier)
            : null,
      }));
      if (unitBased && !units) return { ...result, state: "needs_unit_count", tier_values: tierValues };
      if (tierValues.some((tier) => unitBased && !tier.value)) {
        return { ...result, state: "amount_overflow", tier_values: tierValues };
      }
      return {
        ...result,
        state: "tiered_values",
        tier_values: tierValues,
        applied_rate: appliedRate,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "reimbursement_with_total_and_daily_room_cap"
    ) {
      const totalLimit = policyStateMoney(
        item,
        normalizedEntry.unit_key,
      );
      const actualExpense = policyStateNonNegativeMoney(
        item,
        normalizedEntry.expense_state_key,
      );
      if (totalLimit === null || actualExpense === null) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.unit_key,
          normalizedEntry.expense_state_key,
        ]);
      }
      const eventType = normalizedEntry.eligibility_state_key
        ? policyStateChoice(item, normalizedEntry.eligibility_state_key)
        : "inpatient";
      if (!eventType) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.eligibility_state_key,
        ]);
      }
      if (eventType !== "inpatient") {
        return {
          ...result,
          value: Math.min(totalLimit, actualExpense),
          reference_amount: totalLimit,
          state: "calculated",
          policy_state_key: normalizedEntry.unit_key,
          expense_state_key: normalizedEntry.expense_state_key,
          event_type: eventType,
          eligible_expense: actualExpense,
          total_limit: totalLimit,
        };
      }
      const days = policyStateInteger(
        item,
        normalizedEntry.quantity_state_key,
      );
      const roomMealExpense = policyStateNonNegativeMoney(
        item,
        normalizedEntry.policy_state_keys[0],
      );
      if (days === null || roomMealExpense === null) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.quantity_state_key,
          ...normalizedEntry.policy_state_keys,
        ]);
      }
      if (roomMealExpense > actualExpense) {
        return {
          ...needsPolicyStateResult(result, item, [
            normalizedEntry.expense_state_key,
            ...normalizedEntry.policy_state_keys,
          ]),
          invalid_reason: "room_meal_expense_exceeds_actual_expense",
        };
      }
      const dailyRoomMealLimit = Math.trunc(
        totalLimit * normalizedEntry.rate,
      );
      const roomMealLimit = safeIntegerProduct(
        dailyRoomMealLimit,
        days,
      );
      if (roomMealLimit === null) {
        return { ...result, state: "amount_overflow" };
      }
      const eligibleRoomMealExpense = Math.min(
        roomMealExpense,
        roomMealLimit,
      );
      const eligibleExpense =
        actualExpense - roomMealExpense + eligibleRoomMealExpense;
      if (!Number.isSafeInteger(eligibleExpense) || eligibleExpense < 0) {
        return { ...result, state: "amount_overflow" };
      }
      return {
        ...result,
        value: Math.min(totalLimit, eligibleExpense),
        reference_amount: totalLimit,
        state: "calculated",
        policy_state_key: normalizedEntry.unit_key,
        expense_state_key: normalizedEntry.expense_state_key,
        event_type: eventType,
        hospitalization_days: days,
        actual_expense: actualExpense,
        total_limit: totalLimit,
        daily_room_meal_limit: dailyRoomMealLimit,
        room_meal_limit: roomMealLimit,
        eligible_room_meal_expense: eligibleRoomMealExpense,
        eligible_expense: eligibleExpense,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "reimbursement_with_schedule_and_major_cap"
    ) {
      const ordinaryLimit = policyStateMoney(item, normalizedEntry.unit_key);
      const majorLimit = policyStateMoney(
        item,
        normalizedEntry.secondary_limit_state_key,
      );
      const scheduleRate = policyStateRate(
        item,
        normalizedEntry.rate_state_key,
      );
      const expense = policyStateNonNegativeMoney(
        item,
        normalizedEntry.expense_state_key,
      );
      const missingKeys = [];
      if (ordinaryLimit === null) missingKeys.push(normalizedEntry.unit_key);
      if (majorLimit === null) {
        missingKeys.push(normalizedEntry.secondary_limit_state_key);
      }
      if (scheduleRate === null) missingKeys.push(normalizedEntry.rate_state_key);
      if (expense === null) missingKeys.push(normalizedEntry.expense_state_key);
      if (missingKeys.length) {
        return needsPolicyStateResult(result, item, missingKeys);
      }
      if (
        (normalizedEntry.rate_min && scheduleRate < normalizedEntry.rate_min) ||
        (normalizedEntry.rate_max && scheduleRate > normalizedEntry.rate_max)
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.rate_state_key,
        ]);
      }
      const scheduleLimit = Math.trunc(ordinaryLimit * scheduleRate);
      const threshold = normalizedEntry.rate_threshold || 1;
      const benefitLimit =
        scheduleRate > threshold
          ? Math.min(scheduleLimit, majorLimit)
          : scheduleLimit;
      if (!Number.isSafeInteger(benefitLimit) || benefitLimit <= 0) {
        return { ...result, state: "amount_overflow" };
      }
      let appliedRate = 1;
      if (normalizedEntry.rate_condition_state_key) {
        const selectedCondition = policyStateChoice(
          item,
          normalizedEntry.rate_condition_state_key,
        );
        if (!selectedCondition) {
          return needsPolicyStateResult(result, item, [
            normalizedEntry.rate_condition_state_key,
          ]);
        }
        appliedRate =
          selectedCondition === normalizedEntry.rate_condition_value
            ? normalizedEntry.rate
            : 1;
      }
      if (!appliedRate) return { ...result, state: "needs_rate_table" };
      const eligibleExpense = Math.trunc(expense * appliedRate);
      return {
        ...result,
        value: Math.min(eligibleExpense, benefitLimit),
        reference_amount: benefitLimit,
        state: "calculated",
        expense_amount: expense,
        eligible_expense: eligibleExpense,
        applied_rate: appliedRate,
        schedule_rate: scheduleRate,
        schedule_limit: scheduleLimit,
        ordinary_surgery_limit: ordinaryLimit,
        major_surgery_limit: majorLimit,
        major_surgery_threshold: threshold,
      };
    }
    if (
      normalizedEntry.calculation_basis ===
      "reimbursement_with_greater_of_daily_cap"
    ) {
      const fixedLimit = policyStateMoney(item, normalizedEntry.unit_key);
      const dailyLimit = policyStateNonNegativeMoney(
        item,
        normalizedEntry.secondary_limit_state_key,
      );
      const days = policyStateInteger(
        item,
        normalizedEntry.quantity_state_key,
      );
      const maximumDays = policyStateInteger(
        item,
        normalizedEntry.quantity_cap_state_key,
      );
      const expense = policyStateNonNegativeMoney(
        item,
        normalizedEntry.expense_state_key,
      );
      const missingKeys = [];
      if (fixedLimit === null) missingKeys.push(normalizedEntry.unit_key);
      if (dailyLimit === null) {
        missingKeys.push(normalizedEntry.secondary_limit_state_key);
      }
      if (days === null) missingKeys.push(normalizedEntry.quantity_state_key);
      if (maximumDays === null) {
        missingKeys.push(normalizedEntry.quantity_cap_state_key);
      }
      if (expense === null) missingKeys.push(normalizedEntry.expense_state_key);
      if (missingKeys.length) {
        return needsPolicyStateResult(result, item, missingKeys);
      }
      const eligibleDays = Math.min(days, maximumDays);
      const dailyAggregateLimit = safeIntegerProduct(dailyLimit, eligibleDays);
      if (dailyAggregateLimit === null) {
        return { ...result, state: "amount_overflow" };
      }
      const benefitLimit = Math.max(fixedLimit, dailyAggregateLimit);
      let appliedRate = 1;
      if (normalizedEntry.rate_condition_state_key) {
        const selectedCondition = policyStateChoice(
          item,
          normalizedEntry.rate_condition_state_key,
        );
        if (!selectedCondition) {
          return needsPolicyStateResult(result, item, [
            normalizedEntry.rate_condition_state_key,
          ]);
        }
        appliedRate =
          selectedCondition === normalizedEntry.rate_condition_value
            ? normalizedEntry.rate
            : 1;
      }
      if (!appliedRate) return { ...result, state: "needs_rate_table" };
      const eligibleExpense = Math.trunc(expense * appliedRate);
      return {
        ...result,
        value: Math.min(eligibleExpense, benefitLimit),
        reference_amount: benefitLimit,
        state: "calculated",
        expense_amount: expense,
        eligible_expense: eligibleExpense,
        applied_rate: appliedRate,
        fixed_limit: fixedLimit,
        daily_limit: dailyLimit,
        daily_aggregate_limit: dailyAggregateLimit,
        hospitalization_days: days,
        eligible_days: eligibleDays,
        maximum_days: maximumDays,
      };
    }
    if (
      [
        "reimbursement_with_cap",
        "percentage_of_actual_expense_with_cap",
      ].includes(normalizedEntry.calculation_basis)
    ) {
      const unitBased = ["per_unit", "daily_per_unit"].includes(normalizedEntry.basis);
      if (unitBased && !units) return { ...result, state: "needs_unit_count" };
      const policyRecordedLimit = normalizedEntry.basis === "policy_recorded_limit";
      const limitStateKey =
        policyRecordedLimit &&
        POLICY_STATE_FIELDS[normalizedEntry.unit_key] &&
        ["money", "non_negative_money"].includes(
          POLICY_STATE_FIELDS[normalizedEntry.unit_key].type,
        )
          ? normalizedEntry.unit_key
          : "reimbursement_limit";
      const stateLimit = policyStateMoney(item, limitStateKey);
      let selectedAmountTier = null;
      if (
        normalizedEntry.amount_tiers.length &&
        normalizedEntry.tier_selection_state_key
      ) {
        const tierSelection = policyStateInteger(
          item,
          normalizedEntry.tier_selection_state_key,
        );
        if (tierSelection === null) {
          return needsPolicyStateResult(result, item, [
            normalizedEntry.tier_selection_state_key,
          ]);
        }
        selectedAmountTier = normalizedEntry.amount_tiers.find(
          (tier) =>
            tierSelection >= (tier.min_quantity || 1) &&
            (
              tier.max_quantity === null ||
              tierSelection <= tier.max_quantity
            ),
        ) || null;
        if (!selectedAmountTier) {
          return {
            ...result,
            state: "needs_rate_table",
            tier_selection_state_key:
              normalizedEntry.tier_selection_state_key,
            tier_selection_value: tierSelection,
          };
        }
      }
      const baseLimit = policyRecordedLimit
        ? stateLimit
        : selectedAmountTier
          ? selectedAmountTier.amount
          : amount;
      if (!baseLimit) {
        return policyRecordedLimit
          ? needsPolicyStateResult(result, item, [limitStateKey])
          : result;
      }
      const staticLimitRate = normalizedEntry.limit_rate || 1;
      const policyStateLimitRate = normalizedEntry.limit_rate_state_key
        ? policyStateRate(item, normalizedEntry.limit_rate_state_key)
        : 1;
      if (
        normalizedEntry.limit_rate_state_key &&
        policyStateLimitRate === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.limit_rate_state_key,
        ]);
      }
      const secondaryPolicyStateLimitRate =
        normalizedEntry.secondary_limit_rate_state_key
          ? policyStateRate(
              item,
              normalizedEntry.secondary_limit_rate_state_key,
            )
          : 1;
      if (
        normalizedEntry.secondary_limit_rate_state_key &&
        secondaryPolicyStateLimitRate === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.secondary_limit_rate_state_key,
        ]);
      }
      if (
        normalizedEntry.limit_rate_state_key &&
        (
          (
            normalizedEntry.rate_min &&
            policyStateLimitRate < normalizedEntry.rate_min
          ) ||
          (
            normalizedEntry.rate_max &&
            policyStateLimitRate > normalizedEntry.rate_max
          )
        )
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.limit_rate_state_key,
        ]);
      }
      const adjustedBaseLimit = Math.trunc(
        baseLimit *
          staticLimitRate *
          policyStateLimitRate *
          secondaryPolicyStateLimitRate,
      );
      if (
        !Number.isSafeInteger(adjustedBaseLimit) ||
        adjustedBaseLimit <= 0
      ) {
        return { ...result, state: "amount_overflow" };
      }
      const quantity = normalizedEntry.quantity_state_key
        ? policyStateInteger(item, normalizedEntry.quantity_state_key)
        : null;
      if (
        normalizedEntry.quantity_state_key &&
        quantity === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.quantity_state_key,
        ]);
      }
      const policyQuantityCap = normalizedEntry.quantity_cap_state_key
        ? policyStateInteger(
            item,
            normalizedEntry.quantity_cap_state_key,
          )
        : null;
      if (
        normalizedEntry.quantity_cap_state_key &&
        policyQuantityCap === null
      ) {
        return needsPolicyStateResult(result, item, [
          normalizedEntry.quantity_cap_state_key,
        ]);
      }
      const eligibleQuantity =
        quantity === null
          ? null
          : Math.min(
              quantity,
              normalizedEntry.quantity_cap || Number.MAX_SAFE_INTEGER,
              policyQuantityCap || Number.MAX_SAFE_INTEGER,
            );
      const unitAdjustedLimit = unitBased
        ? safeIntegerProduct(adjustedBaseLimit, units)
        : adjustedBaseLimit;
      const proratedLimit =
        eligibleQuantity !== null &&
        normalizedEntry.limit_proration_threshold &&
        eligibleQuantity > normalizedEntry.limit_proration_threshold
          ? Math.trunc(
              (unitAdjustedLimit * eligibleQuantity) /
                normalizedEntry.limit_proration_threshold,
            )
          : unitAdjustedLimit;
      const value =
        eligibleQuantity === 0
          ? 0
          : normalizedEntry.quantity_state_key
            ? normalizedEntry.limit_proration_threshold
              ? proratedLimit
              : safeIntegerProduct(unitAdjustedLimit, eligibleQuantity)
            : proratedLimit;
      if (value === null) {
        return { ...result, state: "amount_overflow" };
      }
      if (!normalizedEntry.expense_state_key) {
        return {
          ...result,
          value,
          reference_amount: value,
          state: stateLimit ? "policy_state_limit" : "benefit_limit",
          policy_state_key: stateLimit ? limitStateKey : undefined,
          limit_rate: staticLimitRate,
          limit_rate_state_key:
            normalizedEntry.limit_rate_state_key || undefined,
          policy_state_limit_rate: policyStateLimitRate,
          secondary_limit_rate_state_key:
            normalizedEntry.secondary_limit_rate_state_key || undefined,
          secondary_policy_state_limit_rate:
            secondaryPolicyStateLimitRate,
          quantity: quantity === null ? undefined : quantity,
          eligible_quantity:
            eligibleQuantity === null ? undefined : eligibleQuantity,
          quantity_cap: normalizedEntry.quantity_cap || undefined,
          quantity_cap_state_key:
            normalizedEntry.quantity_cap_state_key || undefined,
          policy_quantity_cap: policyQuantityCap || undefined,
          limit_proration_threshold:
            normalizedEntry.limit_proration_threshold || undefined,
        };
      }
      const expense = policyStateNonNegativeMoney(
        item,
        normalizedEntry.expense_state_key,
      );
      if (expense === null) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.expense_state_key],
        );
      }
      let appliedRate =
        normalizedEntry.calculation_basis ===
        "percentage_of_actual_expense_with_cap"
          ? normalizedEntry.rate
          : 1;
      if (normalizedEntry.rate_condition_state_key) {
        const selectedCondition = policyStateChoice(
          item,
          normalizedEntry.rate_condition_state_key,
        );
        if (!selectedCondition) {
          return needsPolicyStateResult(
            result,
            item,
            [normalizedEntry.rate_condition_state_key],
          );
        }
        appliedRate =
          selectedCondition === normalizedEntry.rate_condition_value
            ? normalizedEntry.rate
            : 1;
      }
      if (!appliedRate) return { ...result, state: "needs_rate_table" };
      const eligibleExpense = Math.trunc(expense * appliedRate);
      let remainingAggregateLimit = null;
      if (normalizedEntry.cumulative_paid_state_key) {
        const paidAmount = policyStateNonNegativeMoney(
          item,
          normalizedEntry.cumulative_paid_state_key,
        );
        if (paidAmount === null) {
          return needsPolicyStateResult(
            result,
            item,
            [normalizedEntry.cumulative_paid_state_key],
          );
        }
        const aggregateLimitEntry =
          normalizedEntry.aggregate_limit_entry_id
            ? effectiveCoverageEntries(item).find(
                (candidate) =>
                  candidate.id ===
                  normalizedEntry.aggregate_limit_entry_id,
              )
            : null;
        const aggregateLimit = normalizedEntry.aggregate_limit_entry_id
          ? aggregateLimitEntry?.amount || null
          : value;
        if (aggregateLimit) {
          remainingAggregateLimit = Math.max(0, aggregateLimit - paidAmount);
        }
      }
      const calculatedValue = Math.min(
        eligibleExpense,
        value,
        remainingAggregateLimit === null
          ? Number.MAX_SAFE_INTEGER
          : remainingAggregateLimit,
      );
      return {
        ...result,
        value: calculatedValue,
        reference_amount: value,
        state: "calculated",
        expense_amount: expense,
        applied_rate: appliedRate,
        quantity: quantity === null ? undefined : quantity,
        eligible_quantity:
          eligibleQuantity === null ? undefined : eligibleQuantity,
        quantity_cap: normalizedEntry.quantity_cap || undefined,
        quantity_cap_state_key:
          normalizedEntry.quantity_cap_state_key || undefined,
        policy_quantity_cap: policyQuantityCap || undefined,
        limit_proration_threshold:
          normalizedEntry.limit_proration_threshold || undefined,
        eligible_expense: eligibleExpense,
        remaining_aggregate_limit: remainingAggregateLimit,
        secondary_limit_rate_state_key:
          normalizedEntry.secondary_limit_rate_state_key || undefined,
        secondary_policy_state_limit_rate:
          secondaryPolicyStateLimitRate,
        selected_amount_tier: selectedAmountTier
          ? {
              label: selectedAmountTier.label,
              amount: selectedAmountTier.amount,
            }
          : undefined,
        tier_selection_state_key: selectedAmountTier
          ? normalizedEntry.tier_selection_state_key
          : undefined,
      };
    }
    if (normalizedEntry.calculation_basis === "unknown") {
      if (normalizedEntry.basis === "hospital_daily_amount") {
        const dailyAmount = policyStateMoney(item, "hospital_daily_amount");
        if (!dailyAmount) return needsPolicyStateResult(result, item, ["hospital_daily_amount"]);
        const multiplier = normalizedEntry.multiplier || 1;
        const base = Math.round(dailyAmount * multiplier);
        if (normalizedEntry.rate || normalizedEntry.rate_min || normalizedEntry.rate_max) {
          const exactRateValue = normalizedEntry.rate ? Math.round(base * normalizedEntry.rate) : null;
          return {
            ...result,
            value: exactRateValue,
            reference_amount: base,
            state: exactRateValue ? "policy_state_percentage" : "policy_state_rate_table",
            policy_state_key: "hospital_daily_amount",
            multiplier,
          };
        }
        return {
          ...result,
          value: base,
          reference_amount: dailyAmount,
          state: multiplier === 1 ? "policy_state_daily_rate" : "policy_state_multiplier",
          policy_state_key: "hospital_daily_amount",
          multiplier,
        };
      }
      const stateAmount = firstPolicyStateAmount(item, [
        "cash_surrender_value",
        "policy_dividend_amount",
        "remaining_premium_amount",
        "installment_periodic_amount",
        "unpaid_annuity_balance",
        "policy_reserve_value",
        "current_policy_amount",
        "premium_amount",
      ]);
      if (stateAmount.value) {
        return {
          ...result,
          value: stateAmount.value,
          reference_amount: stateAmount.value,
          state: "policy_state_value",
          policy_state_key: stateAmount.key,
        };
      }
      return policyFieldKeys.length && !amount ? needsPolicyStateResult(result, item, policyFieldKeys) : result;
    }
    if (!amount && !faceAmount && !policyFieldKeys.length) return result;
    if (!amount) return result;
    if (normalizedEntry.calculation_basis === "per_day") {
      if (!normalizedEntry.quantity_state_key) {
        return { ...result, value: amount, state: "daily_rate" };
      }
      const quantity = policyStateInteger(
        item,
        normalizedEntry.quantity_state_key,
      );
      if (quantity === null) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_state_key],
        );
      }
      const eligibleQuantity = Math.min(
        quantity,
        normalizedEntry.quantity_cap || Number.MAX_SAFE_INTEGER,
      );
      const value =
        eligibleQuantity === 0
          ? 0
          : safeIntegerProduct(amount, eligibleQuantity);
      return Number.isSafeInteger(value)
        ? {
            ...result,
            value,
            state: "calculated",
            quantity,
            eligible_quantity: eligibleQuantity,
            quantity_cap: normalizedEntry.quantity_cap || undefined,
            unit_value: amount,
          }
        : { ...result, state: "amount_overflow" };
    }
    if (
      normalizedEntry.calculation_basis === "fixed_amount" &&
      normalizedEntry.quantity_state_key
    ) {
      const quantity = policyStateInteger(
        item,
        normalizedEntry.quantity_state_key,
      );
      if (quantity === null) {
        return needsPolicyStateResult(
          result,
          item,
          [normalizedEntry.quantity_state_key],
        );
      }
      const value = quantity === 0 ? 0 : safeIntegerProduct(amount, quantity);
      return Number.isSafeInteger(value)
        ? { ...result, value, state: "calculated", quantity, unit_value: amount }
        : { ...result, state: "amount_overflow" };
    }
    if (normalizedEntry.calculation_basis === "additional_benefit") {
      return { ...result, value: amount, state: "conditional_amount" };
    }
    return { ...result, value: amount, state: "calculated" };
  }

  function coverageEventScenarios(item) {
    const entries = effectiveCoverageEntries(item);
    const primaryEntries = entries.filter(
      (entry) =>
        entry.benefit_group_id &&
        entry.event_key &&
        entry.aggregation_rule === "choose_one",
    );
    const buildScenario = (
      primaryEntry,
      additiveEntries,
      eventKey,
      eventLabel,
    ) => {
      const scenarioEntries = [primaryEntry, ...additiveEntries];
      const parts = scenarioEntries.map((entry) => ({
        entry_id: entry.id,
        name: entry.name,
        aggregation_rule: entry.aggregation_rule,
        ...coverageValue(entry, item || {}),
      }));
      const requiredFields = uniquePolicyStateFields(
        parts.flatMap((part) => part.required_fields || []),
      );
      const hasAllValues = parts.every(
        (part) =>
          Number.isSafeInteger(part.value) &&
          part.value >= 0,
      );
      const funeralLimitedParts = parts.filter(
        (part) =>
          Number.isSafeInteger(part.funeral_benefit_limit) &&
          part.funeral_benefit_limit >= 0,
      );
      const ordinaryParts = parts.filter(
        (part) => !funeralLimitedParts.includes(part),
      );
      const funeralBenefitLimit = funeralLimitedParts.length
        ? Math.min(
            ...funeralLimitedParts.map(
              (part) => part.funeral_benefit_limit,
            ),
          )
        : null;
      const funeralProtectedAmount = funeralLimitedParts.length
        ? funeralLimitedParts.reduce(
            (total, part) =>
              total +
              (Number.isSafeInteger(part.protected_amount)
                ? part.protected_amount
                : part.value),
            0,
          )
        : 0;
      const funeralAccountValueReturn = funeralLimitedParts.reduce(
        (total, part) =>
          total +
          (Number.isSafeInteger(part.account_value_return)
            ? part.account_value_return
            : 0),
        0,
      );
      const ordinaryValue = ordinaryParts.reduce(
        (total, part) => total + (part.value || 0),
        0,
      );
      const value =
        hasAllValues && funeralBenefitLimit !== null
          ? ordinaryValue +
            funeralAccountValueReturn +
            Math.min(
              funeralProtectedAmount,
              funeralBenefitLimit,
            )
          : hasAllValues
            ? parts.reduce(
                (total, part) => total + part.value,
                0,
              )
            : null;
      return {
        id: `${primaryEntry.benefit_group_id}:${eventKey}`,
        benefit_group_id: primaryEntry.benefit_group_id,
        event_key: eventKey,
        label: eventLabel,
        primary_entry_id: primaryEntry.id,
        additive_entry_ids: additiveEntries.map(
          (entry) => entry.id,
        ),
        parts,
        required_fields: requiredFields,
        value:
          Number.isSafeInteger(value) &&
          value <= MAX_MONEY_AMOUNT
            ? value
            : null,
        gross_value_before_funeral_cap:
          funeralBenefitLimit !== null
            ? ordinaryValue +
              funeralAccountValueReturn +
              funeralProtectedAmount
            : undefined,
        funeral_benefit_limit:
          funeralBenefitLimit !== null
            ? funeralBenefitLimit
            : undefined,
        state: hasAllValues
          ? value <= MAX_MONEY_AMOUNT
            ? "calculated"
            : "amount_overflow"
          : "needs_input",
      };
    };

    return primaryEntries.flatMap((primaryEntry) => {
      const primaryResult = coverageValue(primaryEntry, item || {});
      if (primaryResult.state === "not_eligible") return [];
      const allAdditiveEntries = entries.filter(
        (entry) =>
          entry.benefit_group_id === primaryEntry.benefit_group_id &&
          entry.aggregation_rule === "conditional_additive" &&
          entry.applies_to_entry_ids.includes(primaryEntry.id) &&
          coverageValue(entry, item || {}).state !== "not_eligible",
      );
      const legacyAdditiveEntries = allAdditiveEntries.filter(
        (entry) => !entry.conditional_event_key,
      );
      const conditionalGroups = new Map();
      for (const entry of allAdditiveEntries) {
        if (!entry.conditional_event_key) continue;
        const group =
          conditionalGroups.get(entry.conditional_event_key) || [];
        group.push(entry);
        conditionalGroups.set(entry.conditional_event_key, group);
      }
      const scenarios = [
        buildScenario(
          primaryEntry,
          legacyAdditiveEntries,
          primaryEntry.event_key,
          primaryEntry.event_label || primaryEntry.name,
        ),
      ];
      for (const [conditionalEventKey, conditionalEntries] of
        conditionalGroups.entries()) {
        scenarios.push(
          buildScenario(
            primaryEntry,
            [...legacyAdditiveEntries, ...conditionalEntries],
            conditionalEventKey,
            conditionalEntries[0].conditional_event_label ||
              conditionalEntries[0].name,
          ),
        );
      }
      return scenarios;
    });
  }

  function coverageDetectionText(item) {
    return normalizeText(
      [item?.product_name, item?.product_id, item?.sale_status, item?.display_version, ...(item?.coverage_tags || []), ...(item?.flags || [])].join(" "),
    );
  }

  function detectCoverageBuckets(item) {
    const text = coverageDetectionText(item);
    const category = normalizeText(item?.product_type);
    const officialGroup = Object.entries(OFFICIAL_CATEGORY_GROUPS).find(([, categories]) =>
      [...categories].some((itemCategory) => category === normalizeText(itemCategory)),
    )?.[0];
    if (officialGroup === "property") {
      return COVERAGE_BUCKETS.filter(
        (bucket) => bucket.group === "property" && bucket.categories.some((itemCategory) => category === normalizeText(itemCategory)),
      ).map((bucket) => ({ ...bucket, matchedKeywords: [] }));
    }
    return COVERAGE_BUCKETS.map((bucket) => {
      if (officialGroup && bucket.group !== officialGroup) return null;
      const categoryMatched = bucket.categories.some((itemCategory) => category === normalizeText(itemCategory));
      const matchedKeywords = bucket.keywords.filter((keyword) => text.includes(normalizeText(keyword)));
      return categoryMatched || matchedKeywords.length ? { ...bucket, matchedKeywords } : null;
    }).filter(Boolean);
  }

  function hasDocumentSummaryEvidence(item) {
    if (item?.document_summary_loaded || item?.source_kind === "content") return true;
    if ((item?.reader_focus || []).some((focus) => focus?.summary || focus?.terms?.length)) return true;
    if ((item?.field_hits || []).length || (item?.matched_terms || []).length) return true;
    return false;
  }

  function normalizedStructureStatusId(item) {
    const raw = normalizeText(item?.structure_status || item?.benefit_structure_status);
    return STRUCTURE_STATUSES[raw] ? raw : "";
  }

  function structureStatus(item) {
    const explicit = normalizedStructureStatusId(item);
    if (explicit) return { id: explicit, ...STRUCTURE_STATUSES[explicit] };

    const entries = allStructuredCoverageEntries(item);
    if (entries.length) {
      const results = entries.map((entry) => coverageValue(entry, item || {}));
      if (results.some((result) => USER_INPUT_VALUE_STATES.has(result.state))) {
        return { id: "needs_user_input", ...STRUCTURE_STATUSES.needs_user_input };
      }
      if (results.some((result) => result.value || CALCULATED_VALUE_STATES.has(result.state))) {
        return { id: "calculated", ...STRUCTURE_STATUSES.calculated };
      }
      return { id: "pending_structure", ...STRUCTURE_STATUSES.pending_structure };
    }

    if (hasDocumentSummaryEvidence(item)) return { id: "pending_structure", ...STRUCTURE_STATUSES.pending_structure };
    return { id: "source_pending", ...STRUCTURE_STATUSES.source_pending };
  }

  return {
    MAX_MONEY_AMOUNT,
    MAX_MONEY_DECIMAL_PLACES,
    MAX_UNIT_COUNT,
    MAX_RATE,
    MAX_INSURED_AGE,
    SELECTION_MODES,
    STRUCTURE_STATUSES,
    CALCULATION_BASES,
    POLICY_STATE_FIELDS,
    AMOUNT_ROLES,
    LIMIT_SCOPES,
    AGGREGATION_RULES,
    RESULT_KINDS,
    AMOUNT_STAGES,
    COVERAGE_BUCKETS,
    normalizeUnitCount,
    normalizeMoneyAmount,
    normalizeNonNegativeMoneyAmount,
    moneyDecimalPlaces,
    normalizeDecimalMoneyAmount,
    normalizeContractCurrencyCode,
    normalizePolicyText,
    productVersionFamilyName,
    normalizeCoverageEntry,
    normalizeCoverageEntries,
    allStructuredCoverageEntries,
    normalizePlanOptions,
    normalizeUnitFields,
    policyStateFieldsForEntry,
    policyStateRequirements,
    declaredSelectionMode,
    selectionMode,
    selectionRequirements,
    effectiveCoverageEntries,
    coverageValue,
    coverageEventScenarios,
    structureStatus,
    detectCoverageBuckets,
  };
});
