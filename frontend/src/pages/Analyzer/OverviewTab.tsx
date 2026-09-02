import { Box, Link as MuiLink, Typography } from '@mui/material';
import { useMemo } from 'react';

import type { AggregateRow, Test, TestReport } from '../../api/types';
import { KpiTile } from '../../components/Card';
import { SuccessDonut } from '../../components/charts';
import { num, signedPercent } from '../../lib/format';
import { displayLabel } from '../../theme';

const TOP_N = 6;
const SLOW_N = 10;

function n(row: AggregateRow, key: string): number {
  const value = row[key];
  return typeof value === 'number' ? value : Number(value) || 0;
}

function SectionCard({
  title,
  right,
  children,
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
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
          mb: 1.5,
        }}
      >
        <Box sx={{ ...displayLabel(12, '.08em'), color: 'var(--s-text)' }}>
          {title}
        </Box>
        {right}
      </Box>
      {children}
    </Box>
  );
}

export default function OverviewTab({
  report,
  test,
  onOpenAction,
}: {
  report: TestReport;
  test: Test | null;
  onOpenAction: (actionId: number) => void;
}) {
  const rows = report.test_action_aggregate_data ?? [];
  const threshold = report.slow_action_threshold_ms ?? 200;

  const totals = useMemo(() => {
    const count = rows.reduce((a, r) => a + n(r, 'count'), 0);
    const errors = rows.reduce((a, r) => a + n(r, 'errors'), 0);
    const weighted = rows.reduce((a, r) => a + n(r, 'mean') * n(r, 'count'), 0);
    return {
      count,
      errors,
      successPercent: count ? ((count - errors) * 100) / count : 0,
      mean: count ? weighted / count : 0,
      p90: rows.length ? Math.max(...rows.map((r) => n(r, '90%'))) : 0,
    };
  }, [rows]);

  const failed = useMemo(
    () =>
      rows
        .filter((r) => n(r, 'errors') > 0)
        .sort((a, b) => n(b, 'errors') - n(a, 'errors'))
        .slice(0, TOP_N),
    [rows],
  );
  const maxErrors = failed.length ? n(failed[0], 'errors') : 1;

  const slowest = useMemo(
    () => [...rows].sort((a, b) => n(b, 'mean') - n(a, 'mean')).slice(0, SLOW_N),
    [rows],
  );
  const maxMean = slowest.length ? n(slowest[0], 'mean') : 1;

  if (!rows.length) {
    return (
      <Typography sx={{ color: 'var(--s-text3)' }}>
        No aggregate data for this test — it may still be analyzing, or the
        result file was never parsed.
      </Typography>
    );
  }

  const meanDelta = test?.stats?.mean_diff_percent ?? null;

  return (
    <Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr 1fr',
            md: 'repeat(5, 1fr)',
          },
          gap: 1.5,
          mb: 2.5,
        }}
      >
        <KpiTile
          outlined
          size={26}
          label="Success rate"
          value={totals.successPercent.toFixed(2)}
          unit="%"
          color={
            totals.successPercent < 99 ? 'var(--s-danger)' : 'var(--s-accent)'
          }
        />
        <KpiTile
          outlined
          size={26}
          label="Mean"
          value={Math.round(totals.mean)}
          unit="ms"
          sub={
            meanDelta != null && (
              <Box
                sx={{
                  fontWeight: 700,
                  color:
                    meanDelta > 0
                      ? 'var(--s-danger)'
                      : meanDelta < 0
                        ? 'var(--s-accent-fg)'
                        : 'var(--s-text3)',
                }}
              >
                {signedPercent(meanDelta)}{' '}
                <Box
                  component="span"
                  sx={{ fontWeight: 400, color: 'var(--s-text3)' }}
                >
                  vs previous
                </Box>
              </Box>
            )
          }
        />
        <KpiTile
          outlined
          size={26}
          label="p90 (worst action)"
          value={Math.round(totals.p90)}
          unit="ms"
        />
        <KpiTile
          outlined
          size={26}
          label="Throughput"
          value={
            test?.duration
              ? Math.round(totals.count / test.duration)
              : '—'
          }
          unit="req/s"
        />
        <KpiTile
          outlined
          size={26}
          label="Errors"
          value={num(totals.errors)}
          unit="requests"
          color={totals.errors ? 'var(--s-danger)' : 'var(--s-text)'}
        />
      </Box>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: '300px 1fr 1.3fr' },
          gap: 2,
        }}
      >
        <SectionCard title="Success rate">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2.5 }}>
            <SuccessDonut successPercent={totals.successPercent} />
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                gap: 1.25,
                fontSize: 13,
              }}
            >
              <Box>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.75,
                    color: 'var(--s-text3)',
                  }}
                >
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '2px',
                      background: 'var(--s-accent)',
                    }}
                  />
                  Success
                </Box>
                <Box sx={{ fontWeight: 700, fontSize: 15 }}>
                  {num(totals.count - totals.errors)}
                </Box>
              </Box>
              <Box>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.75,
                    color: 'var(--s-text3)',
                  }}
                >
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '2px',
                      background: 'var(--s-danger)',
                    }}
                  />
                  Failed
                </Box>
                <Box sx={{ fontWeight: 700, fontSize: 15 }}>
                  {num(totals.errors)}
                </Box>
              </Box>
            </Box>
          </Box>
        </SectionCard>

        <SectionCard title="Top failed actions">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {!failed.length && (
              <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
                No failed actions
              </Typography>
            )}
            {failed.map((row) => {
              const errors = n(row, 'errors');
              const count = n(row, 'count');
              return (
                <Box
                  key={row.action_id}
                  onClick={() => onOpenAction(row.action_id)}
                  sx={{
                    cursor: 'pointer',
                    px: 1.25,
                    py: 1,
                    borderRadius: '6px',
                    background: 'var(--s-card2)',
                    '&:hover': { background: 'var(--s-hover)' },
                  }}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 1,
                      fontSize: 13,
                    }}
                  >
                    <MuiLink
                      component="span"
                      sx={{
                        fontWeight: 600,
                        color: 'var(--s-accent-fg)',
                        fontFamily: 'ui-monospace, Menlo, monospace',
                        fontSize: 12,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {row.action}
                    </MuiLink>
                    <Box sx={{ fontWeight: 700, color: 'var(--s-danger)' }}>
                      {num(errors)}
                    </Box>
                  </Box>
                  <Box
                    sx={{
                      height: 4,
                      borderRadius: 999,
                      background: 'var(--s-border)',
                      mt: 0.75,
                    }}
                  >
                    <Box
                      sx={{
                        height: '100%',
                        width: `${Math.round((errors / maxErrors) * 100)}%`,
                        background: 'var(--s-danger)',
                        borderRadius: 999,
                      }}
                    />
                  </Box>
                  <Box
                    sx={{ fontSize: 11.5, color: 'var(--s-text3)', mt: 0.5 }}
                  >
                    {count ? ((errors / count) * 100).toFixed(2) : '0'} % of{' '}
                    {num(count)} requests
                  </Box>
                </Box>
              );
            })}
          </Box>
        </SectionCard>

        <SectionCard
          title="Slowest actions"
          right={
            <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
              mean · threshold {threshold} ms
            </Typography>
          }
        >
          <Box
            sx={{
              position: 'relative',
              display: 'flex',
              flexDirection: 'column',
              gap: 0.875,
            }}
          >
            {maxMean > 0 && threshold < maxMean && (
              <Box
                sx={{
                  position: 'absolute',
                  top: -6,
                  bottom: -6,
                  left: `calc(180px + (100% - 180px) * ${threshold / maxMean})`,
                  borderLeft: '1px dashed var(--s-warn)',
                  zIndex: 1,
                }}
              />
            )}
            {slowest.map((row) => {
              const mean = n(row, 'mean');
              return (
                <Box
                  key={row.action_id}
                  onClick={() => onOpenAction(row.action_id)}
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: '180px 1fr',
                    alignItems: 'center',
                    gap: 1.25,
                    cursor: 'pointer',
                    fontSize: 12,
                  }}
                >
                  <Box
                    title={row.action}
                    sx={{
                      fontFamily: 'ui-monospace, Menlo, monospace',
                      color: 'var(--s-text2)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      textAlign: 'right',
                    }}
                  >
                    {row.action}
                  </Box>
                  <Box
                    sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                  >
                    <Box
                      sx={{
                        height: 16,
                        width: `${Math.max(1, Math.round((mean / maxMean) * 100))}%`,
                        background:
                          mean > threshold
                            ? 'var(--s-warn)'
                            : 'var(--s-accent)',
                        borderRadius: '3px',
                      }}
                    />
                    <Box sx={{ fontWeight: 700, color: 'var(--s-text)' }}>
                      {Math.round(mean)}
                    </Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        </SectionCard>
      </Box>
    </Box>
  );
}
