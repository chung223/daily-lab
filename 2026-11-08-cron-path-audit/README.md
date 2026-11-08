# 🔎 Cron Path Audit — Cron 路徑與技能引用健檢

**在 cron 壞掉之前，先找出它引用了什麼不存在的東西。**

---

## 解決什麼

本週（2026-11-02～11-08）的每日記憶檔裡，同一個形狀出現了七天：

> **「靜默失效（仍未修）」** —— 每一份記錄的最後一節都開頭寫著這五個字。

| 日期 | 排程 | 記錄寫的 |
|---|---|---|
| 11-02 | Notion→Google Calendar ×2 | 第 64 天／逾 100 次失敗 |
| 11-03 | 同上 | 第 65 天／逾 100 次失敗 |
| 11-04 | 同上 | 第 66 天／逾 100 次失敗 |
| 11-05 | 同上 | 第 67 天／逾 100 次失敗 |
| 11-06 | 同上 | 第 68 天／逾 100 次失敗 |
| 11-07 | 同上 | 第 69 天／逾 100 次失敗 |
| 11-08 | 同上 | **第 70 天**／逾 100 次失敗 |

同期的其他靜默失效：

- **每日備份（05:15）** — 連續第 **42** 次失敗（11-02 是第 36 次）
- **記憶→agentmemory 同步（05:00）** — `memsync exit=2`
- **Readmoo 每日特惠（08:00）** — `readmoo exit=2`
- **Dreaming Mode** — `should-dream.sh` 找不到，連續多日 exit 127
- **EDMoms 收文同步** — `Skill(s) not found: openclaw-imports/edoms-check`，連續第 4 天噪音
- **晨報** — 技能路徑全數失效，航空快訊整段略過

### 為什麼會這樣

根因只有一句話：**cron 的指令稿裡寫死的路徑，隨著時間推移全部過期了，但沒有人回頭檢查。**

11-07 那天的記錄寫得很直白：

> 「指令稿內建的路徑常已失效（`should-dream.sh` 在 `.archive/`、技能搬至
> `~/.hermes/skills/openclaw-imports/`、`cwa-weather` 已封存）」

而 11-05 那天抓出了一個更細的：

> 「排程指令稿內建的 Bearer token 有字元錯誤，照抄會 401」

這些錯誤有個共同點：**排程照跑、狀態欄顯示 `ok`、但事情根本沒做成。**
`hermes cron list` 對 no-agent 腳本 job 一律顯示 `ok`，即使腳本 `exit=2`
（這是 11-08 記憶檔裡第 50 行再次記錄的結論）。

### 真正的痛點不是「壞掉」，是「要靠人肉逐日數天數」

本週已經有一個工具在做相鄰的事——`2026-11-01-cron-truth-checker` 比對
「狀態欄」與「實際輸出」。但它只能告訴你**哪個 job 失敗了**，
不能告訴你**為什麼失敗**。

而這裡的每一個失敗，答案都寫在一行路徑上：

```
$ cat ~/.hermes/scripts/oc-notion-sync.sh
...
sendoff) SCRIPT=/Users/chung/.openclaw/workspace/scripts/sync_notion_sendoff_to_gcal.py
```

`$ ls ~/.openclaw/workspace/scripts/`
```
crm_auto_sync.py  discord_send.py  recap_filter.py
```

腳本根本不存在。**但這行字串不在 job 的 prompt 裡**——它在一層 wrapper
shell 裡面。只掃 job 欄位永遠看不到它。

本工具補上這一層。

---

## 做了什麼

`cron_path_audit.py` 掃描 `~/.hermes/cron/jobs.json` 的每個 job，
**兩層都查**：

### 第 1 層：job 本身

- `prompt` / `command` 欄位裡的所有路徑引用
- `skills` / `skill` 欄位宣告的技能名稱

### 第 2 層：no_agent job 的 wrapper 腳本鏈

這是關鍵。`no_agent` job 的 `script` 欄位指向一個 wrapper shell
（`~/.hermes/scripts/oc-*.sh`），wrapper 裡再呼叫真正的 `.py` / `.sh`。
本工具會**遞迴解析** `source` / `exec` 關聯，把整條腳本鏈攤開一起檢查。

