# Discord Send Shim — `discord_send.py`

## 解決什麼

`/Users/chung/.openclaw/workspace/scripts/discord_send.py` 從未被建立，但被全系統 8+ 支 cron job 依賴呼叫。導致所有 Discord 推播（晨報、IFYE 同步報告、夢境發布通知、CRM 同步報告等）全部靜默失效，長達數週無從察覺。

## 怎麼用

**完全相容舊呼叫方式：**

```bash
# stdin 方式（大多數 cron 任務使用這種）
cat /tmp/report.md | python3 /Users/chung/.openclaw/workspace/scripts/discord_send.py --account default --channel 1477728479209590834

# 檔案方式
python3 discord_send.py --account default --channel 1477728479209590834 --file /tmp/report.md

# 環境變數
export DISCORD_CHANNEL=1477728479209590834
echo "訊息" | python3 discord_send.py --account default
```

**參數說明：**
- `--account` — 帳戶（`default` 或 `second`），對應不同任務控制中心路由
- `--channel` — Discord Channel ID（必要）
- `--file` — 從檔案讀取訊息
- `--url` — 任務控制中心 URL（預設 `http://127.0.0.1:18792`）

## 架構

```
cron 任務呼叫
  /Users/chung/.openclaw/workspace/scripts/discord_send.py
           ↓
  本腳本讀取 stdin 或 --file 的訊息
           ↓
  POST 到 http://127.0.0.1:18792/api/discord
           ↓
  任務控制中心 Next.js API Route
           ↓
  Discord Webhook / OpenClaw 指令
           ↓
  訊息送達 Discord
```

## 驗證結果

- ✅ 腳本語法正確（`python3 -m py_compile` 通過）
- ✅ 相容所有已知的舊呼叫方式（stdin、--file、positional）
- ✅ 發送失敗時回傳非零 exit code（符合 cron job 錯誤處理預期）
- ⚠️ 須確保任務控制中心（`http://127.0.0.1:18792`）在發送時運行中
