import type {
  DiagnosticResult,
  ConfigData,
  KBDocument,
  KBStatus,
  IngestionLogEntry,
  OllamaModel,
  ActiveModelInfo,
  HardwareRecommendations,
  ReportSummary,
  ReportDetail,
  SystemHealth,
} from "../types";

const BASE_URL = "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const resp = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new ApiError(resp.status, detail.detail || resp.statusText);
  }

  return resp.json() as Promise<T>;
}

export const api = {
  health: {
    check: () => request<SystemHealth>("GET", "/health"),
    version: () => request<{ version: string }>("GET", "/version"),
  },

  chat: {
    send: (
      message: string,
      conversationId?: string,
      signal?: AbortSignal,
    ) =>
      request<DiagnosticResult>("POST", "/chat", {
        message,
        conversation_id: conversationId,
      }, signal),
  },

  diagnose: {
    run: (query: string, conversationId?: string, signal?: AbortSignal) =>
      request<DiagnosticResult>("POST", "/diagnostics", {
        query,
        conversation_id: conversationId,
      }, signal),
  },

  documents: {
    list: (type?: string) => {
      const params = type ? `?type=${encodeURIComponent(type)}` : "";
      return request<unknown[]>("GET", `/documents${params}`);
    },
    get: (id: string) => request<unknown>("GET", `/documents/${id}`),
  },

  config: {
    get: () => request<ConfigData>("GET", "/config"),
  },

  statistics: {
    get: () => request<{ total_diagnostics: number }>("GET", "/statistics"),
  },

  // ── Phase 1 — Knowledge Base ──────────────────────────────────────────────
  kb: {
    status: () => request<KBStatus>("GET", "/kb/status"),
    log: (limit = 50) => request<IngestionLogEntry[]>("GET", `/kb/log?limit=${limit}`),
    documents: () => request<KBDocument[]>("GET", "/kb/documents"),
    refresh: () => request<{ queued: number; message: string }>("POST", "/kb/refresh"),
    reindex: (filename: string) =>
      request<{ success: boolean; message: string }>("POST", `/kb/reindex/${encodeURIComponent(filename)}`),
    deleteDocument: (filename: string) =>
      request<{ success: boolean; message: string }>("DELETE", `/kb/documents/${encodeURIComponent(filename)}`),
    rawPath: () => request<{ path: string }>("GET", "/kb/raw-path"),
    openFolder: () => request<{ success: boolean }>("POST", "/kb/open-folder"),
  },

  // ── Phase 2 — Models ──────────────────────────────────────────────────────
  models: {
    list: () => request<OllamaModel[]>("GET", "/models"),
    active: () => request<ActiveModelInfo>("GET", "/models/active"),
    activate: (model_name: string) =>
      request<{ success: boolean; active_model: string }>("POST", "/models/activate", { model_name }),
    hardware: () => request<HardwareRecommendations>("GET", "/models/hardware-recommendations"),
    // pull is SSE-based; handled with fetch directly in the component
  },

  // ── Phase 3 — Reports / History ───────────────────────────────────────────
  reports: {
    list: (query?: string) => {
      const params = query ? `?query=${encodeURIComponent(query)}` : "";
      return request<ReportSummary[]>("GET", `/reports${params}`);
    },
    get: (id: string) => request<ReportDetail>("GET", `/reports/${id}`),
    delete: (id: string) =>
      request<{ success: boolean }>("DELETE", `/reports/${id}`),
    location: (id: string) =>
      request<{ absolute_path: string }>("GET", `/reports/${id}/location`),
    rerun: (id: string) =>
      request<{ success: boolean; diagnostic_result: DiagnosticResult }>("POST", `/reports/${id}/rerun`),
  },
};
