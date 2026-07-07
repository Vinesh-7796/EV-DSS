import React from "react";

interface Props {
  status: string;
  stages?: { name: string; status: string; duration_ms?: number }[];
}

function statusStyle(s: string): React.CSSProperties {
  return {
    fontSize: 12,
    fontWeight: 600,
    color: s === "PASSED" ? "#4caf50" : s.includes("WARNING") ? "#ff9800" : s.includes("FAIL") || s.includes("ERROR") ? "#f44336" : "#58a6ff",
    marginBottom: 8,
  };
}

function stageStatusStyle(s: string): React.CSSProperties {
  return {
    color: s === "COMPLETED" ? "#4caf50" : s === "FAILED" ? "#f44336" : "#ff9800",
    fontWeight: 500,
  };
}

export function ProcessingStatus({ status, stages }: Props) {
  return (
    <div
      style={{
        background: "#1e2430",
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "#8b949e",
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          marginBottom: 8,
        }}
      >
        Processing Status
      </div>
      <div style={statusStyle(status)}>{status}</div>
      {stages?.map((s, i) => (
        <div
          key={i}
          style={{
            fontSize: 12,
            display: "flex",
            justifyContent: "space-between",
            padding: "3px 0",
            borderBottom: "1px solid #161b22",
          }}
        >
          <span style={{ color: "#c9d1d9" }}>{s.name}</span>
          <span>
            <span style={stageStatusStyle(s.status)}>{s.status}</span>
            {s.duration_ms !== undefined && (
              <span style={{ color: "#484f58", marginLeft: 6 }}>
                {s.duration_ms.toFixed(0)}ms
              </span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
