import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Sidebar, type SidebarGroup } from "./Sidebar";

const GROUPS: SidebarGroup[] = [
  { id: "shop", label: "Shop", items: [
    { id: "all", label: "All offers", icon: "tag", count: 4 },
    { id: "cat:Outdoors", label: "Outdoors", icon: "tag", count: 1 },
    { id: "cat:Electronics", label: "Electronics", icon: "tag", count: 2 },
  ] },
  { id: "me", label: "Me", items: [{ id: "me", label: "My verifications", icon: "shield" }] },
];

function setup(props: Partial<Parameters<typeof Sidebar>[0]> = {}) {
  const handlers = { onSelect: vi.fn(), onToggleCollapsed: vi.fn(), onDrawerClose: vi.fn() };
  const view = render(<Sidebar groups={GROUPS} activeId="all" collapsed={false} drawerOpen={false} {...handlers} {...props} />);
  return { ...handlers, ...view };
}
const nav = () => screen.getByRole("navigation", { name: "Main" });

describe("Sidebar content", () => {
  it("is a labelled navigation landmark with grouped items and counts", () => {
    setup();
    const ui = within(nav());
    expect(ui.getByRole("button", { name: /^Shop/ })).toBeTruthy();
    expect(ui.getByRole("button", { name: /^Me/ })).toBeTruthy();
    expect(ui.getByRole("button", { name: /All offers/ }).textContent).toContain("4");
    expect(ui.getByRole("button", { name: /Electronics/ }).textContent).toContain("2");
    expect(ui.getByRole("button", { name: "My verifications" })).toBeTruthy();
  });

  it("marks the active item for assistive technology", () => {
    setup({ activeId: "cat:Outdoors" });
    expect(screen.getByRole("button", { name: /Outdoors/ }).getAttribute("aria-current")).toBe("page");
    expect(screen.getByRole("button", { name: /All offers/ }).getAttribute("aria-current")).toBeNull();
  });

  it("reports the chosen item", () => {
    const { onSelect } = setup();
    fireEvent.click(screen.getByRole("button", { name: /Electronics/ }));
    expect(onSelect).toHaveBeenCalledWith("cat:Electronics");
  });

  it("uses real buttons, so the keyboard works without extra code", () => {
    setup();
    for (const el of nav().querySelectorAll("button")) {
      expect(el.getAttribute("tabindex")).toBeNull();
      expect(el.getAttribute("type")).toBe("button");
    }
  });
});

describe("collapsing", () => {
  it("has a toggle that says what it will do and whether the sidebar is open", () => {
    const { onToggleCollapsed } = setup();
    const toggle = screen.getByRole("button", { name: "Collapse sidebar" });
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(toggle);
    expect(onToggleCollapsed).toHaveBeenCalledTimes(1);
  });

  it("when collapsed shows icons only, but every item keeps its accessible name", () => {
    setup({ collapsed: true });
    expect(nav().className).toContain("sidebar--collapsed");
    const toggle = screen.getByRole("button", { name: "Expand sidebar" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    const electronics = screen.getByRole("button", { name: /Electronics/ });
    expect(electronics.getAttribute("title")).toBe("Electronics");
    expect(electronics.querySelector(".sidebar-label")?.className).toContain("sr-only");
    expect(electronics.querySelector(".sidebar-count")).toBeNull();
    expect(electronics.querySelector("svg")).not.toBeNull();
  });

  it("when expanded shows the text labels", () => {
    setup();
    const label = screen.getByRole("button", { name: /Electronics/ }).querySelector(".sidebar-label");
    expect(label?.className).not.toContain("sr-only");
  });
});

describe("accordion groups", () => {
  it("opens and closes a group, and says which list it controls", () => {
    setup();
    const header = screen.getByRole("button", { name: /^Shop/ });
    expect(header.getAttribute("aria-expanded")).toBe("true");
    const listId = header.getAttribute("aria-controls")!;
    expect(document.getElementById(listId)).not.toBeNull();
    fireEvent.click(header);
    expect(header.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("button", { name: /Electronics/ })).toBeNull();
    fireEvent.click(header);
    expect(screen.getByRole("button", { name: /Electronics/ })).toBeTruthy();
  });

  it("keeps the other groups as they were", () => {
    setup();
    fireEvent.click(screen.getByRole("button", { name: /^Shop/ }));
    expect(screen.getByRole("button", { name: "My verifications" })).toBeTruthy();
  });
});

describe("narrow screens: the sidebar is a drawer", () => {
  it("shows a backdrop that closes it", () => {
    const { onDrawerClose } = setup({ drawerOpen: true });
    expect(nav().className).toContain("sidebar--drawer-open");
    fireEvent.click(screen.getByTestId("sidebar-backdrop"));
    expect(onDrawerClose).toHaveBeenCalledTimes(1);
  });

  it("has no backdrop when closed", () => {
    setup();
    expect(screen.queryByTestId("sidebar-backdrop")).toBeNull();
    expect(nav().className).not.toContain("sidebar--drawer-open");
  });

  it("closes on Escape, but only when it is open", () => {
    const open = setup({ drawerOpen: true });
    fireEvent.keyDown(nav(), { key: "Escape" });
    expect(open.onDrawerClose).toHaveBeenCalledTimes(1);
    open.unmount();
    const closed = setup();
    fireEvent.keyDown(nav(), { key: "Escape" });
    expect(closed.onDrawerClose).not.toHaveBeenCalled();
  });

  it("closes after you pick an item", () => {
    const { onSelect, onDrawerClose } = setup({ drawerOpen: true });
    fireEvent.click(screen.getByRole("button", { name: /Outdoors/ }));
    expect(onSelect).toHaveBeenCalledWith("cat:Outdoors");
    expect(onDrawerClose).toHaveBeenCalledTimes(1);
  });

  it("does not close anything when you pick an item on a wide screen", () => {
    const { onDrawerClose } = setup();
    fireEvent.click(screen.getByRole("button", { name: /Outdoors/ }));
    expect(onDrawerClose).not.toHaveBeenCalled();
  });
});

describe("drawer keyboard and focus", () => {
  it("moves the focus into the drawer when it opens, onto the item you are on", () => {
    setup({ drawerOpen: true, activeId: "cat:Outdoors" });
    expect(document.activeElement).toBe(screen.getByRole("button", { name: /Outdoors/ }));
  });

  it("does not grab the focus while it is closed", () => {
    const outside = document.createElement("button");
    document.body.appendChild(outside);
    outside.focus();
    setup();
    expect(document.activeElement).toBe(outside);
    outside.remove();
  });

  it("closes on Escape wherever the focus is, as long as it is open", () => {
    const { onDrawerClose, unmount } = setup({ drawerOpen: true });
    (document.activeElement as HTMLElement).blur(); // focus is now on the page, not in the drawer
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(onDrawerClose).toHaveBeenCalledTimes(1);
    unmount();
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(onDrawerClose).toHaveBeenCalledTimes(1); // the listener is gone with the drawer
  });

  it("ignores other keys", () => {
    const { onDrawerClose } = setup({ drawerOpen: true });
    fireEvent.keyDown(document.body, { key: "Enter" });
    expect(onDrawerClose).not.toHaveBeenCalled();
  });
});
