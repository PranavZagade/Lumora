"use client";

import {
  Table2,
  Columns,
  Rows3,
  Calendar,
  Hash,
  Type,
  ToggleLeft,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DatasetInfo, ColumnInfo } from "@/stores/session";

const columnTypeConfig = {
  numeric: {
    icon: Hash,
    color: "text-primary",
    bg: "bg-primary/10",
    label: "Numeric",
  },
  categorical: {
    icon: Type,
    color: "text-accent",
    bg: "bg-accent/10",
    label: "Categorical",
  },
  datetime: {
    icon: Calendar,
    color: "text-severity-low",
    bg: "bg-severity-low/10",
    label: "Date/Time",
  },
  boolean: {
    icon: ToggleLeft,
    color: "text-severity-medium",
    bg: "bg-severity-medium/10",
    label: "Boolean",
  },
  text: {
    icon: Type,
    color: "text-muted-foreground",
    bg: "bg-secondary",
    label: "Text",
  },
};

interface DatasetSummaryProps {
  dataset: DatasetInfo;
  columns?: ColumnInfo[];
}

export function DatasetSummary({ dataset, columns = [] }: DatasetSummaryProps) {
  return (
    <Card className="shadow-soft overflow-hidden">
      {/* Header Stats */}
      <div className="p-5 border-b border-border/50">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Table2 className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-base font-medium text-foreground">
              {dataset.name}
            </h3>
            <p className="text-sm text-muted-foreground">
              Uploaded {new Date(dataset.uploadedAt).toLocaleDateString()}
            </p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-secondary/50">
            <Rows3 className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold text-foreground">
                {dataset.rows.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Rows</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-secondary/50">
            <Columns className="w-5 h-5 text-muted-foreground" />
            <div>
              <p className="text-lg font-semibold text-foreground">
                {dataset.columns.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground">Columns</p>
            </div>
          </div>
        </div>
      </div>

      {/* Column Details */}
      {columns.length > 0 && (
        <div className="p-5">
          <h4 className="text-sm font-medium text-muted-foreground mb-4 uppercase tracking-wider">
            Column Overview
          </h4>
          <div className="space-y-3">
            {columns.map((column) => {
              const config = columnTypeConfig[column.type];
              const Icon = config.icon;

              return (
                <div
                  key={column.name}
                  className="flex items-center gap-3 p-3 rounded-xl bg-secondary/30 hover:bg-secondary/50 transition-colors"
                >
                  <div
                    className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
                      config.bg
                    )}
                  >
                    <Icon className={cn("w-4 h-4", config.color)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground font-mono truncate">
                      {column.name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge
                        variant="secondary"
                        className={cn("text-2xs border-0", config.bg, config.color)}
                      >
                        {config.label}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {column.uniqueCount.toLocaleString()} unique
                      </span>
                      {column.nullCount > 0 && (
                        <span className="text-xs text-severity-medium">
                          {column.nullCount} missing
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

