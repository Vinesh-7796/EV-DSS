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
