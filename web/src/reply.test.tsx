import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReplyText } from "./reply";

const html = (text: string) => render(<ReplyText text={text} />).container;

describe("ReplyText renders model text safely", () => {
  it("shows plain text in a paragraph", () => {
    const c = html("You pay $1,300.00.");
    expect(c.querySelectorAll("p")).toHaveLength(1);
    expect(c.textContent).toBe("You pay $1,300.00.");
  });

  it.each([
    ["a script tag", "<script>alert(1)</script> hello"],
    ["an image with an event handler", "<img src=x onerror=alert(1)> hello"],
    ["an iframe", '<iframe src="https://evil.example"></iframe>'],
    ["a link tag", '<a href="javascript:alert(1)">click</a>'],
    ["a style tag", "<style>body{display:none}</style>"],
  ])("shows %s as visible text and creates no element for it", (_name, text) => {
    const c = html(text);
    expect(c.textContent).toContain(text.split(" ")[0].slice(0, 5));
    for (const tag of ["script", "img", "iframe", "a", "style", "svg", "object", "embed"]) {
      expect(c.querySelector(tag)).toBeNull();
    }
  });

  it("does not turn markdown links or bare urls into links", () => {
    const c = html("[click me](javascript:alert(1)) and https://example.test/path");
    expect(c.querySelector("a")).toBeNull();
    expect(c.textContent).toContain("[click me](javascript:alert(1))");
  });

  it("keeps html entities as text instead of decoding them into tags", () => {
    const c = html("&lt;b&gt;bold&lt;/b&gt;");
    expect(c.querySelector("b")).toBeNull();
    expect(c.textContent).toBe("&lt;b&gt;bold&lt;/b&gt;");
  });

  it("turns **bold** into <strong> and nothing else", () => {
    const c = html("You pay **$1,300.00** today");
    const strong = c.querySelector("strong");
    expect(strong?.textContent).toBe("$1,300.00");
    expect(c.textContent).toBe("You pay $1,300.00 today");
  });

  it("leaves unbalanced asterisks as they are", () => {
    const c = html("this **is not closed");
    expect(c.querySelector("strong")).toBeNull();
    expect(c.textContent).toBe("this **is not closed");
  });

  it("ignores empty bold markers", () => {
    const c = html("a **** b");
    expect(c.textContent).toContain("a");
    expect(c.querySelectorAll("strong")).toHaveLength(0);
  });

  it("splits blank-line separated text into paragraphs", () => {
    const c = html("First paragraph.\n\nSecond paragraph.");
    expect([...c.querySelectorAll("p")].map((p) => p.textContent)).toEqual(["First paragraph.", "Second paragraph."]);
  });

  it("keeps single line breaks inside a paragraph", () => {
    const c = html("line one\nline two");
    expect(c.querySelectorAll("p")).toHaveLength(1);
    expect(c.querySelectorAll("br")).toHaveLength(1);
  });

  it("renders dash and asterisk bullets as a list", () => {
    const c = html("Offers:\n\n- **10% off** for groups\n- 5% off for nurses\n* cash back");
    expect(c.querySelectorAll("ul")).toHaveLength(1);
    expect([...c.querySelectorAll("li")].map((li) => li.textContent)).toEqual([
      "10% off for groups", "5% off for nurses", "cash back",
    ]);
    expect(c.querySelector("li strong")?.textContent).toBe("10% off");
  });

  it("does not interpret headings, code fences or images", () => {
    const c = html("# Title\n\n```js\nalert(1)\n```\n\n![x](https://evil.example/p.png)");
    for (const tag of ["h1", "pre", "code", "img"]) expect(c.querySelector(tag)).toBeNull();
    expect(c.textContent).toContain("# Title");
  });

  it("handles empty text and very long unbroken text", () => {
    expect(html("").textContent).toBe("");
    expect(html("x".repeat(50_000)).textContent).toHaveLength(50_000);
  });

  it("never uses innerHTML or dangerouslySetInnerHTML anywhere in the app source", () => {
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const name of readdirSync(dir)) {
        const path = join(dir, name);
        if (statSync(path).isDirectory()) walk(path);
        else if (/\.(ts|tsx)$/.test(name) && !/\.test\./.test(name)) files.push(path);
      }
    };
    walk(import.meta.dirname);
    expect(files.length).toBeGreaterThan(0);
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/dangerouslySetInnerHTML|\.innerHTML\s*=|insertAdjacentHTML|document\.write/);
    }
  });
});
