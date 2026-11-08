import { describe, expect, it } from "vitest";
import { STORE_ADDRESS, isStoreAddress, storeAddress, storeIdOf } from "./links";

// The one address shape the page will follow from a reply: "#/store/<letters, digits, _ or ->".
describe("store addresses", () => {
  it.each(["#/store/s4", "#/store/S4", "#/store/store_1-a", "#/store/0"])("accepts %s", (address) => {
    expect(isStoreAddress(address)).toBe(true);
    expect(STORE_ADDRESS.test(address)).toBe(true);
  });

  it.each([
    "", "#", "#/", "#/me", "#/store/", "#/store", "#/STORE/s4", "/store/s4", "store/s4",
    "#/store/s4/", "#/store/s4/extra", "#/store/../me", "#/store/s4?x=1", "#/store/s4#x",
    "#/store/s 4", "#/store/s4\n", "#/store/s4 ", " #/store/s4", "#/store/é1", "#/store/<s4>",
    "javascript:alert(1)", "JAVASCRIPT:alert(1)", "data:text/html,x", "https://evil.example",
    "http://evil.example/store/s4", "//evil.example", "\\\\evil.example",
  ])("rejects %j", (address) => {
    expect(isStoreAddress(address)).toBe(false);
    expect(storeIdOf(address)).toBeNull();
  });

  it("builds an address from an id and reads the id back", () => {
    expect(storeAddress("s4")).toBe("#/store/s4");
    expect(storeIdOf("#/store/s4")).toBe("s4");
  });
});
