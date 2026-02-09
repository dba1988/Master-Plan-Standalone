# Design Tokens Registry

> **Status**: LOCKED
> **Last Updated**: 2026-02-09
> **Authority**: This file is the SINGLE SOURCE OF TRUTH for all design tokens.

## Overview

This document defines the canonical design tokens for the Master Plan Standalone project.
All UI implementations (admin-ui, map-viewer) MUST reference these values.

**DO NOT** hardcode color values, spacing, or typography elsewhere.

---

## 1. Color Palette

### 1.1 Brand Colors

| Token | Hex | RGB | Usage |
|-------|-----|-----|-------|
| `color.brand.primary` | `#3F5277` | `rgb(63, 82, 119)` | Primary UI elements, buttons, links |
| `color.brand.secondary` | `#DAA520` | `rgb(218, 165, 32)` | Hover states, accents |
| `color.brand.accent` | `#F1DA9E` | `rgb(241, 218, 158)` | Active stroke, highlights |

### 1.2 Status Colors

| Token | Fill | Opacity | Stroke | Stroke Width |
|-------|------|---------|--------|--------------|
| `color.status.available` | `rgba(75, 156, 85, 0.50)` | `0.7` | `#FFFFFF` | `1px` |
| `color.status.reserved` | `rgba(255, 193, 7, 0.60)` | `0.6` | `#FFFFFF` | `1px` |
| `color.status.sold` | `rgba(170, 70, 55, 0.60)` | `0.5` | `#FFFFFF` | `1px` |
| `color.status.hidden` | `rgba(158, 158, 158, 0.30)` | `0.3` | `#FFFFFF` | `1px` |
| `color.status.unreleased` | `transparent` | `0` | `transparent` | `0` |

### 1.3 Semantic Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `color.background.primary` | `#FFFFFF` | `#1A1A2E` | Main background |
| `color.background.secondary` | `#F5F5F5` | `#16213E` | Card backgrounds |
| `color.background.tertiary` | `#EEEEEE` | `#0F3460` | Hover states |
| `color.text.primary` | `#212121` | `#FFFFFF` | Main text |
| `color.text.secondary` | `#757575` | `#B0B0B0` | Secondary text |
| `color.text.muted` | `#9E9E9E` | `#808080` | Disabled/muted text |
| `color.border.default` | `#E0E0E0` | `#2D2D44` | Default borders |
| `color.border.focus` | `#3F5277` | `#5A7AB8` | Focus rings |

### 1.4 Feedback Colors

| Token | Value | Usage |
|-------|-------|-------|
| `color.feedback.success` | `#4CAF50` | Success states |
| `color.feedback.warning` | `#FF9800` | Warning states |
| `color.feedback.error` | `#F44336` | Error states |
| `color.feedback.info` | `#2196F3` | Info states |

---

## 2. Typography

### 2.1 Font Family

```css
--font-family-primary: "IBM Plex Sans Arabic", Arial, sans-serif;
--font-family-mono: "IBM Plex Mono", monospace;
```

### 2.2 Font Sizes

| Token | Size | Line Height | Weight | Usage |
|-------|------|-------------|--------|-------|
| `typography.h1` | `2.5rem` (40px) | `1.2` | `600` | Page titles |
| `typography.h2` | `2rem` (32px) | `1.25` | `600` | Section titles |
| `typography.h3` | `1.5rem` (24px) | `1.3` | `500` | Card titles |
| `typography.h4` | `1.25rem` (20px) | `1.4` | `500` | Subsection titles |
| `typography.body.lg` | `1.125rem` (18px) | `1.5` | `400` | Large body text |
| `typography.body.md` | `1rem` (16px) | `1.5` | `400` | Default body text |
| `typography.body.sm` | `0.875rem` (14px) | `1.5` | `400` | Small body text |
| `typography.caption` | `0.75rem` (12px) | `1.4` | `400` | Captions, labels |
| `typography.overline` | `0.625rem` (10px) | `1.6` | `500` | Overline text |

### 2.3 Font Weights

| Token | Value | Usage |
|-------|-------|-------|
| `font.weight.light` | `300` | Light emphasis |
| `font.weight.regular` | `400` | Default text |
| `font.weight.medium` | `500` | Medium emphasis |
| `font.weight.semibold` | `600` | Strong emphasis |
| `font.weight.bold` | `700` | Bold emphasis |

---

## 3. Spacing

### 3.1 Base Scale

| Token | Value | Usage |
|-------|-------|-------|
| `spacing.0` | `0` | No spacing |
| `spacing.1` | `4px` | Minimal spacing |
| `spacing.2` | `8px` | Tight spacing |
| `spacing.3` | `12px` | Compact spacing |
| `spacing.4` | `16px` | Default spacing |
| `spacing.5` | `20px` | Comfortable spacing |
| `spacing.6` | `24px` | Relaxed spacing |
| `spacing.8` | `32px` | Loose spacing |
| `spacing.10` | `40px` | Section spacing |
| `spacing.12` | `48px` | Large section spacing |
| `spacing.16` | `64px` | Page section spacing |

### 3.2 Semantic Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `spacing.component.xs` | `4px` | Icon padding |
| `spacing.component.sm` | `8px` | Compact buttons |
| `spacing.component.md` | `12px` | Default buttons |
| `spacing.component.lg` | `16px` | Large buttons |
| `spacing.layout.gutter` | `24px` | Grid gutters |
| `spacing.layout.section` | `48px` | Between sections |
| `spacing.layout.page` | `64px` | Page margins |

