import React from "react";

interface Props {
  warnings: string[];
}

const style: Record<string, React.CSSProperties> = {
  container: {
    background: "#3d1b1b",
    border: "1px solid #f44336",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  title: {
    fontSize: 13,
    fontWeight: 600,
    color: "#f44336",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: 8,
  },
  item: {
    fontSize: 13,
    color: "#ffcdd2",
    padding: "2px 0",
  },
};

export function SafetyWarnings({ warnings }: Props) {
  if (!warnings || warnings.length === 0) return null;
  return (
    <div style={style.container}>
      <div style={style.title}>Safety Warnings</div>
      {warnings.map((w, i) => (
        <div key={i} style={style.item}>
          &bull; {w}
        </div>
      ))}
    </div>
  );
}
