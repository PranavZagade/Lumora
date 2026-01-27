"use client";

import { useMemo, useState } from "react";
import {
    LineChart,
    Line,
    BarChart,
    Bar,
    AreaChart,
    Area,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
} from "recharts";
import { minMaxSample, checkRenderingLimits } from "@/lib/chart-sampling";
import { formatCompactNumber, formatFullNumber, truncateLabel } from "@/lib/axis-formatter";

// Chart specification interface from backend
export interface ChartSpec {
    chart_type: "line" | "area" | "bar" | "horizontal_bar" | "donut" | "histogram";
    intent: string;
    title: string;
    x_axis: {
        field: string;
        label: string;
        type: "time" | "numeric" | "categorical";
    };
    y_axis: {
        field: string;
        label: string;
        type: "time" | "numeric" | "categorical";
    };
    data: Array<Record<string, unknown>>;
    ui_hints: {
        max_ticks: number;
        tick_interval: number;
        label_rotation: number;
        truncate_labels: boolean;
        max_label_length: number;
        show_legend: boolean;
        show_grid: boolean;
        animate: boolean;
    };
    fallback_reason?: string;
}

// Rendering limits
const MAX_CHART_POINTS = 500;
const MAX_AXIS_TICKS = 10;


// Design system colors
const CHART_COLORS = {
    primary: "hsl(217, 91%, 54%)",      // Blue
    secondary: "hsl(262, 83%, 58%)",    // Purple
    accent: "hsl(0, 84%, 60%)",         // Red
    muted: "hsl(215, 16%, 47%)",
    grid: "hsl(214, 32%, 91%)",
};

// Donut/Pie chart color palette
const PIE_COLORS = [
    "hsl(217, 91%, 54%)",   // Blue
    "hsl(262, 83%, 58%)",   // Purple
    "hsl(0, 84%, 60%)",     // Red
    "hsl(38, 92%, 50%)",    // Amber
    "hsl(142, 76%, 36%)",   // Green
    "hsl(280, 65%, 60%)",   // Violet
    "hsl(190, 90%, 50%)",   // Cyan
    "hsl(25, 95%, 53%)",    // Orange
];

interface ChartRendererProps {
    spec: ChartSpec;
    height?: number;
    onFallbackNeeded?: (reason: string) => void;
}

// Custom tooltip showing EXACT values (not sampled)
function CustomTooltip({
    active,
    payload,
    label,
}: {
    active?: boolean;
    payload?: Array<{ value: number; name: string; payload?: Record<string, unknown> }>;
    label?: string;
}) {
    if (!active || !payload || payload.length === 0) return null;

    return (
        <div className="bg-background/95 backdrop-blur border border-border rounded-lg px-3 py-2 shadow-lg">
            <p className="text-sm font-medium text-foreground">{label}</p>
            {payload.map((entry, index) => (
                <p key={index} className="text-sm text-muted-foreground">
                    {entry.name}:{" "}
                    <span className="font-medium text-foreground" title={formatFullNumber(entry.value)}>
                        {formatCompactNumber(entry.value)}
                    </span>
                </p>
            ))}
        </div>
    );
}

