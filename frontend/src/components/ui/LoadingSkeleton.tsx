import React from 'react';
import { theme } from '../../styles/theme';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 12, radius = theme.radius.sm, style }: SkeletonProps) {
  return (
    <div style={{
      width,
      height,
      borderRadius: radius,
      background: `linear-gradient(90deg, ${theme.bg.tertiary} 25%, ${theme.bg.hover} 50%, ${theme.bg.tertiary} 75%)`,
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
      ...style,
    }} />
  );
}

export function CardSkeleton() {
  return (
    <div style={{
      background: theme.bg.card,
      borderRadius: theme.radius.lg,
      border: `1px solid ${theme.border.primary}`,
      padding: theme.spacing.lg,
    }}>
      <Skeleton width="60%" height={16} style={{ marginBottom: theme.spacing.md }} />
      <Skeleton width="100%" height={10} style={{ marginBottom: theme.spacing.sm }} />
      <Skeleton width="90%" height={10} style={{ marginBottom: theme.spacing.sm }} />
      <Skeleton width="75%" height={10} />
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div style={{ padding: theme.spacing['2xl'], display: 'flex', flexDirection: 'column', gap: theme.spacing.lg }}>
      <Skeleton width="200px" height={24} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: theme.spacing.lg }}>
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  );
}
