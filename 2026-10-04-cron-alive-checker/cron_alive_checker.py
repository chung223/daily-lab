#!/usr/bin/env python3
"""
Cron Alive Checker — 確刊 cron 任務的依賴腳本是否還活著。

使用方式：
  python3 cron_alive_checker.py [--webhook-url URL] [--discord-webhook WEBHOOK_URL]
  python3 cron_alive_checker.py --test  # 只測試不回報

依賴腳本（過去 7 天 log 中出現過的）：
  - /Users/chung/.openclaw/workspace/scripts/discord_send.py
  - /Users/chung/.openclaw/workspace/scripts/crm_auto_sync.py
  - /Users/chung/.openclaw/workspace/skills/tyme4ts (目錄)
  - /Users/chung/.openclaw/workspace/skills/edoms-check-automation/edoms_check.js (Playwright)
  - /Users/chung/.openclaw/workspace/scripts/flight_tracker.py
  - /Users/chung/.openclaw/workspace/scripts/gmail_triage.py
  - /Users/chung/.openclaw/workspace/scripts/ifye_sync.py

通知目標：
  - Discord webhook（預設讀取 HERMES_DISCORD_WEBHOOK 或 discord_webhook 設定檔）
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ── 檢查項目 ──────────────────────────────────────────────
SCRIPT_CHECKS = [
    {
        "name": "discord_send.py",
        "path": "/Users/chung/.openclaw/workspace/scripts/discord_send.py",
        "severity": "critical",
        "note": "所有 cron 任務的通知骨幹；斷了所有推播都看不到"
    },
    {
        "name": "crm_auto_sync.py",
        "path": "/Users/chung/.openclaw/workspace/scripts/crm_auto_sync.py",
        "severity": "high",
        "note": "09:15 CRM 同步 cron 任務依賴；斷了等於沒有 CRM 同步"
    },
    {
        "name": "flight_tracker.py",
        "path": "/Users/chung/.openclaw/workspace/scripts/flight_tracker.py",
        "severity": "medium",
        "note": "接送機追蹤 cron 任務依賴"
    },
    {
        "name": "gmail_triage.py",
        "path": "/Users/chung/.openclaw/workspace/scripts/gmail_triage.py",
        "severity": "medium",
        "note": "Gmail 外文來信 triage cron 任務依賴"
    },
    {
        "name": "ifye_sync.py",
        "path": "/Users/chung/.openclaw/workspace/scripts/ifye_sync.py",
        "severity": "high",
        "note": "IFYE VPS 同步 cron 任務依賴"
    },
]

DIR_CHECKS = [
    {
        "name": "tyme4ts skill 目錄",
        "path": "/Users/chung/.openclaw/workspace/skills/tyme4ts",
        "severity": "medium",
        "note": "晨報 Morning Briefing 依賴；斷了晨報氣候/干支資訊失效"
    },
    {
        "name": "edoms-check-automation skill 目錄",
        "path": "/Users/chung/.openclaw/workspace/skills/edoms-check-automation",
        "severity": "critical",
        "note": "EDMoms 公文系統檢查自動化依賴；過去 7 天登入失敗 16+ 次"
    },
]

WEBHOOK_CHECK = {
    "name": "Discord webhook 可達性",
    "severity": "critical",
}

TZ_TPE = timezone(timedelta(hours=8))

def check_file(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.R_OK)

def check_dir(path: str) -> bool:
    return os.path.isdir(path)

def check_webhook(url: str, timeout: int = 10) -> tuple[bool, str]:
    """測量 webhook 是否可達（送一個簡單的 health check request）。"""
    if not url:
        return False, "未設定 webhook URL"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"content": "🔔 Cron Alive Checker 健康檢查"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if r.status in (200, 204):
                return True, f"✅ HTTP {r.status}"
            return False, f"⚠️ HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return False, f"⚠️ HTTP {e.code}"
    except Exception as e:
        return False, f"❌ {type(e).__name__}: {e}"

def load_webhook() -> str:
    # 1. 環境變數
    url = os.environ.get("HERMES_DISCORD_WEBHOOK")
    if url:
        return url
    # 2. 嘗試讀取設定檔
    config_paths = [
        "/Users/chung/.openclaw/workspace/config.json",
        "/Users/chung/.hermes/config.json",
    ]
    for p in config_paths:
        if os.path.isfile(p):
            try:
                with open(p) as f:
                    cfg = json.load(f)
                url = cfg.get("discord_webhook") or cfg.get("webhook")
                if url:
                    return url
            except Exception:
                pass
    return ""

def format_status(ok: bool) -> str:
    return "✅ 正常" if ok else "❌ 失效"

def build_report(test_only: bool = False) -> str:
    now = datetime.now(TZ_TPE).strftime("%Y-%m-%d %H:%M (台北時間)")
    lines = [
        f"## 🔬 Cron Alive Checker 報告",
        f"__{now}__",
        "",
    ]

    critical_fail = 0
    high_fail = 0

    # 檔案檢查
    for item in SCRIPT_CHECKS:
        ok = check_file(item["path"])
        if not ok:
            severity_icon = "🔴" if item["severity"] == "critical" else "🟠"
            lines.append(f"{severity_icon} **{item['name']}** — 檔案不存在或無法讀取")
            lines.append(f"   路徑：`{item['path']}`")
            lines.append(f"   影響：{item['note']}")
            lines.append("")
            if item["severity"] == "critical":
                critical_fail += 1
            else:
                high_fail += 1
        else:
            size = os.path.getsize(item["path"])
            lines.append(f"🟢 **{item['name']}** — 正常 ({size} bytes)")

    # 目錄檢查
    for item in DIR_CHECKS:
        ok = check_dir(item["path"])
        if not ok:
            severity_icon = "🔴" if item["severity"] == "critical" else "🟠"
            lines.append(f"{severity_icon} **{item['name']}** — 目錄不存在")
            lines.append(f"   路徑：`{item['path']}`")
            lines.append(f"   影響：{item['note']}")
            lines.append("")
            if item["severity"] == "critical":
                critical_fail += 1
            else:
                high_fail += 1
        else:
            files = os.listdir(item["path"])
            lines.append(f"🟢 **{item['name']}** — 正常 ({len(files)} 個檔案/目錄)")

    # Webhook 檢查
    webhook_url = "" if test_only else load_webhook()
    if webhook_url:
        ok, detail = check_webhook(webhook_url)
        icon = "🟢" if ok else "🔴"
        lines.append(f"{icon} **Discord webhook** — {detail}")
        if not ok:
            critical_fail += 1
    else:
        lines.append("⚪ **Discord webhook** — 未設定（跳過通知測試）")

    # 總結
    lines.append("")
    if critical_fail == 0 and high_fail == 0:
        lines.append("✅ **所有檢查通過，cron 任務應正常運作。**")
    else:
        fail_total = critical_fail + high_fail
        lines.append(f"⚠️ **{fail_total} 項失效**（{critical_fail} critical, {high_fail} high）")
        lines.append("請儘速修復，避免 cron 任務靜默失敗。")

    return "\n".join(lines)

def send_to_discord(message: str, webhook_url: str = "") -> bool:
    if not webhook_url:
        webhook_url = load_webhook()
    if not webhook_url:
        print("❌ 未設定 Discord webhook，無法發送通知。")
        return False
    try:
        payload = json.dumps({"content": message}).encode()
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status in (200, 204)
    except Exception as e:
        print(f"❌ Discord 發送失敗：{e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Cron Alive Checker")
    parser.add_argument("--test", action="store_true", help="只測試不回報 Discord")
    parser.add_argument("--webhook-url", dest="webhook_url", default="",
                        help="直接指定 Discord webhook URL（優先於設定檔）")
    parser.add_argument("--send", action="store_true", help="執行並發送 Discord 通知")
    args = parser.parse_args()

    webhook = args.webhook_url or ("" if args.test else load_webhook())
    report = build_report(test_only=args.test)

    print(report)
    print()

    if args.send and not args.test:
        ok = send_to_discord(report, webhook)
        if ok:
            print("✅ Discord 通知已發送。")
        else:
            print("❌ Discord 通知發送失敗（不回報以避免無限重試）。")
            sys.exit(1)
    elif args.test:
        print("（--test 模式：只測試，不發送 Discord）")
    else:
        print("加 --send 發送 Discord 通知，或加 --test 只做本地測試。")

if __name__ == "__main__":
    main()
