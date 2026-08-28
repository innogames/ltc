import { Typography } from '@mui/material';
import { LineChart } from '@mui/x-charts';

import type { TestReport } from '../../api/types';
import { CHART_COLORS } from '../../theme';

export default function ResponseTimesTab({ report }: { report: TestReport }) {
  const points = report.test_data;
  if (!points.length) {
    return <Typography color="text.secondary">No timeseries data.</Typography>;
  }
  const timestamps = points.map((p) => new Date(p.timestamp));
  return (
    <LineChart
      height={420}
      xAxis={[
        {
          data: timestamps,
          scaleType: 'time',
        },
      ]}
      yAxis={[{ id: 'ms' }, { id: 'rps' }]}
      rightAxis="rps"
      series={[
        {
          data: points.map((p) => p.mean),
          label: 'mean, ms',
          yAxisId: 'ms',
          color: CHART_COLORS.mean,
          showMark: false,
        },
        {
          data: points.map((p) => p.median),
          label: 'median, ms',
          yAxisId: 'ms',
          color: CHART_COLORS.median,
          showMark: false,
        },
        {
          data: points.map((p) => Number(p.count) / 60),
          label: 'req/s',
          yAxisId: 'rps',
          color: CHART_COLORS.rps,
          showMark: false,
        },
      ]}
    />
  );
}
