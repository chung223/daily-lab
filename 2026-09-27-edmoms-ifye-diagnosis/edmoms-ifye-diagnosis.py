#!/usr/bin/env python3
"""
EDMoms + IFYE 系統診斷工具
==============================
本週痛點（來源：2026-09-20~26 Daily Recap）：

1. EDMoms 驗證碼卡關 7 天（9/20-26）
   - 根本原因：9/20 已部署 edmom_captcha_solve.py（MLX OCR DeepSeek-OCR-2-bf16）
     但 edoms-check.js 從未呼叫它，仍用舊版 RapidOCR，導致：
     → 每日 8 次 OCR 失敗 → 帳號鎖定（密碼連續輸入錯誤 5 次）
     → 鎖定後隔天自動化繼續跑 → 再鎖一次
   - 證據：logs 顯示 "RapidOCR result: 8T3T" → "error.htm" → "帳號已鎖定"

2. IFYE 同步 2 個新問題（9/25-26）
   - Notion child_database.title 格式改變（9/25）：從「115_01_12來訪」變成
     「115_01_12_航班確認→專員跑流程、收集保單(總)」，只抓到 3/9 代表
   - Gary A. Ayuste 第3站、Justice Kwasi Etsey 第5及第6站縣市欄位空白

這個腳本：
  1. 檢查 EDMoms 帳號狀態（從 logs 推斷）
  2. 檢查 edmom_captcha_solve.py 是否被 edoms-check.js 呼叫（靜態分析）
  3. 檢查 IFYE sync 腳本的 Notion child_database.title 解析邏輯
  4. 產生改善提案（不改系統，只開處方）
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime, timedelta

# ──────────────── 路徑設定 ────────────────
HERMES_SCRIPTS = Path.home() / ".hermes" / "scripts"
EDOMS_LOG = Path.home() / ".hermes" / "logs" / "edoms-check.log"
EDOMS_CHECK = HERMES_SCRIPTS / "edoms-check.js"
EDOMS_LIB = HERMES_SCRIPTS / "edoms-check-lib.js"
EDOM_CAPTCHA_SOLVE = HERMES_SCRIPTS / "edmom_captcha_solve.py"
WORKSPACE = Path("/Users/chung/.openclaw/workspace")

IFYE_SYNC_SCRIPTS = list(WORKSPACE.glob("**/*ifye*sync*.js")) + list(WORKSPACE.glob("**/*ifye*sync*.py"))
IFYE_SYNC_SCRIPTS = [p for p in IFYE_SYNC_SCRIPTS if "node_modules" not in str(p) and "__pycache__" not in str(p)]


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check_edoms_status():
    """檢查 EDMoms 帳號狀態"""
    section("1️⃣  EDMoms 帳號狀態（從 logs 推斷）")

    if not EDOMS_LOG.exists():
        print("⚠️  無法讀取 edoms-check.log")
        return

    lines = EDOMS_LOG.read_text().splitlines()[-200:]

    locked_entries = []
    for line in lines:
        if "帳號已鎖定" in line or "帳號已鎖" in line:
            locked_entries.append(line)

    if locked_entries:
        print(f"❌ 帳號已鎖定（找到 {len(locked_entries)} 筆記錄）：")
        for e in locked_entries[-3:]:
            print(f"   {e}")
    else:
        last_attempts = [l for l in lines if "attempt" in l.lower() and "failed" in l.lower()]
        if last_attempts:
            print(f"⚠️  最近登入失敗（非帳號鎖定）：")
            for e in last_attempts[-2:]:
                print(f"   {e}")

    success_lines = [l for l in lines if "success" in l.lower() or "登入成功" in l or "login success" in l.lower()]
    if success_lines:
        print(f"✅  找到 {len(success_lines)} 筆成功記錄")
    else:
        print("❌  在近 200 行 log 中找不到任何成功記錄")


def check_captcha_integration():
    """檢查 edoms-check.js 是否呼叫了 MLX OCR 破解腳本"""
    section("2️⃣  EDMoms 驗證碼整合缺口分析")

    if not EDOMS_CHECK.exists():
        print(f"⚠️  找不到 {EDOMS_CHECK}")
        return

    content = EDOMS_CHECK.read_text()

    checks = {
        "edmom_captcha_solve.py（MLX OCR 方案）": "edmom_captcha_solve.py" in content,
        "tesseract 直接呼叫": "pytesseract" in content,
        "RapidOCR（舊）": "rapidocr" in content.lower() or "RapidOCR" in content,
        "subprocess + uvx MLX": "uvx" in content and "mlx" in content.lower(),
    }

    print("edoms-check.js 中的 OCR 策略：")
    for name, found in checks.items():
        print(f"  {'✅' if found else '❌'} {name}: {'有' if found else '無'}")

    if checks["edmom_captcha_solve.py（MLX OCR 方案）"]:
        print("\n✅ MLX OCR 方案已整合")
    else:
        print("\n❌ 根本問題：edmom_captcha_solve.py（9/20 已部署）從未被 edoms-check.js 呼叫")
        print("   現況：edoms-check.js 用 RapidOCR → 失敗 → 帳號鎖定")
        print("   解法：edoms-check.js 需在 OCR 階段呼叫 edmom_captcha_solve.py")


def check_ifye_notion_parsing():
    """檢查 IFYE sync 的 Notion child_database.title 解析邏輯"""
    section("3️⃣  IFYE Sync — Notion child_database.title 解析問題")

    if not IFYE_SYNC_SCRIPTS:
        print("⚠️  找不到 IFYE sync 腳本")
        return

    print(f"找到 {len(IFYE_SYNC_SCRIPTS)} 個 IFYE sync 腳本")
    print()

    for script_path in IFYE_SYNC_SCRIPTS[:5]:
        content = script_path.read_text()
        print(f"📄 {script_path.relative_to(WORKSPACE)}")

        child_db_lines = [l.strip() for l in content.splitlines()
                          if "child_database" in l.lower() or "database.title" in l.lower()
                          or "database_name" in l.lower()]
        if child_db_lines:
            print(f"   child_database 相關：{len(child_db_lines)} 處")
            for l in child_db_lines[:3]:
                print(f"     {l[:100]}")
        else:
            print("   ⚠️  無 child_database 相關程式碼")

        filter_lines = [l.strip() for l in content.splitlines()
                        if "startsWith" in l or "includes(" in l or "match(" in l]
        if filter_lines:
            print(f"   資料庫過濾：{len(filter_lines)} 處")
            for l in filter_lines[:3]:
                print(f"     {l[:100]}")
        print()


def generate_fix_proposal():
    """產生改善提案（不改系統，只開處方）"""
    section("5️⃣  改善提案（不改系統）")

    print("""
