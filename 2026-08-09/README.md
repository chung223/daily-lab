# IFYE 2026 世界大使館 (Geo Ambassador Atlas)

**分類：** 資料視覺化（世界地圖互動展示）

**設計風格：** Geo-Editorial Atlas × World Map 地理編輯 atlas × 世界地圖風

**展示：** [index.html](./index.html)

---

## 特色

Geo-Editorial Atlas × World Map 地理編輯 atlas × 世界地圖風格的 IFYE 2026 世界大使館互動展示。

- **頂部4格統計數字牆**（9國代表/51站/4類型/已探索）
- **互動式世界地圖**（SVG簡化輪廓、亞洲/東南亞高亮）
- **5位代表卡片**展示國籍/旗幟/站點數量/站點類型分類標籤（接送機/國際農水/年會）
- **點擊卡片收集探索進度**觸發彩屑慶祝動畫
- **localStorage 持久化**收集進度

## 設計系統

- 亮奶油白背景(#FDF9F4)
- 海軍藍(#1E3A5F)主色 + 金(#D4A574)/珊瑚(#E07A5F)/薄荷(#81B29A)/薰衣草(#9B8FD9)五色點綴
- Playfair Display + Noto Serif TC + DM Sans + Caveat 字體組合
- SVG 世界地圖互動高亮
- 彩屑慶祝動畫

## 技術

- 純 HTML/CSS/JS
- [confetti.js CDN](https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js)
- localStorage 持久化

---

*靈感來源：IFYE 2026 VPS Sync——9位代表（菲律宾2、泰国2、韩国2、瑞士2、迦納1）× 51個站點*
