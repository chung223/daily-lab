#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cron Truth Checker
==================

比對 Hermes cron 的「狀態欄」與「實際執行輸出」，抓出**靜默失效**：
排程回報 last_status=ok / failure_streak=0，但輸出檔裡其實寫著
`exit=2 (ERROR:腳本不存在 ...)` 這類失敗。

為什麼需要這個工具？
-------------------
2026-10-31 晚間查核發現：Notion→Google Calendar 的兩個排程
(f07f7975cca4 / 5b58caed5417) 從 09-28 起累積 50+ 次失敗，
但 `hermes cron list` 的狀態欄四個排程全部顯示 `ok`。
排程回報的是「我執行完了」，不是「我做對了」。

這個工具的邏輯很單純：
  1. 讀 jobs.json → 拿到每個排程「宣稱」的狀態（last_status / failure_streak）
  2. 讀 ~/.hermes/cron/output/<job_id>/*.md → 拿到最近一次「實際」輸出
  3. 對 script 型排程，從輸出檔的 Response 區段抽出 exit code 與錯誤訊號
  4. 兩邊對不上 → 標記為 DIVERGED（靜默失效）

只讀取、不修改任何排程或系統設定。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone

DEFAULT_JOBS = os.path.expanduser("~/.hermes/cron/jobs.json")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/.hermes/cron/output")
DEFAULT_EXEC_DB = os.path.expanduser("~/.hermes/cron/executions.db")
DEFAULT_SCRIPTS_DIR = os.path.expanduser("~/.hermes/scripts")

TZ = timezone(timedelta(hours=8))  # Asia/Taipei

# ─────────────────────────────────────────────────────────────
# 失敗訊號偵測
# ─────────────────────────────────────────────────────────────

# 明確宣告失敗的標記（出現在 script 排程的輸出本文）
HARD_FAIL_PATTERNS = [
    (re.compile(r"exit=(\d+)"), "exit_code"),           # <name> exit=2
    (re.compile(r"\*\*Status:\*\*\s*script failed"), "script_failed"),
    (re.compile(r"Script execution failed:"), "script_failed"),
    (re.compile(r"Traceback \(most recent call last\)"), "traceback"),
    (re.compile(r"RuntimeError:"), "runtime_error"),
]

# 出現這些字樣就算失敗（即使沒有 exit=）
ERROR_WORDS = [
    "ERROR:腳本不存在",
    "codec can't decode",
    "command not found",
    "No such file or directory",
]

# exit code 意義：0=成功，其餘皆視為失敗
FAIL_EXIT_CODES = {1, 2, 126, 127}

# 反向：這些字樣代表「成功」，即使 exit code 非 0 也不該誤判
# （例如某些排程以 exit=2 表示「無新資料，無需處理」的慣例）
# 經實測：memsync / readmoo 的 exit=2 確實是失敗，故不設任何豁免白名單。

# ─────────────────────────────────────────────────────────────
# 資料結構
# ─────────────────────────────────────────────────────────────

@dataclass
class Finding:
    job_id: str
    name: str
    severity: str            # critical / high / medium
    kind: str                # diverged / failed / stale / missing_output
    claimed_status: str      # jobs.json 宣稱的狀態
    claimed_streak: int
    actual: str              # 實際輸出摘要
    detail: str
    last_run: str = ""
    output_file: str = ""
    root_cause: str = ""     # 推測的根因（例如：依賴腳本不存在）

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Report:
    generated_at: str = ""
    scanned_jobs: int = 0
    scanned_script_jobs: int = 0
    findings: list = field(default_factory=list)
    ok_jobs: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "scanned_jobs": self.scanned_jobs,
            "scanned_script_jobs": self.scanned_script_jobs,
            "finding_count": len(self.findings),
            "findings": [f.to_dict() for f in self.findings],
            "ok_jobs": self.ok_jobs,
            "notes": self.notes,
        }


# ─────────────────────────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────────────────────────

def load_jobs(path: str) -> list:
    if not os.path.exists(path):
        raise SystemExit(f"[FATAL] 找不到 jobs.json：{path}")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    return jobs


def latest_output(job_id: str, output_dir: str):
    """回傳 (檔案路徑, 檔案 mtime datetime)"""
    files = glob.glob(os.path.join(output_dir, job_id, "*.md"))
    if not files:
        return None, None
    latest = max(files, key=os.path.getmtime)
    return latest, datetime.fromtimestamp(os.path.getmtime(latest), TZ)


def split_sections(text: str) -> dict:
    """把 cron 輸出檔切成 metadata / body / response 三段。

    檔案格式（script 型）：
        # Cron Job: <name>
        **Job ID:** ...
        **Run Time:** ...
        **Mode:** no_agent (script)
        ---
        <body>

    agent 型則在尾端多一段 "## Response"。
    """
    sections = {"meta": "", "body": "", "response": ""}

    if "## Response" in text:
        head, _, resp = text.partition("## Response")
        sections["response"] = resp.strip()
        text = head
    else:
        sections["response"] = ""

    # 找第一條 "---" 分隔線：其前為 meta，其後為 body
    lines = text.split("\n")
    sep_idx = None
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            sep_idx = i
            break
    if sep_idx is not None:
        sections["meta"] = "\n".join(lines[:sep_idx])
        body = "\n".join(lines[sep_idx + 1:]).strip()
        sections["body"] = body
    else:
        # 沒有 "---" 分隔線的格式（例如 script failed 的輸出檔），
        # 逐行濾掉固定標頭欄位，剩下的就是實際輸出。
        sections["meta"] = "\n".join(lines[:6])
        kept = []
        for ln in lines:
            if ln.startswith("# Cron Job:"):
                continue
            if re.match(r"^\*\*(Job ID|Run Time|Mode|Schedule):\*\*", ln):
                continue
            kept.append(ln)
        sections["body"] = "\n".join(kept).strip()

    # script 型沒有 ## Response，body 就是全部
    if not sections["response"]:
        sections["response"] = sections["body"]
    return sections


def detect_failure(body: str):
    """從 script 排程輸出本文偵測失敗。回傳 (ok, code, detail)"""
    for pat, kind in HARD_FAIL_PATTERNS:
        m = pat.search(body)
        if m:
            if kind == "exit_code":
                code = int(m.group(1))
                if code in FAIL_EXIT_CODES:
                    return False, code, f"exit={code}"
                # exit=0 明確成功
                return True, 0, "exit=0"
            return False, None, kind
    for w in ERROR_WORDS:
        if w in body:
            return False, None, w
    return True, None, ""


def summarize(body: str, limit: int = 160) -> str:
    one = " ".join(body.split())
    return one[:limit] + ("…" if len(one) > limit else "")


def find_root_cause(body: str, job: dict = None, scripts_dir: str = None) -> str:
    """從輸出內容推測根因，讓報告能直接指出「缺哪個檔」。

    兩段式：
      1. 先看輸出本身有沒有明確線索（缺檔路徑、編碼錯誤…）
      2. 輸出沒說清楚時，去看排程的 wrapper 腳本，
         找出它呼叫的 python 檔，檢查是否真的不存在
    """
    m = re.search(r"ERROR:腳本不存在\s+(\S+)", body)
    if m:
        path = m.group(1)
        exists = os.path.exists(path)
        return f"依賴腳本不存在：{path}" + ("（仍不存在）" if not exists else "（現已存在）")
    m = re.search(r"'([^']+)' codec can't decode", body)
    if m:
        return f"編碼錯誤：{m.group(1)} 解碼失敗，通常代表上游指令輸出非 UTF-8 位元組"
    m = re.search(r"command not found", body)
    if m:
        return "指令不存在（command not found）"
    if "RuntimeError: Chrome did not start" in body:
        return "無 agent 腳本例外：Chrome 未啟動"
    if "Traceback" in body:
        return "Python 例外（見輸出檔 traceback）"

    # ── 第二段：從 wrapper 腳本找出真正缺哪個檔 ──
    if job:
        script = job.get("script")
        if script:
            scripts_dir = scripts_dir or DEFAULT_SCRIPTS_DIR
            # 最多追兩層 wrapper（例：oc-notion-sendoff.sh → oc-notion-sync.sh）
            seen = set()
            queue = [os.path.join(scripts_dir, script)]
            while queue:
                wrapper = queue.pop(0)
                if wrapper in seen or not os.path.exists(wrapper):
                    continue
                seen.add(wrapper)
                try:
                    txt = open(wrapper, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                # 優先挑「輸出文字裡也出現過」的候選，避免同一支 wrapper
                # 管兩條線時指錯檔案
                cands = sorted(set(re.findall(
                    r"/Users/[^\s\"']+\.(?:py|sh)", txt)))
                missing = [c for c in cands if not os.path.exists(c)]
                if missing:
                    pick = None
                    # (a) 輸出文字直接出現完整檔名
                    hit = [c for c in missing if os.path.basename(c) in body]
                    if hit:
                        pick = hit[0]
                    else:
                        # (b) 以關鍵 token 重疊挑選（例如輸出說 sendoff，
                        #     候選有 sync_notion_sendoff_to_gcal.py）
                        body_tokens = set(re.findall(r"[a-z]{4,}", body.lower()))
                        best, best_score = None, 0
                        for c in missing:
                            toks = set(re.findall(r"[a-z]{4,}",
                                                  os.path.basename(c).lower()))
                            score = len(body_tokens & toks)
                            if score > best_score:
                                best, best_score = c, score
                        pick = best
                    if pick is None:
                        # 完全沒有 token 重疊（wrapper 只管一條線的常見情況）
                        pick = missing[0]
                    return (f"依賴腳本不存在：{pick}"
                            f"（由 {os.path.basename(wrapper)} 呼叫）")
                # 若這個 wrapper 只是轉呼叫同目錄的另一支 .sh，跟進一層
                for ref in sorted(set(re.findall(
                        r"(?:bash|exec bash)\s+([^\s\"']+\.sh)", txt))):
                    if not ref.startswith("/"):
                        ref = os.path.join(scripts_dir, ref)
                    if os.path.abspath(ref) != os.path.abspath(wrapper):
                        queue.append(ref)
    return ""


def is_stale(job: dict, last_out_dt, now: datetime, stale_days: int = 3) -> bool:
    """排程宣稱有跑，但輸出檔很久沒更新 → 可能排程已停擺。"""
    if last_out_dt is None:
        return False
    return (now - last_out_dt) > timedelta(days=stale_days)


# ─────────────────────────────────────────────────────────────
# 主掃描
# ─────────────────────────────────────────────────────────────

def scan(jobs_path: str, output_dir: str, stale_days: int = 3) -> Report:
    now = datetime.now(TZ)
    rep = Report(generated_at=now.isoformat())
    jobs = load_jobs(jobs_path)
    rep.scanned_jobs = len(jobs)

    for job in jobs:
        jid = job.get("id")
        if not jid:
            continue
        name = job.get("name") or jid
        claimed_status = job.get("last_status") or "unknown"
        streak = job.get("failure_streak")
        streak = streak if isinstance(streak, int) else 0

        if not job.get("no_agent"):
            continue  # 只檢查 script 型排程（agent 型的成敗由模型回報判定，另論）
        rep.scanned_script_jobs += 1

        # 已停用 / 暫停的排程不列入檢查——它們本來就不該再跑，
        # 把舊的失敗輸出當成「今天壞掉」是誤報。
        if not job.get("enabled"):
            rep.notes.append(
                f"略過已停用排程：{name}（最後執行 {job.get('last_run_at') or '無'}）")
            continue

        out_path, out_dt = latest_output(jid, output_dir)

        if out_path is None:
            if job.get("enabled"):
                rep.findings.append(Finding(
                    job_id=jid, name=name, severity="medium", kind="missing_output",
                    claimed_status=claimed_status, claimed_streak=streak,
                    actual="（無輸出檔）", detail="排程已啟用但從未產生任何輸出檔",
                    last_run=job.get("last_run_at") or "",
                ))
            continue

        text = open(out_path, encoding="utf-8", errors="replace").read()
        sec = split_sections(text)
        body = sec["body"] or sec["response"]
        ok, code, detail = detect_failure(body)

        age = now - (out_dt or now)

        # ── 情況 A：宣稱 ok，實際失敗 → 靜默失效（核心） ──
        if claimed_status == "ok" and not ok:
            rep.findings.append(Finding(
                job_id=jid, name=name, severity="critical", kind="diverged",
                claimed_status=claimed_status, claimed_streak=streak,
                actual=summarize(body), detail=f"狀態欄顯示 ok，但輸出實際失敗（{detail}）",
                last_run=job.get("last_run_at") or "",
                output_file=out_path,
                root_cause=find_root_cause(body, job),
            ))
            continue

        # ── 情況 B：狀態欄自己也說 error ──
        if claimed_status in ("error", "failed"):
            rep.findings.append(Finding(
                job_id=jid, name=name, severity="high", kind="failed",
                claimed_status=claimed_status, claimed_streak=streak,
                actual=summarize(body) or (job.get("last_error") or "")[:160],
                detail=f"排程回報失敗（failure_streak={streak}）：{job.get('last_error') or detail}",
                last_run=job.get("last_run_at") or "",
                output_file=out_path,
                root_cause=(find_root_cause(body, job)
                            or find_root_cause(job.get("last_error") or "", job)),
            ))
            continue

        # ── 情況 C：宣稱 ok，但輸出檔很久沒更新 ──
        if is_stale(job, out_dt, now, stale_days) and age > timedelta(days=stale_days):
            rep.findings.append(Finding(
                job_id=jid, name=name, severity="medium", kind="stale",
                claimed_status=claimed_status, claimed_streak=streak,
                actual=f"最後輸出 {out_dt.strftime('%Y-%m-%d %H:%M')}（{age.days} 天前）",
                detail=f"排程啟用中，但輸出已 {age.days} 天未更新",
                last_run=job.get("last_run_at") or "",
                output_file=out_path,
            ))
            continue

        rep.ok_jobs.append({
            "job_id": jid, "name": name,
            "last_run": job.get("last_run_at") or "",
            "output": summarize(body, 100),
        })

    rep.findings.sort(key=lambda f: ({"critical": 0, "high": 1, "medium": 2}[f.severity], f.name))
    return rep


# ─────────────────────────────────────────────────────────────
# 輸出
# ─────────────────────────────────────────────────────────────

SEV_LABEL = {"critical": "🔴 嚴重", "high": "🟠 高", "medium": "🟡 中"}
KIND_LABEL = {
    "diverged": "靜默失效（狀態欄說 ok，實際失敗）",
    "failed": "排程回報失敗",
    "stale": "輸出停滯",
    "missing_output": "無輸出檔",
}


def render_text(rep: Report) -> str:
    L = []
    L.append("🔍 Cron Truth Checker — 靜默失效偵測")
    L.append(f"掃描時間：{rep.generated_at}")
    L.append(f"排程總數：{rep.scanned_jobs}（其中 script 型 {rep.scanned_script_jobs}）")
    L.append("")
    if not rep.findings:
        L.append("✅ 沒有偵測到靜默失效：所有 script 型排程的狀態欄與實際輸出一致。")
    else:
        L.append(f"⚠️ 偵測到 {len(rep.findings)} 項問題：")
        L.append("")
        for i, f in enumerate(rep.findings, 1):
            L.append(f"{i}. {SEV_LABEL[f.severity]}｜{f.name}")
            L.append(f"   • 類型：{KIND_LABEL[f.kind]}")
            L.append(f"   • Job ID：{f.job_id}")
            L.append(f"   • 狀態欄宣稱：`{f.claimed_status}`（failure_streak={f.claimed_streak}）")
            L.append(f"   • 實際輸出：{f.actual}")
            L.append(f"   • 說明：{f.detail}")
            if f.root_cause:
                L.append(f"   • 根因：{f.root_cause}")
            if f.last_run:
                L.append(f"   • 最後執行：{f.last_run}")
            L.append("")
    if rep.ok_jobs:
        L.append(f"✅ 一致且正常：{len(rep.ok_jobs)} 項 — " +
                 "、".join(j["name"] for j in rep.ok_jobs))
    return "\n".join(L)


def render_markdown(rep: Report) -> str:
    L = []
    L.append("# 🔍 Cron Truth Checker 報告")
    L.append("")
    L.append(f"- **掃描時間**：{rep.generated_at}")
    L.append(f"- **排程總數**：{rep.scanned_jobs}（script 型 {rep.scanned_script_jobs}）")
    L.append(f"- **問題數**：{len(rep.findings)}")
    L.append("")
    if rep.findings:
        L.append("| 嚴重度 | 排程 | Job ID | 狀態欄 | 實際 | 根因 |")
        L.append("|---|---|---|---|---|---|")
        for f in rep.findings:
            L.append(f"| {SEV_LABEL[f.severity]} | {f.name} | `{f.job_id}` | `{f.claimed_status}` | "
                     f"{f.actual.replace('|','／')} | {(f.root_cause or f.detail).replace('|','／')} |")
    else:
        L.append("✅ 未偵測到靜默失效。")
    L.append("")
    if rep.ok_jobs:
        L.append("## 正常且一致")
        for j in rep.ok_jobs:
            L.append(f"- ✅ {j['name']} — {j['output']}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description="比對 Hermes cron 狀態欄與實際輸出，抓出靜默失效")
    ap.add_argument("--jobs", default=DEFAULT_JOBS, help="jobs.json 路徑")
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="cron 輸出目錄")
    ap.add_argument("--format", choices=["text", "json", "markdown"], default="text")
    ap.add_argument("--out", help="把報告寫到檔案")
    ap.add_argument("--quiet-ok", action="store_true", help="沒有問題時只輸出最短訊息")
    args = ap.parse_args()

    rep = scan(args.jobs, args.output_dir)

    if args.format == "json":
        out = json.dumps(rep.to_dict(), ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        out = render_markdown(rep)
    else:
        out = render_text(rep)
        if args.quiet_ok and not rep.findings:
            out = "✅ Cron Truth Checker：未偵測到靜默失效。"

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"[OK] 報告已寫入 {args.out}（{len(rep.findings)} 項問題）")
    else:
        print(out)

    # 有問題時 exit=1，方便排程或 CI 判斷
    sys.exit(1 if rep.findings else 0)


if __name__ == "__main__":
    main()
