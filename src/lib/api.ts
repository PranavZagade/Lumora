/**
 * API client for Lumora backend.
 * All data analysis is done server-side. This client only fetches results.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// === Types ===

export interface DatasetInfo {
  id: string;
  name: string;
  rows: number;
  columns: number;
  size_bytes: number;
  uploaded_at: string;
}

export interface ColumnInfo {
  name: string;
  dtype: "numeric" | "categorical" | "datetime" | "boolean" | "text";
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: string[];
}

export interface DatasetProfile {
  dataset: DatasetInfo;
  columns: ColumnInfo[];
}

export interface UploadResponse {
  success: boolean;
  dataset_id: string;
  dataset: DatasetInfo;
  message: string;
}

export type ColumnRole = "identifier" | "timestamp" | "metric" | "dimension";

export interface HealthIssue {
  column: string;
  issue_type: "missing" | "duplicate" | "format";
  severity: "low" | "medium" | "high";
  count: number;
  percentage: number;
  description: string;
  explanation: string;
  role: ColumnRole | null;
}

export interface HealthCheckResult {
  dataset_id: string;
  total_rows: number;
  total_columns: number;
  issues: HealthIssue[];
  overall_health: "good" | "fair" | "poor";
  summary: string;
  checks_performed: string[];
}

export interface Insight {
  id: string;
  insight_type: "trend" | "ranking" | "concentration" | "anomaly" | "summary";
  title: string;
  description: string;
  confidence: number;
  data?: Record<string, unknown>;
}

export interface InsightResult {
  dataset_id: string;
  insights: Insight[];
  generated_at: string;
}

export interface SuggestedQuestion {
  id: string;
  text: string;
  column: string;
  type: "time" | "category" | "numeric" | "quality";
}

export interface SuggestedQuestionsResult {
  dataset_id: string;
  questions: SuggestedQuestion[];
}

export interface ApiError {
  error: string;
  detail?: string;
}

// === API Functions ===

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        error: "Request failed",
        detail: response.statusText,
      }));
      throw new Error(error.detail || error.error);
    }

    return response.json();
  }

  /**
   * Check if the API is healthy.
   */
  async healthCheck(): Promise<{ status: string }> {
    return this.request("/api/health");
  }

  /**
   * Upload a dataset file (CSV or Excel).
   */
  async uploadDataset(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<UploadResponse>("/api/upload/", {
      method: "POST",
      body: formData,
    });
  }

  /**
   * Get the profile of an uploaded dataset.
   */
  async getDatasetProfile(datasetId: string): Promise<DatasetProfile> {
    return this.request<DatasetProfile>(`/api/upload/${datasetId}/profile`);
  }

  /**
   * Delete a dataset.
   */
  async deleteDataset(datasetId: string): Promise<{ success: boolean }> {
    return this.request(`/api/upload/${datasetId}`, {
      method: "DELETE",
    });
  }

  /**
   * Get health check results for a dataset.
   * Includes: missing values, duplicates, format issues.
   */
  async getDataHealthCheck(datasetId: string): Promise<HealthCheckResult> {
    return this.request<HealthCheckResult>(`/api/health-check/${datasetId}`);
  }

  /**
   * Get insights for a dataset.
   * (Will be implemented in backend next)
   */
  async getInsights(datasetId: string): Promise<InsightResult> {
    return this.request<InsightResult>(`/api/insights/${datasetId}`);
  }

  /**
   * Get generic, intent-based suggested questions for a dataset.
   */
  async getSuggestedQuestions(
    datasetId: string
  ): Promise<SuggestedQuestionsResult> {
    return this.request<SuggestedQuestionsResult>(
      `/api/suggested-questions/${datasetId}`
    );
  }

  /**
   * Get semantic mappings for a dataset.
   */
  async getMappings(datasetId: string): Promise<{
    dataset_id: string;
    mappings: Record<string, string>;
  }> {
    return this.request(`/api/mappings/${datasetId}`);
  }

  /**
   * Save a semantic mapping (concept → column).
   */
  async saveMapping(
    datasetId: string,
    concept: string,
    columnName: string
  ): Promise<{
    dataset_id: string;
    concept: string;
    column_name: string;
    success: boolean;
  }> {
    return this.request(`/api/mappings/${datasetId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        concept,
        column_name: columnName,
      }),
    });
  }

  /**
   * Save multiple semantic mappings at once.
   */
  async saveMappings(
    datasetId: string,
    mappings: Record<string, string>
  ): Promise<{
    dataset_id: string;
    mappings: Record<string, string>;
    success: boolean;
  }> {
    return this.request(`/api/mappings/${datasetId}/bulk`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ mappings }),
    });
  }

  /**
   * Execute a natural language question on a dataset.
   * Returns computed results (no raw data sent to AI).
   */
  async executeQuestion(
    datasetId: string,
    question: string
  ): Promise<{
    dataset_id: string;
    intent: Record<string, unknown>;
    result: Record<string, unknown>;
    metadata: Record<string, unknown>;
    confidence: number;
  }> {
    return this.request<{
      dataset_id: string;
      intent: Record<string, unknown>;
      result: Record<string, unknown>;
      metadata: Record<string, unknown>;
      confidence: number;
    }>(`/api/chat/${datasetId}/execute`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question }),
    });
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export class for testing or custom instances
export { ApiClient };
