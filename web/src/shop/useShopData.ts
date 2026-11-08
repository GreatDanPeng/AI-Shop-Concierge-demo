import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Api } from "../api";
import { describeError } from "../errors";
import type { DemoMember, Discounts, Health, Identity } from "../types";

export type ShopApi = Pick<Api, "health" | "demoMembers" | "switchMember" | "me" | "discounts" | "estimate">;

// Loads who is signed in and what they match. The server is the source of truth, and only the latest
// request may update the page, so a slow answer for an earlier choice can never overwrite a later one.
export function useShopData(api: ShopApi) {
  const [members, setMembers] = useState<DemoMember[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [discounts, setDiscounts] = useState<Discounts | null>(null);
  const [choice, setChoice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const latestLoad = useRef(0);

  const load = useCallback(async () => {
    const mine = ++latestLoad.current;
    try {
      const [me, matches] = await Promise.all([api.me(), api.discounts()]);
      if (mine !== latestLoad.current) return;
      setIdentity(me);
      setDiscounts(matches);
      setChoice(me.member_id);
      setError(null);
    } catch (problem) {
      if (mine !== latestLoad.current) return;
      setIdentity(null);
      setDiscounts(null);
      setError(problem instanceof ApiError && problem.status === 401 ? null : describeError(problem));
    }
    setLoaded(true);
  }, [api]);

  useEffect(() => {
    api.demoMembers().then(setMembers).catch(() => setMembers([]));
    api.health().then(setHealth).catch(() => setHealth(null));
    void load();
  }, [api, load]);

  const choose = useCallback(async (id: string) => {
    setChoice(id);
    if (!id) return;
    try {
      await api.switchMember(id);
    } catch (problem) {
      setError(describeError(problem));
      return;
    }
    await load();
  }, [api, load]);

  return { members, health, identity, discounts, choice, error, loaded, choose };
}
