#!/usr/bin/env python3
"""
IFYE 對外通訊追蹤器 v1.0

用途：將 Gmail triage 處理的 IFYE 外語郵件集中記錄，
擺脫「訊息散落在每日 recap、無法快速查詢現況」的困境。

狀態：🔴 緊急 / 🟡 追蹤 / 🟢 完成 / ⚪ 待確認

使用方式：
  python3 ifye_comms.py add --name "Roberta Lin" --subject "繳費電匯" \
      --status 🟡 --due "2025-10-20" --note "等待銀行帳號提供"
  python3 ifye_comms.py list
  python3 ifye_comms.py list --status 🔴
  python3 ifye_comms.py update 1 --status 🟢 --note "已完成電匯"
  python3 ifye_comms.py rm 1
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime, date
from typing import Optional

# ── 預設儲存位置 ───────────────────────────────────────────────
DEFAULT_DB = Path.home() / ".openclaw" / "workspace" / "data" / "ifye_comms.json"
DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)


# ── 資料結構 ───────────────────────────────────────────────────
FIELDNAMES = ["id", "name", "subject", "status", "due", "note", "created", "updated"]

DEFAULT_STATUS = "⚪"

def make_entry(
    name: str,
    subject: str,
    status: str = DEFAULT_STATUS,
    due: Optional[str] = None,
    note: Optional[str] = None,
) -> dict:
    now = datetime.now().strftime("%Y-%m-%d")
    return {
        "id": None,          # 稍後填入
        "name": name,
        "subject": subject,
        "status": status,
        "due": due,
        "note": note or "",
        "created": now,
        "updated": now,
    }


# ── ID 管理者 ───────────────────────────────────────────────────
def next_id(entries: list[dict]) -> int:
    used = {e["id"] for e in entries if e.get("id") is not None}
    return (max(used) + 1) if used else 1


# ── 儲存 ────────────────────────────────────────────────────────
def load(db_path: Path = DEFAULT_DB) -> list[dict]:
    if not db_path.exists():
        return []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def save(entries: list[dict], db_path: Path = DEFAULT_DB) -> None:
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ── 格式化輸出 ──────────────────────────────────────────────────
STATUS_ORDER = ["🔴", "🟡", "🟢", "⚪"]

def color_by_status(status: str) -> str:
    """狀態顏色提示（終端機著色）"""
    if status == "🔴":
        return "\033[91m"   # 紅
    elif status == "🟡":
        return "\033[93m"   # 黃
    elif status == "🟢":
        return "\033[92m"   # 綠
    return "\033[0m"        # 預設


def format_row(e: dict, color: bool = True) -> str:
    due = e["due"] or "—"
    note = e["note"] or ""
    status = e["status"]
    reset = "\033[0m" if color else ""
    sc = color_by_status(status) if color else ""

    overdue = ""
    if e["due"]:
        try:
            due_date = datetime.strptime(e["due"], "%Y-%m-%d").date()
            if due_date < date.today() and status not in ("🟢",):
                overdue = " ⚠️逾期"
        except ValueError:
            pass

    return (
        f"  [{e['id']:>3}]  {sc}{status}{reset}  {e['name']:<28}  "
        f"{e['subject']:<30}  到期:{due}{overdue}"
        + (f"\n       └ {note}" if note else "")
    )


def list_entries(
    entries: list[dict],
    status_filter: Optional[str] = None,
    color: bool = True,
) -> None:
    if status_filter:
        filtered = [e for e in entries if e["status"] == status_filter]
    else:
        filtered = entries

    if not filtered:
        msg = "沒有符合條件的記錄。" if status_filter else "目前沒有任何記錄。"
        print(f"  {msg}")
        return

    # 按狀態排序：🔴 → 🟡 → 🟢 → ⚪
    def sort_key(e):
        try:
            return STATUS_ORDER.index(e["status"])
        except ValueError:
            return len(STATUS_ORDER)
    filtered.sort(key=sort_key)

    print(f"\n═══ IFYE 對外通訊追蹤（共 {len(filtered)} 筆）═══")
    for e in filtered:
        print(format_row(e, color=color))


def summary(entries: list[dict]) -> None:
    counts = {}
    for e in entries:
        counts[e["status"]] = counts.get(e["status"], 0) + 1

    print("\n═══ 摘要 ═══")
    if not counts:
        print("  無記錄")
        return

    for s in STATUS_ORDER:
        if s in counts:
            sc = color_by_status(s)
            reset = "\033[0m"
            print(f"  {sc}{s}{reset}  {counts[s]} 筆")

    # 逾期提醒
    overdue = [
        e for e in entries
        if e["due"]
        and e["status"] not in ("🟢",)
        and e.get("id") is not None
    ]
    now = date.today()
    overdue_count = 0
    for e in overdue:
        try:
            if datetime.strptime(e["due"], "%Y-%m-%d").date() < now:
                overdue_count += 1
        except ValueError:
            pass

    if overdue_count:
        print(f"\n  ⚠️  {overdue_count} 筆已逾期！")

    print()


# ── 命令實作 ────────────────────────────────────────────────────
def cmd_add(args) -> None:
    entries = load(args.db)
    entry = make_entry(
        name=args.name,
        subject=args.subject,
        status=args.status or DEFAULT_STATUS,
        due=args.due,
        note=args.note,
    )
    entry["id"] = next_id(entries)
    entries.append(entry)
    save(entries, args.db)
    print(f"✓ 已新增 [{entry['id']}] {entry['name']} — {entry['subject']}")


def cmd_list(args) -> None:
    entries = load(args.db)
    list_entries(entries, status_filter=args.status, color=args.color)
    if not args.quiet:
        summary(entries)


def cmd_update(args) -> None:
    entries = load(args.db)
    target = next((e for e in entries if e["id"] == args.id_), None)
    if target is None:
        print(f"❌ 找不到 id={args.id_}", file=sys.stderr)
        sys.exit(1)

    if args.status is not None:
        target["status"] = args.status
    if args.note is not None:
        target["note"] = args.note
    if args.due is not None:
        target["due"] = args.due
    if args.name is not None:
        target["name"] = args.name
    if args.subject is not None:
        target["subject"] = args.subject

    target["updated"] = datetime.now().strftime("%Y-%m-%d")
    save(entries, args.db)
    print(f"✓ 已更新 [{target['id']}] {target['name']} — {target['subject']}")


def cmd_rm(args) -> None:
    entries = load(args.db)
    before = len(entries)
    entries = [e for e in entries if e["id"] != args.id_]
    if len(entries) == before:
        print(f"❌ 找不到 id={args.id_}", file=sys.stderr)
        sys.exit(1)
    save(entries, args.db)
    print(f"✓ 已刪除 id={args.id_}")


def cmd_export(args) -> None:
    entries = load(args.db)
    if args.format == "markdown":
        print("# IFYE 對外通訊追蹤\n")
        if not entries:
            print("_無記錄_")
        else:
            for e in sorted(entries, key=lambda x: x["id"] or 0):
                due = e["due"] or "無期限"
                print(f"## [{e['id']}] {e['status']} {e['name']}")
                print(f"- **主旨：** {e['subject']}")
                print(f"- **期限：** {due}")
                print(f"- **備註：** {e['note'] or '（無）'}")
                print(f"- **建檔：** {e['created']}｜**更新：** {e['updated']}")
                print()
    else:
        print(json.dumps(entries, ensure_ascii=False, indent=2))


# ── 主程式 ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="IFYE 對外通訊追蹤器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help=f"資料庫路徑（預設：{DEFAULT_DB}）",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="新增一筆通訊記錄")
    p_add.add_argument("--name", required=True, help="對方名稱")
    p_add.add_argument("--subject", required=True, help="郵件主旨 / 事由")
    p_add.add_argument("--status", default=DEFAULT_STATUS, help=f"狀態（預設：{DEFAULT_STATUS}）")
    p_add.add_argument("--due", help="期限（YYYY-MM-DD）")
    p_add.add_argument("--note", help="備註")
    p_add.set_defaults(func=cmd_add)

    # list
    p_ls = sub.add_parser("list", aliases=["ls"], help="列出所有記錄")
    p_ls.add_argument("--status", help=f"只顯示特定狀態（🔴/🟡/🟢/⚪）")
    p_ls.add_argument("--no-color", dest="color", action="store_false", default=True)
    p_ls.add_argument("--quiet", action="store_true", help="只列出條目，不顯示摘要")
    p_ls.set_defaults(func=cmd_list)

    # update
    p_up = sub.add_parser("update", help="更新指定記錄")
    p_up.add_argument("id_", type=int, help="記錄 ID")
    p_up.add_argument("--status", help=f"新狀態（🔴/🟡/🟢/⚪）")
    p_up.add_argument("--note", help="新備註")
    p_up.add_argument("--due", help="新期限（YYYY-MM-DD）")
    p_up.add_argument("--name", help="新名稱")
    p_up.add_argument("--subject", help="新主旨")
    p_up.set_defaults(func=cmd_update)

    # rm
    p_rm = sub.add_parser("rm", help="刪除指定記錄")
    p_rm.add_argument("id_", type=int, help="記錄 ID")
    p_rm.set_defaults(func=cmd_rm)

    # export
    p_exp = sub.add_parser("export", help="匯出資料")
    p_exp.add_argument("--format", choices=["json", "markdown"], default="markdown")
    p_exp.set_defaults(func=cmd_export)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
