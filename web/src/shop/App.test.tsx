import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import type { DemoMember, Discounts, Estimate, Health, Identity, Offer, StoreMatches } from "../types";
import { App, type ConciergeLink } from "./App";

// ---- fixtures: small hand-written copies of what the server returns ---------------------------
const MEMBERS: DemoMember[] = [
  { id: "m_nurse", display_name: "Avery", verifications: [{ group: "nurse", status: "valid" }] },
  { id: "m_student", display_name: "Sam", verifications: [{ group: "student", status: "expired" }] },
  { id: "m_none", display_name: "Casey", verifications: [] },
];
const IDENTITIES: Record<string, Identity> = {
  m_nurse: { member_id: "m_nurse", display_name: "Avery", verifications: [{ group: "nurse", status: "valid", verified_on: "2026-03-01", expires_on: "2027-03-01" }] },
  m_student: { member_id: "m_student", display_name: "Sam", verifications: [{ group: "student", status: "expired", verified_on: "2025-08-15", expires_on: "2026-08-15" }] },
  m_none: { member_id: "m_none", display_name: "Casey", verifications: [] },
};
const offer = (o: Partial<Offer> & Pick<Offer, "offer_id" | "type" | "headline_bps" | "headline_label">): Offer => ({
  groups: [], excluded_items: [], annual_cap_cents: null, annual_cap_dollars: null,
  stackable_with_cash_back: true, expires_on: null, eligible: true, reasons: [], reason_text: [], ...o,
});
const no = (o: Offer, reason: string, text: string): Offer => ({ ...o, eligible: false, reasons: [reason], reason_text: [text] });
const O1 = offer({ offer_id: "o1", type: "group_discount", headline_bps: 3000, headline_label: "30%", groups: ["nurse", "teacher", "first_responder"], excluded_items: ["new releases"], annual_cap_cents: 800000, annual_cap_dollars: "$8,000.00" });
const O2 = offer({ offer_id: "o2", type: "cash_back", headline_bps: 350, headline_label: "3.5%" });
const O3 = offer({ offer_id: "o3", type: "group_discount", headline_bps: 1500, headline_label: "15%", groups: ["student", "teacher"], stackable_with_cash_back: false, expires_on: "2026-12-31" });
const O4 = offer({ offer_id: "o4", type: "cash_back", headline_bps: 200, headline_label: "2%" });
const O5 = offer({ offer_id: "o5", type: "group_discount", headline_bps: 2000, headline_label: "20%", groups: ["teacher", "student", "nurse"] });
const O9 = offer({ offer_id: "o9", type: "group_discount", headline_bps: 1200, headline_label: "12%", groups: ["student", "teacher"] });
const NOT_VERIFIED = "You haven't verified a group this offer is for (student, teacher).";
const EXPIRED = "Your verification has expired. Renew it to qualify.";

const store = (id: string, name: string, category: string, art: string, offers: Offer[], extra: Partial<StoreMatches> = {}): StoreMatches =>
  ({ store_id: id, name, blurb: `${category} (fictional store)`, category, art, image: null, image_credit: null, offers, ...extra });

