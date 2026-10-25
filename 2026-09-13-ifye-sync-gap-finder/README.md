# IFYE Sync Gap Finder

## 解決什麼

驗證 IFYE Notion → JSON 同步是否存在資料缺口。

每日 sync 排程從 Notion 讀取兩資料庫（115_01_12來訪 9 筆 + 在台 60 筆），合併寫入 `ifye-2026.json`。當 DB2（在台）頁面的 `115_01_12來訪` relation 欄位為空、或人名與 sync 腳本正規化邏輯不一致時，該筆記錄會被漏掉。

本工具在 sync 之後執行一次一致性檢查，第一時間發現缺口，而非累積數週後才暴露。

## 痛點依據

- **Recap 2026-09-04~09-12**：IFYE sync 每日執行，輸出固定 9×51 站（51 站是錯的）
- **Recap 2026-09-09**：`safe_get` 修復了 `NoneType` 錯誤，但 9 筆 relation 空白仍導致 fallback 失效
- **Recap 2026-09-10**：IFYE sync 未完成，relation 對應失敗，VPS 未部署
- **實際驗證（2026-09-13）**：本工具對實際資料執行，發現 **24 筆缺口**

## 怎麼用

```bash
# 標準執行（讀取本機 JSON）
python3 ifye-gap-finder.py

# 從 VPS 下載 JSON 再比對
python3 ifye-gap-finder.py --vps

# 指定本機 JSON 路徑
python3 ifye-gap-finder.py --local /path/to/ifye-2026.json

# 輸出 JSON 結果到檔案（供自動化使用）
python3 ifye-gap-finder.py 2>/dev/null > gap-report.json
```

## 檢查邏輯

| 步驟 | 說明 |
|------|------|
| 1. 查詢 Notion | 讀取 DB1（來訪 9 筆）+ DB2（在台 60 筆） |
| 2. 建立 unique key | 以「代表名 + 站名 + 日期」做為每筆記錄的唯一識別 |
| 3. 讀取 JSON | 從本機或 VPS 讀取 `ifye-2026.json` |
| 4. 比對差集 | Notion 有但 JSON 沒有的 = 缺口 |
| 5. 根因分類 | `relation空白`（DB2 孤立）或 `名稱比對失敗`（sync 正規化問題）|

## 驗證結果（2026-09-13 執行）

```
DB1（來訪代表）:  9 筆
DB2（在台站別）:  60 筆
Notion 在台站 unique keys: 60
JSON 站數:  51 站
差額（Notion 有 / JSON 無）: 24 筆
  • relation 空白導致（DB2 孤立）: 18 筆
  • 名稱比對失敗（sync 邏輯問題）: 6 筆
```

**缺口代表**：
- `Mr.Phoobet Sudsawat` → JSON 寫成 `Phoobet Sudsawatt`：8 站全數漏接
- `Sven Bucheli` → JSON 寫成 `Sven`：9 站全數漏接
- 6 位代表的`送機`記錄：sync 對送機處理的邏輯有缺陷

## 修復建議（只提案不改系統）

1. **緊急**：修補 sync 腳本的正規化邏輯——在比對 DB2 人名時，先正規化再 lookup
2. **緊急**：修補 sync 對「送機」站名的處理（`站` 欄位 = "送機" 的記錄可能被錯誤過濾）
3. **根本解**：補全 Notion DB2 中所有 54 個 relation 欄位（`115_01_12來訪` 欄位），讓 DB1↔DB2 真正連結

## 限制

- 需要 `NOTION_API_KEY`（從 `~/.openclaw/openclaw.json` 讀取）
- 本工具只讀取不寫入，修復方案需手動執行或提出後由人確認
- JSON 路徑：`/Users/chung/.openclaw/sites/ifye/2026/data/ifye-2026.json`
