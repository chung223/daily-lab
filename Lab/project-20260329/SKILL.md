# QR Forge — Daily Lab Build 2026-03-29

## Concept
QR Forge is a sleek, cyberpunk-styled QR code generator that makes creating and downloading QR codes a visually satisfying experience.

## Features
- Real-time QR code generation as you type
- Download QR code as PNG
- Generation history with thumbnails (localStorage)
- Clear history option
- Multiple QR code sizes
- Copy to clipboard support

## Design Direction
- **Aesthetic**: Retro-Terminal × Cyberpunk Glassmorphism
- **Background**: Deep space (#0a0a0f) with subtle grid
- **Primary**: Electric Cyan (#00f5ff)
- **Accent**: Warm Amber (#f59e0b)
- **Typography**: JetBrains Mono + Noto Sans TC
- **Effects**: Scan lines, glow effects, glassmorphism cards

## Technical
- Pure HTML + CSS + JS (single file)
- QRCode.js library via CDN
- Canvas API for QR rendering and PNG export
- localStorage for history

## Files
- index.html (standalone, open directly)
