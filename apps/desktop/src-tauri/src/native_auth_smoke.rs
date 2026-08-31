//! Optional packaged-WebView auth probe and smoke-only WebView profile.
//!
//! Inactive unless `MEMOVI_NATIVE_AUTH_SMOKE=1`. Production launches never set
//! that variable, so this module does not change the shipped session path.
//! When enabled, JavaScript runs *inside* the real WebView after the app URL
//! loads, so `fetch(..., { credentials: "include" })` uses that engine's cookie
//! jar — not TestClient, jsdom, or a Rust HTTP client.

use std::path::PathBuf;
use std::sync::Once;

use tauri::webview::PageLoadEvent;

const API_BASE_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_API";
const REPORT_URL_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_REPORT";
const ENABLED_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE";
const PROFILE_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_PROFILE";
const TAURI_ENV: &str = "MEMOVI_NATIVE_AUTH_SMOKE_TAURI";

static SMOKE_STARTED: Once = Once::new();

pub fn enabled() -> bool {
    std::env::var(ENABLED_ENV)
        .map(|value| value == "1")
        .unwrap_or(false)
}

pub fn create_main_window(app: &mut tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let config = app
        .config()
        .app
        .windows
        .first()
        .cloned()
        .ok_or("Memovi desktop requires a window configuration")?;
    let mut builder = tauri::WebviewWindowBuilder::from_config(app, &config)?;
    if enabled() {
        if let Ok(dir) = std::env::var(PROFILE_ENV) {
            if !dir.trim().is_empty() {
                let path = PathBuf::from(dir);
                std::fs::create_dir_all(&path)?;
                builder = builder.data_directory(path);
            }
        }
    }
    builder.build()?;
    Ok(())
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
    let tauri_version = std::env::var(TAURI_ENV).unwrap_or_default();

    let script = smoke_script(&api_base, &report_url, &tauri_version);
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

fn host_platform() -> &'static str {
    match std::env::consts::OS {
        "macos" => "macos",
        "windows" => "windows",
        "linux" => "linux",
        other => other,
    }
}

fn smoke_script(api_base: &str, report_url: &str, tauri_version: &str) -> String {
    let api_base_js = serde_json::to_string(api_base.trim_end_matches('/')).unwrap();
    let report_url_js = serde_json::to_string(report_url).unwrap();
    let platform_js = serde_json::to_string(host_platform()).unwrap();
    let tauri_js = serde_json::to_string(tauri_version).unwrap();
    format!(
        r#"(function () {{
  const apiBase = {api_base_js};
  const reportUrl = {report_url_js};
  const report = {{
    platform: {platform_js},
    tauri: {tauri_js},
    origin: String(location.origin || ""),
    href: String(location.href || ""),
    userAgent: String(navigator.userAgent || ""),
    documentCookieReadable: String(document.cookie || ""),
    steps: [],
    ok: false
  }};
  function step(name, extra) {{
    report.steps.push(Object.assign({{ name: name }}, extra || {{}}));
  }}
  function parseEmail(body) {{
    try {{
      const data = JSON.parse(body);
      return typeof data.email === "string" ? data.email : "";
    }} catch (error) {{
      return "";
    }}
  }}
  async function call(path, init) {{
    const headers = Object.assign(
      {{ "X-Memovi-Native-Smoke": "1", "Accept": "application/json" }},
      (init && init.headers) || {{}}
    );
    const response = await fetch(apiBase + path, Object.assign({{}}, init || {{}}, {{
      credentials: "include",
      cache: "no-store",
      headers: headers
    }}));
    let body = "";
    try {{ body = await response.text(); }} catch (error) {{ body = ""; }}
    return {{
      status: response.status,
      body: body,
      sessionCookie: response.headers.get("X-Memovi-Session-Cookie") || "",
      sessionReceived: response.headers.get("X-Memovi-Session-Received") || "",
      cacheControl: response.headers.get("Cache-Control") || ""
    }};
  }}
  function finish() {{
    try {{
      fetch(reportUrl, {{ method: "POST", body: JSON.stringify(report), keepalive: true }});
    }} catch (error) {{}}
  }}
  (async function () {{
    try {{
      step("origin", {{ origin: report.origin }});
      if (!report.origin) {{
        throw new Error("origin cannot be determined");
      }}
      const email = "native-smoke-" + Date.now() + "-" + Math.random().toString(16).slice(2) + "@memovi.test";
      const password = "password123";
      const registered = await call("/auth/register", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ email: email, password: password }})
      }});
      step("register", {{
        status: registered.status,
        email: email,
        sessionCookie: registered.sessionCookie,
        sessionReceived: registered.sessionReceived
      }});
      if (registered.status !== 201) {{
        throw new Error("register HTTP " + registered.status);
      }}
      const meAuthed = await call("/auth/me");
      const meEmail = parseEmail(meAuthed.body);
      step("me_after_register", {{
        status: meAuthed.status,
        email: meEmail,
        sessionReceived: meAuthed.sessionReceived,
        cacheControl: meAuthed.cacheControl
      }});
      if (meAuthed.status !== 200) {{
        throw new Error("authenticated /auth/me HTTP " + meAuthed.status);
      }}
      if (meEmail !== email) {{
        throw new Error("authenticated /auth/me email mismatch");
      }}
      const loggedOut = await call("/auth/logout", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: "{{}}"
      }});
      step("logout", {{
        status: loggedOut.status,
        sessionCookie: loggedOut.sessionCookie,
        sessionReceived: loggedOut.sessionReceived
      }});
      if (loggedOut.status !== 204) {{
        throw new Error("logout HTTP " + loggedOut.status);
      }}
      const meAnon = await call("/auth/me");
      step("me_after_logout", {{
        status: meAnon.status,
        sessionReceived: meAnon.sessionReceived,
        cacheControl: meAnon.cacheControl
      }});
      if (meAnon.status !== 401) {{
        throw new Error("expected 401 after logout, got " + meAnon.status);
      }}
      const meAnonAgain = await call("/auth/me");
      step("me_after_logout_repeat", {{ status: meAnonAgain.status }});
      if (meAnonAgain.status !== 401) {{
        throw new Error("expected repeat 401 after logout, got " + meAnonAgain.status);
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
