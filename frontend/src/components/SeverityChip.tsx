import { Chip } from '@mui/material';

import type { SuccessLevel } from '../api/types';
import { successColor } from '../theme';

export default function SeverityChip({ level }: { level: SuccessLevel }) {
  return (
    <Chip
      label={level}
      color={successColor(level)}
      size="small"
      sx={{ textTransform: 'capitalize' }}
    />
  );
}
