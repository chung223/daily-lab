#!/usr/bin/env python3
"""
IFYE Sync Gap Finder
====================
驗證 IFYE Notion → JSON 同步是否存在資料缺口。

用法:
  python3 ifye-gap-finder.py [--vps] [--local PATH]

原理:
  1. 查詢 Notion DB1（115_01_12來訪）+ DB2（在台）
  2. 讀取本機 ifye-2026.json（同步後的產出）
  3. 以「代表名字 + 站名 + 日期」為 key 比對
  4. 輸出 Notion 有但 JSON 沒有的「孤立記錄」

依據:
  - 2026-09-04~12 每日 Recap，IFYE sync 產出 9×51 站
  - 但 Notion 兩資料庫合計 69 筆記錄（9人來訪 + 60站在台）
  - Recap 9/9：「sync-notion.mjs 因 relation 欄位空白導致 fallback 失效，漏接 9 筆」
  - Recap 9/10：IFYE sync 未完成，relation 對應失敗
  - DB2 在台 60 筆的 relation 欄位（115_01_12來訪）全部為空 → 這就是根因
"""

import json
import urllib.request
import urllib.error
import os
import re
import sys
import argparse
from pathlib import Path

# ── 設定 ──────────────────────────────────────────────
DEFAULT_LOCAL_JSON = "/Users/chung/.openclaw/sites/ifye/2026/data/ifye-2026.json"
DEFAULT_VPS_URL   = "https://index.4-h.me/ifye/2026/"

# Notion Database IDs（從 tmp/ifye_*.py 確認）
DB_LAIFU  = "33efdb42-8dea-80b4-8cac-c344bd5bc968"  # 115_01_12來訪
DB_ZAITAI = "360fdb42-8dea-8079-9507-d937dd114023"  # 在台

NOTION_VERSION = "2022-06-28"
PAGE_SIZE = 100

# 預期代表名單（用於模糊比對）
EXPECTED_REPS = [
    "Ibrahim B. Sansalona",
    "Gary A. Ayuste",
    "Jihyun Jung",
    "Yerim An",
    "Phoobet Sudsawatt",
    "Dararat Surinpornwattana",
    "Anna Ruttimann",
    "Sven",
    "Justice Kwasi Etsey",
]


def get_notion_key():
    """從 openclaw.json 讀取 NOTION_API_KEY。"""
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    try:
        with open(cfg) as f:
            return json.load(f)["env"]["vars"].get("NOTION_API_KEY", "")
    except Exception:
        return os.getenv("NOTION_API_KEY", "")


# ── Notion 查詢 ────────────────────────────────────────────────────────────

