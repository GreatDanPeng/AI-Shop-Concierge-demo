import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { Api } from "../api";
import { Icon } from "../design/icons";
import { describeError } from "../errors";
import { ReplyText } from "../reply";

export type Store = { id: string; name?: string } | null;

export type ConciergeProps = {
  api: Pick<Api, "chat">;
  store: Store;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  // A question handed over by the page (the home ask box). Each new id is sent once.
  question?: { id: number; text: string } | null;
};

type ChatMessage = { id: number; role: "user" | "assistant" | "error"; text: string };

const MAX_MESSAGE_CHARS = 2000; // the server's limit
const NARROW_SCREEN = "(max-width: 480px)"; // where the panel covers the page (same as widget.css)
const SUGGESTIONS = [
  "What discounts can I get here?",
  "Why isn't my discount showing?",
  "I'm buying $200 of stuff. What do I pay?",
];

export function ConciergeWidget({ api, store, open, onOpenChange, question = null }: ConciergeProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const busy = useRef(false); // set synchronously, so a fast double submit cannot slip through
  const nextId = useRef(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const handledQuestion = useRef<number | null>(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages, pending, open]);

  const add = (role: ChatMessage["role"], text: string) =>
    setMessages((all) => [...all, { id: nextId.current++, role, text }]);

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || busy.current) return;
    busy.current = true;
    setPending(true);
    add("user", text);
    setDraft("");
    try {
      add("assistant", await api.chat(text, store?.id ?? null));
    } catch (error) {
      add("error", describeError(error));
    } finally {
      busy.current = false;
      setPending(false);
    }
  }

  useEffect(() => {
    if (question && question.id !== handledQuestion.current) {
      handledQuestion.current = question.id;
      void send(question.text); // ignored if blank, or if an answer is still on its way
    }
  }, [question]); // eslint-disable-line react-hooks/exhaustive-deps

  function onInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter is a new line; Enter that confirms an input-method choice is ignored.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void send(draft);
    }
  }

  // A link in an answer opens a store page behind the panel. On a small screen the panel would hide it.
  function onReplyLink() {
    if (typeof window.matchMedia === "function" && window.matchMedia(NARROW_SCREEN).matches) onOpenChange(false);
  }

  function onPanelKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") {
      onOpenChange(false);
      launcherRef.current?.focus();
    }
  }

  return (
    <div className="cw-root">
      {open && (
        <section className="cw-panel" role="dialog" aria-label="Concierge chat" onKeyDown={onPanelKeyDown}>
          <header className="cw-header">
            <span className="cw-title"><Icon name="sparkle" size={18} /><strong>Concierge</strong></span>
          </header>
          <div className="cw-log" role="log" aria-live="polite" ref={logRef}>
            {messages.length === 0 && (
              <div className="cw-suggestions">
                {SUGGESTIONS.map((suggestion) => (
                  <button key={suggestion} type="button" className="cw-chip" onClick={() => void send(suggestion)}>
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
            {messages.map((message) =>
              message.role === "assistant" ? (
                <div key={message.id} className="cw-msg cw-bot">
                  <ReplyText text={message.text} onLink={onReplyLink} />
                </div>
              ) : message.role === "error" ? (
                <div key={message.id} className="cw-msg cw-error" role="alert">
                  {message.text}
                </div>
              ) : (
                <div key={message.id} className="cw-msg cw-user">
                  <p>{message.text}</p>
                </div>
              ),
            )}
            {pending && <div className="cw-msg cw-bot cw-thinking">Thinking…</div>}
          </div>
          <form
            className="cw-composer"
            onSubmit={(event) => {
              event.preventDefault();
              void send(draft);
            }}
          >
            <textarea
              ref={inputRef}
              aria-label="Your question"
              rows={2}
              maxLength={MAX_MESSAGE_CHARS}
              placeholder="Ask about your discounts…"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onInputKeyDown}
            />
            <button type="submit" className="cw-send" disabled={pending || draft.trim() === ""}>
              <Icon name="send" size={16} />
              <span>Send</span>
            </button>
          </form>
        </section>
      )}
      <button
        ref={launcherRef}
        type="button"
        className="cw-launcher"
        aria-label={open ? "Close concierge chat" : "Open concierge chat"}
        aria-expanded={open}
        onClick={() => onOpenChange(!open)}
      >
        <Icon name="sparkle" size={26} />
      </button>
    </div>
  );
}
