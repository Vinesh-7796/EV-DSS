import React from "react";
import type { ConfidenceInfo } from "../../types";

interface Props {
  confidence: ConfidenceInfo;
}

function scoreStyle(value: number): React.CSSProperties {
  return {
    fontSize: 24,
    fontWeight: 700,
    color: value >= 0.8 ? "#4caf50" : value >= 0.6 ? "#ff9800" : "#f44336",
  };
}

function valueStyle(val: number): React.CSSProperties {
  return {
    color: val >= 0.7 ? "#4caf50" : val >= 0.4 ? "#ff9800" : "#f44336",
    fontWeight: 500,
  };
}

function statusStyle(status: string): React.CSSProperties {
  const failed = status.includes("FAIL");
  const passed = status === "PASSED";
  return {
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 4,
    background: passed ? "#1b3d1b" : failed ? "#3d1b1b" : "#1b2d3d",
    color: passed ? "#4caf50" : failed ? "#f44336" : "#58a6ff",
    display: "inline-block",
    marginTop: 4,
  };
}

export function ConfidenceCard({ confidence }: Props) {
  const scores = [
    { label: "Evidence Coverage", value: confidence.evidence_coverage },
    { label: "Citation Validity", value: confidence.citation_validity },
    { label: "Consistency", value: confidence.consistency },
  ];

  return (
    <div
      style={{
        background: "#1e2430",
        borderRadius: 8,
        padding: 16,
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
          marginBottom: 10,
        }}
      >
        Confidence
      </div>
      <div style={scoreStyle(confidence.overall_score)}>
        {(confidence.overall_score * 100).toFixed(0)}%
      </div>
      <div style={{ fontSize: 12, color: "#8b949e", marginTop: 2 }}>
        {confidence.level}
      </div>
      <div style={statusStyle(confidence.validation_status)}>
        {confidence.validation_status}
      </div>
      {scores.map(
        (s) =>
          s.value !== undefined && (
            <div
              key={s.label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "4px 0",
                fontSize: 12,
                borderBottom: "1px solid #161b22",
              }}
            >
              <span style={{ color: "#8b949e" }}>{s.label}</span>
              <span style={valueStyle(s.value)}>{(s.value * 100).toFixed(0)}%</span>
            </div>
          ),
      )}
      {confidence.component_scores?.map((cs) => (
        <div
          key={cs.name}
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "4px 0",
            fontSize: 12,
            borderBottom: "1px solid #161b22",
          }}
        >
          <span style={{ color: "#8b949e" }}>{cs.name.replace(/_/g, " ")}</span>
          <span style={valueStyle(cs.score)}>{(cs.score * 100).toFixed(0)}%</span>
        </div>
      ))}
    </div>
  );
}
