import React from 'react';
import { Card } from '../ui/Card';
import { theme } from '../../styles/theme';

interface Props {
  status: string;
  stages?: { name: string; status: string; duration_ms?: number }[];
}

const stageColors: Record<string, string> = {
  COMPLETED: theme.accent.green,
  PASSED: theme.accent.green,
  FAILED: theme.accent.red,
  WARNING: theme.accent.orange,
  RUNNING: theme.accent.blue,
  PENDING: theme.text.dim,
};

export function ProcessingStatus({ status, stages }: Props) {
  return (
    <Card>
      <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
        Processing Status
      </div>
      <div style={{ fontSize: theme.font.size.base, fontWeight: theme.font.weight.semibold, color: stageColors[status] || theme.accent.blue, marginBottom: theme.spacing.md }}>
        {status}
      </div>
      {stages?.map((s, i) => (
        <div key={i} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '5px 0', borderBottom: `1px solid ${theme.border.subtle}`,
          fontSize: theme.font.size.sm,
        }}>
          <span style={{ color: theme.text.secondary }}>{s.name}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm }}>
            <span style={{ color: stageColors[s.status] || theme.text.muted, fontWeight: theme.font.weight.medium }}>
              {s.status}
            </span>
            {s.duration_ms !== undefined && (
              <span style={{ color: theme.text.dim, fontSize: theme.font.size.xs }}>
                {(s.duration_ms).toFixed(0)}ms
              </span>
            )}
          </span>
        </div>
      ))}
    </Card>
  );
}