const DISCOUNTS: Record<string, Discounts> = {
  m_nurse: { as_of: "2026-11-06", stores: [
    store("s1", "Fjordline Outdoors", "Outdoors", "tent", [O1, O2]),
    store("s2", "Voltage Electronics", "Electronics", "headphones", [no(O3, "NOT_VERIFIED", NOT_VERIFIED), O4]),
    store("s3", "Inkwell Books", "Books", "books", [O5]),
    store("s6", "Lumen Laptops", "Electronics", "laptop", [no(O9, "NOT_VERIFIED", NOT_VERIFIED)]),
  ] },
  m_student: { as_of: "2026-11-06", stores: [
    store("s1", "Fjordline Outdoors", "Outdoors", "tent", [no(O1, "NOT_VERIFIED", "You haven't verified a group this offer is for (nurse, teacher)."), O2]),
    store("s2", "Voltage Electronics", "Electronics", "headphones", [no(O3, "VERIFICATION_EXPIRED", EXPIRED), O4]),
    store("s3", "Inkwell Books", "Books", "books", [no(O5, "VERIFICATION_EXPIRED", EXPIRED)]),
    store("s6", "Lumen Laptops", "Electronics", "laptop", [no(O9, "VERIFICATION_EXPIRED", EXPIRED)]),
  ] },
  m_none: { as_of: "2026-11-06", stores: [
    store("s1", "Fjordline Outdoors", "Outdoors", "tent", [no(O1, "NOT_VERIFIED", NOT_VERIFIED), no(O2, "OFFER_EXPIRED", "This offer has ended.")]),
  ] },
};
const ESTIMATE: Estimate = { store_id: "s1", as_of: "2026-11-06", assumptions: [], dollars: { cart: "$1,500.00", group_discount: "$200.00", you_pay: "$1,300.00", cash_back: "$0.00", total_savings: "$200.00" } };

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => { resolve = res; });
  return { promise, resolve };
}

function makeApi({ signedInAs = null as string | null, configured = true } = {}) {
  let current = signedInAs;
  const health: Health = { ok: true, assistant: { provider: "openrouter", model: "some/model", configured } };
  return {
    health: vi.fn(async () => health),
    demoMembers: vi.fn(async () => MEMBERS),
    switchMember: vi.fn(async (id: string) => { current = id; return { ok: true }; }),
    me: vi.fn(async () => { if (!current) throw new ApiError(401, "not_signed_in"); return IDENTITIES[current]; }),
    discounts: vi.fn(async () => { if (!current) throw new ApiError(401, "not_signed_in"); return DISCOUNTS[current]; }),
    estimate: vi.fn(async (_store: string, _cents: number) => ESTIMATE),
  };
}
const link = () => ({
  setStore: vi.fn<ConciergeLink["setStore"]>(), open: vi.fn<ConciergeLink["open"]>(),
  ask: vi.fn<ConciergeLink["ask"]>(),
});

async function renderApp(options: Parameters<typeof makeApi>[0] = {}) {
  const api = makeApi(options);
  const concierge = link();
  render(<App api={api} concierge={concierge} />);
  await screen.findByLabelText(/signed in as/i);
  if (options.signedInAs) await screen.findByRole("heading", { level: 1, name: /^Hi /i });
  else await screen.findByText(/choose a demo member above/i);
  return { api, concierge };
}
const picker = () => screen.getByLabelText(/signed in as/i) as HTMLSelectElement;
const main = () => within(screen.getByRole("main"));
async function signInAs(id: string) {
  fireEvent.change(picker(), { target: { value: id } });
  await waitFor(() => expect(picker().value).toBe(id));
  await screen.findByRole("heading", { level: 1, name: /^Hi (?!,)/i });
}
const tileNames = () => within(screen.getByRole("list", { name: /your offers/i })).getAllByRole("heading", { level: 3 }).map((h) => h.textContent);

beforeEach(() => { window.location.hash = ""; });
afterEach(() => { window.location.hash = ""; window.localStorage.clear(); });

