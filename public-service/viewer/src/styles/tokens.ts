/**
 * Design tokens for Master Plan viewer.
 * Own copy - no shared code with admin-service.
 */

export const colors = {
  // Status colors (5-status taxonomy)
  status: {
    available: '#22c55e',   // Green
    reserved: '#eab308',    // Yellow
    sold: '#ef4444',        // Red
    hidden: '#6b7280',      // Gray
    unreleased: '#3b82f6',  // Blue
  },

  // UI colors
  ui: {
    background: '#ffffff',
    surface: '#f9fafb',
    border: '#e5e7eb',
    text: {
      primary: '#111827',
      secondary: '#6b7280',
      muted: '#9ca3af',
    },
  },

  // Overlay colors
  overlay: {
    hover: 'rgba(59, 130, 246, 0.3)',
    selected: 'rgba(59, 130, 246, 0.5)',
    default: 'rgba(0, 0, 0, 0.1)',
  },
} as const;

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const typography = {
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif",
  fontSize: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '24px',
    xxl: '32px',
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
} as const;

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  full: '9999px',
} as const;

export type StatusColor = keyof typeof colors.status;

export default {
  colors,
  spacing,
  typography,
  shadows,
  borderRadius,
};
