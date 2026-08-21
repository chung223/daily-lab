# 河流不問方向 — The River Doesn't Ask

## Concept & Vision

三色蛋的凌晨夢境：【河流不問方向】——河流不知道自己要往哪裡去，只是往低處流。真正的長期思維不是豎立告示牌，而是確認腳下的路是否能持續走下去。這個專案是一個冥想式的流水視覺化，用水墨風格呈現三色蛋的河流哲學。

## Design Language

### Aesthetic Direction
**Sumi-e Ink × Zen Water** — 日本水墨畫禪境風格，結合流水動畫。與近期的漫畫風/孟菲斯幾何/暗色終端 完全不同的美學探索。

### Color Palette
- Background: 暖米白 #faf6f0 → 淡象牙 #f0ebe3
- Primary ink: 水墨黑 #1a1a1a → #2d2d2d
- Flow water: 淡藍灰 #8fa5b5 → #a8bdc9
- Accent: 硯台褐 #5c4a3d
- Highlight: 淡墨金 #c9a87c

### Typography
- Primary: Shippori Mincho (日式明朝體)
- Secondary: Noto Serif TC (中文襯線)
- Accent: Caveat (手寫風)

### Motion Philosophy
- 流水背景動畫：CSS 模擬的水波紋緩慢漂移
- 卡片懸停：淡墨暈染效果
- 點擊互動：漣漪擴散動畫
- 頁面載入：墨蹟暈染淡入

## Layout & Structure

### Page Structure
1. **Header**: 豎排標題「河流不問方向」，副標題引用
2. **Central Quote Card**: 核心語錄展示，橫幅卷軸造型
3. **Three Water States**: 三張垂直卡片
   - 河流 River（持續流動）
   - 地下水 Underground Spring（沉默存在）
   - 告示牌 Signpost（強加方向）
4. **Reflection Prompt**: 底部互動提示「你現在做的事情，是不是一條可以持續走下去的路？」
5. **Footer**: 三色蛋 credit + 發布連結

### Responsive Strategy
- Desktop: 三卡片橫排
- Mobile: 卡片垂直堆疊，全寬呈現

## Features & Interactions

### Core Features
1. 流水背景動畫（CSS animation, 持續循環）
2. 語錄卡片點擊：觸發漣漪動畫 + 顯示完整引言
3. 三狀態卡片 hover：墨蹟暈染效果
4. 底部反思輸入：使用者可以輸入自己的反思，localStorage 保存

### Interaction Details
- 點擊卡片：ripple effect (scale 0 → 1, opacity 0.8 → 0)
- Hover 卡片：box-shadow 暈染過渡 300ms
- 輸入框 focus：底部墨線生長動畫

### Edge Cases
- 無 localStorage：graceful degradation，輸入仍可用但不保存

## Component Inventory

### 1. Header
- 豎排大標題（writing-mode: vertical-rl）
- 淡墨副標題
- States: default only

### 2. Quote Banner
- 卷軸造型（左右裝飾圓軸）
- 核心語錄文字居中
- States: default, hover (淡光暈)

### 3. Water State Cards (×3)
- 圓角卡片，頂部彩色漸層標識
- Icon + 標題 + 描述 + 語錄
- States: default, hover (墨蹟暈染)

### 4. Ripple Effect
- 半透明圓形
- CSS animation: ripple expand + fade

### 5. Reflection Input
- 底線輸入框
- 書法筆觸裝飾
- States: default, focus (墨線生長)

### 6. Footer
- 三色蛋名稱 + 連結
- 小字版權

## Technical Approach

- Pure HTML + CSS + Vanilla JS
- CSS Custom Properties for colors
- CSS @keyframes for water flow animation
- localStorage for reflection persistence
- No external dependencies except Google Fonts
