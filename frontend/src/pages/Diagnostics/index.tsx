import React, { useState, useCallback } from "react";
import { InputBox } from "../../components/InputBox";
import { ConfidenceCard } from "../../components/ConfidenceCard";
import { SafetyWarnings } from "../../components/SafetyWarnings";
import { CitationPanel } from "../../components/CitationPanel";
import { EvidenceViewer } from "../../components/EvidenceViewer";
import { ProcessingStatus } from "../../components/ProcessingStatus";
import { api } from "../../services/api";
import type { DiagnosticResult } from "../../types";

const style: Record<string, React.CSSProperties> = {
  page: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
  },
  content: {
    flex: 1,
    overflowY: "auto",
    padding: 16,
  },
  header: {
    fontSize: 16,
    fontWeight: 600,
    color: "#e6e6e6",
    marginBottom: 16,
  },
  card: {
    background: "#1e2430",
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "#8b949e",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 8,
  },
  listItem: {
    fontSize: 13,
    color: "#c9d1d9",
    padding: "4px 0",
    paddingLeft: 16,
    borderBottom: "1px solid #161b22",
  },
};

export function DiagnosticsPage() {
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(async (query: string) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.diagnose.run(query);
      setResult(r);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Request failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div style={style.page}>
      <div style={style.content}>
        <div style={style.header}>Diagnostic Report</div>
        {error && (
          <div style={{ ...style.card, border: "1px solid #f44336", color: "#f44336" }}>
            {error}
          </div>
        )}
        {result && (
          <>
            <div style={style.card}>
              <div style={style.cardTitle}>Problem Summary</div>
              <div style={{ fontSize: 14, color: "#e6e6e6" }}>
                {result.problem_summary}
              </div>
            </div>
            <div style={style.card}>
              <div style={style.cardTitle}>Possible Causes</div>
              {result.possible_causes.map((c, i) => (
                <div key={i} style={style.listItem}>
                  {i + 1}. {c}
                </div>
              ))}
            </div>
            <div style={style.card}>
              <div style={style.cardTitle}>Inspection Steps</div>
              {result.inspection_steps.map((s, i) => (
                <div key={i} style={style.listItem}>
                  {i + 1}. {s}
                </div>
              ))}
            </div>
            <div style={style.card}>
              <div style={style.cardTitle}>Recommended Actions</div>
              {result.recommended_actions.map((a, i) => (
                <div key={i} style={style.listItem}>
                  {i + 1}. {a}
                </div>
              ))}
            </div>
            <ConfidenceCard confidence={result.confidence} />
            <SafetyWarnings warnings={result.safety_warnings} />
            <EvidenceViewer evidence={result.evidence} />
            <CitationPanel citations={result.citations} />
            {result.validation && (
              <ProcessingStatus
                status={result.validation.status}
                stages={result.validation.stages}
              />
            )}
          </>
        )}
        {!result && !loading && (
          <div style={{ color: "#484f58", textAlign: "center", paddingTop: 40 }}>
            Enter a query to run a full diagnostic analysis
          </div>
        )}
      </div>
      <InputBox
        onSend={handleSend}
        disabled={loading}
        placeholder="Describe the vehicle issue..."
      />
    </div>
  );
}
