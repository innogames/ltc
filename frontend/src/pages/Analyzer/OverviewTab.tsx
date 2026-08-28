import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Grid,
  Link as MuiLink,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { BarChart, PieChart } from '@mui/x-charts';
import { useState } from 'react';

import type { TestReport } from '../../api/types';
import { CHART_COLORS } from '../../theme';
import ActionDetailsDialog from './ActionDetailsDialog';

const TOP_ACTIONS = 15;

export default function OverviewTab({ report }: { report: TestReport }) {
  const [openAction, setOpenAction] = useState<number | null>(null);
  const rows = report.test_action_aggregate_data;

  const totalCount = rows.reduce((acc, r) => acc + Number(r.count ?? 0), 0);
  const totalErrors = rows.reduce((acc, r) => acc + Number(r.errors ?? 0), 0);
  const successPercent = totalCount
    ? ((totalCount - totalErrors) * 100) / totalCount
    : 0;

  const failed = rows
    .filter((r) => Number(r.errors ?? 0) > 0)
    .sort((a, b) => Number(b.errors) - Number(a.errors))
    .slice(0, TOP_ACTIONS);

  const slowest = [...rows]
    .sort((a, b) => Number(b.mean) - Number(a.mean))
    .slice(0, TOP_ACTIONS);

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={4}>
        <Card variant="outlined">
          <CardHeader
            title="Success rate"
            titleTypographyProps={{ variant: 'subtitle2' }}
          />
          <CardContent>
            <PieChart
              height={260}
              series={[
                {
                  innerRadius: 60,
                  data: [
                    {
                      id: 0,
                      value: Number(successPercent.toFixed(2)),
                      label: 'Success %',
                      color: CHART_COLORS.success,
                    },
                    {
                      id: 1,
                      value: Number((100 - successPercent).toFixed(2)),
                      label: 'Failed %',
                      color: CHART_COLORS.failure,
                    },
                  ],
                },
              ]}
            />
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={3}>
        <Card variant="outlined">
          <CardHeader
            title="Top failed actions"
            titleTypographyProps={{ variant: 'subtitle2' }}
          />
          <CardContent sx={{ maxHeight: 300, overflow: 'auto', pt: 0 }}>
            <List dense>
              {failed.length === 0 && (
                <ListItem>
                  <ListItemText secondary="No failed actions" />
                </ListItem>
              )}
              {failed.map((row) => (
                <ListItem
                  key={row.action_id}
                  secondaryAction={
                    <Chip
                      size="small"
                      color="error"
                      label={Number(row.errors)}
                    />
                  }
                >
                  <ListItemText
                    primary={
                      <MuiLink
                        component="button"
                        onClick={() => setOpenAction(row.action_id)}
                      >
                        {row.action}
                      </MuiLink>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} md={5}>
        <Card variant="outlined">
          <CardHeader
            title={`Slowest actions (highlight > ${report.slow_action_threshold_ms} ms)`}
            titleTypographyProps={{ variant: 'subtitle2' }}
          />
          <CardContent>
            <Box sx={{ overflowX: 'auto' }}>
              <BarChart
                height={300}
                layout="horizontal"
                yAxis={[
                  {
                    scaleType: 'band',
                    data: slowest.map((r) => r.action),
                    tickLabelStyle: { fontSize: 10 },
                  },
                ]}
                series={[
                  {
                    data: slowest.map((r) => Number(r.mean)),
                    label: 'mean, ms',
                    color: CHART_COLORS.mean,
                  },
                ]}
                margin={{ left: 180 }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>
      <ActionDetailsDialog
        testId={report.test_id}
        actionId={openAction}
        onClose={() => setOpenAction(null)}
      />
    </Grid>
  );
}
