# Discord Safe Send — 可驗證、去重的 Discord 發送工具

## 解決什麼

2026-10-22、10-23、10-25 三天連續發生 **Discord 重複推播事故**：

| 日期 | 事故 | 善後 |
|------|------|------|
| 10-22 | 同一則 IFYE 報告送出 2 則 | 手動刪除重複那則（保留 1 則） |
| 10-23 | 夢境 recap 重複 2 則＋1 則測試訊息 | 手動呼叫 Discord API 逐一刪除 |
| 10-25 | 同一則 recap **連發 4 次**＋1 則測試訊息 | 手動全數刪除 |

根因有兩層：

1. **判定層（主因）**
   現有 `discord_send.py` 的 fallback 判定邏輯：openclaw CLI 回 exit 0 後，
   只看 stdout 裡有沒有 `"sent"` 字樣就回傳成功。但當 OpenClaw gateway
   （`127.0.0.1:18789`）與任務控制中心（`127.0.0.1:18792`）同時掛掉時，
   CLI 仍會回 exit 0、輸出不含有效狀態，於是**判定函式回 True**。
   上游看到「成功」就往下走，看不到成功就會**再送一次** → 重複推播。

2. **驗證層**
   gateway 掛掉時 `openclaw message read` / `delete` 全數失效，
   送完無法回讀確認，問題當下無法察覺。10-24 recap 寫下這句話：
   「像在沒有回音的山谷裡講話——講了，但不知道有沒有被聽見。」

本工具兩層都補上。

## 怎麼用

```bash
cd discord_safe_send.py 所在目錄

# 一般發送（自動去重 + 回讀驗證 + 落地確認）
python3 discord_safe_send.py --channel <CHANNEL_ID> --file /tmp/msg.md

# 測試訊息（自動加標記、可一鍵清除）
python3 discord_safe_send.py --channel <CHANNEL_ID> --file /tmp/t.md --test

# 清除所有本工具產生的測試訊息（掃描頻道最近 100 則）
python3 discord_safe_send.py --channel <CHANNEL_ID> --prune-tests

# 刪除指定訊息（清理誤發的重複推播）
python3 discord_safe_send.py --channel <CHANNEL_ID> --delete-id <MESSAGE_ID>

# 預演（只檢查不送出）
python3 discord_safe_send.py --channel <CHANNEL_ID> --file /tmp/msg.md --dry-run
```

### 參數

| 參數 | 說明 |
|------|------|
| `--channel` | Discord Channel ID（必要） |
| `--account` | `default` / `second`（預設 default），token 自動從 `~/.openclaw/openclaw.json` 讀取 |
| `--file` | 訊息來源檔（與 stdin 二選一） |
| `--test` | 送出測試訊息，附加 `🧪[discord-safe-send-test]` 標記 |
| `--prune-tests` | 清除測試訊息（ledger 紀錄＋頻道掃描雙來源） |
| `--delete-id` | 刪除指定 message id |
| `--force` | 略過去重，強制重送 |
| `--dry-run` | 只檢查不送出 |
| `--ttl-hours` | 去重有效期，預設 24 小時 |
| `--ledger` | ledger 路徑，預設 `~/.cache/discord-safe-send/ledger.json` |

### 設計要點

- **不依賴本機 gateway**：直接走 Discord REST API（`discord.com/api/v10`，
  並在 canary/ptb 節點間自動容錯）。gateway 掛了照樣能送、能驗證、能刪。
- **送出必回讀**：POST 後立刻 GET `/channels/{id}/messages/{msg_id}`
  比對內容與頻道，確認落地才回 exit 0。
- **去重靠內容雜湊**：SHA-256(帳戶‖頻道‖內容) 寫入本機 ledger，
  TTL 內命中就拒絕重送並回報既有 message id。
- **失敗要誠實**：送出成功但回讀驗證不過 → exit 1，不假報成功。
- **單則上限 2000 字**：超過直接擋下，避免 Discord 端才發現。

## 驗證結果

