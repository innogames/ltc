import {
  Box,
  Card,
  CardContent,
  CardHeader,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';
import { LineChart } from '@mui/x-charts';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useState } from 'react';

import {
  DASHBOARD_POLL_MS,
  useOnlineData,
  useTests,
} from '../api/hooks';
import { CHART_COLORS } from '../theme';

interface AggregateRow {
  id: string;
  url: string;
  average: number;
  count: number;
  errors: number;
  maximum: number;
  minimum: number;
}

const AGGREGATE_COLUMNS: GridColDef<AggregateRow>[] = [
  { field: 'url', headerName: 'Action', flex: 2, minWidth: 260 },
  { field: 'average', headerName: 'Average', type: 'number', flex: 1 },
  { field: 'count', headerName: 'Count', type: 'number', flex: 1 },
  { field: 'errors', headerName: 'Errors', type: 'number', flex: 1 },
  { field: 'maximum', headerName: 'Max', type: 'number', flex: 1 },
  { field: 'minimum', headerName: 'Min', type: 'number', flex: 1 },
];

export default function OnlinePage() {
  const [testId, setTestId] = useState<number | null>(null);
  // The select refreshes with the dashboard cadence so newly started
  // tests appear without a reload.
  const { data: running } = useTests(
    { status: ['R'] },
    { refetchInterval: DASHBOARD_POLL_MS },
  );
  const { data: online } = useOnlineData(testId);

  const overTime =
    online?.online_data.find((d) => d.name === 'data_over_time')?.data ?? {};
  const points = Object.values(overTime).sort(
    (a, b) => Number(a.timestamp) - Number(b.timestamp),
  );

  const aggregate =
    online?.online_data.find((d) => d.name === 'aggregate_table')?.data ?? {};
  const aggregateRows: AggregateRow[] = Object.entries(aggregate).map(
    ([url, row]) => ({
      id: url,
      url,
      average: Number(row.average ?? row.response_time ?? 0),
      count: Number(row.count ?? 0),
      errors: Number(row.errors ?? 0),
      maximum: Number(row.maximum ?? 0),
      minimum: Number(row.minimum ?? 0),
    }),
  );

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <FormControl size="small" sx={{ minWidth: 320 }}>
            <InputLabel>Running test</InputLabel>
            <Select
              label="Running test"
              value={testId ?? ''}
              onChange={(e) => setTestId(Number(e.target.value))}
            >
              {(running?.results ?? []).map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name || `${t.project?.name} - ${t.id}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {!running?.results.length && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 1 }}
            >
              No running tests.
            </Typography>
          )}
        </CardContent>
      </Card>

      {online && (
        <>
          <Card sx={{ mb: 2 }}>
            <CardHeader
              title="Response times (live)"
              titleTypographyProps={{ variant: 'subtitle1' }}
            />
            <CardContent>
              {points.length === 0 ? (
                <Typography color="text.secondary">
                  Waiting for data…
                </Typography>
              ) : (
                <LineChart
                  height={380}
                  xAxis={[
                    {
                      data: points.map((p) => new Date(p.timestamp)),
                      scaleType: 'time',
                    },
                  ]}
                  yAxis={[{ id: 'ms' }, { id: 'persec' }]}
                  rightAxis="persec"
                  series={[
                    {
                      data: points.map((p) => Number(p.avg ?? 0)),
                      label: 'avg, ms',
                      yAxisId: 'ms',
                      color: CHART_COLORS.mean,
                      showMark: false,
                    },
                    {
                      data: points.map((p) => Number(p.errors ?? 0) / 60),
                      label: 'errors/s',
                      yAxisId: 'persec',
                      color: CHART_COLORS.failure,
                      showMark: false,
                    },
                    {
                      data: points.map((p) => Number(p.count ?? 0) / 60),
                      label: 'req/s',
                      yAxisId: 'persec',
                      color: CHART_COLORS.rps,
                      showMark: false,
                    },
                  ]}
                />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader
              title="Aggregate (live)"
              titleTypographyProps={{ variant: 'subtitle1' }}
            />
            <CardContent>
              <Box sx={{ height: 420 }}>
                <DataGrid
                  rows={aggregateRows}
                  columns={AGGREGATE_COLUMNS}
                  density="compact"
                  disableRowSelectionOnClick
                  initialState={{
                    sorting: {
                      sortModel: [{ field: 'average', sort: 'desc' }],
                    },
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
