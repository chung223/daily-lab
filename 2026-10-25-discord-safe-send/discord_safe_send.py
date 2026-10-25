#!/usr/bin/env python3
"""
discord_safe_send.py — 可驗證、去重的 Discord 發送工具

解決什麼
--------
2026-10-22、10-23、10-25 三天都發生 Discord 重複推播事故：
同一則 recap 被送出 2～4 則，另有測試訊息殘留，最後都靠人工呼叫
Discord REST API 逐一刪除（HTTP 204）才收拾乾淨。

根因有兩層：
1. 判定層：現有 `discord_send.py` 的 fallback 只看 stdout 裡有沒有
   "sent" 字樣就回 True，gateway 全掛時仍回報成功 → 上游以為沒送出，
   就再送一次。
2. 驗證層：gateway（127.0.0.1:18789）與任務控制中心（127.0.0.1:18792）
   掛掉時，`openclaw message read` 不可用，送完無法回讀確認。

本工具的做法
------------
- 直接走 Discord REST API（discord.com/api/v10），不依賴本機 gateway。
- 送出後立刻回讀（GET /channels/{id}/messages/{msg_id}）比對內容與頻道，
  確認落地才回 exit 0。
- 以 SHA-256（帳戶＋頻道＋訊息內容）寫入本機 ledger，同一則訊息在
  TTL 內重複送出 → 直接拒絕並提示既有 message id。
- 提供 --delete-id 清理（測試訊息、誤發重複），並支援 --prune-tests
  一次掃掉所有本工具產生的測試訊息。
- --dry-run 只做檢查不送。

用法
----
  # 一般發送（自動去重 + 回讀驗證）
  python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/msg.md

  # 測試訊息（自動標記、可一鍵清除）
  python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/t.md --test

  # 清除所有測試訊息
  python3 discord_safe_send.py --channel 1477728479209590834 --prune-tests

  # 刪除指定訊息（清理誤發重複）
  python3 discord_safe_send.py --channel 1477728479209590834 --delete-id 1563606673665425459

  # 預演
  python3 discord_safe_send.py --channel 1477728479209590834 --file /tmp/msg.md --dry-run

參數
----
  --channel     Discord Channel ID（必要）
  --account     帳戶 default / second（預設 default）
  --file        訊息來源檔（與 stdin 二選一）
  --test        送出測試訊息（自動加標記、可被 --prune-tests 清除）
  --prune-tests 清除本工具先前產生的測試訊息
  --delete-id   刪除指定 message id
  --force       略過去重檢查，強制送出
  --dry-run     只檢查不送出
  --ttl-hours   去重有效期（小時，預設 24）
  --ledger      ledger 檔案路徑（預設 ~/.cache/discord-safe-send/ledger.json）

輸出
----
  成功：stdout 印一行 JSON（含 ok / message_id / verified / sha256），exit 0
  失敗：stderr 印原因，exit 1
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASES = [
    "https://discord.com/api/v10",
    "https://canary.discord.com/api/v10",
    "https://ptb.discord.com/api/v10",
]
CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")
DEFAULT_LEDGER = os.path.expanduser("~/.cache/discord-safe-send/ledger.json")
TEST_MARK = "🧪[discord-safe-send-test]"

# 訊息長度上限（Discord 單則 2000 字）
MAX_LEN = 2000


# ── 工具 ──────────────────────────────────────────────────────
def load_token(account: str) -> str:
    """從 openclaw.json 讀出指定帳戶的 Discord bot token。"""
    env_key = f"DISCORD_TOKEN_{account.upper()}"
    if os.environ.get(env_key):
        return os.environ[env_key]
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(f"❌ 找不到設定檔：{CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    accounts = cfg.get("channels", {}).get("discord", {}).get("accounts", {})
    acct = accounts.get(account)
    if not acct or not acct.get("token"):
        raise SystemExit(f"❌ 設定檔中找不到 discord 帳戶「{account}」的 token")
    return acct["token"]


def api(token: str, method: str, path: str, payload=None, timeout=20):
    """呼叫 Discord REST API；自動在多個 base 之間容錯。"""
    last = None
    for base in API_BASES:
        url = f"{base}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "DiscordBot (discord-safe-send, 1.0)",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return resp.status, (json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            last = f"HTTP {e.code}: {body[:300]}"
            if e.code in (401, 403, 404):
                # 認證／權限／不存在 → 換 base 沒用
                return e.code, {"error": last}
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
    raise SystemExit(f"❌ Discord API 全部節點失敗：{last}")


# ── ledger ────────────────────────────────────────────────────
def sha(account: str, channel: str, message: str) -> str:
    return hashlib.sha256(f"{account}\x00{channel}\x00{message}".encode("utf-8")).hexdigest()


def load_ledger(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_ledger(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def find_duplicate(ledger: dict, digest: str, ttl_hours: float):
    """在 TTL 內找到相同內容的既有紀錄，回傳 (message_id, ts) 或 None。"""
    now = time.time()
    for rec in ledger.get("sent", {}).values():
        if rec.get("sha256") != digest:
            continue
        age_h = (now - rec.get("ts", 0)) / 3600.0
        if age_h <= ttl_hours:
            return rec.get("message_id"), rec.get("ts")
    return None


# ── 核心動作 ──────────────────────────────────────────────────
def do_send(token, account, channel, message, ledger_path, ttl_hours, force, test, dry_run):
    digest = sha(account, channel, message)

    if not force:
        dup = find_duplicate(load_ledger(ledger_path), digest, ttl_hours)
        if dup:
            mid, ts = dup
            print(json.dumps({
                "ok": False,
                "reason": "duplicate",
                "message_id": mid,
                "sent_at": ts,
                "sha256": digest,
                "hint": "內容與先前送出者完全相同，已跳過。若確實要重送請加 --force。",
            }, ensure_ascii=False))
            return 1

    if len(message) > MAX_LEN:
        print(json.dumps({
            "ok": False,
            "reason": "too_long",
            "length": len(message),
            "limit": MAX_LEN,
            "hint": "Discord 單則上限 2000 字，請拆分後再送。",
        }, ensure_ascii=False))
        return 1

    body = message if not test else f"{message}\n\n{TEST_MARK}"

    if dry_run:
        print(json.dumps({
            "ok": True, "dry_run": True, "sha256": digest,
            "length": len(body), "would_send": body,
        }, ensure_ascii=False))
        return 0

    status, resp = api(token, "POST", f"/channels/{channel}/messages", {"content": body})
    if status not in (200, 201):
        print(json.dumps({
            "ok": False, "reason": "send_failed", "http": status,
            "detail": resp.get("error", ""),
        }, ensure_ascii=False), file=sys.stderr)
        return 1

    mid = str(resp.get("id", ""))

    # 回讀驗證：確認這則訊息真的在頻道裡、內容相符
    verified = False
    vstatus, vresp = api(token, "GET", f"/channels/{channel}/messages/{mid}")
    if vstatus == 200 and vresp.get("id") == mid:
        verified = (vresp.get("content", "").strip() == body.strip())

    ledger = load_ledger(ledger_path)
    ledger.setdefault("sent", {})[digest] = {
        "sha256": digest,
        "message_id": mid,
        "ts": time.time(),
        "channel": channel,
        "account": account,
        "test": bool(test),
        "verified": verified,
    }
    save_ledger(ledger_path, ledger)

    print(json.dumps({
        "ok": True,
        "message_id": mid,
        "channel": channel,
        "account": account,
        "verified": verified,
        "test": bool(test),
        "sha256": digest,
        "length": len(body),
    }, ensure_ascii=False))
    return 0 if verified else 1


def do_delete(token, channel, message_id):
    status, resp = api(token, "DELETE", f"/channels/{channel}/messages/{message_id}")
    ok = status == 204
    print(json.dumps({"ok": ok, "deleted": message_id, "http": status,
                      "detail": resp.get("error", "")}, ensure_ascii=False))
    return 0 if ok else 1


def do_prune_tests(token, channel, ledger_path, scan=100):
    """清除本工具產生的測試訊息。

    兩個來源：
    1. ledger 中標記為 test 的紀錄
    2. 直接掃描頻道最近 scan 則訊息，找出帶 TEST_MARK 的
       （涵蓋 ledger 遺失、重啟後、或跨工具送出時留下的殘留）
    """
    ledger = load_ledger(ledger_path)
    targets = {r["message_id"] for r in ledger.get("sent", {}).values()
               if r.get("test") and r.get("message_id")}

    scanned = 0
    status, resp = api(token, "GET", f"/channels/{channel}/messages?limit={scan}")
    if status == 200 and isinstance(resp, list):
        scanned = len(resp)
        for m in resp:
            if TEST_MARK in (m.get("content") or ""):
                targets.add(str(m.get("id")))

    deleted, failed = [], []
    for mid in sorted(targets):
        st, _ = api(token, "DELETE", f"/channels/{channel}/messages/{mid}")
        (deleted if st == 204 else failed).append(mid)

    for digest, rec in list(ledger.get("sent", {}).items()):
        if rec.get("message_id") in deleted:
            del ledger["sent"][digest]
    save_ledger(ledger_path, ledger)

    print(json.dumps({"ok": not failed, "scanned": scanned, "found": len(targets),
                      "deleted": deleted, "failed": failed}, ensure_ascii=False))
    return 0 if not failed else 1


# ── CLI ───────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="可驗證、去重的 Discord 發送工具")
    p.add_argument("--channel", required=True)
    p.add_argument("--account", default="default")
    p.add_argument("--file")
    p.add_argument("--test", action="store_true")
    p.add_argument("--prune-tests", action="store_true")
    p.add_argument("--delete-id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ttl-hours", type=float, default=24.0)
    p.add_argument("--ledger", default=DEFAULT_LEDGER)
    args = p.parse_args()

    token = load_token(args.account)

    if args.delete_id:
        return do_delete(token, args.channel, args.delete_id)
    if args.prune_tests:
        return do_prune_tests(token, args.channel, args.ledger)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                message = f.read()
        except Exception as e:
            print(f"❌ 讀取檔案失敗：{e}", file=sys.stderr)
            return 1
    elif not sys.stdin.isatty():
        message = sys.stdin.read()
    else:
        message = ""

    message = message.strip()
    if not message:
        print("❌ 無訊息內容（--file 與 stdin 均無內容）", file=sys.stderr)
        return 1

    return do_send(token, args.account, args.channel, message,
                   args.ledger, args.ttl_hours, args.force, args.test, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
