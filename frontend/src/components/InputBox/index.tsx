import React, { useState, useRef, useEffect } from 'react';
import { theme } from '../../styles/theme';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function InputBox({ onSend, disabled, placeholder = 'Describe the vehicle issue...' }: Props) {
  const [value, setValue] = useState('');
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
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{
      display: 'flex',
      gap: theme.spacing.md,
      padding: `${theme.spacing.lg} ${theme.spacing['2xl']}`,
      borderTop: `1px solid ${theme.border.primary}`,
      background: theme.bg.secondary,
    }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={2}
        disabled={disabled}
        style={{
          flex: 1,
          padding: '12px 16px',
          borderRadius: theme.radius.md,
          border: `1px solid ${theme.border.primary}`,
          background: theme.bg.primary,
          color: theme.text.primary,
          fontSize: theme.font.size.md,
          outline: 'none',
          resize: 'none',
          fontFamily: theme.font.family,
          lineHeight: 1.5,
          maxHeight: 140,
          transition: `border-color ${theme.transition.fast}`,
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = theme.accent.blue; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = theme.border.primary; }}
      />
      <button
        onClick={handleSend}
        disabled={disabled}
        style={{
          padding: '12px 24px',
          borderRadius: theme.radius.md,
          border: 'none',
          background: disabled ? theme.bg.tertiary : theme.accent.blue,
          color: '#fff',
          fontSize: theme.font.size.md,
          fontWeight: theme.font.weight.semibold,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          alignSelf: 'flex-end',
          transition: `all ${theme.transition.fast}`,
        }}
        onMouseEnter={(e) => { if (!disabled) e.currentTarget.style.opacity = '0.9'; }}
        onMouseLeave={(e) => { if (!disabled) e.currentTarget.style.opacity = '1'; }}
      >
        Send
      </button>
    </div>
  );
}
