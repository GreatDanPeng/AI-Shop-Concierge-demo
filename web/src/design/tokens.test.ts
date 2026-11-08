import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Design tokens are the only place colours, radii, shadows, fonts and motion durations are written.
// These tests make that rule, and WCAG AA contrast, mechanical instead of a matter of discipline.

const HERE = import.meta.dirname;
const SRC = join(HERE, "..");
const tokensCss = readFileSync(join(HERE, "tokens.css"), "utf8");

type Block = { selector: string; media: string | null; declarations: Record<string, string> };

function parseDeclarations(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of body.split(";")) {
    const index = part.indexOf(":");
    if (index === -1) continue;
    out[part.slice(0, index).trim()] = part.slice(index + 1).replace(/\s+/g, " ").trim();
  }
  return out;
}

function parseBlocks(css: string): Block[] {
  const blocks: Block[] = [];
  const walk = (text: string, media: string | null) => {
    let pos = 0;
    while (pos < text.length) {
      const open = text.indexOf("{", pos);
      if (open === -1) break;
      const header = text.slice(pos, open).trim();
      let depth = 1;
      let end = open + 1;
      while (end < text.length && depth > 0) {
        if (text[end] === "{") depth++;
        else if (text[end] === "}") depth--;
        end++;
      }
      const body = text.slice(open + 1, end - 1);
      if (header.startsWith("@media")) walk(body, header.slice(6).trim());
      else blocks.push({ selector: header.replace(/\s+/g, " "), media, declarations: parseDeclarations(body) });
      pos = end;
    }
  };
  walk(css.replace(/\/\*[\s\S]*?\*\//g, ""), null);
  return blocks;
}

const blocks = parseBlocks(tokensCss);
const light = blocks.find((b) => b.media === null && b.selector.includes(":root"))!;
const darkAuto = blocks.find((b) => b.media?.includes("prefers-color-scheme: dark") && b.selector.includes(":root"))!;
const darkForced = blocks.find((b) => b.media === null && b.selector.includes('[data-theme="dark"]'))!;
const reduced = blocks.find((b) => b.media?.includes("prefers-reduced-motion: reduce"))!;

const px = (value: string) => Number(/^(\d+)px$/.exec(value)?.[1]);
const ms = (value: string) => Number(/^(\d+)ms$/.exec(value)?.[1]);

function channel(hex: string, start: number) {
  const c = parseInt(hex.slice(start, start + 2), 16) / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}
function luminance(hex: string) {
  expect(hex, "contrast needs a #rrggbb token").toMatch(/^#[0-9a-f]{6}$/i);
  return 0.2126 * channel(hex, 1) + 0.7152 * channel(hex, 3) + 0.0722 * channel(hex, 5);
}
function contrast(a: string, b: string) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("the token file", () => {
  it("has a light set, an automatic dark set, a forced dark set and a reduced-motion set", () => {
    expect(light && darkAuto && darkForced && reduced).toBeTruthy();
    expect(light.selector).toContain(":host"); // the widget's shadow root reads the same tokens
    expect(darkForced.selector).toContain(':host([data-theme="dark"])');
    expect(darkAuto.selector).toContain(':not([data-theme="light"])'); // an explicit light choice wins
  });

  it("defines every token group", () => {
    for (const name of [
      "--color-bg-start", "--color-bg-mid", "--color-bg-end", "--color-surface", "--color-surface-alt",
      "--color-text", "--color-text-muted", "--color-border", "--color-accent", "--color-accent-hover",
      "--color-accent-contrast", "--color-focus", "--color-success-text", "--color-success-bg",
      "--color-danger-text", "--color-danger-bg", "--color-overlay",
      "--radius-small", "--radius-control", "--radius-card", "--radius-pill",
      "--space-1", "--space-2", "--space-3", "--space-4", "--space-6", "--space-8",
      "--shadow-hairline", "--shadow-soft", "--shadow-popover", "--gradient-page",
      "--font-sans", "--text-xs", "--text-sm", "--text-md", "--text-lg", "--text-xl", "--text-hero",
      "--motion-fast", "--motion-base", "--motion-slow", "--motion-ease",
      "--art-bg", "--art-a", "--art-b", "--art-c", "--art-line",
    ]) {
      expect(light.declarations, name).toHaveProperty([name]);
    }
  });

  it("follows the visual specification", () => {
    const d = light.declarations;
    expect(px(d["--radius-card"])).toBeGreaterThanOrEqual(12);
    expect(px(d["--radius-card"])).toBeLessThanOrEqual(16);
    expect(px(d["--radius-control"])).toBeGreaterThanOrEqual(8);
    expect(px(d["--radius-control"])).toBeLessThanOrEqual(12);
    expect(d["--font-sans"]).toMatch(/^"Segoe UI Variable"/);
    expect(d["--font-sans"]).toContain("system-ui");
    for (const step of ["--space-1", "--space-2", "--space-3", "--space-4", "--space-6", "--space-8"]) {
      expect(px(d[step]) % 4, step).toBe(0);
    }
    for (const name of ["--motion-fast", "--motion-base", "--motion-slow"]) {
      expect(ms(d[name]), name).toBeGreaterThanOrEqual(150);
      expect(ms(d[name]), name).toBeLessThanOrEqual(250);
    }
    expect(d["--shadow-soft"]).not.toMatch(/\b(\d{2,})px\b.*\b(\d{2,})px\b.*rgba\([^)]*0\.[3-9]/); // no heavy shadows
  });

  it("gives the dark sets the same tokens as the light set, so nothing stays light by accident", () => {
    const colourNames = (b: Block) => Object.keys(b.declarations).filter((n) => /^--(color|art|shadow|gradient)/.test(n)).sort();
    expect(colourNames(darkAuto)).toEqual(colourNames(light));
    expect(darkForced.declarations).toEqual(darkAuto.declarations); // the two dark sets cannot drift
  });

  it("switches motion off for people who ask for reduced motion", () => {
    for (const name of ["--motion-fast", "--motion-base", "--motion-slow"]) {
      expect(reduced.declarations[name], name).toMatch(/^0(\.\d+)?m?s$/);
    }
  });
});

describe("WCAG AA contrast", () => {
  const themes: [string, Record<string, string>][] = [
    ["light", light.declarations],
    ["dark", { ...light.declarations, ...darkForced.declarations }],
  ];

  describe.each(themes)("%s theme", (_name, d) => {
    const bgStops = ["--color-bg-start", "--color-bg-mid", "--color-bg-end"];
    it.each([
      ["text", "--color-text", "--color-surface"],
      ["text on the soft surface", "--color-text", "--color-surface-alt"],
      ["muted text", "--color-text-muted", "--color-surface"],
      ["muted text on the soft surface", "--color-text-muted", "--color-surface-alt"],
      ["button label on the accent", "--color-accent-contrast", "--color-accent"],
      ["button label on the hovered accent", "--color-accent-contrast", "--color-accent-hover"],
      ["success text", "--color-success-text", "--color-success-bg"],
      ["error text", "--color-danger-text", "--color-danger-bg"],
    ])("%s is at least 4.5:1", (_label, fg, bg) => {
      expect(contrast(d[fg], d[bg])).toBeGreaterThanOrEqual(4.5);
    });

    it.each(bgStops)("text and muted text stay readable on the gradient stop %s", (stop) => {
      expect(contrast(d["--color-text"], d[stop])).toBeGreaterThanOrEqual(4.5);
      expect(contrast(d["--color-text-muted"], d[stop])).toBeGreaterThanOrEqual(4.5);
    });

    it("the focus ring is at least 3:1 against the surface and the page", () => {
      expect(contrast(d["--color-focus"], d["--color-surface"])).toBeGreaterThanOrEqual(3);
      for (const stop of bgStops) expect(contrast(d["--color-focus"], d[stop])).toBeGreaterThanOrEqual(3);
    });
  });
});

describe("tokens are the only source of colour, radius, shadow, font and motion", () => {
  const files: { path: string; text: string }[] = [];
  const walk = (dir: string) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (/\.(css|ts|tsx)$/.test(name) && !/\.test\./.test(name) && name !== "tokens.css") {
        files.push({ path: path.replace(SRC + "/", ""), text: readFileSync(path, "utf8") });
      }
    }
  };
  walk(SRC);
  const css = files.filter((f) => f.path.endsWith(".css"));
  const code = files.filter((f) => !f.path.endsWith(".css"));
  const declarations = (text: string, property: RegExp) =>
    [...text.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([a-z-]+)\s*:\s*([^;{}]+)[;}]/g)]
      .filter((m) => property.test(m[1])).map((m) => m[2].trim());

  it("finds the style sheets and the components", () => {
    expect(css.length).toBeGreaterThan(0);
    expect(code.length).toBeGreaterThan(0);
  });

  it("has no colour literal in any other style sheet", () => {
    for (const { path, text } of css) {
      const stripped = text.replace(/\/\*[\s\S]*?\*\//g, "");
      // the colour keywords only count on their own (not inside "white-space")
      expect(stripped, path).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|(?<![\w-])(white|black)(?![\w-])/);
    }
  });

  it("has no colour literal in components (SVG art uses tokens too)", () => {
    for (const { path, text } of code) {
      expect(text, path).not.toMatch(/#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\brgba?\(|\bhsla?\(/);
    }
  });

  it("takes radii, shadows, fonts and motion from tokens", () => {
    for (const { path, text } of css) {
      for (const value of declarations(text, /^border-radius$/)) expect(value, `${path} border-radius`).toMatch(/^(0|50%|var\(--radius-[a-z]+\))( |$)|var\(--radius/);
      for (const value of declarations(text, /^box-shadow$/)) expect(value, `${path} box-shadow`).toMatch(/^none$|var\(--shadow-|var\(--focus-ring/);
      for (const value of declarations(text, /^font-family$/)) expect(value, `${path} font-family`).toMatch(/^(var\(--font-sans\)|inherit)$/);
      for (const value of declarations(text, /^(transition|animation)(-duration)?$/)) {
        expect(value, `${path} motion`).toMatch(/^none$|var\(--motion-/);
        expect(value, `${path} motion`).not.toMatch(/\d+m?s\b/);
      }
    }
  });

  it("keeps spacing on the 4px grid", () => {
    for (const { path, text } of css) {
      for (const value of declarations(text, /^(padding|margin|gap|row-gap|column-gap)(-[a-z]+)?$/)) {
        for (const match of value.matchAll(/(-?\d+(?:\.\d+)?)px/g)) {
          expect(Number(match[1]) % 4, `${path}: ${value}`).toBe(0);
        }
      }
    }
  });
});
