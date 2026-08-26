#!/bin/bash
#==============================================================================
# 磁碟空間分析器 — disk-usage-analyzer
# 用途：分析本機磁碟空間使用，找出最大空間消耗者
# 使用：./analyze-disk.sh
# 特色：避開網路掛載點（會讓 du 永久卡住）
#==============================================================================

set -euo pipefail

# 顏色
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 已知會卡住的掛載點前綴（遇到就跳過）
SKIP_PREFIXES="/Volumes/T7 /Volumes/Google /Volumes/Dropbox /Users/chung/OrbStack /Users/chung/Google"

is_skipped_mount() {
    local path="$1"
    for prefix in $SKIP_PREFIXES; do
        if [[ "$path" == "$prefix"* ]]; then
            return 0
        fi
    done
    return 1
}

# 有超時的 du（Mac 相容）
du_timed() {
    local target="$1"
    local max_sec="${2:-10}"
    local result
    result=$(/usr/bin/env -i HOME="$HOME" PATH="$PATH" \
        perl -e '
            use File::Find;
            use POSIX strftime;
            $start = time();
            $max = $ARGV[1] || 10;
            $target = $ARGV[0];
            $size = 0;
            if (-d $target) {
                find($target, sub {
                    return if time() - $start > $max;
                    $size += -f $_ ? -s $_ : 0;
                });
                print format_size($size);
            } else {
                print "0";
            }
            sub format_size {
                my $s = shift;
                return "0" if $s < 1024;
                return sprintf("%.1fK", $s/1024) if $s < 1024**2;
                return sprintf("%.1fM", $s/1024**2) if $s < 1024**3;
                return sprintf("%.1fG", $s/1024**3);
            }
        ' "$target" "$max_sec" 2>/dev/null)
    echo "$result"
}

echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}  📊  磁碟空間分析器${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${CYAN}執行時間：$(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

#------------------------------------------------------------------------------
# 1. 整體磁碟概覽（只看 Data 分區 — 真正的啟動碟）
#------------------------------------------------------------------------------
echo -e "${BOLD}【1】啟動碟分區使用量${NC}"
echo "──────────────────────────────────────────"
DATA_PART=$(df -h /System/Volumes/Data 2>/dev/null | tail -1 || df -h / 2>/dev/null | tail -1)
echo "$DATA_PART"
TOTAL=$(echo "$DATA_PART" | awk '{print $2}')
USED=$(echo "$DATA_PART" | awk '{print $3}')
AVAIL=$(echo "$DATA_PART" | awk '{print $4}')
CAPACITY=$(echo "$DATA_PART" | awk '{print $5}')

# 警告判斷
CAP_NUM=$(echo "$CAPACITY" | tr -d '%')
if [ "$CAP_NUM" -ge 95 ]; then
    echo -e "  ${RED}⚠️  嚴重：容量已達 ${CAPACITY}！${NC}"
elif [ "$CAP_NUM" -ge 85 ]; then
    echo -e "  ${YELLOW}⚠️  警告：容量已達 ${CAPACITY}${NC}"
else
    echo -e "  ${GREEN}✅ 容量正常（${CAPACITY}）${NC}"
fi
echo ""

#------------------------------------------------------------------------------
# 2. 所有分區一覽
#------------------------------------------------------------------------------
echo -e "${BOLD}【2】所有分區一覽${NC}"
echo "──────────────────────────────────────────"
df -h 2>/dev/null | grep -E "^/dev|peer" | grep -v "tmpfs\|devfs\|map" | head -20
echo ""

#------------------------------------------------------------------------------
# 3. 使用者目錄定點分析（不走遍歷，避開卡死）
#------------------------------------------------------------------------------
echo -e "${BOLD}【3】常見大空間目錄定點分析${NC}"
echo "──────────────────────────────────────────"
echo -e "  ${YELLOW}（已自動避開網路/外接掛載點）${NC}"
echo ""

check_dir() {
    local dir="$1"
    local label="${2:-}"

    if ! [ -d "$dir" ]; then
        [ -n "$label" ] && echo -e "  ${CYAN}${dir}${NC} ${YELLOW}— 目錄不存在${NC}"
        return
    fi

    if is_skipped_mount "$dir"; then
        echo -e "  ${CYAN}${dir}${NC} ${YELLOW}— 跳過（網路/外接掛載）${NC}"
        return
    fi

    local size count
    # du 可能對某些目錄沒權限，2>/dev/null 吃掉錯誤
    size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "?")
    # find 也要低調
    count=$(find "$dir" -type f \( -path "*/.*" -prune \) -print 2>/dev/null | wc -l | tr -d ' ' || echo "?")

    echo -e "  ${CYAN}${dir}${NC}"
    echo -e "    ${GREEN}${size}${NC}  |  檔案 ${count}"
}

echo "--- 系統位置 ---"
check_dir "/Users/chung/.openclaw"               "OpenClaw 設定"
check_dir "/Users/chung/.openclaw/workspace"     "workspace"
check_dir "/Users/chung/.openclaw/workspace-second" "workspace-second"
check_dir "/Users/chung/.openclaw/backups"       "backups"
echo ""

echo "--- 應用程式資料 ---"
check_dir "/Users/chung/Library/Application Support"
check_dir "/Users/chung/Library/Caches"
check_dir "/Users/chung/Library/Logs"
echo ""

echo "--- 常用資料夾 ---"
check_dir "/Users/chung/Downloads"
check_dir "/Users/chung/Documents"
check_dir "/Users/chung/Desktop"
echo ""

echo "--- 開發工具快取 ---"
check_dir "/Users/chung/.npm"
check_dir "/Users/chung/.yarn"
check_dir "/Users/chung/.pnpm"
check_dir "/Users/chung/.cargo"
check_dir "/Users/chung/go/pkg/mod"
check_dir "/Users/chung/.gradle"
check_dir "/Users/chung/.cache"
echo ""

echo "--- Docker ---"
if [ -d "/Users/chung/.docker" ]; then
    check_dir "/Users/chung/.docker"
fi
echo ""

#------------------------------------------------------------------------------
# 4. Docker 系統空間
#------------------------------------------------------------------------------
echo -e "${BOLD}【4】Docker 系統空間${NC}"
echo "──────────────────────────────────────────"
if command -v docker &>/dev/null; then
    if docker info &>/dev/null; then
        echo -e "  ${GREEN}Docker 正在運行${NC}"
        echo ""
        docker system df 2>/dev/null
        echo ""
        echo -e "  ${BOLD}所有映像:${NC}"
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null | head -15
    else
        echo -e "  ${YELLOW}Docker 已安裝但未運行${NC}"
    fi
else
    echo -e "  ${YELLOW}Docker 未安裝${NC}"
fi
echo ""

#------------------------------------------------------------------------------
# 5. 大檔案搜尋（>500MB）
#------------------------------------------------------------------------------
echo -e "${BOLD}【5】大檔案排行榜（>500MB）${NC}"
echo "──────────────────────────────────────────"
echo -e "  ${YELLOW}搜尋中，預計需要幾秒...${NC}"
echo ""

# 只搜本機目錄，不搜網路掛載
BIG_FILES=$(find /Users/chung -type f -size +500M 2>/dev/null | head -20)
if [ -n "$BIG_FILES" ]; then
    echo "$BIG_FILES" | while read -r f; do
        [ -f "$f" ] || continue
        is_skipped_mount "$(dirname "$f")" && continue
        size=$(du -h "$f" 2>/dev/null | cut -f1 || echo "?")
        echo -e "  ${RED}${size}${NC}  ${f}"
    done
else
    echo -e "  ${GREEN}找不到 >500MB 的檔案${NC}"
fi
echo ""

#------------------------------------------------------------------------------
# 6. node_modules 大全
#------------------------------------------------------------------------------
echo -e "${BOLD}【6】node_modules 位置${NC}"
echo "──────────────────────────────────────────"
NM=$(find /Users/chung -name "node_modules" -type d 2>/dev/null | head -15)
if [ -n "$NM" ]; then
    echo "$NM" | while read -r dir; do
        is_skipped_mount "$dir" && continue
        size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "?")
        parent=$(dirname "$dir" | xargs basename 2>/dev/null)
        echo -e "  ${CYAN}${parent}/node_modules${NC} — ${GREEN}${size}${NC}"
    done
