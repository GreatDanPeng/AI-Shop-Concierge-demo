import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Sidebar, type SidebarGroup } from "../design/Sidebar";
import { categoriesOf, featuredOffers, filterStores, qualifiedOnly } from "./filters";
import { Home } from "./Home";
import { IdentityCard } from "./IdentityCard";
import { useRoute } from "./route";
import { StoreDetail } from "./StoreDetail";
import { TopBar } from "./TopBar";
import { useShopData, type ShopApi } from "./useShopData";

// How the page talks to the concierge widget (a separate script that exposes window.Concierge).
export type ConciergeLink = {
  setStore(id: string | null, name?: string): void;
  open(): void;
  ask(text: string): void;
};

export function App({ api, concierge }: { api: ShopApi; concierge: ConciergeLink }) {
  const data = useShopData(api);
  const [route, navigate] = useRoute();
  const [category, setCategory] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const menuRef = useRef<HTMLButtonElement>(null);
  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    menuRef.current?.focus(); // the focus goes back to where the drawer was opened from
  }, []);

  // The page shows only what the member qualifies for: not-available offers never get this far.
  const qualified = useMemo(() => (data.discounts ? qualifiedOnly(data.discounts.stores) : []), [data.discounts]);
  const categories = useMemo(() => categoriesOf(qualified), [qualified]);
  const visible = useMemo(() => filterStores(qualified, { category, query }), [qualified, category, query]);
  const featured = useMemo(() => featuredOffers(qualified, 3), [qualified]);

  const storeId = route.name === "store" ? route.id : null;
  const currentStore = qualified.find((s) => s.store_id === storeId);
  useEffect(() => {
    if (currentStore) concierge.setStore(currentStore.store_id, currentStore.name);
    else concierge.setStore(null);
  }, [currentStore?.store_id, currentStore?.name, concierge]); // eslint-disable-line react-hooks/exhaustive-deps

  const goHome = () => {
    if (route.name !== "home") navigate("#/");
  };

  const groups: SidebarGroup[] = [
    { id: "shop", label: "Shop", items: [
      { id: "all", label: "All offers", icon: "tag", count: qualified.length },
      ...categories.map((c) => ({ id: `cat:${c.name}`, label: c.name, icon: "tag" as const, count: c.count })),
    ] },
    { id: "me", label: "Me", items: [{ id: "me", label: "My verifications", icon: "shield" }] },
  ];
  const activeId = route.name === "me" ? "me" : category ? `cat:${category}` : "all";
  function select(id: string) {
    if (id === "me") return navigate("#/me");
    setCategory(id === "all" ? null : id.slice("cat:".length));
    goHome();
  }

  let content;
  if (!data.loaded) content = <p className="lead">Loading…</p>;
  else if (route.name === "me" && data.identity) content = <IdentityCard identity={data.identity} />;
  else if (route.name === "store" && data.identity) content = <StoreDetail store={currentStore} api={api} onAsk={() => concierge.open()} />;
  else {
    content = (
      <Home
        identity={data.identity}
        noOffers={data.identity !== null && qualified.length === 0}
        stores={visible}
        featured={featured}
        showFeatured={category === null && query.trim() === ""}
        categories={categories}
        category={category}
        onCategory={(next) => { setCategory(next); goHome(); }}
        onAsk={(text) => concierge.ask(text)}
      />
    );
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main" onClick={(event) => { event.preventDefault(); mainRef.current?.focus(); }}>
        Skip to content
      </a>
      <Sidebar
        groups={groups}
        activeId={activeId}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed(!collapsed)}
        drawerOpen={drawerOpen}
        onDrawerClose={closeDrawer}
        onSelect={select}
      />
      <div className="content">
        <TopBar
          members={data.members}
          choice={data.choice}
          onChoose={(id) => void data.choose(id)}
          query={query}
          onQuery={(next) => { setQuery(next); goHome(); }}
          drawerOpen={drawerOpen}
          onMenu={() => (drawerOpen ? closeDrawer() : setDrawerOpen(true))}
          menuRef={menuRef}
        />
        <main id="main" tabIndex={-1} ref={mainRef}>
          {data.error && <p className="banner banner-error" role="alert">{data.error}</p>}
          {data.health && !data.health.assistant.configured && (
            <p className="banner">The concierge is not set up on this server yet (see the README), but your matches below still work.</p>
          )}
          {content}
        </main>
        <footer className="footer">
          <p>Unofficial concept demo. All offers and members are fictional. Brand names are used for illustration only: none of these brands offers these discounts or is affiliated with this demo. Not affiliated with ID.me.</p>
        </footer>
      </div>
    </div>
  );
}
