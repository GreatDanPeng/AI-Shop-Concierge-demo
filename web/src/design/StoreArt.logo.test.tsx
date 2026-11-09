import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StoreArt } from "./StoreArt";

// A brand store shows its brand's own logo (a file in /brands/), on a plate; the illustration is the fallback.
// Order: a licensed photo, then the logo, then the illustration. Written before the logo support.
const art = (props: Partial<Parameters<typeof StoreArt>[0]> = {}) =>
  render(<StoreArt art="laptop" image={null} credit={null} logo="/brands/apple.svg" {...props} />).container;

describe("StoreArt logo", () => {
  it("shows the logo as a decorative image, inside a logo plate, with no illustration", () => {
    const c = art();
    const img = c.querySelector("img");
    expect(img?.getAttribute("src")).toBe("/brands/apple.svg");
    expect(img?.getAttribute("alt")).toBe("");                       // the store's name is written next to it
    expect(c.querySelector(".store-art")?.classList.contains("store-art--logo")).toBe(true);
    expect(c.querySelector("svg")).toBeNull();
  });

  it("shows a licensed photo in preference to the logo, and keeps the photo's credit", () => {
    const c = art({ image: "/stores/s7.jpg", credit: "Jane Doe" });
    expect(c.querySelector("img")?.getAttribute("src")).toBe("/stores/s7.jpg");
    expect(c.querySelector(".store-art--logo")).toBeNull();
    expect(c.textContent).toContain("Photo: Jane Doe");
  });

  it("draws the illustration when the store has no logo (null, missing)", () => {
    for (const logo of [null, undefined]) {
      const c = art({ logo });
      expect(c.querySelector("svg")?.getAttribute("data-art")).toBe("laptop");
      expect(c.querySelector("img")).toBeNull();
      expect(c.querySelector(".store-art--logo")).toBeNull();
    }
  });

  it("brings the illustration back when the logo file cannot be loaded", () => {
    const c = art();
    fireEvent.error(c.querySelector("img")!);
    expect(c.querySelector("img")).toBeNull();
    expect(c.querySelector("svg")?.getAttribute("data-art")).toBe("laptop");
  });

  it("gives a different logo a fresh try after one failed", () => {
    const { container, rerender } = render(<StoreArt art="laptop" image={null} credit={null} logo="/brands/apple.svg" />);
    fireEvent.error(container.querySelector("img")!);
    rerender(<StoreArt art="laptop" image={null} credit={null} logo="/brands/nike.svg" />);
    expect(container.querySelector("img")?.getAttribute("src")).toBe("/brands/nike.svg");
  });

  it.each([
    "javascript:alert(1)", "https://evil.example/logo.svg", "//evil.example/logo.svg", "/brands/../secret.svg",
    "/brands/a.svg?x=1", "/brands/", "/other/apple.svg", "data:image/svg+xml,<svg/>", "/brands/apple.exe", "",
  ])("never loads a logo path that is not a plain /brands/ file: %j", (logo) => {
    const c = art({ logo });
    expect(c.querySelector("img")).toBeNull();
    expect(c.querySelector("svg")?.getAttribute("data-art")).toBe("laptop");
  });

  it("loads logos lazily, like photos", () => {
    expect(art().querySelector("img")?.getAttribute("loading")).toBe("lazy");
  });
});
