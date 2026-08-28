import {
  Alert,
  Dialog,
  DialogContent,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

import { useActionDetails } from '../../api/hooks';

/**
 * Per-action statistics for the last 5 tests + error list.
 * Replaces the legacy popup window (`popitup`).
 */
export default function ActionDetailsDialog({
  testId,
  actionId,
  onClose,
}: {
  testId: number;
  actionId: number | null;
  onClose: () => void;
}) {
  const { data } = useActionDetails(
    actionId != null ? testId : null,
    actionId,
  );

  return (
    <Dialog open={actionId != null} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{data?.action.name ?? 'Action details'}</DialogTitle>
      <DialogContent>
        {data && (
          <Stack spacing={2}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Test</TableCell>
                  <TableCell align="right">min</TableCell>
                  <TableCell align="right">median</TableCell>
                  <TableCell align="right">mean</TableCell>
                  <TableCell align="right">max</TableCell>
                  <TableCell align="right">IQR</TableCell>
                  <TableCell align="right">std</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.action_data.map((row, i) => (
                  <TableRow key={i}>
                    <TableCell>{row.test_name || `#${i}`}</TableCell>
                    <TableCell align="right">{Math.round(row.min)}</TableCell>
                    <TableCell align="right">{Math.round(row.q2)}</TableCell>
                    <TableCell align="right">{Math.round(row.mean)}</TableCell>
                    <TableCell align="right">{Math.round(row.max)}</TableCell>
                    <TableCell align="right">{Math.round(row.IQR)}</TableCell>
                    <TableCell align="right">
                      {row.std == null ? '—' : Math.round(row.std)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Typography variant="subtitle2">Errors</Typography>
            {data.test_errors.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No errors for this action.
              </Typography>
            )}
            {data.test_errors.map((error, i) => (
              <Alert key={i} severity="error">
                <b>
                  {error.code} (×{error.count})
                </b>{' '}
                {error.text}
              </Alert>
            ))}
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
}
