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
python scripts\run_tii_batch.py --batch-id tii-property-001 --captcha <人工輸入的驗證碼> --fetch-all-pages --fetch-details
python scripts\import_tii_results.py --input-dir work\tii-results --output data\tii-policy-results.json
```

較適合大量批次的方式是啟動本機 operator：

```powershell
python scripts\tii_operator_server.py
```

然後開啟 <http://127.0.0.1:8765/>。這個頁面只在本機執行，Kevin 只需要輸入官方圖片中的驗證碼；送出後會自動查詢該批、翻完整結果頁、抓可用明細頁、重新匯入 `data\tii-policy-results.json`，再準備下一批驗證碼。

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
- 目前 TII 人工批次已啟動：`4 / 306`。
- 目前等待驗證碼批次：`1`。
- 目前 TII 已索引批次：`3 / 306`。
- 目前 TII 完整批次：`3 / 306`。
- 目前已匯入 TII 保單結果：`2,095` 筆。
- 目前已保存 TII 明細頁：`2,094` 筆。
- `tii-property-001` 官方結果總數為 `952` 筆，目前已保存全部 `96` 個結果頁與 `952` 份明細頁。
- `tii-property-002` 官方結果總數為 `618` 筆，目前已保存全部 `62` 個結果頁與 `617` 份明細頁；另有 `1` 份官方明細頁在同一 session 回傳無效明細。
- `tii-property-003` 官方結果總數為 `525` 筆，目前已保存全部 `53` 個結果頁與 `525` 份明細頁。
- `tii-property-004` 已準備驗證碼，仍等待人工輸入。
- 剩餘 `303` 個 TII 批次仍需透過 operator 逐批人工輸入驗證碼，送出後由系統自動翻頁、抓明細、匯入。

保發中心頁面本身分為「財產保險」與「人身保險」。目前批次矩陣已依這個入口拆分：

- 產險：`27` 家公司 x `4` 個產險類別 = `108` 個人工查詢批次。
- 壽險/人身保險：`33` 家公司 x `6` 個人身保險類別 = `198` 個人工查詢批次。
- 合計：`306` 個人工查詢批次，另有 `1` 個非產壽險代碼不列入產險/壽險矩陣。

網站上的每個 TII 批次會列出 `categoryId`、`CompanyID`、`f_CategoryId1`。operator 會依批次計畫送出這些欄位；完成條件不是「有第一頁」，而是 `unique_product_id_count == expected_total_count == imported_record_count`。若只抓到部分頁面，資料會標為 `partial_index`，前台會顯示「已索引」而不是「完整」。前三批已符合完整條件：`tii-property-001` 為 `952 == 952 == 952`，`tii-property-002` 為 `618 == 618 == 618`，`tii-property-003` 為 `525 == 525 == 525`。

如果結果顯示 `robots 擋下`，代表站方規則不允許自動抓取，應改走人工複核或 TII 查詢匯入。

建議節奏：

- 每天 1 批自動 URL/content batch。
- 每天 1 到 3 批 TII 人工驗證碼查詢。
- 優先順序：已停售、不確定、高量公司、健康險/壽險/傷害險/年金險，最後再補其他公司與其他類型。
