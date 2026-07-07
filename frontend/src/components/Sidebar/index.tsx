import React from "react";
import { useApp } from "../../context/AppContext";
import { useChat } from "../../context/ChatContext";

const pages = [
  { id: "chat", label: "Chat", icon: "\uD83D\uDCAC" },
  { id: "diagnostics", label: "Diagnostics", icon: "\uD83D\uDD0D" },
  { id: "documents", label: "Documents", icon: "\uD83D\uDCC4" },
  { id: "settings", label: "Settings", icon: "\u2699\uFE0F" },
];

function sidebarStyle(open: boolean): React.CSSProperties {
  return {
    width: open ? 220 : 0,
    minWidth: open ? 220 : 0,
    overflow: "hidden",
    background: "#0d1117",
    borderRight: "1px solid #1e2430",
    display: "flex",
    flexDirection: "column",
    transition: "width 0.2s, min-width 0.2s",
  };
}

function navItemStyle(active: boolean): React.CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 16px",
    cursor: "pointer",
    color: active ? "#58a6ff" : "#8b949e",
    background: active ? "#161b22" : "transparent",
    borderLeft: active ? "3px solid #58a6ff" : "3px solid transparent",
    fontSize: 14,
    userSelect: "none",
  };
}

export function Sidebar() {
  const { state, setPage } = useApp();
  const chat = useChat();

  return (
    <div style={sidebarStyle(state.sidebarOpen)}>
      <div
        style={{
          padding: "16px 16px 8px",
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "1px",
          color: "#484f58",
        }}
      >
        Navigation
      </div>
      {pages.map((p) => (
        <div
          key={p.id}
          style={navItemStyle(state.currentPage === p.id)}
          onClick={() => setPage(p.id)}
        >
          <span>{p.icon}</span>
          <span>{p.label}</span>
        </div>
      ))}
      <div
        style={{
          padding: "16px 16px 8px",
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "1px",
          color: "#484f58",
        }}
      >
        Conversations
      </div>
      {Object.values(chat.state.conversations).map((conv) => (
        <div
          key={conv.id}
          style={navItemStyle(chat.state.activeConversationId === conv.id)}
          onClick={() => chat.setActiveConversation(conv.id)}
        >
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {conv.title}
          </span>
        </div>
      ))}
      <div
        style={{
          ...navItemStyle(false),
          marginTop: "auto",
          borderTop: "1px solid #1e2430",
        }}
        onClick={() => chat.newConversation()}
      >
        <span>+</span>
        <span>New Conversation</span>
      </div>
    </div>
  );
}
