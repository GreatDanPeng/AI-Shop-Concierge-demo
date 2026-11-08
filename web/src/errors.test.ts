import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { describeError } from "./errors";

describe("describeError", () => {
  it.each([
    [new ApiError(401, "not_signed_in"), /sign in/i],
    [new ApiError(400, "unknown_store"), /store/i],
    [new ApiError(422, "invalid_request"), /1.*2000|characters/i],
    [new ApiError(503, "assistant_not_configured"), /not set up/i],
    [new ApiError(502, "assistant_unavailable"), /temporarily unavailable/i],
    [new ApiError(0, "network"), /reach the server/i],
    [new ApiError(500, "http_error"), /went wrong/i],
    [new Error("boom"), /went wrong/i],
    ["a string", /went wrong/i],
  ])("gives a friendly message for %j", (error, pattern) => {
    expect(describeError(error)).toMatch(pattern);
  });

  it("never shows internal codes or exception text", () => {
    const text = describeError(new ApiError(503, "assistant_not_configured"));
    expect(text).not.toMatch(/assistant_not_configured|OPENROUTER|503/);
    expect(describeError(new Error("secret internal detail"))).not.toMatch(/secret internal detail/);
  });
});
