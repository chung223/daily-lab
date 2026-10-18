# Changelog

## 2026-10-18

- **新增** `2026-10-18-ifye-comms-tracker/` — IFYE 對外通訊追蹤器。Gmail triage 處理的 IFYE 外語郵件（Roberta Lin 電匯、John Muchenje 護照簽證、Janis Brinn 海報格式、Hatibu 護照、Catherine eVisa）散落每日 recap，無法快速查詢現況。本工具集中記錄，支援 🔴🟡🟢⚪ 狀態分級、期限追蹤、Markdown 匯出。驗證通過（add / list / update / rm / export 全部實測正常）。

## 2026-10-11

- **新增** `2026-10-11-discord-send-shim/` — `discord_send.py` Shim。全系統 8+ cron job 依賴此腳本發送 Discord 訊息，但檔案從未建立。本 Shim 相容舊呼叫方式（stdin / --file / positional），透過 openclaw CLI 發送真實訊息到 Discord。驗證通過（openclaw fallback ✅，messageId: 1558752895984345201）。

## 2026-10-04

- **新增** `2026-10-04-cron-alive-checker/` — cron 依賴腳本存活檢查工具。檢測 `discord_send.py`（critical）等 7 項失效。驗證通過（實跑測試案例，7 項失效正確列出）。

## 2026-09-27

- **新增** `2026-09-27-edmoms-ifye-diagnosis/` — EDMoms + IFYE 系統診斷工具。發現 EDMoms 驗證碼卡關根本原因（MLX OCR 未被呼叫）以及 IFYE sync Notion title drift 問題。
