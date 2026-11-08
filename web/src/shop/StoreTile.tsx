import { StoreArt } from "../design/StoreArt";
import type { StoreMatches } from "../types";
import { offerLabel } from "./labels";

// One store in the grid: its picture, name, category and the offers the member qualifies for.
export function StoreTile({ store }: { store: StoreMatches }) {
  return (
    <li className="tile">
      <a className="tile-link" href={`#/store/${store.store_id}`}>
        <StoreArt art={store.art} image={store.image} credit={store.image_credit} />
        <div className="tile-body">
          <h3>{store.name}</h3>
          <p className="tile-category">{store.category}</p>
          <ul className="tile-offers">
            {store.offers.map((offer) => (
              <li key={offer.offer_id} className="offer-chip">{offerLabel(offer)}</li>
            ))}
          </ul>
        </div>
      </a>
    </li>
  );
}
