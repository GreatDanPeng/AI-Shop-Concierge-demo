import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StoreArt } from "./StoreArt";

// One original illustration for each invented brand-store: everyday objects only, no logos, no brand marks,
// drawn from tokens like the first six. Written before the drawings.
const BRAND_ART = ["devices", "phone", "tv", "yoga", "jeans", "runner", "backpack", "jacket", "sofa", "toolbox",
  "openbook", "hotel", "car"];
const ORIGINAL_ART = ["tent", "headphones", "books", "sneaker", "lamp", "laptop"];
const svgOf = (art: string) =>
  render(<StoreArt art={art} image={null} credit={null} />).container.querySelector("svg")!;

describe("brand store illustrations", () => {
  it.each(BRAND_ART)("draws the %s picture with real shapes", (key) => {
    const svg = svgOf(key);
    expect(svg.getAttribute("data-art")).toBe(key);                    // not the shopping-bag fallback
    expect(svg.querySelectorAll("path, rect, ellipse, circle, line").length).toBeGreaterThan(3);
  });

  it("gives each of the thirteen stores a picture of its own", () => {
    expect(new Set(BRAND_ART).size).toBe(13);
    expect(BRAND_ART.filter((key) => ORIGINAL_ART.includes(key) || key === "bag")).toEqual([]);
    const drawings = [...BRAND_ART, ...ORIGINAL_ART, "bag"].map((key) => svgOf(key).innerHTML);
    expect(new Set(drawings).size).toBe(drawings.length);              // no two pictures are the same drawing
  });

  it.each(BRAND_ART)("takes every colour of %s from tokens through classes, never from an attribute", (key) => {
    for (const el of svgOf(key).querySelectorAll("*")) {
      for (const attribute of ["fill", "stroke", "style"]) {
        const value = el.getAttribute(attribute);
        if (value !== null) expect(value, `${key} <${el.tagName}> ${attribute}`).toMatch(/^(none|currentColor)$/);
      }
      expect(el.getAttribute("class") ?? "", `${key} <${el.tagName}>`).toMatch(/^art-(bg|a|b|c|line)$/);
    }
  });

  it.each(BRAND_ART)("keeps %s inside the picture frame and hidden from screen readers", (key) => {
    const svg = svgOf(key);
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("focusable")).toBe("false");
    expect(svg.getAttribute("viewBox")).toBe("0 0 160 100");
    expect(svg.querySelector("text, image, foreignObject, use, a, script")).toBeNull();   // shapes only
  });
});
