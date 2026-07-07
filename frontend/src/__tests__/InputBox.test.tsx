import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { InputBox } from "../components/InputBox";

describe("InputBox", () => {
  it("renders textarea and send button", () => {
    render(<InputBox onSend={() => {}} />);
    expect(screen.getByPlaceholderText("Type your engineering question...")).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("calls onSend when button clicked", () => {
    const onSend = vi.fn();
    render(<InputBox onSend={onSend} />);
    const input = screen.getByPlaceholderText("Type your engineering question...");
    fireEvent.change(input, { target: { value: "Test query" } });
    screen.getByText("Send").click();
    expect(onSend).toHaveBeenCalledWith("Test query");
  });

  it("calls onSend on Enter key", () => {
    const onSend = vi.fn();
    render(<InputBox onSend={onSend} />);
    const input = screen.getByPlaceholderText("Type your engineering question...");
    fireEvent.change(input, { target: { value: "Enter query" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("Enter query");
  });

  it("disables button when disabled prop is true", () => {
    render(<InputBox onSend={() => {}} disabled />);
    expect(screen.getByText("Send")).toBeDisabled();
  });
});
