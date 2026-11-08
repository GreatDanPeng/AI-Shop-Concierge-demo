import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatInput, type PromptSuggestion } from "./ChatInput";

function Harness({ onSend, disabled = false, start = "", suggestions }: { onSend: (text: string) => void; disabled?: boolean; start?: string; suggestions?: PromptSuggestion[] }) {
  const [value, setValue] = useState(start);
  return <ChatInput value={value} onChange={setValue} onSend={onSend} disabled={disabled} placeholder="Ask the concierge…" suggestions={suggestions} />;
}
const box = () => screen.getByRole("textbox", { name: /ask the concierge/i }) as HTMLTextAreaElement;
const type = (text: string) => fireEvent.change(box(), { target: { value: text } });

afterEach(() => {
  delete (HTMLTextAreaElement.prototype as { scrollHeight?: number }).scrollHeight;
});

function fakeScrollHeight(height: number) {
  Object.defineProperty(HTMLTextAreaElement.prototype, "scrollHeight", { configurable: true, get: () => height });
}

describe("ChatInput", () => {
  it("is a labelled text box with the placeholder and a Send button that says what it does", () => {
    render(<Harness onSend={vi.fn()} />);
    expect(box().getAttribute("placeholder")).toBe("Ask the concierge…");
    expect(screen.getByRole("button", { name: /^send$/i }).textContent).toMatch(/send/i);
  });

  it("sends the trimmed text on Enter", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    type("  What do I pay?  ");
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("What do I pay?");
  });

  it("starts a new line on Shift+Enter instead of sending", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    type("first");
    expect(fireEvent.keyDown(box(), { key: "Enter", shiftKey: true })).toBe(true); // not prevented: the browser adds the line
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send while an input method is composing (for example Chinese or Japanese)", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    type("你好");
    fireEvent.keyDown(box(), { key: "Enter", isComposing: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("sends with the button too", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    type("hello");
    fireEvent.click(screen.getByRole("button", { name: /^send$/i }));
    expect(onSend).toHaveBeenCalledWith("hello");
  });

  it("never sends an empty or blank message", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} />);
    expect((screen.getByRole("button", { name: /^send$/i }) as HTMLButtonElement).disabled).toBe(true);
    type("   ");
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("can be disabled", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} disabled start="hello" />);
    expect(box().disabled).toBe(true);
    expect((screen.getByRole("button", { name: /^send$/i }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("limits the message to 2000 characters, like the server", () => {
    render(<Harness onSend={vi.fn()} />);
    expect(box().getAttribute("maxlength")).toBe("2000");
  });

  it("grows with its content, up to a limit", () => {
    render(<Harness onSend={vi.fn()} />);
    fakeScrollHeight(120);
    type("a\nb\nc\nd");
    expect(box().style.height).toBe("120px");
    fakeScrollHeight(900);
    type("a\nb\nc\nd\ne\nf\ng\nh\ni\nj");
    expect(box().style.height).toBe("200px");
  });
});

const PROMPTS: PromptSuggestion[] = [
  { label: "Show my best deals", text: "What are the best discounts I qualify for?" },
  { label: "Check why an offer is missing", text: "Why isn't my discount showing?" },
  { label: "Estimate a cart", text: "I'm buying $200 of stuff. What do I pay?" },
];

describe("prompt chips inside the input", () => {
  const chips = () => within(screen.getByRole("group", { name: /suggested prompts/i })).getAllByRole("button");

  it("sit inside the same box, under the text box, labelled as a group", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} />);
    const form = box().closest("form")!;
    expect(chips().map((c) => c.textContent)).toEqual(PROMPTS.map((p) => p.label));
    for (const chip of chips()) {
      expect(form.contains(chip)).toBe(true);
      // the text box comes first in the page order, the chips after it
      expect(box().compareDocumentPosition(chip) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it("fill the box with the prompt's text when clicked, without sending", () => {
    const onSend = vi.fn();
    render(<Harness onSend={onSend} suggestions={PROMPTS} />);
    fireEvent.click(screen.getByRole("button", { name: "Check why an offer is missing" }));
    expect(box().value).toBe("Why isn't my discount showing?");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("put the cursor back in the box, so the person can edit or press Enter", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} />);
    fireEvent.click(screen.getByRole("button", { name: "Estimate a cart" }));
    expect(document.activeElement).toBe(box());
  });

  it("replace what was typed, so a second click gives a second prompt", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} start="something typed" />);
    fireEvent.click(screen.getByRole("button", { name: "Show my best deals" }));
    fireEvent.click(screen.getByRole("button", { name: "Estimate a cart" }));
    expect(box().value).toBe("I'm buying $200 of stuff. What do I pay?");
  });

  it("are plain buttons that never submit the form", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} />);
    for (const chip of chips()) expect(chip.getAttribute("type")).toBe("button");
  });

  it("show only their label: no description text", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} />);
    expect(screen.getByRole("group", { name: /suggested prompts/i }).textContent).toBe(PROMPTS.map((p) => p.label).join(""));
  });

  it("are not there when no suggestions are given", () => {
    render(<Harness onSend={vi.fn()} />);
    expect(screen.queryByRole("group", { name: /suggested prompts/i })).toBeNull();
  });

  it("are disabled together with the box", () => {
    render(<Harness onSend={vi.fn()} suggestions={PROMPTS} disabled />);
    for (const chip of chips()) expect((chip as HTMLButtonElement).disabled).toBe(true);
  });
});
