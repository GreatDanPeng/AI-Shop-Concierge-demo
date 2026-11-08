import type { Offer, StoreMatches } from "../types";

// Pure functions behind the home page. The page only ever shows offers the member qualifies for:
// an offer that is not available is removed here, with its reason text, and never reaches the screen.

export type CategoryCount = { name: string; count: number };
export type Featured = { store: StoreMatches; offer: Offer };

export function qualifiedOnly(stores: StoreMatches[]): StoreMatches[] {
  return stores
    .map((store) => ({ ...store, offers: store.offers.filter((offer) => offer.eligible) }))
    .filter((store) => store.offers.length > 0);
}

// Categories in the order they first appear, with the number of stores in each.
export function categoriesOf(stores: StoreMatches[]): CategoryCount[] {
  const counts = new Map<string, number>();
  for (const store of stores) counts.set(store.category, (counts.get(store.category) ?? 0) + 1);
  return [...counts].map(([name, count]) => ({ name, count }));
}

// A category and a search text, both optional. The text is matched as plain text, never as a pattern.
export function filterStores(stores: StoreMatches[], { category, query }: { category: string | null; query: string }): StoreMatches[] {
  const needle = query.trim().toLowerCase();
  return stores.filter((store) => {
    if (category && store.category !== category) return false;
    if (!needle) return true;
    return [store.name, store.blurb, store.category].some((text) => text.toLowerCase().includes(needle));
  });
}

// The best qualified offer of each store (largest headline first), best stores first.
export function featuredOffers(stores: StoreMatches[], limit = 3): Featured[] {
  const best: Featured[] = [];
  for (const store of stores) {
    const top = store.offers
      .filter((offer) => offer.eligible)
      .reduce<Offer | null>((winner, offer) => (winner === null || offer.headline_bps > winner.headline_bps ? offer : winner), null);
    if (top) best.push({ store, offer: top });
  }
  // sort() is stable, so equal headlines keep the stores' own order
  return best.sort((a, b) => b.offer.headline_bps - a.offer.headline_bps).slice(0, limit);
}