【提案 A】EDMoms 驗證碼整合修復
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
問題：edoms-check.js 用 RapidOCR，MLX OCR 方案（edmom_captcha_solve.py）未被呼叫
影響：帳號連續 7 天鎖定，公文流程完全停擺

處方（edoms-check.js 修改）：
  1. 在 OCR 階段，優先呼叫 subprocess 執行：
     python3 ~/.hermes/scripts/edmom_captcha_solve.py --auto
     讀取 captcha_result.txt 取得答案
  2. 失敗時降級 RapidOCR（現有邏輯）
  3. 連續 3 次失敗後主動停止並 alert，避免帳號鎖定
  4. 加入 --captcha-only 模式，解除鎖定後只解 captcha 不登入

處方代價：修改約 20 行 JavaScript

───────────────────────────────────────────

【提案 B】IFYE Notion child_database.title 寬鬆比對
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
問題：Notion 子資料庫標題從「115_01_12來訪」變成「115_01_12_航班確認→...」
      導致只抓到 3/9 代表

處方（sync 腳本修改）：
  1. 不要用完整 title 比對，改用 startsWith("115_01_12") 前綴比對
  2. 或用 relation 欄位（而非 title）當 primary key
  3. 比對失敗時同時 log 候選 title，供 human-in-the-loop 確認

處方代價：修改約 5 行 Python/JavaScript

───────────────────────────────────────────

【提案 C】Gary / Justice 縣市欄位空白
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
問題：兩位代表的特定站別縣市欄位在 Notion 是空白

處方：
  1. 查閱原始 Notion 記錄（115_01_12來訪資料庫）的人工確認
  2. 如果是 Notion 填寫缺失，回報對應窗口補填
  3. sync 腳本加入縣市空白時的 fallback邏輯（從代表所屬國家推斷）

處方代價：手動確認
""")


def main():
    print("🔍  EDMoms + IFYE 系統診斷")
    print(f"   執行時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   痛點來源：2026-09-20~26 Daily Recap")

    check_edoms_status()
    check_captcha_integration()
    check_ifye_notion_parsing()
    generate_fix_proposal()

    section("📊  總結")
    print("""
本週兩個主要問題的根本原因：
  1. EDMoms：整合缺口（方案有，但沒串上）
  2. IFYE：格式變化（Notion title drift）

兩者都不是新技術問題，是現有腳本缺少防呆機制。
建議優先處理【提案 A】（EDMoms 公文系統直接影響工作流程）。
""")


if __name__ == "__main__":
    main()
