# 🔍 Cron Truth Checker

**比對 cron 的「狀態欄」與「實際輸出」，抓出靜默失效。**

---

## 解決什麼

Hermes cron 的狀態欄回報的是「**我執行完了**」，不是「**我做對了**」。

2026-10-31 晚間查核時發現一個具體例子：`Notion → Google Calendar` 的兩個排程
（`f07f7975cca4` 送機表／`5b58caed5417` 外國接送機表）從 **09-28 起累積 50+ 次失敗**，
資料從未寫入過 Google 行事曆——但 `hermes cron list` 的狀態欄四個排程**全部顯示 `ok`**，
`failure_streak` 乾淨地是 `0`。

這不是個案。本週（10/26～10/31）的 Daily Recap 裡反覆出現同一個形狀：

| 日期 | 事件 | 狀態欄怎麼說 |
|---|---|---|
| 10-26 | Notion→Calendar 靜默失效 **29 天** | `exit=2 (QUIET)` → 不告警 |
| 10-27 | 同上，累積 **50 次** | 不告警 |
| 10-28 | 每日備份連續失敗 **28 次** | 錯誤寫進 cron 錯誤欄，沒人看 |
| 10-30 | 11 個排程一起 `Connection error.` | 上午全死、下午全好，狀態欄看不出差別 |
| 10-31 | Discord 腳本回 `exit 0` 但**訊息不在頻道** | 靜默失敗再現 |
| 11-01 | 每日備份**連續第 35 次**失敗 | `failure_streak=35` |

三色蛋 10-31 的碎念講得很準：

> **cron 的狀態欄會說謊。** 排程回報的是「我執行完了」，不是「我做對了」。

這個工具把那句話變成可執行的檢查：**每次掃描，讀一次狀態欄，讀一次實際輸出，
兩邊對不上就出聲。**

它只讀取、不修改任何排程或系統設定。

---

## 怎麼用

```bash
# 人看的報告（預設 text 格式）
python3 cron_truth_checker.py

# 寫成 Markdown 報表
python3 cron_truth_checker.py --format markdown --out /tmp/cron-report.md

# 機器讀的 JSON（適合掛到排程或 CI）
python3 cron_truth_checker.py --format json

# 自訂路徑
python3 cron_truth_checker.py --jobs ~/.hermes/cron/jobs.json \
                              --output-dir ~/.hermes/cron/output
```

**Exit code**：有發現問題 → `1`；全部一致 → `0`。
所以可以直接掛進排程，出事時 exit 1 就能觸發通知。

### 建議用法：每天早上跑一次

```bash
#!/bin/bash
REPORT=$(python3 /path/to/cron_truth_checker.py)
if [ $? -ne 0 ]; then
  echo "$REPORT" | your_notify_command
fi
```

---

## 偵測邏輯

工具比對兩個來源：

1. **狀態欄** — `~/.hermes/cron/jobs.json` 的 `last_status` / `failure_streak`
2. **實際輸出** — `~/.hermes/cron/output/<job_id>/` 底下最新一個 `.md`

對每個 script 型排程（`no_agent: true`），從輸出檔切出執行結果，抽出 exit code，
再跟狀態欄對照：

| 情況 | 判定 | 嚴重度 |
|---|---|---|
| 狀態欄 `ok`，實際 `exit≠0` 或有錯誤訊號 | **靜默失效（diverged）** | 🔴 critical |
| 狀態欄自己就是 `error` | 排程回報失敗（failed） | 🟠 high |
| 狀態欄 `ok`，但輸出檔超過 3 天沒更新 | 輸出停滯（stale） | 🟡 medium |
| 排程啟用中，但從未產生輸出檔 | 無輸出檔（missing_output） | 🟡 medium |

### 失敗訊號

- `exit=<非 0>`（1、2、126、127 皆視為失敗；`exit=0` 視為成功）
- `**Status:** script failed`
- `Script execution failed:`
- `Traceback (most recent call last)`
- `RuntimeError:`
- `ERROR:腳本不存在`、`codec can't decode`、`command not found`

### 根因追蹤

偵測到失敗後，工具會往 **wrapper 腳本**追一層（最多兩層），
找出「到底缺哪個檔」，並驗證該檔現在是否仍然不存在：

```
oc-notion-sendoff.sh → oc-notion-sync.sh → sync_notion_sendoff_to_gcal.py（仍不存在）
```

