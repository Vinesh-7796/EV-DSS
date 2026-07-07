import React from "react";
import type { CitationItem } from "../../types";

interface Props {
  citations: CitationItem[];
}

function badgeStyle(valid: boolean): React.CSSProperties {
  return {
    fontSize: 10,
    padding: "1px 6px",
    borderRadius: 3,
    background: valid ? "#1b3d1b" : "#3d1b1b",
    color: valid ? "#4caf50" : "#f44336",
    whiteSpace: "nowrap",
  };
}

export function CitationPanel({ citations }: Props) {
  if (!citations || citations.length === 0) return null;
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
        Citations
      </div>
      {citations.map((c, i) => (
        <div
          key={i}
          style={{
            fontSize: 12,
            color: "#c9d1d9",
            padding: "4px 0",
            borderBottom: "1px solid #161b22",
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
          }}
        >
          <span style={badgeStyle(c.is_valid)}>
            {c.is_valid ? "VALID" : "INVALID"}
          </span>
          <span>{c.text}</span>
        </div>
      ))}
    </div>
  );
}
