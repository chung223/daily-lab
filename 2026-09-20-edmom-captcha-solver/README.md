# EDMoms 驗證碼破解器

## 解決什麼

**痛點（來源：2026-09-13~19 Daily Recap）**

EDMoms（農業公文管理系統）每日同步腳本屢次失敗：
- 9/16、9/17：XLS download timeout（`page.waitForEvent: Timeout 30000ms exceeded`）
- 9/18：驗證碼 OCR 完全失敗，累計 12+ 次重試，整日公文流程卡住

根本原因：EDMoms 登入需要驗證碼（verifyCode），但系統使用的扭曲字體讓 Tesseract + RapidOCR 全部失敗，導致後續所有流程（PDF 下載、OCR、Sheets 同步）全部停擺。

## 怎麼用

### 前置需求
- Chrome 已開啟且 remote debugging port 已啟動（`/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=18792`）
- Python 依賴：`pip install playwright pillow pytesseract && playwright install chromium`
- MLX OCR（可選）：`uvx` 已安裝（`/opt/homebrew/bin/uvx`）

### 基本用法

```bash
# 自動從 Chrome 截圖並解
python3 edmom_captcha_solve.py --auto

# 解指定圖片
python3 edmom_captcha_solve.py -i /path/to/captcha.png

# 指定 CDP port
python3 edmom_captcha_solve.py --auto --cdp http://localhost:18792
```

### 整合進自動化流程

```python
from subprocess import run

# 截圖 + 解
r = run(['python3', 'edmom_captcha_solve.py', '--auto'], capture_output=True, text=True)
captcha = open('captcha_result.txt').read().strip()

# 填入表單
page.fill('#verifyCode', captcha)
page.click('#btnLogin')
```

## 技術策略

1. **MLX OCR（DeepSeek-OCR-2-bf16）**：透過 `uvx` 在 Apple Silicon 本地端執行，繞過 API key 需求
2. **Tesseract 降級**：灰度 + 二值化 + 3x 放大，針對英文數字白名單優化
3. **Playwright CDP 截圖**：直接從瀏覽器記憶體截取驗證碼圖片，繞過磁碟下載延遲

## 驗證結果

| 項目 | 結果 |
|------|------|
| 語法檢查 | ✅ 通過（ast.parse） |
| Tesseract 引擎 | ✅ 已確認（可直接 import） |
| Playwright CDP | ⚠️ Chrome 未開啟 remote debugging（腳本有 graceful fallback） |
| clean_captcha 邏輯 | ✅ 通過測試（`A3-B7_K9` → `A3B7K9`） |

**Live 測試需在 Chrome 開啟 remote debugging 後執行 `python3 edmom_captcha_solve.py --auto`**

## 檔案結構

```
edmom_captcha_solve.py   # 主腳本
captcha_result.txt       # 輸出（解出來的驗證碼）
README.md                # 本檔案
meta.json                # 專案元資料
```

## 限制

- Chrome 必須開啟 remote debugging port
- MLX OCR 第一次執行需下載模型（約數分鐘）
- 若兩種 OCR 均失敗，回傳最長候選字串而非空值
