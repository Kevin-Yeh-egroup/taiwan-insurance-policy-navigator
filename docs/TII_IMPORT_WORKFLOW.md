# 保發中心停售保單查詢匯入流程

官方入口：<https://insprod.tii.org.tw/Query.aspx>

## 目前可自動整理的部分

`scripts/extract_tii_metadata.py` 只讀取查詢頁面上的公開表單資訊，產生：

- 公司類別
- 公司名稱選項
- 保險類別選項
- 可查詢欄位
- 是否需要圖形驗證碼

輸出檔案：

```powershell
python scripts\extract_tii_metadata.py
```

```text
data\tii-query-metadata.json
```

## 圖形驗證碼邊界

保發中心查詢頁需要圖形驗證碼。這個專案不自動破解或繞過驗證碼。

可接受流程是：

1. 人工開啟官方查詢頁。
2. 選擇公司、保險類別、銷售日或停售日。
3. 人工輸入驗證碼並送出。
4. 將結果頁另存成 HTML，或整理成 CSV。
5. 放到 `work\tii-results\`。
6. 執行匯入器。

```powershell
python scripts\import_tii_results.py --input-dir work\tii-results --output data\tii-policy-results.json
```

也可以用批次 runner 啟動單一批次。沒有提供驗證碼時，runner 會抓取官方表單與驗證碼圖片，並把該批標記為等待驗證碼：

```powershell
python scripts\run_tii_batch.py --batch-id tii-property-001
```

人工讀取驗證碼後，再用同一批次送出：

```powershell
python scripts\run_tii_batch.py --batch-id tii-property-001 --captcha <人工輸入的驗證碼>
python scripts\import_tii_results.py --input-dir work\tii-results --output data\tii-policy-results.json
```

## 匯入後如何使用

匯入後的停售保單資料會進入同一個前台視覺化模型。前台應優先呈現：

- 保險公司
- 商品名稱
- 商品類型
- 銷售狀態
- 銷售日/停售日
- 條款或官方結果來源
- 內容重點欄位：理賠/給付、名詞定義、等待期/免責期、除外責任、保費/續保、投保限制

## 重要限制

查詢結果只是公開資訊導覽，不是保險建議、法律意見、理賠承諾或承保判斷。停售與給付內容仍需回官方條款、保險公司或保發中心查詢結果確認。

## 分段處理策略

保單數量很大時，不要一次查完。先產生批次計畫：

```powershell
python scripts\plan_segmented_batches.py --policy-batch-size 80
```

輸出檔案：

```text
data\batch-plan.json
```

目前批次規劃會分成兩種：

- `policy_url_content_batch`：既有保單 URL 的自動批次，每批約 80 筆。
- `tii_manual_captcha_batch`：保發中心查詢的人工驗證碼批次，依公司與保險類別拆分。

執行一批既有 URL/content batch：

```powershell
python scripts\run_policy_batch.py --batch-id policy-url-001
```

執行結果會寫入：

```text
data\policy-batch-results.json
data\batch-progress.json
```

目前自動 URL/content batch 已完成 `policy-url-001` 到 `policy-url-017`：

- 已處理保單 URL：`1,343`
- 可抓取頁面：`559`
- robots 擋下：`532`
- 錯誤或逾時：`252`
- TII 驗證碼批次仍需人工查詢與匯入，不繞過驗證碼。
- 目前 TII 人工批次已啟動：`1 / 306`。
- 目前等待驗證碼批次：`1`。
- 目前 TII 人工批次完成狀態：`0 / 306`。
- 目前已匯入 TII 保單結果：`0` 筆。

保發中心頁面本身分為「財產保險」與「人身保險」。目前批次矩陣已依這個入口拆分：

- 產險：`27` 家公司 x `4` 個產險類別 = `108` 個人工查詢批次。
- 壽險/人身保險：`33` 家公司 x `6` 個人身保險類別 = `198` 個人工查詢批次。
- 合計：`306` 個人工查詢批次，另有 `1` 個非產壽險代碼不列入產險/壽險矩陣。

網站上的每個 TII 批次會列出 `categoryId`、`CompanyID`、`f_CategoryId1`。人工查詢時照這三個欄位選擇，輸入驗證碼後保存結果，再用 `import_tii_results.py` 匯入。

如果結果顯示 `robots 擋下`，代表站方規則不允許自動抓取，應改走人工複核或 TII 查詢匯入。

建議節奏：

- 每天 1 批自動 URL/content batch。
- 每天 1 到 3 批 TII 人工驗證碼查詢。
- 優先順序：已停售、不確定、高量公司、健康險/壽險/傷害險/年金險，最後再補其他公司與其他類型。
