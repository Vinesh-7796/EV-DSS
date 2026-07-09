import React from 'react';
import { theme } from '../../styles/theme';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon = '📋', title, description, action }: EmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: theme.spacing['3xl'] * 2,
      color: theme.text.muted,
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 32, marginBottom: theme.spacing.md }}>{icon}</div>
      <div style={{ fontSize: theme.font.size.md, fontWeight: theme.font.weight.semibold, color: theme.text.secondary, marginBottom: theme.spacing.sm }}>
        {title}
      </div>
      {description && (
        <div style={{ fontSize: theme.font.size.sm, color: theme.text.muted, maxWidth: 360, lineHeight: 1.5 }}>
          {description}
        </div>
      )}
      {action && <div style={{ marginTop: theme.spacing.lg }}>{action}</div>}
    </div>
  );
}
