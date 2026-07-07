import React from "react";
import type { ChatMessage } from "../../types";
import { EvidenceViewer } from "../EvidenceViewer";
import { CitationPanel } from "../CitationPanel";
import { ConfidenceCard } from "../ConfidenceCard";
import { SafetyWarnings } from "../SafetyWarnings";

interface Props {
  message: ChatMessage;
  onCopy?: (content: string) => void;
}

function wrapperStyle(role: string): React.CSSProperties {
  return {
    display: "flex",
    justifyContent: role === "user" ? "flex-end" : "flex-start",
    marginBottom: 12,
  };
}

function bubbleStyle(role: string): React.CSSProperties {
  return {
    maxWidth: "75%",
    padding: "10px 14px",
    borderRadius: 8,
    background: role === "user" ? "#1a6dff" : "#1e2430",
    color: "#e6e6e6",
    fontSize: 14,
    lineHeight: 1.5,
    wordBreak: "break-word",
  };
}

const containerStyle: React.CSSProperties = {
  marginTop: 8,
};

const faultSummaryStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#c9d1d9",
  lineHeight: 1.5,
};

const sectionStyle: React.CSSProperties = {
  marginBottom: 12,
};

const headingStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#8b949e",
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
  marginBottom: 6,
};

const listItemStyle: React.CSSProperties = {
  fontSize: 13,
  color: "#c9d1d9",
  padding: "2px 0",
  marginLeft: 16,
};

const tagContainerStyle: React.CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 6,
};

const tagStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "2px 8px",
  borderRadius: 4,
  background: "#161b22",
  color: "#8b949e",
  display: "inline-block",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  if (!children) return null;
  return (
    <div style={sectionStyle}>
      <div style={headingStyle}>{title}</div>
      {children}
    </div>
  );
}

function ListSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Section title={title}>
      {items.map((item, i) => (
        <div key={i} style={listItemStyle}>&bull; {item}</div>
      ))}
    </Section>
  );
}

function TagSection({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Section title={title}>
      <div style={tagContainerStyle}>
        {items.map((item, i) => (
          <span key={i} style={tagStyle}>{item}</span>
        ))}
      </div>
    </Section>
  );
}

function DiagnosticView({ d }: { d: NonNullable<ChatMessage["diagnostic"]> }) {
  return (
    <div style={containerStyle}>
      <Section title="Fault Summary">
        <div style={faultSummaryStyle}>{d.problem_summary}</div>
      </Section>
      <ListSection title="Possible Causes" items={d.possible_causes} />
      <ListSection title="Inspection Steps" items={d.inspection_steps} />
      <ListSection title="Recommended Actions" items={d.recommended_actions} />
      <TagSection title="Related Components" items={d.related_components} />
      <TagSection title="CAN IDs" items={d.can_signals} />
      <TagSection title="Connectors" items={d.connectors} />
      <TagSection title="Fuses" items={d.fuses} />
      <TagSection title="Relays" items={d.relays} />
      <SafetyWarnings warnings={d.safety_warnings} />
      <ConfidenceCard confidence={d.confidence} />
      <EvidenceViewer evidence={d.evidence} />
      <CitationPanel citations={d.citations} />
    </div>
  );
}

export function MessageBubble({ message, onCopy }: Props) {
  return (
    <div style={wrapperStyle(message.role)}>
      <div style={bubbleStyle(message.role)}>
        {message.role === "user" ? (
          <div>{message.content}</div>
        ) : (
          <>
            <div>{message.content}</div>
            {message.diagnostic && <DiagnosticView d={message.diagnostic} />}
            {onCopy && (
              <button
                style={{ background: "none", border: "none", color: "#484f58", cursor: "pointer", fontSize: 11, padding: 0, marginTop: 4 }}
                onClick={() => onCopy(message.content)}
              >
                Copy
              </button>
            )}
          </>
        )}
        <div
          style={{
            fontSize: 10,
            color: "#484f58",
            marginTop: 4,
            textAlign: "right",
          }}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}