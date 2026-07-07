import React from "react";

const style: React.CSSProperties = {
  height: 32,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#12161e",
  borderTop: "1px solid #1e2430",
  fontSize: 11,
  color: "#484f58",
};

export function Footer() {
  return (
    <footer style={style}>
      EV-DDSS &copy; {new Date().getFullYear()} &mdash; Application Layer v0.1.0
    </footer>
  );
}
