import type { Identity } from "../types";
import { words } from "./labels";

export function IdentityCard({ identity }: { identity: Identity }) {
  return (
    <section className="identity" aria-label="Your verifications">
      <h2>{identity.display_name}</h2>
      {identity.verifications.length === 0 ? (
        <p>No verified group yet. Cash back offers are open to every member.</p>
      ) : (
        <ul>
          {identity.verifications.map((v) => (
            <li key={v.group}>
              <strong>{words(v.group)}</strong>{" "}
              {v.status === "valid" && <span className="ok">Valid until {v.expires_on}</span>}
              {v.status === "expired" && <span className="bad">Expired on {v.expires_on}</span>}
              {v.status === "missing" && <span className="bad">Not valid yet</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
