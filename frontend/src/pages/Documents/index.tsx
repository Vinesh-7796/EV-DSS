import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { KBDocument, KBStatus, IngestionLogEntry } from '../../types';
import { Card, CardHeader, CardFooter } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { SearchBar } from '../../components/ui/SearchBar';
import { EmptyState } from '../../components/ui/EmptyState';
import { PageSkeleton } from '../../components/ui/LoadingSkeleton';
import { theme } from '../../styles/theme';

const typeVariant = (type: string): 'blue' | 'green' | 'orange' | 'purple' | 'gray' => {
  const map: Record<string, 'blue' | 'green' | 'orange' | 'purple' | 'gray'> = {
    pdf: 'blue', xlsx: 'green', dbc: 'orange', png: 'purple', jpg: 'purple',
  };
  return map[type] || 'gray';
};

const statusVariant = (status: string): 'green' | 'orange' | 'red' | 'gray' => {
  const map: Record<string, 'green' | 'orange' | 'red' | 'gray'> = {
    indexed: 'green', processing: 'orange', error: 'red',
  };
  return map[status] || 'gray';
};

function fmtBytes(b: number): string {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

function fmtDate(iso: string): string {
  if (!iso) return '\u2014';
  try { return new Date(iso).toLocaleDateString(); } catch { return iso; }
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [kbStatus, setKbStatus] = useState<KBStatus | null>(null);
  const [log, setLog] = useState<IngestionLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [d, st, l] = await Promise.all([
        api.kb.documents(),
        api.kb.status(),
        api.kb.log(30),
      ]);
      setDocs(d);
      setKbStatus(st);
      setLog(l);
      setError(null);
    } catch {
      setError('Could not reach backend');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); const id = setInterval(load, 20000); return () => clearInterval(id); }, [load]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try { await api.kb.refresh(); await load(); } finally { setRefreshing(false); }
  };

  const handleDelete = async (filename: string) => {
    try { await api.kb.deleteDocument(filename); setConfirmDelete(null); await load(); }
    catch (e) { setError(`Delete failed: ${e instanceof Error ? e.message : 'error'}`); }
  };

  const handleReindex = async (filename: string) => {
    try { await api.kb.reindex(filename); await load(); }
    catch (e) { setError(`Re-index failed: ${e instanceof Error ? e.message : 'error'}`); }
  };

  const filtered = docs.filter(d =>
    d.filename.toLowerCase().includes(search.toLowerCase()) ||
    d.type.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) return <PageSkeleton />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: theme.spacing.sm,
        padding: `${theme.spacing.md} ${theme.spacing['2xl']}`,
        borderBottom: `1px solid ${theme.border.primary}`,
        flexShrink: 0, flexWrap: 'wrap',
      }}>
        <div style={{ fontSize: theme.font.size['3xl'], fontWeight: theme.font.weight.bold, color: theme.text.primary, marginRight: 'auto' }}>
          Documents
        </div>
        <SearchBar value={search} onChange={setSearch} placeholder="Filter documents..." style={{ width: 240 }} />
        <Button variant="secondary" onClick={handleRefresh} loading={refreshing}>Refresh All</Button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: theme.spacing['2xl'] }}>
        {error && (
          <div style={{ color: theme.accent.red, fontSize: theme.font.size.sm, marginBottom: theme.spacing.md, padding: theme.spacing.sm, background: theme.accent.redBg, borderRadius: theme.radius.md }}>
            {error}
          </div>
        )}

        {filtered.length === 0 ? (
          <EmptyState
            icon="📂"
            title={search ? 'No documents match your filter' : 'No indexed documents'}
            description="Run the ingestion pipeline or drop files into the data/raw/ folder."
            action={<Button variant="primary" onClick={handleRefresh}>Refresh</Button>}
          />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: theme.spacing.md }}>
            {filtered.map((doc) => (
              <Card key={doc.filename} hoverable>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: theme.spacing.md }}>
                  <div>
                    <div style={{ fontWeight: theme.font.weight.semibold, color: theme.text.primary, marginBottom: 4, wordBreak: 'break-all' }}>
                      {doc.file_exists ? '' : '\u26A0 '}{doc.filename}
                    </div>
                    <div style={{ display: 'flex', gap: 4, marginTop: theme.spacing.xs }}>
                      <Badge variant={typeVariant(doc.type)}>{doc.type.toUpperCase()}</Badge>
                      <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
                    </div>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: theme.spacing.xs, fontSize: theme.font.size.sm, color: theme.text.muted }}>
                  <span>Size: {fmtBytes(doc.file_size)}</span>
                  <span>Indexed: {fmtDate(doc.last_indexed)}</span>
                  <span>Chunks: {doc.chunks}</span>
                  <span>Nodes: {doc.nodes}</span>
                </div>
                <CardFooter>
                  <Button variant="secondary" size="sm" onClick={() => handleReindex(doc.filename)}>Re-index</Button>
                  <Button variant="danger" size="sm" onClick={() => setConfirmDelete(doc.filename)}>Delete</Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}

        {log.length > 0 && (
          <div style={{ marginTop: theme.spacing['2xl'] }}>
            <div style={{ fontSize: theme.font.size.sm, fontWeight: theme.font.weight.semibold, color: theme.text.muted, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: theme.spacing.sm }}>
              Ingestion Activity Log
            </div>
            <div style={{
              background: theme.bg.card, borderRadius: theme.radius.md, padding: theme.spacing.md,
              maxHeight: 160, overflowY: 'auto', fontSize: theme.font.size.sm, fontFamily: theme.font.mono,
            }}>
              {[...log].reverse().map((e, i) => (
                <div key={i} style={{ padding: '2px 0', color: theme.text.muted }}>
                  <span style={{ color: theme.text.dim }}>[{e.timestamp.split('T')[1]?.slice(0, 8)}]</span>{' '}
                  <span style={{ color: theme.accent.blue }}>{e.event.toUpperCase()}</span>{' '}
                  <strong style={{ color: theme.text.secondary }}>{e.filename}</strong>{' '}
                  &rarr; <span style={{
                    color: e.status === 'done' ? theme.accent.green : e.status === 'failed' ? theme.accent.red : theme.accent.orange
                  }}>{e.status}</span>
                  {e.detail && <span style={{ color: theme.text.dim }}> &mdash; {e.detail}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{
        display: 'flex', gap: theme.spacing.lg,
        padding: `${theme.spacing.sm} ${theme.spacing['2xl']}`,
        borderTop: `1px solid ${theme.border.primary}`,
        background: theme.bg.secondary,
        fontSize: theme.font.size.xs, color: theme.text.muted, flexShrink: 0,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: kbStatus?.watcher_running ? theme.accent.green : theme.accent.red }} />
          Watcher: {kbStatus?.watcher_running ? 'Active' : 'Inactive'}
        </span>
        <span>{kbStatus?.indexed_files ?? 0} indexed</span>
        <span>{kbStatus?.queue_depth ?? 0} queued</span>
        <span>{kbStatus?.total_processed ?? 0} processed</span>
      </div>

      {confirmDelete && (
        <div style={{
          position: 'fixed', inset: 0, background: theme.bg.overlay,
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 999,
        }}>
          <Card style={{ maxWidth: 380, width: '90%' }}>
            <div style={{ fontWeight: theme.font.weight.bold, color: theme.text.primary, marginBottom: theme.spacing.sm }}>Remove Document?</div>
            <div style={{ color: theme.text.muted, fontSize: theme.font.size.sm, marginBottom: theme.spacing.lg }}>
              Remove <strong style={{ color: theme.accent.red }}>{confirmDelete}</strong> from all indexes. The raw file will not be deleted.
            </div>
            <div style={{ display: 'flex', gap: theme.spacing.sm, justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={() => setConfirmDelete(null)}>Cancel</Button>
              <Button variant="danger" onClick={() => handleDelete(confirmDelete)}>Remove</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