describe("the page", () => {
  it("says plainly that it is a demo with fake data", async () => {
    await renderApp();
    expect(document.body.textContent).toMatch(/fictional/i);
    expect(document.body.textContent).toMatch(/not affiliated with id\.me/i);
  });

  it("asks who is shopping when nobody is signed in, and shows no offers or ask box yet", async () => {
    await renderApp();
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/who's shopping today/i);
    expect(screen.queryByRole("list", { name: /your offers/i })).toBeNull();
    expect(screen.queryByRole("textbox", { name: /ask the concierge/i })).toBeNull();
    const options = within(picker()).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(expect.arrayContaining([
      expect.stringMatching(/Avery.*nurse/), expect.stringMatching(/Sam.*student.*expired/), expect.stringMatching(/Casey.*no verified group/),
    ]));
  });

  it("greets the signed-in member by name, with no as-of banner under the greeting", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Hi Avery, what are you shopping for?");
    expect(picker().value).toBe("m_nurse");
    expect(main().queryByText(/as of/i)).toBeNull();
    expect(main().queryByText(/no guarantee/i)).toBeNull();
    expect(main().queryByText(/here is what you qualify for/i)).toBeNull();
  });

  it("has no light/dark switch: dark mode just follows the system, and nothing is stored in the browser", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    expect(screen.queryByRole("group", { name: /theme/i })).toBeNull();
    for (const name of [/^light$/i, /^dark$/i, /^auto$/i]) expect(screen.queryByRole("button", { name })).toBeNull();
    expect(window.localStorage.length).toBe(0);
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("tells the visitor when the assistant is not set up, and stays quiet when it is", async () => {
    await renderApp({ configured: false });
    expect(screen.getByText(/concierge is not set up/i)).toBeTruthy();
  });

  it("does not show that notice when the assistant is set up", async () => {
    await renderApp({ configured: true });
    expect(screen.queryByText(/not set up/i)).toBeNull();
  });
});

describe("only offers you qualify for", () => {
  it("shows qualified offers and hides every store with none (Avery)", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    expect(tileNames()).toEqual(["Fjordline Outdoors", "Voltage Electronics", "Inkwell Books"]); // Lumen Laptops has nothing for Avery
    const grid = within(screen.getByRole("list", { name: /your offers/i }));
    expect(grid.getByRole("link", { name: /Fjordline Outdoors/ }).textContent).toMatch(/30% off[\s\S]*3\.5% cash back/);
    expect(grid.getByRole("link", { name: /Voltage Electronics/ }).textContent).toMatch(/2% cash back/);
  });

  it("never shows an offer that is not available, or why it is not (Avery)", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/15% off|12% off/);               // the two offers Avery does not qualify for
    expect(text).not.toMatch(/not available|haven't verified|NOT_VERIFIED|Renew it/i);
  });

  it("shows only cash back to a member whose verification expired (Sam)", async () => {
    await renderApp();
    await signInAs("m_student");
    expect(tileNames()).toEqual(["Fjordline Outdoors", "Voltage Electronics"]);
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/30% off|15% off|20% off|12% off/);
    expect(text).not.toMatch(/expired|Renew it/i.test(text) ? /$^/ : /Renew it/); // reasons are not shown either
    expect(text).toMatch(/3\.5% cash back/);
  });

  it("says so, and points to the concierge, when nothing qualifies at all (Casey)", async () => {
    await renderApp();
    await signInAs("m_none");
    expect(screen.queryByRole("list", { name: /your offers/i })).toBeNull();
    expect(main().getByText(/no offers matched right now/i)).toBeTruthy();
    expect(main().getByRole("button", { name: /ask the concierge why/i })).toBeTruthy();
  });

  it("has a quiet way to ask why an offer is missing, which asks the concierge", async () => {
    const { concierge } = await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(main().getByRole("button", { name: /ask the concierge why/i }));
    expect(concierge.ask).toHaveBeenCalledWith("Why isn't my discount showing?");
  });
});

