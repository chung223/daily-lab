#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_path_audit.py — Cron 路徑與技能引用健檢

解決的問題
----------
Hermes cron 的每個 job 有兩層引用：
  (1) job 欄位：prompt / command / script
  (2) no_agent job 的 `script` 指向一個 wrapper shell（~/.hermes/scripts/oc-*.sh），
      wrapper 裡面再呼叫真正的 .py / .sh 腳本

只檢查第 (1) 層會漏掉真正壞掉的東西 —— 例如 Notion→Google Calendar 兩個排程
連續 70 天失敗，根因是 `oc-notion-sync.sh` 裡呼叫的
`/Users/chung/.openclaw/workspace/scripts/sync_notion_sendoff_to_gcal.py` 不存在，
但那個字串不在 job 的 prompt 裡，只在 wrapper 裡。

本工具兩層都掃，並把技能引用一起健檢（技能搬家 / 被封存）。

唯讀：不修改任何 cron 設定、jobs.json 或技能檔案。
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

DEFAULT_JOBS = os.path.expanduser("~/.hermes/cron/jobs.json")
DEFAULT_SKILL_DIRS = [
    os.path.expanduser("~/.hermes/skills"),
    os.path.expanduser("~/.openclaw/workspace/skills"),
]
WRAPPER_DIRS = [
    os.path.expanduser("~/.hermes/scripts"),
    os.path.expanduser("~/.openclaw/workspace/scripts"),
]
ARCHIVE_DIR = os.path.expanduser("~/.hermes/skills/.archive")

# 搜尋「檔案搬到哪裡去了」時掃描的根目錄
SEARCH_ROOTS = [
    os.path.expanduser("~/.hermes/scripts"),
    os.path.expanduser("~/.openclaw/workspace/scripts"),
    os.path.expanduser("~/openclaw-backup/scripts"),
    os.path.expanduser("~/.hermes/skills"),
    os.path.expanduser("~/.openclaw/workspace"),
]

# ── 路徑抽取 ────────────────────────────────────────────────
PATH_RE = re.compile(
    r"(?:\$\{?HOME\}?|/Users/[A-Za-z0-9._-]+|~)"
    r"/[^\s\"'`>,;)\]}]*"
)

# 通用絕對路徑（不侷限於 /Users）：用於抓 wrapper 內呼叫的 /opt/... /tmp/... 等
ABS_PATH_RE = re.compile(
    r"(?<![\w./])/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+\.[A-Za-z0-9]{1,6}"
)

# 佔位符／範本片段：不是「真的壞掉的路徑」
PLACEHOLDER_MARKERS = (
    "$(", "${", "YYYY", "*", "（", "）", "、", "，", "。",
    "「", "」", "『", "』", "：", "+", "?", "|", "→", "＝", "=",
    "：", "；", "；",
    ":",   # PATH=環境變數賦值（冒號分隔的多個目錄）不是檔案路徑
)
CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")
VAR_RE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?")
GLOB_CHARS = "*?["


def is_placeholder(p):
    """判斷是否為範本佔位符（$(date …)、YYYY-MM-DD、$TODAY、glob、含中文敘述）"""
    if any(m in p for m in PLACEHOLDER_MARKERS):
        return True
    if CJK_RE.search(p):
        return True
    if any(c in p for c in GLOB_CHARS):
        return True
    if VAR_RE.search(p):
        return True
    return False


def expand(p):
    return os.path.expanduser(
        p.replace("${HOME}", "~").replace("$HOME", "~")
    )


