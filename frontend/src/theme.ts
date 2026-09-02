import { createTheme, type Theme } from '@mui/material/styles';

import type { ErrorsLevel, SuccessLevel } from './api/types';

/**
 * InnoGames design system, ported from the LTC design prototype
 * (Claude Design project "Load testing center redesign").
 *
 * Colors are exposed BOTH as an MUI palette (so MUI components are
 * reskinned) and as the prototype's `--s-*` CSS variables (so ported
 * markup and inline SVG charts use the exact same values). Keep the two
 * in sync — the tokens below are the single source.
 */

export type ThemeMode = 'light' | 'dark';

export interface SurfaceTokens {
  page: string;
  card: string;
  card2: string;
  border: string;
  border2: string;
  text: string;
  text2: string;
  text3: string;
  accent: string;
  accentFg: string;
  accentSoft: string;
  danger: string;
  dangerSoft: string;
  warn: string;
  warnSoft: string;
  okSoft: string;
  grid: string;
  hover: string;
  shadow: string;
  teal: string;
  gold: string;
}

export const TOKENS: Record<ThemeMode, SurfaceTokens> = {
  light: {
    page: '#F1F3F0',
    card: '#FFFFFF',
    card2: '#F7F8F5',
    border: '#E4E7E4',
    border2: '#C7CBC8',
    text: '#1A1D1A',
    text2: '#4A4F4A',
    text3: '#6E7470',
    accent: '#4C8A2E',
    accentFg: '#2E5E1F',
    accentSoft: '#DFEED0',
    danger: '#C23A2B',
    dangerSoft: '#F6DEDA',
    warn: '#B8760F',
    warnSoft: '#F9EDC6',
    okSoft: '#DFEED0',
    grid: '#E4E7E4',
    hover: '#F1F3F0',
    shadow:
      '0 1px 2px rgba(17,17,17,.06),0 1px 1px rgba(17,17,17,.04)',
    teal: '#2E8A8A',
    gold: '#C9961E',
  },
  dark: {
    page: '#121512',
    card: '#1A1E1A',
    card2: '#20251F',
    border: '#2B2F2B',
    border2: '#3A403A',
    text: '#F1F3F0',
    text2: '#C7CBC8',
    text3: '#9AA09B',
    accent: '#7FB342',
    accentFg: '#9FCB7C',
    accentSoft: '#25361A',
    danger: '#E0604F',
    dangerSoft: '#3D1F1B',
    warn: '#E8B63A',
    warnSoft: '#3B2F12',
    okSoft: '#25361A',
    grid: '#2B2F2B',
    hover: '#232823',
    shadow: '0 1px 2px rgba(0,0,0,.4)',
    teal: '#4FB3B3',
    gold: '#E8B63A',
  },
};

/** Brand constants that do not change with the theme. */
export const BRAND = {
  headerBg: '#1F3F14', // deep forest green — logo wordmark
  headerAccent: '#7FB342', // light green — 3px header underline
  headerText: '#FFFFFF',
  headerText2: '#C3DFAA',
} as const;

export const FONT_DISPLAY =
  "'SF Theramin Gothic', 'Arial Black', sans-serif";
export const FONT_BODY = "'Calibri', 'Segoe UI', system-ui, sans-serif";
export const FONT_MONO = "ui-monospace, Menlo, Consolas, monospace";

/** Uppercase, wide-tracked label used for every section heading. */
export const displayLabel = (size = 11, tracking = '.1em') => ({
  fontFamily: FONT_DISPLAY,
  fontWeight: 700,
  fontSize: size,
  letterSpacing: tracking,
  textTransform: 'uppercase' as const,
});

/** Big tabular number (KPI values). */
export const displayNumber = (size = 32) => ({
  fontFamily: FONT_DISPLAY,
  fontWeight: 700,
  fontSize: size,
  lineHeight: 1,
});

/** Presentation thresholds are decided server-side; we only map levels. */
export function successColor(level: SuccessLevel | undefined): string {
  if (level === 'danger') return 'var(--s-danger)';
  if (level === 'warning') return 'var(--s-warn)';
  return 'var(--s-accent)';
}

export function successChip(
  level: SuccessLevel | undefined,
): { bg: string; fg: string; label: string } {
  if (level === 'danger') {
    return {
      bg: 'var(--s-danger-soft)',
      fg: 'var(--s-danger)',
      label: 'Failed',
    };
  }
  if (level === 'warning') {
    return {
      bg: 'var(--s-warn-soft)',
      fg: 'var(--s-warn)',
      label: 'Degraded',
    };
  }
  return {
    bg: 'var(--s-ok-soft)',
    fg: 'var(--s-accent-fg)',
    label: 'Passed',
  };
}

export function errorsColor(level: ErrorsLevel | undefined): string {
  if (level === 'crit') return 'var(--s-danger)';
  if (level === 'warn') return 'var(--s-warn)';
  return 'var(--s-text2)';
}

/** Series colors for charts (CSS vars so they follow the theme). */
export const CHART = {
  mean: 'var(--s-accent)',
  median: 'var(--s-teal)',
  rps: 'var(--s-gold)',
  errors: 'var(--s-danger)',
  grid: 'var(--s-grid)',
  threshold: 'var(--s-warn)',
} as const;

