import React, { createContext, useContext, useReducer, useCallback, useEffect } from "react";
import type { ConfigData } from "../types";
import { api } from "../services/api";
import { WebSocketClient } from "../services/websocket";

interface AppState {
  config: ConfigData | null;
  connectionStatus: "connected" | "disconnected" | "connecting";
  sidebarOpen: boolean;
  currentPage: string;
  theme: "dark";
  documents: unknown[];
  wsClient: WebSocketClient | null;
}

type AppAction =
  | { type: "SET_CONFIG"; payload: ConfigData }
  | { type: "SET_CONNECTION_STATUS"; payload: AppState["connectionStatus"] }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "SET_PAGE"; payload: string }
  | { type: "SET_DOCUMENTS"; payload: unknown[] }
  | { type: "SET_WS_CLIENT"; payload: WebSocketClient | null };

const initialState: AppState = {
  config: null,
  connectionStatus: "disconnected",
  sidebarOpen: true,
  currentPage: "chat",
  theme: "dark",
  documents: [],
  wsClient: null,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_CONFIG":
      return { ...state, config: action.payload };
    case "SET_CONNECTION_STATUS":
      return { ...state, connectionStatus: action.payload };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case "SET_PAGE":
      return { ...state, currentPage: action.payload };
    case "SET_DOCUMENTS":
      return { ...state, documents: action.payload };
    case "SET_WS_CLIENT":
      return { ...state, wsClient: action.payload };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  setPage: (page: string) => void;
  toggleSidebar: () => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const setPage = useCallback(
    (page: string) => dispatch({ type: "SET_PAGE", payload: page }),
    [],
  );

  const toggleSidebar = useCallback(
    () => dispatch({ type: "TOGGLE_SIDEBAR" }),
    [],
  );

  useEffect(() => {
    api.config.get().then(
      (config) => dispatch({ type: "SET_CONFIG", payload: config }),
      () => {},
    );
    api.documents.list().then(
      (docs) => dispatch({ type: "SET_DOCUMENTS", payload: docs }),
      () => {},
    );

    const wsClient = new WebSocketClient();
    wsClient.onStatusChange((status) => {
      dispatch({ type: "SET_CONNECTION_STATUS", payload: status as AppState["connectionStatus"] });
    });
    wsClient.connect();
    dispatch({ type: "SET_WS_CLIENT", payload: wsClient });

    return () => {
      wsClient.disconnect();
    };
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch, setPage, toggleSidebar }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
