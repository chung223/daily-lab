#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_truth_checker 測試套件

用真實抓到的 cron 輸出格式建立測試案例，驗證：
  1. 靜默失效偵測（狀態欄 ok，實際 exit=2）
  2. 狀態欄自己報錯
  3. 成功排程不被誤判
  4. 已停用排程被略過（不誤報）
  5. 缺腳本根因被正確抽出
  6. CLI 端到端跑在假資料上

執行：python3 test_cron_truth_checker.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cron_truth_checker as ctc  # noqa: E402

PASS, FAIL = 0, 0
RESULTS = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(("✅", name, ""))
    else:
        FAIL += 1
        RESULTS.append(("❌", name, detail))


# ─────────────────────────────────────────────
# 測試素材：真實 cron 輸出格式
# ─────────────────────────────────────────────

OUT_OK = """# Cron Job: 行事曆格式糾察

**Job ID:** 4e8982260942
**Run Time:** 2026-11-01 08:30:06
**Mode:** no_agent (script)

---

[Scan] 共 32 筆事件（未來 90 天）

=== 報告 ===
總事件：32
系統事件（跳過）：0
已符合格式：32
已跳過：0
已修正：0
失敗：0
"""

OUT_SILENT_FAIL = """# Cron Job: Notion送機表→Calendar

**Job ID:** f07f7975cca4
**Run Time:** 2026-11-01 15:00:05
**Mode:** no_agent (script)

---

notion-sendoff exit=2 (ERROR:腳本不存在 /Users/chung/.openclaw/workspace/scripts/sync_notion_sendoff_to_gcal.py)
"""

OUT_SCRIPT_FAILED = """# Cron Job: 每日備份

**Job ID:** cbdf7569d334
**Run Time:** 2026-11-01 05:15:40
**Mode:** no_agent (script)
**Status:** script failed

Script execution failed: 'utf-8' codec can't decode byte 0xbc in position 30: invalid start byte
"""

OUT_EXIT127 = """# Cron Job: npm安全週掃

**Job ID:** 0c73c32f8405
**Run Time:** 2026-10-26 09:00:42
**Mode:** no_agent (script)

---

npmscan exit=127
"""


def make_job(jid, name, status="ok", enabled=True, streak=0, no_agent=True):
    return {
        "id": jid, "name": name, "no_agent": no_agent, "enabled": enabled,
        "last_status": status, "failure_streak": streak,
        "last_run_at": "2026-11-01T15:00:05+08:00",
        "last_error": None if status == "ok" else "Script execution failed",
        "schedule": {"kind": "cron", "expr": "0 15 * * *"},
    }


def build_fixture(tmp, jobs, outputs):
    """jobs: list[dict]; outputs: dict[job_id] = content"""
    jobs_path = os.path.join(tmp, "jobs.json")
    out_dir = os.path.join(tmp, "output")
    os.makedirs(out_dir, exist_ok=True)
    with open(jobs_path, "w", encoding="utf-8") as fh:
        json.dump({"jobs": jobs, "updated_at": "2026-11-01T00:00:00+08:00"}, fh)
    for jid, content in outputs.items():
        d = os.path.join(out_dir, jid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "2026-11-01_15-00-05.md"), "w", encoding="utf-8") as fh:
            fh.write(content)
    return jobs_path, out_dir


# ─────────────────────────────────────────────
# 測試 1：單元測試 — detect_failure
# ─────────────────────────────────────────────

def test_detect_failure():
    ok, code, detail = ctc.detect_failure("notion-sendoff exit=2 (ERROR:腳本不存在 /x/y.py)")
    check("detect_failure：exit=2 判為失敗", (not ok) and code == 2, f"ok={ok} code={code}")

    ok, code, detail = ctc.detect_failure("memsync exit=0")
    check("detect_failure：exit=0 判為成功", ok and code == 0, f"ok={ok} code={code}")

    ok, code, detail = ctc.detect_failure("npmscan exit=127")
    check("detect_failure：exit=127 判為失敗", not ok and code == 127, f"ok={ok} code={code}")

    ok, code, detail = ctc.detect_failure("失敗：0\n已修正：0")
    check("detect_failure：含『失敗：0』的成功報告不誤判", ok, f"ok={ok} detail={detail}")

    ok, code, detail = ctc.detect_failure(
        "Script execution failed: 'utf-8' codec can't decode byte 0xbc")
    check("detect_failure：script failed 判為失敗", not ok, f"ok={ok}")

    ok, code, detail = ctc.detect_failure("RuntimeError: Chrome did not start")
    check("detect_failure：RuntimeError 判為失敗", not ok, f"ok={ok}")

    ok, code, detail = ctc.detect_failure("所有檔案同步完成，無異常")
    check("detect_failure：正常文字不誤判", ok, f"ok={ok} detail={detail}")


# ─────────────────────────────────────────────
# 測試 2：單元測試 — split_sections
# ─────────────────────────────────────────────

