# 暑假成长积分银行 Design System

## 1. Atmosphere & Identity

一个给家庭暑假使用的轻量成长工具，感觉应当像一本被认真使用的绿色手账：温和、有秩序、带一点仪式感，但不制造压力。标志性视觉是“成长账户”：把看不见的努力转成可存入、可复盘、可兑换、可归档的资产。

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | --surface-primary | #F6F5E8 | #15211C | Page background |
| Surface/secondary | --surface-secondary | #EEF5DD | #1D2C25 | Side panels |
| Surface/elevated | --surface-elevated | #FFFDF2 | #26362E | Cards, forms |
| Surface/mint | --surface-mint | #DDEDD0 | #2B4437 | Success panels |
| Text/primary | --text-primary | #213A31 | #F4FAEF | Headlines, body |
| Text/secondary | --text-secondary | #63746B | #BFD0C5 | Captions |
| Text/tertiary | --text-tertiary | #8A978F | #8EA397 | Disabled text |
| Border/default | --border-default | #D7E3CF | #3A5045 | Card borders |
| Border/subtle | --border-subtle | #E8EDD9 | #2D4137 | Soft lines |
| Accent/primary | --accent-primary | #4E9B83 | #77C4A7 | Primary actions |
| Accent/hover | --accent-hover | #3F856F | #8DD5BA | Hover state |
| Accent/warm | --accent-warm | #F2BD54 | #F5CA71 | Points, rewards |
| Status/success | --status-success | #3D8E63 | #78D19C | Completed tasks |
| Status/warning | --status-warning | #B97825 | #F0B15D | Redeem cautions |
| Status/error | --status-error | #B66555 | #E98C7D | Clear or destructive |
| Status/info | --status-info | #4E9B83 | #77C4A7 | Informational |

### Rules

- Use green as functional warmth, not decoration.
- Gold is reserved for points and rewards.
- All surface separation uses tonal shifts plus thin borders.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| Display | 36px | 800 | 1.15 | 0 | Main title |
| H1 | 30px | 800 | 1.2 | 0 | Page headers |
| H2 | 22px | 750 | 1.3 | 0 | Section headers |
| H3 | 18px | 750 | 1.35 | 0 | Card titles |
| Body/lg | 17px | 500 | 1.6 | 0 | Lead copy |
| Body | 15px | 500 | 1.55 | 0 | Default text |
| Body/sm | 13px | 500 | 1.45 | 0 | Secondary text |
| Caption | 12px | 650 | 1.35 | 0 | Labels |

### Font Stack

- Primary: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif
- Mono: "Cascadia Mono", Consolas, monospace

### Rules

- Body text never below 12px because this is a family-facing app.
- Use weight and color for hierarchy; avoid oversized type inside compact panels.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px.

| Token | Value | Usage |
|-------|-------|-------|
| --space-1 | 4px | Tight icon/text gaps |
| --space-2 | 8px | Compact controls |
| --space-3 | 12px | Input padding |
| --space-4 | 16px | Card padding |
| --space-5 | 20px | Panel padding |
| --space-6 | 24px | Page gutters |
| --space-8 | 32px | Section separation |
| --space-10 | 40px | Wide desktop gutters |

### Grid

- Max content width: 1280px
- Desktop: 300px sidebar plus flexible main area
- Tablet/mobile: stacked layout with sticky top navigation
- Breakpoints: 720px and 980px

### Rules

- Cards use 8px radius.
- Controls and tabs use pill radius when they represent immediate actions.
- Fixed-height task rows prevent layout shifts when checked.

## 5. Components

### Tab Bar
- **Structure**: horizontal button list with active pill.
- **Variants**: desktop centered, mobile scrollable.
- **Spacing**: --space-2 gaps, --space-3 horizontal padding.
- **States**: hover, active, focus.
- **Accessibility**: buttons expose selected tab with `aria-pressed`.
- **Motion**: opacity and transform only.

### Task Row
- **Structure**: checkbox, title, dimension tag, point badge.
- **Variants**: sidebar compact, main list.
- **Spacing**: --space-3 padding, fixed min-height.
- **States**: default, checked, focus.
- **Accessibility**: native checkbox plus label.
- **Motion**: short transform on point deposit.

### Account Card
- **Structure**: balance, explanatory text, action button.
- **Variants**: sidebar account, top compact balance.
- **Spacing**: --space-4 padding.
- **States**: default and hover for action.
- **Accessibility**: balance announced as text.
- **Motion**: no continuous animation.

### Profile Manager
- **Structure**: child profile selector, add action, editable child name, family sync key, backup actions.
- **Variants**: sidebar stacked on mobile and desktop.
- **Spacing**: --space-3 internal gaps, --space-2 selector/action gap.
- **States**: default, focus, synced, sync error, destructive delete, import error through status line.
- **Accessibility**: native select, labeled text/password input, file input visually hidden but keyboard-safe.
- **Motion**: button press only; no continuous animation.

### Achievement Deposit
- **Structure**: daily achievement textarea, extra point selector, deposit action.
- **Variants**: compact horizontal form on desktop, stacked form on mobile.
- **Spacing**: --space-3 gaps, --space-4 card padding.
- **States**: empty prompt, saved, replaced same-day entry.
- **Accessibility**: labeled selector and textarea, status line confirms saved points.
- **Motion**: button press only; no continuous animation.

## 6. Motion & Interaction

### Timing

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 120ms | ease-out | Button press, checkbox |
| Standard | 220ms | ease-in-out | Tab switch |
| Emphasis | 420ms | cubic-bezier(0.16, 1, 0.3, 1) | Card reveal |

### Rules

- Animate only `transform`, `opacity`, and `filter`.
- Respect `prefers-reduced-motion`.
- Every input and button has a visible focus state.

## 7. Depth & Surface

### Strategy

Mixed, but restrained: tonal-shift plus subtle border and a small green-tinted shadow for elevated panels.

| Level | Value | Usage |
|-------|-------|-------|
| Subtle | 0 1px 2px rgba(57, 91, 74, 0.06) | Rows |
| Default | 0 10px 30px rgba(57, 91, 74, 0.10) | Cards |
| Prominent | 0 18px 48px rgba(57, 91, 74, 0.14) | Main surface |