def check_paths(text):
    """回傳 set of 不存在的檔案路徑（已排除佔位符）"""
    missing = set()
    seen = set()
    expanded_seen = set()

    # 先處理主要路徑（/Users、~、$HOME）
    for raw in PATH_RE.findall(text):
        p = raw.rstrip(".,;:)]}'\"")
        if p in seen:
            continue
        seen.add(p)
        if is_placeholder(p):
            continue
        expanded = expand(p)
        if not expanded or expanded.endswith("/"):
            continue
        if len(expanded) < 12:
            continue
        expanded_seen.add(expanded)
        if os.path.exists(expanded):
            continue
        missing.add(expanded)

    # 再處理其他絕對路徑（wrapper 內呼叫的 /opt/... 等）
    for raw in ABS_PATH_RE.findall(text):
        p = raw.rstrip(".,;:)]}'\"")
        if p in seen:
            continue
        seen.add(p)
        if is_placeholder(p):
            continue
        # 開頭是隱藏目錄（/.git/…）→ 跳過
        if "/." in p:
            continue
        # 只檢查「可執行腳本」類路徑；輸出檔（.json/.jpg/.md 報告）不算失效引用
        if not p.endswith((".sh", ".py", ".mjs", ".js", ".ts", ".plist")):
            continue
        # /tmp 下的產出檔是執行結果，不是需要存在的依賴
        if p.startswith("/tmp/"):
            continue
        expanded = expand(p)
        if len(expanded) < 12:
            continue
        # 已經被主要路徑涵蓋（例如 ~/.hermes/x.sh 與 /.hermes/x.sh）
        if any(expanded.endswith(e) and e != expanded for e in expanded_seen):
            continue
        if os.path.exists(expanded):
            continue
        missing.add(expanded)
    return missing


# ── 技能引用 ────────────────────────────────────────────────
SKILL_REF_RE = re.compile(
    r"\b((?:[a-z0-9][a-z0-9_-]*)/)"
    r"([a-z0-9][a-z0-9._-]*)"
    r"(?=(?:\s|$|[，,。、）)\]」』]))"
)
KNOWN_SKILL_WORDS = {
    "http", "https", "ftp", "etc", "usr", "bin", "var", "tmp", "opt", "private",
    "system", "library", "applications", "users", "home", "dev", "proc", "data",
    "www", "node_modules", "api", "wwwroot", "index", "json", "md", "py", "sh",
    "new", "old", "src", "dist", "build", "logs", "log", "run", "read", "write",
    "release", "breaking", "no", "avoid", "config", "defaults", "and", "or",
    "the", "for", "not", "with", "from", "this", "that", "all", "any", "one",
    "yes", "ok", "in", "on", "at", "to", "by", "of", "if", "is", "it", "as",
    # 注意：不要把 "hermes" 放進來 —— 它是合法的技能分類前綴
    # （~/.hermes/skills/hermes-agent 與 autonomous-ai-agents/hermes-agent）
    "skills",   # 「skills/<name>」是路徑寫法，不是技能分類
    "scripts",  # 「scripts/<name>」是路徑寫法
    "api", "cgi-bin", "public", "static", "assets", "img", "images",
}


def iter_all_skill_dirs(dirs):
    """回傳 {(category, name): skill_dir_path}"""
    found = {}
    for base in dirs:
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            full = os.path.join(base, entry)
            if not os.path.isdir(full):
                continue
            if os.path.exists(os.path.join(full, "SKILL.md")):
                found[(None, entry)] = full
                continue
            if entry.startswith("."):
                continue
            try:
                subdirs = [s for s in sorted(os.listdir(full))
                           if os.path.isdir(os.path.join(full, s))]
            except OSError:
                continue
            for sub in subdirs:
                if os.path.exists(os.path.join(full, sub, "SKILL.md")):
                    found[(entry, sub)] = os.path.join(full, sub)
    return found


def iter_archive_skills(archive_dir):
    """回傳 {name: archive_path}（被封存的技能）"""
    found = {}
    if not os.path.isdir(archive_dir):
        return found
    for entry in sorted(os.listdir(archive_dir)):
        full = os.path.join(archive_dir, entry)
        if not os.path.isdir(full):
            continue
        if os.path.exists(os.path.join(full, "SKILL.md")):
            found[entry] = full
        else:
            for sub in sorted(os.listdir(full)):
                subfull = os.path.join(full, sub)
                if os.path.isdir(subfull) and os.path.exists(
                        os.path.join(subfull, "SKILL.md")):
                    found[sub] = subfull
    return found


