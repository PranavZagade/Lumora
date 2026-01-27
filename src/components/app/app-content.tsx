"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Share2, Download, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sidebar } from "@/components/app/sidebar";
import { WelcomeView } from "@/components/app/welcome-view";
import { ChatInput } from "@/components/app/chat-input";
import { ChatMessage, TypingIndicator } from "@/components/app/chat-message";
import { HealthCheck } from "@/components/app/health-check";
import { DatasetSummary } from "@/components/app/dataset-summary";
import { InsightList } from "@/components/app/insight-card";
import { SuggestedQuestions } from "@/components/app/suggested-questions";
import { MappingSelector } from "@/components/app/mapping-selector";
import { useSessionStore } from "@/stores/session";
import { api, type SuggestedQuestion } from "@/lib/api";
import type {
  DatasetInfo,
  ColumnInfo,
  Insight,
  HealthCheckResult,
  HealthIssue,
} from "@/stores/session";

// Sample data for demo purposes (used when API is unavailable or for sample data)
const SAMPLE_DATASET: DatasetInfo = {
  id: "sample-1",
  name: "sales_data_2024.csv",
  rows: 15847,
  columns: 12,
  uploadedAt: new Date(),
};

const SAMPLE_COLUMNS: ColumnInfo[] = [
  { name: "order_id", type: "text", nullCount: 0, uniqueCount: 15847 },
  { name: "customer_id", type: "categorical", nullCount: 23, uniqueCount: 4521 },
  { name: "product_name", type: "categorical", nullCount: 0, uniqueCount: 156 },
  { name: "quantity", type: "numeric", nullCount: 12, uniqueCount: 48 },
  { name: "unit_price", type: "numeric", nullCount: 0, uniqueCount: 89 },
  { name: "total_amount", type: "numeric", nullCount: 0, uniqueCount: 3421 },
  { name: "order_date", type: "datetime", nullCount: 0, uniqueCount: 365 },
  { name: "region", type: "categorical", nullCount: 45, uniqueCount: 4 },
];

const SAMPLE_HEALTH_CHECK: HealthCheckResult = {
  issues: [],
  overallHealth: "good",
  summary:
    "We checked for missing values, duplicate rows, and invalid formats — none were found.",
  checksPerformed: ["missing values", "duplicate rows", "invalid numeric values", "invalid or future dates"],
};

const SAMPLE_INSIGHTS: Insight[] = [
  {
    id: "1",
    type: "trend",
    title: "Sales peaked in Q4 with 47% growth",
    description:
      "Total revenue increased from $2.1M in Q3 to $3.1M in Q4, driven primarily by the Electronics category which saw a 62% increase.",
    confidence: 0.92,
  },
  {
    id: "2",
    type: "concentration",
    title: "Top 10% of customers generate 68% of revenue",
    description:
      "Your customer base shows significant concentration. The top 452 customers (10%) account for $6.8M of the $10M total revenue.",
    confidence: 0.95,
  },
  {
    id: "3",
    type: "ranking",
    title: "West region leads with $3.2M in sales",
    description:
      "The West region outperformed other regions by 23%. North and South regions are tied at $2.4M each, while East trails at $2.0M.",
    confidence: 0.88,
  },
  {
    id: "4",
    type: "anomaly",
    title: "Unusual spike in returns during March",
    description:
      "Return rate jumped from 2.3% to 8.7% in March, primarily affecting the Apparel category. This coincides with a supplier change.",
    confidence: 0.76,
  },
];

