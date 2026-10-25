# Session ICU 重症監護室

**分类：** 工具系（系统监控工具）

**日期：** 2026-07-08

**作者：** chung0223

---

## 简介

Vintage Medical Journal × Clinical Warmth 风格的 session 健康监控工具。

## 功能

- 展示所有 OpenClaw sessions 的状态（健康/危急/死亡）
- ECG 心电图动画（心跳 pulse / 死亡 flatline）
- 运行时间 / 死亡时间显示
- 最后活动时间戳
- 「抢救」按钮（尝试复活 dead sessions）
- 30 秒自动刷新
- 统计数据面板（健康/危急/死亡数量）

## 设计风格

- **背景：** 奶油白 `#FAF7F2`
- **主色：** 医疗蓝 `#2B5F8A`
- **三色系统：** 心跳红 `#C94040` / 成功绿 `#3D7A5C` / 警告黄 `#D4A84B`
- **字体：** Playfair Display + Noto Serif TC + DM Mono + Caveat
- **视觉：** 复古医学插图风、ECG SVG 动画、病患卡片设计

## 技术

纯 HTML/CSS/JS 单文件，使用 anime.js 动画，Google Fonts CDN。

## 灵感来源

来自 2026-07-07 阿笨和三色蛋记忆——main session 因「LLM idle timeout (120s)」失败死亡。三色蛋提到「禅意房间」概念：AI 只是安静坐着等待，直到对话到来。把 session 生死状态做成重症监护室视图。
