import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatWindow } from "../components/ChatWindow";

describe("ChatWindow", () => {
  it("shows empty state when no messages", () => {
    render(<ChatWindow messages={[]} />);
    expect(screen.getByText("Start a diagnostic session")).toBeInTheDocument();
  });

  it("renders messages", () => {
    const messages = [
      { id: "1", role: "user" as const, content: "Hello", timestamp: Date.now() },
      { id: "2", role: "assistant" as const, content: "Hi there", timestamp: Date.now() },
    ];
    render(<ChatWindow messages={messages} />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Hi there")).toBeInTheDocument();
  });
});
