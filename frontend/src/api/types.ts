// Mirrors the DRF serializers in ltc/api/serializers.py and the contract
// documented by the design prototype's ltc-data.js. Optionally regenerate
// the raw OpenAPI types with `npm run generate-api` and reconcile here.

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
  /** Recent per-test means for this project, oldest → newest (sparkline). */
  spark: number[];
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

/**
 * Per-action aggregate row. Stat columns are DYNAMIC JSONB keys coming from
 * pandas `describe()` plus extras: mean, 50%, 75%, 90%, 99%, min, max,
 * count, errors, std, weight. The aggregate table derives its columns from
 * the keys of the first row, so never hardcode the list.
 */
export interface AggregateRow {
  action: string;
  action_id: number;
  errors_level: ErrorsLevel;
  mean: number;
  count: number;
  errors: number;
  [key: string]: string | number | null;
}

export interface TimeseriesPoint {
  timestamp: string;
  mean: number;
  median: number;
  count: number;
  /** Requests per second, derived server-side from count / resolution. */
  rps: number;
  errors: number;
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

export type HighlightType =
  | 'new_actions'
  | 'absent_actions'
  | 'higher_response_times'
  | 'lower_response_times'
  | 'lower_count';

/** Raw highlight as the API emits it (nested current/other action data). */
export interface HighlightAction {
  type: HighlightType;
  action: {
    name?: string;
    action_id?: number;
    current_test?: { name: string; data: Record<string, number> };
    other_test?: { name: string; data: Record<string, number> };
  };
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

/** Per-host monitoring series for the Analyzer's Monitoring tab. */
export interface MonitoringHost {
  host: string;
  cpu: number[];
  mem: number[];
  la: string;
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
  num_cpu: number | null;
  memory: number | null;
  memory_free: number | null;
  la_1: number | null;
  la_5: number | null;
  la_15: number | null;
  active: boolean;
  /** Number of jmeter-server processes currently running on this host. */
  jmeter: number;
  jmeter_servers: JmeterServer[];
}

export interface Me {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_staff: boolean;
}