同一支 wrapper 管兩條線時（sendoff / foreign），會用輸出文字的 token 重疊挑對檔案，
不會指錯。

### 避免誤報

- **已停用／暫停的排程直接略過**——它們本來就不該再跑，
  把六月停掉的 THSRC 舊失敗輸出當成「今天壞掉」是誤報。
- 成功報告裡的 `失敗：0` 不會被誤判成失敗（只認真正的失敗標記）。
- agent 型排程（`no_agent: false`）不在掃描範圍——它們的成敗由模型回報判定，
  判定規則是另一套，混在一起會製造噪音。

---

## 驗證結果（2026-11-01 實跑）

### 測試套件：40/40 通過

```bash
python3 test_cron_truth_checker.py
```

```
✅ detect_failure：exit=2 判為失敗
✅ detect_failure：exit=0 判為成功
✅ detect_failure：exit=127 判為失敗
✅ detect_failure：含『失敗：0』的成功報告不誤判
✅ detect_failure：script failed 判為失敗
✅ detect_failure：RuntimeError 判為失敗
✅ detect_failure：正常文字不誤判
✅ split_sections：script 輸出能切出 body
✅ split_sections：無分隔線時仍能切出 body（去掉標頭）
✅ split_sections：agent 型優先取 ## Response
✅ root_cause：抽出缺檔路徑
✅ root_cause：抽出編碼錯誤
✅ root_cause：無明確線索時回空字串（不亂猜）
✅ root_cause：從 wrapper 追出缺檔（memsync）
✅ root_cause：從 wrapper 追出缺檔（readmoo）
✅ root_cause：共用 wrapper 時挑對檔案（sendoff）
✅ root_cause：共用 wrapper 時挑對檔案（foreign）
✅ root_cause：正常排程不誤判缺檔
✅ scan：靜默失效被偵測到
✅ scan：靜默失效標為 critical
✅ scan：正常排程不被誤判
✅ scan：正常排程列入 ok 清單
✅ scan：狀態欄報錯者標為 failed
✅ scan：已停用排程被略過（不誤報）
✅ scan：靜默失效帶有根因
✅ CLI：有問題時 exit code = 1
✅ CLI：text 輸出含關鍵字『靜默失效』
✅ CLI：text 輸出含排程名稱
✅ CLI：json 格式可解析
✅ CLI：json 含 1 項發現
✅ CLI：json finding 含 root_cause 欄位
✅ CLI：markdown 含表格
✅ CLI：無問題時 exit code = 0
✅ CLI：無問題時顯示正常
✅ CLI：--out 可寫入報告檔
✅ 真實環境：掃描成功且有 script 排程
✅ 真實環境：偵測到靜默失效（Notion 兩個排程）
✅ 真實環境：每日備份被標為 failed 而非 diverged
✅ 真實環境：正常排程（行事曆格式糾察）不被誤判
✅ 真實環境：已停用排程不被誤報
==============================================================
通過 40 / 40（失敗 0）
```

### 真實環境掃描：抓到 6 項問題

```bash
python3 cron_truth_checker.py
```

```
🔍 Cron Truth Checker — 靜默失效偵測
掃描時間：2026-11-01T16:05:15.870117+08:00
排程總數：33（其中 script 型 10）

⚠️ 偵測到 6 項問題：

1. 🔴 嚴重｜Notion外國接送機→Calendar
   • 狀態欄宣稱：`ok`（failure_streak=0）
   • 實際輸出：notion-foreign exit=2 (ERROR:腳本不存在 .../sync_notion_foreign_transfer_to_gcal.py)
   • 根因：依賴腳本不存在：.../sync_notion_foreign_transfer_to_gcal.py（仍不存在）

2. 🔴 嚴重｜Notion送機表→Calendar
   • 狀態欄宣稱：`ok`（failure_streak=0）
   • 實際輸出：notion-sendoff exit=2 (ERROR:腳本不存在 .../sync_notion_sendoff_to_gcal.py)
   • 根因：依賴腳本不存在：.../sync_notion_sendoff_to_gcal.py（仍不存在）

3. 🔴 嚴重｜Readmoo每日特惠
   • 根因：依賴腳本不存在：.../readmoo_daily.py（由 oc-readmoo.sh 呼叫）

4. 🔴 嚴重｜npm安全週掃
   • 根因：依賴腳本不存在：.../npm_security_check.sh（由 oc-npmscan.sh 呼叫）

5. 🔴 嚴重｜記憶→agentmemory同步
   • 根因：依賴腳本不存在：.../sync_daily_memory_to_agentmemory.py（由 oc-memsync.sh 呼叫）

6. 🟠 高｜每日備份
   • 狀態欄宣稱：`error`（failure_streak=35）
   • 根因：編碼錯誤：utf-8 解碼失敗，通常代表上游指令輸出非 UTF-8 位元組

✅ 一致且正常：1 項 — 行事曆格式糾察
```

