import React from 'react';
import { useApp } from '../../context/AppContext';
import { useChat } from '../../context/ChatContext';
import { theme } from '../../styles/theme';
import { ChatIcon, DiagnosticsIcon, HistoryIcon, DocumentsIcon, ModelsIcon, SettingsIcon, AnalyticsIcon, NewChatIcon } from '../icons';

const navGroups = [
  {
    label: 'Navigation',
    items: [
      { id: 'chat', label: 'Chat', icon: <ChatIcon /> },
      { id: 'diagnostics', label: 'Diagnostics', icon: <DiagnosticsIcon /> },
      { id: 'history', label: 'History', icon: <HistoryIcon /> },
    ],
  },
  {
    label: 'Management',
    items: [
      { id: 'documents', label: 'Documents', icon: <DocumentsIcon /> },
      { id: 'models', label: 'Models', icon: <ModelsIcon /> },
      { id: 'analytics', label: 'Analytics', icon: <AnalyticsIcon /> },
      { id: 'settings', label: 'Settings', icon: <SettingsIcon /> },
    ],
  },
];

export function Sidebar() {
  const { state, setPage } = useApp();
  const chat = useChat();

  return (
    <div style={{
      width: state.sidebarOpen ? 240 : 0,
      minWidth: state.sidebarOpen ? 240 : 0,
      overflow: 'hidden',
      background: theme.bg.secondary,
      borderRight: `1px solid ${theme.border.primary}`,
      display: 'flex',
      flexDirection: 'column',
      transition: `width ${theme.transition.normal}, min-width ${theme.transition.normal}`,
    }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: `${theme.spacing.sm} 0` }}>
        {navGroups.map((group) => (
          <div key={group.label} style={{ marginBottom: theme.spacing.xs }}>
            <div style={{
              padding: `${theme.spacing.sm} ${theme.spacing.xl}`,
              fontSize: theme.font.size.xs,
              fontWeight: theme.font.weight.semibold,
              textTransform: 'uppercase',
              letterSpacing: '0.8px',
              color: theme.text.dim,
            }}>
              {group.label}
            </div>
            {group.items.map((item) => {
              const active = state.currentPage === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => setPage(item.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: theme.spacing.md,
                    padding: `10px ${theme.spacing.xl}`,
                    cursor: 'pointer',
                    color: active ? theme.accent.blue : theme.text.secondary,
                    background: active ? theme.accent.blueBg : 'transparent',
                    borderLeft: `2px solid ${active ? theme.accent.blue : 'transparent'}`,
                    fontSize: theme.font.size.base,
                    fontWeight: active ? theme.font.weight.medium : theme.font.weight.normal,
                    transition: `all ${theme.transition.fast}`,
                    userSelect: 'none',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = theme.bg.tertiary;
                      e.currentTarget.style.color = theme.text.primary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!active) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = theme.text.secondary;
                    }
                  }}
                >
                  <span style={{ display: 'flex', opacity: active ? 1 : 0.6 }}>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
              );
            })}
          </div>
        ))}

        <div style={{
          padding: `${theme.spacing.sm} ${theme.spacing.xl}`,
          fontSize: theme.font.size.xs,
          fontWeight: theme.font.weight.semibold,
          textTransform: 'uppercase',
          letterSpacing: '0.8px',
          color: theme.text.dim,
        }}>
          Conversations
        </div>
        <div style={{
          maxHeight: 240,
          overflowY: 'auto',
        }}>
          {Object.values(chat.state.conversations).map((conv) => (
            <div
              key={conv.id}
              onClick={() => chat.setActiveConversation(conv.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: theme.spacing.sm,
                padding: `8px ${theme.spacing.xl}`,
                cursor: 'pointer',
                color: chat.state.activeConversationId === conv.id ? theme.text.primary : theme.text.muted,
                background: chat.state.activeConversationId === conv.id ? theme.bg.tertiary : 'transparent',
                borderLeft: `2px solid ${chat.state.activeConversationId === conv.id ? theme.accent.blue : 'transparent'}`,
                fontSize: theme.font.size.sm,
                transition: `all ${theme.transition.fast}`,
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = theme.bg.tertiary; e.currentTarget.style.color = theme.text.primary; }}
              onMouseLeave={(e) => {
                if (chat.state.activeConversationId !== conv.id) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = theme.text.muted;
                }
              }}
            >
              <span style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: theme.font.size.sm,
              }}>
                {conv.title}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div
        onClick={() => chat.newConversation()}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: theme.spacing.md,
          padding: `12px ${theme.spacing.xl}`,
          cursor: 'pointer',
          color: theme.text.secondary,
          borderTop: `1px solid ${theme.border.primary}`,
          fontSize: theme.font.size.base,
          fontWeight: theme.font.weight.medium,
          transition: `all ${theme.transition.fast}`,
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = theme.bg.tertiary; e.currentTarget.style.color = theme.text.primary; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = theme.text.secondary; }}
      >
        <NewChatIcon />
        <span>New Conversation</span>
      </div>
    </div>
  );
}