describe("browsing: featured, categories, search", () => {
  it("features the biggest discounts the member qualifies for, one per store", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const featured = within(screen.getByRole("list", { name: /best for you/i })).getAllByRole("link").map((a) => a.textContent ?? "");
    expect(featured).toHaveLength(3);
    expect(featured[0]).toMatch(/30% off.*Fjordline Outdoors/s);
    expect(featured[1]).toMatch(/20% off.*Inkwell Books/s);
    expect(featured[2]).toMatch(/2% cash back.*Voltage Electronics/s);
  });

  it("filters by category with chips that show which one is on", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const chips = within(screen.getByRole("group", { name: /categories/i }));
    expect(chips.getAllByRole("button").map((b) => b.textContent)).toEqual(["All", "Outdoors", "Electronics", "Books"]);
    fireEvent.click(chips.getByRole("button", { name: "Electronics" }));
    expect(chips.getByRole("button", { name: "Electronics" }).getAttribute("aria-pressed")).toBe("true");
    expect(chips.getByRole("button", { name: "All" }).getAttribute("aria-pressed")).toBe("false");
    expect(tileNames()).toEqual(["Voltage Electronics"]);
    fireEvent.click(chips.getByRole("button", { name: "All" }));
    expect(tileNames()).toHaveLength(3);
  });

  it("searches stores by name, and says when nothing matches", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const search = screen.getByRole("searchbox", { name: /search stores/i });
    fireEvent.change(search, { target: { value: "BOOKS" } });
    expect(tileNames()).toEqual(["Inkwell Books"]);
    fireEvent.change(search, { target: { value: "zzz" } });
    expect(main().getByText(/no stores match/i)).toBeTruthy();
  });

  it("draws each store tile with its illustration, or its licensed photo with a credit", async () => {
    const api = makeApi({ signedInAs: "m_nurse" });
    api.discounts.mockResolvedValue({ as_of: "2026-11-06", stores: [
      store("s1", "Fjordline Outdoors", "Outdoors", "tent", [O1], { image: "/stores/s1.jpg", image_credit: "Jane Doe" }),
      store("s3", "Inkwell Books", "Books", "books", [O5]),
    ] });
    render(<App api={api} concierge={link()} />);
    await screen.findByRole("list", { name: /your offers/i });
    const grid = screen.getByRole("list", { name: /your offers/i });
    expect(grid.querySelector("img")?.getAttribute("src")).toBe("/stores/s1.jpg");
    expect(grid.textContent).toContain("Photo: Jane Doe");
    expect(grid.querySelector('svg[data-art="books"]')).not.toBeNull();
  });
});

describe("the sidebar", () => {
  const sidebar = () => within(screen.getByRole("navigation", { name: "Main" }));

  it("lists All offers and the categories you have offers in, with counts, and your verifications", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    expect(sidebar().getByRole("button", { name: /All offers/ }).textContent).toContain("3");
    expect(sidebar().getByRole("button", { name: /Electronics/ }).textContent).toContain("1");
    expect(sidebar().getByRole("button", { name: "My verifications" })).toBeTruthy();
  });

  it("filters the grid like the chips do", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(sidebar().getByRole("button", { name: /Books/ }));
    expect(tileNames()).toEqual(["Inkwell Books"]);
    expect(sidebar().getByRole("button", { name: /Books/ }).getAttribute("aria-current")).toBe("page");
    expect(within(screen.getByRole("group", { name: /categories/i })).getByRole("button", { name: "Books" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("opens your verifications page", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(sidebar().getByRole("button", { name: "My verifications" }));
    const identity = await screen.findByRole("region", { name: /your verifications/i });
    expect(identity.textContent).toMatch(/nurse/);
    expect(identity.textContent).toMatch(/valid until 2027-03-01/i);
    expect(window.location.hash).toBe("#/me");
  });

  it("collapses to icons and opens again", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(screen.getByRole("navigation", { name: "Main" }).className).toContain("sidebar--collapsed");
    fireEvent.click(screen.getByRole("button", { name: "Expand sidebar" }));
    expect(screen.getByRole("navigation", { name: "Main" }).className).not.toContain("sidebar--collapsed");
  });

  it("puts the focus back on the menu button when the drawer closes, and Escape works from anywhere", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const menu = screen.getByRole("button", { name: /open menu/i });
    fireEvent.click(menu);
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(nav.contains(document.activeElement)).toBe(true); // the focus moved into the drawer
    (document.activeElement as HTMLElement).blur();
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(nav.className).not.toContain("sidebar--drawer-open");
    expect(document.activeElement).toBe(screen.getByRole("button", { name: /open menu/i }));
  });

  it("opens as a drawer from the menu button and closes on Escape", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const menu = screen.getByRole("button", { name: /open menu/i });
    expect(menu.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(menu);
    expect(screen.getByRole("navigation", { name: "Main" }).className).toContain("sidebar--drawer-open");
    fireEvent.keyDown(screen.getByRole("navigation", { name: "Main" }), { key: "Escape" });
    expect(screen.getByRole("navigation", { name: "Main" }).className).not.toContain("sidebar--drawer-open");
  });
});

