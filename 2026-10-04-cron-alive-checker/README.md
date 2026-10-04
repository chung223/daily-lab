# 🔬 Cron Alive Checker

**解決什麼：**
cron 任務靜默失敗的問題。過去 7 天（2026-09-28～10-04），多個 cron 任務持續引用不存在的腳本——`discord_send.py`、`crm_auto_sync.py`、`tyme4ts` 目錄等——導致所有 Discord 推播、CRM 同步、晨報氣象資訊靜默失效，沒有人知道。

**怎麼用：**
```bash
# 本地測試（不發 Discord）
python3 cron_alive_checker.py --test

# 執行並發送 Discord 通知
python3 cron_alive_checker.py --send

# 指定 webhook URL
python3 cron_alive_checker.py --send --webhook-url "https://discord.com/api/webhooks/..."
```

建議放進每日早晨的 cron 排程，確保當天的通知基礎設施還活著。

**驗證結果（2026-10-04 實跑）：**
- ✅ 成功檢測 7 項失效：`discord_send.py`（critical）、`crm_auto_sync.py`、`flight_tracker.py`、`gmail_triage.py`、`ifye_sync.py`、`tyme4ts` 目錄、`edoms-check-automation` 目錄
- ✅ 正常項目：無
- ⚠️ Discord webhook 未設定，工具已正確識別並跳過

**根本原因：**
`discord_send.py` 從未被建立，所有 cron 任務卻都寫了要呼叫它。這不是檔案被刪除的問題，是通知腳本從一開始就沒有寫。

**下一步：**
1. 確認 `discord_send.py` 應有的功能（Send message to Discord webhook）
2. 建立 `/Users/chung/.openclaw/workspace/scripts/discord_send.py`
3. 或將通知改為其他已知可用的方式
