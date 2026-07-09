import React from 'react';
import { theme } from '../../styles/theme';

interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  onClick?: () => void;
  hoverable?: boolean;
  selected?: boolean;
}

export function Card({ children, style, onClick, hoverable, selected }: CardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: theme.bg.card,
        borderRadius: theme.radius.lg,
        border: `1px solid ${selected ? theme.accent.blue : theme.border.primary}`,
        padding: theme.spacing.lg,
        transition: `all ${theme.transition.normal}`,
        boxShadow: selected ? `0 0 0 1px ${theme.accent.blue}33, ${theme.shadow.sm}` : theme.shadow.sm,
        cursor: onClick ? 'pointer' : undefined,
        ...(hoverable ? {
          ':hover': { borderColor: theme.accent.blue, boxShadow: theme.shadow.md },
        } : {}),
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      fontSize: theme.font.size.xl,
      fontWeight: theme.font.weight.semibold,
      color: theme.text.primary,
      marginBottom: theme.spacing.md,
      paddingBottom: theme.spacing.sm,
      borderBottom: `1px solid ${theme.border.subtle}`,
      ...style,
    }}>
      {children}
    </div>
  );
}

export function CardBody({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={style}>{children}</div>;
}

export function CardFooter({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      marginTop: theme.spacing.md,
      paddingTop: theme.spacing.sm,
      borderTop: `1px solid ${theme.border.subtle}`,
      display: 'flex',
      gap: theme.spacing.sm,
      alignItems: 'center',
      ...style,
    }}>
      {children}
    </div>
  );
}
