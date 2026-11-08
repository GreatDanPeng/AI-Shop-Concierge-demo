import { Icon } from "../design/icons";
import { StoreArt } from "../design/StoreArt";
import type { Offer, StoreMatches } from "../types";
import { Estimator } from "./Estimator";
import { offerLabel, words } from "./labels";
import type { ShopApi } from "./useShopData";

function OfferDetail({ offer }: { offer: Offer }) {
  return (
    <li className="offer-card">
      <h2>{offerLabel(offer)}</h2>
      <p>{offer.groups.length > 0 ? `For verified: ${offer.groups.map(words).join(", ")}` : "Every member"}</p>
      {offer.excluded_items.length > 0 && <p>Excludes: {offer.excluded_items.join(", ")}</p>}
      {offer.annual_cap_dollars && <p>Annual cap: {offer.annual_cap_dollars}</p>}
      {offer.expires_on && <p>Ends {offer.expires_on}</p>}
      {!offer.stackable_with_cash_back && <p>Can't be combined with cash back</p>}
    </li>
  );
}

const BackLink = () => (
  <a className="back" href="#/">
    <Icon name="arrow-left" />
    <span>All offers</span>
  </a>
);

// A store page: the offers the member qualifies for, in detail, and a cart estimate.
export function StoreDetail({ store, api, onAsk }: { store: StoreMatches | undefined; api: Pick<ShopApi, "estimate">; onAsk: () => void }) {
  if (!store) {
    return (
      <div className="store-page">
        <BackLink />
        <p className="lead">That store isn't in your offers.</p>
      </div>
    );
  }
  return (
    <article className="store-page">
      <BackLink />
      <StoreArt art={store.art} image={store.image} credit={store.image_credit} />
      <h1>{store.name}</h1>
      <p className="lead">{store.blurb}</p>
      <ul className="offer-list" aria-label="Offers for you">
        {store.offers.map((offer) => (
          <OfferDetail key={offer.offer_id} offer={offer} />
        ))}
      </ul>
      <Estimator storeId={store.store_id} api={api} />
      <button type="button" className="button button-secondary" onClick={onAsk}>
        <Icon name="sparkle" size={18} />
        <span>Ask the concierge about this store</span>
      </button>
    </article>
  );
}
