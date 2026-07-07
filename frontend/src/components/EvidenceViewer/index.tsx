import React from "react";
import type { EvidenceItem } from "../../types";

interface Props {
  evidence: EvidenceItem[];
}

const style: Record<string, React.CSSProperties> = {
  container: {
    background: "#1e2430",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: "#8b949e",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 8,
  },
  item: {
    fontSize: 12,
    color: "#c9d1d9",
    padding: "8px 0",
    borderBottom: "1px solid #161b22",
  },
  meta: {
    fontSize: 11,
    color: "#484f58",
    marginTop: 4,
    display: "flex",
    gap: 8,
    flexWrap: "wrap",
  },
  tag: {
    fontSize: 10,
    padding: "1px 6px",
    borderRadius: 3,
    background: "#161b22",
    color: "#8b949e",
  },
  content: {
    fontSize: 12,
    color: "#c9d1d9",
    lineHeight: 1.4,
    marginTop: 4,
  },
};

export function EvidenceViewer({ evidence }: Props) {
  if (!evidence || evidence.length === 0) return null;
  return (
    <div style={style.container}>
      <div style={style.title}>Supporting Evidence</div>
      {evidence.map((e, i) => (
        <div key={i} style={style.item}>
          <div style={style.content}>{e.content}</div>
          <div style={style.meta}>
            {e.document && <span style={style.tag}>{e.document}</span>}
            {e.section && <span style={style.tag}>{e.section}</span>}
            {e.page > 0 && <span style={style.tag}>p.{e.page}</span>}
            {e.node_id && <span style={style.tag}>ID: {e.node_id}</span>}
            {e.validator && <span style={style.tag}>{e.validator}</span>}
            {e.score > 0 && (
              <span style={{ ...style.tag, color: e.score > 0.7 ? "#4caf50" : "#ff9800" }}>
                {(e.score * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
