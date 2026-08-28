// Mirrors the DRF serializers in ltc/api/serializers.py.
// Optionally regenerate the raw OpenAPI types with `npm run generate-api`
// (requires the Django dev server on :8888) and reconcile changes here.

export type TestStatus = 'C' | 'R' | 'A' | 'S' | 'F' | 'FA';

export type SuccessLevel = 'success' | 'warning' | 'danger';
export type ErrorsLevel = 'ok' | 'warn' | 'crit';

export interface Project {
  id: number;
  name: string;
  enabled: boolean;
}

export interface TestStats {
  mean: number | null;
  count: number | null;
  errors: number | null;
  success_requests: number;
  success_level: SuccessLevel;
  prev_test_id: number | null;
  prev_test_mean: number | null;
  mean_diff_percent: number | null;
}

export interface Test {
  id: number;
  name: string;
  project: Project | null;
  status: TestStatus;
  threads: number;
  duration: number;
  started_at: string | null;
  finished_at: string | null;
  stats: TestStats | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Per-action aggregate row; stat columns are dynamic JSON keys
// (mean, 50%, 90%, max, min, count, errors, std, weight, ...).
export interface AggregateRow {
  action: string;
  action_id: number;
  errors_level: ErrorsLevel;
  [key: string]: string | number | null;
}

export interface TimeseriesPoint {
  timestamp: string;
  mean: number;
  median: number;
  count: number;
  [key: string]: string | number;
}

export interface CompareDataPoint {
  test_id: number;
  test_name: string;
  mean: number;
  median: number;
  cpu_load: unknown;
}

export interface TestReport {
  test_id: number;
  name: string;
  test_action_aggregate_data: AggregateRow[];
  test_data: TimeseriesPoint[];
  server_monitoring_data: Record<string, Record<string, unknown>[]>;
  compare_data: CompareDataPoint[];
  slow_action_threshold_ms: number;
}

export interface HighlightAction {
  action: {
    current_test?: { name: string; data: Record<string, number> };
    other_test?: { name: string; data: Record<string, number> };
    name?: string;
    action_id?: number;
  };
  type:
    | 'new_actions'
    | 'absent_actions'
    | 'higher_response_times'
    | 'lower_response_times'
    | 'lower_count';
}

export interface CompareTableRow {
  name: string;
  mean_1: number;
  mean_2: number;
  p50_1: number;
  p50_2: number;
  p90_1: number;
  p90_2: number;
  count_1: number;
  count_2: number;
  max_1: number;
  max_2: number;
  min_1: number;
  min_2: number;
  errors_1: number;
  errors_2: number;
}

export interface CompareResult {
  tests: Test[];
  highlights: {
    critical: HighlightAction[];
    warning: HighlightAction[];
    success: HighlightAction[];
  };
  compare_table: CompareTableRow[];
}

export interface ActionBoxplot {
  q1: number;
  q2: number;
  q3: number;
  IQR: number;
  LW: number;
  UW: number;
  mean: number;
  min: number;
  max: number;
  std: number | null;
  test_name: string;
}

export interface ActionDetails {
  test_id: number;
  action: { id: number; name: string };
  action_data: ActionBoxplot[];
  test_started_at: string | null;
  test_errors: { text: string; code: string; count: number }[];
}

export interface OnlineData {
  id: number;
  name: 'response_codes' | 'aggregate_table' | 'data_over_time';
  data: Record<string, Record<string, number>>;
}

export interface TestOnline {
  id: number;
  name: string;
  project: Project | null;
  status: TestStatus;
  duration: number;
  started_at: string | null;
  online_data: OnlineData[];
}

export interface JmeterServer {
  id: number;
  test: number;
  pid: number;
  port: number;
  jmeter_path: string;
  threads: number;
}

export interface LoadGenerator {
  id: number;
  hostname: string;
  num_cpu: string;
  memory: string;
  memory_free: string;
  la_1: string;
  la_5: string;
  la_15: string;
  active: boolean;
  jmeter_servers: JmeterServer[];
}

export interface Me {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_staff: boolean;
}
