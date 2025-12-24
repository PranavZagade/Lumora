import { create } from "zustand";
import type { SuggestedQuestion } from "@/lib/api";

export type SessionStatus = "idle" | "uploading" | "processing" | "ready" | "error";
export type ColumnRole = "identifier" | "timestamp" | "metric" | "dimension";

export interface DatasetInfo {
  id: string;
  name: string;
  rows: number;
  columns: number;
  uploadedAt: Date;
}

export interface ColumnInfo {
  name: string;
  type: "numeric" | "categorical" | "datetime" | "boolean" | "text";
  nullCount: number;
  uniqueCount: number;
}

export interface HealthIssue {
  column: string;
  type: "missing" | "duplicate" | "format";
  severity: "low" | "medium" | "high";
  count: number;
  percentage: number;
  description: string;
  explanation: string;
  role: ColumnRole | null;
}

export interface HealthCheckResult {
  issues: HealthIssue[];
  overallHealth: "good" | "fair" | "poor";
  summary: string;
  checksPerformed: string[];
}

export interface Insight {
  id: string;
  type: "trend" | "ranking" | "concentration" | "anomaly" | "summary";
  title: string;
  description: string;
  confidence: number;
  data?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  insights?: Insight[];
  requiresMapping?: boolean;
  missingConcepts?: string[];
  availableColumns?: string[];
}

export interface Session {
  id: string;
  name: string;
  createdAt: Date;
  dataset?: DatasetInfo;
  status: SessionStatus;
}

interface SessionState {
  // Current session
  currentSession: Session | null;
  sessions: Session[];
  
  // Dataset state
  dataset: DatasetInfo | null;
  columnProfiles: ColumnInfo[];
  healthCheck: HealthCheckResult | null;
  insights: Insight[];
  suggestedQuestions: SuggestedQuestion[];
  
  // Chat state
  messages: ChatMessage[];
  isTyping: boolean;
  
  // UI state
  sidebarOpen: boolean;
  status: SessionStatus;
  error: string | null;
  
  // Actions
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setStatus: (status: SessionStatus) => void;
  setError: (error: string | null) => void;
  
  // Session actions
  createSession: (name?: string) => Session;
  selectSession: (sessionId: string) => void;
  
  // Dataset actions
  setDataset: (dataset: DatasetInfo) => void;
  setColumnProfiles: (columns: ColumnInfo[]) => void;
  setHealthCheck: (result: HealthCheckResult | null) => void;
  setInsights: (insights: Insight[]) => void;
  setSuggestedQuestions: (questions: SuggestedQuestion[]) => void;
  
  // Chat actions
  addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => void;
  setIsTyping: (typing: boolean) => void;
  clearMessages: () => void;
  
  // Reset
  reset: () => void;
}

const generateId = () => Math.random().toString(36).substring(2, 15);

export const useSessionStore = create<SessionState>((set, get) => ({
  // Initial state
  currentSession: null,
  sessions: [],
  dataset: null,
  columnProfiles: [],
  healthCheck: null,
  insights: [],
  suggestedQuestions: [],
  messages: [],
  isTyping: false,
  sidebarOpen: true,
  status: "idle",
  error: null,
  
  // UI actions
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setStatus: (status) => set({ status, error: status === "error" ? get().error : null }),
  setError: (error) => set({ error, status: error ? "error" : get().status }),
  
  // Session actions
  createSession: (name) => {
    const session: Session = {
      id: generateId(),
      name: name || `Analysis ${get().sessions.length + 1}`,
      createdAt: new Date(),
      status: "idle",
    };
    set((state) => ({
      sessions: [session, ...state.sessions],
      currentSession: session,
      dataset: null,
      columnProfiles: [],
      healthCheck: null,
      insights: [],
      messages: [],
      status: "idle",
      error: null,
    }));
    return session;
  },
  
  selectSession: (sessionId) => {
    const session = get().sessions.find((s) => s.id === sessionId);
    if (session) {
      set({
        currentSession: session,
        messages: [],
        status: session.status,
      });
    }
  },
  
  // Dataset actions
  setDataset: (dataset) =>
    set((state) => ({
      dataset,
      currentSession: state.currentSession
        ? { ...state.currentSession, dataset, status: "ready" }
        : null,
    })),
  
  setColumnProfiles: (columnProfiles) => set({ columnProfiles }),
  setHealthCheck: (healthCheck) => set({ healthCheck }),
  setInsights: (insights) => set({ insights }),
  setSuggestedQuestions: (suggestedQuestions) => set({ suggestedQuestions }),
  
  // Chat actions
  addMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          ...message,
          id: generateId(),
          timestamp: new Date(),
        },
      ],
    })),
  
  setIsTyping: (isTyping) => set({ isTyping }),
  clearMessages: () => set({ messages: [] }),
  
  // Reset
  reset: () =>
    set({
      currentSession: null,
      dataset: null,
      columnProfiles: [],
      healthCheck: null,
      insights: [],
      suggestedQuestions: [],
      messages: [],
      isTyping: false,
      status: "idle",
      error: null,
    }),
}));
