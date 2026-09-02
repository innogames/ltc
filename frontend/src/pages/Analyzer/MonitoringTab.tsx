import { Box, CircularProgress, Typography } from '@mui/material';

import { useMonitoring } from '../../api/hooks';
import { MiniArea } from '../../components/charts';
import { displayLabel } from '../../theme';

function HostCard({
  host,
  la,
  cpu,
  mem,
}: {
  host: string;
  la: string;
  cpu: number[];
  mem: number[];
}) {
  const last = (values: number[]) =>
    values.length ? Math.round(values[values.length - 1]) : null;
  return (
    <Box
      sx={{
        border: '1px solid var(--s-border)',
        borderRadius: '8px',
        p: 2,
        minWidth: 0,
      }}
    >
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          mb: 1.25,
          gap: 1,
        }}
      >
        <Box
          sx={{
            ...displayLabel(12, '.08em'),
            color: 'var(--s-text)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={host}
        >
          {host}
        </Box>
        <Typography variant="body2" sx={{ color: 'var(--s-text3)' }}>
          load avg {la}
        </Typography>
      </Box>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 1.75,
        }}
      >
        <Box>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 12,
              color: 'var(--s-text3)',
            }}
          >
            <span>CPU</span>
            <Box component="b" sx={{ color: 'var(--s-text)' }}>
              {last(cpu) != null ? `${last(cpu)} %` : '—'}
            </Box>
          </Box>
          <MiniArea values={cpu} color="var(--s-accent)" />
        </Box>
        <Box>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 12,
              color: 'var(--s-text3)',
            }}
          >
            <span>Memory</span>
            <Box component="b" sx={{ color: 'var(--s-text)' }}>
              {last(mem) != null ? `${last(mem)} %` : '—'}
            </Box>
          </Box>
          {mem.length ? (
            <MiniArea values={mem} color="var(--s-teal)" />
          ) : (
            <Typography
              variant="body2"
              sx={{ color: 'var(--s-text3)', mt: 0.5, fontSize: 11.5 }}
            >
              not collected
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default function MonitoringTab({ testId }: { testId: number }) {
  const { data: hosts, isLoading } = useMonitoring(testId);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
        <CircularProgress size={18} />
        <Typography sx={{ color: 'var(--s-text3)' }}>
          Loading monitoring data…
        </Typography>
      </Box>
    );
  }

  if (!hosts?.length) {
    return (
      <Typography sx={{ color: 'var(--s-text3)' }}>
        No server monitoring data was collected for this test. Monitoring is
        recorded only when the test's servers report metrics during the run.
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
        gap: 2,
      }}
    >
      {hosts.map((h) => (
        <HostCard
          key={h.host}
          host={h.host}
          la={h.la}
          cpu={h.cpu ?? []}
          mem={h.mem ?? []}
        />
      ))}
    </Box>
  );
}
