import { useEffect, useRef, type FormEvent, type KeyboardEvent } from "react";
import { Icon } from "./icons";

const MAX_MESSAGE_CHARS = 2000; // the server's limit
const MAX_HEIGHT_PX = 200;

// A small hint under the text box: its label is all that shows, its text is what it puts in the box.
export type PromptSuggestion = { label: string; text: string };

export type ChatInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: (text: string) => void;
  placeholder?: string;
  disabled?: boolean;
  label?: string;
  suggestions?: PromptSuggestion[];
};

// The wide input at the heart of the home page: intent first. Enter sends, Shift+Enter is a new line,
// Enter that confirms an input-method choice is ignored, and the box grows with what you type.
// Suggested prompts sit inside the box, under the text; clicking one only fills the box.
export function ChatInput({ value, onChange, onSend, placeholder, disabled = false, label = "Ask the concierge", suggestions = [] }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (text && !disabled) onSend(text);
  };

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      className="chat-input"
      onSubmit={(event: FormEvent) => {
        event.preventDefault();
        submit();
      }}
    >
      <textarea
        ref={ref}
        aria-label={label}
        rows={1}
        maxLength={MAX_MESSAGE_CHARS}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
      <button type="submit" className="chat-input-send" disabled={disabled || value.trim() === ""}>
        <Icon name="send" size={18} />
        <span>Send</span>
      </button>
      {suggestions.length > 0 && (
        <div className="chat-input-prompts" role="group" aria-label="Suggested prompts">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.label}
              type="button"
              className="prompt-chip"
              disabled={disabled}
              onClick={() => {
                onChange(suggestion.text);
                ref.current?.focus();
              }}
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
