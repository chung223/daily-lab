# 📊 磁碟空間分析器（disk-usage-analyzer）

## 解決什麼問題

Chung 的 Mac 啟動碟（`/System/Volumes/Data`）連續多日處於 96-98% 滿的緊急狀態，導致：
- OpenClaw 備份腳本屢次 SIGTERM 中斷
- agentmemory 出現 Timeout 錯誤（空間不足寫入）
- 系統穩定性受到威脅

**核心痛點**：沒有工具能快速看出「空間到底被誰吃掉了」——尤其 Chung 的 home 裡有大量網路掛載（Google Drive、Dropbox、OrbStack），普通 `du -sh ~/*` 會永久卡死。

## 怎麼用

```bash
cd ~/...../Lab/2026-08-26-disk-analyzer/
chmod +x analyze-disk.sh
./analyze-disk.sh
```

輸出分為 8 個區塊：
1. **啟動碟容量**（含紅/黃/綠色警告）
2. **所有分區一覽**
3. **常見大空間目錄定點分析**
4. **Docker 系統空間**
5. **大檔案排行榜（>500MB）**
6. **node_modules 位置**
7. **OpenClaw workspace 內部細節**
8. **清理建議**

## 驗證方式與結果

**執行時間**：2026-08-26 09:16

**實測結果**：
```
⚠️  嚴重：容量已達 96%！（401Gi / 460Gi used，僅剩 17Gi）

OpenClaw 全家桶：
  ~/.openclaw/              34GB total
    workspace/              5.6GB
    workspace-second/       894MB
    backups/               2.8GB
```

腳本成功在 20 秒內完成全部分析，避開了所有網路掛載點，無卡死。

## 證據來源

- 2026-08-19 recap：磁碟 97% 滿（12GB 剩餘）
- 2026-08-22 recap：磁碟 98% 滿（11.1GB 剩餘），agentmemory Timeout 失敗
- 2026-08-19~25 recap：OpenClaw Backup 多次 SIGTERM 中斷
- 2026-08-21 recap：磁碟空間列為「待關注」

## 檔案

- `analyze-disk.sh` — 主腳本（可單獨使用）
- `README.md` — 本說明文件
