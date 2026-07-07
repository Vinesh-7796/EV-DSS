import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SafetyWarnings } from "../components/SafetyWarnings";

describe("SafetyWarnings", () => {
  it("renders nothing when warnings are empty", () => {
    const { container } = render(<SafetyWarnings warnings={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders warning items", () => {
    render(<SafetyWarnings warnings={["High voltage present", "Disconnect battery first"]} />);
    expect(screen.getByText((content) => content.includes("High voltage present"))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("Disconnect battery first"))).toBeInTheDocument();
  });
});
