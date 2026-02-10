/**
 * Ant Design Theme Configuration for Admin UI
 * Source of truth: gsd/parity/TOKENS.md
 */

import type { ThemeConfig } from 'antd';
import { colors, typography } from './tokens';

export const antTheme: ThemeConfig = {
  token: {
    // Brand Colors
    colorPrimary: colors.brand.primary,
    colorSuccess: colors.feedback.success,
    colorWarning: colors.feedback.warning,
    colorError: colors.feedback.error,
    colorInfo: colors.feedback.info,

    // Text Colors
    colorText: colors.text.primary,
    colorTextSecondary: colors.text.secondary,
    colorTextTertiary: colors.text.muted,

    // Background Colors
    colorBgContainer: colors.background.primary,
    colorBgLayout: colors.background.secondary,
    colorBgElevated: colors.background.primary,

    // Border
    colorBorder: colors.border.default,
    colorBorderSecondary: colors.border.default,

    // Typography
    fontFamily: typography.fontFamily.primary,
    fontSize: 14,
    fontSizeSM: 12,
    fontSizeLG: 16,
    fontSizeXL: 20,

    // Border Radius
    borderRadius: 8,
    borderRadiusSM: 4,
    borderRadiusLG: 12,

    // Spacing
    padding: 16,
    paddingSM: 12,
    paddingLG: 24,
    paddingXS: 8,

    margin: 16,
    marginSM: 12,
    marginLG: 24,
    marginXS: 8,

    // Control Heights
    controlHeight: 36,
    controlHeightSM: 28,
    controlHeightLG: 44,

    // Motion
    motionDurationFast: '0.15s',
    motionDurationMid: '0.25s',
    motionDurationSlow: '0.35s',
  },

  components: {
    Button: {
      primaryColor: colors.background.primary,
      borderRadius: 8,
    },
    Card: {
      borderRadiusLG: 12,
    },
    Input: {
      borderRadius: 8,
    },
    Select: {
      borderRadius: 8,
    },
    Table: {
      borderRadius: 8,
      headerBg: colors.background.secondary,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: colors.background.tertiary,
      itemSelectedColor: colors.brand.primary,
    },
    Layout: {
      siderBg: colors.background.primary,
      headerBg: colors.background.primary,
    },
    Modal: {
      borderRadiusLG: 12,
    },
    Notification: {
      borderRadiusLG: 8,
    },
    Message: {
      borderRadiusLG: 8,
    },
  },
};

export default antTheme;
