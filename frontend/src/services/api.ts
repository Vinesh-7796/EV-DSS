import type { DiagnosticResult, ConfigData } from "../types";

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
    check: () => request<{ status: string }>("GET", "/health"),
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
};
