import { useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import { createApi, type Api } from "../api";
import { ConciergeWidget, type Store } from "./ConciergeWidget";
import tokens from "../design/tokens.css?inline";
import css from "./widget.css?inline";

export type MountOptions = {
  apiBase?: string;
  storeId?: string;
  storeName?: string;
  api?: Pick<Api, "chat">; // for tests
};

// What a host page can do with the widget (also reachable as window.Concierge).
export type Theme = "auto" | "light" | "dark";
export type Controller = {
  open(): void;
  close(): void;
  setStore(id: string | null, name?: string): void;
  ask(text: string): void; // opens the panel and sends the question
  setTheme(theme: Theme): void; // light or dark for the widget only; auto follows the system
  unmount(): void;
};

declare global {
  interface Window {
    Concierge?: Controller;
  }
}

type State = { open: boolean; store: Store; question: { id: number; text: string } | null };

function createState(store: Store) {
  let current: State = { open: false, store, question: null };
  const listeners = new Set<() => void>();
  return {
    get: () => current,
    set(patch: Partial<State>) {
      current = { ...current, ...patch };
      listeners.forEach((listener) => listener());
    },
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
  };
}

export function readOptions(script: HTMLScriptElement | null): MountOptions {
  const options: MountOptions = {};
  const read = (name: string) => script?.getAttribute(name)?.trim() || undefined;
  const apiBase = read("data-api-base");
  const storeId = read("data-store-id");
  const storeName = read("data-store-name");
  if (apiBase) options.apiBase = apiBase;
  if (storeId) options.storeId = storeId;
  if (storeName) options.storeName = storeName;
  return options;
}

function Root({ api, state }: { api: Pick<Api, "chat">; state: ReturnType<typeof createState> }) {
  const snapshot = useSyncExternalStore(state.subscribe, state.get);
  return (
    <ConciergeWidget
      api={api}
      store={snapshot.store}
      open={snapshot.open}
      onOpenChange={(open) => state.set({ open })}
      question={snapshot.question}
    />
  );
}

// Adds the widget to the page inside a shadow root, so the page's styles cannot break it and its
// styles cannot leak out. Safe to call twice: the second call returns the first widget.
export function mountConcierge(options: MountOptions = {}, parent: HTMLElement = document.body): Controller {
  if (window.Concierge) return window.Concierge;

  const api = options.api ?? createApi({ apiBase: options.apiBase });
  const state = createState(options.storeId ? { id: options.storeId, name: options.storeName } : null);

  const host = document.createElement("div");
  host.setAttribute("data-concierge-host", "");
  const shadow = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = tokens + css; // the tokens come along, so every colour and motion rule works in here
  const container = document.createElement("div");
  shadow.append(style, container);
  parent.appendChild(host);

  const root = createRoot(container);
  root.render(<Root api={api} state={state} />);
  let asked = 0;

  const controller: Controller = {
    open: () => state.set({ open: true }),
    close: () => state.set({ open: false }),
    setStore: (id, name) => state.set({ store: id ? { id, name } : null }),
    ask(text) {
      if (!text.trim()) return;
      state.set({ open: true, question: { id: ++asked, text } });
    },
    setTheme(theme) {
      if (theme === "auto") host.removeAttribute("data-theme");
      else host.setAttribute("data-theme", theme);
    },
    unmount() {
      root.unmount();
      host.remove();
      if (window.Concierge === controller) delete window.Concierge;
    },
  };
  window.Concierge = controller;
  return controller;
}
