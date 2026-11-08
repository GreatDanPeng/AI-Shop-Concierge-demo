import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Icon, ICON_NAMES } from "./icons";
import { StoreArt } from "./StoreArt";

const ART_KEYS = ["tent", "headphones", "books", "sneaker", "lamp", "laptop"];
const art = (props: Partial<Parameters<typeof StoreArt>[0]> = {}) =>
  render(<StoreArt art="tent" image={null} credit={null} {...props} />).container;

describe("StoreArt illustrations", () => {
  it.each(ART_KEYS)("draws the %s illustration", (key) => {
    const svg = art({ art: key }).querySelector("svg");
    expect(svg?.getAttribute("data-art")).toBe(key);
    expect(svg?.querySelectorAll("path, rect, ellipse, circle, line").length).toBeGreaterThan(2);
  });

  it("falls back to a shopping bag for an unknown or missing key", () => {
    expect(art({ art: "does-not-exist" }).querySelector("svg")?.getAttribute("data-art")).toBe("bag");
    expect(art({ art: null }).querySelector("svg")?.getAttribute("data-art")).toBe("bag");
  });

  it("is decorative: hidden from screen readers (the tile's text names the store)", () => {
    const c = art();
    expect(c.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(c.querySelector("svg")?.getAttribute("focusable")).toBe("false");
  });

  it.each(ART_KEYS)("takes every colour of %s from tokens through classes, never from an attribute", (key) => {
    const svg = art({ art: key }).querySelector("svg")!;
    for (const el of svg.querySelectorAll("*")) {
      for (const attribute of ["fill", "stroke", "style"]) {
        const value = el.getAttribute(attribute);
        if (value !== null) expect(value, `${key} <${el.tagName}> ${attribute}`).toMatch(/^(none|currentColor)$/);
      }
      expect(el.getAttribute("class") ?? "", `${key} <${el.tagName}>`).toMatch(/^art-(bg|a|b|c|line)$/);
    }
  });
});

describe("StoreArt photo slot", () => {
  it("shows a licensed photo instead of the illustration, with its credit", () => {
    const c = art({ image: "/stores/s1.jpg", credit: "Jane Doe" });
    const img = c.querySelector("img")!;
    expect(img.getAttribute("src")).toBe("/stores/s1.jpg");
    expect(img.getAttribute("alt")).toBe("");
    expect(img.getAttribute("loading")).toBe("lazy");
    expect(c.querySelector("svg")).toBeNull();
    expect(c.textContent).toContain("Photo: Jane Doe");
  });

  it("shows no credit line when there is none", () => {
    expect(art({ image: "/stores/s1.jpg" }).textContent).not.toMatch(/photo/i);
  });

  it("brings the illustration back if the photo cannot be loaded, and hides the credit", () => {
    const c = art({ image: "/stores/missing.jpg", credit: "Jane Doe" });
    fireEvent.error(c.querySelector("img")!);
    expect(c.querySelector("img")).toBeNull();
    expect(c.querySelector("svg")?.getAttribute("data-art")).toBe("tent");
    expect(c.textContent).not.toContain("Jane Doe");
  });

  it("tries a new photo again when the image changes after a failure", () => {
    const { container, rerender } = render(<StoreArt art="tent" image="/stores/a.jpg" credit={null} />);
    fireEvent.error(container.querySelector("img")!);
    rerender(<StoreArt art="tent" image="/stores/b.jpg" credit={null} />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe("/stores/b.jpg");
  });
});

describe("icons", () => {
  it("has outline icons only, all drawn the same way, none exposed to screen readers on their own", () => {
    expect(ICON_NAMES.length).toBeGreaterThanOrEqual(12);
    for (const name of ICON_NAMES) {
      const svg = render(<Icon name={name} />).container.querySelector("svg")!;
      expect(svg.getAttribute("aria-hidden"), name).toBe("true");
      expect(svg.getAttribute("fill"), name).toBe("none");
      expect(svg.getAttribute("stroke"), name).toBe("currentColor");
      expect(svg.getAttribute("stroke-width"), name).toBe("1.75");
      expect(svg.querySelectorAll("path, circle, rect, line, polyline").length, name).toBeGreaterThan(0);
    }
  });
});
