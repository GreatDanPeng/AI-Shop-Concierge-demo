import { useState } from "react";
import { ChatInput, type PromptSuggestion } from "../design/ChatInput";
import { StoreArt } from "../design/StoreArt";
import type { Identity, StoreMatches } from "../types";
import type { CategoryCount, Featured } from "./filters";
import { offerLabel } from "./labels";
import { StoreTile } from "./StoreTile";

// Small prompts shown inside the ask box, by verb. Clicking one fills the box; the person decides whether to send.
const PROMPTS: PromptSuggestion[] = [
  { label: "Show my best deals", text: "What are the best discounts I qualify for?" },
  { label: "Check why an offer is missing", text: "Why isn't my discount showing?" },
  { label: "Estimate a cart", text: "I'm buying $200 of stuff. What do I pay and what do I get back?" },
];
const WHY = "Why isn't my discount showing?";

export type HomeProps = {
  identity: Identity | null;
  noOffers: boolean; // signed in, but nothing qualifies anywhere
  stores: StoreMatches[]; // after the category and search filters
  featured: Featured[];
  showFeatured: boolean; // only while nothing narrows the list: no category chosen, no search text
  categories: CategoryCount[];
  category: string | null;
  onCategory: (category: string | null) => void;
  onAsk: (text: string) => void;
};

export function Home({ identity, noOffers, stores, featured, showFeatured, categories, category, onCategory, onAsk }: HomeProps) {
  const [draft, setDraft] = useState("");
  const send = (text: string) => {
    onAsk(text);
    setDraft("");
  };

  if (!identity) {
    return (
      <section className="home">
        <h1 className="greeting">Hi, who's shopping today?</h1>
        <p className="lead">Choose a demo member above to see which discounts you match.</p>
      </section>
    );
  }
  const whyButton = (
    <button type="button" className="link-button" onClick={() => onAsk(WHY)}>Ask the concierge why</button>
  );
  return (
    <section className="home">
      <h1 className="greeting">Hi {identity.display_name}, what are you shopping for?</h1>
      <ChatInput value={draft} onChange={setDraft} onSend={send} placeholder="Ask the concierge about your discounts…" suggestions={PROMPTS} />

      {noOffers ? (
        <p className="empty">No offers matched right now. {whyButton}</p>
      ) : (
        <>
          <div className="chips" role="group" aria-label="Categories">
            <button type="button" className="chip" aria-pressed={category === null} onClick={() => onCategory(null)}>All</button>
            {categories.map((c) => (
              <button key={c.name} type="button" className="chip" aria-pressed={category === c.name} onClick={() => onCategory(c.name)}>
                {c.name}
              </button>
            ))}
          </div>

          {showFeatured && featured.length > 0 && <FeaturedStrip featured={featured} />}

          <h2 className="section-title">Your offers</h2>
          {stores.length > 0 ? (
            <ul className="tile-grid" aria-label="Your offers">
              {stores.map((store) => (
                <StoreTile key={store.store_id} store={store} />
              ))}
            </ul>
          ) : (
            <p className="empty">No stores match your search or filter.</p>
          )}
          <p className="quiet">Not seeing an offer? {whyButton}</p>
        </>
      )}
    </section>
  );
}

function FeaturedStrip({ featured }: { featured: Featured[] }) {
  return (
    <>
      <h2 className="section-title">Best for you</h2>
      <ul className="featured" aria-label="Best for you">
        {featured.map(({ store, offer }) => (
          <li key={store.store_id}>
            <a className="featured-card" href={`#/store/${store.store_id}`}>
              <StoreArt art={store.art} image={store.image} credit={store.image_credit} />
              <span className="featured-offer">{offerLabel(offer)}</span>
              <span className="featured-store">{store.name}</span>
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}
