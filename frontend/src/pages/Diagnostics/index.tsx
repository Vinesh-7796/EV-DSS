import React, { useState, useCallback } from 'react';
import { InputBox } from '../../components/InputBox';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { theme } from '../../styles/theme';
import { api } from '../../services/api';
import type { DiagnosticResult } from '../../types';
import { SafetyWarnings } from '../../components/SafetyWarnings';
import { EvidenceViewer } from '../../components/EvidenceViewer';
import { CitationPanel } from '../../components/CitationPanel';
import { ConfidencePanel } from '../../components/ConfidencePanel';
import { ProcessingStatus } from '../../components/ProcessingStatus';

function SectionBlock({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Card style={{ marginBottom: theme.spacing.md }}>
      <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
        {title}
      </div>
      {items.map((item, i) => (
        <div key={i} style={{
          fontSize: theme.font.size.base,
          color: theme.text.secondary,
          padding: '4px 0',
          paddingLeft: theme.spacing.lg,
          borderBottom: `1px solid ${theme.border.subtle}`,
          lineHeight: 1.5,
        }}>
          &bull; {item}
        </div>
      ))}
    </Card>
  );
}

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
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: theme.spacing['2xl'] }}>
        <div style={{ fontSize: theme.font.size['3xl'], fontWeight: theme.font.weight.bold, color: theme.text.primary, marginBottom: theme.spacing.xl }}>
          Diagnostics
        </div>

        {error && (
          <Card style={{ borderColor: theme.accent.red, marginBottom: theme.spacing.md }}>
            <div style={{ color: theme.accent.red, fontSize: theme.font.size.base }}>{error}</div>
          </Card>
        )}

        {result && (
          <>
            <Card style={{ marginBottom: theme.spacing.md }}>
              <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
                Fault Summary
              </div>
              <div style={{ fontSize: theme.font.size.md, color: theme.text.primary, lineHeight: 1.6 }}>
                {result.problem_summary}
              </div>
              <div style={{ display: 'flex', gap: theme.spacing.sm, marginTop: theme.spacing.sm }}>
                {result.active_model && <Badge variant="blue">{result.active_model}</Badge>}
                {result.processing_time_ms > 0 && (
                  <Badge variant="cyan">{(result.processing_time_ms / 1000).toFixed(1)}s</Badge>
                )}
              </div>
            </Card>
            <SectionBlock title="Possible Causes" items={result.possible_causes} />
            <SectionBlock title="Inspection Steps" items={result.inspection_steps} />
            <SectionBlock title="Recommended Actions" items={result.recommended_actions} />
            <SafetyWarnings warnings={result.safety_warnings} />
            <ConfidencePanel confidence={result.confidence} evidence={result.evidence} citations={result.citations} />
            {result.validation && (
              <ProcessingStatus status={result.validation.status} stages={result.validation.stages} />
            )}
          </>
        )}

        {!result && !loading && (
          <div style={{ textAlign: 'center', paddingTop: 60, color: theme.text.muted }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={theme.text.dim} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: theme.spacing.lg }}>
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            <div style={{ fontSize: theme.font.size.md, fontWeight: theme.font.weight.medium, color: theme.text.secondary, marginBottom: theme.spacing.sm }}>
              Run a diagnostic analysis
            </div>
            <div style={{ fontSize: theme.font.size.sm, color: theme.text.muted }}>
              Describe the vehicle issue to get a structured diagnostic report with confidence scoring and evidence.
            </div>
          </div>
        )}
      </div>
      <InputBox onSend={handleSend} disabled={loading} placeholder="Describe the vehicle issue..." />
    </div>
  );
}
