import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';

import type { AggregateRow, TestReport } from '../../api/types';
import { downloadCsv, num } from '../../lib/format';
import { errorsColor } from '../../theme';

const META_KEYS = new Set(['action', 'action_id', 'errors_level']);

function cellValue(row: AggregateRow, key: string): number | string {
  const value = row[key];
  if (value == null) return '—';
  return typeof value === 'number'
    ? Math.round(value * 10) / 10
    : String(value);
}

function ToggleChip({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <Box
      component="button"
      onClick={onClick}
      sx={{
        height: 34,
        px: 1.5,
        borderRadius: 999,
        cursor: 'pointer',
        fontFamily: 'inherit',
        fontSize: 13,
        fontWeight: 600,
        border: `1px solid ${active ? 'var(--s-accent)' : 'var(--s-border2)'}`,
        background: active ? 'var(--s-accent-soft)' : 'var(--s-card)',
        color: active ? 'var(--s-accent-fg)' : 'var(--s-text2)',
      }}
    >
      {label}
    </Box>
  );
}

export default function AggregateTab({
  report,
  onOpenAction,
}: {
  report: TestReport;
  onOpenAction: (actionId: number) => void;
}) {
  const [query, setQuery] = useState('');
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [slowOnly, setSlowOnly] = useState(false);
  const [sortKey, setSortKey] = useState('mean');
  const [sortDir, setSortDir] = useState(-1);

  const rows = report.test_action_aggregate_data ?? [];
  const threshold = report.slow_action_threshold_ms ?? 200;

  // Stat columns are dynamic: derived from the JSON keys of the first row.
  const keys = useMemo(
    () => (rows.length ? Object.keys(rows[0]).filter((k) => !META_KEYS.has(k)) : []),
    [rows],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = rows.filter((row) => {
      if (q && !row.action.toLowerCase().includes(q)) return false;
      if (errorsOnly && !(Number(row.errors) > 0)) return false;
      if (slowOnly && !(Number(row.mean) > threshold)) return false;
      return true;
    });
    return [...list].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'number' && typeof bv === 'number') {
        return (av - bv) * sortDir;
      }
      return String(av ?? '').localeCompare(String(bv ?? '')) * sortDir;
    });
  }, [rows, query, errorsOnly, slowOnly, threshold, sortKey, sortDir]);

  const sortBy = (key: string) => {
    if (key === sortKey) setSortDir((d) => -d);
    else {
      setSortKey(key);
      setSortDir(key === 'action' ? 1 : -1);
    }
  };

  const exportCsv = () => {
    const header = ['action', ...keys];
    downloadCsv(
      `ltc-test-${report.test_id}-aggregate.csv`,
      [
        header,
        ...visible.map((row) => [
          row.action,
          ...keys.map((k) => {
            const value = row[k];
            return value == null ? '' : value;
          }),
        ]),
      ] as (string | number)[][],
    );
  };

  if (!rows.length) {
    return (
      <Typography sx={{ color: 'var(--s-text3)' }}>
        No aggregate data for this test.
      </Typography>
    );
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          mb: 1.75,
          flexWrap: 'wrap',
        }}
      >
        <TextField
          size="small"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter actions…"
          sx={{ width: 280 }}
        />
        <ToggleChip
          label="Only with errors"
          active={errorsOnly}
          onClick={() => setErrorsOnly((v) => !v)}
        />
        <ToggleChip
          label={`Slower than ${threshold} ms`}
          active={slowOnly}
          onClick={() => setSlowOnly((v) => !v)}
        />
        <Box sx={{ flex: 1 }} />
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          {visible.length} actions · click a row for per-action history
        </Typography>
        <Button variant="outlined" onClick={exportCsv}>
          Export CSV
        </Button>
      </Box>

      <Box
        sx={{
          border: '1px solid var(--s-border)',
          borderRadius: '8px',
          overflow: 'auto',
          maxHeight: 620,
        }}
      >
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {['action', ...keys].map((key) => (
                <TableCell
                  key={key}
                  align={key === 'action' ? 'left' : 'right'}
                  onClick={() => sortBy(key)}
                  sx={{
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    userSelect: 'none',
                    color:
                      sortKey === key ? 'var(--s-text)' : 'var(--s-text3)',
                  }}
                >
                  {key}
                  {sortKey === key ? (sortDir < 0 ? ' ↓' : ' ↑') : ''}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visible.map((row) => (
              <TableRow
                key={row.action_id}
                hover
                onClick={() => onOpenAction(row.action_id)}
                sx={{
                  cursor: 'pointer',
                  background:
                    row.errors_level === 'crit'
                      ? 'var(--s-danger-soft)'
                      : 'transparent',
                }}
              >
                <TableCell
                  sx={{
                    color: 'var(--s-accent-fg)',
                    fontWeight: 600,
                    fontFamily: 'ui-monospace, Menlo, monospace',
                    fontSize: 12,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {row.action}
                </TableCell>
                {keys.map((key) => {
                  const isErrors = key === 'errors';
                  const isSlow =
                    key === 'mean' && Number(row.mean) > threshold;
                  return (
                    <TableCell
                      key={key}
                      align="right"
                      sx={{
                        whiteSpace: 'nowrap',
                        fontWeight:
                          (isErrors && row.errors_level !== 'ok') || isSlow
                            ? 700
                            : 400,
                        color: isErrors
                          ? errorsColor(row.errors_level)
                          : isSlow
                            ? 'var(--s-warn)'
                            : 'var(--s-text2)',
                      }}
                    >
                      {typeof cellValue(row, key) === 'number'
                        ? num(cellValue(row, key) as number, 1)
                        : cellValue(row, key)}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Box>
  );
}