def test_split_sections():
    sec = ctc.split_sections(OUT_OK)
    check("split_sections：script 輸出能切出 body",
          "32" in sec["body"] and "Cron Job" not in sec["body"],
          repr(sec["body"][:80]))

    sec = ctc.split_sections(OUT_SCRIPT_FAILED)
    check("split_sections：無分隔線時仍能切出 body（去掉標頭）",
          "Codec" in sec["body"] or "codec" in sec["body"]
          and "# Cron Job" not in sec["body"],
          repr(sec["body"][:120]))

    agent_out = """# Cron Job: 測試

**Job ID:** abc

---

## Prompt

這是技能內容，不該被當成結果

## Response

✅ 執行成功
"""
    sec = ctc.split_sections(agent_out)
    check("split_sections：agent 型優先取 ## Response",
          "執行成功" in sec["response"] and "技能內容" not in sec["response"],
          repr(sec["response"][:80]))


# ─────────────────────────────────────────────
# 測試 3：單元測試 — find_root_cause
# ─────────────────────────────────────────────

def test_root_cause():
    rc = ctc.find_root_cause(
        "notion-sendoff exit=2 (ERROR:腳本不存在 /Users/chung/.openclaw/workspace/scripts/sync_notion_sendoff_to_gcal.py)")
    check("root_cause：抽出缺檔路徑",
          "sync_notion_sendoff_to_gcal.py" in rc and "不存在" in rc, rc)

    rc = ctc.find_root_cause(
        "Script execution failed: 'utf-8' codec can't decode byte 0xbc")
    check("root_cause：抽出編碼錯誤", "utf-8" in rc, rc)

    rc = ctc.find_root_cause("memsync exit=2")
    check("root_cause：無明確線索時回空字串（不亂猜）", rc == "", repr(rc))

    # 從 wrapper 腳本追根因：oc-memsync.sh 呼叫的 python 檔確實不存在
    rc = ctc.find_root_cause("memsync exit=2", {"script": "oc-memsync.sh"})
    check("root_cause：從 wrapper 追出缺檔（memsync）",
          "sync_daily_memory_to_agentmemory.py" in rc, rc)

    rc = ctc.find_root_cause("readmoo exit=2", {"script": "oc-readmoo.sh"})
    check("root_cause：從 wrapper 追出缺檔（readmoo）",
          "readmoo_daily.py" in rc, rc)

    # 兩條線共用 wrapper 時，要挑對檔案
    rc = ctc.find_root_cause("notion-sendoff exit=2", {"script": "oc-notion-sendoff.sh"})
    check("root_cause：共用 wrapper 時挑對檔案（sendoff）",
          "sync_notion_sendoff_to_gcal.py" in rc
          and "foreign" not in rc, rc)
    rc = ctc.find_root_cause("notion-foreign exit=2", {"script": "oc-notion-foreign.sh"})
    check("root_cause：共用 wrapper 時挑對檔案（foreign）",
          "sync_notion_foreign_transfer_to_gcal.py" in rc, rc)

    # 正常排程不該被推成缺檔
    rc = ctc.find_root_cause("失敗：0", {"script": "calendar_harmonizer.sh"})
    check("root_cause：正常排程不誤判缺檔", rc == "", repr(rc))


# ─────────────────────────────────────────────
# 測試 4：整合掃描 — 靜默失效偵測
# ─────────────────────────────────────────────

