import { Box } from '@mui/material';

import { FONT_BODY } from '../theme';

/**
 * Inline-SVG chart primitives, ported from the design prototype's own
 * drawing code (its `line()` / `area()` helpers). These are used where the
 * prototype's hand-tuned rendering *is* the design: sparklines, the
 * success donut, dual-axis timeseries with a threshold line and error band,
 * and per-run boxplots.
 */

/** SVG path through `values`, mapped into the given box. */
export function linePath(
  values: number[],
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  min: number,
  max: number,
): string {
  const n = values.length;
  if (!n) return '';
  if (n === 1) {
    const y = y1 - (y1 - y0) * ((values[0] - min) / (max - min || 1));
    return `M${x0},${y.toFixed(1)}L${x1},${y.toFixed(1)}`;
  }
  return values
    .map((v, i) => {
      const x = x0 + ((x1 - x0) * i) / (n - 1);
      const y = y1 - (y1 - y0) * ((v - min) / (max - min || 1));
      return `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join('');
}

/** Same as linePath but closed along the baseline (filled band). */
export function areaPath(
  values: number[],
  x0: number,
  x1: number,
  y0: number,
  y1: number,
  min: number,
  max: number,
): string {
  const line = linePath(values, x0, x1, y0, y1, min, max);
  if (!line) return '';
  return `${line}L${x1},${y1}L${x0},${y1}Z`;
}

export function Sparkline({
  values,
  color = 'var(--s-accent)',
  width = 90,
  height = 26,
}: {
  values: number[];
  color?: string;
  width?: number;
  height?: number;
}) {
  if (!values?.length) {
    return <Box sx={{ width, height }} />;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ display: 'block' }}
      aria-hidden
    >
      <path
        d={linePath(values, 2, width - 2, 3, height - 3, min, max)}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** Success/failure donut with the percentage in the middle. */
export function SuccessDonut({
  successPercent,
  size = 140,
}: {
  successPercent: number;
  size?: number;
}) {
  const r = 54;
  const circumference = 2 * Math.PI * r;
  const filled = (circumference * Math.max(0, Math.min(100, successPercent))) / 100;
  return (
    <Box sx={{ position: 'relative', width: size, height: size, flex: 'none' }}>
      <svg width={size} height={size} viewBox="0 0 140 140">
        <circle
          cx={70}
          cy={70}
          r={r}
          fill="none"
          stroke="var(--s-danger)"
          strokeWidth={16}
        />
        <circle
          cx={70}
          cy={70}
          r={r}
          fill="none"
          stroke="var(--s-accent)"
          strokeWidth={16}
          strokeDasharray={`${filled.toFixed(1)} ${circumference.toFixed(1)}`}
          transform="rotate(-90 70 70)"
        />
      </svg>
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: 1,
        }}
      >
        <Box
          component="span"
          sx={{
            fontFamily: "'SF Theramin Gothic', 'Arial Black', sans-serif",
            fontWeight: 700,
            fontSize: 22,
            color: 'var(--s-text)',
          }}
        >
          {successPercent.toFixed(1)}%
        </Box>
        <Box
          component="span"
          sx={{ fontSize: 11, color: 'var(--s-text3)', mt: 0.5 }}
        >
          success
        </Box>
      </Box>
    </Box>
  );
}

export interface Series {
  values: number[];
  color: string;
  width?: number;
  /** Draw as a filled band instead of a line (errors). */
  area?: boolean;
  /** Map onto the right-hand axis instead of the left. */
  right?: boolean;
  visible?: boolean;
}

/**
 * Dual-axis timeseries: left axis in ms, right axis for req/s and errors,
 * with an optional dashed threshold line and highlighted error window.
 */
export function TimeseriesChart({
  series,
  leftMax,
  rightMax,
  thresholdMs,
  xLabels = [],
  height = 260,
}: {
  series: Series[];
  leftMax: number;
  rightMax: number;
  thresholdMs?: number;
  xLabels?: string[];
  height?: number;
}) {
  const W = 802;
  const Y0 = 20;
  const Y1 = height;
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const thresholdY =
    thresholdMs != null && leftMax > 0
      ? Y1 - (Y1 - Y0) * (thresholdMs / leftMax)
      : null;

  const axisLabel = {
    position: 'absolute' as const,
    fontSize: 11,
    color: 'var(--s-text3)',
    fontFamily: FONT_BODY,
    transform: 'translateY(-50%)',
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '46px 1fr 52px',
        columnGap: '6px',
      }}
    >
      <Box sx={{ position: 'relative', mb: '24px' }}>
        {ticks.map((f) => (
          <Box
            key={f}
            component="span"
            sx={{
              ...axisLabel,
              right: 0,
              top: `${((Y1 - (Y1 - Y0) * f) / Y1) * 100}%`,
            }}
          >
            {Math.round(leftMax * f).toLocaleString()}
          </Box>
        ))}
      </Box>

      <Box sx={{ position: 'relative' }}>
        <svg
          viewBox={`0 0 ${W} ${Y1}`}
          width="100%"
          style={{ display: 'block', overflow: 'visible' }}
          preserveAspectRatio="none"
        >
          {ticks.map((f) => {
            const y = Y1 - (Y1 - Y0) * f;
            return (
              <line
                key={f}
                x1={0}
                x2={W}
                y1={y}
                y2={y}
                stroke="var(--s-grid)"
                strokeWidth={1}
              />
            );
          })}
          {thresholdY != null && (
            <line
              x1={0}
              x2={W}
              y1={thresholdY}
              y2={thresholdY}
              stroke="var(--s-warn)"
              strokeDasharray="4 4"
            />
          )}
          {series.map((s, i) =>
            s.visible === false || !s.values.length ? null : s.area ? (
              <path
                key={i}
                d={areaPath(
                  s.values,
                  0,
                  W,
                  Y1 - 80,
                  Y1,
                  0,
                  s.right ? rightMax : leftMax,
                )}
                fill={s.color}
                opacity={0.35}
              />
            ) : (
              <path
                key={i}
                d={linePath(
                  s.values,
                  0,
                  W,
                  Y0,
                  Y1,
                  0,
                  s.right ? rightMax : leftMax,
                )}
                fill="none"
                stroke={s.color}
                strokeWidth={s.width ?? 2}
                vectorEffect="non-scaling-stroke"
              />
            ),
          )}
        </svg>
        {thresholdY != null && (
          <Box
            component="span"
            sx={{
              position: 'absolute',
              left: 4,
              top: `${(thresholdY / Y1) * 100}%`,
              transform: 'translateY(-100%)',
              fontSize: 10,
              color: 'var(--s-warn)',
              pb: '2px',
            }}
          >
            threshold {thresholdMs} ms
          </Box>
        )}
        <Box sx={{ position: 'relative', height: 20, mt: '4px' }}>
          {xLabels.map((label, i) => (
            <Box
              key={i}
              component="span"
              sx={{
                position: 'absolute',
                left: `${(i / Math.max(1, xLabels.length - 1)) * 100}%`,
                transform: 'translateX(-50%)',
                fontSize: 11,
                color: 'var(--s-text3)',
                whiteSpace: 'nowrap',
              }}
            >
              {label}
            </Box>
          ))}
        </Box>
      </Box>

      <Box sx={{ position: 'relative', mb: '24px' }}>
        {ticks.map((f) => (
          <Box
            key={f}
            component="span"
            sx={{
              ...axisLabel,
              left: 0,
              top: `${((Y1 - (Y1 - Y0) * f) / Y1) * 100}%`,
            }}
          >
            {Math.round(rightMax * f).toLocaleString()}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

/** Small CPU/memory area chart used on the Monitoring tab. */
export function MiniArea({
  values,
  color,
  max = 100,
}: {
  values: number[];
  color: string;
  max?: number;
}) {
  if (!values.length) return null;
  return (
    <svg
      viewBox="0 0 300 70"
      width="100%"
      style={{ display: 'block', marginTop: 4 }}
    >
      <path
        d={areaPath(values, 0, 300, 4, 68, 0, max)}
        fill={color}
        opacity={0.15}
      />
      <path
        d={linePath(values, 0, 300, 4, 68, 0, max)}
        fill="none"
        stroke={color}
        strokeWidth={1.6}
      />
    </svg>
  );
}