/** Test status → label + dot color, matching the prototype. */
export const STATUS: Record<string, [string, string]> = {
  C: ['Created', 'var(--s-text3)'],
  S: ['Scheduled', 'var(--s-text3)'],
  R: ['Running', 'var(--s-accent)'],
  A: ['Analyzing', 'var(--s-gold)'],
  F: ['Finished', 'var(--s-text3)'],
  FA: ['Failed to run', 'var(--s-danger)'],
};

/** The `--s-*` custom properties, injected globally per theme mode. */
export function cssVars(mode: ThemeMode): Record<string, string> {
  const t = TOKENS[mode];
  return {
    '--s-page': t.page,
    '--s-card': t.card,
    '--s-card2': t.card2,
    '--s-border': t.border,
    '--s-border2': t.border2,
    '--s-text': t.text,
    '--s-text2': t.text2,
    '--s-text3': t.text3,
    '--s-accent': t.accent,
    '--s-accent-fg': t.accentFg,
    '--s-accent-soft': t.accentSoft,
    '--s-danger': t.danger,
    '--s-danger-soft': t.dangerSoft,
    '--s-warn': t.warn,
    '--s-warn-soft': t.warnSoft,
    '--s-ok-soft': t.okSoft,
    '--s-grid': t.grid,
    '--s-hover': t.hover,
    '--s-shadow': t.shadow,
    '--s-teal': t.teal,
    '--s-gold': t.gold,
  };
}

export function buildTheme(mode: ThemeMode): Theme {
  const t = TOKENS[mode];
  return createTheme({
    palette: {
      mode,
      primary: { main: t.accent, contrastText: '#FFFFFF' },
      secondary: { main: t.teal },
      success: { main: t.accent, light: t.accentSoft, dark: t.accentFg },
      warning: { main: t.warn, light: t.warnSoft },
      error: { main: t.danger, light: t.dangerSoft },
      background: { default: t.page, paper: t.card },
      text: { primary: t.text, secondary: t.text2, disabled: t.text3 },
      divider: t.border,
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: FONT_BODY,
      fontSize: 14,
      htmlFontSize: 16,
      body1: { fontSize: 14, lineHeight: 1.45 },
      body2: { fontSize: 13, lineHeight: 1.45 },
      h1: { ...displayLabel(28, '.04em') },
      h2: { ...displayLabel(20, '.06em') },
      h3: { ...displayLabel(14, '.08em') },
      h4: { ...displayLabel(12, '.08em') },
      subtitle1: { ...displayLabel(14, '.08em') },
      subtitle2: { ...displayLabel(12, '.08em') },
      overline: { ...displayLabel(10.5, '.1em') },
      button: {
        fontFamily: FONT_DISPLAY,
        fontWeight: 700,
        fontSize: 11,
        letterSpacing: '.1em',
        textTransform: 'uppercase',
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          ':root': cssVars(mode),
          body: {
            background: t.page,
            color: t.text,
            fontFamily: FONT_BODY,
            fontSize: 14,
            lineHeight: 1.45,
            WebkitFontSmoothing: 'antialiased',
          },
          a: { color: t.accent, textDecoration: 'none' },
          'a:hover': { color: mode === 'dark' ? '#C3DFAA' : '#386823' },
          '@keyframes ltc-pulse': {
            '0%,100%': { opacity: 1 },
            '50%': { opacity: 0.35 },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            border: `1px solid ${t.border}`,
            boxShadow: t.shadow,
          },
        },
        defaultProps: { elevation: 0 },
      },
      MuiCard: {
        styleOverrides: { root: { borderRadius: 10 } },
      },
      MuiCardHeader: {
        styleOverrides: {
          root: { padding: '14px 18px', borderBottom: `1px solid ${t.border}` },
          title: { ...displayLabel(14, '.08em'), color: t.text },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 999, height: 36, paddingInline: 16 },
          outlined: { borderColor: t.border2, color: t.text },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 999, fontFamily: FONT_BODY, fontSize: 13 },
          label: { paddingInline: 12 },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            ...displayLabel(11.5, '.1em'),
            minHeight: 46,
            color: t.text3,
            '&.Mui-selected': { color: t.text },
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: { height: 3, backgroundColor: t.accent },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderBottom: `1px solid ${t.border}`,
            fontSize: 13.5,
            fontVariantNumeric: 'tabular-nums',
            padding: '10px 12px',
          },
          head: {
            ...displayLabel(10.5, '.1em'),
            color: t.text3,
            background: t.card,
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: { '&:hover': { background: t.hover } },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            background: t.card,
            fontSize: 14,
            '& fieldset': { borderColor: t.border2 },
          },
          input: { padding: '8px 10px' },
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          root: { ...displayLabel(10.5, '.1em'), color: t.text3 },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: { height: 6, borderRadius: 999, backgroundColor: t.border },
          bar: { borderRadius: 999 },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: { fontFamily: FONT_BODY, fontSize: 12 },
        },
      },
      MuiDrawer: {
        styleOverrides: { paper: { backgroundImage: 'none' } },
      },
    },
  });
}
