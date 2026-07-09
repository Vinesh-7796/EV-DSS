import React from 'react';
import type { EvidenceItem } from '../../types';
import { theme } from '../../styles/theme';

interface Props {
  evidence: EvidenceItem[];
}

export function EvidenceViewer({ evidence }: Props) {
  if (!evidence || evidence.length === 0) return null;
  return (
    <div style={{
      background: theme.bg.card,
      borderRadius: theme.radius.lg,
      border: `1px solid ${theme.border.primary}`,
      padding: theme.spacing.lg,
      marginBottom: theme.spacing.md,
    }}>
      <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
        Supporting Evidence
      </div>
      {evidence.map((e, i) => (
        <div key={i} style={{
          padding: theme.spacing.sm, marginBottom: theme.spacing.xs,
          background: theme.bg.tertiary, borderRadius: theme.radius.sm,
        }}>
          <div style={{ fontSize: theme.font.size.sm, color: theme.text.secondary, lineHeight: 1.4 }}>{e.content}</div>
          <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
            {e.document && <span style={{ fontSize: theme.font.size.xs, color: theme.accent.blue }}>{e.document}</span>}
            {e.section && <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>{e.section}</span>}
            {e.page > 0 && <span style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>p.{e.page}</span>}
            {e.score > 0 && (
              <span style={{ fontSize: theme.font.size.xs, color: e.score > 0.7 ? theme.accent.green : theme.accent.orange }}>
                {(e.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
