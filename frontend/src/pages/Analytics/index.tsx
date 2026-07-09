import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { SystemHealth, ReportSummary } from '../../types';
import { Card, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import { theme } from '../../styles/theme';

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

function MetricCard({ label, value, sub, trend, color }: MetricCardProps) {
  return (
    <Card>
      <div style={{ fontSize: theme.font.size.xs, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.xs }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: theme.font.weight.bold, color: color || theme.text.primary, marginBottom: 2 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim }}>{sub}</div>}
      {trend && (
        <div style={{ marginTop: theme.spacing.xs, fontSize: theme.font.size.xs, color: trend === 'up' ? theme.accent.green : trend === 'down' ? theme.accent.red : theme.text.muted }}>
          {trend === 'up' ? '\u2191' : trend === 'down' ? '\u2193' : '\u2192'} {trend === 'up' ? 'Increasing' : trend === 'down' ? 'Decreasing' : 'Stable'}
        </div>
      )}
    </Card>
  );
}

interface BarChartProps {
  data: { label: string; value: number; color?: string }[];
  height?: number;
}

function BarChart({ data, height = 120 }: BarChartProps) {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height, paddingTop: 8 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{
            width: '100%', background: d.color || theme.accent.blue,
            borderRadius: theme.radius.sm, height: `${(d.value / max) * (height - 20)}px`,
            minHeight: 4, transition: `height ${theme.transition.slow}`,
            opacity: 0.8,
          }} />
          <div style={{ fontSize: 9, color: theme.text.dim, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 60 }}>
            {d.label}
          </div>
        </div>
      ))}
    </div>
  );
}

