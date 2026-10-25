# SPEC.md — Session ICU 重症監護室

## 1. Concept & Vision

A vintage medical journal meets modern monitoring dashboard. When Chung's main session died from "LLM idle timeout", it felt like a patient flatlining. This project visualizes all OpenClaw sessions as patients in an ICU — showing their status, uptime, last activity, and a dramatic "revive" animation if you try to bring a dead session back. Ties into 三色蛋's "禪意房間" (Zen Room) concept — the AI was just sitting quietly, waiting... until it wasn't.

**Emotional tone:** Warm, slightly humorous medical nostalgia — like flipping through an old illustrated medical encyclopedia, but the patients are AI sessions.

## 2. Design Language

### Aesthetic Direction
**Vintage Medical Journal × Clinical Warmth** — Think 1920s medical illustrations meets modern monitoring. Clean, authoritative, but with humanity.

### Color Palette
- **Background:** Cream paper `#FAF7F2`
- **Primary (Medical Blue):** `#2B5F8A`
- **Accent (Heartbeat Red):** `#C94040`
- **Success (Vital Green):** `#3D7A5C`
- **Warning (Caution Yellow):** `#D4A84B`
- **Text:** Ink `#1C1409`
- **Muted:** `#8B8680`

### Typography
- **Headings:** Playfair Display (serif, authoritative)
- **Body:** Noto Serif TC (Chinese text)
- **Mono/Technical:** DM Mono (timestamps, IDs)
- **Handwritten notes:** Caveat (doctor's notes feel)

### Spatial System
- Generous whitespace (medical illustrations need room)
- Card-based layout with subtle paper texture
- 16px base, 8px rhythm

### Motion Philosophy
- Heartbeat pulse animation for alive sessions
- Flatline animation for dead sessions
- Dramatic "revive" animation (defibrillator style) when reviving
- Subtle paper rustling feel on hover

### Visual Assets
- Custom SVG icons: heart monitor, IV drip, stethoscope, pills
- ECG line animations
- Vintage medical cross motif (tasteful)
- Paper texture overlay

## 3. Layout & Structure

### Header
- "Session ICU 重症監護室" title in Playfair Display
- Subtitle: "系統對話健康監測"
- Current time display

### Session Grid (Main)
- 2-column responsive grid of session cards
- Each card shows:
  - Session name/label
  - Status indicator (alive flatline/heartbeat)
  - Uptime or "Time of death"
  - Last activity timestamp
  - Status badge (健康/危急/死亡)
  - "Revive" button (for dead sessions)

### Stats Panel
- Total sessions count
- Healthy / Critical / Dead breakdown
- System health percentage

### Footer
- Last refresh timestamp
- Manual refresh button

## 4. Features & Interactions

### Core Features
1. **Session List** — Display all sessions from sessions_list with status
2. **Status Detection** — Healthy (>activeMinutes threshold), Critical (recent activity but long session), Dead (failed/terminated)
3. **Uptime Display** — Show running time or time of death
4. **Revive Button** — For dead sessions, attempts to wake/restart
5. **Auto-refresh** — Every 30 seconds

### Interaction Details
- **Hover on card:** Slight lift, paper texture intensifies
- **Click revive:** 
  1. Button shows "搶救中..."
  2. ECG flatline briefly shows activity
  3. Success: heartbeat animation returns, card turns green
  4. Failure: stays dead, shows "搶救失敗" toast
- **Status badge colors:** Green (healthy), Yellow (critical), Red (dead)

### Edge Cases
- No sessions found: "ICU空空如也" message
- API error: Show last known state with "連線異常" warning
- All healthy: "所有病患狀態穩定" celebration

## 5. Component Inventory

### Session Card
- **States:** Healthy (green border, heartbeat pulse), Critical (yellow border, warning icon), Dead (red border, flatline)
- **Content:** Name, status badge, uptime/death time, last activity, action button
- **Animation:** Subtle pulse for healthy, static for dead

### Status Badge
- Pill-shaped, color-coded
- 、健康 (healthy), 危急 (critical), 死亡 (dead)

### Revive Button
- Default: Outline style, medical blue
- Hover: Filled blue
- Loading: Pulsing animation
- Success: Green, checkmark
- Error: Red, X mark

### Stats Counter
- Large number with label
- Color-coded by category

### ECG Line (SVG animation)
- Healthy: Animated zigzag pulse
- Dead: Flat line

## 6. Technical Approach

- **Pure HTML/CSS/JS** — Single index.html
- **API calls:** sessions_list tool to get current session data
- **LocalStorage:** Persist last known state for offline viewing
- **CDN:** Google Fonts (Playfair Display, Noto Serif TC, DM Mono, Caveat), anime.js for animations
- **Responsive:** Mobile-first, 2-col grid on desktop, 1-col on mobile
