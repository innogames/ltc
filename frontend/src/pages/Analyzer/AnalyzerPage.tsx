import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useProjects, useTestReport, useTests } from '../../api/hooks';
import AggregateTab from './AggregateTab';
import CompareTab from './CompareTab';
import OverviewTab from './OverviewTab';
import ResponseTimesTab from './ResponseTimesTab';

const TABS = [
  'Overview',
  'Compare tests',
  'Aggregate table',
  'Response times',
  'Monitoring',
];

export default function AnalyzerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState(0);

  const projectId = searchParams.get('project')
    ? Number(searchParams.get('project'))
    : null;
  const testId = searchParams.get('test')
    ? Number(searchParams.get('test'))
    : null;

  const { data: projects } = useProjects();
  const { data: tests } = useTests(
    projectId ? { project: projectId } : {},
    {},
  );
  const { data: report, isLoading } = useTestReport(testId);

  const selectedTest = tests?.results.find((t) => t.id === testId);
  const effectiveProject = projectId ?? selectedTest?.project?.id ?? '';

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 240 }}>
            <InputLabel>Project</InputLabel>
            <Select
              label="Project"
              value={effectiveProject}
              onChange={(e) =>
                setSearchParams({ project: String(e.target.value) })
              }
            >
              {(projects ?? []).map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 320 }}>
            <InputLabel>Test</InputLabel>
            <Select
              label="Test"
              value={testId ?? ''}
              onChange={(e) =>
                setSearchParams({
                  ...(effectiveProject
                    ? { project: String(effectiveProject) }
                    : {}),
                  test: String(e.target.value),
                })
              }
            >
              {(tests?.results ?? []).map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name || `${t.project?.name} - ${t.id}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </CardContent>
      </Card>

      {testId == null && (
        <Typography color="text.secondary">
          Select a project and a test to build the report.
        </Typography>
      )}
      {isLoading && testId != null && (
        <Typography color="text.secondary">Loading report…</Typography>
      )}
      {report && (
        <Card>
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            {TABS.map((label) => (
              <Tab key={label} label={label} />
            ))}
          </Tabs>
          <CardContent>
            {tab === 0 && <OverviewTab report={report} />}
            {tab === 1 && <CompareTab report={report} testId={report.test_id} />}
            {tab === 2 && <AggregateTab report={report} />}
            {tab === 3 && <ResponseTimesTab report={report} />}
            {tab === 4 && (
              <Typography color="text.secondary">
                Server monitoring graphs are not implemented (the legacy page
                was empty as well).
              </Typography>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
