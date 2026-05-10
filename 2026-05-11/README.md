# 301 急診室 — 網站リダイレクト調査

用急診室病歷報告風格呈現網站 301 redirect loop 的除錯流程，包含 DNS/Curl/SSL/CF 診斷時間軸、互動式症狀過濾、處方箋建議、localStorage 偵探筆記儲存。

## 功能特色

- **🩺 症狀 Timeline**：6 步驟除錯流程，按類別過濾顯示
- **📋 患者資料**：URL、DNS、Proxy 狀態、主機資訊一目了然
- **💊 處方箋**：4 種可能原因與建議處理方向
- **📝 偵探筆記**：localStorage 自動儲存除錯心得
- **🎨 動畫背景**：漂浮幾何形狀，增加視覺趣味

## 使用方式

直接在瀏覽器開啟 `index.html` 即可使用。點擊上方分類按鈕可依階段篩選症狀，筆記會自動保存在瀏覽器。

## 設計風格

**Brighter Comic Action** — 亮色漫畫動作風，使用 Coral/Navy/Mint/Gold 配色，Bangers 手寫字體增加俏皮感。

## 技術

- 純 HTML/CSS/JS，無需後端
- Google Fonts: Bangers, Caveat, DM Mono, Noto Sans TC
- localStorage 持久化
- CSS 動畫與 hover 互動效果