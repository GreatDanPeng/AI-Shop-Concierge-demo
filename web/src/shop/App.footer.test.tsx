import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import { App } from "./App";

// The demo now uses real brand names for invented offers, so the footer has to say so plainly.
const api = {
  health: vi.fn(async () => ({ ok: true, assistant: { provider: "openrouter", model: "m", configured: true } })),
  demoMembers: vi.fn(async () => []),
  switchMember: vi.fn(async () => ({ ok: true })),
  me: vi.fn(async () => { throw new ApiError(401, "not_signed_in"); }),
  discounts: vi.fn(async () => { throw new ApiError(401, "not_signed_in"); }),
  estimate: vi.fn(),
};
const concierge = { setStore: vi.fn(), open: vi.fn(), ask: vi.fn() };

describe("the footer", () => {
  it("says brand names are only for illustration and that these brands offer none of these discounts", async () => {
    render(<App api={api as never} concierge={concierge} />);
    await screen.findByLabelText(/signed in as/i);
    const footer = (document.querySelector("footer")?.textContent ?? "").replace(/\s+/g, " ");
    expect(footer).toMatch(/brand names are used for illustration only/i);
    expect(footer).toMatch(/none of these brands offers these discounts/i);
    expect(footer).toMatch(/fictional/i);
    expect(footer).toMatch(/not affiliated with id\.me/i);
  });
});
