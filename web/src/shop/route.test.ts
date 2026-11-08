import { describe, expect, it } from "vitest";
import { parseRoute } from "./route";

describe("parseRoute", () => {
  it.each([
    ["", { name: "home" }],
    ["#", { name: "home" }],
    ["#/", { name: "home" }],
    ["#/me", { name: "me" }],
    ["#/store/s1", { name: "store", id: "s1" }],
    ["#/store/store_2-b", { name: "store", id: "store_2-b" }],
  ])("reads %j", (hash, route) => {
    expect(parseRoute(hash)).toEqual(route);
  });

  it.each(["#/store/", "#/store", "#/store/s1/extra", "#/store/<script>", "#/store/s1?x=1", "#/store/../etc", "#/nope", "#main", "#/me/extra", "#/store/%00"])(
    "sends %j home instead of guessing", (hash) => {
      expect(parseRoute(hash)).toEqual({ name: "home" });
    });
});
