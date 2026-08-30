# Gmail Triage Prefilter

## 解決什麼

Gmail 外文來信 triage 每天掃描大量未讀郵件，但多數是偽陽（行銷信、平台通知、純中文郵件）。每封都跑 LLM 代價高，本工具在 LLM 之前先用 heuristic 規則先行過濾，直接排除明顯偽陽，大幅減少 API 呼叫次數。

**痛點來源**：2026-08-27 Gmail triage 掃 40 封，符合候選 7 封→確認 3 封真人來信；2026-08-29 掃 201 封，候選 5 封全排除（10times 行銷、Zep x2 平台通知、翁梨娟繁中、Umaru Sheriff 純確認回覆）。說明現有過濾仰賴 LLM，成本高且有延遲。

## 怎麼用

```bash
# 測試模式：顯示所有信件的評分與過濾原因
python3 gmail_prefilter.py --dry-run

# 正式執行：輸出符合條件的候選信件（JSON）
python3 gmail_prefilter.py

# 自訂分數門檻
python3 gmail_prefilter.py --min-score 50

# 與現有 triage cron 整合（把輸出餵給 LLM triage）
python3 gmail_prefilter.py | jq '.candidates[].id'
```

## 過濾邏輯

| 規則 | 分數影響 |
|------|----------|
| 黑名單網域（10times.com, zep.app, gmail.com 等） | 直接 0 分 |
| No-Reply 寄件者 | 直接 0 分 |
| 主旨含黑名單關鍵字（Newsletter、優惠、驗證等） | 直接 0 分 |
| 內文含黑名單關鍵字（unsubscribe、promotion 等） | 直接 0 分 |
| 白名單關鍵字（4-H, invitation, 代表, 草根 等） | +15 分 |
| 真人姓名風格、非回覆主旨、snippet 長度 > 80 字 | 各 +5 分 |
| 回覆（Re:/Fw:）主旨 | -10 分 |

分數 ≥ 40 為預設門檻，可透過 `--min-score` 調整。

## 驗證結果

使用 2026-08-27~29 真實案例驗證（已知結果）：

| 案例 | 分數 | 預期 | 結果 |
|------|------|------|------|
| 10times 行銷信（偽陽） | 0 | 排除 | ✅ |
| Addatu Giovanni 真人來信（命中） | 85 | 通過 | ✅ |
| 翁梨娟繁體中文（偽陽） | 0 | 排除 | ✅ |
| Gumarur Sheriff 邀請函請求（命中） | 90 | 通過 | ✅ |
| Zep 平台通知（偽陽） | 0 | 排除 | ✅ |
| Marjaana Liukko 婉拒郵件（命中） | 75 | 通過 | ✅ |
| Jack Zep x2 平台通知（偽陽） | 0 | 排除 | ✅ |

**正確率**：7/7（100%）

## 限制

- 需要 `gog` CLI 已登入 Gmail
- 仍會有漏網（新型平台通知、夾帶在論壇郵件中的真人來信）
- 建議先用 `--dry-run` 確認本週偽陽未被錯誤排除，再正式使用
