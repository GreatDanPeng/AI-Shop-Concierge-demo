import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReplyText } from "./reply";

// Security-relevant: a reply is untrusted text. It may contain a link only in the one shape the
// server writes, "[label](#/store/<id>)", and every other form must stay visible, inert text.
const html = (text: string, onLink?: () => void) => render(<ReplyText text={text} onLink={onLink} />).container;

const COBALT = "[Cobalt Shoes: 4% cash back](#/store/s4)";

describe("ReplyText store links", () => {
  it("turns a store link into one anchor whose text is the label", () => {
    const c = html(`You can use ${COBALT} today.`);
    const links = c.querySelectorAll("a");
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute("href")).toBe("#/store/s4");
    expect(links[0].textContent).toBe("Cobalt Shoes: 4% cash back");
    expect(c.textContent).toBe("You can use Cobalt Shoes: 4% cash back today.");
  });

  it("gives the anchor only an href: no target, rel, style or event attributes", () => {
    const [a] = Array.from(html(COBALT).querySelectorAll("a"));
    expect(a.getAttributeNames()).toEqual(["href"]);
  });

  it("works inside a bullet list, several to a line, and inside bold", () => {
    const c = html(`- ${COBALT}\n- [Fjordline Outdoors: 30% off](#/store/s1) and ${COBALT}\n\n**${COBALT}**`);
    expect(Array.from(c.querySelectorAll("li a")).map((a) => a.getAttribute("href")))
      .toEqual(["#/store/s4", "#/store/s1", "#/store/s4"]);
    expect(c.querySelector("strong a")?.getAttribute("href")).toBe("#/store/s4");
  });

  it("keeps bold and plain text around a link exactly as written", () => {
    const c = html(`**Best** deal: ${COBALT}. Pay $1,300.00.`);
    expect(c.querySelector("strong")?.textContent).toBe("Best");
    expect(c.textContent).toBe("Best deal: Cobalt Shoes: 4% cash back. Pay $1,300.00.");
  });

  it.each([
    ["a javascript address", "[click](javascript:alert(1))"],
    ["an upper-case javascript address", "[click](JAVASCRIPT:alert(1))"],
    ["a data address", "[click](data:text/html,<script>alert(1)</script>)"],
    ["an https address", "[Cobalt Shoes: 4% cash back](https://evil.example/pay)"],
    ["a protocol-relative address", "[Cobalt Shoes](//evil.example)"],
    ["an address that climbs out of the store path", "[Cobalt Shoes](#/store/../me)"],
    ["an address with a query string", "[Cobalt Shoes](#/store/s4?next=https://evil.example)"],
    ["an address with a second fragment", "[Cobalt Shoes](#/store/s4#x)"],
    ["an address with extra path", "[Cobalt Shoes](#/store/s4/extra)"],
    ["another page of the shop", "[My verifications](#/me)"],
    ["an empty store id", "[Cobalt Shoes](#/store/)"],
    ["a wrong-case route", "[Cobalt Shoes](#/STORE/s4)"],
    ["an address with a space or a title", '[Cobalt Shoes](#/store/s4 "title")'],
    ["an empty label", "[](#/store/s4)"],
    ["a label with brackets", "[a [b]](#/store/s4)"],
    ["a label with a nested link", "[[x](#/store/s1)](#/store/s4)x"],
    ["a reference-style link", "[Cobalt Shoes][1]\n\n[1]: https://evil.example"],
    ["a bare address", "Go to #/store/s4 now"],
    ["a bare url", "Go to https://evil.example/store/s4 now"],
    ["an html anchor", '<a href="#/store/s4">Cobalt Shoes</a>'],
  ])("does not link %s", (_name, text) => {
    const c = html(text);
    const anchors = Array.from(c.querySelectorAll("a"));
    // The only allowed exceptions: the inner [x](#/store/s1) of the nested case is a valid link by itself.
    const allowed = text.startsWith("[[x]") ? 1 : 0;
    expect(anchors).toHaveLength(allowed);
    for (const tag of ["img", "script", "iframe", "svg"]) expect(c.querySelector(tag)).toBeNull();
    if (!allowed) expect(c.textContent).toContain(text.split("\n")[0].replace(/\*\*/g, ""));
  });

  it("never makes an image: markdown image syntax gives at most a plain store link", () => {
    const c = html("![Cobalt Shoes](#/store/s4) and ![x](https://evil.example/a.png)");
    expect(c.querySelector("img")).toBeNull();
    expect(Array.from(c.querySelectorAll("a")).map((a) => a.getAttribute("href"))).toEqual(["#/store/s4"]);
    expect(c.textContent).toContain("![x](https://evil.example/a.png)");
  });

  it("shows markup inside a label as text and creates no element for it", () => {
    const c = html("[<img src=x onerror=alert(1)>](#/store/s4) [<b>x</b>](#/store/s4)");
    expect(c.querySelector("img")).toBeNull();
    expect(c.querySelector("b")).toBeNull();
  });

  it("calls onLink when a link is clicked and does not stop the navigation", () => {
    const onLink = vi.fn();
    const [a] = Array.from(html(COBALT, onLink).querySelectorAll("a"));
    const notCancelled = fireEvent.click(a);
    expect(onLink).toHaveBeenCalledTimes(1);
    expect(notCancelled).toBe(true);
  });

  it("works without an onLink handler", () => {
    const [a] = Array.from(html(COBALT).querySelectorAll("a"));
    expect(() => fireEvent.click(a)).not.toThrow();
  });
});
