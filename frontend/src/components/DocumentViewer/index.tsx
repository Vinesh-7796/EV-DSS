import React from "react";

interface Props {
  documentId?: string;
  title?: string;
  content?: string;
}

const style: Record<string, React.CSSProperties> = {
  container: {
    background: "#0d1117",
    borderRadius: 8,
    border: "1px solid #1e2430",
    padding: 16,
    minHeight: 200,
    overflow: "auto",
  },
  title: {
    fontSize: 14,
    fontWeight: 600,
    color: "#e6e6e6",
    marginBottom: 12,
    paddingBottom: 8,
    borderBottom: "1px solid #1e2430",
  },
  content: {
    fontSize: 13,
    color: "#c9d1d9",
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
  },
  empty: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    height: 200,
    color: "#484f58",
    fontSize: 13,
  },
};

export function DocumentViewer({ documentId, title, content }: Props) {
  if (!documentId) {
    return (
      <div style={style.container}>
        <div style={style.empty}>Select a document to view</div>
      </div>
    );
  }
  return (
    <div style={style.container}>
      <div style={style.title}>{title || documentId}</div>
      <div style={style.content}>{content || "Loading..."}</div>
    </div>
  );
}