Exit code：`1`（有問題）。

### 逐項人工核對：6 項全部是真實故障

工具只報「輸出看起來像壞掉」，但「真的壞掉」需要人工確認。逐一檢查了
每個排程的 wrapper 腳本與實際檔案，6 項全部為真：

| 排程 | 依賴檔 | 實際狀態 |
|---|---|---|
| Notion 送機表 | `sync_notion_sendoff_to_gcal.py` | ❌ 不存在 |
| Notion 外國接送機 | `sync_notion_foreign_transfer_to_gcal.py` | ❌ 不存在 |
| Readmoo 每日特惠 | `readmoo_daily.py` | ❌ 不存在 |
| npm 安全週掃 | `npm_security_check.sh` | ❌ 不存在 |
| 記憶→agentmemory | `sync_daily_memory_to_agentmemory.py` | ❌ 不存在 |
| 每日備份 | `backup_openclaw.sh` | ❌ 不存在 |

```bash
$ cd /Users/chung/.openclaw/workspace/scripts
$ for f in sync_daily_memory_to_agentmemory.py readmoo_daily.py npm_security_check.sh \
           sync_notion_sendoff_to_gcal.py sync_notion_foreign_transfer_to_gcal.py; do
    if [ -e "$f" ]; then echo "EXISTS  $f"; else echo "MISSING $f"; fi
  done
MISSING sync_daily_memory_to_agentmemory.py
MISSING readmoo_daily.py
MISSING npm_security_check.sh
MISSING sync_notion_sendoff_to_gcal.py
MISSING sync_notion_foreign_transfer_to_gcal.py
```

**沒有誤報，也沒有漏報。**

---

## 這週真正壞掉的是什麼

工具只是把問題指出來，**沒有修改任何東西**（本工具是唯讀的）。
真正的修法在報告裡列出，但都要動到系統或排程，超出本工具範圍：

1. **補回 5 支遺失的腳本** —— `~/.openclaw/workspace/scripts/` 在 10-22 09:18 被清空重建，
   現存只剩 `crm_auto_sync.py`、`discord_send.py`、`recap_filter.py` 三檔。
   需從備份或版本庫還原：`sync_notion_sendoff_to_gcal.py`、
   `sync_notion_foreign_transfer_to_gcal.py`、`readmoo_daily.py`、
   `sync_daily_memory_to_agentmemory.py`、`backup_openclaw.sh`、`npm_security_check.sh`。
2. **每日備份的 utf-8 解碼錯誤** —— `oc-backup.sh` 把上游錯誤輸出當二進位讀取，
   需改成 `errors='replace'` 或用 `iconv` 轉換。
3. **把這個檢查掛進每日排程** —— 讓「安靜」不再等於「正常」。

---

## 為什麼不做成「修好所有東西」

本工具刻意**只讀取**。原因有兩個：

- 補腳本需要知道每支腳本的正確行為（例如 `sync_notion_sendoff_to_gcal.py`
  到底要寫哪些欄位到 Google 行事曆），那是需要還原與驗證的工作，
  不是猜一個檔案出來就算完成。
- 排程與系統設定的修改屬於另一種風險等級的工作，應該明確提出、由人決定。

工具的定位是：**讓問題不再安靜地發生。**

---

## 檔案

| 檔案 | 說明 |
|---|---|
| `cron_truth_checker.py` | 主程式（唯讀掃描） |
| `test_cron_truth_checker.py` | 測試套件（40 項） |
| `README.md` | 本文件 |
| `meta.json` | 中繼資料 |

## 相關

- `2026-10-04-cron-alive-checker` —— 檢查「被引用的腳本檔存在嗎」
  （靜態檢查）。本工具是它的後續：檢查「**實際跑出來的結果**對不對」
  （動態驗證）。兩者互補。

---

*建立於 2026-11-01 · Weekly Workbench*
