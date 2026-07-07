import React from "react";
import { useApp } from "../../context/AppContext";

function headerConnectedDot(connected: boolean): React.CSSProperties {
  return {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: connected ? "#4caf50" : "#f44336",
  };
}

export function Header() {
  const { state } = useApp();
  const connected = state.connectionStatus === "connected";
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: 48,
        padding: "0 16px",
        background: "#12161e",
        borderBottom: "1px solid #1e2430",
      }}
    >
      <span style={{ fontSize: 14, fontWeight: 600, color: "#e6e6e6", letterSpacing: "0.5px" }}>
        EV-DDSS
      </span>
      <div style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
        <span style={headerConnectedDot(connected)} />
        <span style={{ color: connected ? "#4caf50" : "#f44336" }}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
    </header>
  );
}
