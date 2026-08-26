mod native_auth_smoke;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let builder = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(native_auth_smoke::create_main_window);
    native_auth_smoke::attach(builder)
        .run(tauri::generate_context!())
        .expect("error while running Memovi desktop application");
}
