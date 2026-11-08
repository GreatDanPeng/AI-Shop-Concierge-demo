import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import { ConciergeWidget, type Store } from "./ConciergeWidget";

type Chat = (message: string, storeId: string | null) => Promise<string>;

function Harness({ chat, store = { id: "s1", name: "Fjordline Outdoors" }, question }: { chat: Chat; store?: Store; question?: { id: number; text: string } | null }) {
  const [open, setOpen] = useState(false);
  return <ConciergeWidget api={{ chat }} store={store} open={open} onOpenChange={setOpen} question={question} />;
}

const launcher = () => screen.getByRole("button", { name: /(open|close) concierge chat/i });
const openWidget = () => fireEvent.click(screen.getByRole("button", { name: /open concierge chat/i }));
const box = () => screen.getByRole("textbox", { name: /your question/i });
const sendButton = () => screen.getByRole("button", { name: /^send$/i });

function ask(text: string) {
  fireEvent.change(box(), { target: { value: text } });
  fireEvent.click(sendButton());
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

const fakeChat = (reply = "A fine answer.") => vi.fn<Chat>(async () => reply);

afterEach(() => vi.restoreAllMocks());

describe("opening and closing", () => {
  it("starts closed: just the launcher button", () => {
    render(<Harness chat={fakeChat()} />);
    expect(launcher().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("opens a labelled dialog with the question box focused and suggestions, and nothing else on top", () => {
    render(<Harness chat={fakeChat()} />);
    openWidget();
    expect(screen.getByRole("dialog", { name: /concierge/i })).toBeTruthy();
    expect(launcher().getAttribute("aria-expanded")).toBe("true");
    expect(launcher().getAttribute("aria-label")).toMatch(/close concierge chat/i);
    expect(document.activeElement).toBe(box());
    expect(screen.getAllByRole("button").some((b) => /what discounts can i get here/i.test(b.textContent ?? ""))).toBe(true);
    const text = screen.getByRole("dialog").textContent ?? "";
    expect(text).toMatch(/concierge/i);                          // the title stays
    expect(text).not.toMatch(/fake data|unofficial/i);           // removed: the demo disclaimer
    expect(text).not.toMatch(/each question is answered on its own|no\s+guarantee|as-of/i);  // removed: the note
    expect(text).not.toMatch(/asking about/i);                   // removed: the store line
  });

  it("closes on Escape and gives the focus back to the launcher", () => {
    render(<Harness chat={fakeChat()} />);
    openWidget();
    fireEvent.keyDown(box(), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(launcher());
  });

  it("toggles with the launcher", () => {
    render(<Harness chat={fakeChat()} />);
    openWidget();
    fireEvent.click(launcher());
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keeps the conversation when it is closed and opened again", async () => {
    render(<Harness chat={fakeChat("Still here.")} />);
    openWidget();
    ask("hello");
    await screen.findByText("Still here.");
    fireEvent.click(launcher());
    openWidget();
    expect(screen.getByText("Still here.")).toBeTruthy();
    expect(screen.getByText("hello")).toBeTruthy();
  });
});

describe("sending a question", () => {
  it("sends the text and the store, shows both messages and clears the box", async () => {
    const chat = fakeChat("You pay $140.00.");
    render(<Harness chat={chat} />);
    openWidget();
    ask("  I'm buying $200 of gear  ");
    expect(await screen.findByText("You pay $140.00.")).toBeTruthy();
    expect(chat).toHaveBeenCalledTimes(1);
    expect(chat).toHaveBeenCalledWith("I'm buying $200 of gear", "s1");
    expect(screen.getByText("I'm buying $200 of gear")).toBeTruthy();
    expect((box() as HTMLTextAreaElement).value).toBe("");
  });

  it("sends on Enter but not on Shift+Enter", async () => {
    const chat = fakeChat();
    render(<Harness chat={chat} />);
    openWidget();
    fireEvent.change(box(), { target: { value: "first" } });
    fireEvent.keyDown(box(), { key: "Enter", shiftKey: true });
    expect(chat).not.toHaveBeenCalled();
    fireEvent.keyDown(box(), { key: "Enter" });
    await waitFor(() => expect(chat).toHaveBeenCalledWith("first", "s1"));
  });

  it("does not send on Enter while an input method (for example Chinese) is composing", () => {
    const chat = fakeChat();
    render(<Harness chat={chat} />);
    openWidget();
    fireEvent.change(box(), { target: { value: "你好" } });
    fireEvent.keyDown(box(), { key: "Enter", isComposing: true });
    expect(chat).not.toHaveBeenCalled();
  });

  it("sends a suggestion when it is clicked", async () => {
    const chat = fakeChat();
    render(<Harness chat={chat} />);
    openWidget();
    fireEvent.click(screen.getByRole("button", { name: /what discounts can i get here/i }));
    await waitFor(() => expect(chat).toHaveBeenCalledWith("What discounts can I get here?", "s1"));
  });

  it("does not send an empty or blank message", () => {
    const chat = fakeChat();
    render(<Harness chat={chat} />);
    openWidget();
    expect((sendButton() as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(box(), { target: { value: "   " } });
    expect((sendButton() as HTMLButtonElement).disabled).toBe(true);
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(chat).not.toHaveBeenCalled();
  });

  it("limits the message to 2000 characters, like the server", () => {
    render(<Harness chat={fakeChat()} />);
    openWidget();
    expect(box().getAttribute("maxlength")).toBe("2000");
  });

  it("shows a waiting state and ignores a second send until the answer arrives", async () => {
    const pending = deferred<string>();
    const chat = vi.fn<Chat>(() => pending.promise);
    render(<Harness chat={chat} />);
    openWidget();
    ask("one");
    expect(screen.getByText(/thinking/i)).toBeTruthy();
    fireEvent.change(box(), { target: { value: "two" } });
    fireEvent.keyDown(box(), { key: "Enter" });
    fireEvent.click(sendButton());
    expect(chat).toHaveBeenCalledTimes(1);
    await act(async () => pending.resolve("done"));
    expect(await screen.findByText("done")).toBeTruthy();
    expect(screen.queryByText(/thinking/i)).toBeNull();
    ask("three");
    await waitFor(() => expect(chat).toHaveBeenCalledTimes(2));
  });

  it("keeps the order of a longer conversation", async () => {
    const chat = vi.fn<Chat>().mockResolvedValueOnce("answer one").mockResolvedValueOnce("answer two");
    render(<Harness chat={chat} />);
    openWidget();
    ask("question one");
    await screen.findByText("answer one");
    ask("question two");
    await screen.findByText("answer two");
    const log = within(screen.getByRole("log")).getAllByText(/question|answer/).map((n) => n.textContent);
    expect(log).toEqual(["question one", "answer one", "question two", "answer two"]);
  });
});

describe("the store the page is about", () => {
  it("does not show the store name, but still sends its id", async () => {
    const chat = fakeChat();
    render(<Harness chat={chat} />);
    openWidget();
    expect(screen.queryByText("Fjordline Outdoors")).toBeNull();
    ask("hi");
    await waitFor(() => expect(chat).toHaveBeenCalledWith("hi", "s1"));
  });

  it("does not show the store id when there is no name, and still sends it", async () => {
    const chat = fakeChat();
    render(<Harness chat={chat} store={{ id: "s9" }} />);
    openWidget();
    expect(screen.queryByText("s9")).toBeNull();
    ask("hi");
    await waitFor(() => expect(chat).toHaveBeenCalledWith("hi", "s9"));
  });

  it("sends null when the page has no store, and says nothing about it", async () => {
    const chat = fakeChat();
    render(<Harness chat={chat} store={null} />);
    openWidget();
    expect(screen.queryByText(/any store|asking about/i)).toBeNull();
    ask("hi");
    await waitFor(() => expect(chat).toHaveBeenCalledWith("hi", null));
  });

  it("follows the store when the page changes it", async () => {
    const chat = fakeChat();
    const { rerender } = render(<Harness chat={chat} />);
    openWidget();
    rerender(<Harness chat={chat} store={{ id: "s2", name: "Voltage Electronics" }} />);
    expect(screen.queryByText("Voltage Electronics")).toBeNull();   // context only, not shown
    ask("hi");
    await waitFor(() => expect(chat).toHaveBeenCalledWith("hi", "s2"));
  });
});

describe("when something goes wrong", () => {
  it.each([
    [new ApiError(401, "not_signed_in"), /sign in/i],
    [new ApiError(503, "assistant_not_configured"), /not set up/i],
    [new ApiError(502, "assistant_unavailable"), /temporarily unavailable/i],
    [new ApiError(0, "network"), /reach the server/i],
    [new Error("boom"), /went wrong/i],
  ])("shows a friendly message for %j and keeps the question visible", async (error, pattern) => {
    const chat = vi.fn<Chat>().mockRejectedValueOnce(error);
    render(<Harness chat={chat} />);
    openWidget();
    ask("my question");
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(pattern);
    expect(alert.textContent).not.toMatch(/boom|HTTP|assistant_/);
    expect(screen.getByText("my question")).toBeTruthy();
  });

  it("lets the person try again after an error", async () => {
    const chat = vi.fn<Chat>().mockRejectedValueOnce(new ApiError(502, "assistant_unavailable")).mockResolvedValueOnce("Second time lucky.");
    render(<Harness chat={chat} />);
    openWidget();
    ask("try");
    await screen.findByRole("alert");
    ask("try again");
    expect(await screen.findByText("Second time lucky.")).toBeTruthy();
  });
});

describe("rendering text safely", () => {
  it("shows what the person typed as plain text", async () => {
    render(<Harness chat={fakeChat()} />);
    openWidget();
    ask("<b>bold?</b><img src=x onerror=alert(1)>");
    await screen.findByText("A fine answer.");
    const log = screen.getByRole("log");
    expect(log.textContent).toContain("<b>bold?</b>");
    expect(log.querySelector("b")).toBeNull();
    expect(log.querySelector("img")).toBeNull();
  });

  it("never turns a model reply into elements, except bold and lists", async () => {
    const reply = "<img src=x onerror=alert(1)> **safe** [x](javascript:alert(1))\n\n- one\n- two";
    render(<Harness chat={fakeChat(reply)} />);
    openWidget();
    ask("hi");
    await screen.findByText("safe");
    const log = screen.getByRole("log");
    for (const tag of ["img", "a", "script", "iframe"]) expect(log.querySelector(tag)).toBeNull();
    expect(log.querySelector("strong")?.textContent).toBe("safe");
    expect(log.querySelectorAll("li")).toHaveLength(2);
    expect(log.textContent).toContain("<img src=x onerror=alert(1)>");
  });
});

describe("privacy in the browser", () => {
  it("stores nothing: no local storage, no session storage, no cookie", async () => {
    const local = vi.spyOn(Storage.prototype, "setItem");
    const cookies = document.cookie;
    render(<Harness chat={fakeChat("answer")} />);
    openWidget();
    ask("a private question");
    await screen.findByText("answer");
    expect(local).not.toHaveBeenCalled();
    expect(document.cookie).toBe(cookies);
    expect(JSON.stringify(window.localStorage) + JSON.stringify(window.sessionStorage)).not.toContain("private");
  });
});

describe("a question handed over by the page", () => {
  it("is sent once, and shown as the member's own message with the answer", async () => {
    const chat = fakeChat("Here you go.");
    const { rerender } = render(<Harness chat={chat} />);
    openWidget();
    rerender(<Harness chat={chat} question={{ id: 1, text: "I'm buying $200 of gear" }} />);
    expect(await screen.findByText("Here you go.")).toBeTruthy();
    expect(chat).toHaveBeenCalledTimes(1);
    expect(chat).toHaveBeenCalledWith("I'm buying $200 of gear", "s1");
    expect(screen.getByText("I'm buying $200 of gear")).toBeTruthy();
    rerender(<Harness chat={chat} question={{ id: 1, text: "I'm buying $200 of gear" }} />); // same id: not again
    expect(chat).toHaveBeenCalledTimes(1);
  });

  it("is sent again when the page asks again, even with the same words", async () => {
    const chat = fakeChat();
    const { rerender } = render(<Harness chat={chat} />);
    rerender(<Harness chat={chat} question={{ id: 1, text: "hello" }} />);
    await waitFor(() => expect(chat).toHaveBeenCalledTimes(1));
    rerender(<Harness chat={chat} question={{ id: 2, text: "hello" }} />);
    await waitFor(() => expect(chat).toHaveBeenCalledTimes(2));
  });

  it("is ignored while an answer is still on its way, like any other second send", async () => {
    const pending = deferred<string>();
    const chat = vi.fn<Chat>(() => pending.promise);
    const { rerender } = render(<Harness chat={chat} />);
    rerender(<Harness chat={chat} question={{ id: 1, text: "one" }} />);
    rerender(<Harness chat={chat} question={{ id: 2, text: "two" }} />);
    expect(chat).toHaveBeenCalledTimes(1);
    await act(async () => pending.resolve("done"));
  });

  it("ignores a blank question", () => {
    const chat = fakeChat();
    render(<Harness chat={chat} question={{ id: 1, text: "   " }} />);
    expect(chat).not.toHaveBeenCalled();
  });
});
