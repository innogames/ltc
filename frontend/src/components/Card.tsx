import { Box, type SxProps, Typography } from '@mui/material';
import type { ReactNode } from 'react';

import { displayLabel, displayNumber } from '../theme';

/** Panel with the prototype's card treatment and uppercase display title. */
export function Panel({
  title,
  actions,
  children,
  sx,
  bodySx,
  dense,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  sx?: SxProps;
  bodySx?: SxProps;
  dense?: boolean;
}) {
  return (
    <Box
      sx={{
        background: 'var(--s-card)',
        border: '1px solid var(--s-border)',
        borderRadius: '10px',
        boxShadow: 'var(--s-shadow)',
        overflow: 'hidden',
        ...sx,
      }}
    >
      {(title || actions) && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            flexWrap: 'wrap',
            px: 2.25,
            py: 1.75,
            borderBottom: dense ? 'none' : '1px solid var(--s-border)',
          }}
        >
          {title && (
            <Box sx={{ ...displayLabel(14, '.08em'), color: 'var(--s-text)' }}>
              {title}
            </Box>
          )}
          {actions && (
            <>
              <Box sx={{ flex: 1 }} />
              {actions}
            </>
          )}
        </Box>
      )}
      <Box sx={{ px: 2.25, py: 2, ...bodySx }}>{children}</Box>
    </Box>
  );
}

/** KPI tile: uppercase label, big display number, unit + delta line. */
export function KpiTile({
  label,
  value,
  unit,
  color = 'var(--s-text)',
  sub,
  size = 32,
  outlined,
}: {
  label: string;
  value: ReactNode;
  unit?: ReactNode;
  color?: string;
  sub?: ReactNode;
  size?: number;
  outlined?: boolean;
}) {
  return (
    <Box
      sx={{
        background: outlined ? 'var(--s-card2)' : 'var(--s-card)',
        border: '1px solid var(--s-border)',
        borderRadius: outlined ? '8px' : '10px',
        boxShadow: outlined ? 'none' : 'var(--s-shadow)',
        px: 2.25,
        py: 2,
      }}
    >
      <Box sx={{ ...displayLabel(11, '.1em'), color: 'var(--s-text3)' }}>
        {label}
      </Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'baseline',
          gap: 1,
          mt: 0.75,
        }}
      >
        <Box sx={{ ...displayNumber(size), color }}>{value}</Box>
        {unit && (
          <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
            {unit}
          </Typography>
        )}
      </Box>
      {sub && <Box sx={{ mt: 0.75, fontSize: 12 }}>{sub}</Box>}
    </Box>
  );
}

/** Uppercase status/result pill. */
export function Pill({
  label,
  bg,
  fg,
}: {
  label: ReactNode;
  bg: string;
  fg: string;
}) {
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-block',
        px: 1.25,
        py: '3px',
        borderRadius: 999,
        background: bg,
        color: fg,
        ...displayLabel(10.5, '.06em'),
      }}
    >
      {label}
    </Box>
  );
}