---

## 4. Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius.none` | `0` | Sharp corners |
| `radius.sm` | `4px` | Subtle rounding |
| `radius.md` | `8px` | Default rounding |
| `radius.lg` | `12px` | Card rounding |
| `radius.xl` | `16px` | Modal rounding |
| `radius.2xl` | `24px` | Large elements |
| `radius.full` | `9999px` | Pills, circles |

---

## 5. Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `shadow.none` | `none` | No shadow |
| `shadow.xs` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `shadow.sm` | `0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)` | Cards |
| `shadow.md` | `0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)` | Dropdowns |
| `shadow.lg` | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | Modals |
| `shadow.xl` | `0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)` | Popovers |
| `shadow.inner` | `inset 0 2px 4px rgba(0,0,0,0.06)` | Inset elements |

---

## 6. Z-Index

| Token | Value | Usage |
|-------|-------|-------|
| `z.base` | `0` | Default stacking |
| `z.dropdown` | `100` | Dropdowns, select menus |
| `z.sticky` | `200` | Sticky headers |
| `z.overlay` | `300` | Overlay backgrounds |
| `z.modal` | `400` | Modal dialogs |
| `z.popover` | `500` | Popovers, tooltips |
| `z.toast` | `600` | Toast notifications |
| `z.max` | `9999` | Maximum (debugging) |

---

## 7. Transitions

| Token | Value | Usage |
|-------|-------|-------|
| `transition.fast` | `150ms ease-in-out` | Quick feedback |
| `transition.normal` | `250ms ease-in-out` | Default transitions |
| `transition.slow` | `350ms ease-in-out` | Deliberate animations |
| `transition.status` | `300ms ease-out` | Status color changes |

---

## 8. Breakpoints

| Token | Value | Description |
|-------|-------|-------------|
| `breakpoint.xs` | `0px` | Extra small (mobile) |
| `breakpoint.sm` | `640px` | Small (large mobile) |
| `breakpoint.md` | `768px` | Medium (tablet) |
| `breakpoint.lg` | `1024px` | Large (desktop) |
| `breakpoint.xl` | `1280px` | Extra large |
| `breakpoint.2xl` | `1536px` | 2X large |

---

## 9. Icon Sizes

| Token | Value | Usage |
|-------|-------|-------|
| `icon.xs` | `12px` | Inline icons |
| `icon.sm` | `16px` | Button icons |
| `icon.md` | `20px` | Default icons |
| `icon.lg` | `24px` | Large icons |
| `icon.xl` | `32px` | Feature icons |
| `icon.2xl` | `48px` | Hero icons |

---

## 10. Map Viewer Specific

### 10.1 Overlay Styling

| Token | Value | Usage |
|-------|-------|-------|
| `map.overlay.strokeWidth.default` | `1px` | Default stroke |
| `map.overlay.strokeWidth.hover` | `2px` | Hover stroke |
| `map.overlay.strokeWidth.active` | `2px` | Selected stroke |
| `map.overlay.hoverFill` | `rgba(218, 165, 32, 0.3)` | Hover fill |
| `map.overlay.hoverStroke` | `#F1DA9E` | Hover stroke color |
| `map.overlay.activeFill` | `rgba(63, 82, 119, 0.4)` | Active fill |
| `map.overlay.activeStroke` | `#3F5277` | Active stroke color |

### 10.2 Legend & UI

| Token | Value | Usage |
|-------|-------|-------|
| `map.legend.background` | `rgba(255, 255, 255, 0.95)` | Legend panel |
| `map.legend.padding` | `12px` | Legend padding |
| `map.legend.radius` | `8px` | Legend corners |
| `map.bottomSheet.maxHeight` | `60vh` | Mobile sheet height |
| `map.bottomSheet.handleHeight` | `4px` | Drag handle |

---

## Usage Examples

### CSS Variables (Recommended)

```css
:root {
  --color-brand-primary: #3F5277;
  --color-status-available: rgba(75, 156, 85, 0.50);
  --spacing-4: 16px;
  --radius-md: 8px;
}

.button-primary {
  background: var(--color-brand-primary);
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
}
```

### JavaScript/TypeScript

```typescript
import { tokens } from '@/theme/tokens';

const styles = {
  background: tokens.color.brand.primary,
  padding: tokens.spacing[4],
  borderRadius: tokens.radius.md,
};
```

### Styled Components

```typescript
import styled from 'styled-components';
import { tokens } from '@/theme/tokens';

const Button = styled.button`
  background: ${tokens.color.brand.primary};
  padding: ${tokens.spacing[4]};
  border-radius: ${tokens.radius.md};
`;
```

---

## Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-09 | 1.0.0 | Initial token registry created |

---

## References

- [STATUS-TAXONOMY.md](./STATUS-TAXONOMY.md) - Status definitions
- [TASK-000](../tasks/TASK-000-parity-harness.md) - Parity Harness
- [TASK-020](../tasks/TASK-020-viewer-scaffold.md) - Map Viewer implementation
- [TASK-014](../tasks/TASK-014-admin-ui-scaffold.md) - Admin UI implementation
