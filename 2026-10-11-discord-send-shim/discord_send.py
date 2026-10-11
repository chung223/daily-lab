#!/usr/bin/env python3
"""
discord_send.py — 相容舊指令稿介面的 Discord 發送 Shim

用途：
  所有 cron 任務原本呼叫 /Users/chung/.openclaw/workspace/scripts/discord_send.py，
  該檔案從未建立。本腳本補足此缺口。

使用方式（與舊介面完全相容）：
  cat FILE | python3 discord_send.py --account default --channel CHANNEL_ID
  python3 discord_send.py --account default --channel CHANNEL_ID < FILE
  python3 discord_send.py --account default --channel CHANNEL_ID --file FILE
  echo "訊息" | python3 discord_send.py --account default --channel CHANNEL_ID

參數：
  --account   帳戶名稱（default / second）
  --channel   Discord Channel ID（必要）
  --file      從檔案讀取訊息（與 stdin 二選一）
  --url       任務控制中心 URL（預設 http://127.0.0.1:18792）
  --fallback  當 HTTP API 失效時，直接用 openclaw CLI 發送（自動，預設開啟）
  --no-fallback  停用 openclaw CLI fallback，只用 HTTP API
  --help      顯示說明

輸出：
  成功：無輸出（符合原本行為）
  失敗：非零 exit code，錯誤訊息到 stderr
"""

import sys
import os
import json
import argparse
import subprocess

# ── 預設值 ─────────────────────────────────────────────────
DEFAULT_URL = "http://127.0.0.1:18792"
DEFAULT_ACCOUNT = "default"


def get_message() -> str:
    """從 stdin 或 --file 讀取訊息內容。"""
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


def send_via_http(message: str, channel_id: str, account: str, base_url: str) -> tuple[bool, str]:
    """發送訊息到本地任務控制中心 /api/discord 路由。"""
    import urllib.request
    import urllib.error

    url = f"{base_url.rstrip('/')}/api/discord"

    payload = {
        "target": "discord",
        "channel": account,
        "message": message,
        "guildId": str(channel_id) if channel_id else "",
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status in (200, 204):
                return True, f"HTTP {resp.status}"
            return False, f"HTTP {resp.status}: {body[:200]}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body[:200]}"
    except ConnectionRefusedError:
        return False, "CONN_REFUSED"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def send_via_openclaw(message: str, channel_id: str, account: str) -> tuple[bool, str]:
    """Fallback：直接呼叫 openclaw CLI 發送 Discord 訊息。"""
    try:
        # 目標格式：channel:CHANNEL_ID（以數字開頭，Discord 频道 ID）
        target = f"channel:{channel_id}" if channel_id.isdigit() else channel_id
        result = subprocess.run(
            [
                "openclaw", "message", "send",
                "--channel", "discord",
                "--target", target,
                "--message", message,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # 檢查是否真的發送成功
            try:
                output = json.loads(result.stdout) if result.stdout else {}
                if output.get("payload", {}).get("deliveryStatus") == "sent":
                    return True, "openclaw OK"
            except (json.JSONDecodeError, KeyError):
                pass
            # returncode 0 但 deliveryStatus 不是 sent
            if result.stdout and ("sent" in result.stdout.lower() or "ok" in result.stdout.lower()):
                return True, "openclaw OK"
            return False, f"openclaw exit 0 but not delivered: {result.stdout[:200]}"
        return False, f"openclaw exit {result.returncode}: {result.stderr[:200]}"
    except FileNotFoundError:
        return False, "openclaw CLI not found"
    except subprocess.TimeoutExpired:
        return False, "openclaw timeout"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Discord 訊息發送 Shim（相容舊指令稿介面）",
        usage="discord_send.py --account default --channel CHANNEL_ID [--file FILE]",
    )
    parser.add_argument("--account", default=DEFAULT_ACCOUNT, help="帳戶名稱（default/second）")
    parser.add_argument("--channel", default=None, help="Discord Channel ID（必要）")
    parser.add_argument("--file", default=None, help="從檔案讀取訊息內容")
    parser.add_argument(
        "--url",
        default=os.environ.get("TASK_CENTER_URL", DEFAULT_URL),
        help=f"任務控制中心 URL（預設 {DEFAULT_URL}）",
    )
    parser.add_argument("--no-fallback", dest="no_fallback", action="store_true",
                        help="停用 openclaw CLI fallback，只用 HTTP API")
    parser.add_argument("positional", nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # ── 讀取訊息 ─────────────────────────────────────────
    message = ""
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                message = f.read()
        except FileNotFoundError:
            print(f"❌ 找不到檔案：{args.file}", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"❌ 讀取檔案失敗：{e}", file=sys.stderr)
            return 1
    else:
        if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
            message = sys.stdin.read()
    if args.positional:
        message = " ".join(args.positional)

    message = message.strip()
    if not message:
        print("❌ 無訊息內容（stdin 和 --file 均無內容）", file=sys.stderr)
        return 1

    # ── 發送 ─────────────────────────────────────────────
    channel_id = args.channel or os.environ.get("DISCORD_CHANNEL", "")

    # 策略 1：HTTP API
    ok, detail = send_via_http(message, channel_id, args.account, args.url)

    # 策略 2：openclaw CLI fallback（當 HTTP 失效或被禁用時）
    use_fallback = (not ok) and (not args.no_fallback)
    if use_fallback:
        ok2, detail2 = send_via_openclaw(message, channel_id, args.account)
        if ok2:
            ok = True
            detail = f"{detail} → {detail2}"
        else:
            # 兩個都失敗，報告兩者錯誤
            detail = f"HTTP: {detail}; openclaw: {detail2}"

    if ok:
        # 靜默成功（符合原本行為）
        return 0
    else:
        print(f"❌ 發送失敗：{detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
