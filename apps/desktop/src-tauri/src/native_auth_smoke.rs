//! Optional packaged-WebView auth probe.
//!
//! Inactive unless `MEMOVI_NATIVE_AUTH_SMOKE=1`. Production launches never set
//! that variable, so this module does not change the shipped session path.
//! When enabled, JavaScript runs *inside* the real WebView after the app URL
//! loads, so `fetch(..., { credentials: "include" })` uses that engine's cookie
//! jar — not TestClient, jsdom, or a Rust HTTP client.

use std::sync::Once;

use tauri::webview::PageLoadEvent;

const API_BASE_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_API";
const REPORT_URL_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_REPORT";
const ENABLED_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE";

static SMOKE_STARTED: Once = Once::new();

pub fn enabled() -> bool {
    std::env::var(ENABLED_ENV)
        .map(|value| value == "1")
        .unwrap_or(false)
}

pub fn attach<R: tauri::Runtime>(builder: tauri::Builder<R>) -> tauri::Builder<R> {
    if !enabled() {
        return builder;
    }

    let api_base = std::env::var(API_BASE_ENV).unwrap_or_else(|_| "http://127.0.0.1:8000".into());
    let Ok(report_url) = std::env::var(REPORT_URL_ENV) else {
        eprintln!("{REPORT_URL_ENV} is required when {ENABLED_ENV}=1; skipping native auth smoke");
        return builder;
    };

    let script = smoke_script(&api_base, &report_url);
    builder.on_page_load(move |webview, payload| {
        if !matches!(payload.event(), PageLoadEvent::Finished) {
            return;
        }
        if payload.url().scheme() == "about" {
            return;
        }
        if SMOKE_STARTED.is_completed() {
            return;
        }
        let script = script.clone();
        let webview = webview.clone();
        SMOKE_STARTED.call_once(move || {
            if let Err(error) = webview.eval(script) {
                eprintln!("native auth smoke eval failed: {error}");
            }
        });
    })
}

fn smoke_script(api_base: &str, report_url: &str) -> String {
    let api_base_js = serde_json::to_string(api_base.trim_end_matches('/')).unwrap();
    let report_url_js = serde_json::to_string(report_url).unwrap();
    format!(
        r#"(function () {{
  const apiBase = {api_base_js};
  const reportUrl = {report_url_js};
  const report = {{
    origin: String(location.origin || ""),
    href: String(location.href || ""),
    documentCookieReadable: String(document.cookie || ""),
    steps: [],
    ok: false
  }};
  function step(name, extra) {{
    report.steps.push(Object.assign({{ name: name }}, extra || {{}}));
  }}
  async function call(path, init) {{
    const response = await fetch(apiBase + path, Object.assign({{}}, init || {{}}, {{ credentials: "include" }}));
    let body = "";
    try {{ body = await response.text(); }} catch (error) {{ body = ""; }}
    return {{ status: response.status, body: body }};
  }}
  function finish() {{
    try {{
      fetch(reportUrl, {{ method: "POST", body: JSON.stringify(report), keepalive: true }});
    }} catch (error) {{}}
  }}
  (async function () {{
    try {{
      step("origin", {{ origin: report.origin }});
      const email = "native-smoke-" + Date.now() + "-" + Math.random().toString(16).slice(2) + "@memovi.test";
      const password = "password123";
      const registered = await call("/auth/register", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json", "Accept": "application/json" }},
        body: JSON.stringify({{ email: email, password: password }})
      }});
      step("register", {{ status: registered.status }});
      if (registered.status !== 201) {{
        throw new Error("register HTTP " + registered.status);
      }}
      const meAuthed = await call("/auth/me", {{
        headers: {{ "Accept": "application/json" }}
      }});
      step("me_after_register", {{ status: meAuthed.status }});
      if (meAuthed.status !== 200) {{
        throw new Error("authenticated /auth/me HTTP " + meAuthed.status);
      }}
      const loggedOut = await call("/auth/logout", {{
        method: "POST",
        headers: {{ "Accept": "application/json", "Content-Type": "application/json" }},
        body: "{{}}"
      }});
      step("logout", {{ status: loggedOut.status }});
      if (loggedOut.status !== 204 && loggedOut.status !== 200) {{
        throw new Error("logout HTTP " + loggedOut.status);
      }}
      const meAnon = await call("/auth/me", {{
        headers: {{ "Accept": "application/json" }}
      }});
      step("me_after_logout", {{ status: meAnon.status }});
      if (meAnon.status !== 401) {{
        throw new Error("expected 401 after logout, got " + meAnon.status);
      }}
      report.ok = true;
    }} catch (error) {{
      report.error = String(error && error.message ? error.message : error);
    }} finally {{
      finish();
    }}
  }})();
}})();"#
    )
}
