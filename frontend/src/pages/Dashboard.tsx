import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import {
  Box,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  DASHBOARD_POLL_MS,
  useLoadGenerators,
  useProjects,
  useTests,
} from '../api/hooks';
import type { LoadGenerator, Test } from '../api/types';
import { KpiTile, Panel, Pill } from '../components/Card';
import { Sparkline } from '../components/charts';
import { fmtDur, num, relTime, testLabel } from '../lib/format';
import { STATUS, successChip, successColor } from '../theme';

type StatusFilter = 'all' | 'active' | 'attention';

const ACTIVE_STATUSES = ['R', 'A'];

function isActive(test: Test) {
  return ACTIVE_STATUSES.includes(test.status);
}

function DeltaPill({ diff }: { diff: number | null }) {
  if (diff == null) {
    return (
      <Box component="span" sx={{ color: 'var(--s-text3)', ml: 1 }}>
        —
      </Box>
    );
  }
  const bg =
    diff > 10
      ? 'var(--s-danger-soft)'
      : diff < -10
        ? 'var(--s-ok-soft)'
        : 'var(--s-border)';
  const fg =
    diff > 10
      ? 'var(--s-danger)'
      : diff < -10
        ? 'var(--s-accent-fg)'
        : 'var(--s-text2)';
  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 0.25,
        ml: 1,
        minWidth: 58,
        justifyContent: 'center',
        px: 0.75,
        py: '1px',
        borderRadius: '4px',
        fontSize: 12,
        fontWeight: 700,
        background: bg,
        color: fg,
      }}
    >
      {diff > 0 ? (
        <ArrowUpwardIcon sx={{ fontSize: 12 }} />
      ) : diff < 0 ? (
        <ArrowDownwardIcon sx={{ fontSize: 12 }} />
      ) : null}
      {Math.abs(diff).toFixed(1)} %
    </Box>
  );
}

function FilterChip({
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
        height: 28,
        px: 1.5,
        borderRadius: 999,
        cursor: 'pointer',
        fontFamily: 'inherit',
        fontSize: 13,
        fontWeight: active ? 700 : 400,
        border: `1px solid ${active ? 'var(--s-accent)' : 'var(--s-border2)'}`,
        background: active ? 'var(--s-accent)' : 'var(--s-card)',
        color: active ? '#fff' : 'var(--s-text2)',
      }}
    >
      {label}
    </Box>
  );
}

