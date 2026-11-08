#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cron_path_audit.py 的測試套件（純標準庫 unittest）

執行：python3 test_cron_path_audit.py
"""

import json
import os
import shutil
import tempfile
import unittest

import cron_path_audit as C


class TestPlaceholders(unittest.TestCase):
    """佔位符不可被誤判為壞路徑"""

    def test_placeholder_paths_ignored(self):
        text = """
        讀取 /Users/chung/.openclaw/workspace/memory/YYYY-MM-DD.md
        執行 /Users/chung/.openclaw/workspace/scripts/x.py
        寫入 /Users/chung/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
        glob /Users/chung/.openclaw/workspace/memory/recap/*-full.md
        變數 /Users/chung/.openclaw/workspace/memory/$TODAY.md
        中文句 /Users/chung/.openclaw/workspace/memory/近 7 天檔
        PATH  /Users/chung/google-cloud-sdk/bin:/opt/homebrew/bin:/usr/bin
        """
        # /Users/chung/.openclaw/workspace/scripts/x.py 本身也不存在 → 應該被報
        missing = C.check_paths(text)
        self.assertIn("/Users/chung/.openclaw/workspace/scripts/x.py", missing)
        self.assertNotIn(
            "/Users/chung/.openclaw/workspace/memory/YYYY-MM-DD.md", missing)
        self.assertNotIn(
            "/Users/chung/.openclaw/workspace/memory/$(date +%Y-%m-%d).md",
            missing)
        self.assertNotIn(
            "/Users/chung/.openclaw/workspace/memory/recap/*-full.md", missing)
        self.assertNotIn(
            "/Users/chung/.openclaw/workspace/memory/$TODAY.md", missing)
        self.assertNotIn(
            "/Users/chung/.openclaw/workspace/memory/近 7 天檔", missing)
        # PATH 清單不該被當成單一路徑
        for m in missing:
            self.assertNotIn(":/", m)

    def test_existing_path_not_reported(self):
        with tempfile.NamedTemporaryFile(suffix=".py") as f:
            missing = C.check_paths(f"執行 {f.name} 腳本")
        self.assertEqual(missing, set())

    def test_home_expansion(self):
        missing = C.check_paths("cat ~/.hermes/definitely-not-here-xyz.sh")
        self.assertEqual(len(missing), 1)
        self.assertTrue(list(missing)[0].startswith("/Users/chung/.hermes/"))


class TestSkillRefs(unittest.TestCase):
    """技能引用判定"""

    def setUp(self):
        self.known = {
            (None, "solo-skill"): "/tmp/solo-skill",
            ("cat-a", "moved-skill"): "/tmp/cat-a/moved-skill",
        }
        self.archived = {"archived-skill": "/tmp/.archive/archived-skill"}

    def test_moved_category_detected(self):
        text = "請使用 old-cat/moved-skill 技能"
        bad = C.check_skill_refs(text, self.known, self.archived)
        self.assertEqual(len(bad), 1)
        self.assertIn("moved-skill", bad[0][0])

    def test_correct_ref_not_flagged(self):
        text = "請使用 cat-a/moved-skill 技能"
        bad = C.check_skill_refs(text, self.known, self.archived)
        self.assertEqual(bad, [])

    def test_archived_detected(self):
        text = "使用 some-cat/archived-skill"
        bad = C.check_skill_refs(text, self.known, self.archived)
        self.assertEqual(len(bad), 1)
        self.assertIn("封存", bad[0][1])

    def test_english_phrases_not_flagged(self):
        """英文片語不能被誤判成技能引用"""
        text = "no/avoid release/breaking config/defaults the/for/not"
        bad = C.check_skill_refs(text, self.known, self.archived)
        self.assertEqual(bad, [])


class TestWrapperResolution(unittest.TestCase):
    """no_agent job 的 wrapper 腳本要被遞迴解析"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wrapper_dir = os.path.join(self.tmp, "scripts")
        os.makedirs(self.wrapper_dir)
        self.wrapper = os.path.join(self.wrapper_dir, "oc-test.sh")
        with open(self.wrapper, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/bash\n"
                f"source {self.tmp}/oc-notify.sh\n"
                "OUT=$(python3 /nonexistent/path/real_script.py 2>&1)\n"
                "echo done\n"
            )
        self.notify = os.path.join(self.tmp, "oc-notify.sh")
        with open(self.notify, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\ndiscord_send() { :; }\n")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_wrapper_chain_resolved(self):
        old_dirs = C.WRAPPER_DIRS
        C.WRAPPER_DIRS = [self.wrapper_dir]
        try:
            job = {"script": "oc-test.sh"}
            parts, chain = C.collect_wrapper_text(job)
        finally:
            C.WRAPPER_DIRS = old_dirs
        self.assertIn(self.wrapper, chain)
        self.assertIn(self.notify, chain)
        joined = "\n".join(parts)
        self.assertIn("/nonexistent/path/real_script.py", joined)

    def test_missing_wrapper_detected(self):
        old_dirs = C.WRAPPER_DIRS
        C.WRAPPER_DIRS = [self.tmp]
        try:
            self.assertIsNone(C.find_wrapper("oc-nope-xyz.sh"))
        finally:
            C.WRAPPER_DIRS = old_dirs


class TestAuditEndToEnd(unittest.TestCase):
    """整體流程：以假的 jobs.json 跑一次"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.script_dir = os.path.join(self.tmp, "scripts")
        os.makedirs(self.script_dir)
        good = os.path.join(self.script_dir, "good.py")
        with open(good, "w", encoding="utf-8") as f:
            f.write("print('ok')\n")
        wrapper = os.path.join(self.script_dir, "oc-job.sh")
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n"
                    "python3 /absolutely/missing/target.py\n")

        self.jobs = {
            "jobs": [
                {
                    "id": "job_ok",
                    "name": "正常排程",
                    "prompt": f"執行 {good}",
                    "script": None,
                },
                {
                    "id": "job_bad_wrapper",
                    "name": "壞掉的 wrapper",
                    "prompt": "",
                    "script": "oc-job.sh",
                    "no_agent": True,
                },
                {
                    "id": "job_bad_path",
                    "name": "壞掉的路徑",
                    "prompt": "讀取 /Users/chung/nope/missing-file.sh",
                    "script": None,
                },
            ],
            "updated_at": "now",
        }
        self.jobs_path = os.path.join(self.tmp, "jobs.json")
        with open(self.jobs_path, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, ensure_ascii=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_audit_finds_all(self):
        old_dirs = C.WRAPPER_DIRS
        C.WRAPPER_DIRS = [self.script_dir]
        try:
            rows, _ = C.audit(self.jobs_path, [])
        finally:
            C.WRAPPER_DIRS = old_dirs
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(len(rows), 3)
        self.assertEqual(by_id["job_ok"]["missing_paths"], [])
        self.assertIn("/absolutely/missing/target.py",
                      by_id["job_bad_wrapper"]["missing_paths"])
        self.assertIn("/Users/chung/nope/missing-file.sh",
                      by_id["job_bad_path"]["missing_paths"])

    def test_broken_job_counted(self):
        old_dirs = C.WRAPPER_DIRS
        C.WRAPPER_DIRS = [self.script_dir]
        try:
            rows, _ = C.audit(self.jobs_path, [])
        finally:
            C.WRAPPER_DIRS = old_dirs
        broken = [r for r in rows
                  if r["missing_paths"] or r["skill_refs"]
                  or r["wrapper_missing"]]
        self.assertEqual(len(broken), 2)


class TestRealEnvironment(unittest.TestCase):
    """對真實環境跑一次，確認不會對現存的排程誤報太多"""

    def test_real_scan_runs(self):
        if not os.path.exists(C.DEFAULT_JOBS):
            self.skipTest("找不到 jobs.json")
        rows, _ = C.audit(C.DEFAULT_JOBS, C.DEFAULT_SKILL_DIRS)
        self.assertGreater(len(rows), 0)
        for r in rows:
            # 現存的排程不該被判為「wrapper 缺檔」
            if r["script"]:
                self.assertFalse(
                    r["wrapper_missing"],
                    f"{r['name']} 的 wrapper 被判定缺檔")

    def test_known_broken_detected(self):
        """已知壞掉的排程必須被抓到"""
        if not os.path.exists(C.DEFAULT_JOBS):
            self.skipTest("找不到 jobs.json")
        rows, _ = C.audit(C.DEFAULT_JOBS, C.DEFAULT_SKILL_DIRS)
        names = {r["name"]: r for r in rows}
        # 這幾個在本週記錄中皆為持續失敗
        for n in ("每日備份", "Notion送機表→Calendar",
                  "記憶→agentmemory同步", "Readmoo每日特惠"):
            if n in names:
                self.assertTrue(
                    names[n]["missing_paths"],
                    f"{n} 應該有失效路徑卻沒抓到")


if __name__ == "__main__":
    unittest.main(verbosity=2)
