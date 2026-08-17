/**
 * Test-only session cookie bridge for jsdom live smoke.
 *
 * Node's fetch and jsdom's XMLHttpRequest do not share a browser cookie jar,
 * and production session cookies are HttpOnly. This helper records Set-Cookie
 * from API responses and attaches Cookie on subsequent API requests.
 * Production auth and cookie flags are unchanged.
 */

import { API_BASE_URL } from "../api/config";

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.href;
  }
  return input.url;
}

function isApiUrl(url: string, apiBase: string): boolean {
  return url.startsWith(apiBase);
}

function readSetCookie(headers: Headers): string[] {
  const withSetCookie = headers as Headers & {
    getSetCookie?: () => string[];
  };
  if (typeof withSetCookie.getSetCookie === "function") {
    return withSetCookie.getSetCookie();
  }
  const single = headers.get("set-cookie");
  return single ? [single] : [];
}

function ingestCookies(headers: Headers, store: Map<string, string>): void {
  for (const line of readSetCookie(headers)) {
    const pair = line.split(";", 1)[0];
    if (!pair) continue;
    const separator = pair.indexOf("=");
    if (separator <= 0) continue;
    const name = pair.slice(0, separator).trim();
    const value = pair.slice(separator + 1).trim();
    if (!name) continue;
    if (line.toLowerCase().includes("max-age=0") || value === "") {
      store.delete(name);
      continue;
    }
    store.set(name, value);
  }
}

function cookieHeader(store: Map<string, string>): string {
  return [...store.entries()]
    .map(([name, value]) => `${name}=${value}`)
    .join("; ");
}

export function installLiveApiCookieBridge(
  apiBase: string = API_BASE_URL,
): () => void {
  const store = new Map<string, string>();
  const originalFetch = globalThis.fetch.bind(globalThis);
  const OriginalXHR = globalThis.XMLHttpRequest;
  const proto = OriginalXHR.prototype;
  const originalOpen = proto.open;
  const originalSetRequestHeader = proto.setRequestHeader;
  const originalSend = proto.send;

  const xhrMethod = new WeakMap<XMLHttpRequest, string>();
  const xhrUrl = new WeakMap<XMLHttpRequest, string>();
  const xhrHeaders = new WeakMap<XMLHttpRequest, Headers>();

  globalThis.fetch = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url = requestUrl(input);
    const headers = new Headers(init?.headers);
    if (isApiUrl(url, apiBase) && store.size > 0 && !headers.has("Cookie")) {
      headers.set("Cookie", cookieHeader(store));
    }
    const response = await originalFetch(input, { ...init, headers });
    if (isApiUrl(url, apiBase)) {
      ingestCookies(response.headers, store);
    }
    return response;
  }) as typeof fetch;

  proto.open = function open(
    this: XMLHttpRequest,
    method: string,
    url: string | URL,
    async?: boolean,
    username?: string | null,
    password?: string | null,
  ) {
    xhrMethod.set(this, method);
    xhrUrl.set(this, String(url));
    xhrHeaders.set(this, new Headers());
    return originalOpen.call(
      this,
      method,
      url,
      async ?? true,
      username,
      password,
    );
  } as typeof proto.open;

  proto.setRequestHeader = function setRequestHeader(
    this: XMLHttpRequest,
    name: string,
    value: string,
  ) {
    xhrHeaders.get(this)?.set(name, value);
    if (name.toLowerCase() === "cookie") {
      return;
    }
    return originalSetRequestHeader.call(this, name, value);
  };

  proto.send = function send(
    this: XMLHttpRequest,
    body?: Document | XMLHttpRequestBodyInit | null,
  ) {
    const url = xhrUrl.get(this) ?? "";
    if (!isApiUrl(url, apiBase)) {
      return originalSend.call(this, body);
    }

    const method = xhrMethod.get(this) ?? "POST";
    const headers = xhrHeaders.get(this) ?? new Headers();
    if (store.size > 0 && !headers.has("Cookie")) {
      headers.set("Cookie", cookieHeader(store));
    }

    const xhr = this;
    void originalFetch(url, {
      method,
      headers,
      body: body as BodyInit | null | undefined,
      credentials: "include",
    })
      .then(async (response) => {
        ingestCookies(response.headers, store);
        const text = await response.text();
        Object.defineProperty(xhr, "status", {
          configurable: true,
          get: () => response.status,
        });
        Object.defineProperty(xhr, "statusText", {
          configurable: true,
          get: () => response.statusText,
        });
        Object.defineProperty(xhr, "responseText", {
          configurable: true,
          get: () => text,
        });
        Object.defineProperty(xhr, "response", {
          configurable: true,
          get: () => text,
        });
        Object.defineProperty(xhr, "readyState", {
          configurable: true,
          get: () => XMLHttpRequest.DONE,
        });
        xhr.onload?.call(xhr, new ProgressEvent("load"));
        xhr.dispatchEvent(new Event("load"));
      })
      .catch(() => {
        xhr.onerror?.call(xhr, new ProgressEvent("error"));
        xhr.dispatchEvent(new Event("error"));
      });
  };

  return () => {
    globalThis.fetch = originalFetch;
    proto.open = originalOpen;
    proto.setRequestHeader = originalSetRequestHeader;
    proto.send = originalSend;
  };
}