def test_scan_diverged():
    tmp = tempfile.mkdtemp()
    try:
        jobs = [
            make_job("aaa111", "靜默失效排程", status="ok"),
            make_job("bbb222", "正常排程", status="ok"),
            make_job("ccc333", "自己報錯排程", status="error", streak=35),
            make_job("ddd444", "已停用排程", status="ok", enabled=False),
        ]
        outputs = {
            "aaa111": OUT_SILENT_FAIL,
            "bbb222": OUT_OK,
            "ccc333": OUT_SCRIPT_FAILED,
            "ddd444": OUT_EXIT127,
        }
        jp, od = build_fixture(tmp, jobs, outputs)
        rep = ctc.scan(jp, od)

        by_id = {f.job_id: f for f in rep.findings}

        check("scan：靜默失效被偵測到",
              "aaa111" in by_id and by_id["aaa111"].kind == "diverged",
              str(list(by_id)))
        check("scan：靜默失效標為 critical",
              "aaa111" in by_id and by_id["aaa111"].severity == "critical",
              str(by_id.get("aaa111")))
        check("scan：正常排程不被誤判", "bbb222" not in by_id,
              str(list(by_id)))
        check("scan：正常排程列入 ok 清單",
              any(j["job_id"] == "bbb222" for j in rep.ok_jobs),
              str(rep.ok_jobs))
        check("scan：狀態欄報錯者標為 failed",
              "ccc333" in by_id and by_id["ccc333"].kind == "failed",
              str(list(by_id)))
        check("scan：已停用排程被略過（不誤報）", "ddd444" not in by_id,
              str(list(by_id)))
        check("scan：靜默失效帶有根因",
              "aaa111" in by_id and "sync_notion_sendoff" in by_id["aaa111"].root_cause,
              str(by_id.get("aaa111")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────
# 測試 5：CLI 端到端
# ─────────────────────────────────────────────

def test_cli_e2e():
    tmp = tempfile.mkdtemp()
    try:
        jobs = [make_job("aaa111", "靜默失效排程", status="ok")]
        jp, od = build_fixture(tmp, jobs, {"aaa111": OUT_SILENT_FAIL})

        # text 格式：偵測到問題時 exit=1
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "cron_truth_checker.py"),
             "--jobs", jp, "--output-dir", od, "--format", "text"],
            capture_output=True, text=True)
        check("CLI：有問題時 exit code = 1", r.returncode == 1,
              f"rc={r.returncode} out={r.stdout[:200]}")
        check("CLI：text 輸出含關鍵字『靜默失效』",
              "靜默失效" in r.stdout, r.stdout[:200])
        check("CLI：text 輸出含排程名稱",
              "靜默失效排程" in r.stdout, r.stdout[:200])

        # json 格式
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "cron_truth_checker.py"),
             "--jobs", jp, "--output-dir", od, "--format", "json"],
            capture_output=True, text=True)
        check("CLI：json 格式可解析", r.returncode == 1)
        try:
            data = json.loads(r.stdout)
            check("CLI：json 含 1 項發現", data["finding_count"] == 1,
                  str(data.get("finding_count")))
            check("CLI：json finding 含 root_cause 欄位",
                  "root_cause" in data["findings"][0],
                  str(list(data["findings"][0])))
        except json.JSONDecodeError as e:
            check("CLI：json 可解析", False, str(e))

        # markdown 格式
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "cron_truth_checker.py"),
             "--jobs", jp, "--output-dir", od, "--format", "markdown"],
            capture_output=True, text=True)
        check("CLI：markdown 含表格", "| 嚴重度 |" in r.stdout, r.stdout[:200])

        # 無問題時 exit=0
        jobs2 = [make_job("bbb222", "正常排程", status="ok")]
        jp2, od2 = build_fixture(tmp, jobs2, {"bbb222": OUT_OK})
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "cron_truth_checker.py"),
             "--jobs", jp2, "--output-dir", od2],
            capture_output=True, text=True)
        check("CLI：無問題時 exit code = 0", r.returncode == 0,
              f"rc={r.returncode}")
        check("CLI：無問題時顯示正常",
              "沒有偵測到靜默失效" in r.stdout or "未偵測到靜默失效" in r.stdout,
              r.stdout[:200])

        # --out 寫檔
        outp = os.path.join(tmp, "report.md")
        r = subprocess.run(
            [sys.executable, os.path.join(HERE, "cron_truth_checker.py"),
             "--jobs", jp, "--output-dir", od, "--format", "markdown", "--out", outp],
            capture_output=True, text=True)
        check("CLI：--out 可寫入報告檔", os.path.exists(outp), r.stdout[:200])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ─────────────────────────────────────────────
# 測試 6：真實環境（唯讀掃描）
# ─────────────────────────────────────────────

def test_real_env():
    if not os.path.exists(ctc.DEFAULT_JOBS):
        check("真實環境：jobs.json 存在", False, ctc.DEFAULT_JOBS)
        return
    rep = ctc.scan(ctc.DEFAULT_JOBS, ctc.DEFAULT_OUTPUT_DIR)
    check("真實環境：掃描成功且有 script 排程",
          rep.scanned_script_jobs > 0, str(rep.scanned_script_jobs))
    check("真實環境：偵測到靜默失效（Notion 兩個排程）",
          any(f.job_id == "f07f7975cca4" for f in rep.findings)
          and any(f.job_id == "5b58caed5417" for f in rep.findings),
          str([f.job_id for f in rep.findings]))
    check("真實環境：每日備份被標為 failed 而非 diverged",
          any(f.job_id == "cbdf7569d334" and f.kind == "failed" for f in rep.findings),
          str([(f.job_id, f.kind) for f in rep.findings]))
    check("真實環境：正常排程（行事曆格式糾察）不被誤判",
          not any(f.job_id == "4e8982260942" for f in rep.findings),
          str([f.job_id for f in rep.findings]))
    check("真實環境：已停用排程不被誤報",
          not any(f.job_id in ("bf131728b488", "5a4082206f36", "2e3e26e330fb")
                  for f in rep.findings),
          str([f.job_id for f in rep.findings]))


# ─────────────────────────────────────────────
def main():
    for fn in (test_detect_failure, test_split_sections, test_root_cause,
               test_scan_diverged, test_cli_e2e, test_real_env):
        print(f"\n▶ 執行 {fn.__name__}")
        fn()

    print("\n" + "=" * 62)
    for icon, name, detail in RESULTS:
        line = f"{icon} {name}"
        if detail and icon == "❌":
            line += f"\n     → {detail}"
        print(line)
    print("=" * 62)
    print(f"通過 {PASS} / {PASS + FAIL}（失敗 {FAIL}）")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
