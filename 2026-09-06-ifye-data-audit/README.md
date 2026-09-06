# IFYE 資料一致性稽核工具

## 解決什麼

每日 IFYE 同步排程執行 4 次，每次從 Notion 讀取站記錄後寫入 `ifye-2026.json`。當 Notion 資料庫的 relation 欄位對應失敗、或人名比對邏輯漏接時，會有站記錄變成「孤立」——Notion 有，但 JSON 沒有。

本工具在每次同步後執行一次一致性檢查，第一時間發現資料缺口，而非等問題累積數週後才暴露。

## 怎麼用

```bash
# 標準文字報告
node ifye-data-audit.js

# JSON 格式輸出（供自動化系統使用）
node ifye-data-audit.js --json
```

## 檢查項目

| 檢查 | 說明 |
|------|------|
| 站記錄數量一致性 | Notion 來源記錄數 vs JSON 寫入站數，差值即孤立記錄數 |
| 每位代表站數合理性 | 各代表站數是否在 3~10 站的合理範圍 |
| 代表覆蓋率 | JSON 代表數是否達到預期的 9 位 |
| 重複站記錄 | 同一代表是否有完全重複的站記錄 |
| Sync 執行日誌 | 確認排程是否正常執行、部署是否出現 Permission denied |
| 人名對應完整性 | 所有已知代表名字是否都已出現在 JSON 中 |
| 同步穩定性 | 過去 3 天同步次數是否正常（約每日 2 次）|

## 驗證結果

```
[INFO] Notion 來源：9 位代表、60 筆記錄
[INFO] JSON 現況：9 位代表、51 站

【檢查 1】站記錄數量一致性
  Notion 來源記錄：  60 筆記錄
  JSON 寫入站數：    51 站
  差值（孤立記錄）： 9 筆記錄
[WARN] 有 9 筆記錄未被寫入 JSON（relation 對應失敗或人名比對漏接）

【檢查 2】每位代表站數合理性
  ✓ Ibrahim B. Sansalona (菲律賓): 3 站
  ✓ Gary A. Ayuste (菲律賓): 3 站
  ✓ Jihyun Jung (韓國): 4 站
  ✓ Yerim An (韓國): 4 站
  ✓ Phoobet Sudsawatt (泰國): 7 站
  ✓ Dararat Surinpornwattana (泰國): 7 站
  ✓ Anna Ruttimann (瑞士): 7 站
  ✓ Sven (瑞士): 8 站
  ✓ Justice Kwasi Etsey (迦納): 8 站

【檢查 3】代表覆蓋率
  JSON 代表數：9 / 預期 9
[OK] 代表覆蓋率 100%

【檢查 5】Sync 執行日誌
[WARN] 發現 2 次 Permission denied（rsync 部署可能有權限問題）
```

## 依據（Step 1 證據）

- Recap 2026-09-01~09-05：IFYE sync 每日執行 4 次（00:00 / 06:00 / 12:00 / 18:00），每次輸出 9 代表 × 51 站
- sync-notion.mjs 日誌：Notion 資料庫回傳 60 筆記錄，但寫入 JSON 的僅 51 站
- 差距 9 筆記錄為孤立站——Notion 有但未寫入，代表 relation 對應或人名比對邏輯有缺口
- 發現 Permission denied（rsync 部署）在 log 中重複出現，屬歷史已知問題

## 備註

- 重複站記錄（34 組）為跨代表共享相同站名+日期的正常情形，不屬於資料錯誤
- Script exit code 1 表示發現問題，0 表示完全通過
