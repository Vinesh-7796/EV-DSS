import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { ReportSummary, ReportDetail, DiagnosticResult } from '../../types';
import { Card, CardFooter } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { SearchBar } from '../../components/ui/SearchBar';
import { EmptyState } from '../../components/ui/EmptyState';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import { theme } from '../../styles/theme';

function confidenceBadge(level: string): 'green' | 'orange' | 'red' | 'gray' {
  const map: Record<string, 'green' | 'orange' | 'red' | 'gray'> = {
    HIGH: 'green', MEDIUM: 'orange', LOW: 'red',
  };
  return map[level] || 'gray';
}

function fmtDate(iso: string) {
  try { return new Date(iso).toLocaleDateString(); } catch { return iso; }
}

export function HistoryPage() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [filtered, setFiltered] = useState<ReportSummary[]>([]);
  const [selected, setSelected] = useState<ReportDetail | null>(null);
  const [searchQ, setSearchQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [rerunResult, setRerunResult] = useState<DiagnosticResult | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.reports.list();
      setReports(r);
      setFiltered(r);
      setError(null);
    } catch {
      setError('Could not load reports');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!searchQ.trim()) { setFiltered(reports); return; }
    const q = searchQ.toLowerCase();
    setFiltered(reports.filter(
      r => r.query.toLowerCase().includes(q) || r.problem_summary.toLowerCase().includes(q)
    ));
  }, [searchQ, reports]);

  const openReport = async (id: string) => {
    setRerunResult(null);
    try { const d = await api.reports.get(id); setSelected(d); }
    catch { setError('Could not load report'); }
  };

  const handleDelete = async () => {
    if (!selected) return;
    setDeleting(true);
    try { await api.reports.delete(selected.metadata.id); setSelected(null); await load(); }
    catch { setError('Delete failed'); }
    finally { setDeleting(false); }
  };

  const handleRerun = async () => {
    if (!selected) return;
    setRerunning(true); setRerunResult(null);
    try { const res = await api.reports.rerun(selected.metadata.id); setRerunResult(res.diagnostic_result); }
    catch { setError('Re-run failed'); }
    finally { setRerunning(false); }
  };

  const handleOpenLocation = async () => {
    if (!selected) return;
    try { const loc = await api.reports.location(selected.metadata.id); alert(`Location:\n${loc.absolute_path}`); }
    catch { setError('Could not get location'); }
  };

  if (loading) return <PageSkeleton />;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        width: 340, minWidth: 340, display: 'flex', flexDirection: 'column',
        borderRight: `1px solid ${theme.border.primary}`,
      }}>
        <div style={{
          padding: theme.spacing.lg, borderBottom: `1px solid ${theme.border.primary}`, flexShrink: 0,
        }}>
          <div style={{ fontSize: theme.font.size.xl, fontWeight: theme.font.weight.semibold, color: theme.text.primary, marginBottom: theme.spacing.sm }}>
            History
          </div>
          <SearchBar value={searchQ} onChange={setSearchQ} placeholder="Search reports..." />
          {error && <div style={{ color: theme.accent.red, fontSize: theme.font.size.xs, marginTop: theme.spacing.xs }}>{error}</div>}
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {filtered.length === 0 ? (
            <div style={{ padding: theme.spacing.xl, textAlign: 'center', color: theme.text.muted, fontSize: theme.font.size.sm }}>
              {searchQ ? 'No reports match your search.' : 'No diagnostic reports yet.'}
            </div>
          ) : (
            filtered.map(r => (
              <div
                key={r.id}
                onClick={() => openReport(r.id)}
                style={{
                  padding: theme.spacing.md,
                  cursor: 'pointer',
                  borderLeft: `3px solid ${selected?.metadata.id === r.id ? theme.accent.blue : 'transparent'}`,
                  background: selected?.metadata.id === r.id ? theme.bg.tertiary : 'transparent',
                  borderBottom: `1px solid ${theme.border.subtle}`,
                  transition: `background ${theme.transition.fast}`,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = theme.bg.card; }}
                onMouseLeave={(e) => {
                  if (selected?.metadata.id !== r.id) e.currentTarget.style.background = 'transparent';
                }}
              >
                <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.medium, color: theme.text.primary, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.query}
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: theme.font.size.xs, color: theme.text.muted }}>
                  <Badge variant={confidenceBadge(r.confidence_level)}>
                    {r.confidence_level} {(r.confidence_score * 100).toFixed(0)}%
                  </Badge>
                  <span>{fmtDate(r.timestamp)}</span>
                  <span>&middot;</span>
                  <span>{r.model}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selected ? (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', gap: theme.spacing.sm,
              padding: `${theme.spacing.md} ${theme.spacing.lg}`,
              borderBottom: `1px solid ${theme.border.primary}`, flexShrink: 0,
            }}>
              <span style={{ color: theme.text.secondary, fontSize: theme.font.size.sm, marginRight: 'auto', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selected.metadata.query}
              </span>
              <Button variant="success" size="sm" onClick={handleRerun} loading={rerunning}>Re-run</Button>
              <Button variant="secondary" size="sm" onClick={handleOpenLocation}>Location</Button>
              <Button variant="danger" size="sm" onClick={handleDelete} loading={deleting}>Delete</Button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: theme.spacing['2xl'] }}>
              {rerunResult ? (
                <Card>
                  <div style={{
                    background: theme.accent.greenBg, border: `1px solid ${theme.accent.greenBorder}`,
                    borderRadius: theme.radius.sm, padding: theme.spacing.sm, marginBottom: theme.spacing.md,
                    color: theme.accent.green, fontSize: theme.font.size.sm,
                  }}>
                    Re-run complete &mdash; model: {rerunResult.active_model} &middot; confidence: {rerunResult.confidence?.level} ({(rerunResult.confidence?.overall_score * 100).toFixed(0)}%)
                  </div>
                  <div style={{ fontSize: theme.font.size.base, color: theme.text.primary, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                    {rerunResult.problem_summary}
                    {'\n\nCauses:\n'}
                    {rerunResult.possible_causes?.map((c, i) => `${i + 1}. ${c}`).join('\n')}
                  </div>
                </Card>
              ) : (
                <Card>
                  <div style={{ fontSize: theme.font.size.sm, color: theme.text.secondary, lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: theme.font.mono }}>
                    {selected.markdown || 'No content available.'}
                  </div>
                </Card>
              )}
            </div>
          </>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
            <EmptyState icon="🕒" title="Select a report" description="Choose a diagnostic report from the list to view details." />
          </div>
        )}
      </div>
    </div>
  );
}
