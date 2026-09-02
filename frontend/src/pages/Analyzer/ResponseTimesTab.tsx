import { Box, Typography } from '@mui/material';
import { useMemo, useState } from 'react';

import type { Test, TestReport } from '../../api/types';
import { TimeseriesChart } from '../../components/charts';
import { fmtDur } from '../../lib/format';

type SeriesKey = 'mean' | 'median' | 'rps' | 'errors';

const SERIES: { key: SeriesKey; label: string; color: string }[] = [
  { key: 'mean', label: 'mean, ms', color: 'var(--s-accent)' },
  { key: 'median', label: 'median, ms', color: 'var(--s-teal)' },
  { key: 'rps', label: 'req/s', color: 'var(--s-gold)' },
  { key: 'errors', label: 'errors', color: 'var(--s-danger)' },
];

function roundUp(value: number, step: number) {
  return Math.max(step, Math.ceil(value / step) * step);
}

function SummaryCard({ children }: { children: React.ReactNode }) {
  return (
    <Box
      sx={{
        flex: 1,
        px: 1.75,
        py: 1.5,
        border: '1px solid var(--s-border)',
        borderRadius: '8px',
        background: 'var(--s-card2)',
        fontSize: 13,
        minWidth: 180,
      }}
    >
      {children}
    </Box>
  );
}

export default function ResponseTimesTab({
  report,
  test,
}: {
  report: TestReport;
  test: Test | null;
}) {
  const [visible, setVisible] = useState<Record<SeriesKey, boolean>>({
    mean: true,
    median: true,
    rps: true,
    errors: true,
  });

  const points = report.test_data ?? [];
  const threshold = report.slow_action_threshold_ms ?? 200;

  const stats = useMemo(() => {
    if (!points.length) {
      return { leftMax: 100, rightMax: 100, peak: null, above: 0, errors: 0 };
    }
    const leftMax = roundUp(
      Math.max(...points.map((p) => Math.max(p.mean ?? 0, p.median ?? 0))),
      100,
    );
    const rightMax = roundUp(
      Math.max(...points.map((p) => Math.max(p.rps ?? 0, p.errors ?? 0))),
      10,
    );
    const peakIndex = points.reduce(
      (best, p, i) => ((p.mean ?? 0) > (points[best].mean ?? 0) ? i : best),
      0,
    );
    return {
      leftMax,
      rightMax,
      peak: { index: peakIndex, value: points[peakIndex].mean ?? 0 },
      above: points.filter((p) => (p.mean ?? 0) > threshold).length,
      errors: points.reduce((a, p) => a + (p.errors ?? 0), 0),
    };
  }, [points, threshold]);

  if (!points.length) {
    return (
      <Typography sx={{ color: 'var(--s-text3)' }}>
        No timeseries data for this test.
      </Typography>
    );
  }

  const duration = test?.duration || 1800;
  const xLabels = [0, 0.2, 0.4, 0.6, 0.8, 1].map((f) =>
    fmtDur(Math.round(duration * f)),
  );

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          mb: 1.75,
          flexWrap: 'wrap',
        }}
      >
        {SERIES.map((s) => (
          <Box
            key={s.key}
            component="button"
            onClick={() =>
              setVisible((v) => ({ ...v, [s.key]: !v[s.key] }))
            }
            sx={{
              height: 30,
              px: 1.5,
              borderRadius: 999,
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: 12.5,
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 0.875,
              border: `1px solid ${
                visible[s.key] ? 'var(--s-border2)' : 'var(--s-border)'
              }`,
              background: visible[s.key] ? 'var(--s-card)' : 'transparent',
              color: visible[s.key] ? 'var(--s-text)' : 'var(--s-text3)',
            }}
          >
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '2px',
                background: s.color,
                opacity: visible[s.key] ? 1 : 0.4,
              }}
            />
            {s.label}
          </Box>
        ))}
        <Box sx={{ flex: 1 }} />
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          1 min resolution · {points.length} buckets
        </Typography>
      </Box>

      <Box
        sx={{
          border: '1px solid var(--s-border)',
          borderRadius: '8px',
          p: 2,
          pb: 1,
        }}
      >
        <TimeseriesChart
          leftMax={stats.leftMax}
          rightMax={stats.rightMax}
          thresholdMs={threshold}
          xLabels={xLabels}
          series={[
            {
              values: points.map((p) => p.errors ?? 0),
              color: 'var(--s-danger)',
              area: true,
              right: true,
              visible: visible.errors,
            },
            {
              values: points.map((p) => p.rps ?? 0),
              color: 'var(--s-gold)',
              width: 1.5,
              right: true,
              visible: visible.rps,
            },
            {
              values: points.map((p) => p.median ?? 0),
              color: 'var(--s-teal)',
              width: 1.8,
              visible: visible.median,
            },
            {
              values: points.map((p) => p.mean ?? 0),
              color: 'var(--s-accent)',
              width: 2.2,
              visible: visible.mean,
            },
          ]}
        />
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 10,
            letterSpacing: '.08em',
            color: 'var(--s-text3)',
            px: 6,
            pb: 0.5,
          }}
        >
          <span>MS</span>
          <span>REQ/S · ERRORS</span>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 1.5, mt: 1.75, flexWrap: 'wrap' }}>
        <SummaryCard>
          <Box component="span" sx={{ color: 'var(--s-text3)' }}>
            Peak mean{' '}
          </Box>
          <b>{Math.round(stats.peak?.value ?? 0)} ms</b>
          <Box component="span" sx={{ color: 'var(--s-text3)' }}>
            {' '}
            at{' '}
            {fmtDur(
              Math.round(
                (duration * (stats.peak?.index ?? 0)) /
                  Math.max(1, points.length - 1),
              ),
            )}
          </Box>
        </SummaryCard>
        <SummaryCard>
          <Box component="span" sx={{ color: 'var(--s-text3)' }}>
            Time above threshold{' '}
          </Box>
          <b>{Math.round((stats.above / points.length) * 100)} % of the run</b>
        </SummaryCard>
        <SummaryCard>
          <Box component="span" sx={{ color: 'var(--s-text3)' }}>
            Errors in run{' '}
          </Box>
          <b>
            {stats.errors ? stats.errors.toLocaleString() : 'none'}
          </b>
        </SummaryCard>
      </Box>
    </Box>
  );
}
