import CloseIcon from '@mui/icons-material/Close';
import {
  Box,
  CircularProgress,
  Drawer,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

import { useActionDetails } from '../api/hooks';
import type { ActionBoxplot } from '../api/types';
import { num } from '../lib/format';
import { displayLabel } from '../theme';

/** Per-run distribution boxplots (min–max whiskers, IQR box, median line). */
function Boxplots({ runs }: { runs: ActionBoxplot[] }) {
  if (!runs.length) return null;
  const max = Math.max(1, ...runs.map((r) => r.max ?? 0));
  const y = (value: number) => 130 - (120 * value) / max;
  const step = 500 / Math.max(1, runs.length);
  return (
    <Box>
      <svg viewBox="0 0 500 140" width="100%" style={{ display: 'block' }}>
        {runs.map((run, i) => {
          const x = step * (i + 0.5);
          const boxWidth = Math.min(44, step * 0.5);
          const top = y(run.q3);
          const height = Math.max(1, y(run.q1) - y(run.q3));
          return (
            <g key={i}>
              <line
                x1={x}
                x2={x}
                y1={y(run.min)}
                y2={y(run.max)}
                stroke="var(--s-text3)"
              />
              <rect
                x={x - boxWidth / 2}
                y={top}
                width={boxWidth}
                height={height}
                fill="var(--s-accent-soft)"
                stroke="var(--s-accent)"
                rx={2}
              />
              <line
                x1={x - boxWidth / 2}
                x2={x + boxWidth / 2}
                y1={y(run.q2)}
                y2={y(run.q2)}
                stroke="var(--s-accent-fg)"
                strokeWidth={2}
              />
            </g>
          );
        })}
      </svg>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: `repeat(${runs.length}, 1fr)`,
          fontSize: 11,
          color: 'var(--s-text3)',
          textAlign: 'center',
          mt: 0.5,
        }}
      >
        {runs.map((run, i) => (
          <Box
            key={i}
            sx={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {run.test_name || '—'}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export default function ActionDetailsDrawer({
  testId,
  actionId,
  onClose,
}: {
  testId: number | null;
  actionId: number | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useActionDetails(testId, actionId);
  const open = actionId != null;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 560 },
          background: 'var(--s-card)',
          color: 'var(--s-text)',
        },
      }}
    >
      <Box
        sx={{
          px: 2.75,
          py: 2.25,
          borderBottom: '1px solid var(--s-border)',
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ ...displayLabel(10.5, '.1em'), color: 'var(--s-text3)' }}>
            Action details · last 5 runs
          </Box>
          <Box
            sx={{
              fontFamily: 'ui-monospace, Menlo, monospace',
              fontSize: 15,
              fontWeight: 600,
              mt: '2px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {data?.action.name ?? '…'}
          </Box>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Box
        sx={{
          px: 2.75,
          py: 2.25,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 2.25,
        }}
      >
        {isLoading && (
          <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
            <CircularProgress size={18} />
            <Typography sx={{ color: 'var(--s-text3)' }}>Loading…</Typography>
          </Box>
        )}

        {data && (
          <>
            <Box>
              <Box
                sx={{
                  ...displayLabel(12, '.08em'),
                  color: 'var(--s-text)',
                  mb: 1.25,
                }}
              >
                Distribution per run
              </Box>
              <Boxplots runs={data.action_data} />
            </Box>

            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Run</TableCell>
                  <TableCell align="right">min</TableCell>
                  <TableCell align="right">median</TableCell>
                  <TableCell align="right">mean</TableCell>
                  <TableCell align="right">max</TableCell>
                  <TableCell align="right">IQR</TableCell>
                  <TableCell align="right">std</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.action_data.map((run, i) => (
                  <TableRow key={i}>
                    <TableCell sx={{ fontWeight: 700 }}>
                      {run.test_name || `#${i + 1}`}
                    </TableCell>
                    <TableCell align="right">{num(run.min)}</TableCell>
                    <TableCell align="right">{num(run.q2)}</TableCell>
                    <TableCell align="right">{num(run.mean)}</TableCell>
                    <TableCell align="right">{num(run.max)}</TableCell>
                    <TableCell align="right">{num(run.IQR)}</TableCell>
                    <TableCell align="right">{num(run.std)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            <Box>
              <Box
                sx={{
                  ...displayLabel(12, '.08em'),
                  color: 'var(--s-text)',
                  mb: 1.25,
                }}
              >
                Errors in this run
              </Box>
              {!data.test_errors.length ? (
                <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
                  No errors for this action.
                </Typography>
              ) : (
                <Box
                  sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}
                >
                  {data.test_errors.map((error, i) => (
                    <Box
                      key={i}
                      sx={{
                        display: 'flex',
                        gap: 1.25,
                        px: 1.5,
                        py: 1.25,
                        borderRadius: '6px',
                        background: 'var(--s-danger-soft)',
                      }}
                    >
                      <Box
                        sx={{
                          flex: 'none',
                          fontWeight: 700,
                          color: 'var(--s-danger)',
                          fontFamily: 'ui-monospace, Menlo, monospace',
                        }}
                      >
                        {error.code || '—'} ×{num(error.count)}
                      </Box>
                      <Box sx={{ fontSize: 13, color: 'var(--s-text2)' }}>
                        {error.text}
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}
            </Box>
          </>
        )}
      </Box>
    </Drawer>
  );
}
