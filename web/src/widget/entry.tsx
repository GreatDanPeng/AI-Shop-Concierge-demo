// The script a page loads:  <script src="/widget.js" data-store-id="s1" defer></script>
// Optional attributes: data-store-id, data-store-name, data-api-base (another origin needs CORS).
import { mountConcierge, readOptions } from "./mount";

if (typeof window !== "undefined" && !window.Concierge) {
  const options = readOptions(document.currentScript as HTMLScriptElement | null);
  const start = () => mountConcierge(options);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}
