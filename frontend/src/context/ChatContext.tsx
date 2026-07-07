import React, { createContext, useContext, useReducer, useCallback } from "react";
import type { ChatMessage } from "../types";

interface ChatState {
  conversations: Record<string, { id: string; title: string; messages: ChatMessage[] }>;
  activeConversationId: string | null;
  isProcessing: boolean;
  error: string | null;
}

type ChatAction =
  | { type: "ADD_MESSAGE"; payload: { conversationId: string; message: ChatMessage } }
  | { type: "SET_ACTIVE_CONVERSATION"; payload: string }
  | { type: "NEW_CONVERSATION"; payload: { id: string } }
  | { type: "SET_PROCESSING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "CLEAR_CONVERSATION"; payload: string };

const initialState: ChatState = {
  conversations: {},
  activeConversationId: null,
  isProcessing: false,
  error: null,
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_MESSAGE": {
      const { conversationId, message } = action.payload;
      const conv = state.conversations[conversationId] || {
        id: conversationId,
        title: message.content.slice(0, 60),
        messages: [],
      };
      return {
        ...state,
        conversations: {
          ...state.conversations,
          [conversationId]: {
            ...conv,
            messages: [...conv.messages, message],
          },
        },
      };
    }
    case "SET_ACTIVE_CONVERSATION":
      return { ...state, activeConversationId: action.payload };
    case "NEW_CONVERSATION":
      return {
        ...state,
        conversations: {
          ...state.conversations,
          [action.payload.id]: { id: action.payload.id, title: "New Conversation", messages: [] },
        },
        activeConversationId: action.payload.id,
      };
    case "SET_PROCESSING":
      return { ...state, isProcessing: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload };
    case "CLEAR_CONVERSATION": {
      const { [action.payload]: _, ...rest } = state.conversations;
      return { ...state, conversations: rest, activeConversationId: null };
    }
    default:
      return state;
  }
}

interface ChatContextType {
  state: ChatState;
  dispatch: React.Dispatch<ChatAction>;
  addMessage: (conversationId: string, message: ChatMessage) => void;
  setActiveConversation: (id: string) => void;
  newConversation: () => void;
  clearConversation: (id: string) => void;
}

const ChatContext = createContext<ChatContextType | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  const addMessage = useCallback(
    (conversationId: string, message: ChatMessage) =>
      dispatch({ type: "ADD_MESSAGE", payload: { conversationId, message } }),
    [],
  );

  const setActiveConversation = useCallback(
    (id: string) => dispatch({ type: "SET_ACTIVE_CONVERSATION", payload: id }),
    [],
  );

  const newConversation = useCallback(() => {
    const id = crypto.randomUUID();
    dispatch({ type: "NEW_CONVERSATION", payload: { id } });
  }, []);

  const clearConversation = useCallback(
    (id: string) => dispatch({ type: "CLEAR_CONVERSATION", payload: id }),
    [],
  );

  return (
    <ChatContext.Provider
      value={{
        state,
        dispatch,
        addMessage,
        setActiveConversation,
        newConversation,
        clearConversation,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
