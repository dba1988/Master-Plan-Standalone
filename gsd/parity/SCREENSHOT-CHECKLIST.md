# Parity Screenshot Checklist

> **Status**: ACTIVE
> **Last Updated**: 2026-02-10
> **Purpose**: Capture baseline screenshots before development to ensure visual parity.

## Overview

This checklist ensures the new implementation matches the reference design.
Screenshots should be captured from the production/reference system and compared after each UI task.

---

## 1. Required Screenshots

### 1.1 Navigation

- [ ] `/master-plan` — Project list page
- [ ] Header with logo + locale toggle
- [ ] Breadcrumb navigation
- [ ] Footer (if applicable)

### 1.2 Project View

- [ ] `/master-plan/:project` — Full map view
- [ ] Zoom controls (+ / - buttons)
- [ ] Legend panel (collapsed)
- [ ] Legend panel (expanded)
- [ ] Status counts display

### 1.3 Zone Detail

- [ ] `/master-plan/:project/:zone` — Zoomed to zone
- [ ] Zone boundary highlighted
- [ ] Unit labels visible
- [ ] Mini-map navigator

### 1.4 Interactions

- [ ] Unit hover (available) — green highlight, cursor pointer
- [ ] Unit hover (sold) — red highlight, cursor default
- [ ] Unit hover (reserved) — yellow highlight, cursor default
- [ ] Unit selected — golden stroke
- [ ] Details panel open (bottom sheet / sidebar)

### 1.5 Status Colors (5 statuses)

- [ ] Available (green `#4B9C55`, opacity 0.7)
- [ ] Reserved (yellow `#FFC107`, opacity 0.6)
- [ ] Sold (red `#AA4637`, opacity 0.5)
- [ ] Hidden (gray `#9E9E9E`, opacity 0.3) — not visible
- [ ] Unreleased (transparent) — outline only

### 1.6 Locale

- [ ] English labels (LTR layout)
- [ ] Arabic labels (RTL layout)
- [ ] Locale toggle button

### 1.7 Responsive Breakpoints

- [ ] Desktop 1920x1080
- [ ] Desktop 1440x900
- [ ] Tablet 1024x768
- [ ] Tablet 768x1024 (portrait)
- [ ] Mobile 375x812 (iPhone X)
- [ ] Mobile 390x844 (iPhone 14)

### 1.8 Embed Mode

- [ ] `/gc` — Minimal chrome (no header/footer)
- [ ] `/gc?lang=ar` — Arabic embed
- [ ] `/gc?unit=A101` — Pre-selected unit

---

## 2. Admin UI Screenshots

### 2.1 Authentication

- [ ] Login page
- [ ] Login error state
- [ ] Loading state

### 2.2 Dashboard

- [ ] Projects list (empty state)
- [ ] Projects list (with projects)
- [ ] Project card hover

### 2.3 Project Detail

- [ ] Assets tab
- [ ] Editor tab
- [ ] Integrations tab
- [ ] Publish tab

### 2.4 Editor

- [ ] Canvas with overlays
- [ ] Layer panel
- [ ] Properties inspector
- [ ] Tool palette

---

## 3. Validation Process

### 3.1 Before Development

1. Capture all screenshots from production/reference
2. Store in `gsd/parity/screenshots/baseline/`
3. Document browser, viewport, date
4. Commit to repository

### 3.2 After Each UI Task

1. Capture same screenshots from development
2. Store in `gsd/parity/screenshots/{task-id}/`
3. Compare side-by-side against baseline
4. Document any differences

### 3.3 Deviation Handling

| Type | Action |
|------|--------|
| Intentional change | Document in PR description |
| Unintentional change | Fix before merge |
| Improvement | Get approval, update baseline |

### 3.4 Sign-off

- Visual QA approval required for all UI PRs
- Baseline updates require team lead approval

---

## 4. Screenshot Naming Convention

```
{route}_{state}_{viewport}.png

Examples:
master-plan_default_desktop-1920.png
master-plan-project_legend-open_desktop-1440.png
master-plan-project_unit-hover-available_tablet-1024.png
gc_embed-unit-selected_mobile-375.png
admin-login_error_desktop-1920.png
```

---

## 5. Tools & Setup

### Browser
- Chrome (latest stable)
- Same version across all captures

### Extensions
- Full Page Screen Capture (or built-in DevTools)
- Disable browser extensions during capture

### Viewport Sizes

| Name | Width | Height |
|------|-------|--------|
| Desktop XL | 1920 | 1080 |
| Desktop | 1440 | 900 |
| Tablet Landscape | 1024 | 768 |
| Tablet Portrait | 768 | 1024 |
| Mobile Large | 390 | 844 |
| Mobile | 375 | 812 |

### Settings
- System theme: Light
- OS: macOS (for consistent font rendering)
- Zoom: 100%

---

## 6. Comparison Checklist

For each screenshot pair (baseline vs current):

### Visual Elements
- [ ] Colors match exactly
- [ ] Spacing/margins consistent
- [ ] Alignment correct
- [ ] Typography matches (font, size, weight)
- [ ] Icons render correctly
- [ ] Images/logos match

### Interactive States
- [ ] Hover states match
- [ ] Active/selected states match
- [ ] Focus rings match
- [ ] Cursor styles match

### Layout
- [ ] Component positions match
- [ ] Responsive behavior matches
- [ ] Scroll behavior matches
- [ ] Overlay/modal positions match

### Localization
- [ ] RTL layout correct (Arabic)
- [ ] Text direction correct
- [ ] Number formatting correct
- [ ] Date formatting correct

---

## 7. Storage Structure

```
gsd/parity/screenshots/
├── baseline/
│   ├── viewer/
│   │   ├── master-plan_default_desktop-1920.png
│   │   ├── master-plan-project_legend-open_desktop-1920.png
│   │   └── ...
│   └── admin/
│       ├── admin-login_default_desktop-1920.png
│       └── ...
├── TASK-020/
│   ├── viewer/
│   │   └── ...
│   └── comparison-notes.md
└── TASK-014/
    └── ...
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-10 | 1.0.0 | Initial checklist |

---

## References

- [TOKENS.md](./TOKENS.md) - Design tokens
- [STATUS-TAXONOMY.md](./STATUS-TAXONOMY.md) - Status colors
- [TASK-020](../tasks/TASK-020-viewer-scaffold.md) - Viewer implementation
- [TASK-014](../tasks/TASK-014-ui-scaffold-auth.md) - Admin UI implementation
