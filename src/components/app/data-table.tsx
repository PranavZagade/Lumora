"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatCompactNumber, formatFullNumber } from "@/lib/axis-formatter";

interface DataTableProps {
    data: Array<Record<string, unknown>>;
    columns?: string[];
    maxVisibleRows?: number;
    title?: string;
    className?: string;
}

/**
 * Compact fallback table for large datasets.
 * Used when chart rendering would be unreadable.
 * 
 * Features:
 * - Virtualized display (shows limited rows)
 * - Numeric highlighting
 * - Expand/collapse for more rows
 */
export function DataTable({
    data,
    columns,
    maxVisibleRows = 10,
    title,
    className,
}: DataTableProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    // Detect columns from first row if not provided
    const tableColumns = useMemo(() => {
        if (columns) return columns;
        if (data.length === 0) return [];
        return Object.keys(data[0]);
    }, [data, columns]);

    // Visible rows based on expansion state
    const visibleData = useMemo(() => {
        if (isExpanded) return data.slice(0, 100); // Cap at 100 even expanded
        return data.slice(0, maxVisibleRows);
    }, [data, isExpanded, maxVisibleRows]);

    const hasMore = data.length > maxVisibleRows;
    const showingCount = visibleData.length;
    const totalCount = data.length;

    if (data.length === 0) {
        return (
            <div className="text-sm text-muted-foreground text-center py-4">
                No data to display
            </div>
        );
    }

    return (
        <div className={cn("rounded-lg border border-border overflow-hidden", className)}>
            {/* Header */}
            {title && (
                <div className="px-3 py-2 bg-secondary/50 border-b border-border">
                    <span className="text-sm font-medium text-foreground">{title}</span>
                    <span className="text-xs text-muted-foreground ml-2">
                        ({totalCount} rows)
                    </span>
                </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="bg-secondary/30 border-b border-border">
                            {tableColumns.map((col) => (
                                <th
                                    key={col}
                                    className="px-3 py-2 text-left font-medium text-foreground whitespace-nowrap"
                                >
                                    {formatColumnHeader(col)}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {visibleData.map((row, rowIndex) => (
                            <tr
                                key={rowIndex}
                                className={cn(
                                    "border-b border-border/50 hover:bg-secondary/20 transition-colors",
                                    rowIndex % 2 === 0 ? "bg-background" : "bg-secondary/10"
                                )}
                            >
                                {tableColumns.map((col) => (
                                    <td
                                        key={col}
                                        className="px-3 py-2 whitespace-nowrap"
                                    >
                                        {formatCellValue(row[col])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Footer with expand/collapse */}
            {hasMore && (
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full px-3 py-2 flex items-center justify-center gap-1 text-xs text-muted-foreground hover:bg-secondary/30 transition-colors"
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp className="w-3 h-3" />
                            Show less
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-3 h-3" />
                            Show {Math.min(100, totalCount) - showingCount} more of {totalCount} rows
                        </>
                    )}
                </button>
            )}
        </div>
    );
}

/**
 * Format column header for display.
 */
function formatColumnHeader(column: string): string {
    return column
        .replace(/_/g, " ")
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .split(" ")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
}

/**
 * Format cell value with type-aware rendering.
 */
function formatCellValue(value: unknown): React.ReactNode {
    if (value === null || value === undefined) {
        return <span className="text-muted-foreground/50">–</span>;
    }

    if (typeof value === "number") {
        const isLargeNumber = Math.abs(value) >= 1000;
        return (
            <span
                className="font-mono text-primary"
                title={formatFullNumber(value)}
            >
                {isLargeNumber ? formatCompactNumber(value) : value.toLocaleString()}
            </span>
        );
    }

    if (typeof value === "boolean") {
        return (
            <span className={value ? "text-green-500" : "text-red-500"}>
                {value ? "Yes" : "No"}
            </span>
        );
    }

    return String(value);
}
