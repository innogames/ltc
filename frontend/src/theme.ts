import { createTheme } from '@mui/material/styles';

import type { ErrorsLevel, SuccessLevel } from './api/types';

export const theme = createTheme({
  palette: {
    primary: { main: '#1a1a2e' },
    success: { main: '#2e7d32' },
    warning: { main: '#ed6c02' },
    error: { main: '#d32f2f' },
  },
  components: {
    MuiAppBar: {
      defaultProps: { elevation: 1 },
    },
  },
});

// API severity level -> MUI palette color name.
// Thresholds are decided server-side; never re-derive them here.
export function successColor(
  level: SuccessLevel,
): 'success' | 'warning' | 'error' {
  return level === 'danger' ? 'error' : level;
}

export function errorsColor(
  level: ErrorsLevel,
): 'success' | 'warning' | 'error' {
  if (level === 'crit') return 'error';
  if (level === 'warn') return 'warning';
  return 'success';
}

export const CHART_COLORS = {
  success: '#a1df6f',
  failure: '#df6f80',
  mean: '#1976d2',
  median: '#9c27b0',
  rps: '#2e7d32',
};
