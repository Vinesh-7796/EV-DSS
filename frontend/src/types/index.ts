export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  diagnostic?: DiagnosticResult;
}

export interface DiagnosticResult {
  conversation_id: string;
  problem_summary: string;
  possible_causes: string[];
  inspection_steps: string[];
  recommended_actions: string[];
  related_components: string[];
  connectors: string[];
  fuses: string[];
  relays: string[];
  can_signals: string[];
  confidence: ConfidenceInfo;
  safety_warnings: string[];
  evidence: EvidenceItem[];
  citations: CitationItem[];
  entities?: EntityItem[];
  validation?: ValidationInfo;
  processing_time_ms: number;
  active_model?: string;
}

export interface ConfidenceInfo {
  overall_score: number;
  level: string;
  validation_status: string;
  evidence_coverage?: number;
  citation_validity?: number;
  consistency?: number;
  component_scores?: ComponentScore[];
  hallucination_detected?: boolean;
}

export interface ComponentScore {
  name: string;
  score: number;
}

export interface EvidenceItem {
  node_id: string;
  document: string;
  section: string;
  page: number;
  content: string;
  score: number;
  relationship?: string;
  entity?: string;
  validator?: string;
}

export interface CitationItem {
  text: string;
  document_id?: string;
  page?: number;
  section?: string;
  is_valid: boolean;
  reason?: string;
}

export interface EntityItem {
  name: string;
  entity_type: string;
  is_valid: boolean;
  reason?: string;
}

export interface ValidationInfo {
  status: string;
  stages: StageInfo[];
  hallucination_summary?: string;
  safety_rules_triggered?: string[];
}

export interface StageInfo {
  name: string;
  status: string;
  duration_ms: number;
  error?: string;
  result_count?: number;
}

export interface ConfigData {
  application: {
    name: string;
    version: string;
    debug: boolean;
  };
  reasoning: {
    runtime: string;
    model: string;
    temperature: number;
    max_tokens: number;
  };
  retrieval: {
    top_k_vector: number;
    top_k_graph: number;
  };
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: number;
  updated_at: number;
}

// ── Phase 1 — Knowledge Base ────────────────────────────────────────────────

export interface KBDocument {
  filename: string;
  type: string;
  status: "indexed" | "processing" | "error" | "not_indexed";
  chunks: number;
  nodes: number;
  edges: number;
  last_indexed: string;
  checksum: string;
  file_size: number;
  store_id: string;
  file_exists: boolean;
}

export interface KBStatus {
  watcher_running: boolean;
  monitored_path: string;
  queue_depth: number;
  total_processed: number;
  total_errors: number;
  last_event_at: string | null;
  last_error: string | null;
  indexed_files: number;
}

export interface IngestionLogEntry {
  timestamp: string;
  event: "added" | "modified" | "deleted" | "reindex" | "error";
  filename: string;
  status: "queued" | "processing" | "done" | "failed" | "removed";
  detail: string;
  duration_ms: number;
}

// ── Phase 2 — Model Management ──────────────────────────────────────────────

export interface OllamaModel {
  name: string;
  size_bytes: number;
  size_formatted: string;
  quantization: string;
  family: string;
  modified_date: string;
  is_recommended: boolean;
}

export interface ActiveModelInfo {
  active_model: string;
  runtime: string;
  details: OllamaModel | null;
  ollama_url: string;
}

export interface PullProgress {
  status: string;
  digest?: string;
  total?: number;
  completed?: number;
  error?: string;
}

export interface HardwareRecommendations {
  ram_gb: number;
  gpu_vram_gb: number;
  gpu_name: string;
  recommendation: string;
}

// ── Phase 3 — Diagnostic History ────────────────────────────────────────────

export interface ReportSummary {
  id: string;
  timestamp: string;
  query: string;
  problem_summary: string;
  confidence_score: number;
  confidence_level: string;
  model: string;
  processing_time_ms: number;
  md_path: string;
}

export interface ReportDetail {
  metadata: ReportSummary;
  diagnostic_result: DiagnosticResult;
  markdown: string;
}

// ── Phase 4 — System Status ─────────────────────────────────────────────────

export interface SystemHealth {
  status: "healthy" | "degraded" | "offline";
  components: {
    backend: { status: string; name: string; version: string };
    ollama: { status: string; url: string; active_model: string; runtime: string; error?: string };
    embedding: { status: string; model: string; dimension: number };
    vector_db: { status: string; url: string; error?: string };
    graph: { status: string; entity_count: number };
    knowledge_base: {
      status: string;
      indexed_documents: number;
      total_chunks: number;
      total_entities: number;
      last_update: string;
      watcher_running: boolean;
    };
  };
  performance: {
    avg_response_time_ms: number;
    response_samples: number;
  };
  hardware: {
    gpu: { available: boolean; name: string | null; vram_mb: number };
    ram: { total_gb?: number; used_gb?: number; available_gb?: number; percent?: number; available?: boolean };
  };
  version: string;
}
