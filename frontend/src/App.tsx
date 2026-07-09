import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { ChatProvider } from './context/ChatContext';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatPage } from './pages/Chat';
import { DiagnosticsPage } from './pages/Diagnostics';
import { DocumentsPage } from './pages/Documents';
import { SettingsPage } from './pages/Settings';
import { ModelsPage } from './pages/Models';
import { HistoryPage } from './pages/History';
import { AnalyticsPage } from './pages/Analytics';
import { theme } from './styles/theme';

const pages: Record<string, React.ReactNode> = {
  chat: <ChatPage />,
  diagnostics: <DiagnosticsPage />,
  documents: <DocumentsPage />,
  models: <ModelsPage />,
  history: <HistoryPage />,
  settings: <SettingsPage />,
  analytics: <AnalyticsPage />,
};

function MainLayout() {
  const { state } = useApp();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: theme.bg.primary, color: theme.text.primary }}>
      <Header />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: theme.bg.primary }}>
          {pages[state.currentPage] || <ChatPage />}
        </main>
      </div>
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