else
    echo -e "  ${GREEN}找不到 node_modules${NC}"
fi
echo ""

#------------------------------------------------------------------------------
# 7. OpenClaw workspace 內部細節
#------------------------------------------------------------------------------
echo -e "${BOLD}【7】OpenClaw workspace 內部${NC}"
echo "──────────────────────────────────────────"

if [ -d "/Users/chung/.openclaw/workspace" ]; then
    echo -e "  ${BOLD}workspace/${NC}"
    for subdir in /Users/chung/.openclaw/workspace/*/; do
        [ -d "$subdir" ] || continue
        is_skipped_mount "$subdir" && continue
        size=$(du -sh "$subdir" 2>/dev/null | cut -f1 || echo "?")
        name=$(basename "$subdir")
        echo -e "    ${CYAN}${name}/${NC} — ${size}"
    done
    echo ""
fi

if [ -d "/Users/chung/.openclaw/workspace-second" ]; then
    echo -e "  ${BOLD}workspace-second/${NC}"
    for subdir in /Users/chung/.openclaw/workspace-second/*/; do
        [ -d "$subdir" ] || continue
        is_skipped_mount "$subdir" && continue
        size=$(du -sh "$subdir" 2>/dev/null | cut -f1 || echo "?")
        name=$(basename "$subdir")
        echo -e "    ${CYAN}${name}/${NC} — ${size}"
    done
    echo ""
fi

#------------------------------------------------------------------------------
# 8. 清理建議
#------------------------------------------------------------------------------
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${BLUE}  💡  清理建議${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}依據以上分析結果，優先順序：${NC}"
echo ""
echo -e "  ${GREEN}1. npm/yarn/pnpm 快取${NC}"
echo -e "     ${CYAN}rm -rf ~/.npm/_cacache ~/.yarn ~/.pnpm 2>/dev/null${NC}"
echo ""
echo -e "  ${GREEN}2. Docker 清理（確認無重要容器後）${NC}"
echo -e "     ${CYAN}docker system prune -a --volumes${NC}"
echo ""
echo -e "  ${GREEN}3. 下載資料夾清理${NC}"
echo -e "     ${CYAN}ls -lt ~/Downloads/ | head -20${NC}"
echo ""
echo -e "  ${GREEN}4. 系統日誌（需管理員權限）${NC}"
echo -e "     ${CYAN}sudo rm -rf /private/var/log/asl/*.asl${NC}"
echo ""
echo -e "  ${GREEN}5. Google Drive 選擇性同步${NC}"
echo -e "     ${CYAN}Google Drive → 偏好設定 → 選擇性同步${NC}"
echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  分析完成 — $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
