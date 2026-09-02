import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import { api } from './client';
import type {
  ActionDetails,
  CompareResult,
  LoadGenerator,
  Me,
  MonitoringHost,
  Paginated,
  Project,
  Test,
  TestOnline,
  TestReport,
} from './types';

export const DASHBOARD_POLL_MS = 10_000;
export const ONLINE_POLL_MS = 5_000;

export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => (await api.get<Me>('/users/me/')).data,
    staleTime: Infinity,
  });
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects/')).data,
  });
}

export interface TestQuery {
  project?: number;
  status?: string[];
  /** Hide never-started tests (they carry no metrics). */
  started?: boolean;
  projectEnabled?: boolean;
  pageSize?: number;
}

export function useTests(
  params: TestQuery,
  options: { refetchInterval?: number } = {},
) {
  return useQuery({
    queryKey: ['tests', params],
    queryFn: async () => {
      const search = new URLSearchParams();
      if (params.project) search.set('project', String(params.project));
      for (const s of params.status ?? []) search.append('status', s);
      if (params.started) search.set('started', 'true');
      if (params.projectEnabled) search.set('project_enabled', 'true');
      if (params.pageSize) search.set('page_size', String(params.pageSize));
      const { data } = await api.get<Paginated<Test>>(
        `/tests/?${search.toString()}`,
      );
      return data;
    },
    ...options,
  });
}

export function useTestReport(testId: number | null) {
  return useQuery({
    queryKey: ['test-report', testId],
    queryFn: async () =>
      (await api.get<TestReport>(`/tests/${testId}/report/`)).data,
    enabled: testId != null,
  });
}

export function useCompare(testId: number | null, otherId: number) {
  return useQuery({
    queryKey: ['test-compare', testId, otherId],
    queryFn: async () =>
      (await api.get<CompareResult>(`/tests/${testId}/compare/${otherId}/`))
        .data,
    enabled: testId != null,
  });
}

export function useActionDetails(
  testId: number | null,
  actionId: number | null,
) {
  return useQuery({
    queryKey: ['action-details', testId, actionId],
    queryFn: async () =>
      (
        await api.get<ActionDetails>(
          `/tests/${testId}/actions/${actionId}/`,
        )
      ).data,
    enabled: testId != null && actionId != null,
  });
}

export function useMonitoring(testId: number | null) {
  return useQuery({
    queryKey: ['test-monitoring', testId],
    queryFn: async () =>
      (await api.get<MonitoringHost[]>(`/tests/${testId}/monitoring/`)).data,
    enabled: testId != null,
  });
}

export function useOnlineData(testId: number | null) {
  return useQuery({
    queryKey: ['test-online', testId],
    queryFn: async () =>
      (await api.get<TestOnline>(`/tests/${testId}/online/`)).data,
    enabled: testId != null,
    refetchInterval: ONLINE_POLL_MS,
  });
}

export function useLoadGenerators(options: { refetchInterval?: number } = {}) {
  return useQuery({
    queryKey: ['loadgenerators'],
    queryFn: async () =>
      (await api.get<LoadGenerator[]>('/loadgenerators/')).data,
    ...options,
  });
}

/** Terminates a running test (Online page). */
export function useStopTest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (testId: number) =>
      (await api.post<Test>(`/tests/${testId}/stop/`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tests'] });
      queryClient.invalidateQueries({ queryKey: ['test-online'] });
    },
  });
}

/** Publishes the test report to Confluence (Analyzer page). */
export function usePublishReport() {
  return useMutation({
    mutationFn: async (testId: number) =>
      (
        await api.post<{ url?: string; detail?: string }>(
          `/tests/${testId}/publish/`,
        )
      ).data,
  });
}
