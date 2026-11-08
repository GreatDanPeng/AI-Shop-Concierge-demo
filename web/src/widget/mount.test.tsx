import { act, fireEvent, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mountConcierge, readOptions, type Controller } from "./mount";

const chat = vi.fn(async () => "reply");
let controllers: Controller[] = [];

function mount(options = {}) {
  let controller!: Controller;
  act(() => {
    controller = mountConcierge({ api: { chat }, ...options });
  });
  controllers.push(controller);
  const host = document.querySelector("[data-concierge-host]") as HTMLElement;
  return { controller, host, ui: within(host.shadowRoot as unknown as HTMLElement) };
}

afterEach(() => {
  act(() => controllers.forEach((c) => c.unmount()));
  controllers = [];
  document.body.innerHTML = "";
  delete window.Concierge;
  chat.mockClear();
});

describe("mountConcierge", () => {
  it("adds one host element to the page and renders inside a shadow root", () => {
    const before = document.body.children.length;
    const { host, ui } = mount();
    expect(document.body.children.length).toBe(before + 1);
    expect(host.shadowRoot).toBeTruthy();
    expect(ui.getByRole("button", { name: /open concierge chat/i })).toBeTruthy();
    expect(document.body.querySelector("button")).toBeNull(); // nothing leaks into the page's own DOM
  });

  it("brings its own styles inside the shadow root, so the page's styles cannot break it", () => {
    const { host } = mount();
    const style = host.shadowRoot!.querySelector("style");
    expect(style?.textContent?.length).toBeGreaterThan(200);
    expect(style?.textContent).toContain(":host");
  });

  it("brings the design tokens too, so light, dark and reduced motion work inside the shadow root", () => {
    const { host } = mount();
    const css = host.shadowRoot!.querySelector("style")!.textContent!;
    expect(css).toContain("--color-surface");
    expect(css).toContain("prefers-color-scheme: dark");
    expect(css).toContain("prefers-reduced-motion");
  });

  it("can be opened, closed and pointed at a store from the page", () => {
    const { controller, ui } = mount();
    act(() => controller.open());
    expect(ui.getByRole("dialog")).toBeTruthy();
    act(() => controller.setStore("s2", "Voltage Electronics"));
    expect(ui.queryByText("Voltage Electronics")).toBeNull();   // the store is context, not something to show
    act(() => controller.close());
    expect(ui.queryByRole("dialog")).toBeNull();
  });

  it("sends the store set by the page along with the question", async () => {
    const { controller, ui } = mount({ storeId: "s1", storeName: "Fjordline Outdoors" });
    act(() => controller.open());
    act(() => controller.setStore("s3", "Inkwell Books"));
    fireEvent.change(ui.getByRole("textbox", { name: /your question/i }), { target: { value: "hi" } });
    await act(async () => fireEvent.click(ui.getByRole("button", { name: /^send$/i })));
    expect(chat).toHaveBeenCalledWith("hi", "s3");
  });

  it("can forget the store again", async () => {
    const { controller, ui } = mount({ storeId: "s1" });
    act(() => controller.open());
    act(() => controller.setStore(null));
    expect(ui.queryByText(/any store|asking about/i)).toBeNull();
    fireEvent.change(ui.getByRole("textbox", { name: /your question/i }), { target: { value: "hi" } });
    await act(async () => fireEvent.click(ui.getByRole("button", { name: /^send$/i })));
    expect(chat).toHaveBeenLastCalledWith("hi", null);
  });

  it("is idempotent: loading the script twice gives one widget", () => {
    const first = mount();
    act(() => {
      expect(mountConcierge({ api: { chat } })).toBe(first.controller);
    });
    expect(document.querySelectorAll("[data-concierge-host]")).toHaveLength(1);
  });

  it("removes itself completely when unmounted", () => {
    const { controller } = mount();
    act(() => controller.unmount());
    expect(document.querySelector("[data-concierge-host]")).toBeNull();
    expect(window.Concierge).toBeUndefined();
  });

  it("exposes the controller as window.Concierge", () => {
    const { controller } = mount();
    expect(window.Concierge).toBe(controller);
  });
});

describe("asking and theming from the page", () => {
  it("ask() opens the panel and sends the question for the current store", async () => {
    const { controller, ui } = mount({ storeId: "s2", storeName: "Voltage Electronics" });
    await act(async () => controller.ask("What do I pay?"));
    expect(ui.getByRole("dialog")).toBeTruthy();
    expect(chat).toHaveBeenCalledTimes(1);
    expect(chat).toHaveBeenCalledWith("What do I pay?", "s2");
    expect(await ui.findByText("reply")).toBeTruthy();
  });

  it("ask() with the same words twice asks twice", async () => {
    const { controller } = mount();
    await act(async () => controller.ask("again"));
    await act(async () => controller.ask("again"));
    expect(chat).toHaveBeenCalledTimes(2);
  });

  it("ask() with blank text does nothing", async () => {
    const { controller, ui } = mount();
    await act(async () => controller.ask("   "));
    expect(chat).not.toHaveBeenCalled();
    expect(ui.queryByRole("dialog")).toBeNull();
  });

  it("setTheme() puts the choice on the widget's own host element, and auto removes it", () => {
    const { controller, host } = mount();
    act(() => controller.setTheme("dark"));
    expect(host.getAttribute("data-theme")).toBe("dark");
    act(() => controller.setTheme("light"));
    expect(host.getAttribute("data-theme")).toBe("light");
    act(() => controller.setTheme("auto"));
    expect(host.hasAttribute("data-theme")).toBe(false);
  });

  it("setTheme() never touches the page's own elements", () => {
    const { controller } = mount();
    act(() => controller.setTheme("dark"));
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });
});

describe("readOptions", () => {
  const script = (attrs: Record<string, string>) => {
    const el = document.createElement("script");
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  };

  it("reads the data attributes of the script tag", () => {
    expect(readOptions(script({ "data-api-base": "https://shop.example.test", "data-store-id": "s2", "data-store-name": "Voltage" })))
      .toEqual({ apiBase: "https://shop.example.test", storeId: "s2", storeName: "Voltage" });
  });

  it("treats missing or empty attributes as not set", () => {
    expect(readOptions(script({ "data-store-id": "" }))).toEqual({});
    expect(readOptions(null)).toEqual({});
  });
});