def check_skill_refs(text, known, archived):
    """回傳 list of (ref_string, 判定字串)

    只判定「確實是 skill 引用」的情況：
      1. 技能存在但不在這個分類 → 技能搬家了
      2. 技能只存在於 .archive → 被封存
    """
    bad = []
    name_to_cats = defaultdict(list)
    for (cat, name), _path in known.items():
        name_to_cats[name].append(cat)

    for cat, name in SKILL_REF_RE.findall(text):
        cat = cat.rstrip("/")
        low_cat = cat.lower()
        low_name = name.lower()
        if low_cat in KNOWN_SKILL_WORDS or low_name in KNOWN_SKILL_WORDS:
            continue
        if not re.match(r"^[a-z][a-z0-9-]*$", low_cat):
            continue
        if not re.match(r"^[a-z][a-z0-9-]*$", low_name):
            continue
        if re.match(r"^\d", low_name):
            continue

        if name in name_to_cats:
            if cat not in name_to_cats[name]:
                actual = ", ".join(str(c) for c in name_to_cats[name] if c)
                bad.append((f"{cat}/{name}", f"技能在別的分類：{actual}/{name}"))
            continue

        if name in archived:
            bad.append((f"{cat}/{name}", f"技能已封存於 .archive/{name}"))
            continue
    return bad


# ── 檔案搬家偵測 ────────────────────────────────────────────
_MOVED_INDEX = None


def build_moved_index(roots=None):
    """建立 {檔名: [完整路徑]} 索引，用來找出「檔案搬到哪去了」"""
    global _MOVED_INDEX
    if _MOVED_INDEX is not None and roots is None:
        return _MOVED_INDEX
    index = defaultdict(list)
    for root in (roots or SEARCH_ROOTS):
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # 跳過雜訊目錄
            dirnames[:] = [d for d in dirnames
                           if d not in ("node_modules", ".git", "__pycache__",
                                        ".venv", "venv", "public", "uploads",
                                        "dreams")]
            for fn in filenames:
                if fn.endswith((".py", ".sh", ".mjs", ".js")):
                    index[fn].append(os.path.join(dirpath, fn))
            # 技能目錄（內含 SKILL.md）也算一種「搬家的目標」
            if "SKILL.md" in filenames:
                index.setdefault("\0skilldir:" + os.path.basename(dirpath),
                                 []).append(dirpath)
    if roots is None:
        _MOVED_INDEX = index
    return index


def find_moved(path, index=None):
    """若檔案不存在但同名檔案/技能目錄在別處存在，回傳那些路徑"""
    index = index if index is not None else build_moved_index()
    base = os.path.basename(path.rstrip("/"))
    hits = list(index.get(base, []))

    # 技能目錄（workspace/skills/<name>/… → ~/.hermes/skills/<cat>/<name>）
    # 從路徑中找出技能名（skills/ 之後的第一段）
    m = re.search(r"/skills/([^/]+)", path)
    if m:
        hits += index.get("\0skilldir:" + m.group(1), [])
    else:
        hits += index.get("\0skilldir:" + base, [])

    # 去重並排除原路徑本身
    seen = []
    for h in hits:
        if h != path and h not in seen:
            seen.append(h)
    return seen
def find_wrapper(script_name):
    """在已知 wrapper 目錄中找出 script 檔案"""
    if not script_name:
        return None
    for d in WRAPPER_DIRS:
        cand = os.path.join(d, script_name)
        if os.path.exists(cand):
            return cand
    return None


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def collect_wrapper_text(job, depth=0, seen=None):
    """遞迴解析 no_agent job 的 wrapper script，回傳 (文字片段, 引用鏈)"""
    if seen is None:
        seen = set()
    parts = []
    chain = []
    script = job.get("script")
    if not script or depth > 3:
        return parts, chain
    path = find_wrapper(script)
    if not path or path in seen:
        return parts, chain
    seen.add(path)
    chain.append(path)
    text = read_text(path)
    parts.append(text)
    # wrapper 內再 source/exec 別的腳本 → 遞迴
    for m in re.finditer(
        r"(?:source|\.|exec\s+bash)\s+([^\s;]+)", text
    ):
        ref = m.group(1).strip('"\'')
        if not ref.startswith("/"):
            ref = os.path.join(os.path.dirname(path), ref)
        if os.path.exists(ref) and ref not in seen:
            seen.add(ref)
            chain.append(ref)
            sub = read_text(ref)
            parts.append(sub)
    return parts, chain