export function AppContent() {
  const searchParams = useSearchParams();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [apiAvailable, setApiAvailable] = useState(true);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState<string | null>(null);
  const [rowProgress, setRowProgress] = useState<{ current: number; total: number | null }>({
    current: 0,
    total: null,
  });
  const progressAnimRef = useRef<number | null>(null);
  const rowAnimRef = useRef<number | null>(null);
  const progressValueRef = useRef(0);

  const {
    dataset,
    columnProfiles,
    healthCheck,
    insights,
    suggestedQuestions,
    messages,
    isTyping,
    status,
    error,
    mappingActive,
    mappingConcept,
    mappingAvailableColumns,
    createSession,
    setDataset,
    setColumnProfiles,
    setHealthCheck,
    setInsights,
    setSuggestedQuestions,
    addMessage,
    setIsTyping,
    setStatus,
    setError,
    setMappingState,
    clearMappingState,
  } = useSessionStore();

  // Debug: Monitor mapping state changes
  useEffect(() => {
    console.log("Mapping state changed:", {
      mappingActive,
      mappingConcept,
      mappingAvailableColumns: mappingAvailableColumns?.length || 0,
    });
  }, [mappingActive, mappingConcept, mappingAvailableColumns]);

  // Check API availability on mount
  // Check API availability on mount with retries
  useEffect(() => {
    const checkHealth = async (retries = 3, delay = 1000) => {
      try {
        await api.healthCheck();
        setApiAvailable(true);
      } catch (err) {
        console.warn(`API check failed, retrying... (${retries} left)`);
        if (retries > 0) {
          setTimeout(() => checkHealth(retries - 1, delay * 2), delay);
        } else {
          console.error("API Health Check Failed:", err);
          setApiAvailable(false);
        }
      }
    };

    checkHealth();
  }, []);

  // Cleanup animations on unmount
  useEffect(() => {
    return () => {
      if (progressAnimRef.current) cancelAnimationFrame(progressAnimRef.current);
      if (rowAnimRef.current) cancelAnimationFrame(rowAnimRef.current);
    };
  }, []);

  const animateProgress = useCallback((target: number, duration = 600) => {
    const clampedTarget = Math.min(100, Math.max(progressValueRef.current, target));
    if (clampedTarget === progressValueRef.current) return;

    if (progressAnimRef.current) {
      cancelAnimationFrame(progressAnimRef.current);
    }

    const start = performance.now();
    const startVal = progressValueRef.current;

    const step = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      const eased = t * (2 - t); // ease-out
      const value = startVal + (clampedTarget - startVal) * eased;
      progressValueRef.current = value;
      setProgress(value);
      if (t < 1) {
        progressAnimRef.current = requestAnimationFrame(step);
      } else {
        progressAnimRef.current = null;
      }
    };

    progressAnimRef.current = requestAnimationFrame(step);
  }, []);

  const animateRows = useCallback((total: number) => {
    if (rowAnimRef.current) {
      cancelAnimationFrame(rowAnimRef.current);
    }
    const start = performance.now();
    const duration = 800;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = t * (2 - t);
      const current = Math.floor(total * eased);
      setRowProgress({ current, total });
      if (t < 1) {
        rowAnimRef.current = requestAnimationFrame(step);
      } else {
        rowAnimRef.current = null;
      }
    };
    rowAnimRef.current = requestAnimationFrame(step);
  }, []);

  const handleFileSelect = useCallback(async (file: File) => {
    createSession(file.name);
    setStatus("uploading");
    setError(null);
    setHealthCheck(null); // Reset health check
    setSuggestedQuestions([]);
    setProgress(5);
    progressValueRef.current = 5;
    setProgressLabel("Uploading file…");
    setRowProgress({ current: 0, total: null });

    try {
      // Upload to backend API
      const response = await api.uploadDataset(file);

      setStatus("processing");
      animateProgress(30);

      // Get the full profile
      setProgressLabel("Reading rows…");
      animateProgress(40);
      const profile = await api.getDatasetProfile(response.dataset_id);
      animateProgress(60);
      if (profile.dataset.rows) {
        animateRows(profile.dataset.rows);
        setProgressLabel("Reading rows…");
      }

      // Map API response to store format
      const datasetInfo: DatasetInfo = {
        id: profile.dataset.id,
        name: profile.dataset.name,
        rows: profile.dataset.rows,
        columns: profile.dataset.columns,
        uploadedAt: new Date(profile.dataset.uploaded_at),
      };

      const columns: ColumnInfo[] = profile.columns.map((col) => ({
        name: col.name,
        type: col.dtype === "boolean" ? "boolean" : col.dtype,
        nullCount: col.null_count,
        uniqueCount: col.unique_count,
      }));

      setDataset(datasetInfo);
      setColumnProfiles(columns);

      // Stage 3 — Analyzing structure
      setProgressLabel("Analyzing columns and data types…");
      animateProgress(85);

      addMessage({
        role: "assistant",
        content: `I've analyzed your dataset "${file.name}". Here's what I found:`,
      });

      // Fetch health check in the background
      try {
        setProgressLabel("Checking for missing values and duplicates…");
        animateProgress(95);
        const healthResult = await api.getDataHealthCheck(response.dataset_id);

        // Map API response to store format
        const mappedHealthCheck: HealthCheckResult = {
          issues: healthResult.issues.map((issue): HealthIssue => ({
            column: issue.column,
            type: issue.issue_type,
            severity: issue.severity,
            count: issue.count,
            percentage: issue.percentage,
            description: issue.description,
            explanation: issue.explanation,
            role: issue.role,
          })),
          overallHealth: healthResult.overall_health,
          summary: healthResult.summary,
          checksPerformed: healthResult.checks_performed,
        };

        setHealthCheck(mappedHealthCheck);
      } catch (healthError) {
        console.error("Health check failed:", healthError);
        // Don't fail the whole upload if health check fails
      }

      // Fetch structural insights in the background
      try {
        setProgressLabel("Finalizing dataset…");
        const insightsResult = await api.getInsights(response.dataset_id);
        const mappedInsights: Insight[] = insightsResult.insights.map((insight) => ({
          id: insight.id,
          type: insight.insight_type,
          title: insight.title,
          description: insight.description,
          confidence: insight.confidence,
          data: insight.data,
        }));
        setInsights(mappedInsights);
      } catch (insightsError) {
        console.error("Insights fetch failed:", insightsError);
        // Safe to ignore; health check and summary still work
      }

      // Fetch suggested questions in the background
      try {
        const suggested = await api.getSuggestedQuestions(response.dataset_id);
        const mappedQuestions: SuggestedQuestion[] = suggested.questions.map(
          (q) => ({
            id: q.id,
            text: q.text,
            column: q.column,
            type: q.type,
          })
        );
        setSuggestedQuestions(mappedQuestions);
      } catch (questionsError) {
        console.error("Suggested questions fetch failed:", questionsError);
      }

      setProgressLabel("Finalizing dataset…");
      animateProgress(100);
      setStatus("ready");

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to upload file";
      setError(errorMessage);
      setStatus("error");
      setProgress(0);
      progressValueRef.current = 0;
      setProgressLabel(null);

      addMessage({
        role: "assistant",
        content: `Sorry, there was an error processing your file: ${errorMessage}`,
      });
    }
  }, [
    createSession,
    setStatus,
    setError,
    setHealthCheck,
    setDataset,
    setColumnProfiles,
    setInsights,
    setSuggestedQuestions,
    addMessage,
    animateProgress,
    animateRows,
  ]);

  const handleSampleData = useCallback(() => {
    createSession("Sample Sales Data");
    setStatus("processing");
    setHealthCheck(null);
    setSuggestedQuestions([]);
    setProgress(5);
    progressValueRef.current = 5;
    setProgressLabel("Preparing sample data…");
    setRowProgress({ current: 0, total: null });

    setTimeout(() => {
      setProgressLabel("Reading rows…");
      animateProgress(60);
      animateRows(SAMPLE_DATASET.rows);
      setDataset(SAMPLE_DATASET);
      setColumnProfiles(SAMPLE_COLUMNS);
      setHealthCheck(SAMPLE_HEALTH_CHECK);
      setInsights(SAMPLE_INSIGHTS);
      setSuggestedQuestions([]); // For sample mode we can keep this simple for now
      setProgressLabel("Finalizing dataset…");
      animateProgress(100);
      setStatus("ready");

      addMessage({
        role: "assistant",
        content:
          "I've loaded a sample sales dataset with 15,847 orders. Here's an overview of your data and the key insights I discovered:",
      });
    }, 1000);
  }, [
    createSession,
    setStatus,
    setHealthCheck,
    setDataset,
    setColumnProfiles,
    setInsights,
    setSuggestedQuestions,
    addMessage,
    animateProgress,
    animateRows,
  ]);

  // Initialize with sample data if requested
  useEffect(() => {
    if (searchParams.get("sample") === "true" && !dataset) {
      handleSampleData();
    }
  }, [searchParams, dataset, handleSampleData]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSendMessage = useCallback(async (content: string) => {
    if (!dataset) {
      return;
    }

    addMessage({ role: "user", content });
    setIsTyping(true);

    try {
      // Execute question via API
      const result = await api.executeQuestion(dataset.id, content);

      // Debug: Log the full response structure
      console.log("API Response:", JSON.stringify(result, null, 2));
      console.log("Result type:", result.result?.type);

      // Format result for display
      let responseText = "";

      // CRITICAL: Check for column_mapping_required FIRST, before any other processing
      if (result.result?.type === "column_mapping_required") {
        // Handle column mapping request - set explicit mapping state
        const mappingResult = result.result as {
          type: "column_mapping_required";
          concept: string;
          message?: string;
          available_columns?: string[];
        };

        // Ensure available_columns is an array of strings
        const availableColumns: string[] = Array.isArray(mappingResult.available_columns)
          ? mappingResult.available_columns.filter((col): col is string => typeof col === 'string')
          : [];

        // Set explicit mapping state (this triggers the UI)
        console.log("Setting mapping state:", {
          active: true,
          concept: mappingResult.concept,
          columns: availableColumns,
        });
        setMappingState(true, mappingResult.concept, availableColumns);

        // Add message for context (optional, for display)
        addMessage({
          role: "assistant",
          content: mappingResult.message || `To answer this question, I need to know which column represents '${mappingResult.concept}'. Please select the column from your dataset.`,
        });

        setIsTyping(false);
        return;  // Stop processing until mapping is saved
      } else if (result.result?.type === "metadata") {
        const metadataResult = result.result as { type: "metadata"; message?: string };
        if (metadataResult.message && typeof metadataResult.message === "string") {
          responseText = metadataResult.message;
        }
      } else if (result.result?.type === "dataset_summary") {
        const summaryResult = result.result as {
          type: "dataset_summary";
          rows?: number;
          columns?: number;
        };
        responseText = `This dataset contains **${(summaryResult.rows || 0).toLocaleString()}** rows and **${summaryResult.columns || 0}** columns.`;
      } else if (result.result?.message && typeof result.result.message === "string") {
        // Use backend-formatted message for all result types
        responseText = result.result.message;
      } else if (result.result.type === "clarification") {
        // Regular clarification (not mapping-related)
        const clarificationResult = result.result as {
          type: "clarification";
          message?: string;
        };

        responseText = clarificationResult.message || "Please clarify what you want to analyze.";
      } else if (result.result.type === "scalar") {
        const scalarResult = result.result as {
          type: "scalar";
          value?: number;
          aggregation?: string;
          time_period?: string;
          time_periods?: string[];
          dimension_value?: string;
          dimension_values?: string[];
          tied?: boolean;
          tied_count?: number;
        };
        const agg = scalarResult.aggregation || "value";
        const value = scalarResult.value;
        const tied = scalarResult.tied;
        const tiedCount = scalarResult.tied_count;

        // Handle ties
        if (tied && tiedCount) {
          if (agg === "count") {
            responseText = `There are **${value?.toLocaleString() || "0"}** records`;
          } else {
            responseText = `The ${agg} is **${value?.toLocaleString() || "0"}**`;
          }

          // Handle time period ties
          if (scalarResult.time_periods) {
            const periods = scalarResult.time_periods;
            if (periods.length === 2) {
              responseText += ` in both ${periods[0]} and ${periods[1]}`;
            } else {
              responseText += ` in ${periods.length} time periods: ${periods.slice(0, 3).join(", ")}${periods.length > 3 ? `, and ${periods.length - 3} more` : ""}`;
            }
          }

          // Handle dimension ties
          if (scalarResult.dimension_values) {
            const dims = scalarResult.dimension_values;
            if (dims.length === 2) {
              responseText += ` for both ${dims[0]} and ${dims[1]}`;
            } else {
              responseText += ` for ${dims.length} categories: ${dims.slice(0, 3).join(", ")}${dims.length > 3 ? `, and ${dims.length - 3} more` : ""}`;
            }
          }
        } else {
          // Single result
          if (agg === "count") {
            responseText = `There are **${value?.toLocaleString() || "0"}** records`;
          } else {
            responseText = `The ${agg} is **${value?.toLocaleString() || "0"}**`;
          }

          if (scalarResult.time_period) {
            responseText += ` in ${scalarResult.time_period}`;
          }
          if (scalarResult.dimension_value) {
            responseText += ` for ${scalarResult.dimension_value}`;
          }
        }
      } else if (result.result.type === "time_series") {
        const tsResult = result.result as { metric_column?: string; data: Array<{ time: string; value: number }> };
        const data = tsResult.data;
        const metricCol = tsResult.metric_column;
        responseText = `Here's how the ${metricCol ? `values in '${metricCol}'` : "values"} change over time:\n\n`;
        data.slice(0, 10).forEach((item) => {
          responseText += `- ${item.time}: ${item.value.toLocaleString()}\n`;
        });
        if (data.length > 10) {
          responseText += `\n... and ${data.length - 10} more time periods`;
        }
      } else if (result.result.type === "breakdown") {
        const bdResult = result.result as { metric_column?: string; dimension_column?: string; data: Array<{ dimension: string; value: number }> };
        const data = bdResult.data;
        const metricCol = bdResult.metric_column;
        const dimCol = bdResult.dimension_column;
        responseText = `Here's the breakdown${metricCol ? ` of ${metricCol}` : ""}${dimCol ? ` by ${dimCol}` : ""}:\n\n`;
        data.forEach((item) => {
          responseText += `- ${item.dimension}: ${item.value.toLocaleString()}\n`;
        });
      } else if (result.result.type === "ranking") {
        const data = result.result.data as Array<{ group: string; value: number; rank: number }>;
        const metricCol = result.result.metric_column;
        const groupCol = result.result.group_column || result.result.dimension_column;
        const agg = result.result.aggregation || "value";

        if (agg === "count") {
          responseText = `Top ${data.length} ${groupCol ? `by ${groupCol}` : "results"}:\n\n`;
        } else {
          responseText = `Top ${data.length} ${groupCol ? `by ${groupCol}` : "results"}${metricCol ? ` (${agg} of ${metricCol})` : ""}:\n\n`;
        }

        data.forEach((item) => {
          responseText += `${item.rank}. ${item.group}: ${item.value.toLocaleString()}\n`;
        });
      } else if (result.result.type === "empty") {
        responseText = (result.result as { type: "empty"; message?: string }).message || "No results found.";
      } else if (result.result.type === "table") {
        const tableResult = result.result as {
          type: "table";
          data: Array<Record<string, unknown>>;
          columns?: string[];
        };
        const data = tableResult.data;
        const columns = tableResult.columns || (data.length > 0 ? Object.keys(data[0]) : []);

        responseText = `Here are the results:\n\n`;
        if (data.length > 0) {
          // Show first 10 rows
          data.slice(0, 10).forEach((row, idx) => {
            responseText += `Row ${idx + 1}:\n`;
            columns.forEach((col) => {
              const val = row[col];
              responseText += `  ${col}: ${val !== null && val !== undefined ? String(val) : "null"}\n`;
            });
            responseText += "\n";
          });
          if (data.length > 10) {
            responseText += `... and ${data.length - 10} more rows`;
          }
        } else {
          responseText = "No rows returned.";
        }
      } else {
        responseText = "I received an unexpected result format. Please try rephrasing your question.";
      }

      setIsTyping(false);
      addMessage({
        role: "assistant",
        content: responseText,
        visualization: result.visualization || null,  // Pass visualization from API
      });
    } catch (error) {
      setIsTyping(false);
      const errorMessage = error instanceof Error ? error.message : "Failed to execute question";
      addMessage({
        role: "assistant",
        content: `Sorry, I couldn't process that question: ${errorMessage}`,
      });
    }
  }, [addMessage, setIsTyping, setMappingState, dataset]);

  const handleQuestionSelect = useCallback(
    (question: SuggestedQuestion) => {
      // For now, we use the question text as the user message.
      // The structured intent_type is preserved for future routing.
      handleSendMessage(question.text);
    },
    [handleSendMessage]
  );

  const formatNumber = (value: number) => value.toLocaleString();

  const isIdle = status === "idle" && !dataset;
  const isLoading = status === "uploading" || status === "processing";
  const isError = status === "error";
  const hasData = status === "ready" && dataset;

  return (
    <div className="h-screen flex bg-background-secondary">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* API Status Banner */}
        {!apiAvailable && (
          <div className="bg-severity-medium/10 border-b border-severity-medium/20 px-4 py-2 flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 text-severity-medium" />
            <span className="text-severity-medium">
              Backend API unavailable. Using demo mode.
            </span>
          </div>
        )}

        {/* Top Bar */}
        {hasData && (
          <header className="glass border-b border-border/50 px-6 py-3 flex items-center justify-between shrink-0">
            <div>
              <h1 className="text-sm font-medium text-foreground">
                {dataset.name}
              </h1>
              <p className="text-xs text-muted-foreground">
                {dataset.rows.toLocaleString()} rows · {dataset.columns} columns
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" className="gap-2">
                <Share2 className="w-4 h-4" />
                Share
              </Button>
              <Button variant="ghost" size="sm" className="gap-2">
                <Download className="w-4 h-4" />
                Export
              </Button>
            </div>
          </header>
        )}

        {/* Content Area */}
        {isIdle ? (
          <WelcomeView
            onFileSelect={apiAvailable ? handleFileSelect : handleSampleData}
            onSampleData={handleSampleData}
            isUploading={isLoading}
          />
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Scrollable Content */}
            <ScrollArea
              className="flex-1"
              ref={scrollRef as React.RefObject<HTMLDivElement>}
            >
              <div className="max-w-4xl mx-auto p-6 space-y-6">
                {/* Loading State */}
                {isLoading && (
                  <div className="flex flex-col items-center justify-center py-16">
                    <div className="w-full max-w-xl bg-white/80 backdrop-blur border border-border/60 rounded-2xl p-4 shadow-sm">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span className="text-foreground font-medium">
                          {progressLabel || "Preparing your dataset…"}
                        </span>
                        {rowProgress.total ? (
                          <span className="text-[11px] text-muted-foreground">
                            Reading rows:{" "}
                            {formatNumber(
                              Math.min(rowProgress.current, rowProgress.total)
                            )}{" "}
                            / {formatNumber(rowProgress.total)}
                          </span>
                        ) : null}
                      </div>
                      <div className="mt-3 h-3 bg-white/60 rounded-full border border-white/40 shadow-inner overflow-hidden">
                        <div
                          className="h-full rounded-full relative transition-[width] duration-300 ease-out overflow-hidden animate-progress-shift"
                          style={{
                            width: `${Math.min(100, Math.max(0, progress))}%`,
                            boxShadow:
                              "0 0 12px rgba(37,99,235,0.3), 0 0 12px rgba(239,68,68,0.28)",
                          }}
                        >
                          <div className="absolute inset-0 bg-[linear-gradient(135deg,#EF4444_0%,#2563EB_100%)]" />
                          <div className="absolute inset-0 bg-white/15 mix-blend-screen" />
                          <div className="absolute inset-x-0 top-0 h-[40%] bg-white/18" />
                          <div className="absolute inset-0 backdrop-blur-[2px]" />
                        </div>
                      </div>
                      <p className="mt-3 text-xs text-muted-foreground">
                        {progress >= 90
                          ? "Almost done…"
                          : "We’ll finish this as quickly as possible."}
                      </p>
                    </div>
                  </div>
                )}

                {/* Error State */}
                {isError && (
                  <div className="flex flex-col items-center justify-center py-20">
                    <div className="w-12 h-12 rounded-full bg-severity-high/10 flex items-center justify-center mb-4">
                      <AlertCircle className="w-6 h-6 text-severity-high" />
                    </div>
                    <p className="text-sm text-muted-foreground mb-4">
                      {error || "Something went wrong"}
                    </p>
                    <Button variant="outline" onClick={() => setStatus("idle")}>
                      Try Again
                    </Button>
                  </div>
                )}

                {/* Data Ready State */}
                {hasData && (
                  <>
                    {/* Chat Messages */}
                    {messages.map((message) => (
                      <div key={message.id}>
                        <ChatMessage message={message} />
                      </div>
                    ))}

                    {/* Mapping Selector - Rendered based on explicit state, not message flags */}
                    {(() => {
                      console.log("Rendering check:", {
                        mappingActive,
                        mappingConcept,
                        mappingAvailableColumns,
                      });
                      return mappingActive && mappingConcept;
                    })() && (
                        <div className="px-4 py-2">
                          <MappingSelector
                            missingConcepts={mappingConcept ? [mappingConcept] : []}
                            availableColumns={mappingAvailableColumns}
                            onSave={async (mappings) => {
                              if (!dataset) return;
                              try {
                                // Save mappings
                                const mappingEntries = Object.entries(mappings);
                                for (const [concept, columnName] of mappingEntries) {
                                  await api.saveMapping(dataset.id, concept, columnName);
                                }
                                // Clear mapping state
                                clearMappingState();
                                // Re-ask the original question
                                const lastUserMessage = messages
                                  .filter((m) => m.role === "user")
                                  .pop();
                                if (lastUserMessage) {
                                  await handleSendMessage(lastUserMessage.content);
                                }
                              } catch (error) {
                                console.error("Failed to save mapping:", error);
                                addMessage({
                                  role: "assistant",
                                  content: "Failed to save the column mapping. Please try again.",
                                });
                              }
                            }}
                            onCancel={() => {
                              // Clear mapping state
                              clearMappingState();
                              addMessage({
                                role: "assistant",
                                content: "Mapping cancelled. How else can I help?",
                              });
                            }}
                          />
                        </div>
                      )}

                    {/* Typing Indicator */}
                    {isTyping && <TypingIndicator />}

                    {/* Initial Analysis (show after first assistant message) */}
                    {messages.length === 1 && messages[0].role === "assistant" && (
                      <div className="space-y-6 animate-fade-in-up">
                        {/* Health Check */}
                        <HealthCheck
                          healthCheck={healthCheck}
                          totalRows={dataset.rows}
                        />

                        {/* Dataset Summary */}
                        <DatasetSummary
                          dataset={dataset}
                          columns={columnProfiles}
                        />

                        {/* Key Insights */}
                        <div className="space-y-3">
                          <h2 className="text-lg font-medium text-foreground">
                            Key Insights
                          </h2>
                          <InsightList insights={insights} />
                        </div>

                        {/* Suggested Questions */}
                        <SuggestedQuestions
                          questions={suggestedQuestions}
                          onSelect={handleQuestionSelect}
                        />
                      </div>
                    )}
                  </>
                )}
              </div>
            </ScrollArea>

            {/* Chat Input */}
            {hasData && (
              <div className="shrink-0 p-4 border-t border-border/50 bg-background">
                <div className="max-w-4xl mx-auto">
                  <ChatInput
                    onSend={handleSendMessage}
                    disabled={isTyping}
                    placeholder="Ask a question about your data..."
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
