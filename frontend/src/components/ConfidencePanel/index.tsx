import React, { useState, useCallback } from 'react';
import type { ConfidenceInfo, EvidenceItem, CitationItem } from '../../types';
import { theme } from '../../styles/theme';
import { ChevronDown, ChevronUp } from '../icons';

interface Props {
  confidence: ConfidenceInfo;
  evidence: EvidenceItem[];
  citations: CitationItem[];
}

function valColor(v: number): string {
  return v >= 0.7 ? theme.accent.green : v >= 0.4 ? theme.accent.orange : theme.accent.red;
}

export function ConfidencePanel({ confidence, evidence, citations }: Props) {
  const [open, setOpen] = useState(false);
  const toggle = useCallback(() => setOpen((v) => !v), []);

  const sc = confidence.overall_score;
  const scoreColor = sc >= 0.8 ? theme.accent.green : sc >= 0.6 ? theme.accent.orange : theme.accent.red;

  const failed = confidence.validation_status?.includes('FAIL');
  const passed = confidence.validation_status === 'PASSED';
  const statusBg = passed ? theme.accent.greenBg : failed ? theme.accent.redBg : theme.accent.blueBg;
  const statusFg = passed ? theme.accent.green : failed ? theme.accent.red : theme.accent.blue;

  const allScores: { label: string; value: number }[] = [
    ...(['evidence_coverage', 'citation_validity', 'consistency'] as const)
      .filter(k => confidence[k] !== undefined)
      .map(k => ({ label: k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()), value: confidence[k]! })),
    ...(confidence.component_scores?.map(cs => ({
      label: cs.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      value: cs.score,
    })) ?? []),
  ];

  return (
    <div style={{
      background: theme.bg.tertiary,
      borderRadius: theme.radius.lg,
      marginBottom: theme.spacing.md,
      border: `1px solid ${theme.border.secondary}`,
      overflow: 'hidden',
      transition: `all ${theme.transition.normal}`,
    }}>
      <div
        onClick={toggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${theme.spacing.md} ${theme.spacing.lg}`,
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.md }}>
          <span style={{
            fontSize: theme.font.size.sm,
            fontWeight: theme.font.weight.semibold,
            color: theme.text.muted,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
          }}>
            Confidence
          </span>
          <span style={{ fontSize: theme.font.size['2xl'], fontWeight: theme.font.weight.bold, color: scoreColor }}>
            {(sc * 100).toFixed(0)}%
          </span>
          <span style={{
            fontSize: theme.font.size.xs,
            fontWeight: theme.font.weight.semibold,
            color: statusFg,
            background: statusBg,
            padding: '2px 8px',
            borderRadius: theme.radius.full,
          }}>
            {confidence.level}
          </span>
        </div>
        <span style={{ color: theme.text.muted, display: 'flex', transition: `transform ${theme.transition.normal}` }}>
          {open ? <ChevronUp /> : <ChevronDown />}
        </span>
      </div>

      <div style={{
        maxHeight: open ? 5000 : 0,
        opacity: open ? 1 : 0,
        overflow: 'hidden',
        transition: 'max-height 0.35s ease, opacity 0.25s ease',
      }}>
        <div style={{ padding: `0 ${theme.spacing.lg} ${theme.spacing.lg}` }}>
          <div style={{ display: 'flex', gap: theme.spacing.md, marginBottom: theme.spacing.md, flexWrap: 'wrap' }}>
            <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>
              Validation: <span style={{ color: statusFg }}>{confidence.validation_status}</span>
            </span>
            {confidence.hallucination_detected !== undefined && (
              <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>
                Hallucination: <span style={{ color: confidence.hallucination_detected ? theme.accent.red : theme.accent.green }}>
                  {confidence.hallucination_detected ? 'Detected' : 'None'}
                </span>
              </span>
            )}
          </div>

          {allScores.length > 0 && (
            <div style={{ marginBottom: theme.spacing.md }}>
              <div style={{ fontSize: theme.font.size.xs, fontWeight: theme.font.weight.semibold, color: theme.text.dim, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
                Confidence Breakdown
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: theme.spacing.xs }}>
                {allScores.map((s) => (
                  <div key={s.label} style={{
                    display: 'flex', justifyContent: 'space-between', padding: '4px 8px',
                    background: theme.bg.card, borderRadius: theme.radius.sm,
                    fontSize: theme.font.size.sm,
                  }}>
                    <span style={{ color: theme.text.muted }}>{s.label}</span>
                    <span style={{ color: valColor(s.value), fontWeight: theme.font.weight.medium }}>
                      {(s.value * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {evidence.length > 0 && (
            <div style={{ marginBottom: theme.spacing.md }}>
              <div style={{ fontSize: theme.font.size.xs, fontWeight: theme.font.weight.semibold, color: theme.text.dim, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
                Supporting Evidence ({evidence.length})
              </div>
              {evidence.map((e, i) => (
                <div key={i} style={{
                  background: theme.bg.card,
                  borderRadius: theme.radius.sm,
                  padding: theme.spacing.sm,
                  marginBottom: theme.spacing.xs,
                }}>
                  <div style={{ fontSize: theme.font.size.sm, color: theme.text.secondary, lineHeight: 1.4 }}>{e.content}</div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                    {e.document && <span style={{ fontSize: theme.font.size.xs, color: theme.accent.blue }}>{e.document}</span>}
                    {e.section && <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>{e.section}</span>}
                    {e.page > 0 && <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>p.{e.page}</span>}
                    {e.score > 0 && <span style={{ fontSize: theme.font.size.xs, color: valColor(e.score) }}>{(e.score * 100).toFixed(0)}%</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          {citations.length > 0 && (
            <div>
              <div style={{ fontSize: theme.font.size.xs, fontWeight: theme.font.weight.semibold, color: theme.text.dim, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
                Citations ({citations.length})
              </div>
              {citations.map((c, i) => (
                <div key={i} style={{
                  display: 'flex', gap: theme.spacing.sm, alignItems: 'flex-start',
                  padding: '4px 0', fontSize: theme.font.size.sm, color: theme.text.secondary,
                  borderBottom: `1px solid ${theme.border.subtle}`,
                }}>
                  <span style={{
                    fontSize: theme.font.size.xs, padding: '1px 6px', borderRadius: theme.radius.sm,
                    background: c.is_valid ? theme.accent.greenBg : theme.accent.redBg,
                    color: c.is_valid ? theme.accent.green : theme.accent.red,
                    whiteSpace: 'nowrap', fontWeight: theme.font.weight.semibold,
                  }}>
                    {c.is_valid ? 'VALID' : 'INVALID'}
                  </span>
                  <span>{c.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