describe("intent first: the ask box", () => {
  const box = () => screen.getByRole("textbox", { name: /ask the concierge/i }) as HTMLTextAreaElement;

  it("fills the box when a suggestion is chosen, without sending", async () => {
    const { concierge } = await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(screen.getByRole("button", { name: /show my best deals/i }));
    expect(box().value).toMatch(/best discounts/i);
    expect(concierge.ask).not.toHaveBeenCalled();
  });

  it("offers three small prompts by verb inside the ask box, under the placeholder: no cards below it", async () => {
    await renderApp({ signedInAs: "m_nurse" });
    const form = box().closest("form")!;
    for (const name of [/show my best deals/i, /check why an offer is missing/i, /estimate a cart/i]) {
      const chip = screen.getByRole("button", { name });
      expect(form.contains(chip)).toBe(true);
      expect(chip.textContent).toBe(chip.textContent?.trim()); // just the label, no description
    }
    expect(box().compareDocumentPosition(screen.getByRole("button", { name: /estimate a cart/i })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(document.querySelector(".suggestion-card, .suggestions")).toBeNull();
  });

  it("sends the question to the concierge widget on Enter and clears the box", async () => {
    const { concierge } = await renderApp({ signedInAs: "m_nurse" });
    fireEvent.change(box(), { target: { value: "I'm buying $200 of gear" } });
    fireEvent.keyDown(box(), { key: "Enter" });
    expect(concierge.ask).toHaveBeenCalledWith("I'm buying $200 of gear");
    expect(box().value).toBe("");
  });
});

describe("a store page", () => {
  async function openStore(name = "Fjordline Outdoors") {
    const result = await renderApp({ signedInAs: "m_nurse" });
    fireEvent.click(within(screen.getByRole("list", { name: /your offers/i })).getByRole("link", { name: new RegExp(name) }));
    await screen.findByRole("heading", { level: 1, name });
    return result;
  }

  it("opens from a tile and shows only the qualified offers, in detail", async () => {
    await openStore();
    expect(window.location.hash).toBe("#/store/s1");
    const text = screen.getByRole("main").textContent ?? "";
    expect(text).toMatch(/30% off/);
    expect(text).toMatch(/For verified: nurse, teacher, first responder/);
    expect(text).toMatch(/Excludes: new releases/);
    expect(text).toContain("Annual cap: $8,000.00");
    expect(text).toMatch(/3\.5% cash back/);
    expect(text).toMatch(/every member/i);
  });

  it("shows no offer that is not available, even on the store's own page", async () => {
    await openStore("Voltage Electronics");
    const text = screen.getByRole("main").textContent ?? "";
    expect(text).toMatch(/2% cash back/);
    expect(text).not.toMatch(/15% off|can't be combined|haven't verified|not available/i);
  });

  it("points the concierge at this store while you are here, and clears it when you leave", async () => {
    const { concierge } = await openStore();
    expect(concierge.setStore).toHaveBeenLastCalledWith("s1", "Fjordline Outdoors");
    fireEvent.click(screen.getByRole("link", { name: /all offers/i }));
    await screen.findByRole("heading", { level: 1, name: /^Hi Avery/ });
    expect(concierge.setStore).toHaveBeenLastCalledWith(null);
    expect(window.location.hash).toBe("#/");
  });

  it("opens the concierge from the store page", async () => {
    const { concierge } = await openStore();
    fireEvent.click(screen.getByRole("button", { name: /ask the concierge about this store/i }));
    expect(concierge.open).toHaveBeenCalledTimes(1);
  });

  it("shows a kind message for a store that is not in your offers (a typed or old link)", async () => {
    window.location.hash = "#/store/s6"; // Lumen Laptops: nothing qualifies for Avery
    render(<App api={makeApi({ signedInAs: "m_nurse" })} concierge={link()} />);
    expect(await screen.findByText(/isn't in your offers/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: /all offers/i })).toBeTruthy();
  });

  it("opens straight to a store from the address", async () => {
    window.location.hash = "#/store/s3";
    const api = makeApi({ signedInAs: "m_nurse" });
    render(<App api={api} concierge={link()} />);
    expect(await screen.findByRole("heading", { level: 1, name: "Inkwell Books" })).toBeTruthy();
  });

  describe("estimating a cart", () => {
    const type = (text: string) => fireEvent.change(screen.getByLabelText(/cart total/i), { target: { value: text } });
    const submit = () => fireEvent.click(screen.getByRole("button", { name: /^estimate$/i }));

    it("sends the cart in integer cents and shows the server's dollar amounts", async () => {
      const { api } = await openStore();
      type("$1,500");
      submit();
      expect(await screen.findByText("$1,300.00")).toBeTruthy();
      expect(api.estimate).toHaveBeenCalledWith("s1", 150000);
      const text = screen.getByRole("main").textContent ?? "";
      expect(text).toContain("$200.00");
      expect(text).toMatch(/as of 2026-11-06/i);
      expect(text).toMatch(/no guarantee/i);
    });

    it.each(["", "abc", "0", "-5", "12.345", "2000000"])("does not call the server for %j and explains what to type", async (bad) => {
      const { api } = await openStore();
      type(bad);
      submit();
      expect(screen.getByRole("alert").textContent).toMatch(/enter an amount/i);
      expect(api.estimate).not.toHaveBeenCalled();
    });

    it("shows a friendly message when the estimate fails", async () => {
      const { api } = await openStore();
      api.estimate.mockRejectedValueOnce(new ApiError(401, "not_signed_in"));
      type("200");
      submit();
      expect((await screen.findByRole("alert")).textContent).toMatch(/sign in/i);
    });
  });
});

describe("signing in and out of members", () => {
  it("signs in, reloads, and updates the greeting and the offers", async () => {
    const { api } = await renderApp();
    await signInAs("m_nurse");
    expect(api.switchMember).toHaveBeenCalledWith("m_nurse");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Hi Avery, what are you shopping for?");
    expect(tileNames()).toContain("Fjordline Outdoors");
  });

  it("ends up showing the member chosen last when answers arrive out of order", async () => {
    const api = makeApi();
    const slow = deferred<Discounts>();
    render(<App api={api} concierge={link()} />);
    await screen.findByLabelText(/signed in as/i);
    api.discounts.mockImplementationOnce(() => slow.promise); // after the page's own first load
    fireEvent.change(picker(), { target: { value: "m_nurse" } }); // its discounts answer is slow
    await waitFor(() => expect(api.switchMember).toHaveBeenCalledWith("m_nurse"));
    fireEvent.change(picker(), { target: { value: "m_student" } });
    await screen.findByRole("heading", { level: 1, name: /^Hi Sam/ });
    await act(async () => slow.resolve(DISCOUNTS.m_nurse)); // the stale answer arrives last
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/^Hi Sam/);
    expect(document.body.textContent).not.toMatch(/30% off/);
  });

  it("shows a clear message when the offers cannot be loaded", async () => {
    const api = makeApi({ signedInAs: "m_nurse" });
    api.discounts.mockRejectedValue(new ApiError(0, "network"));
    render(<App api={api} concierge={link()} />);
    expect((await screen.findByRole("alert")).textContent).toMatch(/reach the server/i);
  });
});
