import type { Ref } from "react";
import { Icon } from "../design/icons";
import type { DemoMember } from "../types";
import { memberSummary } from "./labels";

export type TopBarProps = {
  members: DemoMember[];
  choice: string;
  onChoose: (id: string) => void;
  query: string;
  onQuery: (query: string) => void;
  drawerOpen: boolean;
  onMenu: () => void;
  menuRef: Ref<HTMLButtonElement>; // so the focus can come back here when the drawer closes
};

export function TopBar({ members, choice, onChoose, query, onQuery, drawerOpen, onMenu, menuRef }: TopBarProps) {
  return (
    <header className="topbar">
      <button ref={menuRef} type="button" className="topbar-menu" aria-label={drawerOpen ? "Close menu" : "Open menu"} aria-expanded={drawerOpen} onClick={onMenu}>
        <Icon name="menu" />
      </button>
      <a className="brand" href="#/">Demo Shop</a>
      <div className="search">
        <Icon name="search" size={18} />
        <input type="search" aria-label="Search stores" placeholder="Search stores" value={query} onChange={(e) => onQuery(e.target.value)} />
      </div>
      <div className="picker">
        <label htmlFor="member-picker">Signed in as</label>
        <select id="member-picker" value={choice} onChange={(e) => onChoose(e.target.value)}>
          <option value="">Choose a demo member…</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.display_name} — {memberSummary(member)}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
