export type NumericDomain = [number, number];

export type AlignedAxis = {
  domain: NumericDomain;
  ticks: number[];
};

type Extent = {
  positive: number;
  negative: number;
  integerOnly: boolean;
  /** False when the axis has no series to show — such an axis must not affect the other one. */
  active: boolean;
};

const SEGMENT_COUNTS = [4, 5, 6] as const;
const NICE_FRACTIONS = [1, 2, 2.5, 5, 10] as const;
const NICE_INTEGER_FRACTIONS = [1, 2, 5, 10] as const;

function getExtent<T extends object>(rows: T[], keys: readonly string[]): Extent {
  let positive = 0;
  let negative = 0;
  let integerOnly = true;
  let active = false;

  for (const row of rows) {
    const values = row as Record<string, unknown>;
    for (const key of keys) {
      const value = Number(values[key]);
      if (!Number.isFinite(value)) continue;
      active = true;
      if (!Number.isInteger(value)) integerOnly = false;
      if (value > positive) positive = value;
      if (value < 0) negative = Math.max(negative, Math.abs(value));
    }
  }

  if (!active) {
    return { positive: 0, negative: 0, integerOnly, active: false };
  }

  if (positive === 0 && negative === 0) {
    return { positive: 1, negative: 0, integerOnly, active: true };
  }

  return { positive, negative, integerOnly, active: true };
}

/** Rounds the step up to a readable value: 1, 2, 2.5, 5 or 10 × 10^n. */
function niceStep(rawStep: number, integerOnly: boolean): number {
  if (!Number.isFinite(rawStep) || rawStep <= 0) return 1;

  const fractions = integerOnly ? NICE_INTEGER_FRACTIONS : NICE_FRACTIONS;
  const exponent = Math.floor(Math.log10(rawStep));
  const magnitude = 10 ** (integerOnly ? Math.max(0, exponent) : exponent);
  const normalized = rawStep / magnitude;
  const fraction = fractions.find((candidate) => normalized <= candidate + 1e-9) ?? 10;

  return fraction * magnitude;
}

/** Strips floating point noise like 0.30000000000000004 from tick labels. */
function cleanNumber(value: number): number {
  return Number(value.toPrecision(12));
}

function buildAxis(extent: Extent, negativeSegments: number, positiveSegments: number): AlignedAxis | null {
  const { positive, negative, integerOnly } = extent;
  if (positive > 0 && positiveSegments === 0) return null;
  if (negative > 0 && negativeSegments === 0) return null;

  const step = niceStep(
    Math.max(
      positiveSegments > 0 ? positive / positiveSegments : 0,
      negativeSegments > 0 ? negative / negativeSegments : 0,
    ),
    integerOnly,
  );

  const min = cleanNumber(-negativeSegments * step);
  const max = cleanNumber(positiveSegments * step);
  const ticks: number[] = [];
  for (let index = 0; index <= negativeSegments + positiveSegments; index += 1) {
    ticks.push(cleanNumber(min + index * step));
  }

  return { domain: [min, max], ticks };
}

/** How much taller the axis is than the data it has to fit: 1 means a perfect fit. */
function getWaste(extent: Extent, axis: AlignedAxis): number {
  const needed = extent.positive + extent.negative;
  if (!extent.active || needed <= 0) return 0;
  return (axis.domain[1] - axis.domain[0]) / needed;
}

/**
 * Builds domains and ticks for two Y axes so that y=0 is rendered at the same
 * height on both of them while tick labels stay round. Both axes share the same
 * number of segments above and below zero, each with its own readable step.
 * Only the keys passed in are measured, so hiding a series rescales the chart.
 */
export function getAlignedChartDomains<T extends object>(
  rows: T[],
  leftKeys: readonly string[],
  rightKeys: readonly string[],
): { left: AlignedAxis; right: AlignedAxis } {
  const extents = [getExtent(rows, leftKeys), getExtent(rows, rightKeys)];
  const hasNegative = extents.some((extent) => extent.active && extent.negative > 0);
  const hasPositive = extents.some((extent) => extent.active && extent.positive > 0);

  let best: { axes: AlignedAxis[]; waste: number } | null = null;

  for (const totalSegments of SEGMENT_COUNTS) {
    const minNegative = hasNegative ? 1 : 0;
    const maxNegative = hasPositive ? totalSegments - 1 : totalSegments;

    for (let negativeSegments = minNegative; negativeSegments <= maxNegative; negativeSegments += 1) {
      const axes = extents.map((extent) => buildAxis(extent, negativeSegments, totalSegments - negativeSegments));
      if (axes.some((axis) => axis === null)) continue;

      const resolved = axes as AlignedAxis[];
      const waste = resolved.reduce((sum, axis, index) => sum + getWaste(extents[index], axis), 0);
      if (!best || waste < best.waste - 1e-9) {
        best = { axes: resolved, waste };
      }
    }
  }

  const [left, right] = best?.axes ?? [
    { domain: [0, 1] as NumericDomain, ticks: [0, 1] },
    { domain: [0, 1] as NumericDomain, ticks: [0, 1] },
  ];

  return { left, right };
}
