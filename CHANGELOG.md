# Changelog

## 2026-10-25

- **新增** `2026-10-25-discord-safe-send/` — Discord Safe Send。10/22、10/23、10/25 連續三天發生 Discord 重複推播事故（同一則訊息分別送出 2、2、4 則，另有測試訊息殘留），全部靠人工呼叫 Discord REST API 逐一刪除。根因為 `discord_send.py` 的 fallback 只看 stdout 含 `"sent"` 就回報成功，gateway（127.0.0.1:18789）與任務控制中心（127.0.0.1:18792）掛掉時仍回 True，上游誤以為未送出而重送；且 gateway 掛掉時 `openclaw message read` 失效，送完無法回讀驗證。本工具直接走 Discord REST API（不依賴本機 gateway），送出後立刻回讀比對確認落地，內容 SHA-256 去重（TTL 24h）攔截重複送出，另支援 `--prune-tests` 掃描頻道清除測試訊息殘留、`--delete-id` 清理誤發重複。驗證通過（發送／去重攔截／重演 10/25 事故情境後頻道僅 1 則／清除 3 則測試訊息／超長擋下／dry-run）；開發中修掉 ledger 漏存 sha256 導致去重失配的 bug。

## 2026-10-18

- **新增** `2026-10-18-ifye-comms-tracker/` — IFYE 對外通訊追蹤器。Gmail triage 處理的 IFYE 外語郵件（Roberta Lin 電匯、John Muchenje 護照簽證、Janis Brinn 海報格式、Hatibu 護照、Catherine eVisa）散落每日 recap，無法快速查詢現況。本工具集中記錄，支援 🔴🟡🟢⚪ 狀態分級、期限追蹤、Markdown 匯出。驗證通過（add / list / update / rm / export 全部實測正常）。

## 2026-10-11

- **新增** `2026-10-11-discord-send-shim/` — `discord_send.py` Shim。全系統 8+ cron job 依賴此腳本發送 Discord 訊息，但檔案從未建立。本 Shim 相容舊呼叫方式（stdin / --file / positional），透過 openclaw CLI 發送真實訊息到 Discord。驗證通過（openclaw fallback ✅，messageId: 1558752895984345201）。

## 2026-10-04

- **新增** `2026-10-04-cron-alive-checker/` — cron 依賴腳本存活檢查工具。檢測 `discord_send.py`（critical）等 7 項失效。驗證通過（實跑測試案例，7 項失效正確列出）。

## 2026-09-27

- **新增** `2026-09-27-edmoms-ifye-diagnosis/` — EDMoms + IFYE 系統診斷工具。發現 EDMoms 驗證碼卡關根本原因（MLX OCR 未被呼叫）以及 IFYE sync Notion title drift 問題。
