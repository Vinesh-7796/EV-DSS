import React from "react";
import { useApp } from "../../context/AppContext";
import { DocumentViewer } from "../../components/DocumentViewer";
import { EvidenceViewer } from "../../components/EvidenceViewer";

const style: Record<string, React.CSSProperties> = {
  page: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    padding: 16,
    overflow: "auto",
  },
  header: {
    fontSize: 16,
    fontWeight: 600,
    color: "#e6e6e6",
    marginBottom: 16,
  },
  placeholder: {
    color: "#484f58",
    textAlign: "center",
    paddingTop: 40,
    fontSize: 14,
  },
};

export function DocumentsPage() {
  const { state } = useApp();
  const docs = state.documents;

  return (
    <div style={style.page}>
      <div style={style.header}>Documents ({docs.length})</div>
      {docs.length === 0 && (
        <div style={style.placeholder}>
          No processed documents available.
          Run the ingestion pipeline to populate the knowledge base.
        </div>
      )}
    </div>
  );
}
