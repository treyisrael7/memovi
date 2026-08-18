/**
 * Test-only session cookie bridge for jsdom live smoke.
 *
 * Node's fetch and jsdom's XMLHttpRequest do not share a browser cookie jar,
 * and production session cookies are HttpOnly. This helper records Set-Cookie
 * from API responses and attaches Cookie on subsequent API requests.
 *
 * Uploads use XMLHttpRequest; jsdom's XHR status is not reliably writable, so
 * API XHR is implemented with fetch while preserving the uploadDocument shape.
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

async function readFormPartBytes(value: FormDataEntryValue): Promise<Uint8Array> {
  if (typeof value === "string") {
    return new TextEncoder().encode(value);
  }

  if (typeof FileReader !== "undefined") {
    const fromReader = await new Promise<Uint8Array | null>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result;
        if (result instanceof ArrayBuffer) {
          resolve(new Uint8Array(result));
          return;
        }
        if (typeof result === "string") {
          resolve(new TextEncoder().encode(result));
          return;
        }
        resolve(null);
      };
      reader.onerror = () => resolve(null);
      try {
        reader.readAsArrayBuffer(value);
      } catch {
        resolve(null);
      }
    });
    if (fromReader && fromReader.byteLength > 0) {
      return fromReader;
    }
  }

  if (typeof value.arrayBuffer === "function") {
    return new Uint8Array(await value.arrayBuffer());
  }

  const buffered = (value as { _buffer?: ArrayBuffer | Uint8Array })._buffer;
  if (buffered) {
    return buffered instanceof Uint8Array
      ? buffered
      : new Uint8Array(buffered);
  }

  throw new Error(
    `Unsupported upload part type: ${Object.prototype.toString.call(value)}`,
  );
}

/** jsdom FormData/File is not accepted by Node fetch; encode multipart bytes. */
async function formDataToMultipart(form: FormData): Promise<{
  body: Uint8Array;
  contentType: string;
}> {
  const boundary = `----MemoviLiveSmoke${crypto.randomUUID().replace(/-/g, "")}`;
  const encoder = new TextEncoder();
  const chunks: Uint8Array[] = [];

  const push = (data: string | Uint8Array) => {
    chunks.push(typeof data === "string" ? encoder.encode(data) : data);
  };

  for (const [name, value] of form.entries()) {
    push(`--${boundary}\r\n`);
    if (typeof value === "string") {
      push(`Content-Disposition: form-data; name="${name}"\r\n\r\n`);
      push(`${value}\r\n`);
    } else {
      const filename = "name" in value && value.name ? value.name : "upload.bin";
      const type =
        "type" in value && value.type ? value.type : "application/octet-stream";
      push(
        `Content-Disposition: form-data; name="${name}"; filename="${filename}"\r\n`,
      );
      push(`Content-Type: ${type}\r\n\r\n`);
      const bytes = await readFormPartBytes(value);
      const decoded = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
      if (
        bytes.byteLength === 0 ||
        decoded === "[object File]" ||
        decoded === "[object Blob]"
      ) {
        throw new Error(
          `Upload file part '${filename}' did not contain document bytes ` +
            `(${bytes.byteLength} bytes, preview=${JSON.stringify(decoded.slice(0, 80))})`,
        );
      }
      push(bytes);
      push(`\r\n`);
    }
  }
  push(`--${boundary}--\r\n`);

  const length = chunks.reduce((total, chunk) => total + chunk.byteLength, 0);
  const body = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return {
    body,
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

class LiveApiXMLHttpRequest {
  static readonly UNSENT = 0;
  static readonly OPENED = 1;
  static readonly HEADERS_RECEIVED = 2;
  static readonly LOADING = 3;
  static readonly DONE = 4;

  status = 0;
  statusText = "";
  responseText = "";
  response: string | null = "";
  readyState = LiveApiXMLHttpRequest.UNSENT;
  withCredentials = false;
  onload: ((this: XMLHttpRequest, ev: ProgressEvent) => void) | null = null;
  onerror: ((this: XMLHttpRequest, ev: ProgressEvent) => void) | null = null;
  onabort: ((this: XMLHttpRequest, ev: ProgressEvent) => void) | null = null;
  upload: { onprogress: ((ev: ProgressEvent) => void) | null } = {
    onprogress: null,
  };

  private method = "GET";
  private url = "";
  private headers = new Headers();

  constructor(
    private readonly originalFetch: typeof fetch,
    private readonly store: Map<string, string>,
    private readonly apiBase: string,
  ) {}

  open(method: string, url: string | URL): void {
    this.method = method;
    this.url = String(url);
    this.headers = new Headers();
    this.readyState = LiveApiXMLHttpRequest.OPENED;
  }

  setRequestHeader(name: string, value: string): void {
    this.headers.set(name, value);
  }

  abort(): void {
    this.onabort?.call(
      this as unknown as XMLHttpRequest,
      new ProgressEvent("abort"),
    );
  }

  send(body?: Document | XMLHttpRequestBodyInit | null): void {
    if (!isApiUrl(this.url, this.apiBase)) {
      this.onerror?.call(
        this as unknown as XMLHttpRequest,
        new ProgressEvent("error"),
      );
      return;
    }

    if (this.store.size > 0 && !this.headers.has("Cookie")) {
      this.headers.set("Cookie", cookieHeader(this.store));
    }

    this.readyState = LiveApiXMLHttpRequest.LOADING;

    void (async () => {
      try {
        const headers = new Headers(this.headers);
        if (this.store.size > 0 && !headers.has("Cookie")) {
          headers.set("Cookie", cookieHeader(this.store));
        }

        let fetchBody: BodyInit | null | undefined =
          body && !(body instanceof Document) ? (body as BodyInit) : null;
        if (typeof FormData !== "undefined" && body instanceof FormData) {
          const multipart = await formDataToMultipart(body);
          fetchBody = multipart.body;
          headers.set("Content-Type", multipart.contentType);
          this.upload.onprogress?.(
            new ProgressEvent("progress", {
              lengthComputable: true,
              loaded: multipart.body.byteLength,
              total: multipart.body.byteLength,
            }),
          );
        }

        const response = await this.originalFetch(this.url, {
          method: this.method,
          headers,
          body: fetchBody,
        });
        ingestCookies(response.headers, this.store);
        const text = await response.text();
        this.status = response.status;
        this.statusText = response.statusText;
        this.responseText = text;
        this.response = text;
        this.readyState = LiveApiXMLHttpRequest.DONE;
        this.onload?.call(
          this as unknown as XMLHttpRequest,
          new ProgressEvent("load"),
        );
      } catch (error: unknown) {
        const detail = error instanceof Error ? error.message : String(error);
        this.status = 599;
        this.statusText = "Network Error";
        this.responseText = JSON.stringify({ detail });
        this.response = this.responseText;
        this.readyState = LiveApiXMLHttpRequest.DONE;
        this.onload?.call(
          this as unknown as XMLHttpRequest,
          new ProgressEvent("load"),
        );
      }
    })();
  }
}

export function installLiveApiCookieBridge(
  apiBase: string = API_BASE_URL,
): () => void {
  const store = new Map<string, string>();
  const originalFetch = globalThis.fetch.bind(globalThis);
  const OriginalXHR = globalThis.XMLHttpRequest;

  globalThis.fetch = (async (
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> => {
    const url = requestUrl(input);
    const headers = new Headers(
      input instanceof Request ? input.headers : undefined,
    );
    if (init?.headers) {
      new Headers(init.headers).forEach((value, key) => {
        headers.set(key, value);
      });
    }
    if (isApiUrl(url, apiBase) && store.size > 0 && !headers.has("Cookie")) {
      headers.set("Cookie", cookieHeader(store));
    }
    // jsdom AbortSignal is not an undici AbortSignal; passing it makes chat SSE
    // hang or throw "Expected signal to be an instance of AbortSignal".
    const { signal: _jsdomSignal, ...restInit } = init ?? {};
    const fetchInput =
      input instanceof Request
        ? new Request(url, {
            method: input.method,
            headers,
            body: input.body,
            credentials: input.credentials,
            redirect: input.redirect,
          })
        : input;
    const response = await originalFetch(fetchInput, {
      ...restInit,
      headers,
      signal: undefined,
    });
    if (isApiUrl(url, apiBase)) {
      ingestCookies(response.headers, store);
    }
    return response;
  }) as typeof fetch;

  function BridgedXHR() {
    return new LiveApiXMLHttpRequest(originalFetch, store, apiBase);
  }
  BridgedXHR.UNSENT = LiveApiXMLHttpRequest.UNSENT;
  BridgedXHR.OPENED = LiveApiXMLHttpRequest.OPENED;
  BridgedXHR.HEADERS_RECEIVED = LiveApiXMLHttpRequest.HEADERS_RECEIVED;
  BridgedXHR.LOADING = LiveApiXMLHttpRequest.LOADING;
  BridgedXHR.DONE = LiveApiXMLHttpRequest.DONE;
  globalThis.XMLHttpRequest = BridgedXHR as unknown as typeof XMLHttpRequest;

  return () => {
    globalThis.fetch = originalFetch;
    globalThis.XMLHttpRequest = OriginalXHR;
  };
}
