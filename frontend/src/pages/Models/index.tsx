import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import type { OllamaModel, ActiveModelInfo, HardwareRecommendations, PullProgress } from '../../types';
import { Card, CardHeader, CardFooter } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import { theme } from '../../styles/theme';

export function ModelsPage() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [activeInfo, setActiveInfo] = useState<ActiveModelInfo | null>(null);
  const [hw, setHw] = useState<HardwareRecommendations | null>(null);
  const [loading, setLoading] = useState(true);
  const [pullModel, setPullModel] = useState('');
  const [pulling, setPulling] = useState(false);
  const [pullLog, setPullLog] = useState<PullProgress[]>([]);
  const [pullPercent, setPullPercent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState<string | null>(null);
  const [confirmActivate, setConfirmActivate] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, a, h] = await Promise.all([
        api.models.list(),
        api.models.active(),
        api.models.hardware(),
      ]);
      setModels(m); setActiveInfo(a); setHw(h);
      setError(null);
    } catch {
      setError('Could not reach model manager');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleActivate = async (modelName: string) => {
    setActivating(modelName); setConfirmActivate(null);
    try { await api.models.activate(modelName); await load(); }
    catch (e) { setError(`Activation failed: ${e instanceof Error ? e.message : 'error'}`); }
    finally { setActivating(null); }
  };

  const handlePull = async () => {
    if (!pullModel.trim()) return;
    setPulling(true); setPullLog([]); setPullPercent(0);
    try {
      const resp = await fetch('/api/models/pull', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: pullModel.trim() }),
      });
      const reader = resp.body?.getReader();
      if (!reader) throw new Error('No stream');
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        for (const line of text.split('\n')) {
          const trimmed = line.replace(/^data: /, '').trim();
          if (!trimmed) continue;
          try {
            const parsed: PullProgress = JSON.parse(trimmed);
            setPullLog(prev => [...prev.slice(-30), parsed]);
            if (parsed.total && parsed.completed) setPullPercent(Math.round((parsed.completed / parsed.total) * 100));
            if (parsed.status === 'success') setPullPercent(100);
          } catch { /* skip */ }
        }
      }
      await load(); setPullModel('');
    } catch (e) {
      setError(`Pull failed: ${e instanceof Error ? e.message : 'error'}`);
    } finally { setPulling(false); }
  };

  if (loading) return <PageSkeleton />;

  const isActive = (name: string) => name === activeInfo?.active_model;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: theme.spacing.sm,
        padding: `${theme.spacing.md} ${theme.spacing['2xl']}`,
        borderBottom: `1px solid ${theme.border.primary}`, flexShrink: 0,
      }}>
        <div style={{ fontSize: theme.font.size['3xl'], fontWeight: theme.font.weight.bold, color: theme.text.primary, marginRight: 'auto' }}>
          Models
        </div>
        <Button variant="secondary" onClick={load}>Refresh</Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: theme.spacing['2xl'] }}>
        {error && (
          <div style={{ color: theme.accent.red, fontSize: theme.font.size.sm, marginBottom: theme.spacing.md, padding: theme.spacing.sm, background: theme.accent.redBg, borderRadius: theme.radius.md }}>
            {error}
          </div>
        )}

        {hw && (
          <Card style={{ marginBottom: theme.spacing.md }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: theme.spacing.sm, fontSize: theme.font.size.sm, color: theme.text.secondary }}>
              <span style={{ fontWeight: theme.font.weight.semibold, color: theme.text.primary }}>Hardware:</span>
              {hw.gpu_name} ({hw.gpu_vram_gb}GB VRAM) &middot; {hw.ram_gb}GB RAM
              <Badge variant="blue">{hw.recommendation}</Badge>
            </div>
          </Card>
        )}

        {activeInfo && (
          <Card style={{ marginBottom: theme.spacing.lg }}>
            <CardHeader>Active Configuration</CardHeader>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: theme.spacing.md }}>
              {[
                ['Model', activeInfo.active_model],
                ['Runtime', activeInfo.runtime],
                ['Size', activeInfo.details?.size_formatted ?? '\u2014'],
                ['Quantization', activeInfo.details?.quantization ?? '\u2014'],
              ].map(([label, val]) => (
                <div key={label}>
                  <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 2 }}>{label}</div>
                  <div style={{ fontFamily: theme.font.mono, fontSize: theme.font.size.base, color: theme.accent.blue }}>{val}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <div style={{ marginBottom: theme.spacing.lg }}>
          <div style={{ fontSize: theme.font.size.xl, fontWeight: theme.font.weight.semibold, color: theme.text.primary, marginBottom: theme.spacing.md }}>
            Installed Models ({models.length})
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: theme.spacing.md }}>
            {models.length === 0 ? (
              <Card>
                <div style={{ color: theme.text.muted, fontSize: theme.font.size.sm }}>
                  No models found. Ensure Ollama is running.
                </div>
              </Card>
            ) : (
              models.map((m) => {
                const active = isActive(m.name);
                return (
                  <Card key={m.name} hoverable selected={active}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: theme.spacing.sm }}>
                      <div>
                        <div style={{ fontWeight: theme.font.weight.semibold, color: theme.text.primary }}>
                          {m.name}
                          {active && <Badge variant="green" style={{ marginLeft: 6 }}>Active</Badge>}
                          {m.is_recommended && <Badge variant="blue" style={{ marginLeft: 4 }}>Recommended</Badge>}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: theme.spacing.xs, fontSize: theme.font.size.sm, color: theme.text.muted }}>
                      <span>Family: {m.family || '\u2014'}</span>
                      <span>Size: {m.size_formatted}</span>
                      <span>Quant: {m.quantization}</span>
                      <span>Modified: {m.modified_date ? m.modified_date.split('T')[0] : '\u2014'}</span>
                    </div>
                    <CardFooter>
                      {active ? (
                        <Badge variant="green">In Use</Badge>
                      ) : (
                        <Button
                          variant="primary"
                          size="sm"
                          loading={activating === m.name}
                          onClick={() => setConfirmActivate(m.name)}
                        >
                          Activate
                        </Button>
                      )}
                    </CardFooter>
                  </Card>
                );
              })
            )}
          </div>
        </div>

        <Card>
          <CardHeader>Download New Model</CardHeader>
          <div style={{ display: 'flex', gap: theme.spacing.sm, alignItems: 'center' }}>
            <input
              style={{
                flex: 1, padding: '8px 12px', borderRadius: theme.radius.md,
                border: `1px solid ${theme.border.primary}`, background: theme.bg.primary,
                color: theme.text.primary, fontSize: theme.font.size.sm, outline: 'none',
              }}
              placeholder="e.g. llama3.2:3b or qwen3:8b"
              value={pullModel}
              onChange={e => setPullModel(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !pulling && handlePull()}
              disabled={pulling}
            />
            <Button variant="success" onClick={handlePull} loading={pulling} disabled={!pullModel.trim()}>
              Pull
            </Button>
          </div>
          {pulling && (
            <div style={{ marginTop: theme.spacing.md }}>
              <div style={{ height: 6, borderRadius: 3, background: theme.bg.tertiary, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pullPercent}%`, background: theme.accent.green, transition: 'width 0.3s' }} />
              </div>
              <div style={{ marginTop: theme.spacing.sm, maxHeight: 100, overflowY: 'auto', fontFamily: theme.font.mono, fontSize: theme.font.size.xs, color: theme.text.muted }}>
                {pullLog.map((p, i) => (
                  <div key={i}>
                    {p.status}
                    {p.total && p.completed ? ` \u2014 ${(p.completed / 1024 / 1024).toFixed(1)}MB / ${(p.total / 1024 / 1024).toFixed(1)}MB` : ''}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {confirmActivate && (
        <div style={{
          position: 'fixed', inset: 0, background: theme.bg.overlay,
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999,
        }}>
          <Card style={{ maxWidth: 380, width: '90%' }}>
            <div style={{ fontWeight: theme.font.weight.bold, color: theme.text.primary, marginBottom: theme.spacing.sm }}>Switch Active Model?</div>
            <div style={{ color: theme.text.muted, fontSize: theme.font.size.sm, marginBottom: theme.spacing.lg }}>
              Switch to <strong style={{ color: theme.accent.blue }}>{confirmActivate}</strong>? Next query will use the new model.
            </div>
            <div style={{ display: 'flex', gap: theme.spacing.sm, justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={() => setConfirmActivate(null)}>Cancel</Button>
              <Button variant="primary" onClick={() => handleActivate(confirmActivate)}>Confirm</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