export function ChartRenderer({ spec, height = 300, onFallbackNeeded }: ChartRendererProps) {
    const { chart_type, x_axis, y_axis, data, ui_hints } = spec;
    const [_, setIsSampled] = useState(false);

    // Check rendering limits and apply sampling if needed
    const { processedData } = useMemo(() => {
        if (!data || data.length === 0) return { processedData: [], sampledCount: 0 };

        // Check if table fallback needed
        const limits = checkRenderingLimits(data.length);
        if (limits.needsFallback && onFallbackNeeded) {
            onFallbackNeeded(limits.reason || "Data exceeds rendering limits");
        }

        // Apply min/max sampling for line/area charts with large datasets
        let workingData = data;
        let sampled = 0;

        if ((chart_type === "line" || chart_type === "area") && data.length > MAX_CHART_POINTS) {
            workingData = minMaxSample(data, MAX_CHART_POINTS, y_axis.field);
            sampled = data.length - workingData.length;
            setIsSampled(true);
        }

        // Process labels
        const result = workingData.map((item) => {
            const processed = { ...item };

            // Truncate x-axis labels if needed
            if (ui_hints.truncate_labels && x_axis.field) {
                const originalValue = item[x_axis.field];
                if (typeof originalValue === "string") {
                    processed[`${x_axis.field}_display`] = truncateLabel(
                        originalValue,
                        ui_hints.max_label_length
                    );
                }
            }

            return processed;
        });

        return { processedData: result, sampledCount: sampled };
    }, [data, ui_hints, x_axis.field, y_axis.field, chart_type, onFallbackNeeded]);

    // Calculate tick interval for X axis (adaptive)
    const tickInterval = useMemo(() => {
        const effectiveLength = processedData.length;
        if (effectiveLength <= MAX_AXIS_TICKS) return 0;
        return Math.ceil(effectiveLength / MAX_AXIS_TICKS) - 1;
    }, [processedData.length]);

    // Common axis props
    const xAxisProps = {
        dataKey: ui_hints.truncate_labels ? `${x_axis.field}_display` : x_axis.field,
        tick: { fontSize: 11, fill: CHART_COLORS.muted },
        tickLine: false,
        axisLine: { stroke: CHART_COLORS.grid },
        angle: ui_hints.label_rotation,
        textAnchor: ui_hints.label_rotation ? ("end" as const) : ("middle" as const),
        height: ui_hints.label_rotation ? 60 : 30,
        interval: tickInterval > 0 ? tickInterval - 1 : 0,
    };

    const yAxisProps = {
        dataKey: y_axis.field,
        tick: { fontSize: 11, fill: CHART_COLORS.muted },
        tickLine: false,
        axisLine: { stroke: CHART_COLORS.grid },
        tickFormatter: (value: number) => formatCompactNumber(value),
        width: 60,
    };

    // Render based on chart type
    if (chart_type === "line") {
        return (
            <ResponsiveContainer width="100%" height={height}>
                <LineChart data={processedData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                    {ui_hints.show_grid && (
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    )}
                    <XAxis {...xAxisProps} />
                    <YAxis {...yAxisProps} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line
                        type="monotone"
                        dataKey={y_axis.field}
                        stroke={CHART_COLORS.primary}
                        strokeWidth={2}
                        dot={{ fill: CHART_COLORS.primary, strokeWidth: 0, r: 3 }}
                        activeDot={{ r: 5, fill: CHART_COLORS.primary }}
                        animationDuration={ui_hints.animate ? 500 : 0}
                    />
                </LineChart>
            </ResponsiveContainer>
        );
    }

    if (chart_type === "area") {
        return (
            <ResponsiveContainer width="100%" height={height}>
                <AreaChart data={processedData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                    {ui_hints.show_grid && (
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    )}
                    <XAxis {...xAxisProps} />
                    <YAxis {...yAxisProps} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                        type="monotone"
                        dataKey={y_axis.field}
                        stroke={CHART_COLORS.primary}
                        fill={`${CHART_COLORS.primary}20`}
                        strokeWidth={2}
                        animationDuration={ui_hints.animate ? 500 : 0}
                    />
                </AreaChart>
            </ResponsiveContainer>
        );
    }

    if (chart_type === "bar") {
        return (
            <ResponsiveContainer width="100%" height={height}>
                <BarChart data={processedData} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                    {ui_hints.show_grid && (
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                    )}
                    <XAxis {...xAxisProps} />
                    <YAxis {...yAxisProps} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                        dataKey={y_axis.field}
                        fill={CHART_COLORS.primary}
                        radius={[4, 4, 0, 0]}
                        animationDuration={ui_hints.animate ? 500 : 0}
                    />
                </BarChart>
            </ResponsiveContainer>
        );
    }

    if (chart_type === "horizontal_bar") {
        // For horizontal bar, we swap the axes
        return (
            <ResponsiveContainer width="100%" height={Math.max(height, processedData.length * 35)}>
                <BarChart
                    data={processedData}
                    layout="vertical"
                    margin={{ top: 10, right: 10, left: 10, bottom: 10 }}
                >
                    {ui_hints.show_grid && (
                        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
                    )}
                    <XAxis
                        type="number"
                        tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
                        tickLine={false}
                        axisLine={{ stroke: CHART_COLORS.grid }}
                        tickFormatter={(value: number) => formatCompactNumber(value)}
                    />
                    <YAxis
                        type="category"
                        dataKey={ui_hints.truncate_labels ? `${y_axis.field}_display` : y_axis.field}
                        tick={{ fontSize: 11, fill: CHART_COLORS.muted }}
                        tickLine={false}
                        axisLine={{ stroke: CHART_COLORS.grid }}
                        width={100}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                        dataKey={x_axis.field}
                        fill={CHART_COLORS.primary}
                        radius={[0, 4, 4, 0]}
                        animationDuration={ui_hints.animate ? 500 : 0}
                    />
                </BarChart>
            </ResponsiveContainer>
        );
    }

    if (chart_type === "donut") {
        return (
            <ResponsiveContainer width="100%" height={height}>
                <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
                    <Pie
                        data={processedData}
                        dataKey={y_axis.field}
                        nameKey={x_axis.field}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        animationDuration={ui_hints.animate ? 500 : 0}
                    >
                        {processedData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    {ui_hints.show_legend && (
                        <Legend
                            formatter={(value) => (
                                <span className="text-sm text-muted-foreground">{value}</span>
                            )}
                        />
                    )}
                </PieChart>
            </ResponsiveContainer>
        );
    }

    // Fallback for unknown chart types
    return (
        <div className="flex items-center justify-center h-40 bg-secondary/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
                Chart type &ldquo;{chart_type}&rdquo; not supported
            </p>
        </div>
    );
}
