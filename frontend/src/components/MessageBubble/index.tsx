import React from 'react';
import type { ChatMessage } from '../../types';
import { ConfidencePanel } from '../ConfidencePanel';
import { SafetyWarnings } from '../SafetyWarnings';
import { theme } from '../../styles/theme';
import { CopyIcon } from '../icons';

interface Props {
  message: ChatMessage;
  onCopy?: (content: string) => void;
}

const headingStyle: React.CSSProperties = {
  fontSize: theme.font.size.lg,
  fontWeight: theme.font.weight.semibold,
  color: theme.text.primary,
  marginBottom: theme.spacing.sm,
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: theme.font.size.sm,
  fontWeight: theme.font.weight.semibold,
  color: theme.text.muted,
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  marginBottom: theme.spacing.xs,
};

const listItemStyle: React.CSSProperties = {
  fontSize: theme.font.size.base,
  color: theme.text.secondary,
  padding: '3px 0',
  marginLeft: theme.spacing.lg,
  lineHeight: 1.5,
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  if (!children) return null;
  return (
    <div style={{ marginBottom: theme.spacing.md }}>
      <div style={sectionTitleStyle}>{title}</div>
      {children}
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Section title={title}>
      {items.map((item, i) => (
        <div key={i} style={listItemStyle}>&bull; {item}</div>
      ))}
    </Section>
  );
}

function TagSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Section title={title}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {items.map((item, i) => (
          <span key={i} style={{
            fontSize: theme.font.size.xs,
            padding: '2px 8px',
            borderRadius: theme.radius.sm,
            background: theme.bg.tertiary,
            color: theme.text.muted,
          }}>
            {item}
          </span>
        ))}
      </div>
    </Section>
  );
}

function DiagnosticView({ d }: { d: NonNullable<ChatMessage['diagnostic']> }) {
  return (
    <div style={{ marginTop: theme.spacing.md, borderTop: `1px solid ${theme.border.subtle}`, paddingTop: theme.spacing.md }}>
      <Section title="Fault Summary">
        <div style={{ fontSize: theme.font.size.base, color: theme.text.primary, lineHeight: 1.6 }}>
          {d.problem_summary}
        </div>
      </Section>
      <ListSection title="Possible Causes" items={d.possible_causes} />
      <ListSection title="Inspection Steps" items={d.inspection_steps} />
      <ListSection title="Recommended Actions" items={d.recommended_actions} />
      <TagSection title="Related Components" items={d.related_components} />
      <TagSection title="Connectors" items={d.connectors} />
      <SafetyWarnings warnings={d.safety_warnings} />
      <ConfidencePanel
        confidence={d.confidence}
        evidence={d.evidence}
        citations={d.citations}
      />
    </div>
  );
}

export function MessageBubble({ message, onCopy }: Props) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: theme.spacing.xl,
      animation: 'fadeIn 0.25s ease',
    }}>
      <div style={{
        maxWidth: isUser ? '60%' : '78%',
        borderRadius: theme.radius.lg,
        padding: isUser ? `${theme.spacing.md} ${theme.spacing.lg}` : 0,
      }}>
        {isUser ? (
          <div style={{
            background: theme.accent.blueBg,
            border: `1px solid ${theme.accent.blueBorder}`,
            borderRadius: theme.radius.lg,
            padding: `12px 18px`,
          }}>
            <div style={{ fontSize: theme.font.size.md, color: theme.text.primary, lineHeight: 1.5 }}>
              {message.content}
            </div>
            <div style={{ fontSize: theme.font.size.xs, color: theme.text.dim, marginTop: theme.spacing.xs, textAlign: 'right' }}>
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        ) : (
          <div style={{
            background: theme.bg.card,
            border: `1px solid ${theme.border.primary}`,
            borderRadius: theme.radius.lg,
            padding: `18px 20px`,
            boxShadow: theme.shadow.sm,
          }}>
            <div style={headingStyle}>
              Diagnostic Report
              {message.diagnostic?.processing_time_ms && (
                <span style={{ fontSize: theme.font.size.xs, fontWeight: theme.font.weight.normal, color: theme.text.muted, marginLeft: theme.spacing.sm }}>
                  {(message.diagnostic.processing_time_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>
            <div style={{ fontSize: theme.font.size.base, color: theme.text.primary, lineHeight: 1.6, marginBottom: theme.spacing.md }}>
              {message.content}
            </div>
            {message.diagnostic && <DiagnosticView d={message.diagnostic} />}
            {onCopy && (
              <button
                onClick={() => onCopy(message.content)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  background: 'none',
                  border: 'none',
                  color: theme.text.muted,
                  cursor: 'pointer',
                  fontSize: theme.font.size.xs,
                  padding: 0,
                  marginTop: theme.spacing.sm,
                  transition: `color ${theme.transition.fast}`,
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = theme.text.secondary; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = theme.text.muted; }}
              >
                <CopyIcon /> Copy
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
