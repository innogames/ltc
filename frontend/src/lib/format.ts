/** Formatting helpers ported from the LTC design prototype. */

/** 3600 → "1 h", 90 → "2 min", 45 → "45 s" */
export function fmtDur(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  if (seconds >= 3600) {
    const h = seconds / 3600;
    return `${h.toFixed(seconds % 3600 ? 1 : 0)} h`;
  }
  if (seconds >= 60) return `${Math.round(seconds / 60)} min`;
  return `${Math.round(seconds)} s`;
}

/** ISO timestamp → "12 min ago" / "3 h ago" / "2 d ago" */
export function relTime(iso: string | null): string {
  if (!iso) return '—';
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (!Number.isFinite(minutes)) return '—';
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 1440) return `${Math.round(minutes / 60)} h ago`;
  return `${Math.round(minutes / 1440)} d ago`;
}

export function num(value: number | null | undefined, digits = 0): string {
  if (value == null || !Number.isFinite(value)) return '—';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function signedPercent(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)} %`;
}

/** Name a test the way every screen does. */
export function testLabel(test: {
  name?: string | null;
  id: number;
  project?: { name: string } | null;
}): string {
  return test.name || `${test.project?.name ?? '?'} - ${test.id}`;
}

/** CSV escape + download, used by the aggregate table's Export CSV. */
export function downloadCsv(filename: string, rows: (string | number)[][]) {
  const body = rows
    .map((row) =>
      row
        .map((cell) => {
          const text = cell == null ? '' : String(cell);
          return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
        })
        .join(','),
    )
    .join('\n');
  const url = URL.createObjectURL(
    new Blob([body], { type: 'text/csv;charset=utf-8' }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
