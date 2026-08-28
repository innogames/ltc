import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import { Box, Typography } from '@mui/material';

/**
 * "123 ms (↑ 5.2 %)" — response-time value with the delta vs the
 * previous test. Up (slower) is red, down (faster) is green.
 */
export default function StatDelta({
  value,
  diffPercent,
}: {
  value: number | null;
  diffPercent: number | null;
}) {
  if (value == null) return <Typography variant="body2">—</Typography>;
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <Typography variant="body2">{Math.round(value)} ms</Typography>
      {diffPercent != null && diffPercent !== 0 && (
        <>
          {diffPercent > 0 ? (
            <ArrowUpwardIcon color="error" sx={{ fontSize: 14 }} />
          ) : (
            <ArrowDownwardIcon color="success" sx={{ fontSize: 14 }} />
          )}
          <Typography variant="caption" color="text.secondary">
            {Math.abs(diffPercent).toFixed(1)} %
          </Typography>
        </>
      )}
    </Box>
  );
}
