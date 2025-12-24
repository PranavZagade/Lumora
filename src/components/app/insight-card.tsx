"use client";

import {
  TrendingUp,
  Award,
  PieChart,
  AlertTriangle,
  FileText,
  ChevronRight,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Insight } from "@/stores/session";

const insightIcons = {
  trend: TrendingUp,
  ranking: Award,
  concentration: PieChart,
  anomaly: AlertTriangle,
  summary: FileText,
};

const insightColors = {
  trend: "bg-primary/10 text-primary",
  ranking: "bg-accent/10 text-accent",
  concentration: "bg-chart-secondary/20 text-chart-secondary",
  anomaly: "bg-severity-medium/10 text-severity-medium",
  summary: "bg-severity-low/10 text-severity-low",
};

interface InsightCardProps {
  insight: Insight;
  index?: number;
  onClick?: () => void;
}

export function InsightCard({ insight, index = 0, onClick }: InsightCardProps) {
  const Icon = insightIcons[insight.type] || FileText;
  const colorClass = insightColors[insight.type] || insightColors.summary;

  return (
    <Card
      className={cn(
        "p-5 shadow-soft hover:shadow-soft-lg transition-all duration-200 cursor-pointer group",
        "animate-fade-in-up"
      )}
      style={{ animationDelay: `${index * 0.1}s` }}
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div
          className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center shrink-0",
            colorClass
          )}
        >
          <Icon className="w-5 h-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="text-base font-medium text-foreground leading-snug">
              {insight.title}
            </h3>
            {insight.confidence >= 0.8 && (
              <Badge
                variant="secondary"
                className="shrink-0 text-2xs bg-severity-low/10 text-severity-low border-0"
              >
                High confidence
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {insight.description}
          </p>
        </div>

        {/* Arrow */}
        <ChevronRight className="w-5 h-5 text-muted-foreground/50 group-hover:text-muted-foreground group-hover:translate-x-0.5 transition-all shrink-0" />
      </div>
    </Card>
  );
}

interface InsightListProps {
  insights: Insight[];
  onInsightClick?: (insight: Insight) => void;
}

export function InsightList({ insights, onInsightClick }: InsightListProps) {
  if (insights.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-12 h-12 rounded-xl bg-secondary mx-auto mb-4 flex items-center justify-center">
          <FileText className="w-6 h-6 text-muted-foreground" />
        </div>
        <p className="text-sm text-muted-foreground">
          No insights found for this dataset
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {insights.map((insight, index) => (
        <InsightCard
          key={insight.id}
          insight={insight}
          index={index}
          onClick={() => onInsightClick?.(insight)}
        />
      ))}
    </div>
  );
}

