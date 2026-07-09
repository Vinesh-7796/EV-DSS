import React from 'react';
import type { CitationItem } from '../../types';
import { theme } from '../../styles/theme';

interface Props {
  citations: CitationItem[];
}

export function CitationPanel({ citations }: Props) {
  if (!citations || citations.length === 0) return null;
  return (
    <div style={{
      background: theme.bg.card,
      borderRadius: theme.radius.lg,
      border: `1px solid ${theme.border.primary}`,
      padding: theme.spacing.lg,
      marginBottom: theme.spacing.md,
    }}>
      <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
        Citations
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
  );
}
