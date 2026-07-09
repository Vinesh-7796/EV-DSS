import React from 'react';
import { theme } from '../../styles/theme';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  style?: React.CSSProperties;
}

export function SearchBar({ value, onChange, placeholder = 'Search...', style }: SearchBarProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: theme.spacing.sm,
      background: theme.bg.secondary,
      border: `1px solid ${theme.border.primary}`,
      borderRadius: theme.radius.md,
      padding: `0 ${theme.spacing.md}`,
      transition: `border-color ${theme.transition.fast}`,
      ...style,
    }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={theme.text.muted} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
      </svg>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          flex: 1,
          background: 'none',
          border: 'none',
          color: theme.text.primary,
          fontSize: theme.font.size.sm,
          padding: '7px 0',
          outline: 'none',
          fontFamily: theme.font.family,
        }}
      />
    </div>
  );
}
