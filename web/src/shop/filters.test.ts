import { describe, expect, it } from "vitest";
import type { Offer, StoreMatches } from "../types";
import { categoriesOf, featuredOffers, filterStores, qualifiedOnly } from "./filters";

const offer = (id: string, type: Offer["type"], bps: number, eligible: boolean): Offer => ({
  offer_id: id, type, headline_bps: bps, headline_label: `${bps / 100}%`, groups: [], excluded_items: [],
  annual_cap_cents: null, annual_cap_dollars: null, stackable_with_cash_back: true, expires_on: null,
  eligible, reasons: eligible ? [] : ["NOT_VERIFIED"], reason_text: eligible ? [] : ["You haven't verified a group."],
});
const store = (id: string, name: string, category: string, offers: Offer[]): StoreMatches => ({
  store_id: id, name, blurb: `${name} blurb`, category, art: null, image: null, image_credit: null, offers,
});

const A = store("s1", "Fjordline Outdoors", "Outdoors", [offer("o1", "group_discount", 3000, true), offer("o2", "cash_back", 350, true)]);
const B = store("s2", "Voltage Electronics", "Electronics", [offer("o3", "group_discount", 1500, false), offer("o4", "cash_back", 200, true)]);
const C = store("s3", "Inkwell Books", "Books", [offer("o5", "group_discount", 2000, false)]);
const D = store("s6", "Lumen Laptops", "Electronics", [offer("o9", "group_discount", 1200, true)]);
const ALL = [A, B, C, D];

describe("qualifiedOnly", () => {
  it("keeps only the offers the member qualifies for", () => {
    const result = qualifiedOnly(ALL);
    expect(result.flatMap((s) => s.offers.map((o) => o.offer_id))).toEqual(["o1", "o2", "o4", "o9"]);
    expect(result.every((s) => s.offers.every((o) => o.eligible))).toBe(true);
  });

  it("hides a store that has no qualified offer", () => {
    expect(qualifiedOnly(ALL).map((s) => s.store_id)).toEqual(["s1", "s2", "s6"]);
  });

  it("leaves no trace of an offer that is not available, including its reason text", () => {
    expect(JSON.stringify(qualifiedOnly(ALL))).not.toMatch(/o3|o5|haven't verified|NOT_VERIFIED/);
  });

  it("does not change its input", () => {
    const before = JSON.stringify(ALL);
    qualifiedOnly(ALL);
    expect(JSON.stringify(ALL)).toBe(before);
  });

  it("gives an empty list when nothing qualifies", () => {
    expect(qualifiedOnly([C])).toEqual([]);
    expect(qualifiedOnly([])).toEqual([]);
  });
});

describe("categoriesOf", () => {
  it("lists categories in the order they first appear, with the number of stores", () => {
    expect(categoriesOf(qualifiedOnly(ALL))).toEqual([
      { name: "Outdoors", count: 1 },
      { name: "Electronics", count: 2 },
    ]);
  });

  it("is empty for no stores", () => {
    expect(categoriesOf([])).toEqual([]);
  });
});

describe("filterStores", () => {
  const stores = qualifiedOnly(ALL);

  it("returns everything for no category and no query", () => {
    expect(filterStores(stores, { category: null, query: "" })).toEqual(stores);
  });

  it("filters by category", () => {
    expect(filterStores(stores, { category: "Electronics", query: "" }).map((s) => s.store_id)).toEqual(["s2", "s6"]);
  });

  it("searches name, blurb and category, ignoring case and surrounding spaces", () => {
    expect(filterStores(stores, { category: null, query: "  LUMEN " }).map((s) => s.store_id)).toEqual(["s6"]);
    expect(filterStores(stores, { category: null, query: "outd" }).map((s) => s.store_id)).toEqual(["s1"]);
    expect(filterStores(stores, { category: null, query: "voltage electronics blurb" }).map((s) => s.store_id)).toEqual(["s2"]);
  });

  it("combines a category and a query", () => {
    expect(filterStores(stores, { category: "Electronics", query: "lumen" }).map((s) => s.store_id)).toEqual(["s6"]);
    expect(filterStores(stores, { category: "Outdoors", query: "lumen" })).toEqual([]);
  });

  it("treats a query as plain text, not a pattern", () => {
    expect(filterStores(stores, { category: null, query: ".*" })).toEqual([]);
    expect(filterStores(stores, { category: null, query: "(" })).toEqual([]);
  });
});

describe("featuredOffers", () => {
  it("picks the best qualified offer of each store, largest first", () => {
    expect(featuredOffers(ALL, 3).map((f) => [f.store.store_id, f.offer.offer_id])).toEqual([
      ["s1", "o1"], ["s6", "o9"], ["s2", "o4"],
    ]);
  });

  it("never features an offer that is not available, even when given unfiltered stores", () => {
    const ids = featuredOffers(ALL, 10).map((f) => f.offer.offer_id);
    expect(ids).not.toContain("o3");
    expect(ids).not.toContain("o5");
  });

  it("respects the limit and keeps store order for ties", () => {
    expect(featuredOffers(ALL, 1)).toHaveLength(1);
    const tie = [store("a", "A", "X", [offer("t1", "group_discount", 1000, true)]), store("b", "B", "X", [offer("t2", "group_discount", 1000, true)])];
    expect(featuredOffers(tie, 2).map((f) => f.store.store_id)).toEqual(["a", "b"]);
  });

  it("is empty when nothing qualifies", () => {
    expect(featuredOffers([C], 3)).toEqual([]);
    expect(featuredOffers([], 3)).toEqual([]);
  });
});
