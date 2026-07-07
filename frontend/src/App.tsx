import React from "react";
import { AppProvider, useApp } from "./context/AppContext";
import { ChatProvider } from "./context/ChatContext";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { Footer } from "./components/Footer";
import { ChatPage } from "./pages/Chat";
import { DiagnosticsPage } from "./pages/Diagnostics";
import { DocumentsPage } from "./pages/Documents";
import { SettingsPage } from "./pages/Settings";

const appStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  height: "100vh",
  background: "#0a0e14",
  color: "#e6e6e6",
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};

const bodyStyle: React.CSSProperties = {
  display: "flex",
  flex: 1,
  overflow: "hidden",
};

const contentStyle: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
};

const pages: Record<string, React.ReactNode> = {
  chat: <ChatPage />,
  diagnostics: <DiagnosticsPage />,
  documents: <DocumentsPage />,
  settings: <SettingsPage />,
};

function MainLayout() {
  const { state } = useApp();
  return (
    <div style={appStyle}>
      <Header />
      <div style={bodyStyle}>
        <Sidebar />
        <main style={contentStyle}>
          {pages[state.currentPage] || <ChatPage />}
        </main>
      </div>
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <ChatProvider>
        <MainLayout />
      </ChatProvider>
    </AppProvider>
  );
}
