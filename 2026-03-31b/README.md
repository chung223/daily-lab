# Process Cards (腳本卡片管理)

視覺化腳本/程序管理面板，讓你一目了然掌握所有腳本的狀態。

## 功能

- 📋 視覺化腳本/程序管理面板
- ➕ 新增/編輯/刪除腳本卡片
- 🔄 狀態追蹤（運行中/閒置/錯誤/已停止）
- 📈 執行次數統計
- ⏰ 最後執行時間
- 💾 localStorage 持久化

## 技術

- 單一 HTML 檔案
- Google Fonts（Caveat + DM Mono + Noto Sans TC）
- CSS 動畫
- localStorage

## 設計

- Warm Paper Card 暖色紙卡片風
- 奶油白背景 (#faf7f2)
- 珊瑚 (#e07a5f)、青色 (#3d7a8c)、金色 (#d4a574)、紫色 (#8b7ec8) 多色點綴
- 狀態色彩左側標示條
- 卡片懸停浮動效果

## 靈感

系統監控腳本 `sync_aoa_to_gog.py` 收到 SIGTERM 錯誤，想做一個視覺化的腳本管理工具。

## 使用方式

直接用瀏覽器開啟 `index.html` 即可使用。

---

*Built with ☕ by 阿笨 — Daily Lab 2026-03-31b*
