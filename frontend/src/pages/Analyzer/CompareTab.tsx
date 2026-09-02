import {
  Box,
  FormControl,
  InputLabel,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';

import { useCompare } from '../../api/hooks';
import type {
  HighlightAction,
  HighlightType,
  TestReport,
} from '../../api/types';
import { num } from '../../lib/format';
import { displayLabel, displayNumber } from '../../theme';

const HIGHLIGHT_TEXT: Record<HighlightType, string> = {
  new_actions: 'New action, absent in the other run',
  absent_actions: 'Absent in the current run',
  higher_response_times: 'Response times significantly higher',
  lower_response_times: 'Response times significantly lower',
  lower_count: 'Executed significantly fewer times',
};

/** The API nests current/other action data; flatten for display. */
function flatten(h: HighlightAction): {
  name: string;
  delta: string;
  text: string;
} {
  const current = h.action.current_test;
  const other = h.action.other_test;
  const name =
    current?.name ?? other?.name ?? h.action.name ?? 'unknown action';
  let delta = '—';
  if (h.type === 'new_actions') delta = 'new';
  else if (h.type === 'absent_actions') delta = 'gone';
  else if (current?.data?.mean != null && other?.data?.mean) {
    const pct =
      ((current.data.mean - other.data.mean) / other.data.mean) * 100;
    delta = `${pct > 0 ? '+' : ''}${pct.toFixed(0)} %`;
  } else if (
    h.type === 'lower_count' &&
    current?.data?.count != null &&
    other?.data?.count
  ) {
    const pct =
      ((current.data.count - other.data.count) / other.data.count) * 100;
    delta = `${pct > 0 ? '+' : ''}${pct.toFixed(0)} %`;
  }
  return { name, delta, text: HIGHLIGHT_TEXT[h.type] ?? h.type };
}

function HighlightCount({
  value,
  label,
  bg,
  fg,
}: {
  value: number;
  label: string;
  bg: string;
  fg: string;
}) {
  return (
    <Box
      sx={{
        textAlign: 'center',
        p: 1.25,
        borderRadius: '6px',
        background: bg,
        color: fg,
      }}
    >
      <Box sx={{ ...displayNumber(22) }}>{value}</Box>
      <Box sx={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '.08em' }}>
        {label}
      </Box>
    </Box>
  );
}

