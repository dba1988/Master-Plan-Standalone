/**
 * Design Tokens for Admin UI
 * Source of truth: gsd/parity/TOKENS.md
 * DO NOT modify without updating TOKENS.md first
 */

// Brand Colors
export const colors = {
  brand: {
    primary: '#3F5277',
    secondary: '#DAA520',
    accent: '#F1DA9E',
  },

  // Background Colors
  background: {
    primary: '#FFFFFF',
    secondary: '#F5F5F5',
    tertiary: '#EEEEEE',
  },

  // Text Colors
  text: {
    primary: '#212121',
    secondary: '#757575',
    muted: '#9E9E9E',
    inverse: '#FFFFFF',
  },

  // Border Colors
  border: {
    default: '#E0E0E0',
    focus: '#3F5277',
  },

  // Feedback Colors
  feedback: {
    success: '#4CAF50',
    warning: '#FF9800',
    error: '#F44336',
    info: '#2196F3',
  },
} as const;

// Typography
export const typography = {
  fontFamily: {
    primary: "'IBM Plex Sans Arabic', Arial, sans-serif",
    mono: "'IBM Plex Mono', monospace",
  },
  fontSize: {
    xs: '0.625rem',   // 10px
    sm: '0.75rem',    // 12px
    md: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '2rem',    // 32px
    '4xl': '2.5rem',  // 40px
  },
  fontWeight: {
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    snug: 1.25,
    normal: 1.5,
    relaxed: 1.6,
  },
} as const;

// Spacing
export const spacing = {
  0: '0',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
} as const;

// Border Radius
export const radius = {
  none: '0',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  '2xl': '24px',
  full: '9999px',
} as const;

// Shadows
export const shadows = {
  none: 'none',
  xs: '0 1px 2px rgba(0,0,0,0.05)',
  sm: '0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)',
  md: '0 4px 6px rgba(0,0,0,0.1), 0 2px 4px rgba(0,0,0,0.06)',
  lg: '0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)',
  xl: '0 20px 25px rgba(0,0,0,0.1), 0 10px 10px rgba(0,0,0,0.04)',
  inner: 'inset 0 2px 4px rgba(0,0,0,0.06)',
} as const;

// Z-Index
export const zIndex = {
  base: 0,
  dropdown: 100,
  sticky: 200,
  overlay: 300,
  modal: 400,
  popover: 500,
  toast: 600,
  max: 9999,
} as const;

// Transitions
export const transitions = {
  fast: '150ms ease-in-out',
  normal: '250ms ease-in-out',
  slow: '350ms ease-in-out',
  status: '300ms ease-out',
} as const;

// Breakpoints
export const breakpoints = {
  xs: '0px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const;

// Icon Sizes
export const iconSizes = {
  xs: '12px',
  sm: '16px',
  md: '20px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
} as const;

// Export all tokens
export const tokens = {
  colors,
  typography,
  spacing,
  radius,
  shadows,
  zIndex,
  transitions,
  breakpoints,
  iconSizes,
} as const;

export default tokens;
