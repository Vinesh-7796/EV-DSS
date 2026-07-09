import React, { useCallback, useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api';
import type { SystemHealth } from '../../types';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { theme } from '../../styles/theme';

function statusColor(status: string): string {
  if (status === 'healthy' || status === 'connected' || status === 'configured' || status === 'empty') return theme.accent.green;
  if (status === 'degraded') return theme.accent.orange;
  return theme.accent.red;
}

function StatusCard({ label, value, sub, status }: { label: string; value: string; sub?: string; status: string }) {
  return (
    <div style={{
      background: theme.bg.card, borderRadius: theme.radius.md, padding: theme.spacing.md,
      display: 'flex', alignItems: 'center', gap: theme.spacing.sm,
      border: `1px solid ${theme.border.primary}`,
    }}>
      <div style={{ width: 10, height: 10, borderRadius: '50%', background: statusColor(status), flexShrink: 0 }} />
      <div>
        <div style={{ fontSize: theme.font.size.xs, color: theme.text.muted }}>{label}</div>
        <div style={{ fontSize: theme.font.size.base, fontWeight: theme.font.weight.semibold, color: theme.text.primary }}>{value}</div>
        {sub && <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim }}>{sub}</div>}
      </div>
    </div>
  );
}

function ConfigCard({ label, rows }: { label: string; rows: [string, string][] }) {
  return (
    <div style={{ marginBottom: theme.spacing.lg }}>
      <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
        {label}
      </div>
      <Card>
        {rows.map(([k, v]) => (
          <div key={k} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '6px 0', borderBottom: `1px solid ${theme.border.subtle}`,
            fontSize: theme.font.size.sm,
          }}>
            <span style={{ color: theme.text.secondary }}>{k}</span>
            <span style={{ color: theme.accent.blue, fontFamily: theme.font.mono, fontSize: theme.font.size.sm }}>{v}</span>
          </div>
        ))}
      </Card>
    </div>
  );
}

export function SettingsPage() {
  const { state } = useApp();
  const config = state.config;
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setRefreshing(true);
    try { const h = await api.health.check(); setHealth(h as SystemHealth); setLastRefresh(new Date()); }
    catch { /* offline */ }
    finally { setRefreshing(false); }
  }, []);

  useEffect(() => { fetchHealth(); const id = setInterval(fetchHealth, 10000); return () => clearInterval(id); }, [fetchHealth]);

  const c = health?.components;
  const kb = c?.knowledge_base;
  const gpu = health?.hardware?.gpu;
  const ram = health?.hardware?.ram;

  const allSections: { label: string; rows: [string, string][] }[] = [
    {
      label: 'Application',
      rows: [
        ['Name', config?.application.name ?? '\u2014'],
        ['Version', config?.application.version ?? '\u2014'],
        ['Debug', config?.application.debug ? 'true' : 'false'],
      ],
    },
    {
      label: 'Reasoning Engine',
      rows: [
        ['Runtime', config?.reasoning.runtime ?? '\u2014'],
        ['Model', config?.reasoning.model ?? '\u2014'],
        ['Temperature', String(config?.reasoning.temperature ?? '\u2014')],
        ['Max Tokens', String(config?.reasoning.max_tokens ?? '\u2014')],
      ],
    },
    {
      label: 'Retrieval Settings',
      rows: [
        ['Top-K Vector', String(config?.retrieval.top_k_vector ?? '\u2014')],
        ['Top-K Graph', String(config?.retrieval.top_k_graph ?? '\u2014')],
      ],
    },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{
        padding: `14px ${theme.spacing['2xl']}`,
        borderBottom: `1px solid ${theme.border.primary}`,
        flexShrink: 0,
      }}>
        <div style={{ fontSize: theme.font.size['3xl'], fontWeight: theme.font.weight.bold, color: theme.text.primary }}>
          Settings
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: theme.spacing['2xl'] }}>
        {config ? allSections.map(s => <ConfigCard key={s.label} {...s} />) : (
          <div style={{ color: theme.text.muted, fontSize: theme.font.size.sm, marginBottom: theme.spacing.xl }}>
            Loading configuration...
          </div>
        )}

        <div style={{ marginTop: theme.spacing['2xl'] }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.md }}>
            <div style={{ fontSize: theme.font.size.xl, fontWeight: theme.font.weight.semibold, color: theme.text.primary }}>
              System Status
            </div>
            <Button variant="secondary" size="sm" onClick={fetchHealth} loading={refreshing}>
              {refreshing ? '\u2026' : 'Refresh'}
            </Button>
            {lastRefresh && (
              <span style={{ fontSize: theme.font.size.xs, color: theme.text.dim }}>
                Last: {lastRefresh.toLocaleTimeString()}
              </span>
            )}
          </div>

          {health ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: theme.spacing.sm, marginBottom: theme.spacing.md }}>
              <StatusCard label="Backend" value={c?.backend.status === 'healthy' ? 'Healthy' : 'Offline'} sub={`v${c?.backend.version}`} status={c?.backend.status ?? 'offline'} />
              <StatusCard label="Ollama" value={c?.ollama.status ?? 'Offline'} sub={`Model: ${c?.ollama.active_model ?? '\u2014'}`} status={c?.ollama.status ?? 'offline'} />
              <StatusCard label="Vector DB" value={c?.vector_db.status ?? 'Offline'} sub={c?.vector_db.url} status={c?.vector_db.status ?? 'offline'} />
              <StatusCard label="Graph Index" value={c?.graph.status ?? 'Offline'} sub={`${c?.graph.entity_count ?? 0} entities`} status={c?.graph.status ?? 'offline'} />
              <StatusCard label="Knowledge Base" value={kb?.status ?? 'Offline'} sub={`${kb?.indexed_documents ?? 0} docs, ${kb?.total_chunks ?? 0} chunks`} status={kb?.status ?? 'offline'} />
              <StatusCard label="KB Watcher" value={kb?.watcher_running ? 'Active' : 'Inactive'} sub={kb?.last_update ? `Updated: ${kb.last_update.split('T')[0]}` : undefined} status={kb?.watcher_running ? 'healthy' : 'degraded'} />
              <StatusCard label="Embedding" value={c?.embedding.model ?? '\u2014'} sub={`dim=${c?.embedding.dimension ?? 0}`} status={c?.embedding.status ?? 'degraded'} />
              <StatusCard label="Avg Response" value={`${health.performance.avg_response_time_ms.toFixed(0)} ms`} sub={`${health.performance.response_samples} samples`} status={health.performance.avg_response_time_ms < 5000 ? 'healthy' : 'degraded'} />
              <StatusCard label="GPU" value={gpu?.available ? (gpu.name ?? 'Detected') : 'Not Available'} sub={gpu?.available && gpu.vram_mb ? `${(gpu.vram_mb / 1024).toFixed(1)} GB VRAM` : undefined} status={gpu?.available ? 'healthy' : 'degraded'} />
              <StatusCard label="RAM" value={ram?.total_gb ? `${ram.total_gb} GB total` : '\u2014'} sub={ram?.used_gb ? `${ram.used_gb} GB used (${ram.percent}%)` : undefined} status={ram?.percent !== undefined ? (ram.percent < 80 ? 'healthy' : 'degraded') : 'degraded'} />
            </div>
          ) : (
            <Card>
              <div style={{ color: theme.text.muted, fontSize: theme.font.size.sm }}>
                {refreshing ? 'Fetching system status...' : 'Backend offline - cannot retrieve system status.'}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