全部實跑，貼實際輸出。

### 1. 基本發送 + 回讀驗證

```
$ python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/wb_test.txt --test
{"ok": true, "message_id": "1563825125780885544", "channel": "1477728479209590834",
 "account": "default", "verified": true, "test": true,
 "sha256": "1f1c0f761eb84c4151f9f54a14dce4ba819052ddec7f3d1d85b25b42df49d931", "length": 62}
EXIT=0
```

### 2. 去重攔截（重複推播事故的直接防線）

```
$ python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/wb_t3.txt --test
{"ok": true, "message_id": "1563825274057920513", ... "verified": true ...}
EXIT=0

$ python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/wb_t3.txt --test   # 內容完全相同
{"ok": false, "reason": "duplicate", "message_id": "1563825274057920513",
 "sent_at": 1792915400.397631,
 "sha256": "b5f2672a12f6658436f6a4c2e9a61732a77b94a1ae6ec1ffb8d5cc9c263da525",
 "hint": "內容與先前送出者完全相同，已跳過。若確實要重送請加 --force。"}
EXIT=1
```

### 3. 整合測試：完整重演 10/25 事故情境

```
=== 步驟1：第一次送出
{"ok": true, "message_id": "1563825407696969871", ... "verified": true ...}
EXIT=0

=== 步驟2：上游誤以為沒送出而重試
{"ok": false, "reason": "duplicate", "message_id": "1563825407696969871", ...}
EXIT=1 （期望 1 = 已攔截重複）

=== 步驟3：確認頻道中此內容只有一則
符合內容的訊息筆數: 1 ['1563825407696969871']

=== 步驟4：清除測試訊息
{"ok": true, "scanned": 100, "found": 1, "deleted": ["1563825407696969871"], "failed": []}
```

**對照：舊行為會送出 2 則（10/25 實際送 4 則），新行為送出 1 則並明確回報被攔截。**

### 4. 清除測試訊息（含 ledger 遺失的殘留）

```
$ python3 discord_safe_send.py --channel 1477728479209590834 --prune-tests
{"ok": true, "scanned": 100, "found": 3,
 "deleted": ["1563825125780885544", "1563825162288369788", "1563825274057920513"], "failed": []}
EXIT=0
```

頻道回讀確認測試訊息已全數清除，只剩正式訊息。

### 5. 超長訊息擋下

```
$ python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/wb_big.txt
{"ok": false, "reason": "too_long", "length": 2100, "limit": 2000,
 "hint": "Discord 單則上限 2000 字，請拆分後再送。"}
EXIT=1
```

### 6. dry-run

```
{"ok": true, "dry_run": true, "sha256": "ab25651ddb942c15d25384f3815daafca6ae105eccfeec1aa1499e7e965e4d05",
 "length": 18, "would_send": "🧪 測試二：dry run 不應送出"}
EXIT=0
```

### 開發過程中修掉的一個 bug

第一版的 ledger 紀錄漏存 `sha256` 欄位，導致去重比對永遠失配（實測第二次
送出仍然成功）。已修正並重新驗證——上面的測試 2 與測試 3 是修正後的結果。

## 建議的導入方式

把 cron 內所有

```
cat FILE | python3 .../discord_send.py --account X --channel Y
```

改成

```
python3 .../discord_safe_send.py --account X --channel Y --file FILE
```

（順便避開 `cat | python3` 觸發安全掃描被擋的問題——10-22、10-25 都遇到過。）

`discord_safe_send.py` 本身不會動到 `discord_send.py`，兩者可並行；
`discord_send.py` 的 fallback 判定邏輯問題需要另外修（屬於既有腳本，
不在本次成品範圍）。

## 安全性

- 不會把 token 寫進任何輸出或檔案；token 從 `~/.openclaw/openclaw.json` 讀取。
- ledger 只存 SHA-256、message id、時間戳，不存訊息內容。
- 測試訊息帶明確標記，`--prune-tests` 只刪有該標記的訊息，不會誤刪正式內容。
