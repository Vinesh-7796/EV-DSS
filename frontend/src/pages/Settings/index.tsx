import React from "react";
import { useApp } from "../../context/AppContext";

const style: Record<string, React.CSSProperties> = {
  page: {
    padding: 24,
    overflow: "auto",
    height: "100%",
  },
  header: {
    fontSize: 16,
    fontWeight: 600,
    color: "#e6e6e6",
    marginBottom: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 600,
    color: "#8b949e",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 12,
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 12px",
    background: "#1e2430",
    borderRadius: 6,
    marginBottom: 6,
  },
  label: {
    fontSize: 13,
    color: "#c9d1d9",
  },
  value: {
    fontSize: 13,
    color: "#58a6ff",
    fontFamily: "monospace",
  },
  note: {
    fontSize: 12,
    color: "#484f58",
    marginTop: 16,
    textAlign: "center",
  },
};

export function SettingsPage() {
  const { state } = useApp();
  const config = state.config;

  return (
    <div style={style.page}>
      <div style={style.header}>Settings</div>
      {config ? (
        <>
          <div style={style.section}>
            <div style={style.sectionTitle}>Application</div>
            <div style={style.row}>
              <span style={style.label}>Name</span>
              <span style={style.value}>{config.application.name}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Version</span>
              <span style={style.value}>{config.application.version}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Debug</span>
              <span style={style.value}>{config.application.debug ? "true" : "false"}</span>
            </div>
          </div>
          <div style={style.section}>
            <div style={style.sectionTitle}>Reasoning Engine</div>
            <div style={style.row}>
              <span style={style.label}>Runtime</span>
              <span style={style.value}>{config.reasoning.runtime}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Model</span>
              <span style={style.value}>{config.reasoning.model}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Temperature</span>
              <span style={style.value}>{config.reasoning.temperature}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Max Tokens</span>
              <span style={style.value}>{config.reasoning.max_tokens}</span>
            </div>
          </div>
          <div style={style.section}>
            <div style={style.sectionTitle}>Retrieval</div>
            <div style={style.row}>
              <span style={style.label}>Top-K Vector</span>
              <span style={style.value}>{config.retrieval.top_k_vector}</span>
            </div>
            <div style={style.row}>
              <span style={style.label}>Top-K Graph</span>
              <span style={style.value}>{config.retrieval.top_k_graph}</span>
            </div>
          </div>
        </>
      ) : (
        <div style={{ color: "#484f58", textAlign: "center", paddingTop: 40 }}>
          Loading configuration...
        </div>
      )}
      <div style={style.note}>
        Settings are read-only. Restart the application to apply configuration changes.
      </div>
    </div>
  );
}
