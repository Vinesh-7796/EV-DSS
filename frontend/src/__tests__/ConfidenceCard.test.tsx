import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceCard } from "../components/ConfidenceCard";

describe("ConfidenceCard", () => {
  const confidence = {
    overall_score: 0.85,
    level: "HIGH",
    validation_status: "PASSED",
    evidence_coverage: 0.9,
    citation_validity: 0.8,
    consistency: 0.85,
  };

  it("renders overall score and level", () => {
    render(<ConfidenceCard confidence={confidence} />);
    const scores = screen.getAllByText(/85%/);
    expect(scores.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("renders validation status", () => {
    render(<ConfidenceCard confidence={confidence} />);
    expect(screen.getByText("PASSED")).toBeInTheDocument();
  });

  it("renders component scores", () => {
    render(<ConfidenceCard confidence={confidence} />);
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
  });
});