# ── 主流程 ──────────────────────────────────────────────────
def load_jobs(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("jobs", "cron", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return list(data.values())
    return data


def job_text(job):
    parts = []
    for key in ("prompt", "command", "task", "message"):
        v = job.get(key)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
    return "\n".join(parts)


def audit(jobs_path, skill_dirs):
    jobs = load_jobs(jobs_path)
    known = iter_all_skill_dirs(skill_dirs)
    archived = iter_archive_skills(ARCHIVE_DIR)
    rows = []
    for job in jobs:
        name = job.get("name") or job.get("id") or "(未命名)"
        jid = job.get("id", "")
        text = job_text(job)
        wrapper_parts, chain = collect_wrapper_text(job)
        full_text = text + "\n" + "\n".join(wrapper_parts)

        miss_paths = sorted(check_paths(full_text))
        skill_refs = check_skill_refs(full_text, known, archived)

        # job 的 skills 欄位也要健檢（EDMoms 排程引用已封存的 openclaw-imports/edoms-check）
        # 規則：分類明確寫錯 → 報；裸名稱（無分類）仍能解析 → 不報；已封存 → 報
        declared = job.get("skills") or ([job["skill"]] if job.get("skill") else [])
        all_names = {n for (_c, n) in known}
        for sref in declared:
            if not isinstance(sref, str):
                continue
            if "/" in sref:
                cat, _, nm = sref.partition("/")
            else:
                cat, nm = None, sref
            if (cat, nm) in known:
                continue
            if nm in archived:
                skill_refs.append((sref, f"技能已封存於 .archive/{nm}"))
            elif "/" in sref and nm in all_names:
                actual = ", ".join(
                    f"{c}/{nm}" for (c, n) in known if n == nm and c
                )
                skill_refs.append((sref, f"技能分類已變更，現位於 {actual}"))
            elif "/" in sref:
                skill_refs.append((sref, "技能不存在"))

        # 找出「搬到哪去了」的檔案
        moved = {}
        for p in miss_paths:
            cands = find_moved(p)
            if cands:
                moved[p] = cands

        # wrapper 本身不存在
        script = job.get("script")
        wrapper_missing = bool(script) and not find_wrapper(script)

        rows.append({
            "name": name,
            "id": jid,
            "no_agent": bool(job.get("no_agent")),
            "script": script,
            "enabled": bool(job.get("enabled", True)),
            "state": job.get("state"),
            "wrapper_missing": wrapper_missing,
            "wrapper_chain": chain,
            "missing_paths": miss_paths,
            "moved_paths": moved,
            "skill_refs": skill_refs,
            "last_status": job.get("last_status"),
            "failure_streak": job.get("failure_streak"),
            "last_error": job.get("last_error"),
        })
    return rows, known


def build_markdown(rows):
    broken = [r for r in rows if r["missing_paths"] or r["skill_refs"]
              or r["wrapper_missing"]]
    n_paths = sum(len(r["missing_paths"]) for r in rows)
    n_skills = sum(len(r["skill_refs"]) for r in rows)
    n_wrap = sum(1 for r in rows if r["wrapper_missing"])

    lines = ["# Cron 路徑與技能引用健檢", ""]
    lines.append(f"- 掃描 job 數：**{len(rows)}**")
    lines.append(f"- 有失效引用的 job：**{len(broken)}**")
    lines.append(f"- 失效路徑引用：**{n_paths}**")
    lines.append(f"- 失效技能引用：**{n_skills}**")
    lines.append(f"- wrapper 腳本缺檔：**{n_wrap}**")
    lines.append("")
    lines.append("## 失效引用明細")
    lines.append("")
    for r in broken:
        state = "（停用中）" if not r.get("enabled", True) else ""
        lines.append(f"### `{r['name']}`（id `{r['id']}`）{state}")
        lines.append("")
        if r["wrapper_chain"]:
            lines.append("**檢查的腳本鏈：**")
            lines.append("")
            for c in r["wrapper_chain"]:
                lines.append(f"- `{c}`")
            lines.append("")
        if r["wrapper_missing"]:
            lines.append(f"**wrapper 缺檔：** `{r['script']}`")
            lines.append("")
        if r["missing_paths"]:
            lines.append("**路徑不存在：**")
            lines.append("")
            for p in r["missing_paths"]:
                lines.append(f"- `{p}`")
                for c in r.get("moved_paths", {}).get(p, []):
                    lines.append(f"    - ↪ 疑似搬家到：`{c}`")
            lines.append("")
        if r["skill_refs"]:
            lines.append("**技能引用失效：**")
            lines.append("")
            for ref, why in r["skill_refs"]:
                lines.append(f"- `{ref}` — {why}")
            lines.append("")
    return "\n".join(lines), len(broken)


def build_text(rows, only_broken=True):
    broken = [r for r in rows if r["missing_paths"] or r["skill_refs"]
              or r["wrapper_missing"]]
    n_paths = sum(len(r["missing_paths"]) for r in rows)
    n_skills = sum(len(r["skill_refs"]) for r in rows)
    lines = ["🔍 Cron 路徑與技能引用健檢", ""]
    lines.append(f"掃描 job：{len(rows)}　｜　有問題：{len(broken)}　｜　"
                 f"失效路徑：{n_paths}　｜　失效技能：{n_skills}")
    lines.append("")
    for r in (broken if only_broken else rows):
        tag = "✗" if (r["missing_paths"] or r["skill_refs"]
                       or r["wrapper_missing"]) else "✓"
        state = "（停用中）" if not r.get("enabled", True) else ""
        lines.append(f"{tag} {r['name']}  ({r['id']}){state}")
        for c in r["wrapper_chain"]:
            lines.append(f"    腳本:       {c}")
        if r["wrapper_missing"]:
            lines.append(f"    wrapper 缺檔: {r['script']}")
        for p in r["missing_paths"]:
            lines.append(f"    路徑不存在: {p}")
            for c in r.get("moved_paths", {}).get(p, []):
                lines.append(f"        ↪ 疑似搬家到: {c}")
        for ref, why in r["skill_refs"]:
            lines.append(f"    技能引用:   {ref}  ({why})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Cron 路徑與技能引用健檢（唯讀）")
    ap.add_argument("--jobs", default=DEFAULT_JOBS)
    ap.add_argument("--skill-dir", action="append", default=None)
    ap.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    ap.add_argument("--out", default=None)
    ap.add_argument("--all", action="store_true",
                    help="列出全部 job（預設只列有問題的）")
    args = ap.parse_args()

    skill_dirs = args.skill_dir or DEFAULT_SKILL_DIRS
    rows, _known = audit(args.jobs, skill_dirs)
    broken = [r for r in rows if r["missing_paths"] or r["skill_refs"]
              or r["wrapper_missing"]]

    if args.format == "json":
        out = {
            "jobs_scanned": len(rows),
            "jobs_with_broken_refs": len(broken),
            "broken_path_refs": sum(len(r["missing_paths"]) for r in rows),
            "broken_skill_refs": sum(len(r["skill_refs"]) for r in rows),
            "results": rows,
        }
        text = json.dumps(out, ensure_ascii=False, indent=2)
    elif args.format == "markdown":
        text, _ = build_markdown(rows)
    else:
        text = build_text(rows, only_broken=not args.all)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已寫入 {args.out}")
    else:
        print(text)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
