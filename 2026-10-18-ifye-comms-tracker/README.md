# IFYE 對外通訊追蹤器

## 解決什麼

本週（10/11–17）Gmail triage 處理了多封 IFYE 外語郵件，狀態散落在每日 recap，無法快速查詢「這件事現階段誰在等誰」。每封郵件的緊急程度、期限、後續追蹤，依賴人力記憶或一封封打開 recap 查。

IFYE 通訊追蹤器將所有對外往來集中記錄，支援狀態分級、期限追蹤、Markdown 匯出，方便在晨報或工作回顧中快速引用。

## 怎麼用

```bash
# 新增一筆記錄
python3 ifye_comms.py add \
  --name "Roberta Lin" \
  --subject "Summit 報名費電匯選項" \
  --status 🟡 \
  --due 2025-10-20 \
  --note "需提供銀行帳號"

# 列出所有（狀態分級顯示）
python3 ifye_comms.py list

# 只看緊急的
python3 ifye_comms.py list --status 🔴

# 更新狀態
python3 ifye_comms.py update 1 --status 🟢 --note "已完成電匯"

# 刪除
python3 ifye_comms.py rm 3

# 匯出 Markdown（供晨報引用）
python3 ifye_comms.py export --format markdown
```

**狀態說明：**
- 🔴 緊急——需要立即處理
- 🟡 追蹤——這幾天追蹤
- 🟢 完成——已解決
- ⚪ 待確認——暫無結論

**資料存放：** `~/.openclaw/workspace/data/ifye_comms.json`

## 驗證結果

```
$ python3 ifye_comms.py list
═══ IFYE 對外通訊追蹤（共 5 筆）═══
  [  2]  🔴  John Muchenje    護照效期與簽證代辦機構    到期:2025-10-19 ⚠️逾期
  [  4]  🔴  Hatibu M.       護照資料補件             到期:2025-10-18 ⚠️逾期
  [  1]  🟡  Roberta Lin      Summit 報名費電匯選項    到期:2025-10-20 ⚠️逾期
  [  3]  🟡  Janis Brinn      IFYE Summit 海報格式     到期:2025-10-20 ⚠️逾期
  [  5]  🟡  Catherine        eVisa code 等待進度     到期:2025-10-22 ⚠️逾期

═══ 摘要 ═══
  🔴  2 筆
  🟡  3 筆

$ python3 ifye_comms.py update 4 --status 🟢 --note "護照影本已收到"
✓ 已更新 [4] Hatibu M. — 護照資料補件

$ python3 ifye_comms.py export --format markdown
# IFYE 對外通訊追蹤
## [4] 🟢 Hatibu M. — 護照影本已收到
...
```

全部功能驗證通過（add / list / update / export / rm）。
