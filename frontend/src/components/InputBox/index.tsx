import React, { useState, useRef, useEffect } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const style: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    gap: 8,
    padding: "12px 16px",
    borderTop: "1px solid #1e2430",
    background: "#12161e",
  },
  input: {
    flex: 1,
    padding: "10px 14px",
    borderRadius: 6,
    border: "1px solid #1e2430",
    background: "#0d1117",
    color: "#e6e6e6",
    fontSize: 14,
    outline: "none",
    resize: "none",
    fontFamily: "inherit",
    lineHeight: 1.4,
    maxHeight: 120,
  },
  button: {
    padding: "10px 20px",
    borderRadius: 6,
    border: "none",
    background: "#1a6dff",
    color: "#fff",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
    alignSelf: "flex-end",
  },
  buttonDisabled: {
    opacity: 0.5,
    cursor: "not-allowed",
  },
};

export function InputBox({ onSend, disabled, placeholder = "Type your engineering question..." }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={style.wrapper}>
      <textarea
        ref={textareaRef}
        style={style.input}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={2}
        disabled={disabled}
      />
      <button
        style={{ ...style.button, ...(disabled ? style.buttonDisabled : {}) }}
        onClick={handleSend}
        disabled={disabled}
      >
        Send
      </button>
    </div>
  );
}