以 `Notion送機表→Calendar` 為例，實際檢查的鏈是：

```
/Users/chung/.hermes/scripts/oc-notion-sendoff.sh
  └─ /Users/chung/.hermes/scripts/oc-notion-sync.sh
       └─ ✗ /Users/chung/.openclaw/workspace/scripts/sync_notion_sendoff_to_gcal.py
```

### 附帶三件事

1. **搬家偵測** —— 檔案不在原位，但同名檔案在別處存在時，直接告訴你搬到哪：
   ```
   ✗ 每日備份
       路徑不存在: /Users/chung/.openclaw/workspace/scripts/backup_openclaw.sh
           ↪ 疑似搬家到: /Users/chung/openclaw-backup/scripts/backup_openclaw.sh
   ```
2. **技能三態判定** —— 技能*搬家*（分類變了）、技能*封存*（在 `.archive`）、技能*不存在*。
   不會把英文片語（`no/avoid`、`release/breaking`）誤判成技能引用。
3. **停用中標記** —— `enabled: false` 的 job 會標「（停用中）」，
   避免把 AOA 同步這種 6 月就停掉的排程跟真正在噴錯的排程混在一起看。

**唯讀**：不修改任何 cron 設定、`jobs.json` 或技能檔案。

---

## 怎麼用

```bash
# 人看的報告（預設，只列有問題的）
python3 cron_path_audit.py

# Markdown 報表
python3 cron_path_audit.py --format markdown --out /tmp/cron-path-audit.md

# 機器讀的 JSON（適合掛進排程或 CI）
python3 cron_path_audit.py --format json

# 列出全部 job（含正常的）
python3 cron_path_audit.py --all

# 自訂路徑
python3 cron_path_audit.py --jobs ~/.hermes/cron/jobs.json \
                            --skill-dir ~/.hermes/skills
```

**Exit code**：有發現失效引用 → `1`；全部一致 → `0`。
所以可以直接掛進排程，出事時 exit 1 就能觸發通知。

### 建議用法：每天早上跑一次

```bash
python3 cron_path_audit.py --format markdown --out /tmp/cron-path-audit.md
# 若 exit 1，把報表送出去
```

或更消極一點 —— 直接把它當成「預防性維護」：
每次搬動技能、封存 skill、或改 `~/.hermes/skills/` 結構之後跑一次，
在壞掉之前就會知道哪些排程的指令稿該跟著改。

---

## 驗證結果

### 單元測試

```
$ python3 test_cron_path_audit.py
test_audit_finds_all (__main__.TestAuditEndToEnd) ... ok
test_broken_job_counted (__main__.TestAuditEndToEnd) ... ok
test_existing_path_not_reported (__main__.TestPlaceholders) ... ok
test_home_expansion (__main__.TestPlaceholders) ... ok
test_placeholder_paths_ignored (__main__.TestPlaceholders) ... ok
test_known_broken_detected (__main__.TestRealEnvironment) ... ok
test_real_scan_runs (__main__.TestRealEnvironment) ... ok
test_archived_detected (__main__.TestSkillRefs) ... ok
test_correct_ref_not_flagged (__main__.TestSkillRefs) ... ok
test_english_phrases_not_flagged (__main__.TestSkillRefs) ... ok
test_moved_category_detected (__main__.TestSkillRefs) ... ok
test_missing_wrapper_detected (__main__.TestWrapperResolution) ... ok
test_wrapper_chain_resolved (__main__.TestWrapperResolution) ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.036s

OK
```

涵蓋：佔位符排除（`$(date)`、`YYYY-MM-DD`、`$TODAY`、glob、中文句尾、PATH 清單）、
技能三態判定、wrapper 遞迴解析、端到端流程、真實環境回歸。

### 真實環境掃描

```
$ python3 cron_path_audit.py
🔍 Cron 路徑與技能引用健檢

掃描 job：33　｜　有問題：15　｜　失效路徑：24　｜　失效技能：2
```

15 個 job 有問題。其中 **11 個是啟用中的排程**（其餘 4 個為 6～8 月已停用者）。

