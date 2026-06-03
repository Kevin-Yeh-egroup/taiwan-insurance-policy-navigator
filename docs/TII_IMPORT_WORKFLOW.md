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