def query_notion_database(db_id, notion_key):
    """查詢 Notion database，回傳所有 page 列表。"""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {"page_size": PAGE_SIZE}
    all_results = []

    while True:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={
                "Authorization": f"Bearer {notion_key}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"[ERROR] Notion API HTTP {e.code}: {e.reason}", file=sys.stderr)
            if e.code == 404:
                print(f"[ERROR] 資料庫 ID 可能錯誤或無權限: {db_id}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"[ERROR] 無法連線 Notion API: {e.reason}", file=sys.stderr)
            sys.exit(1)

        all_results.extend(result.get("results", []))
        if not result.get("has_more"):
            break
        payload["start_cursor"] = result.get("next_cursor")

    print(f"[INFO] DB {db_id}: 讀取 {len(all_results)} 筆記錄", file=sys.stderr)
    return all_results


# ── 欄位提取 ──────────────────────────────────────────────────────────────

def get_field(page, ftype, fname):
    """通用欄位讀取：支援 title / rich_text / select / status / date。"""
    props = page.get("properties", {})
    if fname not in props:
        return None
    prop = props[fname]
    if prop.get("type") != ftype:
        return None
    if ftype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif ftype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif ftype == "select":
        return prop.get("select", {}).get("name", "") or None
    elif ftype == "status":
        return prop.get("status", {}).get("name", "") or None
    elif ftype == "date":
        return prop.get("date", {}).get("start", "")[:10] if prop.get("date", {}).get("start") else None
    return None


def is_relation_empty(page, rel_field):
    """檢查指定 relation 欄位是否為空。"""
    props = page.get("properties", {})
    if rel_field not in props:
        return True
    prop = props[rel_field]
    if prop.get("type") != "relation":
        return True
    return len(prop.get("relation", [])) == 0


def extract_notion_record(page, db_id):
    """
    從 Notion page 取出關鍵欄位，根據資料庫有不同的欄位結構：

    DB1（115_01_12來訪）:
      - Name (title): 代表姓名
      - 國家 (select): 國家
      - 接待家庭 (status): 接待家庭狀態

    DB2（在台）:
      - IFYE (title): 代表姓名
      - 站 (status): 站名（接送機、第1站、第2站…）
      - 行程 (date): 開始日期
      - 接待 (select): 接待縣市
      - 115_01_12來訪 (relation): 對應到 DB1 的連結（目前全部為空！）
    """
    is_db2 = (db_id == DB_ZAITAI)

    if is_db2:
        rep_name = get_field(page, "title", "IFYE")
        station  = get_field(page, "status", "站")
        date     = get_field(page, "date",   "行程")
        rel_field = "115_01_12來訪"
    else:
        rep_name = get_field(page, "title", "Name")
        station  = None   # DB1 是代表本人資料，沒有站
        date     = get_field(page, "date", "接機")
        rel_field = None

    rel_empty = is_relation_empty(page, rel_field) if rel_field else False

    # 建立比對 key
    key = f"{rep_name or ''}|{station or ''}|{date or ''}"

    return {
        "rep_name":   rep_name,
        "station":    station,
        "date":      date,
        "rel_empty": rel_empty,
        "db":        "在台" if is_db2 else "來訪",
        "page_id":   page.get("id", ""),
        "key":       key,
    }


# ── JSON 讀取 ─────────────────────────────────────────────────────────────

def fetch_local_json(json_path):
    """讀取本機 ifye-2026.json。"""
    print(f"[INFO] 讀取本機 JSON: {json_path}", file=sys.stderr)
    if not os.path.exists(json_path):
        print(f"[ERROR] 找不到檔案: {json_path}", file=sys.stderr)
        print(f"[HINT] 請先執行 ifye_merge_v2.py 產生本地 JSON", file=sys.stderr)
        sys.exit(1)
    with open(json_path) as f:
        return json.load(f)


def fetch_vps_json(vps_url):
    """從 VPS 下載 ifye-2026.json（嘗試多種可能路徑）。"""
    candidates = [
        f"{vps_url.rstrip('/')}/ifye-2026.json",
        f"{vps_url.rstrip('/')}/ifye2026.json",
        f"{vps_url.rstrip('/')}/data/ifye-2026.json",
    ]
    for url in candidates:
        print(f"[INFO] 嘗試: {url}", file=sys.stderr)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IFYE-Gap-Finder/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
                if b"<html" in content[:100].lower() or b"<!doctype" in content[:100].lower():
                    continue
                return json.loads(content)
        except Exception:
            continue
    print(f"[ERROR] 無法從 VPS 找到 ifye-2026.json", file=sys.stderr)
    sys.exit(1)


def build_json_station_set(data):
    """
    從 ifye-2026.json 取出所有「代表|站|日期」組合。
    JSON 格式: { "updatedAt": ..., "representatives": [{ "name": ..., "stations": [{ "station": ..., "startDate": ... }] }] }
    """
    stations = set()
    reps_count = 0
    stations_count = 0

    for rep_block in data.get("representatives", []):
        rep_name = rep_block.get("name", "")
        reps_count += 1
        for s in rep_block.get("stations", []):
            station_name = s.get("station", "")
            date = (s.get("startDate") or "")[:10]
            stations.add(f"{rep_name}|{station_name}|{date}")
            stations_count += 1

    return stations, reps_count, stations_count


# ── 人名正規化 ─────────────────────────────────────────────────────────────

def normalize_name(name):
    """小寫、去標點、去除空白，用於模糊比對。"""
    if not name:
        return ""
    n = name.lower().strip()
    n = re.sub(r"[^\w\s]", " ", n)
    n = " ".join(n.split())
    return n


def fuzzy_match_rep(notion_rep, expected_reps):
    """對代表名字做模糊比對，回傳最接近的預期代表或 None。"""
    if not notion_rep:
        return None
    n_norm = normalize_name(notion_rep)
    best, best_score = None, 0
    for exp in expected_reps:
        e_norm = normalize_name(exp)
        words = n_norm.split()
        score = sum(1 for w in words if w in e_norm or e_norm in w) / max(len(words), 1)
        if score > best_score:
            best_score, best = score, exp
    return best if best_score >= 0.5 else None


# ── 主程式 ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IFYE Sync Gap Finder")
    parser.add_argument("--vps", action="store_true",
                        help="從 VPS 下載 JSON（預設：讀取本機）")
    parser.add_argument("--local", default=DEFAULT_LOCAL_JSON,
                        help=f"本機 JSON 檔案路徑（預設: {DEFAULT_LOCAL_JSON}）")
    parser.add_argument("--notion-key", default=get_notion_key(),
                        help="Notion API Key（預設從 openclaw.json 讀取）")
    args = parser.parse_args()

    notion_key = args.notion_key
    if not notion_key:
        print("[ERROR] 找不到 NOTION_API_KEY", file=sys.stderr)
        sys.exit(1)

    # 1. 查詢 Notion
    print("\n=== 查詢 Notion 資料庫 ===", file=sys.stderr)
    pages_laifu  = query_notion_database(DB_LAIFU,  notion_key)
    pages_zaitai = query_notion_database(DB_ZAITAI, notion_key)

    # 2. 從 DB2（在台）建立 Notion 站記錄集合
    #    DB2 是在台的 60 站記錄，這些是會寫入 JSON 的主要資料
    notion_stations = {}   # key -> {rep, station, date, rel_empty, page_id}
    db2_orphan_pages = []  # relation 欄位為空的 DB2 頁面

    for page in pages_zaitai:
        rec = extract_notion_record(page, DB_ZAITAI)
        key = rec["key"]
        notion_stations[key] = {
            "rep_name":  rec["rep_name"],
            "station":   rec["station"],
            "date":      rec["date"],
            "rel_empty": rec["rel_empty"],
            "page_id":   rec["page_id"],
        }
        if rec["rel_empty"]:
            db2_orphan_pages.append(rec)

    # DB1（來訪 9 人）只是基本資料，比對價值有限，納入作為參考
    db1_reps = {}
    for page in pages_laifu:
        rec = extract_notion_record(page, DB_LAIFU)
        if rec["rep_name"]:
            db1_reps[rec["rep_name"]] = rec

    # 3. 讀取 JSON
    if args.vps:
        json_data = fetch_vps_json(DEFAULT_VPS_URL)
    else:
        json_data = fetch_local_json(args.local)

    json_stations, json_reps, json_stations_count = build_json_station_set(json_data)

    # 4. 比對
    notion_keys = set(notion_stations.keys())
    missing = notion_keys - json_stations

    print(f"\n=== 比對結果 ===", file=sys.stderr)
    print(f"  DB1（來訪代表）:  {len(pages_laifu)} 筆", file=sys.stderr)
    print(f"  DB2（在台站別）:  {len(pages_zaitai)} 筆", file=sys.stderr)
    print(f"  Notion 在台站 unique keys: {len(notion_keys)}", file=sys.stderr)
    print(f"  JSON 站數:  {json_stations_count} 站", file=sys.stderr)
    print(f"  差額（Notion 有 / JSON 無）: {len(missing)} 筆", file=sys.stderr)
    if db2_orphan_pages:
        print(f"  ⚠  DB2 relation 空白記錄: {len(db2_orphan_pages)} 筆", file=sys.stderr)

    if missing:
        # 分析：relation 空白 vs 名稱比對失敗
        orphan_keys = {rec["key"] for rec in db2_orphan_pages}
        true_orphan_gaps  = missing & orphan_keys
        name_mismatch_gaps = missing - orphan_keys

        print(f"\n{'='*60}")
        print(f"⚠️  缺口記錄（Notion 有，但 JSON 未寫入）: {len(missing)} 筆")
        print(f"{'='*60}")
        print(f"\n[分析]")
        print(f"  • relation 空白導致（DB2 孤立）: {len(true_orphan_gaps)} 筆")
        print(f"  • 名稱比對失敗（sync 邏輯問題）: {len(name_mismatch_gaps)} 筆")

        print(f"\n--- 缺口詳目（依代表分組）---")
        gaps_by_rep = {}
        for key in sorted(missing):
            rec = notion_stations[key]
            rep = rec["rep_name"] or "（無代表名）"
            if rep not in gaps_by_rep:
                gaps_by_rep[rep] = []
            fuzzy = fuzzy_match_rep(rec["rep_name"], EXPECTED_REPS)
            reason = "relation空白" if key in orphan_keys else "名稱比對失敗"
            gaps_by_rep[rep].append({
                **rec,
                "key": key,
                "suspected_cause": reason,
                "fuzzy_match": fuzzy,
            })

        for rep, recs in sorted(gaps_by_rep.items()):
            fuzzy = recs[0]["fuzzy_match"]
            rep_tag = f" → {fuzzy}" if fuzzy and fuzzy != rep else ""
            print(f"\n  📌 {rep}{rep_tag}（{len(recs)} 站缺口）")
            for rec in recs:
                print(f"      {rec['station'] or '???'} | {rec['date'] or '???'} "
                      f"[{rec['suspected_cause']}] (ID: {rec['page_id'][:8]}...)")

        output = {
            "notion_db1_laifu": len(pages_laifu),
            "notion_db2_zaitai": len(pages_zaitai),
            "notion_station_keys": len(notion_keys),
            "json_total_stations": json_stations_count,
            "gap_count": len(missing),
            "suspected_relation_orphan": len(true_orphan_gaps),
            "suspected_name_mismatch": len(name_mismatch_gaps),
            "gaps": [
                {**notion_stations[k], "key": k}
                for k in sorted(missing)
            ],
        }
        print(f"\n--- JSON 輸出（可重導向至檔案） ---")
        print(json.dumps(output, ensure_ascii=False, indent=2))
        sys.exit(1)
    else:
        print("\n✅ 比對完全一致，無缺口！")
        sys.exit(0)


if __name__ == "__main__":
    main()
