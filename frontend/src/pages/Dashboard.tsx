import {
  Badge,
  Box,
  Card,
  CardContent,
  CardHeader,
  Grid,
  LinearProgress,
  Link as MuiLink,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Link } from 'react-router-dom';

import {
  DASHBOARD_POLL_MS,
  useLoadGenerators,
  useTests,
} from '../api/hooks';
import type { Test } from '../api/types';
import SeverityChip from '../components/SeverityChip';
import StatDelta from '../components/StatDelta';
import { successColor } from '../theme';

const STATUS_LABEL: Record<string, string> = {
  C: 'Created',
  R: 'Running',
  A: 'Analyzing',
  S: 'Scheduled',
  F: 'Finished',
  FA: 'Failed',
};

function testName(test: Test) {
  return test.name || `${test.project?.name ?? '?'} - ${test.id}`;
}

function LastTestsTable({ tests }: { tests: Test[] }) {
  if (!tests.length) return <Typography>No data</Typography>;
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Project</TableCell>
          <TableCell>Test name</TableCell>
          <TableCell align="right">Virtual users</TableCell>
          <TableCell align="right">Duration</TableCell>
          <TableCell align="right">Success requests</TableCell>
          <TableCell>Mean response times</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Result</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {tests.map((test) => (
          <TableRow key={test.id} hover>
            <TableCell>{test.project?.name}</TableCell>
            <TableCell>
              {test.status === 'F' ? (
                <MuiLink component={Link} to={`/analyzer?test=${test.id}`}>
                  <b>{testName(test)}</b>
                </MuiLink>
              ) : (
                <b>{testName(test)}</b>
              )}
            </TableCell>
            <TableCell align="right">{test.threads}</TableCell>
            <TableCell align="right">{test.duration}</TableCell>
            <TableCell align="right">
              {test.stats && (
                <Typography
                  variant="body2"
                  color={`${successColor(test.stats.success_level)}.main`}
                  fontWeight={700}
                >
                  {test.stats.success_requests.toFixed(1)} %
                </Typography>
              )}
            </TableCell>
            <TableCell>
              <StatDelta
                value={test.stats?.mean ?? null}
                diffPercent={test.stats?.mean_diff_percent ?? null}
              />
            </TableCell>
            <TableCell>
              <Typography
                variant="body2"
                color={test.status === 'F' ? 'success.main' : undefined}
                fontWeight={700}
              >
                {STATUS_LABEL[test.status] ?? test.status}
              </Typography>
            </TableCell>
            <TableCell>
              {test.stats && <SeverityChip level={test.stats.success_level} />}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ActiveTests() {
  const { data } = useTests(
    { status: ['R', 'A'] },
    { refetchInterval: DASHBOARD_POLL_MS },
  );
  const active = data?.results ?? [];
  return (
    <Card>
      <CardHeader title="Active tests" titleTypographyProps={{ variant: 'subtitle1' }} />
      <CardContent sx={{ pt: 0 }}>
        {active.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No running tests
          </Typography>
        ) : (
          active.map((test) => {
            const started = test.started_at
              ? new Date(test.started_at).getTime()
              : Date.now();
            const progress = test.duration
              ? Math.min(
                  ((Date.now() - started) / 1000 / test.duration) * 100,
                  100,
                )
              : 0;
            return (
              <Box key={test.id} sx={{ mb: 1.5 }}>
                <Typography variant="body2">
                  {test.project?.name} — #{test.id} (
                  {STATUS_LABEL[test.status]})
                </Typography>
                <LinearProgress variant="determinate" value={progress} />
              </Box>
            );
          })
        )}
      </CardContent>
    </Card>
  );
}

function LoadGenerators() {
  const { data: generators } = useLoadGenerators({
    refetchInterval: DASHBOARD_POLL_MS,
  });
  return (
    <Card sx={{ mt: 2 }}>
      <CardHeader
        title="Load generators"
        titleTypographyProps={{ variant: 'subtitle1' }}
      />
      <CardContent sx={{ pt: 0 }}>
        {!generators?.length ? (
          <Typography variant="body2" color="text.secondary">
            No load generators
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Host</TableCell>
                <TableCell align="right">Free mem</TableCell>
                <TableCell align="right">la_1/5/15</TableCell>
                <TableCell align="right">JMeter</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {generators.map((generator) => {
                const instances = generator.jmeter_servers.length;
                const badgeColor =
                  instances >= 5
                    ? 'error'
                    : instances >= 3
                      ? 'warning'
                      : 'success';
                return (
                  <TableRow key={generator.id} hover>
                    <TableCell>{generator.hostname}</TableCell>
                    <TableCell align="right">{generator.memory_free}</TableCell>
                    <TableCell align="right">
                      {generator.la_1}/{generator.la_5}/{generator.la_15}
                    </TableCell>
                    <TableCell align="right">
                      <Badge
                        badgeContent={instances}
                        color={badgeColor}
                        showZero
                        sx={{ mr: 1 }}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: lastTests } = useTests({}, {});
  return (
    <Grid container spacing={2}>
      <Grid item xs={12} lg={9}>
        <Card>
          <CardHeader
            title="Last tests"
            titleTypographyProps={{ variant: 'subtitle1' }}
          />
          <CardContent sx={{ pt: 0 }}>
            <LastTestsTable tests={lastTests?.results ?? []} />
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} lg={3}>
        <ActiveTests />
        <LoadGenerators />
      </Grid>
    </Grid>
  );
}
