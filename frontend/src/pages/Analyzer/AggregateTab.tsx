import { Box, Link as MuiLink } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useMemo, useState } from 'react';

import type { AggregateRow, TestReport } from '../../api/types';
import ActionDetailsDialog from './ActionDetailsDialog';

const META_KEYS = new Set(['action', 'action_id', 'errors_level']);

const ERRORS_SX = {
  '& .errors-warn': { color: 'warning.main', fontWeight: 700 },
  '& .errors-crit': { color: 'error.main', fontWeight: 700 },
};

export default function AggregateTab({ report }: { report: TestReport }) {
  const [openAction, setOpenAction] = useState<number | null>(null);
  const rows = report.test_action_aggregate_data;

  const columns = useMemo<GridColDef<AggregateRow>[]>(() => {
    if (!rows.length) return [];
    // Stat columns are dynamic: derived from the JSON keys of the first row.
    const statKeys = Object.keys(rows[0]).filter((k) => !META_KEYS.has(k));
    return [
      {
        field: 'action',
        headerName: 'Action',
        flex: 2,
        minWidth: 260,
        renderCell: (params) => (
          <MuiLink
            component="button"
            onClick={() => setOpenAction(params.row.action_id)}
          >
            {params.row.action}
          </MuiLink>
        ),
      },
      ...statKeys.map(
        (key): GridColDef<AggregateRow> => ({
          field: key,
          headerName: key,
          type: 'number',
          flex: 1,
          minWidth: 90,
          valueGetter: (value) =>
            typeof value === 'number' ? Math.round(value * 10) / 10 : value,
          cellClassName:
            key === 'errors'
              ? (params) =>
                  params.row.errors_level === 'ok'
                    ? ''
                    : `errors-${params.row.errors_level}`
              : undefined,
        }),
      ),
    ];
  }, [rows]);

  return (
    <Box sx={{ height: 560, ...ERRORS_SX }}>
      <DataGrid
        rows={rows}
        columns={columns}
        getRowId={(row) => row.action_id}
        density="compact"
        disableRowSelectionOnClick
        initialState={{
          sorting: { sortModel: [{ field: 'mean', sort: 'desc' }] },
        }}
      />
      <ActionDetailsDialog
        testId={report.test_id}
        actionId={openAction}
        onClose={() => setOpenAction(null)}
      />
    </Box>
  );
}
