#!/usr/bin/env node
/**
 * IFYE Sync 資料一致性稽核工具
 * =================================
 * 用途：檢查 Notion 資料庫與 ifye-2026.json 的資料一致性
 *       找出：孤立站 record、代表人名對應缺口、重複記錄
 *
 * 使用方式：
 *   node ifye-data-audit.js                  # 標準文字報告
 *   node ifye-data-audit.js --json           # JSON 格式輸出
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// ── 路徑 ──────────────────────────────────────────────────────────────────
const NOTION_SYNC_SCRIPT = '/Users/chung/.openclaw/scripts/ifye/sync-notion.mjs';
const JSON_DATA          = '/Users/chung/.openclaw/sites/ifye/2026/data/ifye-2026.json';
const LOG_FILE           = '/Users/chung/.openclaw/logs/ifye-sync.log';

// ── 參數 ──────────────────────────────────────────────────────────────────
const outputJSON = process.argv.includes('--json');

// ── 顏色 ──────────────────────────────────────────────────────────────────
const RED    = '\x1b[0;31m';
const YELLOW = '\x1b[0;33m';
const GREEN  = '\x1b[0;32m';
const BLUE   = '\x1b[0;34m';
const CYAN   = '\x1b[0;36m';
const NC     = '\x1b[0m';

// ── 統計 ──────────────────────────────────────────────────────────────────
let totalIssues = 0;

function warn(msg) {
  if (!outputJSON) console.log(`${YELLOW}[WARN]${NC} ${msg}`);
  totalIssues++;
}

function ok(msg) {
  if (!outputJSON) console.log(`${GREEN}[OK]${NC} ${msg}`);
}

function info(msg) {
  if (!outputJSON) console.log(`${BLUE}[INFO]${NC} ${msg}`);
}

function fail(msg) {
  if (!outputJSON) console.log(`${RED}[FAIL]${NC} ${msg}`);
  totalIssues++;
}

// ─────────────────────────────────────────────────────────────────────────
// Step 1: Run Notion sync to get fresh data
// ─────────────────────────────────────────────────────────────────────────
info('執行 Notion 同步取得最新資料...');

let notionOutput;
try {
  notionOutput = execSync(`node "${NOTION_SYNC_SCRIPT}"`, { encoding: 'utf8', timeout: 30000 });
} catch (err) {
  fail(`Notion 同步失敗：${err.message}`);
  process.exit(1);
}

// 解析數量（不用 grep -P，相容 macOS）
const visitorMatch   = notionOutput.match(/Found (\d+) visitors/);
const stationMatch   = notionOutput.match(/Found (\d+) station records/);

const notionVisitors = visitorMatch ? parseInt(visitorMatch[1]) : 0;
const notionStations = stationMatch ? parseInt(stationMatch[1]) : 0;

info(`Notion 來源：${notionVisitors} 位代表、${notionStations} 筆記錄`);

// ─────────────────────────────────────────────────────────────────────────
// Step 2: Read ifye-2026.json
// ─────────────────────────────────────────────────────────────────────────
info('讀取 ifye-2026.json...');

if (!fs.existsSync(JSON_DATA)) {
  fail(`找不到 ifye-2026.json：${JSON_DATA}`);
  process.exit(1);
}

let jsonData;
try {
  jsonData = JSON.parse(fs.readFileSync(JSON_DATA, 'utf8'));
} catch (err) {
  fail(`JSON 解析失敗：${err.message}`);
  process.exit(1);
}

const representatives = jsonData.representatives || [];
const jsonRepCount    = representatives.length;
const jsonStationCount = representatives.reduce((sum, r) => sum + (r.stations || []).length, 0);
const jsonUpdated     = jsonData.updatedAt || '';

info(`JSON 現況：${jsonRepCount} 位代表、${jsonStationCount} 站（更新時間：${jsonUpdated}）`);

// ─────────────────────────────────────────────────────────────────────────
// 報告
// ─────────────────────────────────────────────────────────────────────────
if (!outputJSON) {
  console.log('\n' + '═'.repeat(64));
  console.log('   IFYE 資料一致性稽核報告');
  console.log('═'.repeat(64) + '\n');
}

// Check 1: Station record count mismatch
if (!outputJSON) {
  console.log('【檢查 1】站記錄數量一致性');
  console.log('─'.repeat(40));
  console.log(`  Notion 來源記錄：  ${notionStations} 筆記錄`);
  console.log(`  JSON 寫入站數：    ${jsonStationCount} 站`);
  console.log(`  差值（孤立記錄）： ${notionStations - jsonStationCount} 筆記錄`);
}

const orphanCount = notionStations - jsonStationCount;
if (notionStations > jsonStationCount) {
  warn(`有 ${orphanCount} 筆記錄未被寫入 JSON（relation 對應失敗或人名比對漏接）`);
  if (!outputJSON) console.log('  → 請檢查 sync-notion.mjs 的 normalizeName 邏輯與 relation 欄位');
} else if (notionStations === jsonStationCount) {
  ok('站記錄數量完全一致');
}
if (!outputJSON) console.log('');

// Check 2: Per-representative station counts
if (!outputJSON) {
  console.log('【檢查 2】每位代表站數合理性');
  console.log('─'.repeat(40));
}

const EXPECTED_MIN = 3;
const EXPECTED_MAX = 10;
let anomalyReps = [];

representatives.forEach(r => {
  const cnt    = (r.stations || []).length;
  const name   = r.name || '(未知)';
  const country = r.country || '';
  let status = 'OK';

  if (cnt < EXPECTED_MIN)      status = 'LOW';
  else if (cnt > EXPECTED_MAX)  status = 'HIGH';

  if (!outputJSON) {
    const marker = status === 'OK' ? `${GREEN}✓` : `${YELLOW}⚠ ${status}`;
    console.log(`  ${marker}${NC}  ${name} (${country}): ${cnt} 站`);
  }
  if (status !== 'OK') anomalyReps.push(name);
});

if (anomalyReps.length > 0) {
  warn(`部分代表站數异常：${anomalyReps.join(', ')}`);
} else {
  ok(`所有代表站數在合理範圍（${EXPECTED_MIN}~${EXPECTED_MAX}站）`);
}
if (!outputJSON) console.log('');

// Check 3: Representative coverage
if (!outputJSON) {
  console.log('【檢查 3】代表覆蓋率');
  console.log('─'.repeat(40));
  console.log(`  JSON 代表數：${jsonRepCount} / 預期 9`);
}

const EXPECTED_REPS = 9;
if (jsonRepCount === EXPECTED_REPS) {
  ok('代表覆蓋率 100%');
} else if (jsonRepCount < EXPECTED_REPS) {
  warn(`代表數不足：少 ${EXPECTED_REPS - jsonRepCount} 位`);
}
if (!outputJSON) console.log('');

// Check 4: Duplicate stations
if (!outputJSON) {
  console.log('【檢查 4】重複站記錄');
  console.log('─'.repeat(40));
}

const seen   = new Set();
let dupeCount = 0;
let dupeExamples = [];

representatives.forEach(r => {
  (r.stations || []).forEach(s => {
    const key = `${s.station || ''}|${s.startDate || ''}|${s.endDate || ''}`;
    if (seen.has(key)) {
      dupeCount++;
      if (dupeExamples.length < 3) dupeExamples.push(`  ${s.station} (${s.startDate})`);
    } else {
      seen.add(key);
    }
  });
});

if (dupeCount > 0) {
  warn(`發現 ${dupeCount} 組重複站記錄`);
  dupeExamples.forEach(e => { if (!outputJSON) console.log(e); });
} else {
  ok('無重複站記錄');
}
if (!outputJSON) console.log('');

// Check 5: Sync log
if (!outputJSON) {
  console.log('【檢查 5】Sync 執行日誌');
  console.log('─'.repeat(40));
}

if (fs.existsSync(LOG_FILE)) {
  const logContent = fs.readFileSync(LOG_FILE, 'utf8');
  const doneMatches = logContent.match(/ifye-sync done/g) || [];
  const runCount = doneMatches.length;

  // 最近一次成功同步的時間戳
  const lastDoneMatch = logContent.match(/={3,} IFYE sync (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/g);
  const lastDone = lastDoneMatch ? lastDoneMatch[lastDoneMatch.length - 1].replace(/=+/g, '').trim() : '(找不到)';

  if (!outputJSON) {
    console.log(`  歷史總同步次數：${runCount}`);
    console.log(`  最近成功同步：${lastDone.replace('IFYE sync ', '')}`);
  }

  // 檢查 Permission denied（rsync 部署問題）
  const permDenied = (logContent.match(/Permission denied/g) || []).length;
  if (permDenied > 0) {
    warn(`發現 ${permDenied} 次 Permission denied（rsync 部署可能有權限問題）`);
  } else {
    ok('Sync log 無 rsync 錯誤');
  }
} else {
  warn(`找不到 log 檔案：${LOG_FILE}`);
}
if (!outputJSON) console.log('');

// Check 6: Known representative name matching
if (!outputJSON) {
  console.log('【檢查 6】人名對應完整性');
  console.log('─'.repeat(40));
}

const KNOWN_FIRST_NAMES = ['Ibrahim', 'Gary', 'Jihyun', 'Yerim', 'Phoobet', 'Dararat', 'Anna', 'Sven', 'Justice'];
const repNames = representatives.map(r => r.name || '');

const missing = KNOWN_FIRST_NAMES.filter(name =>
  !repNames.some(n => n.toLowerCase().includes(name.toLowerCase()))
);

if (missing.length > 0) {
  warn(`這些名字可能在 JSON 中未正確對應：${missing.join(', ')}`);
  if (!outputJSON) console.log('  → 請檢查 sync-notion.mjs 的 normalizeName 邏輯');
} else {
  ok('所有已知代表名字皆已對應');
}
if (!outputJSON) console.log('');

// Check 7: Recent sync stability
if (!outputJSON) {
  console.log('【檢查 7】最近同步穩定性');
  console.log('─'.repeat(40));
}

if (fs.existsSync(LOG_FILE)) {
  const logLines = fs.readFileSync(LOG_FILE, 'utf8').split('\n');
  const recentDone = logLines.filter(l => l.includes('ifye-sync done')).slice(-5);

  if (recentDone.length >= 5) {
    ok('最近 5 次同步皆成功');
  } else if (recentDone.length > 0) {
    warn(`最近同步記錄僅 ${recentDone.length} 次，確認排程是否正常`);
  }

  // 檢查是否真的每天都跑（過去 3 天）
  const threeDaysAgo = new Date();
  threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
  const recentSyncs = logLines.filter(l => {
    const dateMatch = l.match(/={3,} IFYE sync (\d{4}-\d{2}-\d{2})/);
    if (!dateMatch) return false;
    return new Date(dateMatch[1]) >= threeDaysAgo;
  });

  if (!outputJSON) {
    console.log(`  過去 3 天同步次數：${recentSyncs.length}`);
    if (recentSyncs.length >= 6) {
      ok('過去 3 天同步頻率正常（約每日 2 次）');
    } else {
      warn('過去 3 天同步頻率偏低');
    }
  }
}
if (!outputJSON) console.log('');

// ─────────────────────────────────────────────────────────────────────────
// 摘要
// ─────────────────────────────────────────────────────────────────────────
if (!outputJSON) {
  console.log('═'.repeat(64));
  console.log('   稽核摘要');
  console.log('═'.repeat(64) + '\n');
  console.log(`  Notion 來源：  ${notionVisitors} 位代表 × ${notionStations} 筆記錄`);
  console.log(`  JSON 寫入：    ${jsonRepCount} 位代表 × ${jsonStationCount} 站`);
  console.log(`  孤立記錄：     ${orphanCount} 筆記錄（未寫入 JSON）`);
  console.log('');
  console.log('  問題偵測：');
  console.log(`    孤立站（relation 未對應）： ${orphanCount}`);
  console.log(`    重複站記錄：               ${dupeCount}`);
  console.log('');
  console.log(`  總問題數：${totalIssues}`);
  console.log('');

  if (totalIssues === 0) {
    console.log(`${GREEN}✅ 所有檢查通過，資料完全一致${NC}`);
  } else {
    console.log(`${YELLOW}⚠ 發現 ${totalIssues} 個問題，請確認上圖${NC}`);
  }
  console.log('');
}

// ─────────────────────────────────────────────────────────────────────────
// JSON output
// ─────────────────────────────────────────────────────────────────────────
if (outputJSON) {
  console.log(JSON.stringify({
    auditTime:        new Date().toISOString(),
    notion:           { visitors: notionVisitors, stationRecords: notionStations },
    json:             { representatives: jsonRepCount, stations: jsonStationCount, updatedAt: jsonUpdated },
    orphanStations:   orphanCount,
    duplicateStations: dupeCount,
    totalIssues,
    representatives:  representatives.map(r => ({
      name:         r.name,
      country:      r.country,
      stationCount: (r.stations || []).length
    }))
  }, null, 2));
}

process.exit(totalIssues > 0 ? 1 : 0);
