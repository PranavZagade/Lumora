/**
 * Axis Formatter Utilities
 * 
 * Adaptive number and date formatting for chart axes.
 * Ensures readable labels without overlap.
 * 
 * CORE PRINCIPLE: Display formatting only - never transform data values.
 */

/**
 * Format a number with K/M/B suffixes for readability.
 * 
 * @param value - Number to format
 * @param decimals - Number of decimal places (default 1)
 * @returns Formatted string (e.g., "1.2K", "3.4M")
 */
export function formatCompactNumber(value: number, decimals: number = 1): string {
    if (value === null || value === undefined || isNaN(value)) return "0";

    const absValue = Math.abs(value);
    const sign = value < 0 ? "-" : "";

    if (absValue >= 1_000_000_000) {
        return sign + (absValue / 1_000_000_000).toFixed(decimals) + "B";
    }
    if (absValue >= 1_000_000) {
        return sign + (absValue / 1_000_000).toFixed(decimals) + "M";
    }
    if (absValue >= 1_000) {
        return sign + (absValue / 1_000).toFixed(decimals) + "K";
    }
    if (absValue >= 1) {
        return sign + absValue.toFixed(absValue % 1 === 0 ? 0 : decimals);
    }
    if (absValue > 0) {
        return sign + absValue.toFixed(decimals);
    }
    return "0";
}

/**
 * Format a number for display with locale-aware separators.
 * 
 * @param value - Number to format
 * @returns Formatted string with commas (e.g., "1,234,567")
 */
export function formatFullNumber(value: number): string {
    if (value === null || value === undefined || isNaN(value)) return "0";
    return value.toLocaleString();
}

/**
 * Format a date value for axis labels.
 * Adapts format based on time range.
 * 
 * @param value - Date string or number (year)
 * @param format - Format hint: "year", "month", "day", "auto"
 * @returns Formatted date string
 */
export function formatDateLabel(
    value: string | number,
    format: "year" | "month" | "day" | "auto" = "auto"
): string {
    // If it's just a year number
    if (typeof value === "number" || /^\d{4}$/.test(String(value))) {
        return String(value);
    }

    // Try to parse as date
    const str = String(value);

    // ISO date format
    if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
        const date = new Date(str);
        if (!isNaN(date.getTime())) {
            if (format === "year" || format === "auto") {
                return date.getFullYear().toString();
            }
            if (format === "month") {
                const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                return `${months[date.getMonth()]} '${String(date.getFullYear()).slice(2)}`;
            }
            if (format === "day") {
                const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                return `${months[date.getMonth()]} ${date.getDate()}`;
            }
        }
    }

    // Return as-is if can't parse
    return str;
}

/**
 * Calculate optimal tick interval for labels.
 * Prevents overlapping labels by skipping values.
 * 
 * @param dataLength - Number of data points
 * @param maxTicks - Maximum visible ticks (default 10)
 * @returns Interval (show every Nth label)
 */
export function calculateTickInterval(dataLength: number, maxTicks: number = 10): number {
    if (dataLength <= maxTicks) return 0; // Show all
    return Math.ceil(dataLength / maxTicks) - 1;
}

/**
 * Truncate a label string with ellipsis.
 * 
 * @param label - String to truncate
 * @param maxLength - Maximum characters (default 12)
 * @returns Truncated string
 */
export function truncateLabel(label: string, maxLength: number = 12): string {
    if (!label) return "";
    const str = String(label);
    if (str.length <= maxLength) return str;
    return str.slice(0, maxLength - 1) + "…";
}

/**
 * Check if labels would overlap at a given density.
 * 
 * @param labelCount - Number of labels
 * @param avgLabelWidth - Average width per label in pixels
 * @param availableWidth - Available axis width in pixels
 * @returns True if labels would overlap
 */
export function wouldLabelsOverlap(
    labelCount: number,
    avgLabelWidth: number = 50,
    availableWidth: number = 600
): boolean {
    const totalWidth = labelCount * avgLabelWidth;
    return totalWidth > availableWidth;
}
