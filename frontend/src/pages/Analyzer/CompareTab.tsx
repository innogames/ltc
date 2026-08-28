import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { BarChart } from '@mui/x-charts';
import { useState } from 'react';

import { useCompare } from '../../api/hooks';
import type { HighlightAction, TestReport } from '../../api/types';
import { CHART_COLORS } from '../../theme';

const HIGHLIGHT_TEXT: Record<HighlightAction['type'], string> = {
  new_actions: 'New action (absent in the other test)',
  absent_actions: 'Action absent in the current test',
  higher_response_times: 'Response times got significantly higher',
  lower_response_times: 'Response times got significantly lower',
  lower_count: 'Executed significantly fewer times',
};

function highlightName(h: HighlightAction) {
  return (
    h.action.current_test?.name ??
    h.action.other_test?.name ??
    h.action.name ??
    '?'
  );
}

function DiffCell({ a, b }: { a: number; b: number }) {
  const better = a <= b;
  return (
    <TableCell
      align="right"
      sx={{ color: better ? 'success.main' : 'error.main' }}
    >
      {Math.round(a)} / {Math.round(b)}
    </TableCell>
  );
}

export default function CompareTab({
  report,
  testId,
}: {
  report: TestReport;
  testId: number;
}) {
  // 0 = previous test of the same project (server default)
  const [otherId, setOtherId] = useState(0);
  const { data: compare } = useCompare(testId, otherId);

  const series = [...report.compare_data].reverse();

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Card variant="outlined">
          <CardHeader
            title="Mean / median vs previous tests"
            titleTypographyProps={{ variant: 'subtitle2' }}
          />
          <CardContent>
            <BarChart
              height={300}
              xAxis={[
                {
                  scaleType: 'band',
                  data: series.map((d) => d.test_name),
                  tickLabelStyle: { fontSize: 10, angle: -20 },
                },
              ]}
              series={[
                {
                  data: series.map((d) => d.mean),
                  label: 'mean, ms',
                  color: CHART_COLORS.mean,
                },
                {
                  data: series.map((d) => d.median),
                  label: 'median, ms',
                  color: CHART_COLORS.median,
                },
              ]}
            />
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12}>
        <FormControl size="small" sx={{ minWidth: 320 }}>
          <InputLabel>Compare against</InputLabel>
          <Select
            label="Compare against"
            value={otherId}
            onChange={(e) => setOtherId(Number(e.target.value))}
          >
            <MenuItem value={0}>Previous test</MenuItem>
            {report.compare_data
              .filter((d) => d.test_id !== testId)
              .map((d) => (
                <MenuItem key={d.test_id} value={d.test_id}>
                  {d.test_name}
                </MenuItem>
              ))}
          </Select>
        </FormControl>
      </Grid>
      {compare && (
        <>
          <Grid item xs={12} md={5}>
            <Stack spacing={1}>
              <Typography variant="subtitle2">Highlights</Typography>
              {(['critical', 'warning', 'success'] as const).map((severity) =>
                compare.highlights[severity].map((h, i) => (
                  <Alert
                    key={`${severity}-${i}`}
                    severity={severity === 'critical' ? 'error' : severity}
                  >
                    <b>{highlightName(h)}</b>: {HIGHLIGHT_TEXT[h.type]}
                  </Alert>
                )),
              )}
              {Object.values(compare.highlights).every(
                (list) => list.length === 0,
              ) && (
                <Typography variant="body2" color="text.secondary">
                  No significant differences found.
                </Typography>
              )}
            </Stack>
          </Grid>
          <Grid item xs={12} md={7}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Side-by-side (current / other)
            </Typography>
            <Box sx={{ maxHeight: 420, overflow: 'auto' }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Action</TableCell>
                    <TableCell align="right">mean</TableCell>
                    <TableCell align="right">50 %</TableCell>
                    <TableCell align="right">90 %</TableCell>
                    <TableCell align="right">count</TableCell>
                    <TableCell align="right">errors</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {compare.compare_table.map((row) => (
                    <TableRow key={row.name} hover>
                      <TableCell>{row.name}</TableCell>
                      <DiffCell a={row.mean_1} b={row.mean_2} />
                      <DiffCell a={row.p50_1} b={row.p50_2} />
                      <DiffCell a={row.p90_1} b={row.p90_2} />
                      <TableCell align="right">
                        {row.count_1} / {row.count_2}
                      </TableCell>
                      <TableCell align="right">
                        {row.errors_1} / {row.errors_2}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Grid>
        </>
      )}
    </Grid>
  );
}
