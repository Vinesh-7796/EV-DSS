import React from 'react';
import { useApp } from '../../context/AppContext';
import { theme } from '../../styles/theme';

export function Header() {
  const { state } = useApp();
  const connected = state.connectionStatus === 'connected';
  const activeModel = state.config?.reasoning?.model;

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      height: 56,
      padding: `0 ${theme.spacing['2xl']}`,
      background: theme.bg.secondary,
      borderBottom: `1px solid ${theme.border.primary}`,
      gap: theme.spacing.lg,
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: theme.spacing.sm,
        fontSize: theme.font.size['2xl'],
        fontWeight: theme.font.weight.bold,
        color: theme.text.primary,
        letterSpacing: '-0.5px',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={theme.accent.blue} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        EV-DSS
      </div>

      <div style={{ flex: 1 }} />

      {activeModel && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: theme.font.size.sm,
          color: theme.text.muted,
          padding: `5px ${theme.spacing.md}`,
          background: theme.bg.tertiary,
          borderRadius: theme.radius.md,
        }}>
          <span style={{ color: theme.accent.cyan, fontWeight: theme.font.weight.medium }}>{activeModel}</span>
        </div>
      )}

      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: theme.font.size.sm,
        color: connected ? theme.accent.green : theme.accent.red,
        fontWeight: theme.font.weight.medium,
      }}>
        <span style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: connected ? theme.accent.green : theme.accent.red,
          animation: connected ? 'none' : 'pulse 2s infinite',
        }} />
        {connected ? 'Connected' : 'Disconnected'}
      </div>

      <div style={{
        width: 1,
        height: 24,
        background: theme.border.primary,
      }} />

      <div style={{
        fontSize: theme.font.size.xs,
        color: theme.text.dim,
      }}>
        v0.1.0
      </div>
    </header>
  );
}
