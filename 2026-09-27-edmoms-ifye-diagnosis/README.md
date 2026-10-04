# EDMoms + IFYE 系統診斷工具

## 解決什麼

**痛點（來源：2026-09-20~26 Daily Recap）**

### 痛點 A：EDMoms 驗證碼卡關 7 天（9/20-26）
- **現象**：每日自動化跑 8 次登入，全部失敗，最後帳號鎖定（密碼連續錯誤 5 次）
- **根本原因**（靜態分析）：
  - 9/20 Weekly Workbench 已部署 `edmom_captcha_solve.py`（MLX OCR DeepSeek-OCR-2-bf16）
  - 但 `edoms-check.js` 從未呼叫它，仍用 RapidOCR
  - RapidOCR 對扭曲字體失敗 → 8 次錯誤輸入 → 帳號鎖定
  - 鎖定後隔天自動化繼續跑 → 再鎖一次，惡性循環
- **影響**：公文流程完全停擺，7 天無新公文通知

### 痛點 B：IFYE 同步 Notion title drift（9/25-26）
- **現象**：Notion 子資料庫標題從 `115_01_12來訪` 變成 `115_01_12_航班確認→專員跑流程、收集保單(總)`
- **根本原因**：sync 腳本用完整 title 比對，標題一變就抓不到
- **影響**：只抓到 3/9 代表，其餘 6 位待確認

### 痛點 C：Gary / Justice 縣市欄位空白
- **現象**：Gary A. Ayuste 第3站、Justice Kwasi Etsey 第5及第6站縣市欄位空白
- **根本原因**：Notion 填寫缺失或 sync 時未正確寫入
- **影響**：VPS 頁面顯示不完整

## 怎麼用

```bash
# 執行診斷（不改系統，只讀取與分析）
python3 edmoms-ifye-diagnosis.py

# 輸出：
#   1️⃣ EDMoms 帳號狀態（從 logs 推斷）
#   2️⃣ 驗證碼整合缺口分析
#   3️⃣ IFYE Sync Notion title drift 分析
#   5️⃣ 改善提案（不改系統，只開處方）
```

## 驗證結果

```
edoms-check.js 中的 OCR 策略：
  ❌ edmom_captcha_solve.py（MLX OCR 方案）: 無  ← 根本問題
  ❌ tesseract 直接呼叫: 無
  ✅ RapidOCR（舊）: 有                          ← 一直失敗

IFYE sync 腳本搜尋：
  ⚠️  請確認 IFYE sync 腳本位置（需同步更新搜尋路徑）
```

## 改善提案

### 提案 A（高優先）：EDMoms 驗證碼整合修復
**問題**：edoms-check.js 用 RapidOCR，MLX OCR 方案未被呼叫
**處方**（edoms-check.js 修改）：
1. 在 OCR 階段，優先呼叫 `subprocess` 執行 `python3 ~/.hermes/scripts/edmom_captcha_solve.py --auto`，讀取 `captcha_result.txt`
2. 失敗時降級 RapidOCR（現有邏輯）
3. 連續 3 次失敗後主動停止並 alert，避免帳號鎖定
4. 加入 `--captcha-only` 模式，解除鎖定後只解 captcha 不登入

### 提案 B（中優先）：IFYE Notion title 寬鬆比對
**問題**：Notion 子資料庫標題 drift
**處方**：
1. 改用 `startsWith("115_01_12")` 前綴比對
2. 或用 relation 欄位當 primary key
3. 比對失敗時 log 候選 title

### 提案 C（低優先）：Gary / Justice 縣市空白
**處方**：手動確認 Notion 原始記錄，補填後重新 sync

## 技術架構

- 純 Python，無外部依賴
- 靜態分析（讀取原始碼）+ log 模式分析
- 不修改任何系統檔案
- 支援離線執行
