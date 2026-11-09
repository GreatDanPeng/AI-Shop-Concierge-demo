import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// The logo plate: official logos are made for light backgrounds (some are black), so the plate stays white
// in dark mode too. Its colour is a token like every other colour. Written before the token and the CSS.
const dir = __dirname;
const tokens = readFileSync(join(dir, "tokens.css"), "utf-8");
const art = readFileSync(join(dir, "art.css"), "utf-8");

describe("logo plate", () => {
  it("defines --logo-plate as white in :root and never overrides it in dark mode", () => {
    expect(tokens).toMatch(/--logo-plate:\s*#ffffff\s*;/i);
    expect(tokens.match(/--logo-plate\s*:/g)).toHaveLength(1);        // once: light and dark share it
  });

  it("paints the plate from the token and fits the logo inside it without cropping", () => {
    const rule = art.match(/\.store-art--logo[^{]*\{[^}]*\}/g)?.join("\n") ?? "";
    expect(rule).toMatch(/background:\s*var\(--logo-plate\)/);
    expect(art).toMatch(/\.store-art--logo img[^{]*\{[^}]*object-fit:\s*contain/);
    expect(rule + art).not.toMatch(/#[0-9a-f]{3,8}\b/i);              // no colour literal outside tokens.css
  });
});
