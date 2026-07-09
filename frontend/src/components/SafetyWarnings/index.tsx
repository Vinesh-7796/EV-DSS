import React from 'react';
import { theme } from '../../styles/theme';

interface Props {
  warnings: string[];
}

export function SafetyWarnings({ warnings }: Props) {
  if (!warnings || warnings.length === 0) return null;
  return (
    <div style={{
      background: theme.accent.redBg,
      border: `1px solid ${theme.accent.redBorder}`,
      borderRadius: theme.radius.lg,
      padding: theme.spacing.md,
      marginBottom: theme.spacing.md,
    }}>
      <div style={{
        fontSize: theme.font.size.sm,
        fontWeight: theme.font.weight.semibold,
        color: theme.accent.red,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: theme.spacing.sm,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        Safety Warnings
      </div>
      {warnings.map((w, i) => (
        <div key={i} style={{ fontSize: theme.font.size.sm, color: '#fca5a5', padding: '2px 0', paddingLeft: theme.spacing.xl }}>
          &bull; {w}
        </div>
      ))}
    </div>
  );
}