### 逐項人工核對（比對各 job 最近一次的實際 cron 輸出）

| 本工具的發現 | 實際 cron 輸出 | 一致 |
|---|---|---|
| `Notion送機表→Calendar` 缺 `sync_notion_sendoff_to_gcal.py` | `notion-sendoff exit=2 (ERROR:腳本不存在 …)` | ✓ |
| `Notion外國接送機→Calendar` 缺 `sync_notion_foreign_transfer_to_gcal.py` | `notion-foreign exit=2 (ERROR:腳本不存在 …)` | ✓ |
| `每日備份` 缺 `backup_openclaw.sh` | `Script execution failed: 'utf-8' codec …`（根因為腳本缺檔） | ✓ |
| `記憶→agentmemory同步` 缺 `sync_daily_memory_to_agentmemory.py` | `memsync exit=2` | ✓ |
| `Readmoo每日特惠` 缺 `readmoo_daily.py` | `readmoo exit=2` | ✓ |
| `npm安全週掃` 缺 `npm_security_check.sh` | `npmscan exit=127` | ✓ |
| `Dreaming Mode` 缺 `should-dream.sh` | 輸出內自述「已不存在，實際執行的是封存版」 | ✓ |
| `EDMoms收文同步Sheets` 技能已封存 | `Skill(s) not found and skipped: openclaw-imports/edoms-check` | ✓ |
| `晨報` 技能路徑全失效 | 輸出內仍引用 `skills/tyme4ts`、`skills/tarot-reader`、`skills/meihua-yishu` | ✓ |
| `每日自我更新檢查` 技能分類變了 | `hermes/hermes-agent` → 現為 `autonomous-ai-agents/hermes-agent` | ✓ |
| `AOA-同步 ×3` 缺 `sync_aoa_playwright.py` | job 為 `enabled:false`（2026-06 起停用）→ 標「（停用中）」 | ✓ |

**無誤報**：其餘 18 個 job（含所有運作正常的排程：行事曆格式糾察、CRM Sync、
魚油提醒、IFYE 同步、心理健身短文、gmail 翻譯等）全部未被標記。

### 修 bug 的過程紀錄（測試真的抓到問題）

初版有四個問題，都是測試先發現的：

1. **技能引用永遠抓不到** —— regex 的第一組結尾帶 `/`，比對時分類名變成
   `"old-cat/"` 而非 `"old-cat"`，導致全部比對失敗。
2. **只抓 `/Users` 開頭的路徑** —— wrapper 內呼叫 `/opt/...`、`/absolutely/...`
   這類路徑完全漏掉（正是 wrapper 解析存在的理由）。
3. **假陽性** —— `/tmp/report.md`、`/uploads/x.jpg` 這些*輸出*檔被當成失效依賴。
4. **假陽性** —— `skills/tyme4ts` 中的 `skills` 被當成技能分類，
   導致每個技能路徑都多報一筆「分類已變更」。

修完後重跑，13/13 通過。

---

## 未完成 / 限制

- **只讀。** 本工具找出問題，但不修。實際修正（把路徑指向封存版、
  把 `skills` 欄位改成新分類、把 `backup_openclaw.sh` 改成
  `~/openclaw-backup/scripts/`）屬於改 cron 設定，本週依規定不改系統。
- **搬家偵測是啟發式的** —— 以檔名比對，同名檔案可能多筆，報告中會全部列出
  讓人自行判斷。
- **不追 symlink 的深層相依** —— wrapper 鏈只解析 `source` / `exec`，
  Python 內部 `import` 的相對路徑不在掃描範圍。
- **`nano-banana-pro-2`** 標記為失效，但該 job 已於 2026-08-26 停用，
  實務上無影響。

---

## 相關工具

- `2026-11-01-cron-truth-checker` — 比對 cron「狀態欄」與「實際輸出」，抓靜默失效。
  **本工具是它的互補**：那支回答「哪個 job 壞了」，這支回答「為什麼壞了、該改哪裡」。
- `2026-10-25-discord-safe-send` — 可驗證、去重的 Discord 發送工具。
