import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createApi } from "./api";
import "./design/tokens.css";
import "./design/art.css";
import { App, type ConciergeLink } from "./shop/App";
import "./shop/shop.css";

// The concierge widget is a separate script (/widget.js) that exposes window.Concierge. The shop
// talks to it like any host page would, and does nothing if it has not loaded.
const concierge: ConciergeLink = {
  setStore: (id, name) => window.Concierge?.setStore(id, name),
  open: () => window.Concierge?.open(),
  ask: (text) => window.Concierge?.ask(text),
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App api={createApi()} concierge={concierge} />
  </StrictMode>,
);
