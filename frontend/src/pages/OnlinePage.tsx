import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useMemo, useState } from 'react';

import {
  DASHBOARD_POLL_MS,
  useOnlineData,
  useStopTest,
  useTests,
} from '../api/hooks';
import { KpiTile, Panel } from '../components/Card';
import { TimeseriesChart } from '../components/charts';
import { fmtDur, num, testLabel } from '../lib/format';

interface LiveRow {
  action: string;
  average: number;
  count: number;
  errors: number;
  maximum: number;
  minimum: number;
}

function roundUp(value: number, step: number) {
  return Math.max(step, Math.ceil(value / step) * step);
}

export default function OnlinePage() {
  const [testId, setTestId] = useState<number | null>(null);
  const [confirmStop, setConfirmStop] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const { data: running } = useTests(
    { status: ['R', 'A'] },
    { refetchInterval: DASHBOARD_POLL_MS },
  );
  const runningTests = running?.results ?? [];
  const selectedId = testId ?? runningTests[0]?.id ?? null;
  const selected = runningTests.find((t) => t.id === selectedId) ?? null;

  const { data: online } = useOnlineData(selectedId);
  const stopTest = useStopTest();

  const series = useMemo(() => {
    const overTime =
      online?.online_data.find((d) => d.name === 'data_over_time')?.data ?? {};
    // JSONB is keyed by timestamp; sort by the key so the line is in order.
    return Object.entries(overTime)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([, row]) => ({
        mean: Number(row.avg ?? row.average ?? 0),
        rps: Number(row.count ?? 0) / 60,
        errors: Number(row.errors ?? 0) / 60,
      }));
  }, [online]);

  const rows: LiveRow[] = useMemo(() => {
    const table =
      online?.online_data.find((d) => d.name === 'aggregate_table')?.data ?? {};
    return Object.entries(table)
      .map(([action, row]) => ({
        action,
        average: Number(row.average ?? 0),
        count: Number(row.count ?? 0),
        errors: Number(row.errors ?? 0),
        maximum: Number(row.maximum ?? 0),
        minimum: Number(row.minimum ?? 0),
      }))
      .sort((a, b) => b.average - a.average);
  }, [online]);

  const last = series[series.length - 1];
  const totals = rows.reduce(
    (acc, r) => ({
      count: acc.count + r.count,
      errors: acc.errors + r.errors,
    }),
    { count: 0, errors: 0 },
  );

  const started = selected?.started_at
    ? new Date(selected.started_at).getTime()
    : null;
  const elapsed = started ? (Date.now() - started) / 1000 : 0;
  const pct = selected?.duration
    ? Math.min(100, (elapsed / selected.duration) * 100)
    : 0;

  const leftMax = series.length
    ? roundUp(Math.max(...series.map((p) => p.mean)), 100)
    : 100;
  const rightMax = series.length
    ? roundUp(Math.max(...series.map((p) => Math.max(p.rps, p.errors))), 10)
    : 10;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      <Panel dense>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 3,
            flexWrap: 'wrap',
          }}
        >
          <FormControl size="small" sx={{ minWidth: 300 }}>
            <InputLabel shrink>Running test</InputLabel>
            <Select
              native
              value={selectedId ?? ''}
              onChange={(e) => setTestId(Number(e.target.value))}
            >
              <option value="" disabled>
                {runningTests.length ? 'Select test' : 'No running tests'}
              </option>
              {runningTests.map((t) => (
                <option key={t.id} value={t.id}>
                  {testLabel(t)}
                </option>
              ))}
            </Select>
          </FormControl>

          {selected && (
            <>
              <Box sx={{ flex: 1, minWidth: 280 }}>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 12,
                    color: 'var(--s-text3)',
                    mb: 0.75,
                  }}
                >
                  <span>
                    Elapsed{' '}
                    <Box component="b" sx={{ color: 'var(--s-text)' }}>
                      {fmtDur(elapsed)}
                    </Box>{' '}
                    of {fmtDur(selected.duration)} · {num(selected.threads)} VUs
                  </span>
                  <Box
                    component="span"
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 0.75,
                    }}
                  >
                    <Box
                      component="span"
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: 99,
                        background: 'var(--s-accent)',
                        animation: 'ltc-pulse 1.6s ease-in-out infinite',
                      }}
                    />
                    live · 5 s
                  </Box>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={pct}
                  sx={{ height: 8 }}
                />
              </Box>

              <Button
                variant="outlined"
                color="error"
                onClick={() => setConfirmStop(true)}
                sx={{ borderWidth: 2 }}
              >
                Stop test
              </Button>
            </>
          )}
        </Box>
      </Panel>

      {!runningTests.length && (
        <Alert severity="info">
          No tests are running right now. This page updates automatically when
          one starts.
        </Alert>
      )}

      {selected && (
        <>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: {
                xs: '1fr 1fr',
                md: 'repeat(5, 1fr)',
              },
              gap: 1.5,
            }}
          >
            <KpiTile
              size={26}
              label="Avg response"
              value={last ? Math.round(last.mean) : '—'}
              unit="ms"
              color={
                last && last.mean > 200 ? 'var(--s-warn)' : 'var(--s-text)'
              }
            />
            <KpiTile
              size={26}
              label="Throughput"
              value={last ? Math.round(last.rps) : '—'}
              unit="req/s"
            />
            <KpiTile
              size={26}
              label="Errors / s"
              value={last ? last.errors.toFixed(2) : '—'}
              color={
                last && last.errors > 0.5
                  ? 'var(--s-danger)'
                  : 'var(--s-text)'
              }
            />
            <KpiTile
              size={26}
              label="Requests total"
              value={num(totals.count)}
            />
            <KpiTile
              size={26}
              label="Errors total"
              value={num(totals.errors)}
              color={totals.errors ? 'var(--s-danger)' : 'var(--s-text)'}
            />
          </Box>

          <Panel title="Response times · live">
            {!series.length ? (
              <Typography sx={{ color: 'var(--s-text3)' }}>
                Waiting for the first results to be parsed…
              </Typography>
            ) : (
              <TimeseriesChart
                height={240}
                leftMax={leftMax}
                rightMax={rightMax}
                series={[
                  {
                    values: series.map((p) => p.errors),
                    color: 'var(--s-danger)',
                    area: true,
                    right: true,
                  },
                  {
                    values: series.map((p) => p.rps),
                    color: 'var(--s-gold)',
                    width: 1.5,
                    right: true,
                  },
                  {
                    values: series.map((p) => p.mean),
                    color: 'var(--s-accent)',
                    width: 2.2,
                  },
                ]}
              />
            )}
          </Panel>

          <Panel title="Aggregate · live" bodySx={{ p: 0 }}>
            {!rows.length ? (
              <Typography sx={{ color: 'var(--s-text3)', p: 2.25 }}>
                No aggregated actions yet.
              </Typography>
            ) : (
              <Box sx={{ overflowX: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Action</TableCell>
                      <TableCell align="right">Average</TableCell>
                      <TableCell align="right">Count</TableCell>
                      <TableCell align="right">Errors</TableCell>
                      <TableCell align="right">Max</TableCell>
                      <TableCell align="right">Min</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((row) => (
                      <TableRow key={row.action} hover>
                        <TableCell
                          sx={{
                            fontFamily: 'ui-monospace, Menlo, monospace',
                            fontSize: 12,
                          }}
                        >
                          {row.action}
                        </TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>
                          {num(row.average, 1)}
                        </TableCell>
                        <TableCell align="right" sx={{ color: 'var(--s-text2)' }}>
                          {num(row.count)}
                        </TableCell>
                        <TableCell
                          align="right"
                          sx={{
                            fontWeight: 700,
                            color: row.errors
                              ? 'var(--s-danger)'
                              : 'var(--s-text2)',
                          }}
                        >
                          {num(row.errors)}
                        </TableCell>
                        <TableCell align="right" sx={{ color: 'var(--s-text2)' }}>
                          {num(row.maximum)}
                        </TableCell>
                        <TableCell align="right" sx={{ color: 'var(--s-text2)' }}>
                          {num(row.minimum)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
          </Panel>
        </>
      )}

      <Dialog open={confirmStop} onClose={() => setConfirmStop(false)}>
        <DialogTitle>Stop this test?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {selected ? testLabel(selected) : ''} will be terminated: the
            JMeter master and every remote jmeter-server for this run are
            killed. This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button variant="outlined" onClick={() => setConfirmStop(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            disabled={stopTest.isPending}
            onClick={() => {
              if (!selectedId) return;
              stopTest.mutate(selectedId, {
                onSuccess: () => {
                  setToast('Test terminated');
                  setConfirmStop(false);
                },
                onError: (error: unknown) => {
                  const detail =
                    (error as { response?: { data?: { detail?: string } } })
                      ?.response?.data?.detail ?? 'Could not stop the test';
                  setToast(detail);
                  setConfirmStop(false);
                },
              });
            }}
          >
            {stopTest.isPending ? 'Stopping…' : 'Stop test'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={!!toast}
        autoHideDuration={6000}
        onClose={() => setToast(null)}
        message={toast}
      />
    </Box>
  );
}
