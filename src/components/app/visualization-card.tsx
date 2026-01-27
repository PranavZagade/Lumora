"use client";

import { useState, useCallback } from "react";
import { BarChart3, ChevronDown, ChevronUp, Table2 } from "lucide-react";
import { ChartRenderer, type ChartSpec } from "./chart-renderer";
import { DataTable } from "./data-table";
import { cn } from "@/lib/utils";

type ViewMode = "chart" | "table";

interface VisualizationCardProps {
    spec: ChartSpec | null;
    className?: string;
}

export function VisualizationCard({ spec, className }: VisualizationCardProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    const [viewMode, setViewMode] = useState<ViewMode>("chart");
    const [fallbackReason, setFallbackReason] = useState<string | null>(null);

    // Handle chart fallback request
    const handleFallbackNeeded = useCallback((reason: string) => {
        setFallbackReason(reason);
        setViewMode("table");
    }, []);

    // Don't render if no spec
    if (!spec) {
        return null;
    }

    // Don't render if spec has a fallback reason (ineligible)
    if (spec.fallback_reason) {
        return null;
    }

    const dataCount = spec.data?.length || 0;
    const showTableToggle = dataCount > 0;

    return (
        <div
            className={cn(
                "bg-secondary/50 rounded-2xl border border-border/50 overflow-hidden",
                "animate-fade-in-up",
                className
            )}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3">
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center gap-2 hover:opacity-80 transition-opacity"
                >
                    <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center">
                        <BarChart3 className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <span className="text-sm font-medium text-foreground">
                        {spec.title || "Visualization"}
                    </span>
                    <span className="text-xs text-muted-foreground capitalize">
                        ({spec.intent})
                    </span>
                    {isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    ) : (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    )}
                </button>

                {/* View mode toggle */}
                {showTableToggle && isExpanded && (
                    <div className="flex items-center gap-1 bg-background/50 rounded-lg p-0.5">
                        <button
                            onClick={() => setViewMode("chart")}
                            disabled={fallbackReason !== null}
                            className={cn(
                                "px-2 py-1 text-xs rounded-md transition-colors",
                                viewMode === "chart"
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:text-foreground",
                                fallbackReason && "opacity-50 cursor-not-allowed"
                            )}
                        >
                            <BarChart3 className="w-3 h-3" />
                        </button>
                        <button
                            onClick={() => setViewMode("table")}
                            className={cn(
                                "px-2 py-1 text-xs rounded-md transition-colors",
                                viewMode === "table"
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:text-foreground"
                            )}
                        >
                            <Table2 className="w-3 h-3" />
                        </button>
                    </div>
                )}
            </div>

            {/* Content */}
            {isExpanded && (
                <div className="px-4 pb-4">
                    {/* Fallback notice */}
                    {fallbackReason && viewMode === "table" && (
                        <p className="text-xs text-muted-foreground mb-2">
                            Showing table: {fallbackReason}
                        </p>
                    )}

                    <div className="bg-background rounded-xl p-4 border border-border/30">
                        {viewMode === "chart" ? (
                            <ChartRenderer
                                spec={spec}
                                height={280}
                                onFallbackNeeded={handleFallbackNeeded}
                            />
                        ) : (
                            <DataTable
                                data={spec.data as Array<Record<string, unknown>>}
                                maxVisibleRows={10}
                            />
                        )}
                    </div>

                    {/* Data count indicator */}
                    <p className="text-xs text-muted-foreground mt-2 text-right">
                        {dataCount} data point{dataCount !== 1 ? "s" : ""}
                    </p>
                </div>
            )}
        </div>
    );
}
