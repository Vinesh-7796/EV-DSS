import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "../components/MessageBubble";

describe("MessageBubble", () => {
  const userMsg = {
    id: "1",
    role: "user" as const,
    content: "What is the battery voltage?",
    timestamp: Date.now(),
  };

  const assistantMsg = {
    id: "2",
    role: "assistant" as const,
    content: "The battery voltage is 12.6V.",
    timestamp: Date.now(),
  };

  it("renders user message", () => {
    render(<MessageBubble message={userMsg} />);
    expect(screen.getByText("What is the battery voltage?")).toBeInTheDocument();
  });

  it("renders assistant message", () => {
    render(<MessageBubble message={assistantMsg} />);
    expect(screen.getByText("The battery voltage is 12.6V.")).toBeInTheDocument();
  });

  it("shows copy button for assistant messages", () => {
    const onCopy = vi.fn();
    render(<MessageBubble message={assistantMsg} onCopy={onCopy} />);
    const btn = screen.getByText("Copy");
    btn.click();
    expect(onCopy).toHaveBeenCalledWith("The battery voltage is 12.6V.");
  });
});
