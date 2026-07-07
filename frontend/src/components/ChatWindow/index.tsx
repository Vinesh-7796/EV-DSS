import React, { useRef, useEffect } from "react";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "../MessageBubble";

interface Props {
  messages: ChatMessage[];
  isProcessing?: boolean;
  onCopy?: (content: string) => void;
}

const style: Record<string, React.CSSProperties> = {
  container: {
    flex: 1,
    overflowY: "auto",
    padding: "16px 24px",
  },
  empty: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    color: "#484f58",
    fontSize: 14,
    textAlign: "center",
  },
  typing: {
    display: "flex",
    gap: 4,
    padding: "10px 14px",
    background: "#1e2430",
    borderRadius: 8,
    width: "fit-content",
    marginBottom: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#484f58",
    animation: "pulse 1.2s infinite",
  },
};

export function ChatWindow({ messages, isProcessing, onCopy }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  if (messages.length === 0) {
    return (
      <div style={style.container}>
        <div style={style.empty}>
          Ask an engineering question to begin diagnosis
        </div>
      </div>
    );
  }

  return (
    <div style={style.container}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} onCopy={onCopy} />
      ))}
      {isProcessing && (
        <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 12 }}>
          <div style={style.typing}>
            <div style={style.dot} />
            <div style={{ ...style.dot, animationDelay: "0.2s" }} />
            <div style={{ ...style.dot, animationDelay: "0.4s" }} />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
