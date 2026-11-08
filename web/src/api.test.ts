import { describe, expect, it, vi } from "vitest";
import { ApiError, createApi } from "./api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function setup(response: Response | (() => Promise<Response>)) {
  const fetchImpl = vi.fn<typeof fetch>(typeof response === "function" ? response : async () => response.clone());
  return { fetchImpl, api: createApi({ fetchImpl }) };
}

describe("createApi", () => {
  it("posts a chat message and the store as JSON, with the session cookie", async () => {
    const { api, fetchImpl } = setup(json(200, { reply: "hi there" }));
    expect(await api.chat("hello", "s1")).toBe("hi there");
    expect(fetchImpl).toHaveBeenCalledWith("/chat", expect.objectContaining({
      method: "POST",
      credentials: "same-origin",
      body: JSON.stringify({ message: "hello", store_id: "s1" }),
    }));
  });

  it("sends a null store when there is none, and never a member id", async () => {
    const { api, fetchImpl } = setup(json(200, { reply: "ok" }));
    await api.chat("hello", null);
    const body = JSON.parse((fetchImpl.mock.calls[0][1] as RequestInit).body as string);
    expect(body).toEqual({ message: "hello", store_id: null });
  });

  it("can talk to another origin when the widget is embedded elsewhere", async () => {
    const fetchImpl = vi.fn<typeof fetch>(async () => json(200, { reply: "ok" }));
    const api = createApi({ apiBase: "https://shop.example.test", fetchImpl });
    await api.chat("hello", null);
    expect(fetchImpl.mock.calls[0][0]).toBe("https://shop.example.test/chat");
  });

  it.each([
    ["me", "/me"],
    ["discounts", "/discounts"],
    ["health", "/health"],
    ["demoMembers", "/demo/members"],
  ] as const)("%s is a GET of %s", async (method, path) => {
    const { api, fetchImpl } = setup(json(200, {}));
    await (api as unknown as Record<string, () => Promise<unknown>>)[method]();
    expect(fetchImpl.mock.calls[0][0]).toBe(path);
    expect((fetchImpl.mock.calls[0][1] as RequestInit).method ?? "GET").toBe("GET");
  });

  it("asks for an estimate with the store and the cart in cents in the query", async () => {
    const { api, fetchImpl } = setup(json(200, {}));
    await api.estimate("s3", 150000);
    expect(fetchImpl.mock.calls[0][0]).toBe("/estimate?store_id=s3&cart_cents=150000");
  });

  it("signs in by posting the chosen demo member", async () => {
    const { api, fetchImpl } = setup(json(200, { ok: true }));
    await api.switchMember("m_nurse");
    expect(fetchImpl).toHaveBeenCalledWith("/demo/switch-member", expect.objectContaining({
      method: "POST", body: JSON.stringify({ member_id: "m_nurse" }),
    }));
  });

  it.each([
    [401, { detail: "not_signed_in" }, "not_signed_in"],
    [400, { detail: "unknown_store" }, "unknown_store"],
    [503, { detail: "assistant_not_configured" }, "assistant_not_configured"],
    [502, { detail: "assistant_unavailable" }, "assistant_unavailable"],
    [422, { detail: [{ type: "string_too_long", loc: ["body", "message"], msg: "x", input: "y".repeat(5) }] }, "invalid_request"],
  ])("turns HTTP %i into an ApiError with the code %s", async (status, body, code) => {
    const { api } = setup(json(status, body));
    await expect(api.chat("hi", null)).rejects.toMatchObject({ status, code });
  });

  it("does not keep the rejected input of a 422 in the error", async () => {
    const { api } = setup(json(422, { detail: [{ input: "MARKER-PRIVATE-MESSAGE", msg: "too long" }] }));
    const error = await api.chat("hi", null).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(JSON.stringify(error) + String((error as Error).message)).not.toContain("MARKER-PRIVATE-MESSAGE");
  });

  it("copes with an error that is not JSON (an HTML page from a proxy)", async () => {
    const { api } = setup(new Response("<html>Bad gateway</html>", { status: 502 }));
    await expect(api.chat("hi", null)).rejects.toMatchObject({ status: 502, code: "http_error" });
  });

  it("copes with a success that is not JSON", async () => {
    const { api } = setup(new Response("<html>hello</html>", { status: 200 }));
    await expect(api.me()).rejects.toMatchObject({ code: "bad_response" });
  });

  it("copes with a chat answer that has no reply", async () => {
    const { api } = setup(json(200, { nope: true }));
    await expect(api.chat("hi", null)).rejects.toMatchObject({ code: "bad_response" });
  });

  it("turns a network failure into an ApiError with status 0", async () => {
    const { api } = setup(() => Promise.reject(new TypeError("Failed to fetch")));
    await expect(api.chat("hi", null)).rejects.toMatchObject({ status: 0, code: "network" });
  });
});
