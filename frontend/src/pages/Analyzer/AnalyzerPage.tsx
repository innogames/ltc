import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import {
  Alert,
  Badge,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  Snackbar,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import {
  useCompare,
  useProjects,
  usePublishReport,
  useTestReport,
  useTests,
} from '../../api/hooks';
import { Panel, Pill } from '../../components/Card';
import ActionDetailsDrawer from '../../components/ActionDetailsDrawer';
import { fmtDur, num, relTime, testLabel } from '../../lib/format';
import { displayLabel, successChip } from '../../theme';
import AggregateTab from './AggregateTab';
import CompareTab from './CompareTab';
import MonitoringTab from './MonitoringTab';
import OverviewTab from './OverviewTab';
import ResponseTimesTab from './ResponseTimesTab';

const TAB_LABELS = [
  'Overview',
  'Compare tests',
  'Aggregate table',
  'Response times',
  'Monitoring',
];

function ContextStat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Box>
      <Box sx={{ ...displayLabel(10.5, '.1em'), color: 'var(--s-text3)' }}>
        {label}
      </Box>
      <Box sx={{ color: 'var(--s-text)', fontWeight: 600, mt: '2px' }}>
        {value}
      </Box>
    </Box>
  );
}

export default function AnalyzerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState(0);
  const [compareId, setCompareId] = useState(0);
  const [openAction, setOpenAction] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const testId = searchParams.get('test')
    ? Number(searchParams.get('test'))
    : null;
  const projectParam = searchParams.get('project')
    ? Number(searchParams.get('project'))
    : null;

  const { data: projects } = useProjects();
  const { data: allTests } = useTests({ started: true, pageSize: 200 });

  const selected = allTests?.results.find((t) => t.id === testId) ?? null;
  const projectId = projectParam ?? selected?.project?.id ?? null;

  const projectTests = (allTests?.results ?? []).filter(
    (t) => t.project?.id === projectId,
  );

  const { data: report, isLoading, isError } = useTestReport(testId);
  const { data: compare } = useCompare(tab === 1 ? testId : null, compareId);
  const publish = usePublishReport();

  const chip = successChip(selected?.stats?.success_level);
  const prevTestId = selected?.stats?.prev_test_id ?? null;

  const selectTest = (id: number) => {
    setCompareId(0);
    setSearchParams(
      projectId
        ? { project: String(projectId), test: String(id) }
        : { test: String(id) },
    );
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      <Panel dense>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2.5,
            flexWrap: 'wrap',
          }}
        >
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel shrink>Project</InputLabel>
            <Select
              native
              value={projectId ?? ''}
              onChange={(e) => {
                const pid = Number(e.target.value);
                const first = (allTests?.results ?? []).find(
                  (t) => t.project?.id === pid,
                );
                setCompareId(0);
                setSearchParams({
                  project: String(pid),
                  ...(first ? { test: String(first.id) } : {}),
                });
              }}
            >
              <option value="" disabled>
                Select project
              </option>
              {(projects ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 280 }}>
            <InputLabel shrink>Test</InputLabel>
            <Select
              native
              value={testId ?? ''}
              onChange={(e) => selectTest(Number(e.target.value))}
            >
              <option value="" disabled>
                Select test
              </option>
              {projectTests.map((t) => (
                <option key={t.id} value={t.id}>
                  {`${testLabel(t)} · ${relTime(t.started_at)}`}
                </option>
              ))}
            </Select>
          </FormControl>

          <Box
            sx={{ width: '1px', height: 40, background: 'var(--s-border)' }}
          />

          <Box sx={{ display: 'flex', gap: 3.5, fontSize: 13 }}>
            <ContextStat
              label="Started"
              value={relTime(selected?.started_at ?? null)}
            />
            <ContextStat label="VUs" value={num(selected?.threads ?? null)} />
            <ContextStat
              label="Duration"
              value={fmtDur(selected?.duration ?? 0)}
            />
            <ContextStat
              label="Result"
              value={
                selected?.status === 'FA' ? (
                  <Pill
                    label="Aborted"
                    bg="var(--s-danger-soft)"
                    fg="var(--s-danger)"
                  />
                ) : (
                  <Pill label={chip.label} bg={chip.bg} fg={chip.fg} />
                )
              }
            />
          </Box>

          <Box sx={{ flex: 1 }} />

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<ChevronLeftIcon />}
              disabled={!prevTestId}
              onClick={() => prevTestId && selectTest(prevTestId)}
              sx={{ fontFamily: 'inherit', fontSize: 13, fontWeight: 600 }}
            >
              Previous run
            </Button>
            <Button
              variant="contained"
              disabled={!testId || publish.isPending}
              onClick={() =>
                testId &&
                publish.mutate(testId, {
                  onSuccess: (data) =>
                    setToast(
                      data.url
                        ? `Published: ${data.url}`
                        : 'Report published to Confluence',
                    ),
                  onError: (error: unknown) => {
                    const detail =
                      (error as { response?: { data?: { detail?: string } } })
                        ?.response?.data?.detail ??
                      'Publishing failed';
                    setToast(detail);
                  },
                })
              }
            >
              {publish.isPending ? 'Publishing…' : 'Publish to Confluence'}
            </Button>
          </Box>
        </Box>
      </Panel>

      {testId == null && (
        <Typography sx={{ color: 'var(--s-text3)' }}>
          Select a project and a test to build the report.
        </Typography>
      )}

      {isError && testId != null && (
        <Alert severity="error">
          Could not load the report for test {testId}.
        </Alert>
      )}

      {isLoading && testId != null && (
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', p: 2 }}>
          <CircularProgress size={18} />
          <Typography sx={{ color: 'var(--s-text3)' }}>
            Loading report…
          </Typography>
        </Box>
      )}

      {report && (
        <Panel bodySx={{ p: 2.5 }} dense>
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              borderBottom: '1px solid var(--s-border)',
              mx: -2.25,
              px: 1.5,
              mt: -1.75,
              mb: 2.5,
            }}
          >
            {TAB_LABELS.map((label, i) => (
              <Tab
                key={label}
                label={
                  i === 1 && compare?.highlights.critical.length ? (
                    <Badge
                      badgeContent={compare.highlights.critical.length}
                      color="error"
                      sx={{ '& .MuiBadge-badge': { right: -14, top: 2 } }}
                    >
                      {label}
                    </Badge>
                  ) : (
                    label
                  )
                }
              />
            ))}
          </Tabs>

          {tab === 0 && (
            <OverviewTab
              report={report}
              test={selected}
              onOpenAction={setOpenAction}
            />
          )}
          {tab === 1 && (
            <CompareTab
              report={report}
              testId={report.test_id}
              compareId={compareId}
              onCompareChange={setCompareId}
              onSelectTest={selectTest}
            />
          )}
          {tab === 2 && (
            <AggregateTab report={report} onOpenAction={setOpenAction} />
          )}
          {tab === 3 && (
            <ResponseTimesTab report={report} test={selected} />
          )}
          {tab === 4 && <MonitoringTab testId={report.test_id} />}
        </Panel>
      )}

      <ActionDetailsDrawer
        testId={testId}
        actionId={openAction}
        onClose={() => setOpenAction(null)}
      />

      <Snackbar
        open={!!toast}
        autoHideDuration={6000}
        onClose={() => setToast(null)}
        message={toast}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Box>
  );
}
