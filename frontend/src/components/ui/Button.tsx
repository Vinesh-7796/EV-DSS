import React from 'react';
import { theme } from '../../styles/theme';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'success';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: { background: theme.accent.blue, color: '#fff', border: 'none' },
  secondary: { background: theme.bg.elevated, color: theme.text.secondary, border: `1px solid ${theme.border.primary}` },
  danger: { background: theme.accent.redBg, color: theme.accent.red, border: `1px solid ${theme.accent.redBorder}` },
  ghost: { background: 'transparent', color: theme.text.secondary, border: 'none' },
  success: { background: theme.accent.greenBg, color: theme.accent.green, border: `1px solid ${theme.accent.greenBorder}` },
};

const sizeStyles: Record<string, React.CSSProperties> = {
  sm: { padding: '4px 10px', fontSize: theme.font.size.sm, borderRadius: theme.radius.sm },
  md: { padding: '6px 14px', fontSize: theme.font.size.base, borderRadius: theme.radius.md },
  lg: { padding: '8px 18px', fontSize: theme.font.size.md, borderRadius: theme.radius.md },
};

export function Button({ variant = 'secondary', size = 'sm', loading, disabled, style, children, ...props }: ButtonProps) {
  return (
    <button
      style={{
        fontWeight: theme.font.weight.semibold,
        cursor: loading || disabled ? 'not-allowed' : 'pointer',
        opacity: loading || disabled ? 0.5 : 1,
        transition: `all ${theme.transition.fast}`,
        ...variantStyles[variant],
        ...sizeStyles[size],
        ...style,
      }}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Working...' : children}
    </button>
  );
}
