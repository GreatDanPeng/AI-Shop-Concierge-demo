import type { DemoMember, Discounts, Estimate, Health, Identity } from "./types";

// An error from the API. It carries only the HTTP status and a short code, never the text of the
// request or of the server's reply, so it is safe to show or log.
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super(`HTTP ${status}: ${code}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type ApiOptions = { apiBase?: string; fetchImpl?: typeof fetch };
export type Api = ReturnType<typeof createApi>;

async function errorCode(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "invalid_request"; // validation errors echo the input: ignore it
  } catch {
    // not JSON (for example an HTML page from a proxy)
  }
  return "http_error";
}

export function createApi({ apiBase = "", fetchImpl }: ApiOptions = {}) {
  const doFetch: typeof fetch = fetchImpl ?? ((...args) => fetch(...args));
  // Same origin: the demo sign-in cookie travels by itself. Another origin needs "include" (and CORS).
  const credentials: RequestCredentials = apiBase ? "include" : "same-origin";

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let response: Response;
    try {
      response = await doFetch(apiBase + path, { credentials, ...init });
    } catch {
      throw new ApiError(0, "network");
    }
    if (!response.ok) throw new ApiError(response.status, await errorCode(response));
    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError(response.status, "bad_response");
    }
  }

  const post = <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });

  return {
    health: () => request<Health>("/health"),
    demoMembers: () => request<DemoMember[]>("/demo/members"),
    switchMember: (memberId: string) => post<{ ok: boolean }>("/demo/switch-member", { member_id: memberId }),
    me: () => request<Identity>("/me"),
    discounts: () => request<Discounts>("/discounts"),
    estimate: (storeId: string, cartCents: number) =>
      request<Estimate>(`/estimate?store_id=${encodeURIComponent(storeId)}&cart_cents=${cartCents}`),
    // The member is never sent: the server knows who is signed in from the cookie.
    async chat(message: string, storeId: string | null): Promise<string> {
      const data = await post<{ reply?: unknown }>("/chat", { message, store_id: storeId });
      if (typeof data.reply !== "string") throw new ApiError(200, "bad_response");
      return data.reply;
    },
  };
}