function LastTestsTable({ tests }: { tests: Test[] }) {
  const navigate = useNavigate();
  if (!tests.length) {
    return (
      <Typography sx={{ color: 'var(--s-text3)', py: 2 }}>
        No tests yet.
      </Typography>
    );
  }
  return (
    <Box sx={{ overflowX: 'auto' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Test</TableCell>
            <TableCell>Started</TableCell>
            <TableCell align="right">VUs</TableCell>
            <TableCell align="right">Duration</TableCell>
            <TableCell align="right">Success</TableCell>
            <TableCell align="right">Mean · Δ prev</TableCell>
            <TableCell>Trend</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Result</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {tests.map((test) => {
            const stats = test.stats;
            const chip = successChip(stats?.success_level);
            const active = isActive(test);
            const [statusLabel, statusDot] = STATUS[test.status] ?? [
              test.status,
              'var(--s-text3)',
            ];
            const diff = stats?.mean_diff_percent ?? null;
            return (
              <TableRow
                key={test.id}
                hover
                onClick={() => navigate(`/analyzer?test=${test.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>
                  <Box sx={{ fontWeight: 700, color: 'var(--s-text)' }}>
                    {testLabel(test)}
                  </Box>
                  <Box sx={{ fontSize: 12, color: 'var(--s-text3)' }}>
                    {test.project?.name}
                  </Box>
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap', color: 'var(--s-text2)' }}>
                  {relTime(test.started_at)}
                </TableCell>
                <TableCell align="right" sx={{ color: 'var(--s-text2)' }}>
                  {num(test.threads)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ whiteSpace: 'nowrap', color: 'var(--s-text2)' }}
                >
                  {fmtDur(test.duration)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontWeight: 700,
                    color: successColor(stats?.success_level),
                  }}
                >
                  {stats ? `${stats.success_requests.toFixed(1)} %` : '—'}
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                  {active ? (
                    <Box component="span" sx={{ color: 'var(--s-text3)' }}>
                      —
                    </Box>
                  ) : (
                    <>
                      <Box
                        component="span"
                        sx={{ fontWeight: 700, color: 'var(--s-text)' }}
                      >
                        {stats?.mean != null
                          ? `${Math.round(stats.mean)} ms`
                          : '—'}
                      </Box>
                      <DeltaPill diff={diff} />
                    </>
                  )}
                </TableCell>
                <TableCell sx={{ py: 0.75 }}>
                  <Sparkline
                    values={stats?.spark ?? []}
                    color={
                      diff != null && diff > 10
                        ? 'var(--s-danger)'
                        : 'var(--s-accent)'
                    }
                  />
                </TableCell>
                <TableCell sx={{ whiteSpace: 'nowrap' }}>
                  <Box
                    component="span"
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 0.75,
                      color: 'var(--s-text2)',
                    }}
                  >
                    <Box
                      component="span"
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: 99,
                        background: statusDot,
                        animation: active
                          ? 'ltc-pulse 1.6s ease-in-out infinite'
                          : 'none',
                      }}
                    />
                    {statusLabel}
                  </Box>
                </TableCell>
                <TableCell>
                  {test.status === 'FA' ? (
                    <Pill
                      label="Aborted"
                      bg="var(--s-danger-soft)"
                      fg="var(--s-danger)"
                    />
                  ) : active ? (
                    <Pill label="…" bg="var(--s-border)" fg="var(--s-text3)" />
                  ) : (
                    <Pill label={chip.label} bg={chip.bg} fg={chip.fg} />
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </Box>
  );
}

function ActiveTests({ tests }: { tests: Test[] }) {
  const navigate = useNavigate();
  return (
    <Panel title="Active tests">
      {!tests.length ? (
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          No running tests
        </Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.75 }}>
          {tests.map((test) => {
            const started = test.started_at
              ? new Date(test.started_at).getTime()
              : Date.now();
            const elapsed = (Date.now() - started) / 1000;
            const pct = test.duration
              ? Math.min(100, (elapsed / test.duration) * 100)
              : 0;
            const analyzing = test.status === 'A';
            return (
              <Box
                key={test.id}
                onClick={() => navigate(`/analyzer?test=${test.id}`)}
                sx={{ cursor: 'pointer' }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                  }}
                >
                  <Box sx={{ fontWeight: 700 }}>{testLabel(test)}</Box>
                  <Box sx={{ fontSize: 12, color: 'var(--s-text3)' }}>
                    {analyzing
                      ? 'analyzing…'
                      : `${fmtDur(Math.max(0, test.duration - elapsed))} left`}
                  </Box>
                </Box>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                    color: 'var(--s-text3)',
                    mt: '2px',
                    mb: 0.75,
                  }}
                >
                  <span>
                    {num(test.threads)} VUs · {STATUS[test.status]?.[0]}
                  </span>
                  <span>{Math.round(analyzing ? 100 : pct)} %</span>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={analyzing ? 100 : pct}
                  sx={{
                    '& .MuiLinearProgress-bar': {
                      background: analyzing
                        ? 'var(--s-gold)'
                        : 'var(--s-accent)',
                    },
                  }}
                />
              </Box>
            );
          })}
        </Box>
      )}
    </Panel>
  );
}

function Bar({
  value,
  color,
}: {
  value: number;
  color: string;
}) {
  return (
    <Box
      sx={{
        height: 4,
        borderRadius: 999,
        background: 'var(--s-border)',
        mt: 0.5,
      }}
    >
      <Box
        sx={{
          height: '100%',
          width: `${Math.max(0, Math.min(100, value))}%`,
          background: color,
          borderRadius: 999,
        }}
      />
    </Box>
  );
}

function Generators({ generators }: { generators: LoadGenerator[] }) {
  const online = generators.filter((g) => g.active).length;
  return (
    <Panel
      title="Load generators"
      actions={
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          {online} of {generators.length} online
        </Typography>
      }
      sx={{ mt: 2.5 }}
    >
      {!generators.length ? (
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          No load generators
        </Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {generators.map((g) => {
            const memPct =
              g.memory && g.memory_free != null
                ? Math.round(((g.memory - g.memory_free) / g.memory) * 100)
                : 0;
            const laPct =
              g.la_1 != null && g.num_cpu
                ? Math.min(100, Math.round((g.la_1 / g.num_cpu) * 100))
                : 0;
            const badgeBg = !g.active
              ? 'var(--s-border)'
              : g.jmeter >= 5
                ? 'var(--s-danger-soft)'
                : g.jmeter >= 3
                  ? 'var(--s-warn-soft)'
                  : 'var(--s-ok-soft)';
            const badgeFg = !g.active
              ? 'var(--s-text3)'
              : g.jmeter >= 5
                ? 'var(--s-danger)'
                : g.jmeter >= 3
                  ? 'var(--s-warn)'
                  : 'var(--s-accent-fg)';
            return (
              <Box
                key={g.id}
                sx={{
                  px: 1.5,
                  py: 1.25,
                  border: '1px solid var(--s-border)',
                  borderRadius: '8px',
                  background: 'var(--s-card2)',
                  opacity: g.active ? 1 : 0.55,
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 1,
                  }}
                >
                  <Box
                    sx={{
                      fontWeight: 700,
                      fontSize: 13,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={g.hostname}
                  >
                    {g.hostname.split('.')[0]}
                  </Box>
                  <Box
                    title="JMeter instances"
                    sx={{
                      flex: 'none',
                      minWidth: 22,
                      height: 22,
                      px: 0.875,
                      borderRadius: 999,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: 12,
                      background: badgeBg,
                      color: badgeFg,
                    }}
                  >
                    {g.active ? g.jmeter : 'off'}
                  </Box>
                </Box>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 1.25,
                    mt: 1,
                    fontSize: 12,
                    color: 'var(--s-text3)',
                  }}
                >
                  <Box>
                    <Box
                      sx={{ display: 'flex', justifyContent: 'space-between' }}
                    >
                      <span>Memory</span>
                      <Box component="span" sx={{ color: 'var(--s-text2)' }}>
                        {g.active && g.memory != null
                          ? `${num(g.memory_free, 1)} / ${num(g.memory, 0)} free`
                          : 'offline'}
                      </Box>
                    </Box>
                    <Bar
                      value={memPct}
                      color={
                        memPct > 85 ? 'var(--s-danger)' : 'var(--s-accent)'
                      }
                    />
                  </Box>
                  <Box>
                    <Box
                      sx={{ display: 'flex', justifyContent: 'space-between' }}
                    >
                      <span>Load 1/5/15</span>
                      <Box component="span" sx={{ color: 'var(--s-text2)' }}>
                        {g.active && g.la_1 != null
                          ? `${num(g.la_1, 1)} / ${num(g.la_5, 1)} / ${num(g.la_15, 1)}`
                          : '—'}
                      </Box>
                    </Box>
                    <Bar
                      value={laPct}
                      color={laPct > 60 ? 'var(--s-warn)' : 'var(--s-accent)'}
                    />
                  </Box>
                </Box>
              </Box>
            );
          })}
        </Box>
      )}
    </Panel>
  );
}

export default function Dashboard() {
  const [projectFilter, setProjectFilter] = useState(0);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const { data: projects } = useProjects();
  // Never-started tests carry no metrics — the API hides them for us.
  const { data: tests, isLoading } = useTests(
    { started: true, pageSize: 60 },
    { refetchInterval: DASHBOARD_POLL_MS },
  );
  const { data: generators } = useLoadGenerators({
    refetchInterval: DASHBOARD_POLL_MS,
  });

  const all = tests?.results ?? [];

  const rows = useMemo(() => {
    let list = all;
    if (projectFilter) {
      list = list.filter((t) => t.project?.id === projectFilter);
    }
    if (statusFilter === 'active') list = list.filter(isActive);
    if (statusFilter === 'attention') {
      list = list.filter(
        (t) => t.status === 'FA' || t.stats?.success_level !== 'success',
      );
    }
    return list;
  }, [all, projectFilter, statusFilter]);

  const finished = all.filter((t) => t.status === 'F');
  const passed = finished.filter(
    (t) => t.stats?.success_level === 'success',
  ).length;
  const attention = all.filter(
    (t) =>
      t.status === 'FA' ||
      (t.status === 'F' && t.stats?.success_level !== 'success'),
  ).length;
  const running = all.filter((t) => t.status === 'R').length;
  const analyzing = all.filter((t) => t.status === 'A').length;
  const slots = (generators ?? []).reduce((a, g) => a + (g.jmeter ?? 0), 0);
  const capacity = (generators ?? []).filter((g) => g.active).length * 5;

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', lg: '1fr 340px' },
        gap: 2.5,
        alignItems: 'start',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2.5,
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr 1fr',
              md: 'repeat(4, 1fr)',
            },
            gap: 1.5,
          }}
        >
          <KpiTile
            label="Running now"
            value={running}
            unit={`+ ${analyzing} analyzing`}
          />
          <KpiTile
            label={`Pass rate · last ${finished.length || 0} tests`}
            value={
              finished.length
                ? `${Math.round((passed / finished.length) * 100)} %`
                : '—'
            }
            color="var(--s-accent)"
            unit={`${passed} of ${finished.length} passed`}
          />
          <KpiTile
            label="Needs attention"
            value={attention}
            color="var(--s-danger)"
            unit="failed or degraded"
          />
          <KpiTile
            label="Generator capacity"
            value={`${slots} / ${capacity}`}
            unit="JMeter slots in use"
          />
        </Box>

        <Panel
          title="Last tests"
          bodySx={{ p: 0 }}
          actions={
            <Box
              sx={{
                display: 'inline-flex',
                border: '1px solid var(--s-border2)',
                borderRadius: '6px',
                overflow: 'hidden',
              }}
            >
              {(
                [
                  ['all', 'All'],
                  ['active', 'Active'],
                  ['attention', 'Needs attention'],
                ] as [StatusFilter, string][]
              ).map(([key, label]) => (
                <Box
                  key={key}
                  component="button"
                  onClick={() => setStatusFilter(key)}
                  sx={{
                    height: 28,
                    px: 1.5,
                    border: 0,
                    borderRight: '1px solid var(--s-border)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 12,
                    fontWeight: 600,
                    background:
                      statusFilter === key
                        ? 'var(--s-accent-soft)'
                        : 'var(--s-card)',
                    color:
                      statusFilter === key
                        ? 'var(--s-accent-fg)'
                        : 'var(--s-text2)',
                  }}
                >
                  {label}
                </Box>
              ))}
            </Box>
          }
        >
          <Box
            sx={{
              display: 'flex',
              gap: 0.75,
              flexWrap: 'wrap',
              px: 2.25,
              py: 1.5,
              borderBottom: '1px solid var(--s-border)',
            }}
          >
            <FilterChip
              label="All projects"
              active={!projectFilter}
              onClick={() => setProjectFilter(0)}
            />
            {(projects ?? []).map((p) => (
              <FilterChip
                key={p.id}
                label={p.name}
                active={projectFilter === p.id}
                onClick={() => setProjectFilter(p.id)}
              />
            ))}
          </Box>
          {isLoading ? (
            <Typography sx={{ p: 2.25, color: 'var(--s-text3)' }}>
              Loading tests…
            </Typography>
          ) : (
            <LastTestsTable tests={rows} />
          )}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              px: 2.25,
              py: 1.25,
              borderTop: '1px solid var(--s-border)',
              fontSize: 12,
              color: 'var(--s-text3)',
            }}
          >
            <span>
              {rows.length} of {all.length} tests
            </span>
            <span>Auto-refresh every 10 s</span>
          </Box>
        </Panel>
      </Box>

      <Box component="aside" sx={{ minWidth: 0 }}>
        <ActiveTests tests={all.filter(isActive)} />
        <Generators generators={generators ?? []} />
      </Box>
    </Box>
  );
}
