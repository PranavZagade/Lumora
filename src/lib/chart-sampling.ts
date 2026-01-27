/**
 * Chart Sampling Utilities
 * 
 * Min/max envelope sampling for large datasets.
 * Preserves extrema (spikes) while reducing visual density.
 * 
 * CORE PRINCIPLE: No data transformation - display-only resolution reduction.
 */

export interface DataPoint {
    [key: string]: unknown;
}

/**
 * Min/max envelope sampling for time series data.
 * 
 * For each bucket, preserves both the minimum and maximum values,
 * ensuring spikes and dips are never lost.
 * 
 * @param data - Array of data points
 * @param maxPoints - Maximum number of points to return (~500 for charts)
 * @param valueKey - Key of the numeric value to sample
 * @returns Downsampled array preserving extrema
 */
export function minMaxSample<T extends DataPoint>(
    data: T[],
    maxPoints: number,
    valueKey: string
): T[] {
    if (!data || data.length === 0) return [];
    if (data.length <= maxPoints) return data;

    const bucketSize = Math.ceil(data.length / (maxPoints / 2)); // Divide by 2 since we keep min+max
    const result: T[] = [];

    for (let i = 0; i < data.length; i += bucketSize) {
        const bucket = data.slice(i, Math.min(i + bucketSize, data.length));

        if (bucket.length === 0) continue;
        if (bucket.length === 1) {
            result.push(bucket[0]);
            continue;
        }

        // Find min and max in bucket
        let minPoint = bucket[0];
        let maxPoint = bucket[0];
        let minVal = Number(bucket[0][valueKey]) || 0;
        let maxVal = Number(bucket[0][valueKey]) || 0;

        for (const point of bucket) {
            const val = Number(point[valueKey]) || 0;
            if (val < minVal) {
                minVal = val;
                minPoint = point;
            }
            if (val > maxVal) {
                maxVal = val;
                maxPoint = point;
            }
        }

        // Add min and max in order (preserve time ordering if applicable)
        const minIndex = bucket.indexOf(minPoint);
        const maxIndex = bucket.indexOf(maxPoint);

        if (minIndex <= maxIndex) {
            result.push(minPoint);
            if (minPoint !== maxPoint) result.push(maxPoint);
        } else {
            result.push(maxPoint);
            if (minPoint !== maxPoint) result.push(minPoint);
        }
    }

    return result;
}

/**
 * Simple downsampling that takes every Nth point.
 * Use when order matters but min/max preservation is not critical.
 * 
 * @param data - Array of data points
 * @param maxPoints - Maximum number of points to return
 * @returns Evenly sampled array
 */
export function evenSample<T>(data: T[], maxPoints: number): T[] {
    if (!data || data.length === 0) return [];
    if (data.length <= maxPoints) return data;

    const step = Math.ceil(data.length / maxPoints);
    const result: T[] = [];

    for (let i = 0; i < data.length; i += step) {
        result.push(data[i]);
    }

    // Always include the last point
    if (result[result.length - 1] !== data[data.length - 1]) {
        result.push(data[data.length - 1]);
    }

    return result;
}

/**
 * Calculate tick positions for an axis.
 * Returns approximately 8-12 evenly spaced values.
 * 
 * @param data - Array of numeric values
 * @param maxTicks - Maximum number of ticks (default 10)
 * @returns Array of tick values
 */
export function calculateTicks(data: number[], maxTicks: number = 10): number[] {
    if (!data || data.length === 0) return [];

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;

    if (range === 0) return [min];

    // Calculate nice step size
    const roughStep = range / maxTicks;
    const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
    const normalized = roughStep / magnitude;

    let niceStep: number;
    if (normalized <= 1) niceStep = magnitude;
    else if (normalized <= 2) niceStep = 2 * magnitude;
    else if (normalized <= 5) niceStep = 5 * magnitude;
    else niceStep = 10 * magnitude;

    const ticks: number[] = [];
    const start = Math.floor(min / niceStep) * niceStep;

    for (let tick = start; tick <= max; tick += niceStep) {
        if (tick >= min) {
            ticks.push(tick);
        }
        if (ticks.length >= maxTicks) break;
    }

    return ticks;
}

/**
 * Check if data exceeds chart rendering limits.
 * 
 * @param dataLength - Number of data points
 * @param categoryCount - Number of unique categories (for bar charts)
 * @returns Object indicating if fallback is needed
 */
export function checkRenderingLimits(
    dataLength: number,
    categoryCount?: number
): { needsFallback: boolean; reason?: string } {
    const MAX_CHART_POINTS = 500;
    const MAX_CATEGORIES = 12;

    if (dataLength > MAX_CHART_POINTS * 2) {
        // Even after min/max sampling, would exceed limits
        return {
            needsFallback: true,
            reason: `Too many data points (${dataLength}) for chart rendering`
        };
    }

    if (categoryCount && categoryCount > MAX_CATEGORIES) {
        return {
            needsFallback: true,
            reason: `Too many categories (${categoryCount}) for readable chart`
        };
    }

    return { needsFallback: false };
}
