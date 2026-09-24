/* Typed API client. All requests are same-origin (/api/v1 is proxied to FastAPI by Next). */

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;
  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const BASE = "/api/v1";

async function parse(res: Response) {
  const text = await res.text();
  let body: any = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) {
    const err = body?.error;
    throw new ApiError(
      res.status,
      err?.code ?? "http_error",
      err?.message ?? (res.status >= 500 ? "Something went wrong on our side. Please try again." : "Request failed."),
      err?.details,
    );
  }
  return body;
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      credentials: "include",
      ...rest,
      headers: { ...(json !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });
  } catch {
    throw new ApiError(0, "network_error", "We couldn't reach PathFinder. Check your connection and try again.");
  }
  return parse(res);
}

export const get = <T = any>(path: string) => api<T>(path);
export const post = <T = any>(path: string, json?: unknown) => api<T>(path, { method: "POST", json: json ?? {} });
export const patch = <T = any>(path: string, json?: unknown) => api<T>(path, { method: "PATCH", json: json ?? {} });
export const del = <T = any>(path: string) => api<T>(path, { method: "DELETE" });

export async function upload<T = any>(path: string, form: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { method: "POST", body: form, credentials: "include" });
  } catch {
    throw new ApiError(0, "network_error", "Upload failed — check your connection.");
  }
  return parse(res);
}

export type StreamEvent =
  | { event: "meta"; data: any }
  | { event: "token"; data: { t: string } }
  | { event: "done"; data: any }
  | { event: "error"; data: { code: string; message: string } };

/** POST and consume a Server-Sent Events stream. */
export async function stream(path: string, json: unknown, onEvent: (e: StreamEvent) => void, signal?: AbortSignal) {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(json),
      signal,
    });
  } catch (e: any) {
    if (e?.name === "AbortError") return;
    throw new ApiError(0, "network_error", "We couldn't reach the mentor. Check your connection.");
  }
  if (!res.ok || !res.body) await parse(res);
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let event = "message";
      let data = "";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      try {
        onEvent({ event, data: JSON.parse(data) } as StreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
