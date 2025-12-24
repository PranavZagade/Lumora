"use client";

import {
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Info,
  Copy,
  FileX,
  Calendar,
} from "lucide-react";
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { HealthIssue, HealthCheckResult } from "@/stores/session";

const severityConfig = {
  low: {
    icon: CheckCircle2,
    color: "text-severity-low",
    bg: "bg-severity-low/10",
    label: "Low",
    tooltip: "Minor impact on analysis",
  },
  medium: {
    icon: AlertTriangle,
    color: "text-severity-medium",
    bg: "bg-severity-medium/10",
    label: "Medium",
    tooltip: "May affect analysis accuracy",
  },
  high: {
    icon: AlertCircle,
    color: "text-severity-high",
    bg: "bg-severity-high/10",
    label: "High",
    tooltip: "Significant impact on analysis",
  },
};

const issueTypeConfig = {
  missing: {
    icon: FileX,
    label: "Missing Values",
  },
  duplicate: {
    icon: Copy,
    label: "Duplicates",
  },
  format: {
    icon: Calendar,
    label: "Format Issue",
  },
};

const roleLabels = {
  identifier: "ID",
  timestamp: "Time",
  metric: "Metric",
  dimension: "Dimension",
};

interface HealthIssueRowProps {
  issue: HealthIssue;
}

function HealthIssueRow({ issue }: HealthIssueRowProps) {
  const severityCfg = severityConfig[issue.severity];
  const typeCfg = issueTypeConfig[issue.type];
  const SeverityIcon = severityCfg.icon;
  const TypeIcon = typeCfg.icon;

  return (
    <div className="py-4 border-b border-border/50 last:border-0">
      <div className="flex items-start gap-3">
        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0", severityCfg.bg)}>
          <SeverityIcon className={cn("w-4 h-4", severityCfg.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-foreground font-mono">
              {issue.column}
            </span>
            <Badge variant="secondary" className="text-2xs gap-1">
              <TypeIcon className="w-3 h-3" />
              {typeCfg.label}
            </Badge>
            {issue.role && (
              <Badge variant="outline" className="text-2xs">
                {roleLabels[issue.role]}
              </Badge>
            )}
            <Badge className={cn("text-2xs border-0", severityCfg.bg, severityCfg.color)}>
              {severityCfg.label}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {issue.description}
          </p>
          {/* Business impact explanation */}
          <div className="flex items-start gap-1.5 mt-2 text-xs text-muted-foreground">
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{issue.explanation}</span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <span className="text-sm font-semibold text-foreground">
            {issue.count.toLocaleString()}
          </span>
          <p className="text-xs text-muted-foreground">
            {issue.percentage}%
          </p>
        </div>
      </div>
    </div>
  );
}

/**
 * Static Transparency Panel - "What We Checked"
 * This panel is ALWAYS shown regardless of whether issues are found.
 * The list is STATIC and does NOT change based on what issues exist.
 */
interface TransparencyPanelProps {
  checksPerformed: string[];
}

function TransparencyPanel({ checksPerformed }: TransparencyPanelProps) {
  return (
    <div className="bg-secondary/30 rounded-lg p-3">
      <p className="text-xs font-medium text-muted-foreground mb-2">
        We checked for:
      </p>
      <ul className="space-y-1">
        {checksPerformed.map((check, index) => (
          <li 
            key={index} 
            className="text-xs text-muted-foreground flex items-center gap-2"
          >
            <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
            {check}
          </li>
        ))}
      </ul>
    </div>
  );
}

interface HealthCheckProps {
  healthCheck: HealthCheckResult | null;
  totalRows: number;
}

export function HealthCheck({ healthCheck }: HealthCheckProps) {
  const [expanded, setExpanded] = useState(true);

  // If no health check data yet, show loading or placeholder
  if (!healthCheck) {
    return (
      <Card className="shadow-soft overflow-hidden">
        <div className="p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
            <div className="w-5 h-5 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
          </div>
          <div>
            <h3 className="text-base font-medium text-foreground">
              Running Health Check...
            </h3>
            <p className="text-sm text-muted-foreground">
              Analyzing data quality
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const { issues, overallHealth, summary, checksPerformed } = healthCheck;
  
  const highCount = issues.filter((i) => i.severity === "high").length;
  const mediumCount = issues.filter((i) => i.severity === "medium").length;
  const lowCount = issues.filter((i) => i.severity === "low").length;

  const hasIssues = issues.length > 0;
  
  // Determine status config based on overall health
  const statusConfig = overallHealth === "poor" 
    ? severityConfig.high 
    : overallHealth === "fair" 
      ? severityConfig.medium 
      : severityConfig.low;
  const StatusIcon = statusConfig.icon;

  return (
    <TooltipProvider delayDuration={300}>
      <Card className="shadow-soft overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-4 p-5 hover:bg-secondary/30 transition-colors"
        >
        <div
          className={cn(
            "w-10 h-10 rounded-xl flex items-center justify-center",
            statusConfig.bg
          )}
        >
          <StatusIcon className={cn("w-5 h-5", statusConfig.color)} />
        </div>
        <div className="flex-1 text-left">
          <h3 className="text-base font-medium text-foreground">
            Data Health Check
          </h3>
          <p className="text-sm text-muted-foreground">
            {summary}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {highCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-severity-high/10 text-severity-high border-0 cursor-help">
                  {highCount} high
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>{severityConfig.high.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          )}
          {mediumCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-severity-medium/10 text-severity-medium border-0 cursor-help">
                  {mediumCount} medium
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>{severityConfig.medium.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          )}
          {lowCount > 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-severity-low/10 text-severity-low border-0 cursor-help">
                  {lowCount} low
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>{severityConfig.low.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-border/50">
          {hasIssues ? (
            <div className="px-5 pb-5">
              {issues.map((issue, index) => (
                <HealthIssueRow 
                  key={`${issue.column}-${issue.type}-${index}`} 
                  issue={issue} 
                />
              ))}
              
              {/* Transparency Panel - Always shown */}
              <div className="mt-4 pt-4 border-t border-border/30">
                <TransparencyPanel checksPerformed={checksPerformed} />
              </div>
            </div>
          ) : (
            <div className="px-5 py-6 text-center">
              <CheckCircle2 className="w-8 h-8 text-severity-low mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                {summary}
              </p>
              
              {/* Transparency Panel - Always shown */}
              <div className="mt-4 text-left">
                <TransparencyPanel checksPerformed={checksPerformed} />
              </div>
            </div>
          )}
        </div>
      )}
      </Card>
    </TooltipProvider>
  );
}
