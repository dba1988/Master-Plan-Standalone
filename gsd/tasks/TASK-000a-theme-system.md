# TASK-000a: Theme System Implementation

**Phase**: 0 - Parity Harness
**Status**: [x] Completed
**Priority**: P0 - Critical (Blocker)
**Depends On**: TOKENS.md, STATUS-TAXONOMY.md
**Blocks**: TASK-014 (Admin UI), TASK-020 (Map Viewer)

## Objective

Implement theme tokens and status styling in both services. Per ARCHITECTURE.md, each service owns its own copy of design tokens.

> **IMPORTANT**: No shared `@masterplan/theme` package. Tokens are duplicated in each service following the "duplication is acceptable" principle.

## Token Locations

```
admin-service/ui/src/
├── styles/
│   ├── tokens.ts           # Design tokens from TOKENS.md
│   ├── status.ts           # Status colors from STATUS-TAXONOMY.md
│   ├── globals.css         # CSS variables
│   └── theme.ts            # Ant Design theme config

public-service/viewer/src/
├── styles/
│   ├── tokens.ts           # Design tokens (own copy)
│   ├── status-colors.ts    # Status colors (own copy)
│   └── globals.css         # CSS variables
```

## Token Source of Truth

All token values MUST match `gsd/parity/TOKENS.md`. Do NOT modify tokens without updating the source of truth first.

Reference TOKENS.md for:
- Brand colors (primary, secondary, accent)
- Status colors (5-status taxonomy with fill, stroke, solid variants)
- Typography (font family, sizes, weights)
- Spacing scale
- Border radius
- Shadows
- Z-index layers
- Transitions
- Breakpoints

## Status Styling

Reference `gsd/parity/STATUS-TAXONOMY.md` for canonical status definitions.

### Status Type
```typescript
type UnitStatus = 'available' | 'reserved' | 'sold' | 'hidden' | 'unreleased';
```

### Status Style Properties
Each status has:
- `fill`: RGBA color for overlay fill
- `fillOpacity`: Opacity value (0-1)
- `stroke`: Border color (typically white)
- `strokeWidth`: Border width in pixels
- `solid`: Opaque color for badges/pills

### Status Behavior
- `isSelectable(status)`: Only `available` returns true
- `isVisible(status)`: Returns false for `hidden`
- Hover/active states only apply to selectable statuses

### SVG Style States
1. **Default**: Uses status fill/stroke colors
2. **Hovered** (selectable only): Secondary color highlight
3. **Active**: Primary color highlight with thicker stroke

## CSS Variables

Generate CSS custom properties from tokens:
- Variables follow pattern: `--{category}-{name}` (e.g., `--color-brand-primary`)
- Inject into `:root` in globals.css

### Key Variable Groups
| Prefix | Examples |
|--------|----------|
| `--color-brand-*` | primary, secondary, accent |
| `--color-status-*-fill` | available-fill, sold-fill |
| `--color-status-*-solid` | available-solid, sold-solid |
| `--color-bg-*` | primary, secondary, tertiary |
| `--color-text-*` | primary, secondary, muted |
| `--spacing-*` | 1 through 16 |
| `--radius-*` | sm, md, lg, xl, full |
| `--shadow-*` | xs, sm, md, lg, xl |
| `--font-*` | family, size, weight |

## React Hooks

### Admin UI (admin-service/ui)

**useStatusStyle hook** for styling overlays and badges:

Input: `{ status, isHovered?, isActive? }`

Returns:
- All fill/stroke values
- `cursor`: 'pointer' for selectable, 'default' otherwise
- `isSelectable`: Boolean
- `isVisible`: Boolean

### Viewer (public-service/viewer)

**useStatusStyle hook** for overlay rendering:

Input: `{ status, isHovered?, isActive?, locale? }`

Returns:
- `svgStyle`: Ready-to-apply SVG attributes
- `label`: Localized status label (en/ar)
- Status metadata

## Admin UI Theme (Ant Design)

Configure Ant Design theme in `admin-service/ui/src/styles/theme.ts`:
- Primary color: Brand primary (#3F5277)
- Component token overrides as needed
- CSS variable integration

## Acceptance Criteria

- [x] Tokens implemented in `admin-service/ui/src/styles/tokens.ts`
- [x] Tokens implemented in `public-service/viewer/src/styles/tokens.ts`
- [x] Values match `gsd/parity/TOKENS.md` exactly
- [x] Status utilities match `gsd/parity/STATUS-TAXONOMY.md`
- [x] CSS variables generate correctly in both services
- [x] `useStatusStyle` hook works in both services
- [x] Status transitions animate smoothly (300ms ease-out)
- [x] Ant Design theme configured in admin-service/ui
