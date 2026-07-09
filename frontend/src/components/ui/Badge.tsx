import React from 'react';
import { theme } from '../../styles/theme';

type BadgeVariant = 'green' | 'orange' | 'red' | 'blue' | 'gray' | 'purple' | 'cyan';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  style?: React.CSSProperties;
}

const badgeColors: Record<BadgeVariant, { bg: string; fg: string }> = {
  green: { bg: theme.accent.greenBg, fg: theme.accent.green },
  orange: { bg: theme.accent.orangeBg, fg: theme.accent.orange },
  red: { bg: theme.accent.redBg, fg: theme.accent.red },
  blue: { bg: theme.accent.blueBg, fg: theme.accent.blue },
  gray: { bg: theme.bg.tertiary, fg: theme.text.muted },
  purple: { bg: theme.accent.purpleBg, fg: theme.accent.purple },
  cyan: { bg: theme.accent.cyanBg, fg: theme.accent.cyan },
};

export function Badge({ variant = 'gray', children, style }: BadgeProps) {
  const c = badgeColors[variant];
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '2px 8px',
      borderRadius: theme.radius.full,
      fontSize: theme.font.size.xs,
      fontWeight: theme.font.weight.semibold,
      background: c.bg,
      color: c.fg,
      lineHeight: 1.4,
      ...style,
    }}>
      {children}
    </span>
  );
}
