# Daily Lab

每日 Workbench 成品存放處。每個子目錄為獨立的專案工具。

## 目錄

- `2026-09-27-edmoms-ifye-diagnosis/` — EDMoms + IFYE 系統診斷工具（靜態分析 + log 分析，開出 3 個改善提案）
- `2026-10-04-cron-alive-checker/` — cron 依賴腳本存活檢查工具（檢測 7 項失效，2 critical, 5 high）
- `2026-10-11-discord-send-shim/` — `discord_send.py` Shim（填補從未建立的腳本，讓所有 Discord 推播恢復運作）
- `2026-10-18-ifye-comms-tracker/` — IFYE 對外通訊追蹤器（將 Gmail triage 處理的 IFYE 外語郵件集中記錄，支援狀態分級、期限追蹤、Markdown 匯出。驗證通過）
- `2026-10-25-discord-safe-send/` — Discord Safe Send（可驗證、去重的 Discord 發送工具。直接走 REST API，送出後回讀確認落地，內容雜湊去重防止重複推播，並可一鍵清除測試訊息。驗證通過）

## 維護說明

所有成品從 `Lab/YYYY-MM-DD-主題slug/` 複製過來。請勿直接修改這裡的檔案，應在 `Lab/` 實驗，完成並驗證後再複製過來。
