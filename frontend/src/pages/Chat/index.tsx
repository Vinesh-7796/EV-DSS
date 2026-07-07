import React, { useCallback } from "react";
import { ChatWindow } from "../../components/ChatWindow";
import { InputBox } from "../../components/InputBox";
import { useChat } from "../../context/ChatContext";
import { api } from "../../services/api";
import type { ChatMessage } from "../../types";

export function ChatPage() {
  const { state, addMessage, dispatch } = useChat();
  const activeConv = state.activeConversationId
    ? state.conversations[state.activeConversationId]
    : null;

  const handleSend = useCallback(
    async (message: string) => {
      let cid = state.activeConversationId;
      if (!cid) {
        cid = crypto.randomUUID();
        dispatch({ type: "NEW_CONVERSATION", payload: { id: cid } });
        dispatch({ type: "SET_ACTIVE_CONVERSATION", payload: cid });
      }

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        timestamp: Date.now(),
      };
      addMessage(cid, userMsg);
      dispatch({ type: "SET_PROCESSING", payload: true });

      try {
        const result = await api.chat.send(message, cid);
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.problem_summary,
          timestamp: Date.now(),
          diagnostic: result,
        };
        addMessage(cid, assistantMsg);
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : "Request failed";
        dispatch({ type: "SET_ERROR", payload: errMsg });
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error: ${errMsg}`,
          timestamp: Date.now(),
        };
        addMessage(cid, errorMsg);
      } finally {
        dispatch({ type: "SET_PROCESSING", payload: false });
      }
    },
    [state.activeConversationId, addMessage, dispatch],
  );

  const handleCopy = useCallback((content: string) => {
    navigator.clipboard.writeText(content).catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <ChatWindow
        messages={activeConv?.messages || []}
        isProcessing={state.isProcessing}
        onCopy={handleCopy}
      />
      <InputBox onSend={handleSend} disabled={state.isProcessing} />
    </div>
  );
}
