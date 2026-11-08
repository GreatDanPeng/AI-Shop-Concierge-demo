import { useCallback, useEffect, useState } from "react";
import { storeIdOf } from "../links";

// Tiny hash routing (no dependency): "#/" home, "#/me" verifications, "#/store/<id>" a store page.
// Anything else is home, so a hand-edited or hostile hash can never reach the page as markup or a path.
export type Route = { name: "home" } | { name: "me" } | { name: "store"; id: string };

export function parseRoute(hash: string): Route {
  if (hash === "#/me") return { name: "me" };
  const id = storeIdOf(hash);
  return id === null ? { name: "home" } : { name: "store", id };
}

export function useRoute(): [Route, (hash: string) => void] {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const navigate = useCallback((hash: string) => {
    if (window.location.hash === hash) setRoute(parseRoute(hash));
    else window.location.hash = hash;
  }, []);
  return [route, navigate];
}
