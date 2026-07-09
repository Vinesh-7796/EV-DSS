import React, { useRef, useEffect } from 'react';
import type { ChatMessage } from '../../types';
import { MessageBubble } from '../MessageBubble';
import { theme } from '../../styles/theme';

interface Props {
  messages: ChatMessage[];
  isProcessing?: boolean;
  onCopy?: (content: string) => void;
}

export function ChatWindow({ messages, isProcessing, onCopy }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  if (messages.length === 0) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflowY: 'auto',
      }}>
        <div style={{
          textAlign: 'center',
          color: theme.text.muted,
          maxWidth: 400,
        }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke={theme.text.dim} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: theme.spacing.lg }}>
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <div style={{ fontSize: theme.font.size.md, fontWeight: theme.font.weight.medium, color: theme.text.secondary, marginBottom: theme.spacing.sm }}>
            Start a diagnostic session
          </div>
          <div style={{ fontSize: theme.font.size.sm, color: theme.text.muted, lineHeight: 1.6 }}>
            Describe the vehicle issue below. The system will analyze fault codes, cross-reference technical documentation, and provide structured diagnostic guidance.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: `${theme.spacing.xl} ${theme.spacing['3xl']}`,
    }}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} onCopy={onCopy} />
      ))}
      {isProcessing && (
        <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: theme.spacing.lg, animation: 'fadeIn 0.2s ease' }}>
          <div style={{
            display: 'flex',
            gap: 6,
            padding: '12px 20px',
            background: theme.bg.card,
            borderRadius: theme.radius.lg,
          }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: theme.accent.blue,
                opacity: 0.4,
                animation: 'pulse 1.2s infinite',
                animationDelay: `${i * 0.2}s`,
              }} />
            ))}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