interface AnalyticsData {
  totalDiagnostics: number;
  avgResponseTime: number;
  responseSamples: number;
  indexedDocuments: number;
  totalChunks: number;
  entityCount: number;
  gpuAvailable: boolean;
  gpuName: string | null;
  gpuVram: number;
  ramPercent: number;
  ramTotal: number;
  activeModel: string;
  mostFrequentCodes: { label: string; value: number }[];
  responseTimeTrend: { label: string; value: number }[];
}

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);

  const fetchData = useCallback(async () => {
    try {
      const [health, stats, rep] = await Promise.all([
        api.health.check().catch(() => null),
        api.statistics.get().catch(() => ({ total_diagnostics: 0 })),
        api.reports.list().catch(() => [] as ReportSummary[]),
      ]);
      setReports(rep);

      const h = health as SystemHealth | null;
      const c = h?.components;
      const perf = h?.performance;
      const kb = c?.knowledge_base;
      const gpu = h?.hardware?.gpu;
      const ram = h?.hardware?.ram;

      const codeCounts: Record<string, number> = {};
      rep.forEach(r => {
        const code = r.query.slice(0, 20);
        codeCounts[code] = (codeCounts[code] || 0) + 1;
      });
      const mostFrequent = Object.entries(codeCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([label, value]) => ({ label: label.length > 15 ? label.slice(0, 15) + '...' : label, value }));

      const responseTimeTrend = rep
        .filter(r => r.processing_time_ms > 0)
        .slice(-10)
        .map((r, i) => ({
          label: `#${i + 1}`,
          value: Math.round(r.processing_time_ms / 1000),
        }));

      setData({
        totalDiagnostics: stats.total_diagnostics || rep.length,
        avgResponseTime: perf?.avg_response_time_ms ?? 0,
        responseSamples: perf?.response_samples ?? 0,
        indexedDocuments: kb?.indexed_documents ?? 0,
        totalChunks: kb?.total_chunks ?? 0,
        entityCount: c?.graph?.entity_count ?? 0,
        gpuAvailable: gpu?.available ?? false,
        gpuName: gpu?.name ?? null,
        gpuVram: gpu?.vram_mb ?? 0,
        ramPercent: ram?.percent ?? 0,
        ramTotal: ram?.total_gb ?? 0,
        activeModel: c?.ollama?.active_model ?? 'N/A',
        mostFrequentCodes: mostFrequent.length > 0 ? mostFrequent : [{ label: 'No data', value: 1 }],
        responseTimeTrend: responseTimeTrend.length > 0 ? responseTimeTrend : [{ label: 'No data', value: 1 }],
      });
      setError(null);
    } catch {
      setError('Could not load analytics data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 30000); return () => clearInterval(id); }, [fetchData]);

  if (loading) return <PageSkeleton />;

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: theme.spacing['2xl'] }}>
      <div style={{ fontSize: theme.font.size['3xl'], fontWeight: theme.font.weight.bold, color: theme.text.primary, marginBottom: theme.spacing.xl }}>
        Analytics Dashboard
      </div>

      {error && (
        <div style={{ color: theme.accent.red, fontSize: theme.font.size.sm, marginBottom: theme.spacing.md, padding: theme.spacing.sm, background: theme.accent.redBg, borderRadius: theme.radius.md }}>
          {error}
        </div>
      )}

      {data && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: theme.spacing.md, marginBottom: theme.spacing.xl }}>
            <MetricCard label="Total Diagnostics" value={String(data.totalDiagnostics)} sub="All time" color={theme.accent.blue} />
            <MetricCard label="Avg Response" value={`${data.avgResponseTime.toFixed(0)}ms`} sub={`${data.responseSamples} samples`} color={data.avgResponseTime < 5000 ? theme.accent.green : theme.accent.orange} />
            <MetricCard label="Active Model" value={data.activeModel} sub="Current model" color={theme.accent.cyan} />
            <MetricCard label="Documents Indexed" value={String(data.indexedDocuments)} sub={`${data.totalChunks} chunks total`} color={theme.accent.green} />
            <MetricCard label="RAM Usage" value={`${data.ramPercent}%`} sub={`${data.ramTotal} GB total`} color={data.ramPercent < 80 ? theme.accent.green : theme.accent.orange} />
            <MetricCard label="GPU" value={data.gpuAvailable ? (data.gpuName ?? 'Available') : 'N/A'} sub={data.gpuVram ? `${(data.gpuVram / 1024).toFixed(1)} GB VRAM` : undefined} color={data.gpuAvailable ? theme.accent.green : theme.text.muted} />
            <MetricCard label="Entity Count" value={String(data.entityCount)} sub="Graph entities" color={theme.accent.purple} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: theme.spacing.xl }}>
            <Card>
              <CardHeader>Response Time Trend (last 10)</CardHeader>
              <BarChart data={data.responseTimeTrend} height={140} />
              <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim, marginTop: theme.spacing.sm }}>
                Values in seconds
              </div>
            </Card>

            <Card>
              <CardHeader>Most Frequent Queries</CardHeader>
              <BarChart
                data={data.mostFrequentCodes.map(d => ({ ...d, color: theme.accent.orange }))}
                height={140}
              />
            </Card>

            <Card>
              <CardHeader>Model Latency</CardHeader>
              <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: theme.font.size.sm, color: theme.text.secondary }}>Avg Response Time</span>
                  <span style={{ fontSize: theme.font.size.base, fontWeight: theme.font.weight.semibold, color: theme.accent.blue }}>
                    {data.avgResponseTime.toFixed(0)} ms
                  </span>
                </div>
                <div style={{ height: 8, borderRadius: 4, background: theme.bg.tertiary, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${Math.min((data.avgResponseTime / 10000) * 100, 100)}%`,
                    background: data.avgResponseTime < 5000 ? theme.accent.green : theme.accent.orange,
                    borderRadius: 4, transition: 'width 0.5s',
                  }} />
                </div>
                <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim }}>
                  Threshold: 5000ms &middot; {data.responseSamples} samples
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader>Document Growth</CardHeader>
              <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.sm }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: theme.font.size.sm, color: theme.text.secondary }}>Indexed Documents</span>
                  <span style={{ fontSize: theme.font.size.base, fontWeight: theme.font.weight.semibold, color: theme.accent.green }}>
                    {data.indexedDocuments}
                  </span>
                </div>
                <div style={{ height: 8, borderRadius: 4, background: theme.bg.tertiary, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', width: `${Math.min(data.totalChunks / 50, 100)}%`,
                    background: theme.accent.green, borderRadius: 4, transition: 'width 0.5s',
                  }} />
                </div>
                <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim }}>
                  {data.totalChunks} total chunks &middot; {data.entityCount} entities
                </div>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
