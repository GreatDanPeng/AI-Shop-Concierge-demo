import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConciergeWidget } from "./ConciergeWidget";

// Links in answers go to a store page of this shop. On a narrow screen the panel covers the page, so
// it closes after the click and the page behind it is visible; on a wide screen it stays open.
const REPLY = "Try [Cobalt Shoes: 4% cash back](#/store/s4) today.";
const NARROW = "(max-width: 480px)";

function Harness() {
  const [open, setOpen] = useState(false);
  return <ConciergeWidget api={{ chat: async () => REPLY }} store={null} open={open} onOpenChange={setOpen} />;
}

async function openAndAsk() {
  render(<Harness />);
  fireEvent.click(screen.getByRole("button", { name: /open concierge chat/i }));
  fireEvent.change(screen.getByRole("textbox", { name: /your question/i }), { target: { value: "deals?" } });
  fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
  return screen.findByRole("link", { name: /cobalt shoes: 4% cash back/i });
}

function screenIs(narrow: boolean) {
  window.matchMedia = vi.fn((query: string) => ({ matches: narrow && query === NARROW, media: query })) as never;
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => {
  delete (window as { matchMedia?: unknown }).matchMedia;
  vi.restoreAllMocks();
});

describe("links inside the concierge panel", () => {
  it("shows the answer's store link as a real link", async () => {
    const link = await openAndAsk();
    expect(link.getAttribute("href")).toBe("#/store/s4");
  });

  it("goes to the store page and keeps the panel open on a wide screen", async () => {
    screenIs(false);
    const link = await openAndAsk();
    fireEvent.click(link);
    await waitFor(() => expect(window.location.hash).toBe("#/store/s4"));   // jsdom navigates a tick later
    expect(screen.queryByRole("dialog")).not.toBeNull();
  });

  it("goes to the store page and closes the panel on a narrow screen", async () => {
    screenIs(true);
    const link = await openAndAsk();
    fireEvent.click(link);
    await waitFor(() => expect(window.location.hash).toBe("#/store/s4"));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("keeps the panel open when the browser cannot tell the screen size", async () => {
    const link = await openAndAsk();                     // jsdom has no matchMedia
    expect(() => fireEvent.click(link)).not.toThrow();
    expect(screen.queryByRole("dialog")).not.toBeNull();
  });
});