export default function CompareTab({
  report,
  testId,
  compareId,
  onCompareChange,
  onSelectTest,
}: {
  report: TestReport;
  testId: number;
  compareId: number;
  onCompareChange: (id: number) => void;
  onSelectTest: (id: number) => void;
}) {
  const { data: compare, isLoading } = useCompare(testId, compareId);

  // compare_data comes newest-first from the API; chart reads left→right.
  const history = [...(report.compare_data ?? [])].reverse();
  const maxMean = Math.max(1, ...history.map((h) => h.mean ?? 0));

  const highlights = compare
    ? (
        [
          ['critical', 'var(--s-danger)'],
          ['warning', 'var(--s-warn)'],
          ['success', 'var(--s-accent)'],
        ] as const
      ).flatMap(([key, color]) =>
        compare.highlights[key].map((h) => ({ ...flatten(h), color })),
      )
    : [];

  return (
    <Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '1fr 360px' },
          gap: 2,
          mb: 2,
        }}
      >
        <Box
          sx={{
            border: '1px solid var(--s-border)',
            borderRadius: '8px',
            p: 2,
            minWidth: 0,
          }}
        >
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              mb: 1.25,
              flexWrap: 'wrap',
              gap: 1,
            }}
          >
            <Box sx={{ ...displayLabel(12, '.08em'), color: 'var(--s-text)' }}>
              Mean · median across last {history.length} runs
            </Box>
            <Box
              sx={{
                display: 'flex',
                gap: 1.75,
                fontSize: 12,
                color: 'var(--s-text3)',
              }}
            >
              <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '2px',
                    background: 'var(--s-accent)',
                  }}
                />
                mean
              </Box>
              <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.75 }}>
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: '2px',
                    background: 'var(--s-teal)',
                  }}
                />
                median
              </Box>
            </Box>
          </Box>

          {!history.length ? (
            <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
              No comparable runs in this project yet.
            </Typography>
          ) : (
            <>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'flex-end',
                  gap: 1.25,
                  height: 200,
                  borderBottom: '1px solid var(--s-border)',
                  px: 0.75,
                }}
              >
                {history.map((h) => {
                  const current = h.test_id === testId;
                  return (
                    <Tooltip
                      key={h.test_id}
                      title={`${h.test_name}: mean ${Math.round(h.mean)} ms`}
                    >
                      <Box
                        onClick={() => onSelectTest(h.test_id)}
                        sx={{
                          flex: 1,
                          display: 'flex',
                          alignItems: 'flex-end',
                          justifyContent: 'center',
                          gap: '2px',
                          height: '100%',
                          cursor: 'pointer',
                          background: current
                            ? 'var(--s-accent-soft)'
                            : 'transparent',
                          borderRadius: '4px 4px 0 0',
                          opacity:
                            current || compareId === h.test_id ? 1 : 0.55,
                        }}
                      >
                        <Box
                          sx={{
                            width: '38%',
                            height: `${Math.round((h.mean / maxMean) * 100)}%`,
                            background: 'var(--s-accent)',
                            borderRadius: '2px 2px 0 0',
                          }}
                        />
                        <Box
                          sx={{
                            width: '38%',
                            height: `${Math.round(((h.median ?? 0) / maxMean) * 100)}%`,
                            background: 'var(--s-teal)',
                            borderRadius: '2px 2px 0 0',
                          }}
                        />
                      </Box>
                    </Tooltip>
                  );
                })}
              </Box>
              <Box
                sx={{
                  display: 'flex',
                  gap: 1.25,
                  px: 0.75,
                  pt: 0.75,
                  fontSize: 11,
                  color: 'var(--s-text3)',
                }}
              >
                {history.map((h) => (
                  <Box
                    key={h.test_id}
                    sx={{
                      flex: 1,
                      textAlign: 'center',
                      fontWeight: h.test_id === testId ? 700 : 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h.test_name}
                  </Box>
                ))}
              </Box>
            </>
          )}
        </Box>

        <Box
          sx={{
            border: '1px solid var(--s-border)',
            borderRadius: '8px',
            p: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: 1.5,
          }}
        >
          <FormControl size="small" fullWidth>
            <InputLabel shrink>Compare against</InputLabel>
            <Select
              native
              value={compareId}
              onChange={(e) => onCompareChange(Number(e.target.value))}
            >
              <option value={0}>Previous run</option>
              {history
                .filter((h) => h.test_id !== testId)
                .map((h) => (
                  <option key={h.test_id} value={h.test_id}>
                    {h.test_name}
                  </option>
                ))}
            </Select>
          </FormControl>

          <Typography
            variant="body2"
            sx={{ color: 'var(--s-text2)', lineHeight: 1.5 }}
          >
            Comparing{' '}
            <Box component="b" sx={{ color: 'var(--s-text)' }}>
              {testId}
            </Box>{' '}
            with{' '}
            <Box component="b" sx={{ color: 'var(--s-text)' }}>
              {compareId
                ? compareId
                : (compare?.tests?.[1]?.id ?? 'previous run')}
            </Box>
            . Highlights use a Student&apos;s t-test on per-action response
            times.
          </Typography>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 1,
              mt: 'auto',
            }}
          >
            <HighlightCount
              value={compare?.highlights.critical.length ?? 0}
              label="critical"
              bg="var(--s-danger-soft)"
              fg="var(--s-danger)"
            />
            <HighlightCount
              value={compare?.highlights.warning.length ?? 0}
              label="warning"
              bg="var(--s-warn-soft)"
              fg="var(--s-warn)"
            />
            <HighlightCount
              value={compare?.highlights.success.length ?? 0}
              label="improved"
              bg="var(--s-ok-soft)"
              fg="var(--s-accent-fg)"
            />
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '360px 1fr' },
          gap: 2,
        }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box
            sx={{
              ...displayLabel(12, '.08em'),
              color: 'var(--s-text)',
              mb: 0.5,
            }}
          >
            Highlights
          </Box>
          {isLoading && (
            <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
              Running the comparison…
            </Typography>
          )}
          {!isLoading && !highlights.length && (
            <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
              No significant differences found.
            </Typography>
          )}
          {highlights.map((h, i) => (
            <Box
              key={`${h.name}-${i}`}
              sx={{
                display: 'flex',
                gap: 1.25,
                px: 1.5,
                py: 1.25,
                borderRadius: '6px',
                border: '1px solid var(--s-border)',
                background: 'var(--s-card2)',
              }}
            >
              <Box
                sx={{
                  flex: 'none',
                  width: 4,
                  borderRadius: '2px',
                  background: h.color,
                }}
              />
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 1,
                  }}
                >
                  <Box
                    title={h.name}
                    sx={{
                      fontFamily: 'ui-monospace, Menlo, monospace',
                      fontSize: 12,
                      fontWeight: 600,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {h.name}
                  </Box>
                  <Box sx={{ fontWeight: 700, color: h.color }}>{h.delta}</Box>
                </Box>
                <Box
                  sx={{ fontSize: 12, color: 'var(--s-text3)', mt: '2px' }}
                >
                  {h.text}
                </Box>
              </Box>
            </Box>
          ))}
        </Box>

        <Box
          sx={{
            border: '1px solid var(--s-border)',
            borderRadius: '8px',
            overflow: 'auto',
            maxHeight: 520,
          }}
        >
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Action</TableCell>
                <TableCell align="right">Mean</TableCell>
                <TableCell align="right">Δ</TableCell>
                <TableCell align="right">p50</TableCell>
                <TableCell align="right">p90</TableCell>
                <TableCell align="right">Count</TableCell>
                <TableCell align="right">Errors</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(compare?.compare_table ?? []).map((row) => {
                const delta = row.mean_2
                  ? ((row.mean_1 - row.mean_2) / row.mean_2) * 100
                  : 0;
                return (
                  <TableRow key={row.name} hover>
                    <TableCell
                      sx={{
                        fontFamily: 'ui-monospace, Menlo, monospace',
                        fontSize: 12,
                      }}
                    >
                      {row.name}
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <b>{Math.round(row.mean_1)}</b>{' '}
                      <Box component="span" sx={{ color: 'var(--s-text3)' }}>
                        / {Math.round(row.mean_2)}
                      </Box>
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{
                        fontWeight: 700,
                        color:
                          delta > 10
                            ? 'var(--s-danger)'
                            : delta < -10
                              ? 'var(--s-accent-fg)'
                              : 'var(--s-text3)',
                      }}
                    >
                      {`${delta > 0 ? '+' : ''}${delta.toFixed(0)} %`}
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      {Math.round(row.p50_1)} / {Math.round(row.p50_2)}
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      {Math.round(row.p90_1)} / {Math.round(row.p90_2)}
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{ whiteSpace: 'nowrap', color: 'var(--s-text2)' }}
                    >
                      {num(row.count_1)} / {num(row.count_2)}
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{
                        whiteSpace: 'nowrap',
                        color:
                          row.errors_1 > row.errors_2
                            ? 'var(--s-danger)'
                            : 'var(--s-text2)',
                      }}
                    >
                      {num(row.errors_1)} / {num(row.errors_2)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      </Box>
    </Box>
  );
}
